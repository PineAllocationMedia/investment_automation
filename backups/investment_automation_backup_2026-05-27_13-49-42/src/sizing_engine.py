from __future__ import annotations

from typing import Any

from .cash_flow_quality_engine import compute_cash_flow_quality
from .shareholder_discipline_engine import compute_shareholder_discipline
from .shareholder_return_engine import compute_shareholder_return_quality
from .utils import clamp, safe_float


EXPECTED_CAGR_QUALITY_SCORE = {
    "VERY_HIGH": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 30,
    "UNCERTAIN": 20,
}

OPPORTUNITY_COST_SCORE = {
    "CLEARLY_BETTER_THAN_VFV": 100,
    "SIMILAR_TO_VFV": 50,
    "WORSE_THAN_VFV": 0,
}


def drawdown_opportunity_score(drawdown: float | None) -> float:
    if drawdown is None:
        return 25.0
    if drawdown <= -0.30:
        return 100.0
    if drawdown <= -0.20:
        return 80.0
    if drawdown <= -0.10:
        return 50.0
    return 25.0


def compute_valuation_score(analysis: dict[str, Any]) -> float:
    peg = safe_float(analysis.get("peg"))
    ratio = safe_float(analysis.get("price_to_fair_value"))
    quality_too_expensive = analysis.get("quality_but_too_expensive") is True
    if (peg is not None and peg > 4) or (ratio is not None and ratio > 1.70):
        return 0.0
    if quality_too_expensive:
        return 30.0
    if (peg is not None and peg > 2.5) or (ratio is not None and ratio > 1.20):
        return 60.0
    return 100.0


def compute_business_quality_score(analysis: dict[str, Any]) -> float:
    roic = safe_float(analysis.get("roic_5y_avg"))
    score_total = (safe_float(analysis.get("score_total")) or 0.0) * 10
    roic_score = _score_percent_threshold(roic, 10, 25)
    margin_score = 100.0 if analysis.get("net_margin_stable_or_expanding") is True else 35.0
    moat_score = 100.0 if analysis.get("moat_clear") is True else 35.0 if analysis.get("moat_clear") is False else 55.0
    management_score = 100.0 if analysis.get("management_quality_good") is True else 55.0
    balance_score = 100.0 if analysis.get("balance_sheet_strong") is True else 55.0
    return round(
        clamp(
            0.30 * score_total
            + 0.25 * roic_score
            + 0.20 * moat_score
            + 0.10 * margin_score
            + 0.075 * management_score
            + 0.075 * balance_score,
            0,
            100,
        ),
        2,
    )


def compute_high_cagr_potential_score(analysis: dict[str, Any]) -> float:
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    eps_hist = safe_float(analysis.get("eps_growth_5y"))
    sector_cagr = safe_float(analysis.get("sector_cagr_estimated"))
    expected_score = EXPECTED_CAGR_QUALITY_SCORE.get(str(analysis.get("expected_cagr_quality")), 20)
    opportunity_score = OPPORTUNITY_COST_SCORE.get(str(analysis.get("opportunity_cost_status")), 0)
    valuation_score = compute_valuation_score(analysis)
    market_growth_score = safe_float(analysis.get("market_growth_thesis_score"))
    market_growth_component = market_growth_score if market_growth_score is not None else _score_percent_threshold(sector_cagr, 5, 12)
    return round(
        clamp(
            0.30 * _score_percent_threshold(eps_est, 8, 20)
            + 0.20 * _score_percent_threshold(eps_hist, 5, 18)
            + 0.10 * _score_percent_threshold(sector_cagr, 5, 12)
            + 0.05 * market_growth_component
            + 0.15 * expected_score
            + 0.10 * opportunity_score
            + 0.10 * valuation_score,
            0,
            100,
        ),
        2,
    )


