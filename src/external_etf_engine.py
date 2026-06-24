from __future__ import annotations

from typing import Any

from .asset_type_engine import etf_asset_profile, is_etf_asset_analysis
from .utils import normalize_ticker, safe_float


EXTERNAL_ETF_COLUMNS = [
    "ticker",
    "universe",
    "asset_type",
    "asset_focus",
    "mode",
    "external_etf_allocation_status",
    "external_etf_score",
    "capital_allocation_score",
    "mode_fit",
    "current_price",
    "price_above_sma_200",
    "stock_return_1y",
    "drawdown_from_12m_high",
    "reason",
]

EXTERNAL_ETF_UNIVERSES = {"WATCHLIST", "MARKET_SCANNER", "DISCOVERY_IDEAS"}

MODE_MIN_SCORES = {
    "balanced": 72.0,
    "family-office": 68.0,
    "rational-aggressive": 64.0,
    "high-cagr": 10_000.0,
}

MODE_ROLE_SCORES = {
    "balanced": {
        "ETF_CONSERVATIVE_ALLOCATION": 88,
        "ETF_BALANCED_ALLOCATION": 84,
        "ETF_LOW_VOLATILITY_EQUITY": 82,
        "ETF_BOND": 78,
        "ETF_DEFENSIVE_SECTOR": 76,
        "ETF_CASH_LIKE": 72,
        "ETF_DIVIDEND": 70,
        "ETF_S_AND_P_500": 70,
        "ETF_CANADA_EQUITY": 68,
        "ETF_BROAD_MARKET": 68,
        "ETF_REAL_ESTATE": 52,
        "ETF_NASDAQ_100": 42,
        "ETF_TECHNOLOGY": 36,
        "ETF_OR_FUND": 50,
    },
    "family-office": {
        "ETF_S_AND_P_500": 82,
        "ETF_BROAD_MARKET": 80,
        "ETF_BALANCED_ALLOCATION": 78,
        "ETF_LOW_VOLATILITY_EQUITY": 76,
        "ETF_CANADA_EQUITY": 74,
        "ETF_DIVIDEND": 72,
        "ETF_CONSERVATIVE_ALLOCATION": 70,
        "ETF_DEFENSIVE_SECTOR": 69,
        "ETF_BOND": 64,
        "ETF_CASH_LIKE": 58,
        "ETF_NASDAQ_100": 60,
        "ETF_TECHNOLOGY": 56,
        "ETF_REAL_ESTATE": 54,
        "ETF_OR_FUND": 56,
    },
    "rational-aggressive": {
        "ETF_S_AND_P_500": 80,
        "ETF_BROAD_MARKET": 78,
        "ETF_NASDAQ_100": 76,
        "ETF_TECHNOLOGY": 70,
        "ETF_CANADA_EQUITY": 70,
        "ETF_BALANCED_ALLOCATION": 66,
        "ETF_LOW_VOLATILITY_EQUITY": 64,
        "ETF_DIVIDEND": 62,
        "ETF_DEFENSIVE_SECTOR": 58,
        "ETF_CONSERVATIVE_ALLOCATION": 56,
        "ETF_REAL_ESTATE": 52,
        "ETF_BOND": 46,
        "ETF_CASH_LIKE": 38,
        "ETF_OR_FUND": 58,
    },
}

SPECULATIVE_ASSET_TYPES = {"ETF_BITCOIN"}
SPECULATIVE_NAME_TERMS = {
    "LEVERAGED",
    "2X",
    "3X",
    "INVERSE",
    "DAILY BULL",
    "DAILY BEAR",
    "ULTRA",
    "CALL OPTION",
    "COVERED CALL",
    "BITCOIN",
    "CRYPTO",
}
GROWTH_ETF_TYPES = {"ETF_NASDAQ_100", "ETF_TECHNOLOGY"}


def apply_external_etf_candidate_context(
    mode: str,
    portfolio_risk: dict[str, Any],
    *analysis_groups: dict[str, dict[str, Any]],
) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if is_external_etf_candidate(analysis):
                analysis.update(score_external_etf_candidate(analysis, mode, portfolio_risk))


def is_external_etf_candidate(analysis: dict[str, Any]) -> bool:
    return str(analysis.get("universe") or "") in EXTERNAL_ETF_UNIVERSES and is_etf_asset_analysis(analysis)


def is_external_etf_allocation_candidate(analysis: dict[str, Any]) -> bool:
    return is_external_etf_candidate(analysis) and bool(analysis.get("external_etf_allocation_status"))


def external_etf_is_eligible(analysis: dict[str, Any], mode: str) -> bool:
    if mode == "high-cagr":
        return False
    if not is_external_etf_allocation_candidate(analysis):
        return False
    if analysis.get("external_etf_allocation_status") != "ELIGIBLE_EXTERNAL_ETF_ALLOCATION":
        return False
    score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    return score >= MODE_MIN_SCORES.get(mode, 10_000.0)


