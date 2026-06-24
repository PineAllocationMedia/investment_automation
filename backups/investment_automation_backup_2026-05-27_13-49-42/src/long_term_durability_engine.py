from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


DURABILITY_STATUSES = {
    "VERY_DURABLE_COMPOUNDER",
    "DURABLE_BUT_CYCLICAL",
    "HIGH_GROWTH_BUT_FRAGILE",
    "SPECULATIVE_OR_UNPROVEN",
}

CYCLICAL_PROFILES = {
    "BANK",
    "INSURANCE",
    "UTILITY",
    "PIPELINE",
    "RESOURCES",
    "ENERGY_CYCLICAL",
    "REIT",
    "ALT_ASSET_MANAGER",
    "ASSET_MANAGER",
}


def compute_long_term_durability(analysis: dict[str, Any]) -> dict[str, Any]:
    components = _component_scores(analysis)
    score = round(clamp(sum(components.values()), 0, 100), 2)
    status = _durability_status(analysis, score, components)
    reasons = _durability_reasons(analysis, status, components)
    return {
        "long_term_durability_score": score,
        "long_term_durability_status": status,
        "long_term_durability_reason": " ".join(reasons),
        "long_term_durability_components": components,
    }


def _component_scores(analysis: dict[str, Any]) -> dict[str, float]:
    return {
        "structural_quality": _structural_quality_score(analysis),
        "growth_durability": _growth_durability_score(analysis),
        "thesis_durability": _thesis_durability_score(analysis),
        "risk_and_valuation_resilience": _risk_and_valuation_score(analysis),
        "data_reliability": _data_reliability_score(analysis),
        "historical_trend": _historical_trend_score(analysis),
    }


