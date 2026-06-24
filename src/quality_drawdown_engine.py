from __future__ import annotations

from typing import Any

from .asset_type_engine import is_etf_asset_analysis
from .utils import clamp, safe_float


QUALITY_DRAWDOWN_COLUMNS = [
    "universe",
    "ticker",
    "quality_drawdown_status",
    "quality_drawdown_score",
    "quality_drawdown_allocation_adjustment",
    "quality_drawdown_reason",
    "news_context_status",
    "news_context_reason",
    "news_context_sources",
    "news_context_source_channels",
    "news_context_search_queries",
    "news_context_headlines",
]

FUNDAMENTAL_RISK_KEYWORDS = {
    "cuts guidance",
    "cut guidance",
    "lowers guidance",
    "guidance cut",
    "profit warning",
    "misses revenue",
    "misses earnings",
    "weak demand",
    "slowing growth",
    "sales decline",
    "margin pressure",
    "profit falls",
    "earnings fall",
    "loss widens",
    "cash burn",
    "debt downgrade",
    "default",
    "going concern",
    "bankruptcy",
    "insolvency",
    "faillite",
}

REGULATORY_OR_LEGAL_KEYWORDS = {
    "antitrust",
    "lawsuit",
    "class action",
    "investigation",
    "probe",
    "sec charges",
    "doj",
    "ftc",
    "regulator",
    "regulatory",
    "fraud",
    "accounting",
    "settlement",
}

SECTOR_OR_MACRO_KEYWORDS = {
    "rates",
    "rate fears",
    "inflation",
    "tariff",
    "recession",
    "macro",
    "sector",
    "selloff",
    "sell-off",
    "rotation",
    "market pullback",
    "tech rout",
    "ai trade",
}

TEMPORARY_REACTION_KEYWORDS = {
    "stock falls after",
    "shares fall after",
    "stock drops after",
    "shares drop after",
    "profit taking",
    "valuation concern",
    "valuation concerns",
    "multiple compression",
    "market reaction",
    "despite beat",
    "beats estimates",
    "raises guidance",
    "reaffirms",
}


def apply_quality_drawdown_context(*analysis_groups: dict[str, dict[str, Any]]) -> None:
    for group in analysis_groups:
        for analysis in group.values():
            if analysis.get("ticker") == "VFV.TO" or is_etf_asset_analysis(analysis):
                continue
            analysis.update(compute_quality_drawdown_opportunity(analysis))


def compute_quality_drawdown_opportunity(analysis: dict[str, Any]) -> dict[str, Any]:
    news_context = classify_news_context(analysis)
    if not _has_price_weakness(analysis):
        return {
            **news_context,
            "quality_drawdown_status": "NO_DRAWDOWN_SIGNAL",
            "quality_drawdown_score": 0.0,
            "quality_drawdown_allocation_adjustment": 0.0,
            "quality_drawdown_reason": "Aucune faiblesse de prix assez importante pour activer la règle quality drawdown.",
        }

    score = _quality_drawdown_score(analysis)
    hard_block_reasons = _hard_block_reasons(analysis, news_context)
    if hard_block_reasons:
        status = "PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK"
        if str(analysis.get("thesis_status") or "") in {"WEAKENING", "BROKEN", "UNCERTAIN"} or str(
            analysis.get("liquidation_status") or ""
        ) in {"ORANGE", "RED"}:
            status = "AVOID_FALLING_KNIFE"
        return {
            **news_context,
            "quality_drawdown_status": status,
            "quality_drawdown_score": score,
            "quality_drawdown_allocation_adjustment": -6.0 if status == "PRICE_WEAKNESS_WITH_FUNDAMENTAL_RISK" else -10.0,
            "quality_drawdown_reason": "Baisse de prix détectée, mais le modèle refuse de la traiter comme opportunité: "
            + "; ".join(hard_block_reasons),
        }

    if score >= 78:
        adjustment = _opportunity_adjustment(news_context)
        return {
            **news_context,
            "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
            "quality_drawdown_score": score,
            "quality_drawdown_allocation_adjustment": adjustment,
            "quality_drawdown_reason": (
                "Baisse de prix importante avec thèse intacte, vente GREEN, qualité/durabilité élevées et "
                "aucun signal fondamental confirmé. La faiblesse du prix devient une opportunité potentielle, "
                "mais le sizing reste limité par les autres garde-fous."
            ),
        }

    if score >= 62:
        return {
            **news_context,
            "quality_drawdown_status": "QUALITY_DRAWDOWN_REVIEW",
            "quality_drawdown_score": score,
            "quality_drawdown_allocation_adjustment": 1.5,
            "quality_drawdown_reason": (
                "Baisse de prix sur une entreprise possiblement solide, mais les preuves ne sont pas assez fortes "
                "pour en faire une opportunité prioritaire."
            ),
        }

    return {
        **news_context,
        "quality_drawdown_status": "NORMAL_PULLBACK_OR_WEAK_SETUP",
        "quality_drawdown_score": score,
        "quality_drawdown_allocation_adjustment": 0.0,
        "quality_drawdown_reason": (
            "La baisse est détectée, mais la qualité, la croissance, les preuves ou la valorisation ne justifient "
            "pas de bonifier l'allocation."
        ),
    }