def score_external_etf_candidate(
    analysis: dict[str, Any],
    mode: str,
    portfolio_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    portfolio_risk = portfolio_risk or {}
    ticker = normalize_ticker(analysis.get("ticker"))
    profile = etf_asset_profile(ticker, analysis, analysis.get("sector"))
    asset_type = str(profile.get("asset_type") or analysis.get("asset_type") or "ETF_OR_FUND")
    asset_focus = str(profile.get("asset_focus") or analysis.get("asset_focus") or "ETF")
    name = str(profile.get("asset_name") or analysis.get("asset_name") or analysis.get("company_name_found") or ticker)
    current_price = safe_float(analysis.get("current_price"))
    price_above_sma = analysis.get("price_above_sma_200")
    return_1y = safe_float(analysis.get("adjusted_stock_return_1y"))
    if return_1y is None:
        return_1y = safe_float(analysis.get("stock_return_1y"))
    drawdown = safe_float(analysis.get("drawdown_from_12m_high"))
    beta = safe_float(analysis.get("beta"))

    if mode == "high-cagr":
        return _external_etf_result(
            analysis,
            profile,
            mode,
            0.0,
            "DISABLED_FOR_HIGH_CAGR",
            "Mode high-cagr inchangé: les ETF externes ne reçoivent pas d'allocation automatique.",
            "DISABLED",
        )

    if _is_speculative_etf(asset_type, name):
        return _external_etf_result(
            analysis,
            profile,
            mode,
            0.0,
            "REJECTED_EXTERNAL_ETF",
            "ETF externe rejeté: levier, inverse, crypto, options ou exposition spéculative détectée.",
            "REJECTED_SPECULATIVE",
        )

    if current_price is None or current_price <= 0:
        return _external_etf_result(
            analysis,
            profile,
            mode,
            0.0,
            "INSUFFICIENT_ETF_DATA",
            "ETF externe non admissible: prix gratuit indisponible; contrairement aux ETF défensifs pré-approuvés, il faut des données de marché minimales.",
            "INSUFFICIENT_DATA",
        )

    base_scores = MODE_ROLE_SCORES.get(mode, {})
    score = float(base_scores.get(asset_type, base_scores.get("ETF_OR_FUND", 50)))
    reasons = [f"Rôle ETF {asset_focus}: base {score:.0f}/100 pour le mode {mode}."]

    if price_above_sma is True:
        score += 4
        reasons.append("Prix au-dessus de la SMA 200.")
    elif price_above_sma is False:
        score -= 7
        reasons.append("Prix sous SMA 200; allocation limitée par prudence.")

    if return_1y is not None:
        if return_1y >= 0.08:
            score += 4
            reasons.append("Rendement 1 an solide pour une exposition ETF.")
        elif return_1y >= 0:
            score += 2
            reasons.append("Rendement 1 an positif.")
        elif return_1y <= -0.15:
            score -= 8
            reasons.append("Rendement 1 an faible; risque de mauvais contexte ou d'exposition cyclique.")
        else:
            score -= 3
            reasons.append("Rendement 1 an négatif.")

    if drawdown is not None:
        if drawdown <= -0.25:
            score -= 8
            reasons.append("Drawdown élevé pour un ETF; pas traité comme rabais automatique.")
        elif drawdown <= -0.15:
            score -= 4
            reasons.append("Drawdown modéré.")

    if beta is not None:
        if mode == "balanced" and beta > 1.05:
            score -= 6
            reasons.append("Bêta trop élevé pour le mode balanced.")
        elif mode == "family-office" and beta > 1.20:
            score -= 4
            reasons.append("Bêta élevé pour family-office.")

    if asset_type in GROWTH_ETF_TYPES:
        tech_weight = safe_float(portfolio_risk.get("tech_ai_semi_weight")) or 0.0
        if mode == "balanced":
            score -= 18
            reasons.append("ETF croissance/technologie peu adapté au mode le plus prudent.")
        elif tech_weight > 0.40:
            penalty = 18 if mode == "family-office" else 12
            score -= penalty
            reasons.append("Portefeuille déjà exposé à tech/IA/semi; ETF croissance plafonné.")

    if asset_type in {"ETF_REAL_ESTATE"} and mode in {"balanced", "family-office"}:
        score -= 5
        reasons.append("Immobilier coté sensible aux taux; prudence en mode conservateur.")

    score = round(max(0.0, min(100.0, score)), 2)
    minimum = MODE_MIN_SCORES.get(mode, 10_000.0)
    status = "ELIGIBLE_EXTERNAL_ETF_ALLOCATION" if score >= minimum else "WATCH_ONLY_EXTERNAL_ETF"
    if status != "ELIGIBLE_EXTERNAL_ETF_ALLOCATION":
        reasons.append(f"Score sous le seuil ETF externe du mode ({minimum:.0f}).")

    return _external_etf_result(
        analysis,
        profile,
        mode,
        score,
        status,
        " ".join(reasons),
        _mode_fit_label(mode, asset_type),
    )


def external_etf_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for analysis in group.values():
            if not is_external_etf_allocation_candidate(analysis):
                continue
            rows.append({column: _external_etf_column_value(analysis, column) for column in EXTERNAL_ETF_COLUMNS})
    return sorted(
        rows,
        key=lambda row: (
            1 if row.get("external_etf_allocation_status") == "ELIGIBLE_EXTERNAL_ETF_ALLOCATION" else 0,
            safe_float(row.get("external_etf_score")) or 0.0,
            str(row.get("ticker") or ""),
        ),
        reverse=True,
    )


def _external_etf_result(
    analysis: dict[str, Any],
    profile: dict[str, str],
    mode: str,
    score: float,
    status: str,
    reason: str,
    mode_fit: str,
) -> dict[str, Any]:
    eligible = status == "ELIGIBLE_EXTERNAL_ETF_ALLOCATION"
    expected_quality = _expected_quality_for_external_etf(mode, str(profile.get("asset_type") or ""))
    opportunity = _opportunity_status_for_external_etf(str(profile.get("asset_type") or ""), mode)
    result = {
        "asset_type": profile.get("asset_type"),
        "asset_role": "EXTERNAL_ETF_CANDIDATE" if eligible else "EXTERNAL_ETF_WATCH_ONLY",
        "asset_name": profile.get("asset_name"),
        "asset_focus": profile.get("asset_focus"),
        "company_name_found": profile.get("company_name_found"),
        "external_etf_allocation_status": status,
        "external_etf_score": score,
        "external_etf_reason": reason,
        "external_etf_mode_fit": mode_fit,
        "external_etf_mode": mode,
        "capital_allocation_score": score if eligible else analysis.get("capital_allocation_score", "ETF"),
        "expected_cagr_quality": expected_quality,
        "opportunity_cost_status": opportunity,
        "opportunity_cost_reason": f"ETF externe évalué selon son rôle de portefeuille en mode {mode}, pas comme entreprise individuelle.",
        "add_eligibility_status": "ADD_ALLOWED" if eligible else "ETF_HOLD_ONLY",
        "add_eligibility_reason": reason,
        "add_eligibility_size": "LIMITED" if eligible else "NONE",
        "liquidation_status": "GREEN",
        "sell_status": "GREEN",
        "quality_but_too_expensive": False,
        "data_quality": "ETF",
        "data_reliability_level": "ETF",
        "requires_manual_validation_for_large_allocation": False,
    }
    universe = str(analysis.get("universe") or "")
    if universe == "WATCHLIST":
        result.update({"watchlist_status": status, "watchlist_reason": reason})
    elif universe == "MARKET_SCANNER":
        result.update({"candidate_status": status, "candidate_reason": reason, "valuation_status": "ETF_RULES"})
    elif universe == "DISCOVERY_IDEAS":
        result.update(
            {
                "discovery_status": status,
                "discovery_reason": reason,
                "discovery_suggested_action": "ETF externe analysé automatiquement; aucune promotion requise dans les modes non-high-cagr si le statut est admissible.",
                "valuation_status": "ETF_RULES",
            }
        )
    return result


def _external_etf_column_value(analysis: dict[str, Any], column: str) -> Any:
    if column == "reason":
        return analysis.get("external_etf_reason", "")
    if column == "mode_fit":
        return analysis.get("external_etf_mode_fit", "")
    if column == "mode":
        return analysis.get("external_etf_mode", "")
    return analysis.get(column, "")


def _is_speculative_etf(asset_type: str, name: str) -> bool:
    if asset_type in SPECULATIVE_ASSET_TYPES:
        return True
    upper_name = str(name or "").upper()
    return any(term in upper_name for term in SPECULATIVE_NAME_TERMS)


def _mode_fit_label(mode: str, asset_type: str) -> str:
    if mode == "balanced":
        return "préservation du patrimoine avec croissance raisonnable"
    if mode == "family-office":
        return "diversification professionnelle avec croissance contrôlée"
    if mode == "rational-aggressive":
        return "croissance diversifiée avec garde-fous"
    return "non applicable"


def _expected_quality_for_external_etf(mode: str, asset_type: str) -> str:
    if mode == "rational-aggressive" and asset_type in {"ETF_S_AND_P_500", "ETF_BROAD_MARKET", "ETF_NASDAQ_100", "ETF_TECHNOLOGY"}:
        return "HIGH"
    if mode == "family-office" and asset_type in {"ETF_S_AND_P_500", "ETF_BROAD_MARKET", "ETF_BALANCED_ALLOCATION"}:
        return "HIGH"
    return "MEDIUM"


def _opportunity_status_for_external_etf(asset_type: str, mode: str) -> str:
    if asset_type == "ETF_S_AND_P_500":
        return "SIMILAR_TO_VFV"
    if mode == "balanced" and asset_type in {"ETF_CONSERVATIVE_ALLOCATION", "ETF_BALANCED_ALLOCATION", "ETF_LOW_VOLATILITY_EQUITY", "ETF_BOND"}:
        return "ETF_COMPLEMENTS_VFV"
    if mode in {"family-office", "rational-aggressive"} and asset_type in {"ETF_BROAD_MARKET", "ETF_NASDAQ_100", "ETF_TECHNOLOGY"}:
        return "ETF_COMPLEMENTS_VFV"
    return "ETF_DIVERSIFICATION_TOOL"
