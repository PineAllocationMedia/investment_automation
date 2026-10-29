"""Shared, private M3 contribution arithmetic for IR+PI and PI-only CC routes.

All values are caller-supplied. No holdings authentication, quote retrieval,
investment proposal, model admission, archive, schedule, or trade occurs.
"""
from __future__ import annotations

from typing import Any, Mapping

from .contribution_math import project_gross_contribution
from .known_costs import tally_supplied_costs
from .funded_costs_reconciliation import reconcile_funded_contribution


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
    gross = project_gross_contribution(**contribution_inputs)
    notes = []
    if gross["status"] == "UNAVAILABLE":
        notes.append("Gross contribution projection unavailable: required scope flags were not established.")
    else:
        notes.append("Gross contribution math only; real account costs, taxes, FX and execution not assessed.")

    costs = None
    funded = None
    if cost_inputs is not None:
        if not isinstance(cost_inputs, Mapping):
            raise ValueError("cost_inputs must be a mapping")
        if cost_inputs.get("analysis_as_of") != analysis_as_of:
            raise ValueError("cost_inputs analysis cutoff must match request as_of")
        costs = tally_supplied_costs(gross_projection=gross, **cost_inputs)
        if costs["status"] != "SUPPLIED_COST_TALLY_ONLY":
            notes.append("After-cost analysis unavailable: incomplete or infeasible supplied purchase costs.")
        else:
            notes.append("Supplied-cost tally only; quotes, taxes and net execution not certified.")
            if costs.get("gross_allocation_funding_conflict"):
                notes.append("Gross allocation uses the full contribution; deducting fees from that same contribution needs a revised plan.")
        funded = reconcile_funded_contribution(
            contribution_inputs=contribution_inputs, gross_projection=gross,
            cost_tally=costs,
        )
        if funded["status"] == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED":
            notes.append("Conditional new-capital budget reconciled to stated costs; order-size-dependent fees and real execution must be rechecked. See private annex.")
        else:
            notes.append("Funded new-capital budget unavailable; missing or incompatible cost/funding data. Gross projection remains separately labeled.")

    # Display only NEW-capital percentages, never balances, cost quotes, or
    # projected order amounts in the report or public memory.
    summary = {
        "analysis_id": analysis_id,
        "portfolio_as_of": portfolio_as_of,
        "gross_status": gross["status"],
        "allocations_pct": (dict(contribution_inputs["allocations_pct"])
                            if gross["status"] == "GROSS_PROJECTION_ONLY" else None),
        "cost_status": costs["status"] if costs is not None else "NOT_SUPPLIED",
        "funded_status": funded["status"] if funded is not None else "NOT_ASSESSED",
        "one_time_supplied_cost_share_pct": (
            funded["one_time_supplied_cost_share_pct"]
            if funded is not None and funded["status"] ==
                "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED" else None),
        "source_authentication": "NOT_PERFORMED",
    }
    return {
        "gross_contribution_private": gross,
        "supplied_costs_private": costs,
        "funded_contribution_private": funded,
        "report_summary_private": summary,
        "limitations": notes,
        "execution_status": "UNAVAILABLE_NOT_EXECUTION_CERTIFIED",
        "storage": "NONE",
    }
