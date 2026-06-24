from __future__ import annotations

from collections import defaultdict
from typing import Any

from .utils import clamp, safe_float


HIDDEN_CLUSTER_FIELDS = [
    "hidden_cluster_risk_level",
    "hidden_cluster_exposure",
    "hidden_cluster_clusters",
    "hidden_cluster_adjustment",
    "hidden_cluster_reason",
    "hidden_cluster_guardrail",
    "hidden_cluster_exception_applied",
]


CLUSTER_DEFINITIONS: dict[str, dict[str, set[str]]] = {
    "AI_SEMI_CLOUD_INFRA": {
        "tickers": {
            "NVDA",
            "AVGO",
            "ASML",
            "TSM",
            "MSFT",
            "GOOGL",
            "AMZN",
            "META",
            "LRCX",
            "KLAC",
            "SNPS",
            "CDNS",
        },
        "terms": {
            "ai",
            "artificial intelligence",
            "semiconductor",
            "semiconductors",
            "cloud",
            "data center",
            "datacenter",
            "infrastructure",
            "chip",
            "chips",
        },
    },
    "MEGA_CAP_TECH_PLATFORMS": {
        "tickers": {"AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "NVDA", "ADBE", "CRM", "NOW", "INTU"},
        "terms": {"mega cap", "technology", "software", "platform", "internet", "advertising", "cloud"},
    },
    "RATES_SENSITIVE_GROWTH": {
        "tickers": {"TSLA", "BAM", "SHOP", "MELI", "NOW", "CRM", "INTU"},
        "terms": {"growth", "rates_sensitive", "rates sensitive", "consumer", "alternative_assets", "long duration"},
    },
    "INDUSTRIAL_ELECTRIFICATION_AUTOMATION": {
        "tickers": {"SIEGY", "SBGSY", "SCHN", "SU.PA", "AIR.PA", "WSP.TO"},
        "terms": {"industrial", "automation", "electrification", "engineering", "infrastructure", "machinery"},
    },
    "HEALTHCARE_INNOVATION": {
        "tickers": {"LLY", "NVO", "UNH", "ISRG", "DHR", "JNJ"},
        "terms": {"healthcare", "pharma", "pharmaceutical", "innovation", "medical", "glp", "biotech"},
    },
    "PAYMENTS_FINANCIAL_NETWORKS": {
        "tickers": {"MA", "V", "SPGI", "MCO", "BAM", "JPM"},
        "terms": {"payments", "financials", "financial", "credit", "rating", "alternative_assets"},
    },
    "CANADA_CAD_CLUSTER": {
        "tickers": {"BAM", "CSU.TO", "TOI.V", "WSP.TO", "NPI.TO", "BLX.TO", "VFV.TO"},
        "terms": {"canada", "cad", "toronto"},
    },
}

MODE_MAX_ADJUSTMENT = {
    "balanced": -4.5,
    "family-office": -4.0,
    "rational-aggressive": -3.5,
    "high-cagr": -3.0,
}


def apply_hidden_cluster_guardrails(
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]] | None,
    market_analyses: dict[str, dict[str, Any]] | None,
    discovery_analyses: dict[str, dict[str, Any]] | None,
    portfolio_risk: dict[str, Any],
    *,
    mode: str = "high-cagr",
) -> None:
    cluster_exposures = compute_hidden_cluster_exposures(analyses)
    portfolio_risk["hidden_cluster_exposure"] = dict(
        sorted(cluster_exposures.items(), key=lambda item: item[1], reverse=True)
    )
    hidden_alerts = hidden_cluster_alerts(cluster_exposures)
    portfolio_risk["hidden_cluster_alerts"] = hidden_alerts
    portfolio_risk.setdefault("alerts", []).extend(hidden_alerts)

    for group in (analyses, watchlist_analyses or {}, market_analyses or {}, discovery_analyses or {}):
        for analysis in group.values():
            analysis.update(compute_hidden_cluster_context(analysis, cluster_exposures, mode=mode))