def compute_winner_accelerated(analysis: dict[str, Any]) -> dict[str, Any]:
    catastrophic = bool(analysis.get("catastrophic_flags"))
    eps_hist = safe_float(analysis.get("eps_growth_5y"))
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    growth_ok = (eps_hist is not None and eps_hist >= 10) or (eps_est is not None and eps_est >= 10)
    quality_too_expensive = analysis.get("quality_but_too_expensive") is True
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    winner = (
        (safe_float(analysis.get("score_total")) or 0.0) >= 8
        and conviction >= 75
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and analysis.get("price_above_sma_200") is True
        and growth_ok
        and not catastrophic
        and analysis.get("criterion_7_validated") is True
        and analysis.get("liquidation_status") == "GREEN"
        and str(analysis.get("monitoring_status") or "NORMAL") == "NORMAL"
        and _data_reliability_ok_for_winner(analysis)
        and _shareholder_discipline_ok_for_winner(analysis)
        and (not quality_too_expensive or conviction >= 90)
    )
    return {
        "winner_accelerated": winner,
        "winner_accelerated_reason": "Toutes les conditions Winner accéléré sont confirmées."
        if winner
        else "Les conditions Winner accéléré ne sont pas toutes confirmées.",
    }


def compute_capital_allocation_score(
    analysis: dict[str, Any],
    portfolio_risk: dict[str, Any],
    tax_penalty: float = 0.0,
) -> dict[str, Any]:
    score_total_normalized = (safe_float(analysis.get("score_total")) or 0.0) * 10
    conviction_score = safe_float(analysis.get("conviction_score")) or 0.0
    expected_score = EXPECTED_CAGR_QUALITY_SCORE.get(str(analysis.get("expected_cagr_quality")), 20)
    opportunity_score = OPPORTUNITY_COST_SCORE.get(str(analysis.get("opportunity_cost_status")), 0)
    drawdown_score = drawdown_opportunity_score(safe_float(analysis.get("drawdown_from_12m_high")))
    valuation_score = compute_valuation_score(analysis)
    business_quality_score = compute_business_quality_score(analysis)
    high_cagr_potential_score = compute_high_cagr_potential_score(analysis)
    quality_cagr_intersection = min(business_quality_score, high_cagr_potential_score)
    durability_score = safe_float(analysis.get("long_term_durability_score"))
    shareholder_return = compute_shareholder_return_quality(analysis)
    shareholder_return_score = safe_float(shareholder_return.get("shareholder_return_quality_score")) or 0.0
    shareholder_return_adjustment = safe_float(shareholder_return.get("shareholder_return_adjustment")) or 0.0
    cash_flow_quality = compute_cash_flow_quality(analysis)
    cash_flow_quality_score = safe_float(cash_flow_quality.get("cash_flow_quality_score")) or 0.0
    cash_flow_quality_adjustment = safe_float(cash_flow_quality.get("cash_flow_quality_adjustment")) or 0.0
    shareholder_discipline = compute_shareholder_discipline({**analysis, **cash_flow_quality})
    shareholder_discipline_score = safe_float(shareholder_discipline.get("shareholder_discipline_score")) or 0.0
    shareholder_discipline_adjustment = safe_float(shareholder_discipline.get("shareholder_discipline_adjustment")) or 0.0
    quality_drawdown_adjustment = safe_float(analysis.get("quality_drawdown_allocation_adjustment")) or 0.0
    market_growth_thesis_score = safe_float(analysis.get("market_growth_thesis_score"))
    market_growth_thesis_adjustment = safe_float(analysis.get("market_growth_thesis_adjustment")) or 0.0
    market_regime_adjustment = safe_float(analysis.get("market_regime_allocation_adjustment")) or 0.0
    sector_euphoria_adjustment = safe_float(analysis.get("sector_euphoria_allocation_adjustment")) or 0.0

    base = (
        0.20 * score_total_normalized
        + 0.20 * conviction_score
        + 0.15 * expected_score
        + 0.10 * opportunity_score
        + 0.10 * drawdown_score
        + 0.05 * valuation_score
        + 0.20 * quality_cagr_intersection
    )
    if durability_score is not None:
        base = 0.90 * base + 0.10 * durability_score
    base += shareholder_return_adjustment
    base += cash_flow_quality_adjustment
    base += shareholder_discipline_adjustment
    base += quality_drawdown_adjustment
    base += market_growth_thesis_adjustment
    base += market_regime_adjustment
    base += sector_euphoria_adjustment

    penalties: list[tuple[float, str]] = []
    position_weight = safe_float(analysis.get("position_weight")) or 0.0
    sector = analysis.get("sector")
    sector_weight = portfolio_risk.get("concentration_by_sector", {}).get(sector, 0.0)
    top3_weight = safe_float(portfolio_risk.get("top3_weight")) or 0.0

    if position_weight > 0.40:
        penalties.append((30, "position_weight > 40 %"))
    elif position_weight > 0.30:
        penalties.append((15, "position_weight > 30 %"))
    if sector_weight > 0.55:
        penalties.append((25, "secteur déjà > 55 %"))
    elif sector_weight > 0.40:
        penalties.append((15, "secteur déjà > 40 %"))
    if top3_weight > 0.60:
        penalties.append((15, "top 3 concentration déjà > 60 %"))
    if analysis.get("thesis_status") != "INTACT":
        penalties.append((30, "thesis_status != INTACT"))
    add_status = str(analysis.get("add_eligibility_status") or "")
    if add_status == "ADD_ALLOWED_SMALL":
        penalties.append((8, "achat limité: surveillance technique/valorisation"))
    elif analysis.get("liquidation_status") != "GREEN":
        penalties.append((20, "liquidation_status != GREEN"))
    missing_count = safe_float(analysis.get("score_missing_data_count")) or 0.0
    coverage_status = str(analysis.get("ticker_coverage_status") or "")
    validation_status = str(analysis.get("ticker_validation_status") or "")
    provider_limitation = coverage_status in {
        "LOW_FREE_DATA_COVERAGE",
        "PARTIAL_FREE_DATA_COVERAGE",
        "NEEDS_BNCD_OR_MANUAL_CONFIRMATION",
    } and validation_status not in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}
    if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        penalties.append((40, "ticker ou données de marché à valider avant allocation"))
    elif missing_count > 3:
        if provider_limitation:
            penalties.append((8, "données gratuites mal couvertes: allocation limitée jusqu'à validation"))
        else:
            penalties.append((15, "nombreuses données critiques manquantes"))
    elif missing_count > 0:
        penalties.append((3 if provider_limitation else 5, "quelques données critiques manquantes"))
    if analysis.get("trend_status") == "DETERIORATING":
        trend_penalty = 10 if (safe_float(analysis.get("trend_severity")) or 0.0) >= 2 else 5
        penalties.append((trend_penalty, "détérioration détectée vs analyses précédentes"))
    reliability_score = safe_float(analysis.get("data_reliability_score"))
    auto_dependency = str(analysis.get("auto_estimate_dependency") or "")
    if reliability_score is not None:
        if reliability_score < 45:
            penalties.append((25, "fiabilité des données faible"))
        elif reliability_score < 60:
            penalties.append((18, "fiabilité des données limitée"))
        elif reliability_score < 75:
            penalties.append((10, "fiabilité des données moyenne"))
    if auto_dependency == "HIGH":
        penalties.append((10, "dépendance élevée aux estimations automatiques"))
    proof_penalty = safe_float(analysis.get("score_evidence_penalty")) or 0.0
    proof_level = str(analysis.get("score_evidence_level") or "")
    if proof_penalty:
        penalties.append((proof_penalty, f"preuve du score {proof_level}: score confirmé vs estimé"))
    cycle_penalty = _stabilized_cycle_penalty(analysis)
    if cycle_penalty:
        cycle_level = analysis.get("cycle_bubble_risk_level") or "N/D"
        penalties.append((cycle_penalty, f"risque cycle/bulle/tendance {cycle_level}"))
    normalized_cycle_status = str(analysis.get("cycle_normalized_status") or "")
    if normalized_cycle_status == "POSSIBLE_PEAK_EARNINGS":
        penalties.append((5, "profits possiblement au-dessus du cycle normalisé"))
    elif normalized_cycle_status == "ABOVE_NORMAL_CYCLE":
        penalties.append((2, "croissance/profits au-dessus du cycle normalisé"))
    durability_status = str(analysis.get("long_term_durability_status") or "")
    if durability_status == "SPECULATIVE_OR_UNPROVEN":
        penalties.append((18, "durabilité 15-30 ans non prouvée"))
    elif durability_status == "HIGH_GROWTH_BUT_FRAGILE":
        penalties.append((5, "haut potentiel mais fragilité 15-30 ans"))
    elif durability_status == "DURABLE_BUT_CYCLICAL":
        penalties.append((2, "durable mais cyclique"))
    if str(analysis.get("market_growth_thesis_status") or "") == "HYPE_RISK":
        penalties.append((3, "thèse de marché attrayante mais risque de hype"))
    if tax_penalty:
        penalties.append((tax_penalty, "emplacement fiscal approximatif moins optimal"))

    penalty_total = sum(points for points, _ in penalties)
    final_score = round(clamp(base - penalty_total, 0, 100), 2)
    return {
        "capital_allocation_score": final_score,
        "capital_allocation_components": {
            "score_total_normalized": score_total_normalized,
            "conviction_score": conviction_score,
            "expected_cagr_quality_score": expected_score,
            "opportunity_cost_score": opportunity_score,
            "drawdown_opportunity_score": drawdown_score,
            "valuation_score": valuation_score,
            "business_quality_score": business_quality_score,
            "high_cagr_potential_score": high_cagr_potential_score,
            "quality_cagr_intersection": quality_cagr_intersection,
            "long_term_durability_score": durability_score,
            "shareholder_return_quality_score": shareholder_return_score,
            "shareholder_return_adjustment": shareholder_return_adjustment,
            "cash_flow_quality_score": cash_flow_quality_score,
            "cash_flow_quality_adjustment": cash_flow_quality_adjustment,
            "shareholder_discipline_score": shareholder_discipline_score,
            "shareholder_discipline_adjustment": shareholder_discipline_adjustment,
            "quality_drawdown_allocation_adjustment": quality_drawdown_adjustment,
            "market_growth_thesis_score": market_growth_thesis_score,
            "market_growth_thesis_adjustment": market_growth_thesis_adjustment,
            "market_regime_allocation_adjustment": market_regime_adjustment,
            "sector_euphoria_allocation_adjustment": sector_euphoria_adjustment,
            "base": base,
            "penalties": penalties,
        },
        "business_quality_score": business_quality_score,
        "high_cagr_potential_score": high_cagr_potential_score,
        "quality_cagr_intersection": quality_cagr_intersection,
        **shareholder_return,
        **cash_flow_quality,
        **shareholder_discipline,
    }


