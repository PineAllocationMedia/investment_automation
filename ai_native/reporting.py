"""Read-only, evidence-preserving R1 report rendering.

No source retrieval, source verification, storage, scheduling, or trades.
All input statuses are caller-provided and preserved, never upgraded.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import re
from typing import Any, Mapping

from .strategy_authority import assess_r1_mode
from .strategy_research_brief import prepare_strategy_research_brief

EVIDENCE_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
REPORT_STATUSES = frozenset({"EXPLORATORY", "CONDITIONAL", "COMPONENT_SUPPORTED"})


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty string required")
    return value.strip()


def _iso_date(value: Any, field: str) -> str:
    text = _string(value, field)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{field}: ISO date YYYY-MM-DD required") from exc
    return text


def _facts(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("facts: list required")
    identifiers: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"facts[{i}]: record required")
        ref = _string(item.get("id"), f"facts[{i}].id")
        if ref in identifiers:
            raise ValueError(f"facts[{i}]: duplicate evidence ID")
        identifiers.add(ref)
        _string(item.get("claim"), f"facts[{i}].claim")
        status = _string(item.get("status"), f"facts[{i}].status")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"facts[{i}]: invalid evidence status")
        if status == "VERIFIED":
            url = _string(item.get("source_url"), f"facts[{i}].source_url")
            if not url.startswith("https://"):
                raise ValueError(f"facts[{i}]: verified claim needs HTTPS source URL")
            _string(item.get("period"), f"facts[{i}].period")
            _string(item.get("checked_by"), f"facts[{i}].checked_by")
            _iso_date(item.get("checked_at"), f"facts[{i}].checked_at")
    return value


def _source_review(packet: Mapping[str, Any], analysis_id: str, as_of: str,
                   facts: list[Mapping[str, Any]]) -> tuple[dict[str, list[str]], int] | None:
    """Validate private structural-review handoff, never certify research facts."""
    review = packet.get("fact_source_alignment_private")
    if review is None:
        return None
    if not isinstance(review, Mapping) or (
        review.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"
        or review.get("analysis_id") != analysis_id
        or review.get("analysis_as_of") != as_of
        or review.get("source_authentication") != "NOT_PERFORMED"
        or review.get("evidence_upgrade") != "NONE"
        or review.get("decision_grade_status") != "NOT_ESTABLISHED"
    ):
        raise ValueError("REPORT_SOURCE_REVIEW_AUTHORITY_OR_ID_MISMATCH")
    expected = {f["id"]: f["status"] for f in facts}
    rows = review.get("facts_private")
    if not isinstance(rows, list):
        raise ValueError("REPORT_SOURCE_REVIEW_FACTS_REQUIRED")
    by_id: dict[str, list[str]] = {}
    for entry in rows:
        if not isinstance(entry, Mapping):
            raise ValueError("REPORT_SOURCE_REVIEW_ENTRY_INVALID")
        fid = entry.get("fact_id_private")
        if fid not in expected or fid in by_id or entry.get("ir_reported_status") != expected[fid]:
            raise ValueError("REPORT_SOURCE_REVIEW_FACT_MISMATCH")
        flags = entry.get("review_flags")
        if not isinstance(flags, list) or any(
            not isinstance(f, str) or not f or not all(c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in f)
            for f in flags
        ):
            raise ValueError("REPORT_SOURCE_REVIEW_FLAGS_INVALID")
        alignment = "REVIEW_REQUIRED" if flags else "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"
        if entry.get("alignment") != alignment:
            raise ValueError("REPORT_SOURCE_REVIEW_ALIGNMENT_MISMATCH")
        by_id[fid] = flags
    count = sum(bool(x) for x in by_id.values())
    if set(by_id) != set(expected) or review.get("facts_needing_review") != count:
        raise ValueError("REPORT_SOURCE_REVIEW_COVERAGE_MISMATCH")
    return by_id, count



def _portfolio_observation_lines(packet: Mapping[str, Any], analysis_id: str,
                                 as_of: str) -> list[str]:
    """Describe supplied private P coverage without repeating holdings or cash amounts.

    The original structurally prepared P ledger stays outside this summary.
    A complete caller-reported denominator never certifies total ownership,
    account completeness, independent evidence or Portfolio Room.
    """
    observation = packet.get("portfolio_observation_private")
    if observation is None:
        return []
    if not isinstance(observation, Mapping) or (
        observation.get("analysis_id") != analysis_id
        or observation.get("analysis_as_of") != as_of
        or observation.get("private_scope") is not True
        or observation.get("verification") != "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"
        or observation.get("portfolio_room_status") != "ROOM_UNAVAILABLE"
        or observation.get("source_retrieval") != "NONE"
        or observation.get("blossom_access") != "NONE"
        or observation.get("writes") != "NONE"
        or observation.get("decision_authority") != "CEO_ONLY"
    ):
        raise ValueError("REPORT_P_LEDGER_AUTHORITY_OR_ID_MISMATCH")
    observed = _iso_date(observation.get("observed_on"), "P.observed_on")
    if observed > as_of:
        raise ValueError("REPORT_P_LEDGER_AFTER_CUTOFF")
    records = observation.get("p_ledger_private")
    if not isinstance(records, list) or not records or len(records) > 10000:
        raise ValueError("REPORT_P_LEDGER_ROWS_INVALID")
    ids = []
    for record in records:
        if not isinstance(record, Mapping) or not isinstance(record.get("p_id"), str):
            raise ValueError("REPORT_P_LEDGER_ROW_INVALID")
        ids.append(record["p_id"])
    if len(set(ids)) != len(ids) or "P-CASH" in ids:
        raise ValueError("REPORT_P_LEDGER_DUPLICATE_ROW")
    cash = observation.get("cash_record_private")
    if (not isinstance(cash, Mapping) or cash.get("p_id") != "P-CASH"
            or cash.get("visibility") not in {"VERIFIED_VISIBLE", "UNCERTAIN", "NOT_VISIBLE"}):
        raise ValueError("REPORT_P_LEDGER_CASH_INVALID")
    qualifiers = observation.get("missing_or_qualified")
    if (not isinstance(qualifiers, list) or len(qualifiers) > 10000
            or any(not isinstance(q, str) or not q for q in qualifiers)):
        raise ValueError("REPORT_P_LEDGER_QUALIFIERS_INVALID")
    # Raw UI percentages are observational, NOT M3 amount-derived weights.
    # Reconcile each displayed figure before showing even a bounded aggregate.
    display = observation.get("displayed_weight_summary_private")
    displayed: list[Decimal] = []
    for rec in records:
        state = rec.get("displayed_weight_visibility", "NOT_VISIBLE")
        raw = rec.get("displayed_weight_pct_private")
        if (state not in {"VERIFIED_VISIBLE", "UNCERTAIN", "NOT_VISIBLE"}
                or (state == "VERIFIED_VISIBLE") != (raw is not None)):
            raise ValueError("REPORT_DISPLAYED_WEIGHT_VISIBILITY_INVALID")
        if raw is not None:
            if not isinstance(raw, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,2})\.[0-9]{2}", raw):
                raise ValueError("REPORT_DISPLAYED_WEIGHT_INVALID")
            try:
                value = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("REPORT_DISPLAYED_WEIGHT_INVALID") from exc
            if not value.is_finite() or not 0 <= value <= 100:
                raise ValueError("REPORT_DISPLAYED_WEIGHT_INVALID")
            displayed.append(value)
    if display is None:
        if displayed:
            raise ValueError("REPORT_DISPLAYED_WEIGHT_SUMMARY_MISSING")
    elif (not isinstance(display, Mapping)
          or set(display) != {"visible_count", "position_row_count",
                              "displayed_weight_sum_pct", "normalization",
                              "denominator_verification"}
          or display["normalization"] != "NONE_DISPLAYED_VALUES_UNCHANGED"
          or display["denominator_verification"] != "NOT_PERFORMED"
          or type(display["visible_count"]) is not int
          or display["visible_count"] != len(displayed)
          or type(display["position_row_count"]) is not int
          or display["position_row_count"] != len(records)
          or not displayed):
        raise ValueError("REPORT_DISPLAYED_WEIGHT_SUMMARY_INVALID")
    if display is not None:
        expected = (f"{sum(displayed, Decimal('0')):.2f}"
                    if len(displayed) == len(records) else None)
        if display["displayed_weight_sum_pct"] != expected:
            raise ValueError("REPORT_DISPLAYED_WEIGHT_SUM_INVALID")
    stage = observation.get("status")
    weights = observation.get("known_scope_weights_pct")
    if stage == "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA":
        if (not isinstance(weights, Mapping)
                or set(weights) != set(ids) | {"P-CASH"}
                or qualifiers):
            raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
        try:
            values = [Decimal(v) for v in weights.values() if isinstance(v, str)]
        except InvalidOperation as exc:
            raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID") from exc
        if (len(values) != len(weights) or any(
                not v.is_finite() or v < 0 or v > 100 or v.as_tuple().exponent < -2
                for v in values) or sum(values) != Decimal("100.00")):
            raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
        # Compare with the original private M3 amounts, not only a 100% sum.
        # This duplicates the bounded largest-remainder parity check, never
        # recalculates a new portfolio allocation or source authority.
        amounts = {}
        try:
            for record in records:
                raw = record.get("market_value_base")
                if not isinstance(raw, str):
                    raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
                amounts[record["p_id"]] = Decimal(raw)
            cash_raw = cash.get("amount_base")
            if not isinstance(cash_raw, str):
                raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
            amounts["P-CASH"] = Decimal(cash_raw)
            if any(not v.is_finite() or v < 0 or v.as_tuple().exponent < -2
                   for v in amounts.values()):
                raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
            total = sum(amounts.values())
            if total <= 0:
                raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
            ideals = {key: v * Decimal("10000") / total for key, v in amounts.items()}
            units = {key: int(v.to_integral_value(rounding=ROUND_DOWN)) for key, v in ideals.items()}
            remaining = 10000 - sum(units.values())
            for key in sorted(units, key=lambda k: (-(ideals[k] - units[k]), k))[:remaining]:
                units[key] += 1
            expected = {key: f"{Decimal(units[key]) / Decimal('100'):.2f}"
                        for key in units}
        except (InvalidOperation, OverflowError) as exc:
            raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID") from exc
        if dict(weights) != expected:
            raise ValueError("REPORT_P_LEDGER_SCOPED_WEIGHTS_INVALID")
        coverage = "CALLER_REPORTED_SCOPED_DENOMINATOR_ONLY"
    elif stage == "OBSERVATION_LEDGER_ONLY":
        if weights is not None:
            raise ValueError("REPORT_P_LEDGER_INCOMPLETE_HAS_WEIGHTS")
        coverage = "INCOMPLETE_NO_DERIVED_WEIGHTS"
    else:
        raise ValueError("REPORT_P_LEDGER_STAGE_INVALID")
    lines = [
        "", "## Private portfolio observation — coverage and provenance",
        f"Observed as of {observed}; {len(records)} caller-reported position row(s). "
        f"Coverage: {coverage}.",
        f"Cash visibility: {cash['visibility']}; {len(qualifiers)} unresolved qualification(s) "
        "remain in the original private P ledger.",
    ]
    if display is not None:
        summed = display["displayed_weight_sum_pct"]
        lines.append(
            f"Work/screenshot-displayed allocations transcribed for "
            f"{display['visible_count']}/{len(records)} position rows; "
            + (f"raw displayed total {summed}%" if summed is not None
               else "complete displayed total UNKNOWN")
            + ". No rounding reconciliation or normalization was performed; "
              "displayed weights cannot establish a monetary/account denominator "
              "or otherwise authorize portfolio calculations."
        )
    lines.append(
        "The visible scope and any derived weights are NOT independently authenticated "
        "broker holdings, complete account exposure, Portfolio Room admission, "
        "investment guidance or trade authorization. No account IDs, holdings, "
        "cash values or individual position weights are reproduced here."
    )
    return lines


def _portfolio_exposure_lines(packet: Mapping[str, Any], analysis_id: str,
                              as_of: str) -> list[str]:
    """Summarize only M3 CURRENT scoped known/unknown/cash fractions.

    Existing private M3 classification and its historical fund scenarios stay
    in the annex. No issuer, security, account, raw amount or source reference
    is reproduced in the concise CC report.
    """
    exposures = packet.get("portfolio_exposures_private")
    if exposures is None:
        return []
    if not isinstance(exposures, Mapping):
        raise ValueError("REPORT_EXPOSURE_INVALID")
    if exposures.get("status") == "UNAVAILABLE_INCOMPLETE_P_LEDGER":
        if (exposures.get("economic_issuer_pct_private") is not None
                or exposures.get("source_authentication") != "NOT_PERFORMED"
                or exposures.get("portfolio_room_status") != "ROOM_UNAVAILABLE"):
            raise ValueError("REPORT_EXPOSURE_UNAVAILABLE_AUTHORITY_MISMATCH")
        return ["", "## Scoped portfolio exposures — unavailable",
                "Complete and reconcile the private dated portfolio ledger before "
                "using any sector, region or economic issuer percentages."]
    if (exposures.get("status") not in {
            "CALLER_REPORTED_SCOPED_EXPOSURES",
            "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS"}
            or exposures.get("analysis_id") != analysis_id
            or exposures.get("source_authentication") !=
                "CALLER_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
            or exposures.get("coverage_scope") !=
                "EXPLICIT_LEDGER_SCOPE_ONLY_NOT_HOUSEHOLD_TOTAL"
            or exposures.get("portfolio_room_status") != "ROOM_UNAVAILABLE"
            or exposures.get("trading_authority") != "NONE"
            or exposures.get("writes") != "NONE"):
        raise ValueError("REPORT_EXPOSURE_AUTHORITY_OR_ID_MISMATCH")
    observed = _iso_date(exposures.get("observation_as_of"), "exposures.observed_on")
    observation = packet.get("portfolio_observation_private")
    if (observed > as_of or not isinstance(observation, Mapping)
            or observation.get("analysis_id") != analysis_id
            or observation.get("observed_on") != observed
            or observation.get("status") != "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"
            or observation.get("private_scope") is not True):
        raise ValueError("REPORT_EXPOSURE_OBSERVATION_MISMATCH")

    def read_pct(name: str) -> Decimal:
        raw = exposures.get(name)
        if not isinstance(raw, str) or not 1 <= len(raw) <= 7:
            raise ValueError("REPORT_EXPOSURE_PERCENT_INVALID")
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError("REPORT_EXPOSURE_PERCENT_INVALID") from exc
        if (not value.is_finite() or not 0 <= value <= 100
                or value != value.quantize(Decimal("0.01"))):
            raise ValueError("REPORT_EXPOSURE_PERCENT_INVALID")
        return value

    known, unknown, cash = (read_pct(key) for key in (
        "known_exposure_pct", "unclassified_or_unknown_fund_pct", "cash_pct"))
    # M3 rounds each component to 0.01 percentage points. Accounting for
    # the independent rounding, their scoped total must still equal 100.
    if abs(known + unknown + cash - Decimal("100")) > Decimal("0.02"):
        raise ValueError("REPORT_EXPOSURE_SCOPE_SUM_MISMATCH")
    if ((unknown > 0 and exposures["status"] != "PARTIAL_KNOWN_EXPOSURE_LOWER_BOUNDS")
            or (unknown == 0 and exposures["status"] != "CALLER_REPORTED_SCOPED_EXPOSURES")):
        raise ValueError("REPORT_EXPOSURE_COVERAGE_STATUS_MISMATCH")
    historical = exposures.get("fund_composition_date_alignment")
    if historical not in {
        "NO_PRIOR_DATED_FUND_SNAPSHOTS_REPORTED",
        "PRIOR_DATED_FUND_SNAPSHOTS",
    }:
        raise ValueError("REPORT_EXPOSURE_FUND_DATE_STATUS_INVALID")
    if historical == "PRIOR_DATED_FUND_SNAPSHOTS":
        if (unknown == 0
                or exposures.get("economic_issuer_rank_coverage_reported_complete") is not False
                or not isinstance(exposures.get("historical_fund_scenario_private"), Mapping)
                or not isinstance(exposures.get("historical_fund_p_ids_private"), list)
                or not exposures["historical_fund_p_ids_private"]):
            raise ValueError("REPORT_EXPOSURE_HISTORICAL_AUTHORITY_MISMATCH")
    elif exposures.get("historical_fund_scenario_private") is not None:
        raise ValueError("REPORT_EXPOSURE_FUND_DATE_STATUS_INVALID")
    lines = ["", "## Scoped portfolio exposures — caller-reported, not certified",
             f"Observed {observed}: {known:.2f}% known classified exposure, "
             f"{unknown:.2f}% unknown/unclassified and {cash:.2f}% cash "
             "of the explicitly observed private scope (not all household accounts)."]
    if historical == "PRIOR_DATED_FUND_SNAPSHOTS":
        lines.append(
            "Older ETF/fund constituents are excluded from CURRENT known exposures; "
            "their entire reported fund value is in the unknown share. "
            "Any historical scenario is PRIVATE and illustrative, not current look-through.")
    if unknown > 0:
        lines.append(
            "Issuer, sector and region overlap may be larger than the reported known portion; "
            "verify original fund constituents, dates, rights, cash and account coverage.")
    lines.append(
        "No underlying holdings, individual weights, issuer IDs, broker values or source "
        "links are reproduced. This is not verified Portfolio Room, advice or a trade.")
    return lines


def _new_contribution_lines(packet: Mapping[str, Any], analysis_id: str,
                            as_of: str) -> list[str]:
    """Show only supplied NEW-capital percentages, never private positions.

    The gross/funded statuses are computed by the existing M3 helpers. This
    renderer cannot independently validate brokerage economics or holdings.
    """
    summary = packet.get("new_contribution_summary_private")
    if summary is None:
        return []
    if not isinstance(summary, Mapping) or (
        summary.get("analysis_id") != analysis_id
        or summary.get("source_authentication") != "NOT_PERFORMED"
    ):
        raise ValueError("CONTRIBUTION_REPORT_ID_OR_AUTHORITY_MISMATCH")
    observed_at = _iso_date(summary.get("portfolio_as_of"), "portfolio_as_of")
    if observed_at > as_of:
        raise ValueError("CONTRIBUTION_REPORT_OBSERVATION_AFTER_CUTOFF")
    gross = summary.get("gross_status")
    costs = summary.get("cost_status")
    funded = summary.get("funded_status")
    if gross not in {"GROSS_PROJECTION_ONLY", "UNAVAILABLE"} or not isinstance(costs, str) or not isinstance(funded, str):
        raise ValueError("CONTRIBUTION_REPORT_INVALID_STATUS")
    lines = ["", "## New contributions — private, caller-supplied plan"]
    if gross != "GROSS_PROJECTION_ONLY":
        if summary.get("allocations_pct") is not None:
            raise ValueError("CONTRIBUTION_REPORT_UNSUPPORTED_PERCENTAGES")
        lines.append("Gross contribution projection UNAVAILABLE: portfolio scope, cash, currency or identity inputs are not established.")
    else:
        allocations = summary.get("allocations_pct")
        if not isinstance(allocations, Mapping) or not allocations:
            raise ValueError("CONTRIBUTION_REPORT_ALLOCATIONS_REQUIRED")
        exact = {}
        for instrument, raw in allocations.items():
            if (not isinstance(instrument, str) or not instrument.strip()
                    or len(instrument) > 80 or any(ord(c) < 32 for c in instrument)
                    or not isinstance(raw, str)):
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            try:
                pct = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION") from exc
            if not pct.is_finite() or pct < 0 or pct > 100:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            exact[instrument] = pct
        if sum(exact.values()) != 100:
            raise ValueError("CONTRIBUTION_REPORT_PERCENTAGES_NOT_100")
        lines.append("Percentages of **NEW contribution only** (user/analyst supplied, gross of costs; not portfolio target weights):")
        ordered = sorted(exact, key=lambda key: (-exact[key], key))
        for instrument in ordered[:8]:
            safe = instrument.replace("\\", "\\\\").replace("`", "\\`").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"- `{safe}`: {format(exact[instrument], 'g')}% of new capital")
        if len(ordered) > 8:
            lines.append(f"- {len(ordered) - 8} other destinations in private M3 annex.")
    sensitivity = summary.get("largest_security_line_sensitivity_private")
    if sensitivity is not None:
        if (gross != "GROSS_PROJECTION_ONLY" or not isinstance(sensitivity, Mapping)
                or set(sensitivity) != {
                    "status", "before_largest_non_cash_security_pct",
                    "gross_after_largest_non_cash_security_pct",
                    "conditional_funded_after_largest_non_cash_security_pct",
                    "before_scoped_cash_pct", "gross_after_scoped_cash_pct",
                    "conditional_funded_after_scoped_cash_pct",
                    "authority"}
                or sensitivity.get("authority") !=
                    "DESCRIPTIVE_CALLER_SUPPLIED_NO_PORTFOLIO_POLICY_OR_EXECUTION"):
            raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_AUTHORITY_INVALID")
        is_funded = funded == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
        if sensitivity["status"] != (
                "GROSS_AND_CONDITIONAL_FUNDED_SCOPED_SENSITIVITY"
                if is_funded else "GROSS_ONLY_SCOPED_SENSITIVITY"):
            raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_STATUS_MISMATCH")

        def concentration_pct(key: str) -> str | None:
            raw = sensitivity[key]
            if raw is None:
                return None
            if not isinstance(raw, str) or len(raw) > 6:
                raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_PERCENT_INVALID")
            try:
                amount = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_PERCENT_INVALID") from exc
            if (not amount.is_finite() or amount < 0 or amount > 100
                    or amount != amount.quantize(Decimal("0.01"))):
                raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_PERCENT_INVALID")
            return f"{amount:.2f}"

        before = concentration_pct("before_largest_non_cash_security_pct")
        gross_after = concentration_pct("gross_after_largest_non_cash_security_pct")
        funded_after = concentration_pct("conditional_funded_after_largest_non_cash_security_pct")
        before_cash = concentration_pct("before_scoped_cash_pct")
        gross_cash = concentration_pct("gross_after_scoped_cash_pct")
        funded_cash = concentration_pct("conditional_funded_after_scoped_cash_pct")
        if before_cash is None or gross_cash is None:
            raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_CASH_REQUIRED")
        if not is_funded and funded_cash is not None:
            raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_FUNDED_UNAUTHORIZED")
        if not is_funded and funded_after is not None:
            raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_FUNDED_UNAUTHORIZED")
        if before is not None or gross_after is not None:
            lines.append(
                "Largest single non-cash security line, percent of the SAME scoped "
                "portfolio including cash: before "
                f"{before + '%' if before is not None else 'UNAVAILABLE'}; "
                "after the caller-supplied GROSS new-capital scenario "
                f"{gross_after + '%' if gross_after is not None else 'UNAVAILABLE'}. "
                "These maxima may refer to different securities; not economic-issuer "
                "look-through, a concentration limit, a recommendation or executed holdings."
            )
            if is_funded:
                lines.append(
                    "Under the separately conditional fixed-supplied-cost funded "
                    "scenario: largest non-cash security line "
                    f"{funded_after + '%' if funded_after is not None else 'UNAVAILABLE'}. "
                    "Fixed fees require a real broker requote; no net investment "
                    "outcome or trade is certified."
                )
        else:
            lines.append(
                "Single-security concentration UNAVAILABLE: no positive non-cash "
                "security line in the supplied scoped scenario.")
        lines.append(
            "Cash within the SAME caller-confirmed portfolio scope: before "
            f"{before_cash}% and after the GROSS hypothetical contribution "
            f"{gross_cash}% (P-CASH, not a strategy reserve target). "
            "These are descriptive scoped percentages, not externally "
            "available emergency funds or authorization to rebalance.")
        if is_funded:
            if funded_cash is None:
                raise ValueError("CONTRIBUTION_REPORT_CONCENTRATION_CASH_REQUIRED")
            lines.append(
                "Under the separate conditional fixed-supplied-cost funded "
                f"scenario: scoped cash {funded_cash}%; cost quotes, external "
                "funding, accessible cash and net execution remain unverified.")

    # Optional one-to-three GROSS-only alternatives from the same M3
    # projection engine. Show only scoped percentages, never private balances,
    # trade destinations or cost quotes. Refuse forged net/authority labels.
    alternatives = summary.get("gross_alternatives_private")
    if alternatives is not None:
        if (gross != "GROSS_PROJECTION_ONLY"
                or not isinstance(alternatives, Mapping)
                or set(alternatives) != {"status", "scenarios", "authority"}
                or alternatives["status"] != "GROSS_ALTERNATIVES_ONLY_NOT_NET"
                or alternatives["authority"] !=
                    "CALLER_SUPPLIED_HYPOTHETICAL_NOT_PORTFOLIO_POLICY"):
            raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_AUTHORITY_INVALID")
        scenarios = alternatives["scenarios"]
        if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 3:
            raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_COUNT_INVALID")
        validated = []
        for index, variant in enumerate(scenarios, start=1):
            if (not isinstance(variant, Mapping)
                    or set(variant) != {
                        "scenario_index", "gross_after_largest_non_cash_security_pct",
                        "gross_after_scoped_cash_pct"}
                    or type(variant["scenario_index"]) is not int
                    or variant["scenario_index"] != index):
                raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_SCHEMA_INVALID")
            percents = []
            for key in ("gross_after_largest_non_cash_security_pct",
                        "gross_after_scoped_cash_pct"):
                raw = variant[key]
                if raw is None and key == "gross_after_largest_non_cash_security_pct":
                    percents.append("UNAVAILABLE")
                    continue
                if not isinstance(raw, str) or len(raw) > 6:
                    raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_PERCENT_INVALID")
                try:
                    pct = Decimal(raw)
                except InvalidOperation as exc:
                    raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_PERCENT_INVALID") from exc
                if (not pct.is_finite() or pct < 0 or pct > 100
                        or pct != pct.quantize(Decimal("0.01"))):
                    raise ValueError("CONTRIBUTION_REPORT_ALTERNATIVES_PERCENT_INVALID")
                percents.append(f"{pct:.2f}%")
            validated.append((index, *percents))
        lines.append(
            "Other caller-supplied alternatives, GROSS only, using the same "
            "dated scoped portfolio and contribution amount; separately "
            "numbered in the private M3 input:"
        )
        for index, largest, cash in validated:
            lines.append(
                f"- Alternative {index}: largest non-cash security line "
                f"{largest}; scoped cash {cash}."
            )
        lines.append(
            "Do not compare these gross alternatives as net investment outcomes: "
            "baseline cost quotes/funding do not apply to them. No preferred "
            "allocation, issuer look-through, reserve target or trade is implied."
        )

    burden_text = summary.get("one_time_supplied_cost_share_pct")
    if burden_text is not None:
        if (costs != "SUPPLIED_COST_TALLY_ONLY"
                or funded != "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
                or gross != "GROSS_PROJECTION_ONLY"
                or not isinstance(burden_text, str)):
            raise ValueError("CONTRIBUTION_REPORT_COST_BURDEN_INCONSISTENT")
        try:
            burden = Decimal(burden_text)
        except InvalidOperation as exc:
            raise ValueError("CONTRIBUTION_REPORT_COST_BURDEN_INVALID") from exc
        if (not burden.is_finite() or not 0 <= burden < 100
                or burden != burden.quantize(Decimal("0.0001"))
                or len(burden_text) > 10):
            raise ValueError("CONTRIBUTION_REPORT_COST_BURDEN_INVALID")
    if costs == "NOT_SUPPLIED" and funded == "NOT_ASSESSED":
        lines.append("Costs/funding NOT ASSESSED: gross plan only; no executable allocation.")
    elif (costs == "SUPPLIED_COST_TALLY_ONLY"
          and funded == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
          and gross == "GROSS_PROJECTION_ONLY"):
        lines.append("Cost-funded budget CONDITIONALLY RECONCILED using caller-supplied fixed fees; percentages are unchanged, but net amounts and funding differ. Requote size-dependent costs and verify account taxes/FX before any decision.")
        if burden_text is not None:
            lines.append(
                f"Supplied one-time purchase costs: {burden:.4f}% of total NEW cash "
                "committed (including separately funded fees where applicable). "
                "Descriptive only: not annualized, net Expected Return, a broker "
                "quote or trading authorization."
            )
    elif (costs in {"NOT_SUPPLIED", "INCOMPLETE_COST_INPUTS", "UNAVAILABLE_GROSS_PROJECTION",
                     "UNAVAILABLE_COSTS_EXCEED_CONTRIBUTION", "SUPPLIED_COST_TALLY_ONLY"}
          and (funded == "NOT_ASSESSED" or funded.startswith("UNAVAILABLE_"))):
        lines.append("After-cost funded allocation UNAVAILABLE: charges, funding or scope are incomplete or inconsistent. Do not treat the gross percentages as an executable plan.")
    else:
        raise ValueError("CONTRIBUTION_REPORT_COST_FUNDING_STATUS_MISMATCH")
    lines.append("PI observations and allocations are caller-supplied; no holdings authentication, source certification, price, trade or investment recommendation.")
    return lines


def _valuation_lines(packet: Mapping[str, Any], analysis_id: str,
                     as_of: str) -> list[str]:
    """Show the existing M2 scenario measures without inventing Expected Return."""
    result = packet.get("valuation_scenarios_private")
    if result is None:
        return []
    if not isinstance(result, Mapping) or (
        result.get("analysis_id") != analysis_id
        or result.get("analysis_as_of") != as_of
        or result.get("source_authentication") != "NOT_PERFORMED"
        or result.get("trade_or_portfolio_authority") != "NONE"
        or result.get("expected_return_status") != "NOT_ESTABLISHED_NO_PROBABILITIES_OR_ASSUMPTION_CERTIFICATION"
        or result.get("benchmark_expected_return_status") != "VFV_ER_UNAVAILABLE_UNLESS_SEPARATELY_EVIDENCED"
        or result.get("calculation_scope") != "CURRENT_SUPPLIED_INPUTS_ONLY_NO_PIT"
    ):
        raise ValueError("VALUATION_REPORT_ID_OR_AUTHORITY_MISMATCH")
    status = result.get("status")
    if status not in {"CONDITIONAL_SCENARIO_ARITHMETIC_ONLY", "UNAVAILABLE_INCOMPATIBLE_BASIS"}:
        raise ValueError("VALUATION_REPORT_STATUS_INVALID")
    _iso_date(result.get("quoted_at"), "valuation.quoted_at")
    if result["quoted_at"] > as_of:
        raise ValueError("VALUATION_REPORT_FUTURE_QUOTE")
    currency, horizon = result.get("currency"), result.get("horizon_years")
    if (not isinstance(currency, str) or len(currency) != 3 or not currency.isascii()
            or not currency.isalpha() or currency != currency.upper()
            or type(horizon) is not int or not 1 <= horizon <= 30):
        raise ValueError("VALUATION_REPORT_BASIS_INVALID")
    scenarios = result.get("scenarios_private")
    if not isinstance(scenarios, Mapping) or set(scenarios) != {"BEAR", "BASE", "BULL"}:
        raise ValueError("VALUATION_REPORT_SCENARIO_SET_INVALID")
    lines = ["", "## Valuation scenarios — conditional, private",
             f"Caller-supplied {horizon}-year scenario arithmetic in {currency}; issuer value assumptions and quotation remain unverified."]
    quote = packet.get("valuation_quote_trace_private")
    if quote is not None:
        if (not isinstance(quote, Mapping)
                or quote.get("status") != "PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED"
                or quote.get("analysis_id") != analysis_id
                or quote.get("analysis_as_of") != as_of
                or quote.get("source_authentication") != "NOT_PERFORMED"
                or quote.get("original_market_price_verification") != "NOT_ESTABLISHED"
                or quote.get("market_price_or_fx_authority") != "NONE"
                or quote.get("writes") != "NONE"
                or quote.get("quote_reference_private") != result.get("quote_source_ref")):
            raise ValueError("VALUATION_QUOTE_TRACE_AUTHORITY_OR_ID_MISMATCH")
        stage = quote.get("review_stage")
        reasons = quote.get("reason_codes")
        matched = quote.get("matched_observation_id_private")
        if (stage not in {"EVIDENCE_RESOLUTION", "HUMAN_QUOTE_REVIEW_ONLY"}
                or not isinstance(reasons, list)
                or len(reasons) > 24
                or any(not isinstance(code, str) or not code or len(code) > 100
                       or any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in code)
                       for code in reasons)
                or (stage == "HUMAN_QUOTE_REVIEW_ONLY") != (matched is not None and not reasons)
                or (matched is not None and matched != result.get("quote_source_ref"))):
            raise ValueError("VALUATION_QUOTE_TRACE_STAGE_INVALID")
        lines.append(
            "**Quotation provenance:** " +
            ("one caller-supplied observation structurally aligned; human authentication still required."
             if stage == "HUMAN_QUOTE_REVIEW_ONLY"
             else "evidence resolution required; scenario arithmetic is not a checked market-price return.") +
            " No live quote or original-source verification was performed.")

    for name in ("BEAR", "BASE", "BULL"):
        row = scenarios[name]
        if not isinstance(row, Mapping) or row.get("assumption_validation") != "NOT_PERFORMED":
            raise ValueError("VALUATION_REPORT_ASSUMPTIONS_NOT_CERTIFIED")
        measure, value = row.get("return_measure"), row.get("scenario_return_pct_annual")
        if measure not in {"PRICE_ONLY_CAGR_NOT_TOTAL_RETURN",
                           "YEAR_END_CASHFLOW_IRR_CONDITIONAL", "UNAVAILABLE"}:
            raise ValueError("VALUATION_REPORT_MEASURE_INVALID")
        if status == "UNAVAILABLE_INCOMPATIBLE_BASIS":
            if measure != "UNAVAILABLE" or value is not None:
                raise ValueError("VALUATION_REPORT_INVALID_UNAVAILABLE")
        elif measure == "UNAVAILABLE":
            raise ValueError("VALUATION_REPORT_INVALID_AVAILABLE")
        reasons = row.get("reason_codes")
        if not isinstance(reasons, list) or any(
            not isinstance(v, str) or not v or len(v) > 100 or
            any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in v)
            for v in reasons
        ):
            raise ValueError("VALUATION_REPORT_REASON_CODES_INVALID")
        if measure == "UNAVAILABLE":
            if not any(v in reasons for v in (
                "SECURITY_SHARE_CLASS_OR_CORPORATE_ACTION_BASIS_UNCONFIRMED",
                "CURRENCY_OR_FX_BASIS_UNCONFIRMED",
            )):
                raise ValueError("VALUATION_REPORT_UNAVAILABLE_REASON_MISSING")
            lines.append(f"- **{name}: UNAVAILABLE** — security/share-class or currency basis unconfirmed.")
            continue
        if measure == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN":
            if (row.get("annual_distributions_status") != "UNKNOWN"
                    or "DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY" not in reasons):
                raise ValueError("VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH")
        else:
            if (row.get("annual_distributions_status") != "EXPLICITLY_SUPPLIED"
                    or "DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY" in reasons):
                raise ValueError("VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH")
        if not isinstance(value, str) or len(value) > 40:
            raise ValueError("VALUATION_REPORT_RETURN_INVALID")
        try:
            annual = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("VALUATION_REPORT_RETURN_INVALID") from exc
        if not annual.is_finite() or annual < -100 or annual > Decimal("1000000000"):
            raise ValueError("VALUATION_REPORT_RETURN_INVALID")
        formatted = format(annual, "f")
        if measure == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN":
            label = "price-only CAGR; distributions UNKNOWN, not total return"
        else:
            label = "conditional year-end cash-flow IRR on explicitly supplied distributions"
        lines.append(f"- **{name}: {formatted}% annualized** — {label}.")
    lines.append("These are alternative scenario calculations, not probabilities, not probability-weighted Expected Return, not FX-adjusted account performance and not forecast alpha versus VFV. No investment or trade authority.")
    return lines



def _weighted_cashflow_lines(packet: Mapping[str, Any], analysis_id: str,
                             as_of: str) -> list[str]:
    """Expose bounded analyst probability sensitivity, never an ER verdict."""
    result = packet.get("weighted_cashflow_model_private")
    if result is None:
        return []
    valuation = packet.get("valuation_scenarios_private")
    quote = packet.get("valuation_quote_trace_private")
    if not isinstance(result, Mapping) or not isinstance(valuation, Mapping) or not isinstance(quote, Mapping):
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_DEPENDENCIES_REQUIRED")
    if (result.get("status") not in {
                "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED",
                "UNAVAILABLE_NEEDS_EVIDENCE_OR_COMPATIBLE_ASSUMPTIONS"}
            or result.get("analysis_id") != analysis_id
            or result.get("analysis_as_of") != as_of
            or result.get("security_id_private") != valuation.get("security_id")
            or result.get("currency") != valuation.get("currency")
            or result.get("horizon_years") != valuation.get("horizon_years")
            or result.get("probability_calibration") != "NOT_PERFORMED"
            or result.get("price_authentication") != "NOT_PERFORMED"
            or result.get("model_expected_return_authority") != "NOT_CERTIFIED"
            or result.get("vfv_alpha") != "NOT_ESTABLISHED"
            or result.get("account_costs_fx_tax") != "NOT_EVALUATED"
            or result.get("trading_authority") != "NONE"
            or result.get("storage") != "NONE"
            or result.get("probability_basis") not in {"PAM_ASSUMPTION", "THIRD_PARTY_ESTIMATE"}):
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_AUTHORITY_OR_ID_MISMATCH")
    _string(result.get("probability_rationale_ref_private"), "probability_rationale_ref_private")
    raw = result.get("probabilities_pct_private")
    if not isinstance(raw, Mapping) or set(raw) != {"BEAR", "BASE", "BULL"}:
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_WEIGHTS_INVALID")
    weights = []
    for name in ("BEAR", "BASE", "BULL"):
        val = raw[name]
        if not isinstance(val, str) or len(val) > 32:
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_WEIGHTS_INVALID")
        try:
            weight = Decimal(val)
        except InvalidOperation as exc:
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_WEIGHTS_INVALID") from exc
        if not weight.is_finite() or weight < 0 or weight > 100:
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_WEIGHTS_INVALID")
        weights.append(weight)
    if sum(weights) != 100:
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_WEIGHTS_INVALID")
    measure, number = result.get("measure"), result.get("conditional_annualized_pct")
    reasons = result.get("reason_codes")
    if (not isinstance(reasons, list) or len(reasons) > 12 or
            any(not isinstance(x, str) or not x or len(x) > 100 or
                any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for ch in x) for x in reasons)):
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_REASON_CODES_INVALID")
    options = {"WEIGHTED_TERMINAL_PRICE_ONLY_CAGR_DISTRIBUTIONS_UNKNOWN",
               "IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR"}
    if measure == "UNAVAILABLE":
        if (result["status"] != "UNAVAILABLE_NEEDS_EVIDENCE_OR_COMPATIBLE_ASSUMPTIONS"
                or number is not None or not reasons):
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_UNAVAILABLE_INCONSISTENT")
        line = "**Conditional weighted cash-flow sensitivity: UNAVAILABLE** — source/basis or distribution assumptions need review."
    elif measure in options:
        if (result["status"] != "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED"
                or reasons or quote.get("review_stage") != "HUMAN_QUOTE_REVIEW_ONLY"
                or valuation.get("status") != "CONDITIONAL_SCENARIO_ARITHMETIC_ONLY"
                or not isinstance(number, str) or len(number) > 40):
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_AVAILABLE_INCONSISTENT")
        try:
            annual = Decimal(number)
        except InvalidOperation as exc:
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_RETURN_INVALID") from exc
        if not annual.is_finite() or annual < -100 or annual > Decimal("1000000000"):
            raise ValueError("WEIGHTED_CASHFLOW_REPORT_RETURN_INVALID")
        label = ("price-only annualized weighted terminal outcome; distributions UNKNOWN"
                 if measure == "WEIGHTED_TERMINAL_PRICE_ONLY_CAGR_DISTRIBUTIONS_UNKNOWN"
                 else "IRR of weighted year-end cash flows; not the mean of scenario IRRs")
        line = f"**Conditional weighted cash-flow sensitivity: {format(annual, 'f')}% annualized** — {label}."
    else:
        raise ValueError("WEIGHTED_CASHFLOW_REPORT_MEASURE_INVALID")
    weighting = ", ".join(
        f"{name} {format(weight, 'f')}%"
        for name, weight in zip(("BEAR", "BASE", "BULL"), weights)
    )
    return [
        "", "### Analyst-supplied probability sensitivity — NOT certified Expected Return",
        f"Assumed weights: {weighting}; basis: {result['probability_basis']} (not independently calibrated).",
        line,
        "Scenario probabilities, terminal assumptions, prices and cash-flow timings require human source and method review. No expected alpha, benchmark forecast, FX/fees/tax-adjusted account return, capital-allocation ranking or trade authorization."
    ]


def _fundamental_lines(packet: Mapping[str, Any], analysis_id: str,
                       as_of: str) -> list[str]:
    """Display M2 descriptive issuer economics, not verified Quality or ER."""
    dossier = packet.get("fundamental_dossier_private")
    if dossier is None:
        return []
    if not isinstance(dossier, Mapping) or (
        dossier.get("status") != "INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED"
        or dossier.get("analysis_id") != analysis_id
        or dossier.get("analysis_as_of") != as_of
        or dossier.get("evidence_authority") != "CALLER_REPORTED_ONLY_NOT_ORIGINAL_AUTHENTICATED"
        or dossier.get("normalized_owner_earnings_status") != "NOT_ESTABLISHED"
        or dossier.get("quality_or_durability_verdict") != "NOT_AUTOMATICALLY_ESTABLISHED"
        or dossier.get("expected_return_or_trade") != "NOT_ESTABLISHED"
        or dossier.get("organic_growth_status") != "UNKNOWN_ACQUISITIONS_AND_MIX_NOT_EVALUATED"
        or dossier.get("writes") != "NONE"
    ):
        raise ValueError("FUNDAMENTAL_REPORT_ID_OR_AUTHORITY_MISMATCH")

    pairs = dossier.get("metric_pairs_private")
    metrics = dossier.get("descriptive_metrics_private")
    axes = dossier.get("qualitative_axes_private")
    limits = dossier.get("limitations")
    if not isinstance(pairs, Mapping) or not isinstance(metrics, Mapping) or not isinstance(limits, list):
        raise ValueError("FUNDAMENTAL_REPORT_INVALID_STRUCTURE")
    allowed_metrics = {"reported_revenue_change_pct", "reported_operating_margin_pct",
                       "cfo_less_cash_capex_descriptive", "cfo_less_capex_label",
                       "diluted_share_count_change_pct"}
    if set(metrics) - allowed_metrics:
        raise ValueError("FUNDAMENTAL_REPORT_UNKNOWN_METRIC")
    if not isinstance(axes, Mapping) or set(axes) != {
        "COMPETITIVE_POSITION", "REINVESTMENT", "PERMANENT_LOSS"
    }:
        raise ValueError("FUNDAMENTAL_REPORT_QUALITATIVE_AXES_REQUIRED")
    for name, pair in pairs.items():
        if name not in {"REVENUE", "OPERATING_INCOME", "CFO", "CASH_CAPEX", "DILUTED_AVG_SHARES"}:
            raise ValueError("FUNDAMENTAL_REPORT_UNKNOWN_SOURCE_METRIC")
        if not isinstance(pair, Mapping) or pair.get("status") not in {
            "INDICATIVE_COMPARABLE", "UNAVAILABLE"
        }:
            raise ValueError("FUNDAMENTAL_REPORT_PAIR_STATUS_INVALID")
    def supported(*names: str) -> bool:
        return all(name in pairs and pairs[name].get("status") == "INDICATIVE_COMPARABLE"
                   for name in names)
    def decimal(value: Any) -> str:
        if not isinstance(value, str) or not 1 <= len(value) <= 50:
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID")
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID") from exc
        if not number.is_finite() or (number and number.copy_abs().adjusted() > 15):
            raise ValueError("FUNDAMENTAL_REPORT_NUMBER_INVALID")
        return format(number, "f")
    def two_numbers(key: str) -> tuple[str, str]:
        values = metrics[key]
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("FUNDAMENTAL_REPORT_PERIOD_VALUES_INVALID")
        return decimal(values[0]), decimal(values[1])

    lines = ["", "## Fundamental economics — indicative, private",
             "Caller-reported issuer observations only; comparability checks are structural, not original-source authentication."]
    if "reported_revenue_change_pct" in metrics:
        if not supported("REVENUE"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        lines.append("- Reported revenue change (two supplied annual periods): " +
                     decimal(metrics["reported_revenue_change_pct"]) + "%; not confirmed organic growth.")
    else:
        lines.append("- Reported revenue growth: UNAVAILABLE or noncomparable.")
    if "reported_operating_margin_pct" in metrics:
        if not supported("REVENUE", "OPERATING_INCOME"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        before, after = two_numbers("reported_operating_margin_pct")
        lines.append(f"- Reported operating margin, prior → later period: {before}% → {after}%.")
    else:
        lines.append("- Reported operating margin: UNAVAILABLE or noncomparable.")
    if "cfo_less_cash_capex_descriptive" in metrics:
        if not supported("CFO", "CASH_CAPEX") or metrics.get("cfo_less_capex_label") != "NOT_NORMALIZED_OWNER_EARNINGS":
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_CASHFLOW")
        left, right = pairs["CFO"], pairs["CASH_CAPEX"]
        if any(left.get(k) != right.get(k) for k in ("period_ends", "currency", "unit")):
            raise ValueError("FUNDAMENTAL_REPORT_CASHFLOW_BASIS_MISMATCH")
        curr, unit = left.get("currency"), left.get("unit")
        if any(not isinstance(v, str) or not 1 <= len(v) <= 20 or
               any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_/" for c in v)
               for v in (curr, unit)):
            raise ValueError("FUNDAMENTAL_REPORT_CASHFLOW_UNIT_INVALID")
        before, after = two_numbers("cfo_less_cash_capex_descriptive")
        lines.append(f"- CFO less cash capex (prior → later): {before} → {after} {unit} ({curr}); "
                     "**not normalized owner earnings**.")
    elif "cfo_less_capex_label" in metrics:
        raise ValueError("FUNDAMENTAL_REPORT_ORPHAN_CASHFLOW_LABEL")
    else:
        lines.append("- CFO less cash capex: UNAVAILABLE or noncomparable.")
    if "diluted_share_count_change_pct" in metrics:
        if not supported("DILUTED_AVG_SHARES"):
            raise ValueError("FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION")
        lines.append("- Diluted average-share count change: " +
                     decimal(metrics["diluted_share_count_change_pct"]) + "% (not a share-price return).")
    else:
        lines.append("- Diluted share count change: UNAVAILABLE.")
    for axis in ("COMPETITIVE_POSITION", "REINVESTMENT", "PERMANENT_LOSS"):
        row = axes[axis]
        if not isinstance(row, Mapping) or row.get("status") not in {"SPECIALIST_REPORTED", "UNKNOWN"}:
            raise ValueError("FUNDAMENTAL_REPORT_INVALID_QUALITATIVE_STATUS")
        ids = row.get("ir_fact_ids")
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x for x in ids):
            raise ValueError("FUNDAMENTAL_REPORT_INVALID_QUALITATIVE_LINKS")
        evidence = "linked IR facts" if ids else "no linked IR facts"
        lines.append(f"- {axis.replace('_', ' ').title()}: {row['status']} ({evidence}); no independent verdict.")
    if any(not isinstance(s, str) or not s or len(s) > 140
           or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:_" for c in s)
           for s in limits):
        raise ValueError("FUNDAMENTAL_REPORT_LIMITATIONS_INVALID")
    if limits:
        lines.append(f"- {len(limits)} comparability/evidence limitation(s) remain; see private dossier.")
    lines.append("Quality, durability, organic growth, normalized owner earnings and Expected Return remain NOT ESTABLISHED. No investment ranking, source certification or trade authority.")
    return lines


def _portfolio_room_lines(packet: Mapping[str, Any], analysis_id: str,
                          as_of: str) -> list[str]:
    """Display M3 Portfolio Room qualifications, not an allocation decision."""
    room = packet.get("portfolio_room_review_private")
    if room is None:
        return []
    if not isinstance(room, Mapping) or (
        room.get("analysis_id") != analysis_id
        or room.get("as_of") != as_of
        or room.get("portfolio_room_authority") != "QUALITATIVE_SPECIALIST_REPORTED_ONLY"
        or room.get("independent_evidence_check") != "NOT_PERFORMED"
        or room.get("contribution_or_sale_proposal") != "NONE_NOT_AUTOMATED"
        or room.get("trade_authority") != "NONE_CEO_ONLY"
        or room.get("public_memory_write") != "NONE"
    ):
        raise ValueError("ROOM_REPORT_AUTHORITY_OR_ID_MISMATCH")
    status = room.get("status")
    if status not in {"ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"}:
        raise ValueError("ROOM_REPORT_STATUS_INVALID")
    observed = _iso_date(room.get("observed_on"), "room.observed_on")
    if observed > as_of:
        raise ValueError("ROOM_REPORT_FUTURE_OBSERVATION")
    axes = room.get("research_axes_private")
    checks = room.get("portfolio_checks_private")
    research_names = ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
    check_names = ("CONCENTRATION", "CORRELATED_DRIVERS", "ALTERNATIVES", "ACCOUNT_COSTS")
    if not isinstance(axes, Mapping) or set(axes) != set(research_names):
        raise ValueError("ROOM_REPORT_RESEARCH_AXES_INVALID")
    if not isinstance(checks, Mapping) or set(checks) != set(check_names):
        raise ValueError("ROOM_REPORT_PORTFOLIO_CHECKS_INVALID")
    for name in research_names:
        row = axes[name]
        if not isinstance(row, Mapping) or row.get("status") not in {"SPECIALIST_REPORTED", "UNKNOWN"}:
            raise ValueError("ROOM_REPORT_RESEARCH_STATUS_INVALID")
        refs = row.get("ir_fact_ids")
        if not isinstance(refs, list) or any(not isinstance(x, str) or not x for x in refs):
            raise ValueError("ROOM_REPORT_RESEARCH_REFS_INVALID")
    for name in check_names:
        row = checks[name]
        if not isinstance(row, Mapping) or row.get("status") not in {"SPECIALIST_REPORTED", "UNKNOWN"}:
            raise ValueError("ROOM_REPORT_CHECK_STATUS_INVALID")
        ref = row.get("source_ref")
        if ref is not None and (not isinstance(ref, str) or not ref.strip()):
            raise ValueError("ROOM_REPORT_CHECK_REF_INVALID")
    warnings = room.get("missing_or_qualified")
    if not isinstance(warnings, list) or len(warnings) > 60 or any(
        not isinstance(code, str) or not 1 <= len(code) <= 100
        or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:" for c in code)
        for code in warnings
    ):
        raise ValueError("ROOM_REPORT_LIMITATIONS_INVALID")

    def percentage(raw: Any) -> str | None:
        if raw is None:
            return None
        if not isinstance(raw, str) or not 1 <= len(raw) <= 48:
            raise ValueError("ROOM_REPORT_PERCENT_INVALID")
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError("ROOM_REPORT_PERCENT_INVALID") from exc
        if not number.is_finite() or not 0 <= number <= 100:
            raise ValueError("ROOM_REPORT_PERCENT_INVALID")
        return format(number, "f")

    known = percentage(room.get("known_candidate_issuer_exposure_pct_private"))
    unknown = percentage(room.get("unclassified_lookthrough_pct_private"))
    lines = ["", "## Portfolio Room — caller-reported, not certified",
             f"**Portfolio Room:** {status}; portfolio observed {observed}. No independent verification of holdings or investment admission."]
    if known is None:
        lines.append("- Known supplied candidate-issuer exposure: UNKNOWN.")
    else:
        lines.append(f"- Known supplied candidate-issuer exposure: {known}% of the scoped portfolio (conditional lower bound, not complete look-through).")
    if unknown is None:
        lines.append("- Unclassified fund exposure: UNKNOWN.")
    else:
        lines.append(f"- Unclassified/unknown fund look-through: {unknown}% of scoped portfolio; may conceal additional correlated exposures.")
    for axis in research_names:
        row = axes[axis]
        label = "linked IR facts supplied" if row["ir_fact_ids"] else "no linked IR facts"
        lines.append(f"- {axis.replace('_', ' ').title()}: {row['status']} ({label}; not independently certified).")
    for check in check_names:
        row = checks[check]
        label = "source reference supplied" if row["source_ref"] else "source reference missing"
        lines.append(f"- Portfolio {check.replace('_', ' ').lower()}: {row['status']} ({label}).")
    if "HISTORICAL_FUND_COMPOSITION_NOT_CURRENT" in warnings:
        lines.append("- Fund constituent evidence predates the portfolio observation; current issuer exposure cannot be inferred from that historical fund snapshot. Obtain a dated composition and review differences.")
        if known is not None:
            if "HISTORICAL_FUND_EXCLUDED_FROM_KNOWN_LOWER_BOUND" not in warnings:
                raise ValueError("ROOM_REPORT_HISTORICAL_LOWER_BOUND_UNQUALIFIED")
            lines.append("- The displayed known issuer lower bound excludes ALL prior-dated fund constituents; only separately reported direct/current-dated exposure contributes. The old fund may overlap this issuer, so complete concentration and Portfolio Room remain UNAVAILABLE.")
        elif "HISTORICAL_FUND_EXCLUDED_FROM_KNOWN_LOWER_BOUND" in warnings:
            raise ValueError("ROOM_REPORT_HISTORICAL_LOWER_BOUND_UNQUALIFIED")
    if warnings:
        lines.append(f"- **{len(warnings)} unresolved/qualified condition(s)** in private Portfolio Room annex; review before considering any new capital.")
    lines.append("No target allocation, selling decision, ranking, after-cost alpha or trading permission is established; analysis remains human-reviewed.")
    return lines


def _opportunity_triage_lines(packet: Mapping[str, Any],
                              analysis_id: str, as_of: str,
                              strategy: str) -> list[str]:
    """Summarize an explicitly supplied non-ranking M2 research queue."""
    triage = packet.get("opportunity_triage_private")
    if triage is None:
        return []
    if not isinstance(triage, Mapping) or (
        triage.get("status") != "PRIVATE_RESEARCH_TRIAGE_PREPARED_NOT_RANKED"
        or triage.get("analysis_id") != analysis_id
        or triage.get("analysis_as_of") != as_of
        or triage.get("strategy_id") != strategy
        or triage.get("universe_completeness") != "NOT_VERIFIED_NOT_GLOBAL_SCREENING"
        or triage.get("source_authentication") != "NOT_PERFORMED"
        or triage.get("normalized_expected_return") != "NOT_ESTABLISHED"
        or triage.get("ranking_or_buy_recommendation") != "NONE"
        or triage.get("portfolio_allocation") != "NONE"
        or triage.get("external_discovery_or_storage") != "NONE"
    ):
        raise ValueError("TRIAGE_REPORT_ID_OR_AUTHORITY_MISMATCH")
    scope = triage.get("universe_scope")
    if scope not in {"OWN_PORTFOLIO", "WATCHLIST", "GLOBAL_DISCOVERY", "MIXED_REQUEST"}:
        raise ValueError("TRIAGE_REPORT_UNIVERSE_SCOPE_INVALID")
    candidates = triage.get("candidates_private_in_supplied_order")
    counts = triage.get("stage_counts")
    total = triage.get("declared_candidate_count")
    stages = ("EVIDENCE_RESOLUTION", "HUMAN_DEEP_DIVE")
    if (not isinstance(candidates, list) or type(total) is not int
            or not 1 <= total <= 30 or len(candidates) != total
            or not isinstance(counts, Mapping) or set(counts) != set(stages)
            or any(type(counts[s]) is not int or counts[s] < 0 for s in stages)
            or sum(counts.values()) != total):
        raise ValueError("TRIAGE_REPORT_COUNT_MISMATCH")
    actual = {s: 0 for s in stages}
    seen: set[str] = set()
    lines = ["", "## Research candidate triage — private, not ranked",
             f"**Supplied {scope.replace('_', ' ').lower()} subset:** {total} candidates; "
             f"{counts['EVIDENCE_RESOLUTION']} awaiting evidence resolution and "
             f"{counts['HUMAN_DEEP_DIVE']} queued for human deep dive."]
    for index, item in enumerate(candidates):
        if not isinstance(item, Mapping):
            raise ValueError("TRIAGE_REPORT_CANDIDATE_INVALID")
        name, stage = item.get("candidate_id_private"), item.get("research_work_stage")
        reasons = item.get("review_reasons")
        if (not isinstance(name, str) or not 1 <= len(name) <= 160
                or any(ord(c) < 32 for c in name) or name in seen
                or stage not in stages or not isinstance(reasons, list)
                or len(reasons) != len(set(reasons))
                or any(not isinstance(code, str) or not 1 <= len(code) <= 100
                       or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in code)
                       for code in reasons)
                or (stage == "EVIDENCE_RESOLUTION") != bool(reasons)
                or item.get("selection_status") != "CEO_OR_ANALYST_REVIEW_ONLY"
                or item.get("investability") != "NOT_EVALUATED"):
            raise ValueError("TRIAGE_REPORT_CANDIDATE_STATUS_INVALID")
        seen.add(name)
        actual[stage] += 1
        if index < 8:
            safe_name = name if all(c.isascii() and (c.isalnum() or c in "._:-") for c in name) else f"candidate #{index + 1}"
            reason = ", ".join(reasons[:3]) if reasons else "source-use structure appears aligned; authenticity not verified"
            if len(reasons) > 3:
                reason += f" (+{len(reasons) - 3} more in private annex)"
            lines.append(f"- **{safe_name}** — {stage.replace('_', ' ').lower()}: {reason}.")
    if actual != dict(counts):
        raise ValueError("TRIAGE_REPORT_STAGE_COUNT_MISMATCH")
    if total > 8:
        lines.append(f"- {total - 8} additional supplied candidates retained in private research annex (original order, no rank).")
    lines.append("Research work queue only. No global market screening, independently checked original source, probabilistic Expected Return, investability verdict, recommendation, portfolio allocation or trades.")
    return lines


def _candidate_comparison_lines(packet: Mapping[str, Any], analysis_id: str,
                                as_of: str, strategy: str) -> list[str]:
    """Show only scenario-to-scenario arithmetic, not Expected Return or rank."""
    comp = packet.get("candidate_comparison_private")
    if comp is None:
        return []
    if not isinstance(comp, Mapping) or (
        comp.get("status") != "CONDITIONAL_RESEARCH_COMPARISON_ONLY"
        or comp.get("analysis_id") != analysis_id
        or comp.get("analysis_as_of") != as_of
        or comp.get("strategy_id") != strategy
        or comp.get("probability_weighted_expected_return") != "NOT_ESTABLISHED"
        or comp.get("benchmark_expected_return") != "NOT_ESTABLISHED"
        or comp.get("forward_alpha_or_superiority") != "NOT_ESTABLISHED"
        or comp.get("recommendation_or_ranking") != "NOT_AUTHORIZED"
        or comp.get("portfolio_allocation") != "NOT_CALCULATED"
        or comp.get("source_authentication") != "NOT_PERFORMED"
        or comp.get("rights_and_costs") != "NOT_VERIFIED"
        or comp.get("trading_authority") != "NONE_CEO_ONLY"
        or comp.get("writes") != "NONE"
    ):
        raise ValueError("COMPARISON_REPORT_ID_OR_AUTHORITY_MISMATCH")
    candidates = comp.get("candidates_private")
    pairs = comp.get("pairwise_scenario_differences_private")
    horizon = comp.get("comparison_horizon_years")
    currency = comp.get("account_currency")
    if (not isinstance(candidates, list) or not 2 <= len(candidates) <= 6
            or not isinstance(pairs, list)
            or len(pairs) != len(candidates) * (len(candidates) - 1) // 2
            or type(horizon) is not int or not 1 <= horizon <= 30
            or not isinstance(currency, str) or len(currency) != 3
            or not currency.isascii() or not currency.isalpha() or currency != currency.upper()):
        raise ValueError("COMPARISON_REPORT_STRUCTURE_INVALID")
    ids = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("COMPARISON_REPORT_CANDIDATE_INVALID")
        name = candidate.get("candidate_id")
        if (not isinstance(name, str) or not name.strip() or len(name) > 160
                or name in ids or candidate.get("source_authentication") != "NOT_PERFORMED"
                or candidate.get("role") not in {"SECURITY", "REFERENCE_ETF"}
                or candidate.get("research_status") not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or candidate.get("portfolio_room_status") not in {"ROOM_CONDITIONAL", "ROOM_UNAVAILABLE", "NOT_EVALUATED"}
                or candidate.get("horizon_years") != horizon):
            raise ValueError("COMPARISON_REPORT_CANDIDATE_INVALID")
        ids.append(name)
    def dec(raw: Any) -> Decimal:
        if not isinstance(raw, str) or not 1 <= len(raw) <= 48:
            raise ValueError("COMPARISON_REPORT_NUMBER_INVALID")
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError("COMPARISON_REPORT_NUMBER_INVALID") from exc
        if not number.is_finite() or not Decimal("-1000000000") <= number <= Decimal("1000000000"):
            raise ValueError("COMPARISON_REPORT_NUMBER_INVALID")
        return number
    def shown(name: str) -> str:
        return name if all(c.isascii() and (c.isalnum() or c in "._:-") for c in name) else "private candidate"
    stages = ("BEAR", "BASE", "BULL")
    lines = ["", "## Cross-candidate scenario arithmetic — private, not ranked",
             f"{len(candidates)} caller-supplied candidates over {horizon} years; account currency {currency}. "
             "Shown differences are first-minus-second in percentage points, not investment merit."]
    expected = [(i, j) for i in range(len(candidates)) for j in range(i + 1, len(candidates))]
    for idx, (pair, (i, j)) in enumerate(zip(pairs, expected)):
        a, b = candidates[i], candidates[j]
        if (not isinstance(pair, Mapping)
                or pair.get("first_candidate_id") != ids[i]
                or pair.get("second_candidate_id") != ids[j]
                or not isinstance(pair.get("by_scenario"), Mapping)
                or set(pair["by_scenario"]) != set(stages)):
            raise ValueError("COMPARISON_REPORT_PAIR_MISMATCH")
        entries = []
        for scenario in stages:
            row = pair["by_scenario"][scenario]
            if not isinstance(row, Mapping):
                raise ValueError("COMPARISON_REPORT_ROW_INVALID")
            status, delta, reasons = (row.get("comparison_status"), row.get("delta_first_minus_second_pp"),
                                      row.get("reason_codes"))
            if (status not in {"SCENARIO_ARITHMETIC_ONLY", "NOT_COMPARABLE"}
                    or not isinstance(reasons, list) or not 1 <= len(reasons) <= 20
                    or any(not isinstance(code, str) or not 1 <= len(code) <= 100
                           or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in code)
                           for code in reasons)):
                raise ValueError("COMPARISON_REPORT_ROW_STATUS_INVALID")
            if status == "NOT_COMPARABLE":
                if delta is not None:
                    raise ValueError("COMPARISON_REPORT_UNSUPPORTED_SPREAD")
                result = "NOT_COMPARABLE"
            else:
                methods = [c.get("scenario_return_measure") for c in (a, b)]
                returns = [c.get("scenario_return_pct_annual") for c in (a, b)]
                if any(not isinstance(x, Mapping) or set(x) != set(stages)
                       for x in methods + returns):
                    raise ValueError("COMPARISON_REPORT_CANDIDATE_SCENARIOS_INVALID")
                method_a, method_b = (x[scenario] for x in methods)
                issues = a.get("qualification_codes", []) + b.get("qualification_codes", [])
                if (method_a != method_b or method_a not in {
                    "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN", "YEAR_END_CASHFLOW_IRR_CONDITIONAL"}
                    or a.get("currency") != currency or b.get("currency") != currency
                    or a.get("quoted_at") != b.get("quoted_at")
                    or "BEAR_BASE_BULL_ORDER_INCONSISTENT" in issues
                    or "MIXED_RETURN_MEASURE_WITHIN_CANDIDATE" in issues):
                    raise ValueError("COMPARISON_REPORT_UNSUPPORTED_SPREAD")
                difference = dec(delta)
                if difference != dec(returns[0][scenario]) - dec(returns[1][scenario]):
                    raise ValueError("COMPARISON_REPORT_SPREAD_MISMATCH")
                basis = ("PRICE_ONLY_NOT_TOTAL_RETURN" if method_a == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN"
                         else "YEAR_END_IRR_ASSUMPTIONS_UNVERIFIED")
                if reasons != [basis]:
                    raise ValueError("COMPARISON_REPORT_RETURN_BASIS_MISMATCH")
                result = f"{format(difference, 'f')} pp ({'price-only CAGR' if method_a == 'PRICE_ONLY_CAGR_NOT_TOTAL_RETURN' else 'conditional year-end IRR'})"
            entries.append(f"{scenario}: {result}")
        if idx < 4:
            lines.append(f"- **{shown(ids[i])} minus {shown(ids[j])}** — " + "; ".join(entries) + ".")
    if len(pairs) > 4:
        lines.append(f"- {len(pairs) - 4} additional pair comparisons in the private annex.")
    lines.append("No source/FX/tax/cost certification, probability-weighted Expected Return, VFV forecast, expected alpha, ranking, portfolio allocation or trading authority.")
    return lines


def _historical_comparison_lines(packet: Mapping[str, Any],
                                 analysis_id: str, as_of: str, kind: str) -> list[str]:
    """Human-only review of supplied prior/current claims, never certified change."""
    result = packet.get("historical_research_comparison_private")
    if result is None:
        return []
    if (kind != "FOLLOWUP" or not isinstance(result, Mapping)
            or result.get("source_authentication") != "NOT_PERFORMED"
            or result.get("economic_change_status") != "NOT_EVALUATED"
            or result.get("privacy") != "PRIVATE_ONLY"):
        raise ValueError("HISTORY_REPORT_AUTHORITY_OR_KIND_MISMATCH")
    status = result.get("status")
    items = result.get("review_items_private")
    if status not in {"BASELINE_NOT_AVAILABLE", "NO_FACT_LINKS_SUPPLIED",
                      "STRUCTURAL_REVIEW_PREPARED"} or not isinstance(items, list) or len(items) > 200:
        raise ValueError("HISTORY_REPORT_STATUS_OR_ITEMS_INVALID")
    lines = ["", "### Prior/current research — structural follow-up only"]
    if status == "BASELINE_NOT_AVAILABLE":
        if items or result.get("prior_analysis_id_private") is not None:
            raise ValueError("HISTORY_REPORT_BASELINE_INCONSISTENT")
        lines.append("BASELINE_NOT_AVAILABLE: no earlier case was supplied; no historical conclusion is possible.")
        return lines
    prior_id = result.get("prior_analysis_id_private")
    if (not isinstance(prior_id, str) or not prior_id or prior_id == analysis_id
            or result.get("current_analysis_id_private") != analysis_id
            or result.get("current_as_of") != as_of
            or (packet.get("prior_analysis_id") is not None
                and packet["prior_analysis_id"] != prior_id)
            or result.get("comparability") != "ANALYST_MUST_VERIFY_IDENTITY_METRIC_UNITS_PERIODS_AND_RIGHTS"
            or result.get("baseline_authentication") != "CALLER_SUPPLIED_RECORD_STRUCTURALLY_CHECKED_ONLY"
            or type(result.get("strategy_changed")) is not bool
            or type(result.get("method_changed")) is not bool):
        raise ValueError("HISTORY_REPORT_ID_OR_BASIS_MISMATCH")
    old_date = _iso_date(result.get("prior_as_of"), "history.prior_as_of")
    if old_date >= as_of:
        raise ValueError("HISTORY_REPORT_PRIOR_DATE_INVALID")
    if (status == "STRUCTURAL_REVIEW_PREPARED") != bool(items):
        raise ValueError("HISTORY_REPORT_LINK_STATUS_MISMATCH")
    lines.append(f"Supplied earlier case dated {old_date}; current {as_of}. Evidence and metric comparability are not independently verified.")
    changes = []
    if result["strategy_changed"]:
        changes.append("strategy")
    if result["method_changed"]:
        changes.append("method version")
    if changes:
        lines.append("Comparability WARNING: " + " and ".join(changes) + " changed between cases.")
    seen_old, seen_new = set(), set()
    same, different = 0, 0
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ValueError("HISTORY_REPORT_LINK_INVALID")
        old, new = item.get("prior_fact_id"), item.get("current_fact_id")
        valid = lambda v: (isinstance(v, str) and 1 <= len(v) <= 80
                           and v[0].isascii() and v[0].isalnum()
                           and all(c.isascii() and (c.isalnum() or c in "._:-") for c in v))
        if (not valid(old) or not valid(new) or old in seen_old or new in seen_new
                or item.get("prior_evidence_status") not in EVIDENCE_STATUSES
                or item.get("current_evidence_status") not in EVIDENCE_STATUSES
                or item.get("text_check") not in {
                    "TEXT_SAME_NOT_EVIDENCE_OF_NO_CHANGE",
                    "TEXT_DIFF_NOT_CERTIFIED_ECONOMIC_CHANGE"}):
            raise ValueError("HISTORY_REPORT_LINK_INVALID")
        seen_old.add(old)
        seen_new.add(new)
        is_diff = item["text_check"] == "TEXT_DIFF_NOT_CERTIFIED_ECONOMIC_CHANGE"
        different += is_diff
        same += not is_diff
        if index < 6:
            label = "wording differs, economic change UNVERIFIED" if is_diff else "wording unchanged, stability NOT PROVEN"
            lines.append(f"- {old} → {new}: {item['prior_evidence_status']} → {item['current_evidence_status']}; {label}.")
    if items:
        lines.append(f"{len(items)} linked facts: {different} wording differences, {same} unchanged; no certified thesis change.")
    else:
        lines.append("NO_FACT_LINKS_SUPPLIED: no linked claims to review; do not infer no change.")
    if len(items) > 6:
        lines.append(f"{len(items) - 6} further links remain in the private annex.")
    lines.append("Human review required for comparable definitions, original evidence, sources, rights and thesis changes. No automatic archive search or investment action.")
    return lines


def _macro_sector_context_lines(packet: Mapping[str, Any], analysis_id: str,
                                as_of: str, strategy: str) -> list[str]:
    """Only structural macro/sector review labels, never causal or trading advice."""
    context = packet.get("macro_sector_context_private")
    if context is None:
        return []
    if (not isinstance(context, Mapping)
            or context.get("status") != "PRIVATE_MACRO_SECTOR_CONTEXT_PREPARED_NOT_CERTIFIED"
            or context.get("analysis_id") != analysis_id
            or context.get("analysis_as_of") != as_of
            or context.get("strategy_id") != strategy
            or context.get("source_authentication") != "NOT_PERFORMED"
            or context.get("causal_inference") != "ANALYST_HYPOTHESIS_NOT_CERTIFIED"
            or context.get("market_timing_or_price_prediction") != "NONE"
            or context.get("ranking_or_trading_authority") != "NONE"
            or context.get("public_memory_write") != "NONE"):
        raise ValueError("CONTEXT_REPORT_AUTHORITY_OR_MANDATE_MISMATCH")
    rows, counts = context.get("drivers_private_in_supplied_order"), context.get("stage_counts")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 8 or not isinstance(counts, Mapping):
        raise ValueError("CONTEXT_REPORT_ROWS_INVALID")
    actual = {"EVIDENCE_RESOLUTION": 0, "HUMAN_CAUSAL_REVIEW": 0}
    seen = set()
    lines = ["", "## Macro and sector context — conditional research links",
             "Reported drivers tied to IR/source IDs only; causal claims, timing and returns are not verified."]
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("CONTEXT_REPORT_ROW_INVALID")
        did = row.get("driver_id")
        if (not isinstance(did, str) or not 1 <= len(did) <= 80
                or not did[0].isascii() or not did[0].isalnum()
                or any(not c.isascii() or not (c.isalnum() or c in "._:-") for c in did)
                or did in seen or row.get("scope") not in {"MACRO", "SECTOR"}
                or row.get("reported_effect") not in {
                    "TAILWIND_REPORTED", "HEADWIND_REPORTED", "MIXED_REPORTED", "UNKNOWN"}
                or row.get("research_work_stage") not in actual
                or row.get("causal_authentication") != "NOT_PERFORMED"):
            raise ValueError("CONTEXT_REPORT_ROW_AUTHORITY_INVALID")
        refs, observations, reasons = (row.get("ir_fact_ids_private"),
                                        row.get("source_observation_ids_private"),
                                        row.get("review_reasons"))
        if (not isinstance(refs, list) or not refs
                or not isinstance(observations, list) or not isinstance(reasons, list)
                or (row["research_work_stage"] == "EVIDENCE_RESOLUTION") != bool(reasons)
                or any(not isinstance(code, str) or not 1 <= len(code) <= 80
                       or any(not c.isascii() or not (c.isupper() or c.isdigit() or c == "_")
                              for c in code) for code in reasons)):
            raise ValueError("CONTEXT_REPORT_EVIDENCE_INVALID")
        seen.add(did)
        actual[row["research_work_stage"]] += 1
        lines.append(f"- {did} [{row['scope']}]: {row['reported_effect']}; "
                     f"{row['research_work_stage']}, {len(reasons)} unresolved qualifier(s).")
    if counts != actual or context.get("driver_count") != len(rows):
        raise ValueError("CONTEXT_REPORT_COUNT_MISMATCH")
    lines.append(f"**Research queue:** {actual['EVIDENCE_RESOLUTION']} evidence-resolution, "
                 f"{actual['HUMAN_CAUSAL_REVIEW']} human causal-review item(s). "
                 "Private hypotheses, source locators, countercases and checks stay in the annex.")
    return lines

def _exceptional_lifecycle_lines(packet: Mapping[str, Any], analysis_id: str,
                                 as_of: str, strategy: str) -> list[str]:
    """Compact private review stage; no original holdings or trade instructions."""
    review = packet.get("exceptional_lifecycle_review_private")
    if review is None:
        return []
    if not isinstance(review, Mapping) or (
        review.get("analysis_id") != analysis_id
        or review.get("analysis_as_of") != as_of
        or review.get("strategy_id") != strategy
        or review.get("status") not in {
            "EVIDENCE_RESOLUTION_NO_ACTION", "HUMAN_THESIS_AND_COST_REVIEW_ONLY"}
        or review.get("source_authentication") != "NOT_PERFORMED"
        or review.get("account_and_cost_authentication") != "NOT_PERFORMED"
        or review.get("portfolio_room_admission") != "NONE"
        or review.get("allocation_or_sale_proposal") != "NONE"
        or review.get("trade_authority") != "NONE_CEO_ONLY"
        or review.get("public_memory_write") != "NONE"
    ):
        raise ValueError("LIFECYCLE_REPORT_AUTHORITY_OR_ID_MISMATCH")
    observed = _iso_date(review.get("portfolio_observed_on"), "lifecycle.observed_on")
    if observed > as_of:
        raise ValueError("LIFECYCLE_REPORT_FUTURE_OBSERVATION")
    refs = review.get("original_ir_fact_ids_private")
    current = review.get("current_evidence_refs_private")
    missing = review.get("missing_or_qualified")
    if (not isinstance(refs, list) or not refs or len(refs) > 24
            or not isinstance(current, list) or len(current) > 24
            or not isinstance(missing, list) or len(missing) > 16):
        raise ValueError("LIFECYCLE_REPORT_REFS_INVALID")
    from .exceptional_lifecycle import EVENTS, VIEWS
    event, view = review.get("thesis_event"), review.get("analyst_reported_view")
    if event not in EVENTS or view not in VIEWS:
        raise ValueError("LIFECYCLE_REPORT_VIEW_INVALID")
    return [
        "", "## Exceptional position lifecycle — High-CAGR, human review only",
        f"Thesis event category: {event}; specialist-reported hypothesis: {view} "
        "(not an actionable recommendation).",
        f"Observed as of {observed}; {len(refs)} original IR fact link(s), "
        f"{len(current)} current supplied evidence reference(s).",
        "Recent-source link status: "
        + ("NOT_SUPPLIED" if review.get("current_evidence_annex_private") is None
           else "CALLER_REPORTED_STRUCTURAL_ONLY_NOT_CERTIFIED") + ".",
        f"Review stage: {review['status']}; {len(missing)} unresolved qualification(s) "
        "in the private annex. Original thesis, position, costs and countercase "
        "require independent human review.",
        "No sell/trim trigger is inferred from price volatility, uncertainty or "
        "a reported view. No target weight, order, verified cost, tax conclusion "
        "or transaction authority has been established.",
    ]


def _five_pillar_lines(packet: Mapping[str, Any], analysis_id: str,
                       as_of: str, strategy: str) -> list[str]:
    """Join separately qualified four IR pillars with the fifth PI Room view.

    This reports cross-specialist reconciliation only, not a composite score,
    promotion of either source's status, or portfolio admission.
    """
    ir = packet.get("pillar_trace_private")
    room = packet.get("portfolio_room_review_private")
    if ir is None or room is None:
        return []
    if not isinstance(ir, Mapping) or not isinstance(room, Mapping) or (
        ir.get("status") != "PRIVATE_FOUR_PILLAR_IR_TRACE_NOT_CERTIFIED"
        or ir.get("analysis_id") != analysis_id
        or ir.get("analysis_as_of") != as_of
        or ir.get("strategy_id") != strategy
        or ir.get("source_authentication") != "NOT_PERFORMED"
        or ir.get("investment_or_trade_authority") != "NONE"
        or room.get("analysis_id") != analysis_id
        or room.get("as_of") != as_of
        or room.get("strategy_id") != strategy
        or room.get("portfolio_room_authority") != "QUALITATIVE_SPECIALIST_REPORTED_ONLY"
        or room.get("independent_evidence_check") != "NOT_PERFORMED"
        or room.get("trade_authority") != "NONE_CEO_ONLY"
        or room.get("status") not in {"ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"}
    ):
        raise ValueError("FIVE_PILLAR_AUTHORITY_OR_ID_MISMATCH")
    research_date = _iso_date(ir.get("research_as_of"), "five_pillar.research_as_of")
    portfolio_date = _iso_date(room.get("observed_on"), "five_pillar.observed_on")
    if research_date > as_of or portfolio_date > as_of:
        raise ValueError("FIVE_PILLAR_FUTURE_EVIDENCE")
    ledger = packet.get("portfolio_observation_private")
    if ledger is not None and (
        not isinstance(ledger, Mapping)
        or ledger.get("analysis_id") != analysis_id
        or ledger.get("observed_on") != portfolio_date
        or ledger.get("private_scope") is not True
    ):
        raise ValueError("FIVE_PILLAR_ROOM_P_LEDGER_MISMATCH")
    names = ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
    ir_rows, pi_rows = ir.get("pillars_private"), room.get("research_axes_private")
    if (not isinstance(ir_rows, Mapping) or set(ir_rows) != set(names)
            or not isinstance(pi_rows, Mapping) or set(pi_rows) != set(names)):
        raise ValueError("FIVE_PILLAR_FOUR_RESEARCH_AXES_REQUIRED")
    lines = [
        "", "## Five-pillar integrated view — reported, not certified",
        "Four research dimensions from IR and the separate Portfolio Room from PI. "
        "A matching reference is not independent evidence or an investment rating.",
    ]
    for name in names:
        ir_row, pi_row = ir_rows[name], pi_rows[name]
        if not isinstance(ir_row, Mapping) or not isinstance(pi_row, Mapping):
            raise ValueError("FIVE_PILLAR_RESEARCH_ROW_INVALID")
        ir_status, pi_status = ir_row.get("reported_status"), pi_row.get("status")
        stage = ir_row.get("review_stage")
        ir_refs, pi_refs = ir_row.get("ir_fact_ids_private"), pi_row.get("ir_fact_ids")
        if (ir_status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or pi_status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or stage not in {"NOT_ASSESSED", "EVIDENCE_RESOLUTION", "HUMAN_RESEARCH_REVIEW_ONLY"}
                or not isinstance(ir_refs, list) or not isinstance(pi_refs, list)
                or any(not isinstance(ref, str) or not ref for ref in ir_refs + pi_refs)
                or len(set(ir_refs)) != len(ir_refs)
                or len(set(pi_refs)) != len(pi_refs)):
            raise ValueError("FIVE_PILLAR_RESEARCH_LINK_INVALID")
        if ir_status == "UNKNOWN":
            comparison = "IR_NOT_ASSESSED"
        elif pi_status == "UNKNOWN":
            comparison = "PI_RESEARCH_UNKNOWN"
        elif set(ir_refs) != set(pi_refs):
            comparison = "FACT_LINK_DIVERGENCE_REQUIRES_REVIEW"
        elif stage == "EVIDENCE_RESOLUTION":
            comparison = "SAME_REPORTED_LINKS_EVIDENCE_RESOLUTION"
        else:
            comparison = "SAME_REPORTED_LINKS_HUMAN_REVIEW_ONLY"
        lines.append(f"- {name.replace('_', ' ').title()}: "
                     f"IR {stage}; PI {pi_status}; {comparison}.")
    lines.append(f"- Portfolio Room: {room['status']} (observed {portfolio_date}); "
                 "qualitative, caller-reported and never admission authority.")
    lines.append("No composite five-pillar score, validated expected return, "
                 "target weight, buying or selling decision, or trade authority. "
                 "Review conflicting IR/PI links and original evidence manually.")
    return lines


def _pillar_trace_lines(packet: Mapping[str, Any], analysis_id: str,
                        as_of: str, strategy: str) -> list[str]:
    """Report four IR axes as research queues, never as investment scores."""
    trace = packet.get("pillar_trace_private")
    if trace is None:
        return []
    if not isinstance(trace, Mapping) or (
        trace.get("status") != "PRIVATE_FOUR_PILLAR_IR_TRACE_NOT_CERTIFIED"
        or trace.get("analysis_id") != analysis_id
        or trace.get("analysis_as_of") != as_of
        or trace.get("strategy_id") != strategy
        or trace.get("source_authentication") != "NOT_PERFORMED"
        or trace.get("expected_return_certification") != "NOT_ESTABLISHED"
        or trace.get("portfolio_room") != "SEPARATE_PI_EVIDENCE_REQUIRED"
        or trace.get("investment_or_trade_authority") != "NONE"
        or trace.get("storage") != "NONE"
    ):
        raise ValueError("PILLAR_REPORT_AUTHORITY_MISMATCH")
    researched = _iso_date(trace.get("research_as_of"), "pillar.research_as_of")
    if researched > as_of:
        raise ValueError("PILLAR_REPORT_FUTURE_RESEARCH")
    rows = trace.get("pillars_private")
    names = ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
    if not isinstance(rows, Mapping) or set(rows) != set(names):
        raise ValueError("PILLAR_REPORT_FOUR_AXES_REQUIRED")
    lines = ["", "## Four research pillars — specialist-reported, not certified"]
    for name in names:
        row = rows[name]
        if not isinstance(row, Mapping):
            raise ValueError("PILLAR_REPORT_AXIS_INVALID")
        reported = row.get("reported_status")
        stage = row.get("review_stage")
        refs = row.get("ir_fact_ids_private")
        if (reported not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or stage not in {"NOT_ASSESSED", "EVIDENCE_RESOLUTION", "HUMAN_RESEARCH_REVIEW_ONLY"}
                or (reported == "UNKNOWN") != (stage == "NOT_ASSESSED")
                or not isinstance(refs, list) or len(refs) > 24
                or any(not isinstance(ref, str) or not ref or len(ref) > 80 for ref in refs)
                or len(set(refs)) != len(refs)
                or (reported == "SPECIALIST_REPORTED" and not refs)):
            raise ValueError("PILLAR_REPORT_AXIS_STATUS_INVALID")
        lines.append(
            f"- **{name.replace('_', ' ').title()}** — {stage.replace('_', ' ').lower()}; "
            f"{len(refs)} referenced IR fact(s); no source or economic certification.")
    lines.append("Portfolio Room is a separate, dated PI assessment; "
                 "no overall five-pillar score, normalized Expected Return, VFV alpha, admission or trade authority.")
    return lines


def _mode_research_lines(packet: Mapping[str, Any], analysis_id: str,
                         as_of: str, strategy: str) -> list[str]:
    """Display only fixed mode questions, trace stage and count (no IR narrative)."""
    trace = packet.get("mode_research_trace_private")
    if trace is None:
        return []
    if (not isinstance(trace, Mapping)
            or trace.get("status") != "PRIVATE_MODE_RESEARCH_TRACE_NOT_CERTIFIED"
            or trace.get("analysis_id") != analysis_id
            or trace.get("analysis_as_of") != as_of
            or not isinstance(trace.get("strategy_id"), str)
            or trace["strategy_id"].strip().lower() != strategy.strip().lower()
            or trace.get("source_authentication") != "NOT_PERFORMED"
            or trace.get("method_load") != "NOT_VERIFIED"
            or trace.get("investment_or_trade_authority") != "NONE"
            or trace.get("storage") != "NONE"
            or _iso_date(trace.get("research_as_of"), "mode.research_as_of") > as_of):
        raise ValueError("MODE_RESEARCH_REPORT_AUTHORITY_MISMATCH")
    questions = prepare_strategy_research_brief(strategy)["ir_research_questions"]
    rows = trace.get("questions_private")
    if not isinstance(rows, list) or len(rows) != len(questions):
        raise ValueError("MODE_RESEARCH_REPORT_QUESTION_COUNT_INVALID")
    lines = ["", "## Mode-specific IR research — evidence links, not certification"]
    for i, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            raise ValueError("MODE_RESEARCH_REPORT_ROW_INVALID")
        status, stage, refs = row.get("reported_status"), row.get("review_stage"), row.get("ir_fact_ids_private")
        if (row.get("question_index") != i
                or row.get("question_text") != questions[i - 1]
                or status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or stage not in {"NOT_ASSESSED", "EVIDENCE_RESOLUTION", "HUMAN_RESEARCH_REVIEW_ONLY"}
                or (status == "UNKNOWN") != (stage == "NOT_ASSESSED")
                or not isinstance(refs, list) or len(refs) > 12
                or (status == "SPECIALIST_REPORTED" and not refs)
                or any(not isinstance(ref, str) or not ref for ref in refs)):
            raise ValueError("MODE_RESEARCH_REPORT_LINK_OR_STAGE_INVALID")
        lines.append(f"- Q{i}: {questions[i - 1]} — {stage}; {len(refs)} referenced IR fact(s).")
    lines.append("Links are specialist-reported, not verified economic conclusions. "
                 "Portfolio-specific questions require separate dated PI evidence.")
    return lines


def _mode_portfolio_lines(packet: Mapping[str, Any], analysis_id: str,
                          as_of: str, strategy: str) -> list[str]:
    """Show only fixed PI questions/stages and P-row counts, never holdings."""
    trace = packet.get("mode_portfolio_trace_private")
    if trace is None:
        return []
    if (not isinstance(trace, Mapping)
            or trace.get("status") != "PRIVATE_MODE_PI_TRACE_NOT_AUTHENTICATED"
            or trace.get("analysis_id") != analysis_id
            or trace.get("analysis_as_of") != as_of
            or not isinstance(trace.get("strategy_id"), str)
            or trace["strategy_id"].strip().lower() != strategy.strip().lower()
            or trace.get("source_authentication") != "NOT_PERFORMED"
            or trace.get("method_load") != "NOT_VERIFIED"
            or trace.get("portfolio_room_authority") != "NONE"
            or trace.get("investment_or_trade_authority") != "NONE"
            or trace.get("storage") != "NONE"
            or trace.get("observation_link_status") not in {"CALLER_REPORTED_P_LEDGER", "NO_P_LEDGER"}
            or _iso_date(trace.get("portfolio_as_of"), "mode_pi.portfolio_as_of") > as_of):
        raise ValueError("MODE_PI_REPORT_AUTHORITY_MISMATCH")
    questions = prepare_strategy_research_brief(strategy)["pi_portfolio_questions"]
    rows = trace.get("questions_private")
    if not isinstance(rows, list) or len(rows) != len(questions):
        raise ValueError("MODE_PI_REPORT_QUESTION_COUNT_INVALID")
    lines = ["", "## Mode-specific PI research — private observation links, not certification"]
    for i, row in enumerate(rows, 1):
        if not isinstance(row, Mapping):
            raise ValueError("MODE_PI_REPORT_ROW_INVALID")
        status, stage, refs = row.get("reported_status"), row.get("review_stage"), row.get("p_ids_private")
        if (type(row.get("question_index")) is not int or row["question_index"] != i
                or row.get("question_text") != questions[i - 1]
                or status not in {"SPECIALIST_REPORTED", "UNKNOWN"}
                or stage not in {"NOT_ASSESSED", "EVIDENCE_RESOLUTION", "HUMAN_PORTFOLIO_REVIEW_ONLY"}
                or (status == "UNKNOWN") != (stage == "NOT_ASSESSED")
                or not isinstance(refs, list) or len(refs) > 24
                or len(set(refs)) != len(refs)
                or (status == "SPECIALIST_REPORTED") != bool(refs)
                or any(not isinstance(ref, str) or not ref for ref in refs)
                or (trace["observation_link_status"] == "NO_P_LEDGER"
                    and stage == "HUMAN_PORTFOLIO_REVIEW_ONLY")):
            raise ValueError("MODE_PI_REPORT_LINK_OR_STAGE_INVALID")
        lines.append(f"- Q{i}: {questions[i - 1]} — {stage}; {len(refs)} caller-reported P record link(s).")
    lines.append("No holdings, weights, fees or account values reproduced. "
                 "P links do not establish Portfolio Room, approved policy or trade authority.")
    return lines



_CALCULATION_METRICS = {
    "OPERATING_MARGIN": "OPERATING_MARGIN_PERCENT",
    "REVENUE_GROWTH_YOY": "REVENUE_GROWTH_YOY_PERCENT",
    "CFO_LESS_PPE": "CFO_MINUS_PPE_PROXY_NOT_NORMALIZED_FCF",
}


def _calculation_lines(packet: Mapping[str, Any]) -> list[str]:
    """Present M5 results in the private report, without source or PIT promotion."""
    checks = packet.get("calculation_checks_private")
    if checks is None:
        return []
    if not isinstance(checks, list):
        raise ValueError("CALCULATION_REPORT_LIST_REQUIRED")
    if not checks:
        return []
    lines = [
        "", "## Descriptive financial calculations — conditional",
        "M5 checks supplied current-observation arithmetic only. Source authenticity, "
        "original-IR point-in-time availability, normalized economics and investment "
        "authority are NOT established.",
    ]
    for i, item in enumerate(checks):
        if not isinstance(item, Mapping):
            raise ValueError("CALCULATION_REPORT_ENTRY_INVALID")
        op = item.get("operation")
        status = item.get("status")
        if (not isinstance(op, str) or op not in _CALCULATION_METRICS
                or not isinstance(status, str)
                or status not in {"FORMALLY_CALCULATED", "UNAVAILABLE"}
                or item.get("source_verification") != "NOT_PERFORMED"
                or item.get("temporal_authority") != "CURRENT_OBSERVATION_ONLY"):
            raise ValueError("CALCULATION_REPORT_AUTHORITY_OR_OPERATION_INVALID")
        ids = item.get("fact_ids")
        if (not isinstance(ids, list) or len(ids) != 2
                or any(not isinstance(x, str) or not x.strip() for x in ids)):
            raise ValueError("CALCULATION_REPORT_FACT_IDS_INVALID")
        if status == "UNAVAILABLE":
            if set(item) != {"status", "operation", "fact_ids", "reason_codes",
                             "source_verification", "temporal_authority"}:
                raise ValueError("CALCULATION_REPORT_UNAVAILABLE_SCHEMA_INVALID")
            reasons = item["reason_codes"]
            if (not isinstance(reasons, list) or not reasons or len(reasons) > 24
                    or any(not isinstance(x, str)
                           or re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", x) is None
                           for x in reasons)):
                raise ValueError("CALCULATION_REPORT_REASONS_INVALID")
            if i < 8:
                lines.append(f"- {op}: UNAVAILABLE ({', '.join(sorted(set(reasons)))}).")
            continue
        mandatory = {"status", "operation", "metric", "value", "unit",
                     "fact_ids", "input_evidence_labels", "source_rights_statuses",
                     "source_verification", "temporal_authority", "decision_grade"}
        rights = item.get("source_rights_statuses")
        labels = item.get("input_evidence_labels")
        if (set(item) not in (mandatory, mandatory | {"permission_caveat"})
                or item.get("metric") != _CALCULATION_METRICS[op]
                or item.get("decision_grade") is not False
                or not isinstance(labels, list) or len(labels) != 2
                or any(not isinstance(x, str)
                       or x not in {"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"}
                       for x in labels)
                or not isinstance(rights, list) or len(rights) != 2
                or any(not isinstance(x, str)
                       or x not in {"PERMITTED", "UNCERTAIN", "RESTRICTED"}
                       for x in rights)):
            raise ValueError("CALCULATION_REPORT_FORMAL_SCHEMA_INVALID")
        uncertain = "UNCERTAIN" in rights
        if (("permission_caveat" in item) != uncertain
                or (uncertain and item["permission_caveat"]
                    != "SOURCE_USE_UNCERTAIN_REVIEW_REQUIRED")):
            raise ValueError("CALCULATION_REPORT_RIGHTS_CAVEAT_INVALID")
        value = item.get("value")
        if (not isinstance(value, str) or len(value) > 48
                or re.fullmatch(r"-?[0-9]{1,24}\.[0-9]{2}", value) is None):
            raise ValueError("CALCULATION_REPORT_VALUE_INVALID")
        unit = item.get("unit")
        if op != "CFO_LESS_PPE":
            if unit != "PERCENT":
                raise ValueError("CALCULATION_REPORT_UNIT_INVALID")
            shown = value + "%"
        else:
            if (not isinstance(unit, str)
                    or re.fullmatch(r"[A-Za-z0-9_./-]{1,40} [A-Z]{3}", unit) is None):
                raise ValueError("CALCULATION_REPORT_UNIT_INVALID")
            shown = value + " " + unit
        if i < 8:
            qualifier = "; source rights require review" if uncertain else ""
            lines.append(f"- {op}: {shown} (formal arithmetic only{qualifier}).")
    if len(checks) > 8:
        lines.append(f"- {len(checks) - 8} additional check(s) retained in the private annex.")
    return lines


def render_report(packet: Mapping[str, Any]) -> str:
    """Render a concise markdown research report or user-requested follow-up.

    The presence of evidence metadata does not independently validate a claim.
    Portfolio-sensitive packets must remain in the user's private environment.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("packet: mapping required")
    kind = _string(packet.get("kind"), "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind: DECISION or FOLLOWUP required")
    if kind != "FOLLOWUP" and packet.get("historical_research_comparison_private") is not None:
        raise ValueError("HISTORY_REPORT_AUTHORITY_OR_KIND_MISMATCH")
    analysis_id = _string(packet.get("analysis_id"), "analysis_id")
    as_of = _iso_date(packet.get("as_of"), "as_of")
    strategy = _string(packet.get("strategy"), "strategy")
    mode_gate = assess_r1_mode(strategy)
    if ("strategy_policy_gate" in packet
            and packet["strategy_policy_gate"] != mode_gate):
        raise ValueError("REPORT_R1_STRATEGY_POLICY_GATE_MISMATCH")
    method_version = _string(packet.get("method_version"), "method_version")
    status = _string(packet.get("status"), "status")
    if status not in REPORT_STATUSES:
        raise ValueError("unsupported report status")
    objective = _string(packet.get("objective"), "objective")
    decision_line = _string(packet.get("decision_line"), "decision_line")
    next_action = _string(packet.get("next_action"), "next_action")
    if not isinstance(packet.get("summary"), list) or not (1 <= len(packet["summary"]) <= 6):
        raise ValueError("summary: 1 to 6 points required")
    for i, item in enumerate(packet["summary"]):
        _string(item, f"summary[{i}]")
    facts = _facts(packet.get("facts"))
    source_review = _source_review(packet, analysis_id, as_of, facts)
    lines = [
        f"# {'User-requested reassessment' if kind == 'FOLLOWUP' else 'Investment decision research'} — {analysis_id}",
        f"**As of:** {as_of} | **Strategy:** {strategy} | **Method:** {method_version} | **Status:** {status}",
        f"**R1 strategy policy:** {mode_gate['policy_authority']}; method load {mode_gate['method_load']}. {mode_gate['limitation']}",
        f"**Question:** {objective}",
        "", "## Decision line", decision_line, "", "## Key findings",
    ]
    lines += [f"- {item.strip()}" for item in packet["summary"]]
    lines += [
        "", "**Source assurance:** IR evidence statuses are research-reported, not "
        "independently authenticated by this report (including rights and historical availability)."
    ]
    if source_review is not None:
        _, flagged_count = source_review
        lines.append(
            f"**Source reconciliation:** {flagged_count}/{len(facts)} facts require "
            "human source-use review based on supplied observations; no status was upgraded."
        )
    lines += _pillar_trace_lines(packet, analysis_id, as_of, strategy)
    lines += _mode_research_lines(packet, analysis_id, as_of, strategy)
    lines += _mode_portfolio_lines(packet, analysis_id, as_of, strategy)
    lines += ["", "## Supporting observations"]
    if facts:
        for item in facts:
            ref = item["id"].strip()
            evidence_status = item["status"].strip()
            locator = item.get("source_url") or "SOURCE_NOT_SUPPLIED"
            period = item.get("period") or "PERIOD_UNKNOWN"
            lines.append(f"- [{ref} / {evidence_status}] {item['claim'].strip()} (period: {period}; source: {locator})")
            if source_review is not None and source_review[0][ref]:
                flags = ", ".join(source_review[0][ref])
                lines.append(f"  - **Source review required:** {flags}. IR-reported label is not independently corroborated.")
    else:
        lines.append("No underlying fact records supplied; no factual verification is asserted.")
    lines += _opportunity_triage_lines(packet, analysis_id, as_of, strategy)
    lines += _macro_sector_context_lines(packet, analysis_id, as_of, strategy)
    lines += _fundamental_lines(packet, analysis_id, as_of)
    lines += _calculation_lines(packet)
    lines += _valuation_lines(packet, analysis_id, as_of)
    lines += _weighted_cashflow_lines(packet, analysis_id, as_of)
    lines += _candidate_comparison_lines(packet, analysis_id, as_of, strategy)
    lines += _new_contribution_lines(packet, analysis_id, as_of)
    lines += _portfolio_observation_lines(packet, analysis_id, as_of)
    lines += _portfolio_exposure_lines(packet, analysis_id, as_of)
    lines += _portfolio_room_lines(packet, analysis_id, as_of)
    lines += _five_pillar_lines(packet, analysis_id, as_of, strategy)
    lines += _exceptional_lifecycle_lines(packet, analysis_id, as_of, strategy)
    if kind == "FOLLOWUP":
        previous_id = packet.get("prior_analysis_id")
        if previous_id is None:
            prior_line = "BASELINE_NOT_AVAILABLE: no previous analysis was provided."
        else:
            prior_line = f"Prior analysis: {_string(previous_id, 'prior_analysis_id')}"
        start_raw, end_raw = packet.get("period_start"), packet.get("period_end")
        if (start_raw is None) != (end_raw is None):
            raise ValueError("follow-up comparison dates must be supplied together")
        if start_raw is None:
            window_label = "no fixed reporting window"
        else:
            start = _iso_date(start_raw, "period_start")
            end = _iso_date(end_raw, "period_end")
            if start > end or end > as_of:
                raise ValueError("follow-up period must be ordered and end by as_of")
            window_label = f"{start} to {end}"
        changes = packet.get("changes")
        if not isinstance(changes, list):
            raise ValueError("changes: list required, possibly empty")
        lines += ["", f"## Requested comparison ({window_label})", prior_line]
        if not changes:
            lines.append("No changes entered in this packet; this is NOT proof that no market or thesis events occurred.")
        else:
            for i, change in enumerate(changes):
                if not isinstance(change, Mapping):
                    raise ValueError(f"changes[{i}]: record required")
                subject = _string(change.get("subject"), f"changes[{i}].subject")
                finding = _string(change.get("finding"), f"changes[{i}].finding")
                cstatus = _string(change.get("status"), f"changes[{i}].status")
                if cstatus not in EVIDENCE_STATUSES:
                    raise ValueError(f"changes[{i}]: invalid status")
                lines.append(f"- **{subject}** [{cstatus}]: {finding}")
        lines += _historical_comparison_lines(packet, analysis_id, as_of, kind)
    lines += [
        "", "## Strongest countercase / limitation",
        _string(packet.get("countercase"), "countercase"),
        "", "## Evidence and portfolio boundaries",
        _string(packet.get("limitations"), "limitations"),
        "", "## Next human action", next_action,
        "", "_Rendered from supplied data only. No source checks, monitoring, archival or investment execution performed by this formatter._",
    ]
    return "\n".join(lines) + "\n"