def _structural_quality_score(analysis: dict[str, Any]) -> float:
    roic = safe_float(analysis.get("roic_5y_avg"))
    roic_threshold = safe_float(analysis.get("profile_roic_threshold")) or 15.0
    score = 0.0
    if roic is None:
        score += 4.0
    elif roic >= max(20.0, roic_threshold * 1.35):
        score += 10.0
    elif roic >= roic_threshold:
        score += 8.0
    elif roic >= roic_threshold * 0.70:
        score += 5.0
    else:
        score += 2.0

    score += _bool_points(analysis.get("moat_clear"), true_points=8.0, false_points=1.0, missing_points=4.0)
    score += _bool_points(analysis.get("net_margin_stable_or_expanding"), true_points=6.0, false_points=1.0, missing_points=3.0)
    score += _bool_points(analysis.get("management_quality_good"), true_points=5.0, false_points=1.0, missing_points=3.0)
    score += _bool_points(analysis.get("balance_sheet_strong"), true_points=6.0, false_points=1.0, missing_points=3.0)
    cash_status = str(analysis.get("cash_flow_quality_status") or "")
    if cash_status == "EXCELLENT_CASH_COMPOUNDER":
        score += 2.0
    elif cash_status == "GOOD_CASH_GENERATOR":
        score += 1.0
    elif cash_status in {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"}:
        score -= 4.0
    elif cash_status == "CASH_FLOW_UNCERTAIN":
        score -= 1.0
    shareholder_status = str(analysis.get("shareholder_discipline_status") or "")
    if shareholder_status == "SHAREHOLDER_FRIENDLY":
        score += 1.5
    elif shareholder_status == "HIGH_DILUTION_RISK":
        score -= 4.0
    elif shareholder_status == "DILUTION_WATCH":
        score -= 1.5
    return round(clamp(score, 0.0, 35.0), 2)


def _growth_durability_score(analysis: dict[str, Any]) -> float:
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    eps_hist = safe_float(analysis.get("eps_growth_5y"))
    sector_cagr = safe_float(analysis.get("sector_cagr_estimated"))
    score = 0.0

    score += _growth_points(eps_est, excellent=15.0, good=10.0, weak=5.0, max_points=8.0)
    score += _growth_points(eps_hist, excellent=12.0, good=8.0, weak=4.0, max_points=5.0)
    score += _growth_points(sector_cagr, excellent=8.0, good=5.0, weak=2.0, max_points=4.0)
    expected = str(analysis.get("expected_cagr_quality") or "")
    score += {"VERY_HIGH": 3.0, "HIGH": 2.5, "MEDIUM": 1.5, "LOW": 0.5, "UNCERTAIN": 0.0}.get(expected, 1.0)
    return round(clamp(score, 0.0, 20.0), 2)


def _thesis_durability_score(analysis: dict[str, Any]) -> float:
    thesis = str(analysis.get("thesis_status") or "")
    fundamental = str(analysis.get("fundamental_thesis_status") or thesis)
    if thesis == "BROKEN" or fundamental == "BROKEN":
        return 0.0
    if thesis == "WEAKENING" or fundamental == "WEAKENING":
        return 6.0
    if thesis == "UNCERTAIN" or fundamental == "UNCERTAIN":
        return 4.0
    return 15.0 if thesis == "INTACT" else 7.0


def _risk_and_valuation_score(analysis: dict[str, Any]) -> float:
    score = 15.0
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    if cycle_level == "EXTREME":
        score -= 8.0
    elif cycle_level == "HIGH":
        score -= 5.0
    elif cycle_level == "MEDIUM":
        score -= 2.0

    if analysis.get("quality_but_too_expensive") is True:
        score -= 4.0
    ratio = safe_float(analysis.get("price_to_fair_value"))
    peg = safe_float(analysis.get("peg"))
    if ratio is not None and ratio > 1.40:
        score -= 4.0
    elif ratio is not None and ratio > 1.20:
        score -= 2.0
    if peg is not None and peg > 3.0:
        score -= 3.0
    elif peg is not None and peg > 2.5:
        score -= 1.5

    profile = str(analysis.get("business_profile") or "")
    if profile in {"RESOURCES", "ENERGY_CYCLICAL"}:
        score -= 3.0
    elif profile in CYCLICAL_PROFILES:
        score -= 1.5
    return round(clamp(score, 0.0, 15.0), 2)


def _data_reliability_score(analysis: dict[str, Any]) -> float:
    reliability = safe_float(analysis.get("data_reliability_score"))
    if reliability is None:
        level = str(analysis.get("data_reliability_level") or "").upper()
        reliability = {"HIGH": 85.0, "MEDIUM": 65.0, "LOW": 35.0}.get(level, 60.0)
    score = clamp(reliability / 10.0, 0.0, 10.0)
    if str(analysis.get("auto_estimate_dependency") or "").upper() == "HIGH":
        score -= 2.0
    missing_count = safe_float(analysis.get("score_missing_data_count")) or 0.0
    if missing_count > 3:
        score -= 2.0
    return round(clamp(score, 0.0, 10.0), 2)


def _historical_trend_score(analysis: dict[str, Any]) -> float:
    trend = str(analysis.get("trend_status") or "STABLE")
    severity = safe_float(analysis.get("trend_severity")) or 0.0
    if trend == "SOLIDIFYING":
        return 5.0
    if trend == "DEVELOPING":
        return 3.5
    if trend == "DETERIORATING":
        return 0.0 if severity >= 2 else 2.0
    return 4.0


def _durability_status(analysis: dict[str, Any], score: float, components: dict[str, float]) -> str:
    thesis = str(analysis.get("thesis_status") or "")
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    profile = str(analysis.get("business_profile") or "")
    high_cagr = _high_cagr_signal(analysis)
    missing_count = safe_float(analysis.get("score_missing_data_count")) or 0.0
    structural_quality = safe_float(components.get("structural_quality")) or 0.0
    cycle_hot = cycle_level in {"HIGH", "EXTREME"}

    if thesis in {"BROKEN", "UNCERTAIN"} or analysis.get("data_reliability_level") == "LOW" or missing_count > 3:
        return "SPECULATIVE_OR_UNPROVEN"

    fragile = (
        high_cagr >= 75
        and (
            score < 72
            or analysis.get("quality_but_too_expensive") is True
            or (analysis.get("balance_sheet_strong") is False and _field_confirmed(analysis, "balance_sheet_strong"))
            or (cycle_hot and structural_quality < 28)
        )
    )
    if fragile:
        return "HIGH_GROWTH_BUT_FRAGILE"

    if score >= 68 and thesis == "INTACT" and (profile in CYCLICAL_PROFILES or cycle_hot):
        return "DURABLE_BUT_CYCLICAL"

    if score >= 82 and thesis == "INTACT" and analysis.get("moat_clear") is True:
        return "VERY_DURABLE_COMPOUNDER"

    if score >= 74 and thesis == "INTACT":
        return "VERY_DURABLE_COMPOUNDER"

    return "SPECULATIVE_OR_UNPROVEN"


def _high_cagr_signal(analysis: dict[str, Any]) -> float:
    existing = safe_float(analysis.get("high_cagr_potential_score"))
    if existing is not None:
        return existing
    score_total = (safe_float(analysis.get("score_total")) or 0.0) * 10.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    expected = str(analysis.get("expected_cagr_quality") or "")
    expected_score = {"VERY_HIGH": 100.0, "HIGH": 85.0, "MEDIUM": 60.0, "LOW": 30.0, "UNCERTAIN": 20.0}.get(expected, 40.0)
    growth_score = _growth_points(eps_est, excellent=18.0, good=12.0, weak=6.0, max_points=100.0)
    return round(clamp(0.35 * score_total + 0.25 * conviction + 0.25 * expected_score + 0.15 * growth_score, 0.0, 100.0), 2)


def _durability_reasons(analysis: dict[str, Any], status: str, components: dict[str, float]) -> list[str]:
    reasons = [f"Durabilité 15-30 ans: {status}."]
    if components["structural_quality"] >= 28:
        reasons.append("Qualité structurelle forte.")
    elif components["structural_quality"] < 18:
        reasons.append("Qualité structurelle insuffisamment prouvée.")
    if components["growth_durability"] >= 15:
        reasons.append("Croissance durable favorable.")
    elif components["growth_durability"] < 8:
        reasons.append("Croissance long terme moins évidente.")
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    if cycle_level in {"HIGH", "EXTREME"}:
        reasons.append(f"Risque de cycle/tendance {cycle_level}, donc sizing plus prudent.")
    if analysis.get("quality_but_too_expensive") is True:
        reasons.append("Valorisation exigeante pour un horizon très long.")
    cash_status = str(analysis.get("cash_flow_quality_status") or "")
    if cash_status in {"EXCELLENT_CASH_COMPOUNDER", "GOOD_CASH_GENERATOR"}:
        reasons.append("Conversion en cash-flow favorable.")
    elif cash_status in {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"}:
        reasons.append("Conversion en cash-flow fragile.")
    shareholder_status = str(analysis.get("shareholder_discipline_status") or "")
    if shareholder_status == "SHAREHOLDER_FRIENDLY":
        reasons.append("Discipline actionnariale favorable.")
    elif shareholder_status in {"DILUTION_WATCH", "HIGH_DILUTION_RISK"}:
        reasons.append("Dilution/actionnariat à surveiller.")
    if analysis.get("thesis_status") != "INTACT":
        reasons.append("Thèse non pleinement intacte.")
    if analysis.get("data_reliability_level") == "LOW":
        reasons.append("Données trop faibles pour conclure solidement.")
    return reasons


def _field_confirmed(analysis: dict[str, Any], field: str) -> bool:
    manual_fields = _field_set(analysis.get("manual_override_fields"))
    research_fields = _field_set(analysis.get("research_report_fields"))
    auto_fields = _field_set(analysis.get("auto_estimated_fields"))
    return field in manual_fields or field in research_fields or field not in auto_fields


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}


def _bool_points(value: Any, true_points: float, false_points: float, missing_points: float) -> float:
    if value is True:
        return true_points
    if value is False:
        return false_points
    return missing_points


def _growth_points(value: float | None, excellent: float, good: float, weak: float, max_points: float) -> float:
    if value is None:
        return max_points * 0.35
    if value >= excellent:
        return max_points
    if value >= good:
        return max_points * 0.75
    if value >= weak:
        return max_points * 0.45
    if value > 0:
        return max_points * 0.20
    return 0.0