def classify_news_context(analysis: dict[str, Any]) -> dict[str, Any]:
    triggered = _news_check_triggered(analysis)
    headlines = _as_list(analysis.get("news_context_headlines"))
    sources = _as_list(analysis.get("news_context_sources"))
    checked_at = analysis.get("news_context_checked_at") or analysis.get("news_checked_at")
    if not triggered:
        return _news_result(
            "NOT_TRIGGERED",
            "Pas de baisse ou changement assez important pour utiliser les nouvelles comme diagnostic.",
            headlines,
            sources,
            checked_at,
            triggered=False,
        )
    if not headlines:
        return _news_result(
            "NO_RECENT_NEWS_FOUND",
            "Aucun titre de nouvelle gratuit disponible dans le flux yfinance/Yahoo Finance au moment de l'analyse.",
            headlines,
            sources,
            checked_at,
        )

    text = " ".join(headlines).lower()
    fundamental_hits = _keyword_hits(text, FUNDAMENTAL_RISK_KEYWORDS)
    legal_hits = _keyword_hits(text, REGULATORY_OR_LEGAL_KEYWORDS)
    macro_hits = _keyword_hits(text, SECTOR_OR_MACRO_KEYWORDS)
    temporary_hits = _keyword_hits(text, TEMPORARY_REACTION_KEYWORDS)

    if legal_hits and (fundamental_hits or len(legal_hits) >= 2):
        return _news_result(
            "REGULATORY_OR_LEGAL_RISK_REPORTED",
            "Des titres récents mentionnent un risque réglementaire, légal ou d'enquête: " + ", ".join(legal_hits[:3]) + ".",
            headlines,
            sources,
            checked_at,
        )
    if fundamental_hits:
        return _news_result(
            "FUNDAMENTAL_DETERIORATION_REPORTED",
            "Des titres récents mentionnent une possible détérioration fondamentale: "
            + ", ".join(fundamental_hits[:3])
            + ".",
            headlines,
            sources,
            checked_at,
        )
    if macro_hits and not temporary_hits:
        return _news_result(
            "SECTOR_OR_MACRO_PRESSURE",
            "Les nouvelles pointent surtout vers une pression de marché, de secteur ou de macro: "
            + ", ".join(macro_hits[:3])
            + ".",
            headlines,
            sources,
            checked_at,
        )
    if temporary_hits:
        return _news_result(
            "TEMPORARY_MARKET_REACTION",
            "Les titres disponibles ressemblent surtout à une réaction de marché ou de valorisation: "
            + ", ".join(temporary_hits[:3])
            + ".",
            headlines,
            sources,
            checked_at,
        )
    return _news_result(
        "UNKNOWN_OR_MIXED",
        "Les titres gratuits ne donnent pas un diagnostic clair; le modèle conserve la prudence des données fondamentales.",
        headlines,
        sources,
        checked_at,
    )


