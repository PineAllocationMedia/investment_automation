from __future__ import annotations

import re
from typing import Any

from .utils import clamp, safe_float


MARKET_GROWTH_THESIS_COLUMNS = [
    "universe",
    "ticker",
    "market_growth_thesis_score",
    "market_growth_thesis_status",
    "market_growth_thesis_adjustment",
    "market_growth_thesis_confidence",
    "market_growth_thesis_themes",
    "market_growth_thesis_sources",
    "market_growth_thesis_reason",
]


THEME_CATALOG = {
    "AI_CLOUD_SOFTWARE": {
        "keywords": {"ai", "cloud", "software", "saas", "data", "cybersecurity", "digital"},
        "score": 18.0,
        "sources": ["SEC/company filings", "OECD digital economy", "company IR"],
        "reason": "vent structurel numerisation, cloud, automatisation logicielle et IA.",
    },
    "SEMICONDUCTORS": {
        "keywords": {"semiconductor", "semiconductors", "semi", "chips", "foundry"},
        "score": 16.0,
        "sources": ["SIA semiconductor reports", "SEC/company filings", "company IR"],
        "reason": "demande structurelle liee au calcul, IA, donnees et infrastructure numerique.",
    },
    "DIGITAL_PAYMENTS": {
        "keywords": {"payments", "payment", "card", "fintech", "commerce", "consumer"},
        "score": 14.0,
        "sources": ["company filings", "World Bank financial inclusion", "company IR"],
        "reason": "transition durable du cash vers les paiements electroniques et reseaux mondiaux.",
    },
    "HEALTHCARE_INNOVATION": {
        "keywords": {"healthcare", "pharma", "pharmaceutical", "medical", "innovation", "diabetes", "obesity"},
        "score": 13.0,
        "sources": ["OECD health data", "World Bank demographics", "company filings"],
        "reason": "demographie, innovation medicale et besoins de sante persistants.",
    },
    "ELECTRIFICATION_AUTOMATION": {
        "keywords": {"electrification", "automation", "industrial", "engineering", "construction"},
        "score": 12.0,
        "sources": ["IEA electrification outlook", "World Bank infrastructure", "company filings"],
        "reason": "investissements durables en electrification, automatisation et infrastructures.",
    },
    "ENERGY_TRANSITION": {
        "keywords": {"renewable", "renewables", "utility", "power", "electricity", "clean energy", "solar", "wind"},
        "score": 9.0,
        "sources": ["IEA", "IRENA", "EIA", "company filings"],
        "reason": "besoin structurel d'energie, mais rendement tres sensible aux taux, prix et regulation.",
    },
    "FINANCIAL_MARKETS": {
        "keywords": {"bank", "financial", "asset", "insurance", "alternative_assets", "credit"},
        "score": 7.0,
        "sources": ["company filings", "IMF financial stability", "central bank data"],
        "reason": "croissance liee aux marches et au credit, mais fortement cyclique.",
    },
    "RESOURCES_COMMODITIES": {
        "keywords": {"mining", "metals", "commodity", "commodities", "resources", "oil", "gas", "energy"},
        "score": 4.0,
        "sources": ["EIA/IEA", "company filings", "commodity market data"],
        "reason": "demande possible, mais le cycle des prix domine souvent le rendement.",
    },
}