def compute_hidden_cluster_exposures(analyses: dict[str, dict[str, Any]]) -> dict[str, float]:
    exposures: defaultdict[str, float] = defaultdict(float)
    for analysis in analyses.values():
        weight = safe_float(analysis.get("position_weight")) or 0.0
        if weight <= 0:
            continue
        if _is_broad_benchmark(analysis):
            continue
        for cluster in clusters_for_analysis(analysis):
            exposures[cluster] += weight
    return dict(exposures)


def compute_hidden_cluster_context(
    analysis: dict[str, Any],
    cluster_exposures: dict[str, float],
    *,
    mode: str = "high-cagr",
) -> dict[str, Any]:
    if _is_broad_benchmark(analysis) or _is_non_company_etf(analysis):
        return _result(
            level="ETF",
            exposure=0.0,
            clusters=[],
            adjustment=0.0,
            reason="Non applicable à un ETF large ou à un actif indiciel.",
            exception=False,
        )
    clusters = sorted(clusters_for_analysis(analysis))
    if not clusters:
        return _result("LOW", 0.0, [], 0.0, "Aucun cluster caché significatif détecté.", False)

    max_exposure = max((safe_float(cluster_exposures.get(cluster)) or 0.0) for cluster in clusters)
    level = _risk_level(max_exposure)
    adjustment = _base_adjustment(level, mode)
    exception = False
    if adjustment < 0 and _exceptional_compounder_exception(analysis):
        exception = True
        adjustment = round(adjustment * 0.35, 2)
    reason = _reason(level, max_exposure, clusters, adjustment, exception)
    return _result(level, max_exposure, clusters, adjustment, reason, exception)


def clusters_for_analysis(analysis: dict[str, Any]) -> set[str]:
    ticker = str(analysis.get("ticker") or "").upper()
    text = _analysis_text(analysis)
    clusters: set[str] = set()
    for name, definition in CLUSTER_DEFINITIONS.items():
        if ticker in definition["tickers"] or _text_has_term(text, definition["terms"]):
            clusters.add(name)
    return clusters


def hidden_cluster_alerts(cluster_exposures: dict[str, float]) -> list[dict[str, Any]]:
    alerts = []
    for cluster, exposure in sorted(cluster_exposures.items(), key=lambda item: item[1], reverse=True):
        if exposure >= 0.55:
            level = "cluster caché extrême"
        elif exposure >= 0.40:
            level = "cluster caché élevé"
        else:
            continue
        alerts.append(
            {
                "risk_type": "cluster_caché",
                "name": cluster,
                "weight": round(exposure, 4),
                "alert": level,
            }
        )
    return alerts


