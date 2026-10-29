"""Shared, private M3 contribution arithmetic for IR+PI and PI-only CC routes.

All values are caller-supplied. No holdings authentication, quote retrieval,
investment proposal, model admission, archive, schedule, or trade occurs.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Mapping

from .contribution_math import project_gross_contribution
from .known_costs import tally_supplied_costs
from .funded_costs_reconciliation import reconcile_funded_contribution


def _largest_non_cash_security_pct(weights: Mapping[str, str] | None) -> str | None:
    """Largest *security line*, excluding cash, in a previously checked M3 scenario.

    This is not economic-issuer concentration or an investable limit. The
    existing contribution solver provides positive, finite weight strings.
    Cash remains in the original scoped denominator.
    """
    if weights is None:
        return None
    values = [Decimal(value) for security, value in weights.items()
              if security != "P-CASH" and Decimal(value) > 0]
    if not values:
        return None
    return f"{max(values).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def _scoped_cash_pct(weights: Mapping[str, str] | None) -> str | None:
    """Percent of the P-CASH line within the complete caller-supplied scope.

    Missing P-CASH means zero only after M3's complete and cash-accounted gross
    projection; incomplete source data never enter this calculation.
    """
    if weights is None:
        return None
    value = Decimal(weights.get("P-CASH", "0"))
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def prepare_new_capital_projection(
    *, analysis_id: str, analysis_as_of: str, portfolio_as_of: str,
    contribution_inputs: Mapping[str, Any],
    cost_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute one consistent private gross/cost/funded scenario and report seam.

    Reuse the existing deterministic M3 contracts. Caller assertions about
    portfolio coverage never become independently verified observations.
    """
    if not isinstance(contribution_inputs, Mapping):
        raise ValueError("contribution_inputs must be a mapping")
    if contribution_inputs.get("as_of") != portfolio_as_of:
        raise ValueError("Contribution input must use exact PI portfolio observation date")
    # One optional bounded set of alternative NEW-capital plans. All scenarios
    # reuse the exact same confirmed portfolio basis, date, currency and budget.
    # They never inherit baseline cost quotes or become proposed investments.
    base_inputs = dict(contribution_inputs)
    alternative_allocations = base_inputs.pop("alternative_allocations_pct", None)
    if alternative_allocations is not None and (
        not isinstance(alternative_allocations, list)
        or not 1 <= len(alternative_allocations) <= 3
        or any(not isinstance(item, Mapping) or not item
               for item in alternative_allocations)
    ):
        raise ValueError("ALTERNATIVE_CONTRIBUTION_SCENARIOS_INVALID")
    # Optional quotes must match the alternative scenario count and are
    # never substituted for the baseline's separately supplied cost schedule.
    if cost_inputs is not None and not isinstance(cost_inputs, Mapping):
        raise ValueError("cost_inputs must be a mapping")
    baseline_cost_inputs = dict(cost_inputs) if cost_inputs is not None else None
    alternative_cost_inputs = (baseline_cost_inputs.pop("alternative_cost_inputs", None)
                               if baseline_cost_inputs is not None else None)
    if alternative_cost_inputs is not None and (
        alternative_allocations is None
        or not isinstance(alternative_cost_inputs, list)
        or len(alternative_cost_inputs) != len(alternative_allocations)
        or any(not isinstance(q, Mapping) or not q for q in alternative_cost_inputs)
    ):
        raise ValueError("ALTERNATIVE_COST_QUOTES_MUST_MATCH_SCENARIOS")
    gross = project_gross_contribution(**base_inputs)
    notes = []
    if gross["status"] == "UNAVAILABLE":
        notes.append("Gross contribution projection unavailable: required scope flags were not established.")
    else:
        notes.append("Gross contribution math only; real account costs, taxes, FX and execution not assessed.")

    costs = None
    funded = None
    if cost_inputs is not None:
        if baseline_cost_inputs.get("analysis_as_of") != analysis_as_of:
            raise ValueError("cost_inputs analysis cutoff must match request as_of")
        costs = tally_supplied_costs(gross_projection=gross, **baseline_cost_inputs)
        if costs["status"] != "SUPPLIED_COST_TALLY_ONLY":
            notes.append("After-cost analysis unavailable: incomplete or infeasible supplied purchase costs.")
        else:
            notes.append("Supplied-cost tally only; quotes, taxes and net execution not certified.")
            if costs.get("gross_allocation_funding_conflict"):
                notes.append("Gross allocation uses the full contribution; deducting fees from that same contribution needs a revised plan.")
        funded = reconcile_funded_contribution(
            contribution_inputs=base_inputs, gross_projection=gross,
            cost_tally=costs,
        )
        if funded["status"] == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED":
            notes.append("Conditional new-capital budget reconciled to stated costs; order-size-dependent fees and real execution must be rechecked. See private annex.")
        else:
            notes.append("Funded new-capital budget unavailable; missing or incompatible cost/funding data. Gross projection remains separately labeled.")

    # Descriptive concentration sensitivity of the already supplied hypothetical
    # new-cash destinations. No new allocation choice, security identification,
    # issuer look-through or brokerage quote is introduced by this calculation.
    concentration = None
    if gross["status"] == "GROSS_PROJECTION_ONLY":
        funded_ok = (funded is not None and funded.get("status") ==
                     "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")
        concentration = {
            "status": ("GROSS_AND_CONDITIONAL_FUNDED_SCOPED_SENSITIVITY"
                       if funded_ok else "GROSS_ONLY_SCOPED_SENSITIVITY"),
            "before_largest_non_cash_security_pct": _largest_non_cash_security_pct(
                gross["current_weights_pct"]),
            "gross_after_largest_non_cash_security_pct": _largest_non_cash_security_pct(
                gross["projected_weights_pct"]),
            "conditional_funded_after_largest_non_cash_security_pct": (
                _largest_non_cash_security_pct(
                    funded["conditional_projection_private"]["projected_weights_pct"])
                if funded_ok else None),
            "before_scoped_cash_pct": _scoped_cash_pct(
                gross["current_weights_pct"]),
            "gross_after_scoped_cash_pct": _scoped_cash_pct(
                gross["projected_weights_pct"]),
            "conditional_funded_after_scoped_cash_pct": (
                _scoped_cash_pct(
                    funded["conditional_projection_private"]["projected_weights_pct"])
                if funded_ok else None),
            "authority": "DESCRIPTIVE_CALLER_SUPPLIED_NO_PORTFOLIO_POLICY_OR_EXECUTION",
        }

    alternatives_private = None
    alternative_cost_summary = None
    alternative_cost_details = None
    if alternative_allocations is not None:
        if gross["status"] != "GROSS_PROJECTION_ONLY":
            notes.append("Alternative gross plans unavailable: the original scoped portfolio basis is incomplete.")
        else:
            alternatives = []
            cost_views = []
            alternative_cost_details = [] if alternative_cost_inputs is not None else None
            for i, allocation in enumerate(alternative_allocations, start=1):
                scenario_inputs = dict(base_inputs)
                scenario_inputs["allocations_pct"] = dict(allocation)
                projection = project_gross_contribution(**scenario_inputs)
                if projection["status"] != "GROSS_PROJECTION_ONLY":
                    raise ValueError("ALTERNATIVE_CONTRIBUTION_BASIS_UNAVAILABLE")
                alternatives.append({
                    "scenario_index": i,
                    "gross_after_largest_non_cash_security_pct":
                        _largest_non_cash_security_pct(projection["projected_weights_pct"]),
                    "gross_after_scoped_cash_pct":
                        _scoped_cash_pct(projection["projected_weights_pct"]),
                })
                if alternative_cost_inputs is not None:
                    # Exact, independent, destination-specific cost sources.
                    # Never carry the baseline quote to another gross scenario.
                    quote = alternative_cost_inputs[i - 1]
                    if (set(quote) != {
                            "charges_by_destination", "cost_currency",
                            "cost_quote_as_of", "analysis_as_of", "funding"}
                            or quote["analysis_as_of"] != analysis_as_of):
                        raise ValueError("ALTERNATIVE_COST_QUOTE_SCHEMA_OR_DATE")
                    alt_tally = tally_supplied_costs(
                        gross_projection=projection, **dict(quote))
                    alt_funded = reconcile_funded_contribution(
                        contribution_inputs=scenario_inputs,
                        gross_projection=projection, cost_tally=alt_tally)
                    funded_ok = (alt_funded["status"] ==
                                 "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")
                    # Compare burden ONLY for complete independently quoted
                    # fixed fees on the identical funding/date/currency basis.
                    # FROM_CONTRIBUTION preserves the same total NEW cash
                    # denominator; external cash does not, so do not compare.
                    comparable = (
                        funded_ok and funded is not None
                        and funded.get("status") ==
                            "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
                        and funded.get("funding") == "FROM_CONTRIBUTION"
                        and alt_funded.get("funding") == "FROM_CONTRIBUTION"
                        and costs is not None
                        and costs.get("cost_quote_as_of") ==
                            alt_tally.get("cost_quote_as_of")
                        and costs.get("currency") == alt_tally.get("currency")
                    )
                    burden_delta = (
                        f"{Decimal(alt_funded['one_time_supplied_cost_share_pct']) - Decimal(funded['one_time_supplied_cost_share_pct']):+.4f}"
                        if comparable else None
                    )
                    cost_views.append({
                        "scenario_index": i,
                        "cost_burden_delta_vs_baseline_pp": burden_delta,
                        "cost_burden_comparison_basis": (
                            "MATCHED_FROM_CONTRIBUTION_AND_QUOTE_DATE_ONLY"
                            if comparable else "NOT_COMPARABLE"), 
                        "cost_status": alt_tally["status"],
                        "funded_status": alt_funded["status"],
                        "one_time_supplied_cost_share_pct": (
                            alt_funded["one_time_supplied_cost_share_pct"] if funded_ok else None),
                        "conditional_funded_after_largest_non_cash_security_pct": (
                            _largest_non_cash_security_pct(
                                alt_funded["conditional_projection_private"]["projected_weights_pct"])
                            if funded_ok else None),
                        "conditional_funded_after_scoped_cash_pct": (
                            _scoped_cash_pct(
                                alt_funded["conditional_projection_private"]["projected_weights_pct"])
                            if funded_ok else None),
                    })
                    alternative_cost_details.append({
                        "scenario_index": i,
                        "gross_projection_private": projection,
                        "supplied_costs_private": alt_tally,
                        "funded_contribution_private": alt_funded,
                    })
            if alternative_cost_inputs is not None:
                alternative_cost_summary = {
                    "status": "SEPARATELY_QUOTED_CONDITIONAL_ALTERNATIVES",
                    "scenarios": cost_views,
                    "authority": "CALLER_SUPPLIED_FIXED_COSTS_NOT_NET_RETURN_OR_EXECUTION",
                }
            alternatives_private = {
                "status": "GROSS_ALTERNATIVES_ONLY_NOT_NET",
                "scenarios": alternatives,
                "authority": "CALLER_SUPPLIED_HYPOTHETICAL_NOT_PORTFOLIO_POLICY",
            }
            notes.append(
                "Alternative contribution destinations are separate GROSS hypotheticals "
                "on the same scoped basis. Baseline fee quotes and conditional funding "
                "cannot be reused; no alternative net comparison or selection is certified."
            )
            if alternative_cost_summary is not None:
                notes.append(
                    "Alternative fees are separately caller-supplied, each with its "
                    "own fixed-cost funding check; incomplete quote components remain "
                    "unavailable. Net returns, optimal allocation, brokerage requotes "
                    "and execution are NOT established."
                )

    # Display only NEW-capital percentages and bounded aggregate sensitivity,
    # never balances, cost quotes, or projected order amounts in the report.
    summary = {
        "analysis_id": analysis_id,
        "portfolio_as_of": portfolio_as_of,
        "gross_status": gross["status"],
        "gross_unavailable_reason_codes": (
            list(gross["reason_codes"]) if gross["status"] == "UNAVAILABLE" else None),
        "allocations_pct": (dict(contribution_inputs["allocations_pct"])
                            if gross["status"] == "GROSS_PROJECTION_ONLY" else None),
        "cost_status": costs["status"] if costs is not None else "NOT_SUPPLIED",
        "funded_status": funded["status"] if funded is not None else "NOT_ASSESSED",
        "one_time_supplied_cost_share_pct": (
            funded["one_time_supplied_cost_share_pct"]
            if funded is not None and funded["status"] ==
                "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED" else None),
        "largest_security_line_sensitivity_private": concentration,
        "gross_alternatives_private": alternatives_private,
        "conditional_alternative_costs_private": alternative_cost_summary,
        "source_authentication": "NOT_PERFORMED",
    }
    return {
        "gross_contribution_private": gross,
        "supplied_costs_private": costs,
        "funded_contribution_private": funded,
        "alternative_cost_details_private": alternative_cost_details,
        "report_summary_private": summary,
        "limitations": notes,
        "execution_status": "UNAVAILABLE_NOT_EXECUTION_CERTIFIED",
        "storage": "NONE",
    }