def compute_market_growth_thesis(analysis: dict[str, Any]) -> dict[str, Any]:
    """Score the long-term market runway with a deliberately modest sizing impact.

    This is not a news/hype engine. It uses available local analysis fields and a
    stable catalog of public-source evidence categories to decide whether the
    company's market has a durable tailwind.
    """

    themes = _matched_themes(analysis)
    score = 35.0
    reasons: list[str] = []
    sources: set[str] = set()

    sector_cagr = safe_float(analysis.get("sector_cagr_estimated"))
    benchmark_10y = _as_percent_points(analysis.get("benchmark_10y_cagr"))
    benchmark_5y = _as_percent_points(analysis.get("benchmark_5y_cagr"))
    revenue_growth = _as_percent_points(analysis.get("revenue_growth"))
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    eps_hist = safe_float(analysis.get("eps_growth_5y"))

    sector_points, sector_reason = _growth_points(sector_cagr, excellent=10.0, good=8.0, okay=5.0, max_points=18.0)
    score += sector_points
    reasons.append(sector_reason)

    if benchmark_10y is not None:
        points, reason = _growth_points(benchmark_10y, excellent=8.0, good=6.0, okay=3.0, max_points=12.0)
        score += points
        reasons.append("benchmark 10 ans: " + reason)
    else:
        reasons.append("benchmark 10 ans indisponible: la these de marche depend davantage des autres preuves.")

    if benchmark_5y is not None:
        points, reason = _growth_points(benchmark_5y, excellent=7.0, good=5.0, okay=2.0, max_points=7.0)
        score += points
        reasons.append("benchmark 5 ans: " + reason)

    if analysis.get("benchmark_above_sma_200") is True:
        score += 3.0
        reasons.append("benchmark sectoriel au-dessus de sa SMA 200.")

    theme_score = 0.0
    theme_names: list[str] = []
    for theme_name, theme in themes:
        theme_score += float(theme["score"])
        theme_names.append(theme_name)
        sources.update(str(source) for source in theme["sources"])
    if themes:
        score += min(theme_score, 24.0)
        reasons.append("themes detectes: " + "; ".join(str(theme["reason"]) for _, theme in themes[:3]))
    else:
        reasons.append("aucun grand theme structurel specifique detecte automatiquement.")

    company_growth_values = [value for value in [revenue_growth, eps_est, eps_hist] if value is not None]
    if company_growth_values:
        company_growth = max(company_growth_values)
        if company_growth >= 15:
            score += 10.0
            reasons.append("croissance entreprise forte et compatible avec un marche en expansion.")
        elif company_growth >= 8:
            score += 6.0
            reasons.append("croissance entreprise positive et compatible avec un marche sain.")
        elif company_growth >= 3:
            score += 2.5
            reasons.append("croissance entreprise positive mais moderee.")
        else:
            score -= 5.0
            reasons.append("croissance entreprise faible: le marche adressable ne se traduit pas encore clairement.")
    else:
        reasons.append("croissance entreprise indisponible: confiance reduite.")

    score += _source_quality_bonus(analysis, sources)
    penalty, penalty_reasons = _risk_penalty(analysis)
    score -= penalty
    reasons.extend(penalty_reasons)

    score = round(clamp(score, 0, 100), 2)
    confidence = _confidence_level(analysis, score, bool(themes))
    status = _status_for(score, analysis, theme_names)
    adjustment = _allocation_adjustment(score, status, analysis, confidence)

    if not sources:
        sources.update(["yfinance benchmark/market data", "local sector/factor mapping"])
    sources.update(_existing_source_labels(analysis))

    return {
        "market_growth_thesis_score": score,
        "market_growth_thesis_status": status,
        "market_growth_thesis_adjustment": adjustment,
        "market_growth_thesis_confidence": confidence,
        "market_growth_thesis_themes": theme_names,
        "market_growth_thesis_sources": sorted(sources),
        "market_growth_thesis_reason": " ".join(reasons),
    }


