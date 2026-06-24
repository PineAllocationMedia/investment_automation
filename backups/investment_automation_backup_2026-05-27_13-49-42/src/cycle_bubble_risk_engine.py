from __future__ import annotations

from typing import Any

from .portfolio_risk_engine import TECH_AI_SEMI_FACTORS
from .utils import clamp, safe_float


SEMI_TICKERS = {
    "ASML",
    "AVGO",
    "LRCX",
    "KLAC",
    "NVDA",
    "TSM",
    "TXN",
    "AMAT",
    "ADI",
    "QCOM",
    "MU",
    "MPWR",
}

RISK_MULTIPLIER = {
    "LOW": 1.0,
    "MEDIUM": 0.90,
    "HIGH": 0.75,
    "EXTREME": 0.60,
}

RISK_PENALTY = {
    "LOW": 0.0,
    "MEDIUM": 3.0,
    "HIGH": 8.0,
    "EXTREME": 14.0,
}

FULL_CYCLE_PROFILES = {
    "SEMI_CAPEX_CYCLE",
    "RESOURCE_CYCLE",
    "ENERGY_CYCLE",
    "INDUSTRIAL_CYCLE",
    "FINANCIAL_MARKET_CYCLE",
    "CONSUMER_CYCLE",
    "TECH_AI_GROWTH_THEME",
}

NORMALIZED_GROWTH_CAPS = {
    "SEMI_CAPEX_CYCLE": 18.0,
    "RESOURCE_CYCLE": 8.0,
    "ENERGY_CYCLE": 8.0,
    "INDUSTRIAL_CYCLE": 10.0,
    "FINANCIAL_MARKET_CYCLE": 11.0,
    "CONSUMER_CYCLE": 12.0,
    "TECH_AI_GROWTH_THEME": 14.0,
}

NORMALIZED_MARGIN_CEILINGS = {
    "SEMI_CAPEX_CYCLE": 0.35,
    "RESOURCE_CYCLE": 0.22,
    "ENERGY_CYCLE": 0.20,
    "INDUSTRIAL_CYCLE": 0.16,
    "FINANCIAL_MARKET_CYCLE": 0.40,
    "CONSUMER_CYCLE": 0.14,
    "TECH_AI_GROWTH_THEME": 0.32,
}


def compute_cycle_bubble_risk(
    analysis: dict[str, Any],
    portfolio_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    portfolio_risk = portfolio_risk or {}
    profile = _risk_profile(analysis)
    cyclicality_score, cyclicality_reason = _cyclicality_score(profile)
    heat_score, heat_reasons = _market_heat_score(analysis)
    valuation_score, valuation_reasons = _valuation_heat_score(analysis)
    crowding_score, crowding_reasons = _portfolio_crowding_score(analysis, portfolio_risk)
    normalized_score, normalized_reasons, normalized_context = _full_cycle_normalization_score(profile, analysis)

    raw_score = cyclicality_score + heat_score + valuation_score + crowding_score + normalized_score
    total_score = round(clamp(raw_score, 0, 100), 2)
    level = _risk_level(total_score)
    reasons = [cyclicality_reason, *heat_reasons, *valuation_reasons, *crowding_reasons, *normalized_reasons]

    return {
        "cycle_risk_profile": profile,
        "cycle_bubble_risk_level": level,
        "cycle_bubble_score": total_score,
        "cycle_bubble_penalty": RISK_PENALTY[level],
        "cycle_bubble_allocation_multiplier": RISK_MULTIPLIER[level],
        "cycle_bubble_reasons": reasons,
        "cycle_bubble_manual_check": level in {"HIGH", "EXTREME"},
        "cycle_bubble_not_a_sell_signal": True,
        "cycle_bubble_comment": _comment(level),
        **normalized_context,
    }


def cycle_risk_rows(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]] | None = None,
    market_analyses: dict[str, dict[str, Any]] | None = None,
    discovery_analyses: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for universe, group in [
        ("CORE_PORTFOLIO", analyses),
        ("WATCHLIST", watchlist_analyses or {}),
        ("MARKET_UNIVERSE", market_analyses or {}),
        ("DISCOVERY_IDEAS", discovery_analyses or {}),
    ]:
        for row in group.values():
            if row.get("ticker") == "VFV.TO" or row.get("benchmark_role") is True:
                continue
            rows.append(
                {
                    "universe": universe,
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "cycle_risk_profile": row.get("cycle_risk_profile"),
                    "cycle_bubble_risk_level": row.get("cycle_bubble_risk_level"),
                    "cycle_bubble_score": row.get("cycle_bubble_score"),
                    "cycle_bubble_penalty": row.get("cycle_bubble_penalty"),
                    "allocation_multiplier": row.get("cycle_bubble_allocation_multiplier"),
                    "cycle_normalized_status": row.get("cycle_normalized_status"),
                    "cycle_normalized_growth_cap": row.get("cycle_normalized_growth_cap"),
                    "cycle_adjusted_growth_estimate": row.get("cycle_adjusted_growth_estimate"),
                    "cycle_normalized_earnings_risk_score": row.get("cycle_normalized_earnings_risk_score"),
                    "comment": row.get("cycle_bubble_comment"),
                    "reasons": _list_text(row.get("cycle_bubble_reasons")),
                }
            )
    return sorted(rows, key=_cycle_row_sort_key, reverse=True)


