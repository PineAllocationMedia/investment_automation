"""Semantic-neutral pure annual cash-flow IRR mathematics.

This module knows nothing about companies, ETFs, accounting metrics, evidence,
policy, recommendations, or portfolios.  It solves one positive initial value
against nonnegative year-end cash flows and a positive terminal value.
"""
from __future__ import annotations

import math


DEFAULT_MAX_ITERATIONS = 256
DEFAULT_ROOT_TOLERANCE = 1e-14
DEFAULT_RESIDUAL_TOLERANCE = 1e-10


class AnnualCashFlowIRRError(ValueError):
    """The annual cash-flow IRR cannot be represented faithfully in binary64."""


def solve_annual_cashflow_irr(
    initial_value: float,
    annual_cashflows: tuple[float, ...],
    terminal_value: float,
    *,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    root_tolerance: float = DEFAULT_ROOT_TOLERANCE,
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE,
) -> float:
    """Return the unique annualized IRR for positive-terminal cash flows.

    Callers own economic validation.  This boundary still rejects values that
    would violate the numerical domain, so it can be reused without silently
    manufacturing a root.
    """
    if type(initial_value) not in (int, float) or not math.isfinite(initial_value) \
            or initial_value <= 0:
        raise AnnualCashFlowIRRError("Initial value must be positive and finite")
    if type(annual_cashflows) is not tuple or not annual_cashflows:
        raise AnnualCashFlowIRRError("At least one annual cash flow is required")
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0
           for value in annual_cashflows):
        raise AnnualCashFlowIRRError(
            "Annual cash flows must be nonnegative and finite")
    if type(terminal_value) not in (int, float) \
            or not math.isfinite(terminal_value) or terminal_value <= 0:
        raise AnnualCashFlowIRRError("Terminal value must be positive and finite")
    if type(max_iterations) is not int or max_iterations < 0:
        raise AnnualCashFlowIRRError("max_iterations must be a nonnegative integer")

    horizon = len(annual_cashflows)
    cash = [(year, math.log(value))
            for year, value in enumerate(annual_cashflows, 1) if value > 0]
    cash.append((horizon, math.log(terminal_value)))
    log_initial = math.log(initial_value)

    def residual(log_gross: float) -> float:
        terms = [log_cash - year * log_gross for year, log_cash in cash]
        peak = max(terms)
        return (peak
                + math.log(math.fsum(math.exp(term - peak) for term in terms))
                - log_initial)

    lower = math.log1p(math.nextafter(-1.0, 0.0))
    upper = math.log(float.fromhex("0x1.fffffffffffffp+1023"))
    if residual(lower) < 0 or residual(upper) > 0:
        raise AnnualCashFlowIRRError(
            "Root is outside representable annual-return range")
    for _ in range(max_iterations):
        midpoint = lower + (upper - lower) / 2
        error = residual(midpoint)
        if error > 0:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= root_tolerance * max(1.0, abs(midpoint)):
            try:
                result = math.expm1(midpoint)
            except OverflowError as exc:
                raise AnnualCashFlowIRRError(
                    "Unrepresentable annualized return") from exc
            if (not math.isfinite(result) or result <= -1
                    or abs(residual(math.log1p(result))) > residual_tolerance):
                raise AnnualCashFlowIRRError(
                    "Returned root fails representability/NPV residual check")
            return result
    raise AnnualCashFlowIRRError("IRR bisection did not converge")
