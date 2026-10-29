"""On-demand private change in scoped portfolio weights between two dated observations.

Reuses the existing P-ledger constructor for the caller-supplied prior input.
This is NOT price performance, trading flow, executed holdings, total household
wealth, attribution, broker verification or proof of historical completeness.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from .portfolio_observation import prepare_observation_ledger

HUNDRED = Decimal("100")
PCT = Decimal("0.01")
COMPLETE = "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA"


def _positions(ledger: Mapping[str, Any]) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for row in ledger["p_ledger_private"]:
        security = row["security_id"]
        if not isinstance(security, str) or not security or security == "P-CASH":
            raise ValueError("SNAPSHOT_SECURITY_ID_INVALID")
        value = Decimal(row["market_value_base"])
        result[security] = result.get(security, Decimal("0")) + value
    return result


def _percent(part: Decimal, total: Decimal) -> Decimal:
    return (part * HUNDRED / total).quantize(PCT, rounding=ROUND_HALF_UP)


def _caller_visible_ui_weights(ledger: Mapping[str, Any]) -> dict[str, Decimal] | None:
    """Strictly descriptive source-displayed percentages; not monetary weights.

    A dated, claimed-complete named account and independently visible security/
    account identities are needed on each date. We do NOT manufacture a cash
    percentage, normalize a raw UI total (which may exceed 100), aggregate
    duplicate share-class IDs, or convert a source percentage into dollars.
    """
    if (ledger.get("private_scope") is not True
            or ledger.get("captured_at") in {None, "UNKNOWN"}
            or ledger.get("source_type") not in {
                "PRIVATE_SCREENSHOT_TRANSCRIPTION",
                "PRIVATE_EXPORT_TRANSCRIPTION", "PRIVATE_USER_TABLE",
                "AUTHORIZED_BLOSSOM_TRANSCRIPTION",
            }):
        return None
    records = ledger.get("p_ledger_private")
    summary = ledger.get("displayed_weight_summary_private")
    missing = ledger.get("missing_or_qualified")
    if (not isinstance(records, list) or not records
            or not isinstance(summary, Mapping)
            or not isinstance(missing, list)
            or summary.get("visible_count") != len(records)
            or summary.get("position_row_count") != len(records)
            or summary.get("normalization") != "NONE_DISPLAYED_VALUES_UNCHANGED"
            or summary.get("denominator_verification") != "NOT_PERFORMED"):
        return None
    # Missing amounts, cash, FX and currency are precisely why this UI-only
    # fallback exists. Hidden positions, source access, timestamps and account
    # identity are never waived. Row-field qualification may be for money, but
    # the security and account fields must be independently visibly reported.
    allowed = {
        "ACCOUNT_CURRENCY_UNKNOWN", "CASH_NOT_VISIBLE_OR_UNQUANTIFIED",
        "COMMON_CURRENCY_BASIS_UNCONFIRMED",
    }
    if any(not isinstance(x, str) or (
            x not in allowed and not x.endswith(":FIELD_NOT_COMPARABLE_OR_NOT_VISIBLE"))
           for x in missing):
        return None
    values: dict[str, Decimal] = {}
    for row in records:
        if not isinstance(row, Mapping):
            return None
        security = row.get("security_id")
        flags = row.get("field_statuses")
        raw = row.get("displayed_weight_pct_private")
        if (not isinstance(security, str) or not security or security == "P-CASH"
                or security in values
                or row.get("account_scope") != ledger.get("account_scope")
                or not isinstance(flags, Mapping)
                or flags.get("security_id") != "VERIFIED_VISIBLE"
                or flags.get("account_scope") != "VERIFIED_VISIBLE"
                or row.get("displayed_weight_visibility") != "VERIFIED_VISIBLE"
                or not isinstance(raw, str)):
            return None
        try:
            pct = Decimal(raw)
        except (ValueError, ArithmeticError):
            return None
        if (not pct.is_finite() or not 0 <= pct <= 100
                or pct != pct.quantize(PCT)):
            return None
        values[security] = pct
    stated_sum = summary.get("displayed_weight_sum_pct")
    if (not isinstance(stated_sum, str)
            or stated_sum != f"{sum(values.values(), Decimal('0')):.2f}"):
        return None
    return values


def compare_private_portfolio_snapshots(
    *, analysis_id: str, analysis_as_of: str, prior_analysis_id: str,
    current_observation: Mapping[str, Any],
    prior_observation_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare only identical named account scope and currency, on user request.

    Prior inputs are independently reconstructed through the original M3
    visibility/cash/date guard. Neither prior nor current data is authenticated.
    A missing scope is UNAVAILABLE, never inferred from display-only weights.
    """
    if not isinstance(prior_observation_inputs, Mapping):
        raise ValueError("PRIOR_SNAPSHOT_INPUTS_REQUIRED")
    if not isinstance(current_observation, Mapping):
        raise ValueError("CURRENT_SNAPSHOT_OBSERVATION_REQUIRED")
    if (not isinstance(prior_analysis_id, str) or not prior_analysis_id.strip()
            or prior_analysis_id == analysis_id):
        raise ValueError("SNAPSHOT_PRIOR_ANALYSIS_ID_REQUIRED")
    if (current_observation.get("analysis_id") != analysis_id
            or current_observation.get("analysis_as_of") != analysis_as_of
            or current_observation.get("private_scope") is not True
            or current_observation.get("verification") !=
                "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"):
        raise ValueError("SNAPSHOT_CURRENT_ID_OR_AUTHORITY_INVALID")
    if (prior_observation_inputs.get("analysis_id") != prior_analysis_id
            or prior_observation_inputs.get("private_scope") is not True):
        raise ValueError("SNAPSHOT_PRIOR_ID_OR_SCOPE_INVALID")
    previous = prepare_observation_ledger(**dict(prior_observation_inputs))
    old_date = previous["observed_on"]
    new_date = current_observation["observed_on"]
    if not old_date < new_date <= analysis_as_of:
        raise ValueError("SNAPSHOT_DATES_NOT_STRICTLY_ORDERED")
    if (previous["account_scope"] != current_observation.get("account_scope")
            or previous["currency"] != current_observation.get("currency")):
        raise ValueError("SNAPSHOT_ACCOUNT_OR_CURRENCY_BASIS_CHANGED")
    if (previous["analysis_as_of"] > analysis_as_of
            or current_observation.get("currency") in {"UNKNOWN", "UNK", "XXX", "XTS", "TBD"}):
        raise ValueError("SNAPSHOT_ORIGINAL_CUTOFF_OR_CURRENCY_UNKNOWN")

    common = {
        "analysis_id": analysis_id,
        "analysis_as_of": analysis_as_of,
        "prior_analysis_id": prior_analysis_id,
        "prior_observed_on": old_date,
        "current_observed_on": new_date,
        "privacy": "PRIVATE_ONLY",
        "source_authentication": "NOT_PERFORMED",
        "performance_or_transaction_inference": "NONE",
        "storage": "NONE",
        "trading_authority": "NONE",
    }
    missing = [
        label for label, item in (
            ("PRIOR_SCOPE_INCOMPLETE", previous),
            ("CURRENT_SCOPE_INCOMPLETE", current_observation))
        if item.get("status") != COMPLETE or item.get("known_scope_weights_pct") is None
    ]
    if missing:
        # Separate *visually displayed* weight-change evidence is useful for
        # Blossom pages showing percentage but not cash/market-value amounts.
        # Compare ONLY identical visible security sets from the same claimed
        # complete named account. Never infer a missing line's weight as zero.
        older_ui = _caller_visible_ui_weights(previous)
        newer_ui = _caller_visible_ui_weights(current_observation)
        if (older_ui is not None and newer_ui is not None
                and set(older_ui) == set(newer_ui)):
            rows = []
            for security in sorted(older_ui):
                old_pct, new_pct = older_ui[security], newer_ui[security]
                rows.append({
                    "security_id_private": security,
                    "prior_weight_pct": f"{old_pct:.2f}",
                    "current_weight_pct": f"{new_pct:.2f}",
                    "weight_change_pp": f"{new_pct - old_pct:.2f}",
                    "presence": "CONTINUING",
                })
            return {
                **common,
                "status": "OBSERVED_UI_WEIGHT_CHANGE_ONLY_NO_MONETARY_DENOMINATOR",
                "reason_codes": ["MONETARY_DENOMINATOR_NOT_VERIFIED"],
                "rows_private": rows,
                "matched_instrument_count": len(rows),
                "newly_visible_count": 0,
                "no_longer_visible_count": 0,
                "largest_absolute_security_weight_shift_pp": (
                    f"{max(abs(newer_ui[k] - older_ui[k]) for k in older_ui):.2f}"),
                "cash_weight_change_pp": None,
            }
        return {
            **common, "status": "UNAVAILABLE_INCOMPLETE_SNAPSHOT_SCOPE",
            "reason_codes": missing,
            "rows_private": None,
            "matched_instrument_count": None,
            "newly_visible_count": None,
            "no_longer_visible_count": None,
            "largest_absolute_security_weight_shift_pp": None,
            "cash_weight_change_pp": None,
        }

    old_total = Decimal(previous["scope_total_base"])
    new_total = Decimal(current_observation["scope_total_base"])
    if old_total <= 0 or new_total <= 0:
        raise ValueError("SNAPSHOT_DENOMINATOR_INVALID")
    old_positions = _positions(previous)
    new_positions = _positions(current_observation)
    prior_cash = Decimal(previous["cash_record_private"]["amount_base"])
    current_cash = Decimal(current_observation["cash_record_private"]["amount_base"])
    if (sum(old_positions.values(), prior_cash) != old_total
            or sum(new_positions.values(), current_cash) != new_total):
        raise ValueError("SNAPSHOT_TOTAL_PARITY_INVALID")
    all_keys = sorted(set(old_positions) | set(new_positions))
    rows = []
    for security in all_keys:
        old_pct = _percent(old_positions.get(security, Decimal("0")), old_total)
        new_pct = _percent(new_positions.get(security, Decimal("0")), new_total)
        change = _percent(new_positions.get(security, Decimal("0")), new_total) - old_pct
        rows.append({
            "security_id_private": security,
            "prior_weight_pct": f"{old_pct:.2f}",
            "current_weight_pct": f"{new_pct:.2f}",
            "weight_change_pp": f"{change:.2f}",
            "presence": (
                "CONTINUING" if security in old_positions and security in new_positions
                else "NEWLY_VISIBLE" if security in new_positions else "NO_LONGER_VISIBLE"
            ),
        })
    return {
        **common, "status": "DESCRIPTIVE_SCOPED_WEIGHT_CHANGE_NOT_RETURN",
        "reason_codes": [],
        "rows_private": rows,
        "matched_instrument_count": sum(
            x["presence"] == "CONTINUING" for x in rows),
        "newly_visible_count": sum(
            x["presence"] == "NEWLY_VISIBLE" for x in rows),
        "no_longer_visible_count": sum(
            x["presence"] == "NO_LONGER_VISIBLE" for x in rows),
        "largest_absolute_security_weight_shift_pp": (
            f"{max((abs(Decimal(x['weight_change_pp'])) for x in rows), default=Decimal('0')):.2f}"),
        "cash_weight_change_pp": (
            f"{_percent(current_cash,new_total) - _percent(prior_cash,old_total):.2f}"),
    }
