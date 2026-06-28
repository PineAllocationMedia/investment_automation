from __future__ import annotations

from typing import Any

from .tax_location_engine import compute_after_tax_yield
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
    *,
    gross_yield: float | None = None,
    account_type: str | None = None,
    is_canadian_eligible_dividend: bool = False,
    is_us_dividend: bool = False,
    vfv_gross_yield: float | None = None,
    vfv_account_type: str | None = None,
) -> dict[str, Any]:
    score_total = safe_float(score.get("score_total")) or 0.0
    moat_clear = manual.get("moat_clear") is True
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    valuation_severity = str(score.get("valuation_severity") or "")
    growth_superior_to_market = eps_est is not None and eps_est >= 8
    add_is_allowed = liquidation_status == "GREEN" or add_eligibility_status in {"ADD_ALLOWED", "ADD_ALLOWED_SMALL"}
    tax_context = _after_tax_yield_context(
        ticker=str(score.get("ticker") or manual.get("ticker") or ""),
        gross_yield=first_number(gross_yield, score.get("dividend_yield"), manual.get("dividend_yield")),
        account_type=account_type or str(score.get("account_type") or manual.get("account_type") or ""),
        is_canadian_eligible_dividend=is_canadian_eligible_dividend,
        is_us_dividend=is_us_dividend,
        vfv_gross_yield=vfv_gross_yield,
        vfv_account_type=vfv_account_type or account_type or str(score.get("account_type") or manual.get("account_type") or ""),
    )
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
            **tax_context,
        }

    if strong_common_requirements and _valuation_allows_limited_allocation(score, conviction_score, expected_cagr_quality, valuation_severity):
        return {
            "opportunity_cost_status": "SIMILAR_TO_VFV",
            "opportunity_cost_reason": (
                "Qualité exceptionnelle, mais valorisation exigeante: le titre peut recevoir une allocation limitée, "
                "sans être traité comme clairement meilleur que VFV pour un gros bloc."
            ),
            **tax_context,
        }

    # Separate lower-quality path: if an expensive high-quality name failed the
    # limited-allocation valuation gate above, it intentionally falls through
    # here and can become WORSE_THAN_VFV instead of being rescued mechanically.
    if (
        7 <= score_total < 8
        or 55 <= conviction_score < 75
        or expected_cagr_quality == "MEDIUM"
    ) and thesis_status in {"INTACT", "UNCERTAIN"}:
        return {
            "opportunity_cost_status": "SIMILAR_TO_VFV",
            "opportunity_cost_reason": "Potentiel correct, mais l’avantage face à VFV n’est pas clair.",
            **tax_context,
        }

    return {
        "opportunity_cost_status": "WORSE_THAN_VFV",
        "opportunity_cost_reason": "Score, thèse, valorisation, données ou qualité CAGR insuffisants par rapport à VFV.",
        **tax_context,
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


def _after_tax_yield_context(
    *,
    ticker: str,
    gross_yield: float | None,
    account_type: str,
    is_canadian_eligible_dividend: bool,
    is_us_dividend: bool,
    vfv_gross_yield: float | None,
    vfv_account_type: str,
) -> dict[str, Any]:
    gross = safe_float(gross_yield)
    vfv_gross = safe_float(vfv_gross_yield)
    if gross is None:
        gross = 0.0
    result = compute_after_tax_yield(
        ticker,
        gross,
        account_type or "UNKNOWN",
        is_canadian_eligible_dividend,
        is_us_dividend,
    )
    vfv_result = compute_after_tax_yield(
        "VFV.TO",
        vfv_gross if vfv_gross is not None else 0.0,
        vfv_account_type or account_type or "UNKNOWN",
        False,
        True,
    )
    return {
        "gross_yield": gross,
        "after_tax_yield_adjusted": result["after_tax_yield"],
        "tax_adjustment_factor": result["tax_adjustment_factor"],
        "tax_adjustment_note": result["tax_note"],
        "vfv_gross_yield": vfv_gross if vfv_gross is not None else 0.0,
        "vfv_after_tax_yield_adjusted": vfv_result["after_tax_yield"],
        "vfv_tax_adjustment_note": vfv_result["tax_note"],
        "after_tax_yield_spread_vs_vfv": result["after_tax_yield"] - vfv_result["after_tax_yield"],
    }


def first_number(*values: Any) -> float | None:
    for value in values:
        number = safe_float(value)
        if number is not None:
            return number
    return None