def hidden_cluster_rows_for_report(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    display = []
    for row in rows:
        level = str(row.get("hidden_cluster_risk_level") or "LOW")
        adjustment = safe_float(row.get("hidden_cluster_adjustment")) or 0.0
        if level in {"LOW", "ETF"} and adjustment == 0:
            continue
        display.append(
            {
                "ticker": row.get("ticker"),
                "niveau": level,
                "exposition_cluster": round(safe_float(row.get("hidden_cluster_exposure")) or 0.0, 4),
                "ajustement_sizing": adjustment,
                "clusters": row.get("hidden_cluster_clusters") or "",
                "lecture": row.get("hidden_cluster_reason") or "",
            }
        )
    return display


def compact_hidden_cluster_rows(
    rows: list[dict[str, Any]],
    allocated_tickers: set[str] | None = None,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    allocated_tickers = allocated_tickers or set()
    all_rows = hidden_cluster_rows_for_report(rows)
    all_rows.sort(
        key=lambda row: (
            str(row.get("ticker") or "") in allocated_tickers,
            abs(safe_float(row.get("ajustement_sizing")) or 0.0),
            safe_float(row.get("exposition_cluster")) or 0.0,
        ),
        reverse=True,
    )
    return all_rows[:limit]


def _analysis_text(analysis: dict[str, Any]) -> str:
    pieces = [
        analysis.get("ticker"),
        analysis.get("sector"),
        analysis.get("industry"),
        analysis.get("sector_name"),
        analysis.get("region"),
        analysis.get("currency"),
        analysis.get("expected_cagr_quality"),
        analysis.get("market_growth_thesis_status"),
        analysis.get("cycle_bubble_risk_level"),
    ]
    factors = analysis.get("factor_exposure") or []
    if isinstance(factors, list):
        pieces.extend(factors)
    else:
        pieces.append(factors)
    return " ".join(str(piece or "").replace("_", " ").replace("-", " ").lower() for piece in pieces)


def _text_has_term(text: str, terms: set[str]) -> bool:
    tokens = set(text.replace("/", " ").split())
    for term in terms:
        normalized = term.replace("_", " ").lower()
        if normalized == "ai":
            if "ai" in tokens:
                return True
        elif normalized in text:
            return True
    return False


def _risk_level(exposure: float) -> str:
    if exposure >= 0.55:
        return "EXTREME"
    if exposure >= 0.40:
        return "HIGH"
    if exposure >= 0.30:
        return "MEDIUM"
    return "LOW"


def _base_adjustment(level: str, mode: str) -> float:
    if level not in {"HIGH", "EXTREME"}:
        return 0.0
    max_adjustment = MODE_MAX_ADJUSTMENT.get(mode, MODE_MAX_ADJUSTMENT["rational-aggressive"])
    if level == "HIGH":
        return round(max(max_adjustment * 0.65, max_adjustment), 2)
    return max_adjustment


def _exceptional_compounder_exception(analysis: dict[str, Any]) -> bool:
    business_quality = safe_float(analysis.get("business_quality_score"))
    if business_quality is None:
        business_quality = (safe_float(analysis.get("score_total")) or 0.0) * 10
    return (
        analysis.get("thesis_status") == "INTACT"
        and analysis.get("liquidation_status") == "GREEN"
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and (safe_float(analysis.get("conviction_score")) or 0.0) >= 85
        and business_quality >= 80
        and str(analysis.get("data_reliability_level") or "") == "HIGH"
        and analysis.get("quality_but_too_expensive") is not True
    )


def _reason(level: str, exposure: float, clusters: list[str], adjustment: float, exception: bool) -> str:
    cluster_text = ", ".join(clusters) if clusters else "aucun"
    if level in {"LOW", "MEDIUM"}:
        return (
            f"Cluster(s) détecté(s): {cluster_text}; exposition actuelle {exposure:.1%}. "
            "Pas d’amortisseur de sizing requis."
        )
    if exception:
        return (
            f"Cluster caché {level.lower()} ({exposure:.1%}) sur {cluster_text}; amortisseur réduit car le titre "
            "reste exceptionnel, fiable, thèse intacte et clairement meilleur que VFV."
        )
    return (
        f"Cluster caché {level.lower()} ({exposure:.1%}) sur {cluster_text}; sizing légèrement amorti "
        "pour éviter d’ajouter trop de capital au même pari sous-jacent."
    )


def _is_broad_benchmark(analysis: dict[str, Any]) -> bool:
    ticker = str(analysis.get("ticker") or "").upper()
    sector = str(analysis.get("sector") or "").lower()
    return ticker == "VFV.TO" or analysis.get("benchmark_role") is True or "s&p 500" in sector or "broad market" in sector


def _is_non_company_etf(analysis: dict[str, Any]) -> bool:
    asset_type = str(analysis.get("asset_type") or "").upper()
    sector = str(analysis.get("sector") or "").lower()
    return asset_type.startswith("ETF") and ("broad" in sector or "balanced" in sector or "aggregate" in sector)


def _result(
    level: str,
    exposure: float,
    clusters: list[str],
    adjustment: float,
    reason: str,
    exception: bool,
) -> dict[str, Any]:
    return {
        "hidden_cluster_risk_level": level,
        "hidden_cluster_exposure": round(clamp(exposure, 0.0, 1.0), 4),
        "hidden_cluster_clusters": ", ".join(clusters),
        "hidden_cluster_adjustment": round(adjustment, 2),
        "hidden_cluster_reason": reason,
        "hidden_cluster_guardrail": (
            "Ajustement appliqué seulement au sizing; aucune vente automatique et aucun blocage d’un compounder exceptionnel."
        ),
        "hidden_cluster_exception_applied": bool(exception),
    }
