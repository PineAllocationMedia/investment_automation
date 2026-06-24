from __future__ import annotations

from typing import Any

from .benchmark_relevance_engine import benchmark_multiplier, benchmark_relevance_level
from .utils import clamp, safe_float


def conviction_category(score: float) -> str:
    if score >= 85:
        return "VERY_HIGH"
    if score >= 70:
        return "HIGH"
    if score >= 55:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "VERY_LOW"


def compute_conviction_score(
    manual: dict[str, Any],
    score: dict[str, Any],
    thesis_status: str,
    market: dict[str, Any],
    benchmark: dict[str, Any],
) -> dict[str, Any]:
    conviction = 50.0
    reasons: list[str] = []

    def add(points: float, reason: str) -> None:
        nonlocal conviction
        conviction += points
        point_text = f"{points:+.0f}" if float(points).is_integer() else f"{points:+.1f}"
        reasons.append(f"{point_text}: {reason}")

    score_total = safe_float(score.get("score_total")) or 0.0
    roic = safe_float(score.get("roic_5y_avg"))
    eps_hist = safe_float(score.get("eps_growth_5y"))
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    peg = safe_float(score.get("peg"))
    price_to_fair_value = safe_float(score.get("price_to_fair_value"))
    roic_threshold = safe_float(score.get("profile_roic_threshold")) or 15.0
    eps_hist_threshold = safe_float(score.get("profile_eps_hist_threshold")) or 10.0
    eps_est_threshold = safe_float(score.get("profile_eps_est_threshold")) or 12.0
    sector_threshold = safe_float(score.get("profile_sector_cagr_threshold")) or 8.0
    peg_limit = safe_float(score.get("profile_peg_limit")) or 2.0
    benchmark_10y = safe_float(benchmark.get("benchmark_10y_cagr"))
    benchmark_5y = safe_float(benchmark.get("benchmark_5y_cagr"))
    benchmark_weight = benchmark_multiplier(benchmark)
    benchmark_level = benchmark_relevance_level(benchmark)
    stock_return_1y = safe_float(market.get("stock_return_1y"))
    benchmark_return_1y = safe_float(benchmark.get("benchmark_return_1y"))
    underperformance = (
        stock_return_1y - benchmark_return_1y
        if stock_return_1y is not None and benchmark_return_1y is not None
        else None
    )

    if score_total >= 8:
        add(10, "score_total >= 8")
    if roic is not None and roic >= roic_threshold:
        add(8, f"capital/proxy confirmé >= seuil profil ({roic_threshold:.0f} %)")
    if eps_hist is not None and eps_hist > eps_hist_threshold:
        add(8, f"croissance EPS historique > seuil profil ({eps_hist_threshold:.0f} %)")
    if eps_est is not None and eps_est > eps_est_threshold:
        add(8, f"croissance EPS estimée > seuil profil ({eps_est_threshold:.0f} %)")
    if manual.get("net_margin_stable_or_expanding") is True:
        add(6, "marge stable ou en expansion")
    if manual.get("moat_clear") is True:
        add(6, "moat clair")
    if sector_cagr is not None and sector_cagr >= sector_threshold:
        add(6, f"secteur CAGR estimé >= seuil profil ({sector_threshold:.0f} %)")
    if benchmark_10y is not None and benchmark_10y >= 0.06:
        add(5 * benchmark_weight, f"benchmark 10 ans >= 6 % (pertinence {benchmark_level})")
    if market.get("price_above_sma_200") is True:
        add(5, "prix au-dessus SMA 200")
    if benchmark.get("benchmark_above_sma_200") is True:
        add(5 * benchmark_weight, f"benchmark au-dessus SMA 200 (pertinence {benchmark_level})")
    if peg is not None and peg <= peg_limit:
        add(5, f"PEG <= limite profil ({peg_limit:.1f})")
    if price_to_fair_value is not None and price_to_fair_value <= 1.20:
        add(5, "prix / juste valeur <= 1.20")
    if manual.get("management_quality_good") is True:
        add(5, "management de qualité")
    if manual.get("balance_sheet_strong") is True:
        add(5, "bilan financier solide")
    if manual.get("manual_confidence_level") == "HIGH":
        add(5, "confiance manuelle HIGH")

    missing_count = int(score.get("score_missing_data_count") or 0)
    if missing_count:
        add(-5 * missing_count, f"{missing_count} donnée(s) critique(s) manquante(s)")
    if peg is not None and peg > peg_limit + 0.5:
        add(-8, f"PEG > limite profil + 0.5 ({peg_limit + 0.5:.1f})")
    if peg is not None and peg > peg_limit + 1.0:
        add(-12, f"PEG > limite profil + 1.0 ({peg_limit + 1.0:.1f})")
    if price_to_fair_value is not None and price_to_fair_value > 1.40:
        add(-8, "prix / juste valeur > 1.40")
    if market.get("price_above_sma_200") is False:
        add(-8, "prix sous SMA 200")
    if benchmark_5y is not None and benchmark_5y < 0.03:
        add(-10 * benchmark_weight, f"benchmark 5 ans < 3 % (pertinence {benchmark_level})")
    if underperformance is not None and underperformance <= -0.15:
        add(-10 * benchmark_weight, f"sous-performance vs ETF <= -15 points (pertinence {benchmark_level})")
    if manual.get("margin_or_profitability_under_pressure") is True:
        add(-10, "marge/rentabilité sous pression")
    if manual.get("regulatory_risk_high") is True:
        add(-10, "risque réglementaire élevé")
    if manual.get("geopolitical_risk_high") is True:
        add(-10, "risque géopolitique élevé")
    if manual.get("single_product_dependency_high") is True:
        add(-10, "dépendance produit élevée")
    if thesis_status == "WEAKENING":
        add(-15, "thèse WEAKENING")
    if thesis_status == "BROKEN":
        add(-30, "thèse BROKEN")
    if manual.get("manual_confidence_level") == "LOW":
        add(-15, "confiance manuelle LOW")

    conviction = round(clamp(conviction, 0, 100), 2)
    return {
        "conviction_score": conviction,
        "conviction_category": conviction_category(conviction),
        "conviction_reasons": reasons,
    }
