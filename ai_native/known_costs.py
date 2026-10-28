"""Conservative, supplied-input cost tally for R1 contribution scenarios.

No quotes, source authentication, tax advice, net positions, optimization or trade.
All charges are account-base-currency amounts supplied with a source locator.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

COST_TYPES = ("commission", "bid_ask_spread", "fx_conversion", "purchase_tax", "other_fees")
FUNDING = frozenset({"FROM_CONTRIBUTION", "EXTERNAL_CASH", "UNKNOWN"})
CENT = Decimal("0.01")


def _money(raw: Any, label: str) -> Decimal:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label}: explicit decimal string required")
    try:
        num = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if not num.is_finite() or num < 0 or num != num.quantize(CENT):
        raise ValueError(f"{label}: finite nonnegative amount with <=2 decimals required")
    return num


def _date(raw: Any, label: str) -> date:
    if not isinstance(raw, str):
        raise ValueError(f"{label}: YYYY-MM-DD required")
    try:
        d = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid date") from exc
    if d.isoformat() != raw:
        raise ValueError(f"{label}: canonical YYYY-MM-DD required")
    return d


def tally_supplied_costs(
    *,
    gross_projection: Mapping[str, Any],
    charges_by_destination: Mapping[str, Mapping[str, Mapping[str, str]]],
    cost_currency: str,
    cost_quote_as_of: str,
    analysis_as_of: str,
    funding: str,
) -> dict[str, Any]:
    """Tally known supplied purchase costs without inventing unavailable charges.

    Every nonzero gross destination requires five explicitly sourced cost entries,
    including any *supported* 0.00. Missing entries cannot be inferred as zero.
    Costs are not proof of executable broker quotes, prices, rates or tax treatment.
    """
    if not isinstance(gross_projection, Mapping):
        raise ValueError("gross_projection: mapping required")
    if gross_projection.get("status") != "GROSS_PROJECTION_ONLY":
        return {"status": "UNAVAILABLE_GROSS_PROJECTION", "net_economics_status": "UNAVAILABLE"}
    if not isinstance(cost_currency, str) or not cost_currency.strip():
        raise ValueError("cost_currency: explicit account-base currency required")
    currency = gross_projection.get("currency")
    if not isinstance(currency, str) or cost_currency.strip().upper() != currency:
        raise ValueError("CURRENCY_MISMATCH: charges must be in gross projection account currency")
    quote_date = _date(cost_quote_as_of, "cost_quote_as_of")
    if quote_date > _date(analysis_as_of, "analysis_as_of"):
        raise ValueError("FUTURE_COST_QUOTE: later than analysis cutoff")
    if funding not in FUNDING:
        raise ValueError("funding: FROM_CONTRIBUTION, EXTERNAL_CASH or UNKNOWN required")
    allocations = gross_projection.get("allocations")
    if not isinstance(allocations, Mapping) or not isinstance(charges_by_destination, Mapping):
        raise ValueError("gross allocations and charges must be mappings")
    active = {key for key, amount in allocations.items() if _money(amount, f"allocation:{key}") > 0}
    if set(charges_by_destination) != active:
        raise ValueError("DESTINATION_MISMATCH: charges must cover exactly positive gross destinations")
    known = Decimal("0.00")
    missing = []
    source_refs = []
    for dest in sorted(active):
        charges = charges_by_destination[dest]
        if not isinstance(charges, Mapping):
            raise ValueError(f"charges:{dest}: mapping required")
        if set(charges) - set(COST_TYPES):
            raise ValueError(f"charges:{dest}: unexpected cost component")
        for kind in COST_TYPES:
            row = charges.get(kind)
            if row is None:
                missing.append(f"{dest}:{kind}")
                continue
            if not isinstance(row, Mapping):
                raise ValueError(f"charges:{dest}:{kind}: mapping required")
            amount = row.get("amount_base")
            if amount is None:
                missing.append(f"{dest}:{kind}")
                continue
            value = _money(amount, f"charges:{dest}:{kind}")
            source = row.get("source_ref")
            if not isinstance(source, str) or not source.strip():
                missing.append(f"{dest}:{kind}:SOURCE_NOT_SUPPLIED")
                continue
            known += value
            source_refs.append({"destination": dest, "component": kind, "source_ref": source.strip()})
    result = {
        "currency": currency,
        "cost_quote_as_of": cost_quote_as_of,
        "analysis_as_of": analysis_as_of,
        "funding": funding,
        "known_cost_subtotal_base": f"{known:.2f}",
        "missing_components": missing,
        "source_references_private": source_refs,
        "net_economics_status": "UNAVAILABLE_NOT_EXECUTION_CERTIFIED",
        "gross_positions_unchanged": True,
        "scope": "PRIVATE_SCOPED_SUPPLIED_INPUTS_ONLY",
    }
    if missing:
        return {"status": "INCOMPLETE_COST_INPUTS", **result}
    contribution = _money(gross_projection.get("contribution"), "gross.contribution")
    result["total_supplied_costs_base"] = f"{known:.2f}"
    if funding == "FROM_CONTRIBUTION":
        if known >= contribution:
            return {"status": "UNAVAILABLE_COSTS_EXCEED_CONTRIBUTION", **result}
        result["maximum_remaining_contribution_budget_base"] = f"{contribution - known:.2f}"
        result["gross_allocation_funding_conflict"] = known > 0
    elif funding == "EXTERNAL_CASH":
        result["additional_external_cash_required_base"] = f"{known:.2f}"
    return {"status": "SUPPLIED_COST_TALLY_ONLY", **result}
