from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


THEME_TERMS = {
    "ai",
    "artificial intelligence",
    "semiconductor",
    "semiconductors",
    "cloud",
    "software",
    "technology",
    "digital",
    "internet",
    "platform",
    "advertising",
    "data center",
    "infrastructure",
}

MODE_MAX_ADJUSTMENT = {
    "balanced": -4.5,
    "family-office": -4.0,
    "rational-aggressive": -3.5,
    "high-cagr": -3.0,
}


def apply_double_counting_context(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]],
    market_analyses: dict[str, dict[str, Any]],
    discovery_analyses: dict[str, dict[str, Any]],
    mode: str,
) -> None:
    for group in [analyses, watchlist_analyses, market_analyses, discovery_analyses]:
        for analysis in group.values():
            analysis.update(compute_double_counting_context(analysis, mode))


def compute_double_counting_context(analysis: dict[str, Any], mode: str = "rational-aggressive") -> dict[str, Any]:
    if _is_non_company_asset(analysis):
        return _result(
            level="NOT_APPLICABLE",
            adjustment=0.0,
            overlap_score=0.0,
            clusters=[],
            reason="Non applicable: ETF, benchmark ou actif non évalué comme entreprise individuelle.",
        )

    clusters: list[str] = []
    reasons: list[str] = []
    overlap_score = 0.0

    growth_count = _growth_signal_count(analysis)
    momentum_count = _momentum_signal_count(analysis)
    theme_count = _theme_signal_count(analysis)
    quality_count = _quality_confirmation_count(analysis)

    if growth_count >= 4:
        overlap_score += 1.4
        clusters.append("growth")
        reasons.append("plusieurs signaux récompensent la même croissance")
    if growth_count >= 5:
        overlap_score += 0.6
    if _growth_thesis_echo(analysis):
        overlap_score += 0.9
        clusters.append("market_growth")
        reasons.append("croissance, marché adressable et CAGR attendu se recoupent")
    if _conviction_growth_echo(analysis):
        overlap_score += 0.8
        clusters.append("conviction_growth")
        reasons.append("conviction élevée et score élevé reposent partiellement sur le même profil de croissance")
    if theme_count >= 1 and growth_count >= 4:
        overlap_score += 0.9
        clusters.append("theme_growth")
        reasons.append("thème porteur et croissance forte peuvent être comptés deux fois")
    if theme_count >= 2:
        overlap_score += 0.5
    if momentum_count >= 2 and growth_count >= 4:
        overlap_score += 0.7
        clusters.append("momentum_growth")
        reasons.append("momentum et croissance renforcent possiblement le même narratif")
    if _theme_euphoria_echo(analysis):
        overlap_score += 0.8
        clusters.append("theme_euphoria")
        reasons.append("thème/cycle/euphorie déjà signalé ailleurs dans le modèle")

    if quality_count >= 4:
        overlap_score -= 1.0
        reasons.append("réduction: qualité indépendante confirmée par plusieurs preuves")
    elif quality_count <= 1 and overlap_score >= 2.0:
        overlap_score += 0.4
        reasons.append("peu de preuves indépendantes hors croissance/thème")

    overlap_score = round(clamp(overlap_score, 0.0, 7.0), 2)
    level = _risk_level(overlap_score)
    adjustment = _adjustment_for_level(level)
    if adjustment < 0 and quality_count >= 4:
        adjustment *= 0.65
    if adjustment < 0 and _valuation_supports_growth(analysis):
        adjustment *= 0.85
    adjustment = round(max(adjustment, MODE_MAX_ADJUSTMENT.get(mode, -3.5)), 2)

    return _result(
        level=level,
        adjustment=adjustment,
        overlap_score=overlap_score,
        clusters=clusters,
        reason=_reason(level, adjustment, reasons),
    )


def _growth_signal_count(analysis: dict[str, Any]) -> int:
    count = 0
    if (safe_float(analysis.get("eps_growth_5y")) or 0.0) >= 10:
        count += 1
    if (safe_float(analysis.get("eps_growth_estimated_3_5y")) or 0.0) >= 12:
        count += 1
    if (safe_float(analysis.get("sector_cagr_estimated")) or 0.0) >= 8:
        count += 1
    if str(analysis.get("expected_cagr_quality") or "") in {"HIGH", "VERY_HIGH"}:
        count += 1
    if (safe_float(analysis.get("high_cagr_potential_score")) or 0.0) >= 80:
        count += 1
    if (safe_float(analysis.get("market_growth_thesis_score")) or 0.0) >= 75:
        count += 1
    return count


def _momentum_signal_count(analysis: dict[str, Any]) -> int:
    count = 0
    if analysis.get("price_above_sma_200") is True:
        count += 1
    if analysis.get("benchmark_above_sma_200") is True:
        count += 1
    stock_return = safe_float(analysis.get("stock_return_1y"))
    benchmark_return = safe_float(analysis.get("benchmark_return_1y"))
    if stock_return is not None and stock_return >= 0.20:
        count += 1
    if stock_return is not None and benchmark_return is not None and stock_return - benchmark_return >= 0.10:
        count += 1
    return count