def quality_drawdown_rows_for_csv(*analysis_groups: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in analysis_groups:
        for row in group.values():
            status = str(row.get("quality_drawdown_status") or "")
            if not status:
                continue
            rows.append(
                {
                    "universe": row.get("universe"),
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "quality_drawdown_status": status,
                    "quality_drawdown_score": row.get("quality_drawdown_score"),
                    "quality_drawdown_allocation_adjustment": row.get("quality_drawdown_allocation_adjustment"),
                    "quality_drawdown_reason": row.get("quality_drawdown_reason"),
                    "news_context_status": row.get("news_context_status"),
                    "news_context_reason": row.get("news_context_reason"),
                    "news_context_sources": "; ".join(_as_list(row.get("news_context_sources"))),
                    "news_context_source_channels": "; ".join(_as_list(row.get("news_context_source_channels"))),
                    "news_context_search_queries": "; ".join(_as_list(row.get("news_context_search_queries"))),
                    "news_context_headlines": "; ".join(_as_list(row.get("news_context_headlines"))[:5]),
                }
            )
    return rows


def _has_price_weakness(analysis: dict[str, Any]) -> bool:
    drawdown_12m = safe_float(analysis.get("drawdown_from_12m_high"))
    drawdown_8m = safe_float(analysis.get("drawdown_from_8m_high"))
    stock_return = safe_float(analysis.get("stock_return_1y"))
    benchmark_return = safe_float(analysis.get("benchmark_return_1y"))
    underperformance = (
        stock_return - benchmark_return if stock_return is not None and benchmark_return is not None else None
    )
    return any(
        [
            drawdown_12m is not None and drawdown_12m <= -0.18,
            drawdown_8m is not None and drawdown_8m <= -0.12,
            analysis.get("price_above_sma_200") is False and drawdown_12m is not None and drawdown_12m <= -0.08,
            underperformance is not None and underperformance <= -0.15,
        ]
    )


def _news_check_triggered(analysis: dict[str, Any]) -> bool:
    if _has_price_weakness(analysis):
        return True
    if str(analysis.get("monitoring_status") or "NORMAL") in {"WATCH", "MANUAL_REVIEW", "CRITICAL"}:
        return True
    if analysis.get("allocation_decision") in {"DO_NOT_ADD", "NO_NEW_ALLOCATION"} and (
        safe_float(analysis.get("capital_allocation_score_change")) or 0.0
    ) < -3:
        return True
    return False


def _quality_drawdown_score(analysis: dict[str, Any]) -> float:
    score_total = (safe_float(analysis.get("score_total")) or 0.0) * 10.0
    conviction = safe_float(analysis.get("conviction_score")) or 50.0
    durability = safe_float(analysis.get("long_term_durability_score")) or 60.0
    cash_flow = safe_float(analysis.get("cash_flow_quality_score")) or 60.0
    reliability = safe_float(analysis.get("data_reliability_score")) or _reliability_level_score(analysis)
    valuation = _valuation_resilience_score(analysis)
    price_opportunity = _price_opportunity_points(analysis)
    return round(
        clamp(
            0.20 * score_total
            + 0.18 * conviction
            + 0.18 * durability
            + 0.16 * cash_flow
            + 0.12 * reliability
            + 0.10 * valuation
            + 0.06 * price_opportunity,
            0,
            100,
        ),
        2,
    )


def _hard_block_reasons(analysis: dict[str, Any], news_context: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if analysis.get("thesis_status") != "INTACT":
        reasons.append("thèse non intacte")
    if analysis.get("liquidation_status") in {"ORANGE", "RED"}:
        reasons.append(f"signal de vente {analysis.get('liquidation_status')}")
    if analysis.get("quality_but_too_expensive") is True:
        reasons.append("valorisation encore trop élevée malgré la baisse")
    if (safe_float(analysis.get("data_reliability_score")) or _reliability_level_score(analysis)) < 60:
        reasons.append("fiabilité des données insuffisante")
    if (safe_float(analysis.get("score_missing_data_count")) or 0.0) > 3:
        reasons.append("trop de données critiques manquantes")
    if analysis.get("confirmed_fundamental_sell_signals"):
        reasons.append("signal fondamental de vente confirmé")
    news_status = str(news_context.get("news_context_status") or "")
    if news_status in {"FUNDAMENTAL_DETERIORATION_REPORTED", "REGULATORY_OR_LEGAL_RISK_REPORTED"}:
        reasons.append("nouvelles récentes compatibles avec un risque fondamental")
    if analysis.get("cash_flow_quality_status") in {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"}:
        reasons.append("qualité du cash-flow insuffisante")
    if analysis.get("shareholder_discipline_status") == "HIGH_DILUTION_RISK":
        reasons.append("dilution/actionnaires défavorable")
    return reasons


def _opportunity_adjustment(news_context: dict[str, Any]) -> float:
    status = str(news_context.get("news_context_status") or "")
    if status == "TEMPORARY_MARKET_REACTION":
        return 6.0
    if status in {"SECTOR_OR_MACRO_PRESSURE", "NO_RECENT_NEWS_FOUND", "UNKNOWN_OR_MIXED"}:
        return 4.0
    return 3.0


def _valuation_resilience_score(analysis: dict[str, Any]) -> float:
    ratio = safe_float(analysis.get("price_to_fair_value"))
    peg = safe_float(analysis.get("peg"))
    score = 75.0
    if ratio is not None:
        if ratio <= 1.0:
            score += 20.0
        elif ratio <= 1.20:
            score += 10.0
        elif ratio > 1.40:
            score -= 35.0
        elif ratio > 1.25:
            score -= 15.0
    if peg is not None:
        if peg <= 2.0:
            score += 10.0
        elif peg > 3.0:
            score -= 25.0
        elif peg > 2.5:
            score -= 10.0
    return clamp(score, 0.0, 100.0)


def _price_opportunity_points(analysis: dict[str, Any]) -> float:
    drawdown = safe_float(analysis.get("drawdown_from_12m_high"))
    if drawdown is None:
        return 35.0
    if drawdown <= -0.35:
        return 95.0
    if drawdown <= -0.25:
        return 85.0
    if drawdown <= -0.18:
        return 70.0
    if drawdown <= -0.10:
        return 50.0
    return 25.0


def _reliability_level_score(analysis: dict[str, Any]) -> float:
    level = str(analysis.get("data_reliability_level") or analysis.get("confidence_level") or "MEDIUM").upper()
    return {"HIGH": 82.0, "MEDIUM": 65.0, "LOW": 35.0}.get(level, 60.0)


def _keyword_hits(text: str, keywords: set[str]) -> list[str]:
    return sorted({keyword for keyword in keywords if keyword in text})


def _news_result(
    status: str,
    reason: str,
    headlines: list[str],
    sources: list[str],
    checked_at: Any,
    triggered: bool = True,
) -> dict[str, Any]:
    return {
        "news_context_triggered": triggered,
        "news_context_status": status,
        "news_context_reason": reason,
        "news_context_headlines": headlines[:8],
        "news_context_sources": sources[:8],
        "news_context_checked_at": checked_at,
    }


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace("|", ";").split(";") if part.strip()]
    return [str(part).strip() for part in value if str(part).strip()]