def market_growth_thesis_rows_for_csv(
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
            if row.get("benchmark_role") is True or str(row.get("asset_type") or "").upper() in {"ETF", "FNB"}:
                continue
            if row.get("market_growth_thesis_score") in {None, ""}:
                continue
            rows.append(
                {
                    "universe": universe,
                    "ticker": row.get("ticker_display", row.get("ticker")),
                    "market_growth_thesis_score": row.get("market_growth_thesis_score"),
                    "market_growth_thesis_status": row.get("market_growth_thesis_status"),
                    "market_growth_thesis_adjustment": row.get("market_growth_thesis_adjustment"),
                    "market_growth_thesis_confidence": row.get("market_growth_thesis_confidence"),
                    "market_growth_thesis_themes": _list_text(row.get("market_growth_thesis_themes")),
                    "market_growth_thesis_sources": _list_text(row.get("market_growth_thesis_sources")),
                    "market_growth_thesis_reason": row.get("market_growth_thesis_reason"),
                }
            )
    return sorted(rows, key=_row_sort_key, reverse=True)


def _matched_themes(analysis: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    text_parts = [
        analysis.get("ticker"),
        analysis.get("company_name"),
        analysis.get("company_name_found"),
        analysis.get("sector"),
        analysis.get("business_profile"),
        analysis.get("business_profile_label"),
        analysis.get("benchmark_ticker"),
        " ".join(str(item) for item in (analysis.get("factor_exposure") or [])),
    ]
    text = " ".join(str(part or "") for part in text_parts).lower()
    normalized_text = text.replace("_", " ")
    tokens = set(re.findall(r"[a-z0-9]+", normalized_text))
    matched = []
    for theme_name, theme in THEME_CATALOG.items():
        if any(_keyword_matches(str(keyword), text, normalized_text, tokens) for keyword in theme["keywords"]):
            matched.append((theme_name, theme))
    return matched


def _keyword_matches(keyword: str, raw_text: str, normalized_text: str, tokens: set[str]) -> bool:
    keyword = keyword.lower().strip()
    if not keyword:
        return False
    if "_" in keyword:
        return keyword in raw_text or keyword.replace("_", " ") in normalized_text
    if " " in keyword:
        return keyword in normalized_text
    return keyword in tokens


def _growth_points(value: float | None, *, excellent: float, good: float, okay: float, max_points: float) -> tuple[float, str]:
    if value is None:
        return 4.0, "donnee de croissance de marche indisponible."
    if value >= excellent:
        return max_points, f"croissance excellente ({value:.1f} %)."
    if value >= good:
        return max_points * 0.75, f"croissance solide ({value:.1f} %)."
    if value >= okay:
        return max_points * 0.45, f"croissance correcte ({value:.1f} %)."
    if value >= 0:
        return max_points * 0.15, f"croissance faible mais positive ({value:.1f} %)."
    return -4.0, f"croissance negative ({value:.1f} %)."


def _risk_penalty(analysis: dict[str, Any]) -> tuple[float, list[str]]:
    penalty = 0.0
    reasons: list[str] = []
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "").upper()
    if cycle_level == "EXTREME":
        penalty += 18.0
        reasons.append("risque cycle/bulle extreme: le vent de marche peut deja etre trop anticipe.")
    elif cycle_level == "HIGH":
        penalty += 10.0
        reasons.append("risque cycle/bulle eleve: prudence sur le narratif de marche.")
    elif cycle_level == "MEDIUM":
        penalty += 4.0
        reasons.append("risque cycle/bulle moyen.")

    profile = str(analysis.get("business_profile") or "")
    if profile in {"RESOURCES", "ENERGY_CYCLICAL"}:
        penalty += 7.0
        reasons.append("profil ressources/energie: le cycle des prix peut dominer la these long terme.")
    if analysis.get("quality_but_too_expensive") is True:
        penalty += 5.0
        reasons.append("qualite possiblement trop chere: le marche peut etre bon sans que le prix soit bon.")
    if str(analysis.get("data_reliability_level") or "").upper() == "LOW":
        penalty += 6.0
        reasons.append("fiabilite des donnees faible: these de marche moins exploitable.")
    return penalty, reasons


def _source_quality_bonus(analysis: dict[str, Any], sources: set[str]) -> float:
    bonus = 0.0
    if analysis.get("official_confirmed_fields") or analysis.get("sec_edgar_cik"):
        bonus += 3.0
        sources.add("SEC EDGAR/company filings")
    if analysis.get("research_report_sources"):
        bonus += 2.0
        sources.add("local BNCD/Morningstar reports")
    if analysis.get("news_context_headlines"):
        bonus += 1.0
        sources.add("free recent news context")
    if analysis.get("benchmark_ticker"):
        bonus += 1.0
        sources.add("sector benchmark proxy")
    return min(bonus, 6.0)


def _existing_source_labels(analysis: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    if analysis.get("official_data_sources"):
        labels.append("official data already fetched")
    if analysis.get("research_report_sources"):
        labels.append("local research report already parsed")
    if analysis.get("news_context_sources"):
        labels.append("news context already checked")
    return labels


def _confidence_level(analysis: dict[str, Any], score: float, has_theme: bool) -> str:
    reliability = safe_float(analysis.get("data_reliability_score"))
    missing = safe_float(analysis.get("score_missing_data_count")) or 0.0
    if reliability is not None and reliability >= 75 and missing <= 1 and has_theme:
        return "HIGH"
    if score >= 70 and missing <= 3:
        return "MEDIUM"
    if reliability is not None and reliability < 55:
        return "LOW"
    return "MEDIUM" if has_theme else "LOW"


def _status_for(score: float, analysis: dict[str, Any], themes: list[str]) -> str:
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "").upper()
    profile = str(analysis.get("business_profile") or "")
    sector_cagr = safe_float(analysis.get("sector_cagr_estimated"))
    if profile in {"BANK", "INSURANCE", "ASSET_MANAGER", "ALT_ASSET_MANAGER"} and (sector_cagr is None or sector_cagr < 5):
        return "MATURE_OR_LOW_GROWTH"
    if cycle_level == "EXTREME" and score >= 65:
        return "HYPE_RISK"
    if score >= 78 and cycle_level not in {"HIGH", "EXTREME"}:
        return "STRUCTURAL_TAILWIND"
    if score >= 65:
        return "ATTRACTIVE_BUT_CYCLICAL" if cycle_level in {"MEDIUM", "HIGH"} else "STRUCTURAL_TAILWIND"
    if score >= 50:
        return "PROMISING_BUT_UNPROVEN" if themes else "MATURE_OR_LOW_GROWTH"
    return "MATURE_OR_LOW_GROWTH"


def _allocation_adjustment(score: float, status: str, analysis: dict[str, Any], confidence: str) -> float:
    if status == "HYPE_RISK":
        return -3.0
    if confidence == "LOW":
        if score >= 75:
            return 0.5
        return -1.0 if score < 50 else 0.0
    if status == "STRUCTURAL_TAILWIND":
        if score >= 85:
            return 3.0
        if score >= 75:
            return 2.0
        return 1.0
    if status == "ATTRACTIVE_BUT_CYCLICAL":
        return 1.0 if score >= 75 and analysis.get("thesis_status") == "INTACT" else 0.0
    if status == "PROMISING_BUT_UNPROVEN":
        return 0.0
    return -2.0 if score < 45 else 0.0


def _as_percent_points(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    if -1.0 <= number <= 1.0:
        return number * 100
    return number


def _list_text(values: Any) -> str:
    if not values:
        return ""
    if isinstance(values, list):
        return ", ".join(str(value) for value in values if value not in {None, ""})
    return str(values)


def _row_sort_key(row: dict[str, Any]) -> tuple[float, str]:
    return safe_float(row.get("market_growth_thesis_score")) or 0.0, str(row.get("ticker"))
