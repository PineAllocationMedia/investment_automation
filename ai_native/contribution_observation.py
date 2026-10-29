"""Reconcile a private, dated visible P-ledger with new-capital arithmetic.

This consumes only the already validated, caller-reported M3 ledger. No
Blossom/broker authentication, FX conversion, policy choice or trade occurs.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def _money(value: Any) -> Decimal:
    """Compare exact reported base-currency amounts; no float conversion."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION") from exc
    if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal("0.01")):
        raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION")
    return amount


def reconcile_observed_contribution_basis(
    observation: Mapping[str, Any],
    contribution_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Copy/reconcile an explicitly complete P-ledger into contribution inputs.

    If the caller supplies positions_base, all observed securities must match
    by exact economic security ID and summed base-currency market value, and
    nonzero scoped cash must be present as P-CASH. When positions_base is
    omitted, derive it from the already validated private ledger, including
    nonzero cash. This never upgrades caller visibility to broker proof.
    """
    if not isinstance(contribution_inputs, Mapping):
        raise ValueError("contribution_inputs: mapping required")
    prepared = dict(contribution_inputs)
    if (prepared.get("scope_complete") is True
            and observation.get("known_scope_weights_pct") is None):
        raise ValueError("PI_CONTRIBUTION_SCOPE_CONFLICTS_WITH_OBSERVATION")
    if (prepared.get("same_currency_basis_verified") is True
            and (not isinstance(prepared.get("currency"), str)
                 or prepared["currency"].strip().upper() != observation.get("currency"))):
        raise ValueError("PI_CONTRIBUTION_CURRENCY_CONFLICTS_WITH_OBSERVATION")

    required_flags = ("scope_complete", "cash_accounted_for",
                      "same_currency_basis_verified", "instrument_identity_verified")
    if (observation.get("known_scope_weights_pct") is None
            or any(prepared.get(key) is not True for key in required_flags)
            or prepared.get("as_of") != observation.get("observed_on")):
        # Keep existing UNAVAILABLE and date-mismatch semantics. Do not
        # derive a complete position base from missing/uncertain observations.
        return prepared

    values: dict[str, Decimal] = {}
    for row in observation["p_ledger_private"]:
        security = row["security_id"]
        if security == "P-CASH":
            raise ValueError("PI_CONTRIBUTION_RESERVED_CASH_ID_COLLISION")
        values[security] = values.get(security, Decimal("0")) + _money(
            row["market_value_base"])
    cash = _money(observation["cash_record_private"]["amount_base"])
    if cash:
        values["P-CASH"] = cash
    expected_total = sum(values.values(), Decimal("0"))
    if expected_total != _money(observation["scope_total_base"]):
        raise ValueError("PI_CONTRIBUTION_OBSERVATION_TOTAL_MISMATCH")

    if "positions_base" not in prepared:
        prepared["positions_base"] = {
            key: f"{amount:.2f}" for key, amount in sorted(values.items())
        }
        return prepared

    supplied = prepared["positions_base"]
    if not isinstance(supplied, Mapping):
        raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION")
    parsed: dict[str, Decimal] = {}
    for key, amount in supplied.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION")
        parsed[key] = _money(amount)
    if cash == 0 and parsed.get("P-CASH") == 0:
        parsed.pop("P-CASH")
    if cash and "P-CASH" not in parsed:
        raise ValueError("PI_CONTRIBUTION_CASH_MISSING_FROM_SCOPED_BASIS")
    if parsed != values:
        raise ValueError("PI_CONTRIBUTION_POSITIONS_CONFLICT_WITH_OBSERVATION")
    return prepared