def _risk_profile(analysis: dict[str, Any]) -> str:
    ticker = str(analysis.get("ticker") or "")
    business_profile = str(analysis.get("business_profile") or "")
    benchmark = str(analysis.get("benchmark_ticker") or "")
    sector = _lower(analysis.get("sector"))
    factors = {_lower(item) for item in (analysis.get("factor_exposure") or [])}
    text = " ".join([ticker, business_profile, benchmark, sector, " ".join(sorted(factors))]).lower()

    if ticker in SEMI_TICKERS or benchmark == "SOXX" or "semiconductor" in text or "semiconductors" in text:
        return "SEMI_CAPEX_CYCLE"
    if business_profile == "RESOURCES" or any(term in text for term in ["gold", "mining", "uranium", "materials", "resources"]):
        return "RESOURCE_CYCLE"
    if business_profile in {"ENERGY_CYCLICAL", "PIPELINE"} or any(term in text for term in ["oil", "gas", "energy", "pipeline"]):
        return "ENERGY_CYCLE"
    if business_profile in {"BANK", "INSURANCE", "ASSET_MANAGER", "ALT_ASSET_MANAGER"}:
        return "FINANCIAL_MARKET_CYCLE"
    if any(term in text for term in ["industrial", "industrials", "machinery", "engineering", "construction", "automation"]):
        return "INDUSTRIAL_CYCLE"
    if any(term in text for term in ["consumer", "discretionary", "retail", "automotive", "luxury"]):
        return "CONSUMER_CYCLE"
    if bool(factors & {_lower(item) for item in TECH_AI_SEMI_FACTORS}) or any(term in text for term in ["ai", "cloud", "software", "technology"]):
        return "TECH_AI_GROWTH_THEME"
    if business_profile in {"UTILITY", "REIT"}:
        return "RATE_SENSITIVE_DEFENSIVE"
    return "BROAD_QUALITY"


def _cyclicality_score(profile: str) -> tuple[float, str]:
    scores = {
        "SEMI_CAPEX_CYCLE": (22.0, "Industrie très cyclique: semi-conducteurs / capex / IA."),
        "RESOURCE_CYCLE": (22.0, "Industrie cyclique: ressources / matières premières."),
        "ENERGY_CYCLE": (20.0, "Industrie cyclique: énergie / pipelines / prix des commodités."),
        "INDUSTRIAL_CYCLE": (15.0, "Industrie sensible au cycle économique ou au capex industriel."),
        "FINANCIAL_MARKET_CYCLE": (14.0, "Entreprise sensible au cycle du crédit, des marchés ou des taux."),
        "CONSUMER_CYCLE": (12.0, "Entreprise sensible au cycle de consommation."),
        "TECH_AI_GROWTH_THEME": (10.0, "Thème croissance/tech: excellent possible, mais sensible aux attentes du marché."),
        "RATE_SENSITIVE_DEFENSIVE": (8.0, "Profil défensif ou régulé, mais sensible aux taux."),
        "BROAD_QUALITY": (4.0, "Profil moins cyclique détecté."),
    }
    return scores.get(profile, scores["BROAD_QUALITY"])