def _theme_signal_count(analysis: dict[str, Any]) -> int:
    text_parts = [str(analysis.get("sector") or "")]
    factors = analysis.get("factor_exposure") or []
    if isinstance(factors, str):
        text_parts.append(factors)
    else:
        text_parts.extend(str(item) for item in factors)
    text = " ".join(text_parts).lower()
    tokens = set(text.replace("/", " ").replace("-", " ").replace("_", " ").split())
    count = 1 if "ai" in tokens else 0
    return count + sum(1 for term in THEME_TERMS if term != "ai" and term in text)


def _quality_confirmation_count(analysis: dict[str, Any]) -> int:
    count = 0
    if (safe_float(analysis.get("business_quality_score")) or 0.0) >= 85:
        count += 1
    if (safe_float(analysis.get("roic_5y_avg")) or 0.0) >= 15:
        count += 1
    if analysis.get("moat_clear") is True:
        count += 1
    if (safe_float(analysis.get("cash_flow_quality_score")) or 0.0) >= 75:
        count += 1
    if (safe_float(analysis.get("long_term_durability_score")) or 0.0) >= 75:
        count += 1
    if (safe_float(analysis.get("shareholder_discipline_score")) or 0.0) >= 70:
        count += 1
    return count


def _growth_thesis_echo(analysis: dict[str, Any]) -> bool:
    return (
        (safe_float(analysis.get("sector_cagr_estimated")) or 0.0) >= 8
        and str(analysis.get("expected_cagr_quality") or "") in {"HIGH", "VERY_HIGH"}
        and (safe_float(analysis.get("market_growth_thesis_score")) or 0.0) >= 75
    )


def _conviction_growth_echo(analysis: dict[str, Any]) -> bool:
    return (
        (safe_float(analysis.get("score_total")) or 0.0) >= 8.5
        and (safe_float(analysis.get("conviction_score")) or 0.0) >= 85
        and str(analysis.get("expected_cagr_quality") or "") in {"HIGH", "VERY_HIGH"}
        and (safe_float(analysis.get("high_cagr_potential_score")) or 0.0) >= 80
    )


def _theme_euphoria_echo(analysis: dict[str, Any]) -> bool:
    if str(analysis.get("cycle_bubble_risk_level") or "") in {"HIGH", "EXTREME"}:
        return True
    if (safe_float(analysis.get("sector_euphoria_allocation_adjustment")) or 0.0) < 0:
        return True
    if str(analysis.get("market_growth_thesis_status") or "") == "HYPE_RISK":
        return True
    return False


def _valuation_supports_growth(analysis: dict[str, Any]) -> bool:
    ratio = safe_float(analysis.get("price_to_fair_value"))
    peg = safe_float(analysis.get("peg"))
    return (
        analysis.get("quality_but_too_expensive") is not True
        and ratio is not None
        and peg is not None
        and ratio <= 1.20
        and peg <= 2.0
    )


def _is_non_company_asset(analysis: dict[str, Any]) -> bool:
    if analysis.get("benchmark_role") is True:
        return True
    asset_type = str(analysis.get("asset_type") or "")
    if asset_type.startswith("ETF"):
        return True
    return str(analysis.get("score_total") or "") in {"BENCHMARK", "ETF"}


def _risk_level(overlap_score: float) -> str:
    if overlap_score < 1.75:
        return "LOW"
    if overlap_score < 3.0:
        return "MEDIUM"
    if overlap_score < 4.75:
        return "HIGH"
    return "EXTREME"


def _adjustment_for_level(level: str) -> float:
    return {
        "LOW": 0.0,
        "MEDIUM": -1.0,
        "HIGH": -2.25,
        "EXTREME": -3.75,
    }.get(level, 0.0)


def _reason(level: str, adjustment: float, reasons: list[str]) -> str:
    if level == "LOW":
        return "Aucun double comptage significatif détecté; les signaux semblent assez indépendants."
    reason_text = "; ".join(_dedupe(reasons[:4])) or "signaux de croissance ou de thème possiblement redondants"
    return (
        f"Risque {level}: {reason_text}. Ajustement sizing modéré de {adjustment:.2f} point(s), "
        "sans changer le score fondamental ni déclencher de vente."
    )


def _result(
    level: str,
    adjustment: float,
    overlap_score: float,
    clusters: list[str],
    reason: str,
) -> dict[str, Any]:
    return {
        "double_counting_risk_level": level,
        "double_counting_overlap_score": overlap_score,
        "double_counting_adjustment": adjustment,
        "double_counting_clusters": "; ".join(_dedupe(clusters)),
        "double_counting_reason": reason,
    }


def _dedupe(values: list[str]) -> list[str]:
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
