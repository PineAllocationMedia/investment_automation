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
