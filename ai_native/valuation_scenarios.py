"""Deterministic, private M2 scenario return arithmetic on caller-supplied assumptions.

No financial sourcing, normalization, FX, price discovery, probability model,
benchmark forecast, tax/account economics, trade or investment admission.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping

METHODS = frozenset({"NORMALIZED_MULTIPLE", "OWNER_CASH", "MID_CYCLE",
                     "PRODUCT_RUNWAY", "SECTOR_NAV", "OTHER_EXPLICIT"})
BASIS = frozenset({"PAM_ASSUMPTION", "SOURCE_FACT", "THIRD_PARTY_ESTIMATE"})
SCENARIOS = ("BEAR", "BASE", "BULL")


def _text(raw: Any, label: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label}: explicit nonempty text required")
    return raw.strip()


def _date(raw: Any, label: str) -> date:
    value = _text(raw, label)
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid ISO date") from exc
    if result.isoformat() != value:
        raise ValueError(f"{label}: canonical ISO date required")
    return result


def _decimal(raw: Any, label: str, *, strictly_positive: bool = False) -> Decimal:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label}: explicit decimal string required")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: invalid decimal") from exc
    if not value.is_finite() or value < 0 or (strictly_positive and value == 0):
        raise ValueError(f"{label}: finite {'positive' if strictly_positive else 'nonnegative'} number required")
    # Bound extreme exponents to prevent pathological IRR/Decimal work.
    if value and not (-12 <= value.adjusted() <= 15):
        raise ValueError(f"{label}: decimal magnitude outside supported arithmetic range")
    return value


def _irr(p0: Decimal, amounts: list[Decimal]) -> Decimal:
    """Year-end payment IRR; unique root when any future payment is positive."""
    with localcontext() as ctx:
        ctx.prec = 44
        if all(v == 0 for v in amounts):
            return Decimal("-1")

        def present(x: Decimal) -> Decimal:
            cumulative = Decimal(0)
            divisor = Decimal(1)
            for amount in amounts:
                divisor *= x
                cumulative += amount / divisor
            return cumulative

        lo = Decimal("0.000000000000000001")  # x = 1 + annual IRR
        hi = Decimal(2)
        for _ in range(96):
            if present(hi) <= p0:
                break
            hi *= 2
        else:
            raise ValueError("IRR_BRACKET_UNAVAILABLE")
        for _ in range(164):
            mid = (lo + hi) / 2
            if present(mid) > p0:
                lo = mid
            else:
                hi = mid
        return ((lo + hi) / 2) - 1


def evaluate_valuation_scenarios(
    *, analysis_id: str, analysis_as_of: str, security_id: str, currency: str,
    quoted_at: str, quote_source_ref: str, price_per_share: str,
    horizon_years: int, security_basis_confirmed_by_caller: bool,
    currency_basis_confirmed_by_caller: bool,
    scenarios: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Return conditional per-share scenario returns, never probabilistic ER.

    Terminal per-share values are ALREADY researched and caller-supplied;
    this arithmetic must not be mistaken for a normalized valuation model.
    Distributions=None means UNKNOWN, not zero; explicit year-end distribution
    schedules require evidence locators for every year, including zero amounts.
    """
    aid = _text(analysis_id, "analysis_id")
    instrument = _text(security_id, "security_id")
    unit = _text(currency, "currency").upper()
    if len(unit) != 3 or not unit.isalpha():
        raise ValueError("currency: three letters required")
    cutoff, quote_date = _date(analysis_as_of, "analysis_as_of"), _date(quoted_at, "quoted_at")
    if quote_date > cutoff:
        raise ValueError("QUOTE_AFTER_ANALYSIS_CUTOFF")
    quote_ref = _text(quote_source_ref, "quote_source_ref")
    price = _decimal(price_per_share, "price_per_share", strictly_positive=True)
    if type(horizon_years) is not int or not (1 <= horizon_years <= 30):
        raise ValueError("horizon_years: explicit integer in 1..30 required")
    for name, supplied in (("security_basis_confirmed_by_caller", security_basis_confirmed_by_caller),
                           ("currency_basis_confirmed_by_caller", currency_basis_confirmed_by_caller)):
        if type(supplied) is not bool:
            raise ValueError(f"{name}: explicit boolean required")
    if not isinstance(scenarios, Mapping) or set(scenarios) != set(SCENARIOS):
        raise ValueError("EXACT_BEAR_BASE_BULL_REQUIRED")

    unsupported = []
    if not security_basis_confirmed_by_caller:
        unsupported.append("SECURITY_SHARE_CLASS_OR_CORPORATE_ACTION_BASIS_UNCONFIRMED")
    if not currency_basis_confirmed_by_caller:
        unsupported.append("CURRENCY_OR_FX_BASIS_UNCONFIRMED")
    output = {}
    for name in SCENARIOS:
        row = scenarios[name]
        if not isinstance(row, Mapping):
            raise ValueError(f"{name}: mapping required")
        method = _text(row.get("valuation_method"), f"{name}.valuation_method")
        if method not in METHODS:
            raise ValueError(f"{name}: unsupported valuation_method")
        classification = _text(row.get("assumption_basis"), f"{name}.assumption_basis")
        if classification not in BASIS:
            raise ValueError(f"{name}: unsupported assumption_basis")
        rationale = _text(row.get("rationale_ref"), f"{name}.rationale_ref")
        terminal = _decimal(row.get("terminal_price_per_share"), f"{name}.terminal_price_per_share")
        terminal_ref = _text(row.get("terminal_value_ref"), f"{name}.terminal_value_ref")
        schedule = row.get("annual_distributions_per_share")
        reasons = list(unsupported)
        payments = None
        if schedule is None:
            reasons.append("DISTRIBUTIONS_UNKNOWN_PRICE_RETURN_ONLY")
        else:
            if not isinstance(schedule, list) or len(schedule) != horizon_years:
                raise ValueError(f"{name}: exactly one explicit year-end distribution per horizon year required")
            payments = []
            for idx, payment in enumerate(schedule):
                if not isinstance(payment, Mapping):
                    raise ValueError(f"{name}: distribution[{idx}] mapping required")
                payments.append(_decimal(payment.get("amount_per_share"), f"{name}:distribution[{idx}]"))
                _text(payment.get("source_ref"), f"{name}:distribution[{idx}].source_ref")
        result = {
            "valuation_method": method, "assumption_basis": classification,
            "rationale_ref": rationale, "terminal_value_ref": terminal_ref,
            "terminal_price_per_share": str(terminal),
            "annual_distributions_status": "UNKNOWN" if payments is None else "EXPLICITLY_SUPPLIED",
            "scenario_return_pct_annual": None, "return_measure": "UNAVAILABLE",
            "reason_codes": sorted(set(reasons)),
            "assumption_validation": "NOT_PERFORMED",
        }
        if not unsupported:
            if payments is None:
                with localcontext() as ctx:
                    ctx.prec = 44
                    return_fraction = ((terminal / price) ** (Decimal(1) / Decimal(horizon_years)) - 1) if terminal else Decimal("-1")
                result["return_measure"] = "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN"
            else:
                cashflows = list(payments)
                cashflows[-1] += terminal
                return_fraction = _irr(price, cashflows)
                result["return_measure"] = "YEAR_END_CASHFLOW_IRR_CONDITIONAL"
            result["scenario_return_pct_annual"] = str((return_fraction * Decimal(100)).quantize(Decimal("0.01")))
        output[name] = result
    return {
        "status": "CONDITIONAL_SCENARIO_ARITHMETIC_ONLY" if not unsupported else "UNAVAILABLE_INCOMPATIBLE_BASIS",
        "analysis_id": aid, "analysis_as_of": analysis_as_of,
        "security_id": instrument, "currency": unit, "quoted_at": quoted_at,
        "quote_source_ref": quote_ref, "price_per_share": str(price),
        "horizon_years": horizon_years, "scenarios_private": output,
        "expected_return_status": "NOT_ESTABLISHED_NO_PROBABILITIES_OR_ASSUMPTION_CERTIFICATION",
        "benchmark_expected_return_status": "VFV_ER_UNAVAILABLE_UNLESS_SEPARATELY_EVIDENCED",
        "trade_or_portfolio_authority": "NONE", "source_authentication": "NOT_PERFORMED",
        "calculation_scope": "CURRENT_SUPPLIED_INPUTS_ONLY_NO_PIT",
    }