def _market_heat_score(analysis: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    stock_return = _as_decimal(analysis.get("stock_return_1y"))
    benchmark_return = _as_decimal(analysis.get("benchmark_return_1y"))
    drawdown = _as_decimal(analysis.get("drawdown_from_12m_high"))
    benchmark_relevance = str(analysis.get("benchmark_relevance_level") or "").upper()

    if stock_return is not None:
        if stock_return >= 0.60:
            score += 24
            reasons.append("Performance 1 an très élevée: risque de tendance déjà avancée.")
        elif stock_return >= 0.40:
            score += 18
            reasons.append("Performance 1 an élevée: risque de payer une tendance chaude.")
        elif stock_return >= 0.25:
            score += 10
            reasons.append("Performance 1 an forte.")

    if benchmark_return is not None and benchmark_relevance in {"HIGH", "MEDIUM"}:
        if benchmark_return >= 0.45:
            score += 18
            reasons.append("ETF sectoriel très fort sur 1 an: thème possiblement chaud.")
        elif benchmark_return >= 0.30:
            score += 12
            reasons.append("ETF sectoriel fort sur 1 an.")

    if drawdown is not None:
        if drawdown >= -0.03:
            score += 14
            reasons.append("Prix très proche du sommet 12 mois.")
        elif drawdown >= -0.08:
            score += 9
            reasons.append("Prix proche du sommet 12 mois.")
        elif drawdown <= -0.25:
            score -= 5
            reasons.append("Drawdown significatif: risque de bulle actuelle moins élevé, mais thèse à valider.")

    if analysis.get("price_above_sma_200") is True:
        score += 4
    return max(score, 0.0), reasons


def _valuation_heat_score(analysis: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    peg = safe_float(analysis.get("peg"))
    ratio = safe_float(analysis.get("price_to_fair_value"))
    forward_pe = safe_float(analysis.get("forward_pe"))
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))

    if analysis.get("quality_but_too_expensive") is True:
        score += 18
        reasons.append("Qualité possible, mais valorisation déjà exigeante.")
    if ratio is not None:
        if ratio > 1.40:
            score += 20
            reasons.append("Prix > 140 % de la juste valeur estimée.")
        elif ratio > 1.20:
            score += 10
            reasons.append("Prix > 120 % de la juste valeur estimée.")
    if peg is not None:
        if peg > 3:
            score += 16
            reasons.append("PEG > 3: attentes de croissance élevées.")
        elif peg > 2.5:
            score += 8
            reasons.append("PEG > 2.5: valorisation sensible aux attentes.")
    if forward_pe is not None and eps_est is not None and eps_est > 0 and forward_pe > max(35, eps_est * 3):
        score += 10
        reasons.append("Forward PE élevé par rapport à la croissance estimée.")
    return score, reasons


