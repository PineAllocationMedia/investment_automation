"""Non-authorizing R1 scenario sensitivity on caller-supplied displayed weights.

This is *not* historical calibration, a certified portfolio, a drawdown forecast,
an allocation recommendation, or a policy approval. No sources are fetched.
Unlike the legacy V1 stock-only stress engine, every scenario shock is supplied
explicitly and unknown coverage stays unknown.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .strategy_authority import R1_MODES

FUNCTIONS = frozenset({
    "GROWTH", "DEFLATION_DURATION", "INFLATION_MONETARY",
    "LIQUIDITY_SHORT_DURATION", "UNCLASSIFIED",
})
TWO = Decimal("0.01")
HUNDRED = Decimal("100")


def _text(raw: Any, field: str) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 256:
        raise ValueError(f"{field}: nonempty bounded text required")
    return raw.strip()


def _date(raw: Any, field: str) -> date:
    value = _text(raw, field)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field}: ISO date required") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field}: canonical ISO date required")
    return parsed


def _number(raw: Any, field: str, *, minimum: Decimal, maximum: Decimal) -> Decimal:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{field}: decimal string required")
    try:
        result = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError(f"{field}: invalid decimal") from exc
    if not result.is_finite() or not minimum <= result <= maximum:
        raise ValueError(f"{field}: finite in-bounds decimal required")
    if result.as_tuple().exponent < -4:
        raise ValueError(f"{field}: at most four decimal places")
    return result


def _pct(value: Decimal) -> str:
    return str(value.quantize(TWO))


def evaluate_scenario_weight_sensitivity(
    *, analysis_id: str, analysis_as_of: str, strategy_id: str,
    denominator_evidence: str, positions: list[Mapping[str, Any]],
    scenarios: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Calculate illustrative scenario percent-point contributions, never advice.

    denominator_evidence is a *caller report*, not independently verified.
    A complete 100% displayed view is NOT proof of a complete brokerage account.
    Partial positions/shocks yield contributions only, not a portfolio return.
    """
    aid = _text(analysis_id, "analysis_id")
    cutoff = _date(analysis_as_of, "analysis_as_of")
    mode = _text(strategy_id, "strategy_id").lower()
    if mode not in R1_MODES:
        raise ValueError("R1_MODE_NOT_SELECTED")
    if denominator_evidence not in {
        "DISPLAYED_VIEW_DENOMINATOR_CALLER_ATTESTED", "UNKNOWN",
    }:
        raise ValueError("DENOMINATOR_EVIDENCE_INVALID")
    if not isinstance(positions, list) or not 1 <= len(positions) <= 250:
        raise ValueError("POSITIONS_COUNT_INVALID")
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 20:
        raise ValueError("SCENARIOS_COUNT_INVALID")

    weight_by_id: dict[str, Decimal] = {}
    function_by_id: dict[str, str] = {}
    for i, row in enumerate(positions):
        if not isinstance(row, Mapping) or set(row) != {"p_id", "weight_pct", "function"}:
            raise ValueError("POSITION_EXACT_SCHEMA_REQUIRED")
        pid = _text(row["p_id"], f"positions[{i}].p_id")
        if pid in weight_by_id:
            raise ValueError("DUPLICATE_POSITION_ID")
        weight_by_id[pid] = _number(
            row["weight_pct"], f"{pid}.weight_pct",
            minimum=Decimal(0), maximum=HUNDRED,
        )
        function = _text(row["function"], f"{pid}.function")
        if function not in FUNCTIONS:
            raise ValueError("FUNCTION_NOT_SUPPORTED")
        function_by_id[pid] = function

    total_weight = sum(weight_by_id.values(), Decimal(0))
    denominator_known = denominator_evidence == "DISPLAYED_VIEW_DENOMINATOR_CALLER_ATTESTED"
    valid_weight_total = total_weight <= HUNDRED
    complete_displayed_weight = total_weight == HUNDRED
    result_rows: list[dict[str, Any]] = []
    seen_scenarios: set[str] = set()
    for i, scenario in enumerate(scenarios):
        if not isinstance(scenario, Mapping) or set(scenario) != {
            "scenario_id", "as_of", "assumption_source_ref", "shocks_pct_by_p_id",
        }:
            raise ValueError("SCENARIO_EXACT_SCHEMA_REQUIRED")
        sid = _text(scenario["scenario_id"], f"scenarios[{i}].scenario_id")
        if sid in seen_scenarios:
            raise ValueError("DUPLICATE_SCENARIO_ID")
        seen_scenarios.add(sid)
        dated = _date(scenario["as_of"], f"{sid}.as_of")
        if dated > cutoff:
            raise ValueError("SCENARIO_SOURCE_AFTER_ANALYSIS")
        ref = _text(scenario["assumption_source_ref"], f"{sid}.assumption_source_ref")
        shocks = scenario["shocks_pct_by_p_id"]
        if not isinstance(shocks, Mapping) or set(shocks) - set(weight_by_id):
            raise ValueError("SHOCKS_MUST_REFERENCE_SUPPLIED_POSITIONS")
        values = {
            pid: _number(raw, f"{sid}.{pid}.shock_pct",
                         minimum=Decimal(-100), maximum=Decimal(500))
            for pid, raw in shocks.items()
        }
        supported_ids = [pid for pid in weight_by_id if pid in values]
        unknown_ids = [pid for pid in weight_by_id if pid not in values]
        covered = sum((weight_by_id[pid] for pid in supported_ids), Decimal(0))
        contribution = sum(
            (weight_by_id[pid] * values[pid] / HUNDRED for pid in supported_ids),
            Decimal(0),
        )
        by_function: dict[str, Decimal] = {}
        for pid in supported_ids:
            function = function_by_id[pid]
            by_function[function] = by_function.get(function, Decimal(0)) + (
                weight_by_id[pid] * values[pid] / HUNDRED
            )
        if not denominator_known:
            status = "UNAVAILABLE_DENOMINATOR"
        elif not valid_weight_total:
            status = "UNAVAILABLE_WEIGHTS_EXCEED_100_NO_NORMALIZATION"
        elif not complete_displayed_weight or any(weight_by_id[p] > 0 for p in unknown_ids):
            status = "PARTIAL_SCOPED_SENSITIVITY_ONLY"
        else:
            status = "COMPLETE_DISPLAYED_VIEW_HYPOTHETICAL_ONLY"
        arithmetic_supported = denominator_known and valid_weight_total
        result_rows.append({
            "scenario_id": sid, "scenario_as_of": dated.isoformat(),
            "assumption_source_ref_caller_reported": ref,
            "status": status,
            "modeled_coverage_weight_pct": _pct(covered) if arithmetic_supported else None,
            "unmodeled_weight_pct": _pct(HUNDRED - covered) if arithmetic_supported else None,
            "partial_contribution_pct_points": _pct(contribution) if arithmetic_supported else None,
            "by_caller_reported_function_pct_points": {
                f: _pct(v) for f, v in sorted(by_function.items())
            } if arithmetic_supported else None,
            "scoped_displayed_hypothetical_return_pct": (
                _pct(contribution)
                if status == "COMPLETE_DISPLAYED_VIEW_HYPOTHETICAL_ONLY"
                else None
            ),
            "unmodeled_p_ids": unknown_ids,
            "is_drawdown_or_loss_bound": False,
            "historical_calibration": "NOT_PERFORMED",
        })
    return {
        "status": "NON_BINDING_CALLER_SUPPLIED_SCENARIO_SENSITIVITY",
        "analysis_id": aid, "analysis_as_of": cutoff.isoformat(),
        "strategy_id": mode,
        "displayed_weight_total_pct": _pct(total_weight),
        "denominator_evidence": denominator_evidence,
        "scope_authority": "CALLER_REPORTED_DISPLAYED_VIEW_NOT_ACCOUNT_VERIFIED",
        "source_authentication": "NOT_PERFORMED",
        "historical_calibration": "NOT_PERFORMED",
        "policy_authority": "NONE",
        "method_load": "NOT_VERIFIED",
        "investment_allocation_or_trade_authority": "NONE",
        "storage": "NONE",
        "scenarios": result_rows,
    }
