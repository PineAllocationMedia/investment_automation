"""Conditional, private multi-security valuation scenario comparisons.

Per-security arithmetic is delegated to the existing scenario checker. No
source verification, FX forecast, probability weighting, portfolio advice,
alpha, optimizer, ranking, persistent storage or trade authority is supplied.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from itertools import combinations
from typing import Any, Mapping

from .valuation_scenarios import evaluate_valuation_scenarios
from .valuation_quote_trace import trace_valuation_quote
from .conditional_weighted_cashflows import calculate_weighted_cashflows

ROLES = frozenset({"SECURITY", "REFERENCE_ETF"})
CONFIDENCE = frozenset({"SPECIALIST_REPORTED", "UNKNOWN"})
ROOM = frozenset({"ROOM_CONDITIONAL", "ROOM_UNAVAILABLE", "NOT_EVALUATED"})
SCENARIOS = ("BEAR", "BASE", "BULL")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: explicit text required")
    return value.strip()


def _date(value: Any, name: str) -> str:
    text = _text(value, name)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{name}: canonical date required") from exc
    if parsed.isoformat() != text:
        raise ValueError(f"{name}: canonical date required")
    return text


def _currency(value: Any, name: str) -> str:
    cur = _text(value, name).upper()
    if len(cur) != 3 or not cur.isascii() or not cur.isalpha():
        raise ValueError(f"{name}: ISO three-letter currency required")
    return cur


def compare_candidates(
    *, analysis_id: str, analysis_as_of: str, strategy_id: str,
    account_currency: str, candidates: list[Mapping[str, Any]],
    source_annex: Mapping[str, Any] | None = None,
    ir_research_as_of: str | None = None,
) -> dict[str, Any]:
    """Compute guarded *scenario-to-scenario* pp differences, never Expected Return.

    Each candidate supplies a full same-ID/same-date valuation_inputs packet,
    and optional IR/PI context as explicitly reported but never authenticated.
    Cross-currency and mismatched-return-measure comparisons yield no spread.
    """
    run_id = _text(analysis_id, "analysis_id")
    cutoff = _date(analysis_as_of, "analysis_as_of")
    strategy = _text(strategy_id, "strategy_id")
    acct = _currency(account_currency, "account_currency")
    if not isinstance(candidates, list) or not (2 <= len(candidates) <= 6):
        raise ValueError("CANDIDATE_COUNT_MUST_BE_2_TO_6")
    if ir_research_as_of is not None and _date(ir_research_as_of, "ir_research_as_of") > cutoff:
        raise ValueError("CANDIDATE_IR_DATE_AFTER_ANALYSIS")
    records: list[dict[str, Any]] = []
    ids: set[str] = set()
    securities: set[str] = set()
    horizons: set[int] = set()
    for i, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            raise ValueError(f"candidate[{i}]: mapping required")
        cid = _text(candidate.get("candidate_id"), f"candidate[{i}].candidate_id")
        if cid in ids:
            raise ValueError("DUPLICATE_CANDIDATE_ID")
        ids.add(cid)
        role = _text(candidate.get("role"), f"{cid}.role")
        if role not in ROLES:
            raise ValueError("INVALID_CANDIDATE_ROLE")
        method = _text(candidate.get("research_method_version"), f"{cid}.research_method_version")
        status = _text(candidate.get("research_status"), f"{cid}.research_status")
        if status not in CONFIDENCE:
            raise ValueError("RESEARCH_STATUS_NOT_AUTHENTICATED")
        room = _text(candidate.get("portfolio_room_status"), f"{cid}.portfolio_room_status")
        if room not in ROOM:
            raise ValueError("PORTFOLIO_ROOM_MUST_NOT_BE_CERTIFIED_BY_COMPARATOR")
        risk_ref = _text(candidate.get("principal_failure_ref"), f"{cid}.principal_failure_ref")
        valuation = candidate.get("valuation_inputs")
        if not isinstance(valuation, Mapping):
            raise ValueError("VALUATION_INPUTS_MAPPING_REQUIRED")
        if valuation.get("analysis_id") != run_id or valuation.get("analysis_as_of") != cutoff:
            raise ValueError("CANDIDATE_ANALYSIS_ID_OR_DATE_MISMATCH")
        result = evaluate_valuation_scenarios(**valuation)
        security = result["security_id"]
        if security in securities:
            raise ValueError("DUPLICATE_SECURITY_ID")
        securities.add(security)
        horizons.add(result["horizon_years"])
        returns = {s: result["scenarios_private"][s]["scenario_return_pct_annual"] for s in SCENARIOS}
        measure = {s: result["scenarios_private"][s]["return_measure"] for s in SCENARIOS}
        inconsistent = False
        if len(set(measure.values())) == 1 and all(returns.values()):
            vals = [Decimal(returns[s]) for s in SCENARIOS]
            inconsistent = not (vals[0] <= vals[1] <= vals[2])
        reasons = []
        if inconsistent:
            reasons.append("BEAR_BASE_BULL_ORDER_INCONSISTENT")
        if status == "UNKNOWN":
            reasons.append("RESEARCH_STATUS_UNKNOWN")
        if room != "ROOM_CONDITIONAL":
            reasons.append("PORTFOLIO_ROOM_UNAVAILABLE_OR_NOT_EVALUATED")
        if result["currency"] != acct:
            reasons.append("FOREIGN_CURRENCY_WITHOUT_ACCOUNT_FX_MODEL")
        if result["status"] != "CONDITIONAL_SCENARIO_ARITHMETIC_ONLY":
            reasons.append("SCENARIO_INPUT_BASIS_UNAVAILABLE")
        if len(set(measure.values())) != 1:
            reasons.append("MIXED_RETURN_MEASURE_WITHIN_CANDIDATE")
        # Optional *actual* M2 weighted cashflow path. Recompute from supplied
        # valuation/quote/probability inputs, never accept a caller's invented
        # weighted-return result or a precomputed prospective alpha.
        weighted = None
        if "probability_inputs" in candidate:
            probs = candidate["probability_inputs"]
            if not isinstance(probs, Mapping):
                raise ValueError("CANDIDATE_PROBABILITY_INPUTS_MAPPING_REQUIRED")
            trace = trace_valuation_quote(
                valuation=result, source_annex=source_annex,
                ir_research_as_of=ir_research_as_of or cutoff,
            )
            weighted = calculate_weighted_cashflows(
                valuation_inputs=valuation,
                valuation_scenarios=result,
                quote_trace=trace,
                probability_inputs=probs,
            )
            if (weighted["security_id_private"] != security
                    or weighted["model_expected_return_authority"] != "NOT_CERTIFIED"
                    or weighted["probability_calibration"] != "NOT_PERFORMED"
                    or weighted["account_costs_fx_tax"] != "NOT_EVALUATED"
                    or weighted["trading_authority"] != "NONE"):
                raise ValueError("CANDIDATE_WEIGHTED_MODEL_AUTHORITY_INVALID")
        records.append({"candidate_id": cid, "role": role, "security_id": security,
                        "currency": result["currency"], "quoted_at": result["quoted_at"], "account_currency": acct,
                        "horizon_years": result["horizon_years"],
                        "research_method_version": method, "research_status": status,
                        "portfolio_room_status": room, "principal_failure_ref": risk_ref,
                        "valuation_private": deepcopy(result),
                        "weighted_cashflow_model_private": deepcopy(weighted),
                        "scenario_return_pct_annual": returns,
                        "scenario_return_measure": measure,
                        "qualification_codes": reasons,
                        "source_authentication": "NOT_PERFORMED"})
    if len(horizons) != 1:
        raise ValueError("CANDIDATES_MUST_USE_SAME_HORIZON")
    pairs = []
    weighted_pairs = []
    has_weighted = any(row["weighted_cashflow_model_private"] is not None
                       for row in records)
    for first, second in combinations(records, 2):
        differences: dict[str, Any] = {}
        reasons = []
        if first["currency"] != acct or second["currency"] != acct:
            reasons.append("ACCOUNT_CURRENCY_FX_MODEL_MISSING")
        if first["quoted_at"] != second["quoted_at"]:
            reasons.append("QUOTE_OBSERVATION_DATE_MISMATCH")
        if "MIXED_RETURN_MEASURE_WITHIN_CANDIDATE" in (first["qualification_codes"] + second["qualification_codes"]):
            reasons.append("INTRA_CANDIDATE_RETURN_MEASURES_INCONSISTENT")
        if "BEAR_BASE_BULL_ORDER_INCONSISTENT" in (first["qualification_codes"] + second["qualification_codes"]):
            reasons.append("SCENARIO_ORDER_INCONSISTENT")
        for scenario in SCENARIOS:
            measure_a = first["scenario_return_measure"][scenario]
            measure_b = second["scenario_return_measure"][scenario]
            a = first["scenario_return_pct_annual"][scenario]
            b = second["scenario_return_pct_annual"][scenario]
            local_reason = list(reasons)
            if measure_a != measure_b or measure_a == "UNAVAILABLE":
                local_reason.append("RETURN_MEASURE_NOT_COMPARABLE")
            if a is None or b is None:
                local_reason.append("SCENARIO_RETURN_UNAVAILABLE")
            if local_reason:
                differences[scenario] = {"delta_first_minus_second_pp": None,
                                         "comparison_status": "NOT_COMPARABLE",
                                         "reason_codes": sorted(set(local_reason))}
            else:
                gap = Decimal(a) - Decimal(b)
                differences[scenario] = {"delta_first_minus_second_pp": str(gap),
                                         "comparison_status": "SCENARIO_ARITHMETIC_ONLY",
                                         "reason_codes": (["PRICE_ONLY_NOT_TOTAL_RETURN"] if
                                             measure_a == "PRICE_ONLY_CAGR_NOT_TOTAL_RETURN" else
                                             ["YEAR_END_IRR_ASSUMPTIONS_UNVERIFIED"])}
        pairs.append({"first_candidate_id": first["candidate_id"],
                      "second_candidate_id": second["candidate_id"],
                      "by_scenario": differences})
        if has_weighted:
            a, b = (first["weighted_cashflow_model_private"],
                    second["weighted_cashflow_model_private"])
            weighted_reasons = []
            if a is None or b is None:
                weighted_reasons.append("PROBABILITIES_OR_MODEL_NOT_SUPPLIED_FOR_BOTH")
            else:
                required_measure = "IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR"
                if a["measure"] != required_measure or b["measure"] != required_measure:
                    weighted_reasons.append("EXPLICIT_TOTAL_CASHFLOW_IRR_MISSING")
                if (a["status"] != "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED"
                        or b["status"] != "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED"
                        or a["conditional_annualized_pct"] is None
                        or b["conditional_annualized_pct"] is None):
                    weighted_reasons.append("WEIGHTED_CASHFLOW_EVIDENCE_UNAVAILABLE")
            if first["currency"] != acct or second["currency"] != acct:
                weighted_reasons.append("ACCOUNT_CURRENCY_FX_MODEL_MISSING")
            if first["quoted_at"] != second["quoted_at"]:
                weighted_reasons.append("QUOTE_OBSERVATION_DATE_MISMATCH")
            if (first["research_status"] == "UNKNOWN"
                    or second["research_status"] == "UNKNOWN"):
                weighted_reasons.append("RESEARCH_STATUS_UNKNOWN")
            # Room is an independent decision gate: lack of holdings does not
            # nullify a reproducible economic sensitivity calculation.
            spread = None
            if not weighted_reasons:
                left = Decimal(a["conditional_annualized_pct"])
                right = Decimal(b["conditional_annualized_pct"])
                if not left.is_finite() or not right.is_finite():
                    raise ValueError("CANDIDATE_WEIGHTED_RETURN_NONFINITE")
                spread = str(left - right)
            weighted_pairs.append({
                "first_candidate_id": first["candidate_id"],
                "second_candidate_id": second["candidate_id"],
                "status": ("CONDITIONAL_TOTAL_CASHFLOW_IRR_SPREAD_ONLY"
                           if spread is not None else "NOT_COMPARABLE"),
                "first_minus_second_pp": spread,
                "reason_codes": sorted(set(weighted_reasons)),
                "return_basis": "IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR",
                "evidence_authority": "MODEL_INPUTS_STRUCTURALLY_CHECKED_NOT_CERTIFIED",
                "cost_fx_tax": "NOT_EVALUATED",
            })
    return {"status": "CONDITIONAL_RESEARCH_COMPARISON_ONLY",
            "analysis_id": run_id, "analysis_as_of": cutoff,
            "strategy_id": strategy, "account_currency": acct,
            "comparison_horizon_years": next(iter(horizons)),
            "candidates_private": records, "pairwise_scenario_differences_private": pairs,
            "pairwise_weighted_cashflow_private": weighted_pairs,
            "probability_weighted_expected_return": "NOT_ESTABLISHED",
            "benchmark_expected_return": "NOT_ESTABLISHED",
            "forward_alpha_or_superiority": "NOT_ESTABLISHED",
            "recommendation_or_ranking": "NOT_AUTHORIZED",
            "portfolio_allocation": "NOT_CALCULATED",
            "source_authentication": "NOT_PERFORMED", "rights_and_costs": "NOT_VERIFIED",
            "trading_authority": "NONE_CEO_ONLY", "writes": "NONE"}