def _portfolio_crowding_score(analysis: dict[str, Any], portfolio_risk: dict[str, Any]) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    sector = str(analysis.get("sector") or "Unknown")
    sector_weight = safe_float((portfolio_risk.get("concentration_by_sector") or {}).get(sector)) or 0.0
    factors = {str(item) for item in (analysis.get("factor_exposure") or [])}
    tech_like = bool(factors & TECH_AI_SEMI_FACTORS) or str(analysis.get("benchmark_ticker") or "") == "SOXX"
    tech_weight = safe_float(portfolio_risk.get("tech_ai_semi_weight")) or 0.0

    if sector != "Unknown":
        if sector_weight > 0.55:
            score += 20
            reasons.append(f"Secteur déjà très concentré dans le portefeuille: {sector}.")
        elif sector_weight > 0.40:
            score += 14
            reasons.append(f"Secteur déjà concentré dans le portefeuille: {sector}.")
        elif sector_weight > 0.25:
            score += 7
            reasons.append(f"Secteur déjà significatif dans le portefeuille: {sector}.")

    if tech_like:
        if tech_weight > 0.60:
            score += 18
            reasons.append("Exposition portefeuille tech/IA/semi-conducteurs déjà très élevée.")
        elif tech_weight > 0.40:
            score += 10
            reasons.append("Exposition portefeuille tech/IA/semi-conducteurs déjà élevée.")
    return score, reasons


def _full_cycle_normalization_score(profile: str, analysis: dict[str, Any]) -> tuple[float, list[str], dict[str, Any]]:
    if profile not in FULL_CYCLE_PROFILES:
        return 0.0, [], {
            "cycle_normalized_status": "NOT_CYCLICAL",
            "cycle_normalized_growth_cap": None,
            "cycle_adjusted_growth_estimate": safe_float(analysis.get("eps_growth_estimated_3_5y")),
            "cycle_normalized_earnings_risk_score": 0.0,
            "cycle_normalized_earnings_reasons": [],
        }

    cap = _normalized_growth_cap(profile, analysis)
    eps_est = _as_percent_points(analysis.get("eps_growth_estimated_3_5y"))
    eps_hist = _as_percent_points(analysis.get("eps_growth_5y"))
    earnings_growth = _as_percent_points(analysis.get("earnings_growth"))
    revenue_growth = _as_percent_points(analysis.get("revenue_growth"))
    stock_return = _as_percent_points(analysis.get("stock_return_1y"))
    drawdown = _as_decimal(analysis.get("drawdown_from_12m_high"))
    forward_pe = safe_float(analysis.get("forward_pe"))
    trailing_pe = safe_float(analysis.get("trailing_pe"))
    profit_margin = safe_float(analysis.get("profit_margins"))

    available = [value for value in [eps_est, eps_hist, earnings_growth, revenue_growth, stock_return, forward_pe, trailing_pe, profit_margin] if value is not None]
    if len(available) < 3:
        return 6.0, ["Données insuffisantes pour normaliser le cycle complet."], {
            "cycle_normalized_status": "INSUFFICIENT_CYCLE_DATA",
            "cycle_normalized_growth_cap": cap,
            "cycle_adjusted_growth_estimate": min(eps_est, cap) if eps_est is not None else None,
            "cycle_normalized_earnings_risk_score": 6.0,
            "cycle_normalized_earnings_reasons": ["Données insuffisantes pour normaliser le cycle complet."],
        }

    score = 0.0
    reasons: list[str] = []
    adjusted_growth = min(eps_est, cap) if eps_est is not None else None

    if eps_est is not None and eps_est > cap + 5:
        if eps_est > cap + 15:
            score += 16
            reasons.append("Croissance future estimée très au-dessus du niveau normalisé du cycle.")
        else:
            score += 9
            reasons.append("Croissance future estimée au-dessus du niveau normalisé du cycle.")

    recent_growth = first_present_percent(earnings_growth, eps_hist)
    if recent_growth is not None:
        if recent_growth > cap * 4:
            score += 20
            reasons.append("Croissance des bénéfices récente exceptionnelle: risque de bénéfices de haut de cycle.")
        elif recent_growth > cap * 2.5:
            score += 12
            reasons.append("Croissance des bénéfices récente très supérieure au cycle normal.")

    if revenue_growth is not None and revenue_growth > cap * 2:
        score += 6
        reasons.append("Croissance des revenus très supérieure au rythme normalisé du cycle.")

    if stock_return is not None and drawdown is not None and stock_return > 40 and drawdown > -0.08:
        score += 8
        reasons.append("Titre fort et proche du sommet: risque d’acheter après une phase déjà favorable du cycle.")

    if recent_growth is not None and recent_growth > cap * 2.5 and forward_pe is not None and forward_pe <= max(22.0, cap * 1.6):
        score += 9
        reasons.append("P/E raisonnable malgré profits très élevés: possible illusion de valorisation de haut de cycle.")

    if trailing_pe is not None and forward_pe is not None and trailing_pe > forward_pe * 2.2 and profile in {"SEMI_CAPEX_CYCLE", "TECH_AI_GROWTH_THEME"}:
        score += 6
        reasons.append("Écart important entre trailing P/E et forward P/E: attentes très dépendantes du prochain cycle de bénéfices.")

    margin_ceiling = NORMALIZED_MARGIN_CEILINGS.get(profile)
    if profit_margin is not None and margin_ceiling is not None:
        if profit_margin > margin_ceiling + 0.12:
            score += 12
            reasons.append("Marge actuelle très supérieure au niveau prudent de cycle complet.")
        elif profit_margin > margin_ceiling:
            score += 7
            reasons.append("Marge actuelle supérieure au niveau prudent de cycle complet.")

    if drawdown is not None and drawdown <= -0.25:
        score = max(0.0, score - 4.0)
        reasons.append("Drawdown important: le risque de payer le sommet du cycle est partiellement réduit.")

    score = round(clamp(score, 0, 35), 2)
    if score >= 26:
        status = "POSSIBLE_PEAK_EARNINGS"
    elif score >= 14:
        status = "ABOVE_NORMAL_CYCLE"
    elif score > 0:
        status = "WATCH_CYCLE_NORMALIZATION"
    else:
        status = "NORMALIZED_OK"
        reasons.append("Aucun signal fort de bénéfices au-dessus du cycle normalisé.")

    return score, reasons, {
        "cycle_normalized_status": status,
        "cycle_normalized_growth_cap": cap,
        "cycle_adjusted_growth_estimate": round(adjusted_growth, 3) if adjusted_growth is not None else None,
        "cycle_normalized_earnings_risk_score": score,
        "cycle_normalized_earnings_reasons": reasons,
    }


