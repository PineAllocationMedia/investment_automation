"""Gross-only, source-agnostic contribution arithmetic for supervised portfolio research.

This module does not propose allocations, fetch market data or calculate net costs.
Its inputs require a resolved same-currency, dated and complete *scoped* account.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Mapping

CENT = Decimal("0.01")
HUNDRED = Decimal("100")


def _decimal(value: str, label: str) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: exact decimal string required")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{label}: finite nonnegative decimal required")
    return number


def _money(value: str, label: str) -> Decimal:
    number = _decimal(value, label)
    if number != number.quantize(CENT):
        raise ValueError(f"{label}: at most two decimal places")
    return number


def project_gross_contribution(
    *,
    positions_base: Mapping[str, str],
    allocations_pct: Mapping[str, str],
    contribution_base: str,
    currency: str,
    as_of: str,
    scope_complete: bool,
    cash_accounted_for: bool,
    same_currency_basis_verified: bool,
    instrument_identity_verified: bool,
) -> dict:
    """Project a *user-supplied* 100%-allocated new contribution, gross of costs.

    Money inputs are account-base-currency values, not share counts or quotes.
    No missing position may be inferred to be zero; caller certifies scoped coverage.
    Returns UNAVAILABLE instead of calculating with uncertain input boundaries.
    """
    missing = [
        label for label, ready in (
            ("SCOPE_INCOMPLETE", scope_complete),
            ("CASH_UNKNOWN", cash_accounted_for),
            ("CURRENCY_BASIS_UNVERIFIED", same_currency_basis_verified),
            ("INSTRUMENT_IDENTITY_UNVERIFIED", instrument_identity_verified),
        ) if ready is not True
    ]
    if not as_of or not isinstance(as_of, str):
        missing.append("OBSERVATION_DATE_UNKNOWN")
    else:
        try:
            if date.fromisoformat(as_of).isoformat() != as_of:
                missing.append("OBSERVATION_DATE_INVALID")
        except ValueError:
            missing.append("OBSERVATION_DATE_INVALID")
    # A checked common-currency flag cannot turn UNKNOWN, a bare symbol, or
    # malformed text into an account-base monetary denomination. ISO-like
    # syntax is checked only; this does not authenticate the actual currency.
    base_currency = currency.strip().upper() if isinstance(currency, str) else ""
    if (len(base_currency) != 3 or not base_currency.isascii()
            or not base_currency.isalpha()):
        missing.append("ACCOUNT_CURRENCY_UNKNOWN")
    if missing:
        return {"status": "UNAVAILABLE", "reason_codes": missing}

    contribution = _money(contribution_base, "contribution_base")
    if contribution <= 0:
        raise ValueError("contribution_base: positive contribution required")
    if not positions_base or not allocations_pct:
        raise ValueError("positions and allocations must be supplied")
    for key in (*positions_base, *allocations_pct):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("instrument keys must be nonempty resolved identities")

    positions = {key: _money(value, f"position:{key}") for key, value in positions_base.items()}
    pct = {key: _decimal(value, f"allocation:{key}") for key, value in allocations_pct.items()}
    if any(value > HUNDRED for value in pct.values()) or sum(pct.values()) != HUNDRED:
        raise ValueError("allocations_pct must total exactly 100 percent")

    # Largest remainders conserve exact cents and are deterministic on key ties.
    ideals = {key: contribution * value / HUNDRED for key, value in pct.items()}
    increments = {key: amount.quantize(CENT, rounding=ROUND_DOWN) for key, amount in ideals.items()}
    remaining_cents = int((contribution - sum(increments.values())) / CENT)
    if remaining_cents < 0 or remaining_cents > len(increments):
        raise AssertionError("cent reconciliation invariant")
    rank = sorted(increments, key=lambda key: (-(ideals[key] - increments[key]), key))
    for key in rank[:remaining_cents]:
        increments[key] += CENT

    current_total = sum(positions.values())
    projected_total = current_total + contribution
    all_keys = sorted(set(positions) | set(increments))
    projected = {key: positions.get(key, Decimal("0")) + increments.get(key, Decimal("0")) for key in all_keys}
    if sum(projected.values()) != projected_total or sum(increments.values()) != contribution:
        raise AssertionError("portfolio conservation invariant")

    return {
        "status": "GROSS_PROJECTION_ONLY",
        "as_of": as_of,
        "currency": base_currency,
        "current_total": f"{current_total:.2f}",
        "contribution": f"{contribution:.2f}",
        "projected_total": f"{projected_total:.2f}",
        "allocations": {key: f"{increments[key]:.2f}" for key in sorted(increments)},
        "projected_positions": {key: f"{projected[key]:.2f}" for key in all_keys},
        "current_weights_pct": (
            {key: str(positions.get(key, Decimal('0')) * HUNDRED / current_total) for key in all_keys}
            if current_total > 0 else None
        ),
        "projected_weights_pct": {
            key: str(projected[key] * HUNDRED / projected_total) for key in all_keys
        },
        "net_execution_status": "UNAVAILABLE_COSTS_NOT_ASSESSED",
        "scope": "SUPPLIED_SCOPED_ACCOUNT_ONLY",
        "note": "Input allocations are provided by the user/analyst; no recommendation, price, FX, tax, fee or trade is produced.",
    }
