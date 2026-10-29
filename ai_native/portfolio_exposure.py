"""Private, conservative look-through exposure aggregation from an M3 P-ledger.

Read-only caller-supplied classifications. Fund compositions are not fetched or
certified; unknown portions remain unknown. No investment room or trades.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping

CENT = Decimal("0.01")
HUNDRED = Decimal(100)


def _text(v: Any, label: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{label}: nonempty text required")
    return v.strip()


def _date(v: Any, label: str) -> date:
    s = _text(v, label)
    try:
        d = date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO date") from exc
    if d.isoformat() != s:
        raise ValueError(f"{label}: canonical YYYY-MM-DD required")
    return d


def _decimal(v: Any, label: str) -> Decimal:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{label}: decimal string required")
    try:
        d = Decimal(v)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if not d.is_finite() or d < 0 or d.adjusted() > 15:
        raise ValueError(f"{label}: finite nonnegative and bounded decimal required")
    return d


def aggregate_portfolio_exposures(
    ledger: Mapping[str, Any], *,
    classifications_by_p_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return private lower-bound economic/sector/region exposures.

    Direct security classifications must be explicitly supplied. Funds have a
    supplied fractional composition with a complete-coverage *claim*; any
    remainder becomes UNKNOWN. This is NEVER verified investment evidence.
    """
    if not isinstance(ledger, Mapping) or not isinstance(classifications_by_p_id, Mapping):
        raise ValueError("ledger and classifications_by_p_id: mappings required")
    if (ledger.get("status") != "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"
            or not isinstance(ledger.get("known_scope_weights_pct"), Mapping)):
        return {"status": "UNAVAILABLE_INCOMPLETE_P_LEDGER", "economic_issuer_pct_private": None,
                "portfolio_room_status": "ROOM_UNAVAILABLE", "source_authentication": "NOT_PERFORMED"}
    if ledger.get("private_scope") is not True:
        raise ValueError("PRIVATE_SCOPE_REQUIRED")
    aid = _text(ledger.get("analysis_id"), "analysis_id")
    cutoff = _date(ledger.get("observed_on"), "observed_on")
    total = _decimal(ledger.get("scope_total_base"), "scope_total_base")
    if total == 0:
        raise ValueError("ZERO_SCOPED_DENOMINATOR")
    records = ledger.get("p_ledger_private")
    cash_row = ledger.get("cash_record_private")
    if not isinstance(records, list) or not isinstance(cash_row, Mapping):
        raise ValueError("MISSING_P_LEDGER_ROWS")
    if cash_row.get("visibility") != "VERIFIED_VISIBLE":
        raise ValueError("CASH_NOT_VISIBLY_ACCOUNTED")
    cash = _decimal(cash_row.get("amount_base"), "cash.amount_base")
    sums: dict[str, dict[str, Decimal]] = {g: defaultdict(Decimal) for g in ("issuer", "sector", "region")}
    # Scenario-only attribution for prior fund snapshots. Never mix it with
    # today's known exposure lower bounds or today's unknown exposure.
    historical_sums: dict[str, dict[str, Decimal]] = {
        g: defaultdict(Decimal) for g in ("issuer", "sector", "region")
    }
    unknown = Decimal(0)
    seen = set()
    funds = []
    historical_fund_p_ids = []
    classification_provenance = []
    qualifications = []
    values_total = cash

    def add_exposure(amount: Decimal, row: Mapping[str, Any], source: str, *,
                     destination: Mapping[str, dict[str, Decimal]] = sums) -> None:
        for group, col in (("issuer", "economic_issuer_id"), ("sector", "sector"), ("region", "region")):
            key = _text(row.get(col), f"{source}.{col}")
            destination[group][key] += amount

    for i, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise ValueError("INVALID_P_RECORD")
        pid = _text(record.get("p_id"), f"P[{i}].p_id")
        if pid in seen or pid == "P-CASH":
            raise ValueError("DUPLICATE_OR_RESERVED_P_ID")
        seen.add(pid)
        val = _decimal(record.get("market_value_base"), f"{pid}.market_value_base")
        values_total += val
        classification = classifications_by_p_id.get(pid)
        if classification is None:
            unknown += val
            qualifications.append(f"{pid}:CLASSIFICATION_MISSING")
            continue
        if not isinstance(classification, Mapping):
            raise ValueError(f"{pid}: classification must be a mapping")
        if _text(classification.get("security_id"), f"{pid}.security_id") != record.get("security_id"):
            raise ValueError("SECURITY_ID_MISMATCH")
        kind = _text(classification.get("kind"), f"{pid}.kind")
        source_ref = _text(classification.get("source_ref"), f"{pid}.source_ref")
        dated = _date(classification.get("as_of"), f"{pid}.as_of")
        rights = _text(classification.get("rights_status"), f"{pid}.rights_status")
        if rights not in {"PERMITTED", "UNCERTAIN", "RESTRICTED"}:
            raise ValueError("SOURCE_RIGHTS_INVALID")
        if dated > cutoff:
            raise ValueError("CLASSIFICATION_NEWER_THAN_OBSERVATION")
        classification_provenance.append({"p_id": pid, "source_ref_private": source_ref,
                                          "as_of": dated.isoformat(), "rights_status": rights})
        if rights != "PERMITTED":
            unknown += val
            qualifications.append(f"{pid}:SOURCE_RIGHTS_{rights}")
            continue
        if kind == "DIRECT_EQUITY":
            add_exposure(val, classification, source_ref)
        elif kind == "FUND":
            # A dated fund holdings snapshot is not proof of today's
            # constituents. Keep its scenario arithmetic privately, but do
            # not let prior-dated holdings imply current Portfolio Room.
            is_historical = dated < cutoff
            if is_historical:
                historical_fund_p_ids.append(pid)
                qualifications.append(f"{pid}:FUND_COMPOSITION_PREDATES_OBSERVATION")
            completeness = classification.get("composition_complete_reported")
            if type(completeness) is not bool:
                raise ValueError("FUND_COMPLETENESS_BOOLEAN_REQUIRED")
            holdings = classification.get("constituents")
            if not isinstance(holdings, list):
                raise ValueError("FUND_CONSTITUENTS_LIST_REQUIRED")
            summed_fraction = Decimal(0)
            for j, holding in enumerate(holdings):
                if not isinstance(holding, Mapping):
                    raise ValueError("INVALID_FUND_CONSTITUENT")
                fraction = _decimal(holding.get("fund_weight_pct"), f"{pid}.constituent[{j}].fund_weight_pct")
                summed_fraction += fraction
                add_exposure(
                    val * fraction / HUNDRED, holding, source_ref,
                    destination=historical_sums if is_historical else sums,
                )
            if summed_fraction > HUNDRED:
                raise ValueError("FUND_COMPOSITION_OVER_100_PERCENT")
            if completeness and summed_fraction != HUNDRED:
                raise ValueError("FALSE_FUND_COMPLETENESS_ASSERTION")
            if not completeness and summed_fraction == HUNDRED:
                raise ValueError("FUND_TOTAL_100_REQUIRES_EXPLICIT_COVERAGE_CONFIRMATION")
            # Old holdings lists cannot certify any fraction of the present
            # fund position. Count the ENTIRE fund as unknown today even when
            # its prior snapshot happened to sum to 100%.
            unknown += (val if is_historical
                        else val * (HUNDRED - summed_fraction) / HUNDRED)
            if summed_fraction != HUNDRED:
                qualifications.append(f"{pid}:FUND_COMPOSITION_PARTIAL")
            funds.append({"p_id": pid, "source_ref_private": source_ref,
                          "reported_composition_coverage_pct": str(summed_fraction),
                          "complete_reported_not_authenticated": completeness,
                          "current_exposure_treatment": (
                              "HISTORICAL_ILLUSTRATIVE_ONLY" if is_historical
                              else "CURRENT_DATED_CALLER_REPORT_ONLY")})
        else:
            raise ValueError("UNSUPPORTED_INSTRUMENT_KIND")
    if set(classifications_by_p_id) - seen:
        raise ValueError("CLASSIFICATION_OUTSIDE_P_SCOPE")
    if values_total != total:
        raise ValueError("SCOPE_TOTAL_RECONCILIATION_FAILED")
    scoped_known = total - cash - unknown
    if scoped_known < 0:
        raise ValueError("NEGATIVE_KNOWN_EXPOSURE")

    def pct(amount: Decimal) -> str:
        return str((amount / total * HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP))

    def group_pct(group: str, bucket: Mapping[str, dict[str, Decimal]] = sums) -> dict[str, str]:
        return {k: pct(v) for k, v in sorted(bucket[group].items())}

    return {
        "status": "CALLER_REPORTED_SCOPED_EXPOSURES" if unknown == 0 else "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS",
        "analysis_id": aid, "observation_as_of": ledger["observed_on"],
        "account_scope_private": ledger.get("account_scope"), "currency": ledger.get("currency"),
        "economic_issuer_pct_private": group_pct("issuer"),
        "sector_pct_private": group_pct("sector"),
        "region_pct_private": group_pct("region"),
        "known_exposure_pct": pct(scoped_known),
        "unclassified_or_unknown_fund_pct": pct(unknown),
        "cash_pct": pct(cash), "fund_composition_private": funds,
        "historical_fund_scenario_private": (
            {"basis": "OLD_CONSTITUENTS_APPLIED_TO_CURRENT_REPORTED_FUND_VALUES_NOT_PIT",
             "economic_issuer_pct_of_current_scope_private": group_pct("issuer", historical_sums),
             "sector_pct_of_current_scope_private": group_pct("sector", historical_sums),
             "region_pct_of_current_scope_private": group_pct("region", historical_sums),
             "current_or_historical_actual_holdings": "NOT_ESTABLISHED"}
            if historical_fund_p_ids else None),
        "historical_fund_p_ids_private": sorted(historical_fund_p_ids),
        "fund_composition_date_alignment": (
            "PRIOR_DATED_FUND_SNAPSHOTS" if historical_fund_p_ids
            else "NO_PRIOR_DATED_FUND_SNAPSHOTS_REPORTED"),
        "classification_provenance_private": classification_provenance,
        "qualifications": sorted(qualifications),
        "coverage_scope": "EXPLICIT_LEDGER_SCOPE_ONLY_NOT_HOUSEHOLD_TOTAL",
        "source_authentication": "CALLER_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
        "economic_issuer_rank_coverage_reported_complete": (
            unknown == 0 and not historical_fund_p_ids),
        "portfolio_room_status": "ROOM_UNAVAILABLE",
        "trading_authority": "NONE", "writes": "NONE",
    }