def _score_percent_threshold(value: float | None, floor: float, excellent: float) -> float:
    if value is None:
        return 50.0
    if value <= floor:
        return max(0.0, value / floor * 50.0) if floor > 0 else 0.0
    return clamp(50.0 + ((value - floor) / (excellent - floor)) * 50.0, 50.0, 100.0)


def _data_reliability_ok_for_winner(analysis: dict[str, Any]) -> bool:
    reliability_score = safe_float(analysis.get("data_reliability_score"))
    dependency = str(analysis.get("auto_estimate_dependency") or "LOW")
    if reliability_score is None:
        return True
    return reliability_score >= 75 and dependency != "HIGH"


def _shareholder_discipline_ok_for_winner(analysis: dict[str, Any]) -> bool:
    status = str(analysis.get("shareholder_discipline_status") or "")
    return status not in {"HIGH_DILUTION_RISK"}


def _stabilized_cycle_penalty(analysis: dict[str, Any]) -> float:
    raw_penalty = safe_float(analysis.get("cycle_bubble_penalty")) or 0.0
    if raw_penalty <= 0:
        return 0.0
    durability = str(analysis.get("long_term_durability_status") or "")
    expected_quality = str(analysis.get("expected_cagr_quality") or "")
    thesis_intact = analysis.get("thesis_status") == "INTACT"
    clearly_better = analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
    if thesis_intact and clearly_better and expected_quality in {"HIGH", "VERY_HIGH"}:
        if durability in {"VERY_DURABLE_COMPOUNDER", "DURABLE_BUT_CYCLICAL"}:
            return round(min(raw_penalty * 0.55, 12.0), 2)
        if durability == "HIGH_GROWTH_BUT_FRAGILE":
            return round(min(raw_penalty * 0.70, 15.0), 2)
    return raw_penalty
