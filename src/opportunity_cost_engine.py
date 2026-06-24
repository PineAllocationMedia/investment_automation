from __future__ import annotations

from typing import Any

from .utils import safe_float


def compute_opportunity_cost_status(
    manual: dict[str, Any],
    score: dict[str, Any],
    conviction_score: float,
    expected_cagr_quality: str,
    thesis_status: str,
    liquidation_status: str,
    quality_but_too_expensive: bool,
    add_eligibility_status: str | None = None,
) -> dict[str, Any]:
    score_total = safe_float(score.get("score_total")) or 0.0
    moat_clear = manual.get("moat_clear") is True
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    valuation_severity = str(score.get("valuation_severity") or "")
    growth_superior_to_market = eps_est is not None and eps_est >= 8
    add_is_allowed = liquidation_status == "GREEN" or add_eligibility_status in {"ADD_ALLOWED", "ADD_ALLOWED_SMALL"}
    strong_common_requirements = (
        score_total >= 8
        and conviction_score >= 75
        and expected_cagr_quality in {"HIGH", "VERY_HIGH"}
        and thesis_status == "INTACT"
        and add_is_allowed
        and moat_clear
        and growth_superior_to_market
    )

    if strong_common_requirements and not quality_but_too_expensive:
        return {
            "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
            "opportunity_cost_reason": "L’action mérite du capital plus que VFV selon qualité, conviction, moat, croissance et valorisation.",
        }

    if strong_common_requirements and _valuation_allows_limited_allocation(score, conviction_score, expected_cagr_quality, valuation_severity):
        return {
            "opportunity_cost_status": "SIMILAR_TO_VFV",
            "opportunity_cost_reason": (
                "Qualité exceptionnelle, mais valorisation exigeante: le titre peut recevoir une allocation limitée, "
                "sans être traité comme clairement meilleur que VFV pour un gros bloc."
            ),
        }

    if (
        7 <= score_total < 8
        or 55 <= conviction_score < 75
        or expected_cagr_quality == "MEDIUM"
    ) and thesis_status in {"INTACT", "UNCERTAIN"}:
        return {
            "opportunity_cost_status": "SIMILAR_TO_VFV",
            "opportunity_cost_reason": "Potentiel correct, mais l’avantage face à VFV n’est pas clair.",
        }

    return {
        "opportunity_cost_status": "WORSE_THAN_VFV",
        "opportunity_cost_reason": "Score, thèse, valorisation, données ou qualité CAGR insuffisants par rapport à VFV.",
    }


def _valuation_allows_limited_allocation(
    score: dict[str, Any],
    conviction_score: float,
    expected_cagr_quality: str,
    valuation_severity: str,
) -> bool:
    return (
        valuation_severity == "EXPENSIVE_BUT_EXCEPTIONAL"
        and expected_cagr_quality == "VERY_HIGH"
        and conviction_score >= 85
        and (safe_float(score.get("score_total")) or 0.0) >= 8.5
    )