def first_present_percent(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _normalized_growth_cap(profile: str, analysis: dict[str, Any]) -> float:
    cap = NORMALIZED_GROWTH_CAPS.get(profile, 12.0)
    if analysis.get("moat_clear") is True and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}:
        cap += 2.0
    if profile == "SEMI_CAPEX_CYCLE" and safe_float(analysis.get("market_cap")) and (safe_float(analysis.get("market_cap")) or 0.0) >= 100_000_000_000:
        cap += 2.0
    return round(cap, 2)


def _risk_level(score: float) -> str:
    if score >= 65:
        return "EXTREME"
    if score >= 45:
        return "HIGH"
    if score >= 25:
        return "MEDIUM"
    return "LOW"


def _comment(level: str) -> str:
    if level == "EXTREME":
        return "Risque élevé de payer un thème/cycle très avancé: allocation fortement limitée, pas un signal de vente automatique."
    if level == "HIGH":
        return "Risque de thème chaud ou de cycle favorable déjà reflété: allocation réduite et validation manuelle recommandée."
    if level == "MEDIUM":
        return "Risque de cycle/tendance présent mais acceptable avec sizing prudent."
    return "Risque de cycle/tendance faible avec les données disponibles."


def _as_decimal(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if abs(number) > 2:
        return number / 100
    return number


def _as_percent_points(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if -5 <= number <= 5:
        return number * 100
    return number


def _lower(value: Any) -> str:
    return str(value or "").lower()


def _list_text(values: Any) -> str:
    if not values:
        return "Aucun"
    if isinstance(values, list):
        return "; ".join(str(value) for value in values if str(value))
    return str(values)


def _cycle_row_sort_key(row: dict[str, Any]) -> tuple[int, float, str]:
    level_rank = {"EXTREME": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(str(row.get("cycle_bubble_risk_level")), 0)
    return level_rank, safe_float(row.get("cycle_bubble_score")) or 0.0, str(row.get("ticker"))
