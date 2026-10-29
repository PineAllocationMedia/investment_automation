"""Private optional probability-weighted cash-flow arithmetic for supplied M2 scenarios.

This computes an IRR on *probability-weighted cash flows*, NOT an average of
scenario IRRs, a verified Expected Return, forecast alpha, FX-adjusted account
return or investment authorization. No model probabilities are inferred.
"""
from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Any, Mapping

from .valuation_scenarios import _decimal, _irr, SCENARIOS


def _text(value: Any, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key}: nonempty explicit text required")
    return value.strip()


def _weight(raw: Any, label: str) -> Decimal:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 32:
        raise ValueError(f"{label}: explicit percent decimal string required")
    number = _decimal(raw, label)
    if number > 100 or number.as_tuple().exponent < -6:
        raise ValueError(f"{label}: percentage must be in 0..100 with at most six decimals")
    return number


def calculate_weighted_cashflows(
    *, valuation_inputs: Mapping[str, Any],
    valuation_scenarios: Mapping[str, Any],
    quote_trace: Mapping[str, Any],
    probability_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Conditional sensitivity from exactly three user/specialist-weighted cases.

    Requires one same-security/currency/base, full distribution schedules in all
    three scenarios or UNKNOWN in all three, and caller-linked quote evidence.
    No probability calibration, reinvestment forecast or market data supplied.
    """
    if not all(isinstance(v, Mapping) for v in (
        valuation_inputs, valuation_scenarios, quote_trace, probability_inputs
    )):
        raise ValueError("WEIGHTED_CASHFLOW_MAPPING_REQUIRED")
    if set(probability_inputs) != {
        "analysis_id", "analysis_as_of", "security_id", "probability_basis",
        "probability_rationale_ref", "probabilities_pct",
    }:
        raise ValueError("WEIGHTED_CASHFLOW_EXACT_INPUT_SCHEMA")
    aid = _text(probability_inputs.get("analysis_id"), "analysis_id")
    as_of = _text(probability_inputs.get("analysis_as_of"), "analysis_as_of")
    instrument = _text(probability_inputs.get("security_id"), "security_id")
    if (valuation_inputs.get("analysis_id") != aid
            or valuation_scenarios.get("analysis_id") != aid
            or valuation_inputs.get("analysis_as_of") != as_of
            or valuation_scenarios.get("analysis_as_of") != as_of
            or valuation_inputs.get("security_id") != instrument
            or valuation_scenarios.get("security_id") != instrument):
        raise ValueError("WEIGHTED_CASHFLOW_ANALYSIS_OR_INSTRUMENT_MISMATCH")
    basis = _text(probability_inputs.get("probability_basis"), "probability_basis")
    if basis not in {"PAM_ASSUMPTION", "THIRD_PARTY_ESTIMATE"}:
        raise ValueError("WEIGHTED_CASHFLOW_PROBABILITY_BASIS_UNSUPPORTED")
    rationale = _text(probability_inputs.get("probability_rationale_ref"), "probability_rationale_ref")
    raw_weights = probability_inputs.get("probabilities_pct")
    if not isinstance(raw_weights, Mapping) or set(raw_weights) != set(SCENARIOS):
        raise ValueError("WEIGHTED_CASHFLOW_BEAR_BASE_BULL_WEIGHTS_REQUIRED")
    weights = {s: _weight(raw_weights[s], s) for s in SCENARIOS}
    if sum(weights.values()) != Decimal(100):
        raise ValueError("WEIGHTED_CASHFLOW_PROBABILITIES_MUST_SUM_100")
    if (quote_trace.get("status") != "PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED"
            or quote_trace.get("analysis_id") != aid
            or quote_trace.get("analysis_as_of") != as_of
            or quote_trace.get("source_authentication") != "NOT_PERFORMED"
            or quote_trace.get("original_market_price_verification") != "NOT_ESTABLISHED"
            or quote_trace.get("market_price_or_fx_authority") != "NONE"
            or quote_trace.get("quote_reference_private") != valuation_scenarios.get("quote_source_ref")
            or quote_trace.get("review_stage") not in {"EVIDENCE_RESOLUTION", "HUMAN_QUOTE_REVIEW_ONLY"}):
        raise ValueError("WEIGHTED_CASHFLOW_QUOTE_TRACE_AUTHORITY_INVALID")
    if (valuation_scenarios.get("source_authentication") != "NOT_PERFORMED"
            or valuation_scenarios.get("trade_or_portfolio_authority") != "NONE"
            or valuation_scenarios.get("expected_return_status")
            != "NOT_ESTABLISHED_NO_PROBABILITIES_OR_ASSUMPTION_CERTIFICATION"
            or valuation_scenarios.get("currency") != str(valuation_inputs.get("currency", "")).upper()
            or valuation_scenarios.get("quoted_at") != valuation_inputs.get("quoted_at")):
        raise ValueError("WEIGHTED_CASHFLOW_VALUATION_AUTHORITY_OR_BASIS_INVALID")
    rows = valuation_inputs.get("scenarios")
    evaluated = valuation_scenarios.get("scenarios_private")
    if not isinstance(rows, Mapping) or set(rows) != set(SCENARIOS) or (
            not isinstance(evaluated, Mapping) or set(evaluated) != set(SCENARIOS)):
        raise ValueError("WEIGHTED_CASHFLOW_SCENARIOS_INVALID")
    horizon = valuation_scenarios.get("horizon_years")
    if type(horizon) is not int or not 1 <= horizon <= 30 or horizon != valuation_inputs.get("horizon_years"):
        raise ValueError("WEIGHTED_CASHFLOW_HORIZON_MISMATCH")
    price = _decimal(valuation_scenarios.get("price_per_share"), "price", strictly_positive=True)
    if price != _decimal(valuation_inputs.get("price_per_share"), "price", strictly_positive=True):
        raise ValueError("WEIGHTED_CASHFLOW_PRICE_MISMATCH")
    base = {
        "status": "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": as_of,
        "security_id_private": instrument, "currency": valuation_scenarios["currency"],
        "horizon_years": horizon, "probability_basis": basis,
        "probability_rationale_ref_private": rationale,
        "probabilities_pct_private": {s: str(weights[s]) for s in SCENARIOS},
        "conditional_annualized_pct": None,
        "measure": "UNAVAILABLE",
        "reason_codes": [],
        "probability_calibration": "NOT_PERFORMED",
        "price_authentication": "NOT_PERFORMED",
        "model_expected_return_authority": "NOT_CERTIFIED",
        "vfv_alpha": "NOT_ESTABLISHED",
        "account_costs_fx_tax": "NOT_EVALUATED",
        "trading_authority": "NONE", "storage": "NONE",
    }
    reasons = []
    if valuation_scenarios.get("status") != "CONDITIONAL_SCENARIO_ARITHMETIC_ONLY":
        reasons.append("SCENARIO_SECURITY_OR_CURRENCY_BASIS_UNCONFIRMED")
    if quote_trace.get("review_stage") != "HUMAN_QUOTE_REVIEW_ONLY":
        reasons.append("ORIGINAL_QUOTE_EVIDENCE_UNRESOLVED")
    schedules = []
    terminals = {}
    for name in SCENARIOS:
        input_row, output_row = rows[name], evaluated[name]
        if not isinstance(input_row, Mapping) or not isinstance(output_row, Mapping):
            raise ValueError("WEIGHTED_CASHFLOW_ROW_REQUIRED")
        terminal = _decimal(input_row.get("terminal_price_per_share"), name + ".terminal")
        if terminal != _decimal(output_row.get("terminal_price_per_share"), name + ".evaluated_terminal"):
            raise ValueError("WEIGHTED_CASHFLOW_TERMINAL_MISMATCH")
        if output_row.get("assumption_validation") != "NOT_PERFORMED":
            raise ValueError("WEIGHTED_CASHFLOW_ASSUMPTION_AUTHORITY_INVALID")
        schedule = input_row.get("annual_distributions_per_share")
        state = output_row.get("annual_distributions_status")
        if schedule is None:
            if state != "UNKNOWN" or output_row.get("return_measure") not in {
                "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN", "UNAVAILABLE",
            }:
                raise ValueError("WEIGHTED_CASHFLOW_DISTRIBUTION_STATE_MISMATCH")
            schedules.append(None)
        else:
            if not isinstance(schedule, list) or len(schedule) != horizon or (
                    state != "EXPLICITLY_SUPPLIED" or
                    output_row.get("return_measure") not in {"YEAR_END_CASHFLOW_IRR_CONDITIONAL", "UNAVAILABLE"}):
                raise ValueError("WEIGHTED_CASHFLOW_DISTRIBUTIONS_INVALID")
            values = []
            for j, row in enumerate(schedule):
                if not isinstance(row, Mapping):
                    raise ValueError("WEIGHTED_CASHFLOW_DISTRIBUTION_ROW_INVALID")
                _text(row.get("source_ref"), f"{name}.distribution[{j}].source_ref")
                values.append(_decimal(row.get("amount_per_share"), f"{name}.distribution[{j}]"))
            schedules.append(values)
        terminals[name] = terminal
    if any(schedule is None for schedule in schedules) and any(schedule is not None for schedule in schedules):
        reasons.append("MIXED_DISTRIBUTION_KNOWLEDGE")
    if reasons:
        return {**base, "status": "UNAVAILABLE_NEEDS_EVIDENCE_OR_COMPATIBLE_ASSUMPTIONS",
                "reason_codes": sorted(set(reasons))}
    fractions = {s: weights[s] / Decimal(100) for s in SCENARIOS}
    with localcontext() as ctx:
        ctx.prec = 44
        terminal = sum(fractions[s] * terminals[s] for s in SCENARIOS)
        if all(schedule is None for schedule in schedules):
            annual = (terminal / price) ** (Decimal(1) / Decimal(horizon)) - 1 if terminal else Decimal(-1)
            measure = "WEIGHTED_TERMINAL_PRICE_ONLY_CAGR_DISTRIBUTIONS_UNKNOWN"
        else:
            payments = [
                sum(fractions[s] * schedules[i][year] for i, s in enumerate(SCENARIOS))
                for year in range(horizon)
            ]
            payments[-1] += terminal
            annual = _irr(price, payments)
            measure = "IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR"
        annual_pct = str((annual * Decimal(100)).quantize(Decimal("0.01")))
    return {
        **base, "measure": measure, "conditional_annualized_pct": annual_pct,
        "reason_codes": [],
    }
