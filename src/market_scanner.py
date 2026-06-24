from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark_relevance_engine import benchmark_relevance_level
from .utils import load_yaml, normalize_ticker, read_csv_records, safe_float, write_csv_records
from .watchlist_engine import compute_data_quality


MARKET_UNIVERSE_COLUMNS = ["ticker", "company_name"]
DEFAULT_COMPANY_NAMES = {
    "GOOGL": "Alphabet Inc.",
    "AMZN": "Amazon.com Inc.",
    "NVDA": "NVIDIA Corporation",
    "COST": "Costco Wholesale Corporation",
    "V": "Visa Inc.",
    "UNH": "UnitedHealth Group Incorporated",
    "HD": "The Home Depot Inc.",
    "ADBE": "Adobe Inc.",
    "OR.PA": "L'Oreal S.A.",
    "RMS.PA": "Hermes International SCA",
    "AIR.PA": "Airbus SE",
    "TSM": "Taiwan Semiconductor Manufacturing Company",
    "INTU": "Intuit Inc.",
    "ISRG": "Intuitive Surgical Inc.",
    "SPGI": "S&P Global Inc.",
    "MCO": "Moody's Corporation",
    "DHR": "Danaher Corporation",
    "LIN": "Linde plc",
    "ACN": "Accenture plc",
    "BRK-B": "Berkshire Hathaway Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "NVO": "Novo Nordisk A/S",
    "SAP": "SAP SE",
    "SONY": "Sony Group Corporation",
    "MELI": "MercadoLibre Inc.",
    "SHOP": "Shopify Inc.",
    "ROP": "Roper Technologies Inc.",
    "TXN": "Texas Instruments Incorporated",
    "NOW": "ServiceNow Inc.",
    "CRM": "Salesforce Inc.",
    "LRCX": "Lam Research Corporation",
    "KLAC": "KLA Corporation",
    "SNPS": "Synopsys Inc.",
    "CDNS": "Cadence Design Systems Inc.",
    "NPI.TO": "Northland Power Inc.",
    "BLX.TO": "Boralex Inc.",
}
MARKET_CANDIDATE_STATUSES = {
    "MANUAL_REVIEW_TOP_CANDIDATE",
    "PROMISING_BUT_INCOMPLETE",
    "TOO_EXPENSIVE",
    "REJECTED",
}
SCANNER_SCOPE_NOTE = "Le scanner analyse seulement l’univers fourni ou la liste par défaut. Il ne couvre pas tout le marché."


def create_market_universe_template(path: str | Path, rows: list[dict[str, Any]]) -> None:
    write_csv_records(path, rows, MARKET_UNIVERSE_COLUMNS)


def load_market_universe(config_path: str | Path, csv_path: str | Path) -> dict[str, dict[str, Any]]:
    csv_rows = [
        row
        for row in read_csv_records(csv_path)
        if normalize_ticker(row.get("ticker"))
    ]
    if csv_rows:
        return {
            normalize_ticker(row.get("ticker")): {
                "ticker": normalize_ticker(row.get("ticker")),
                "company_name": str(row.get("company_name") or "").strip(),
                "sector": str(row.get("sector") or "").strip(),
                "region": str(row.get("region") or "").strip(),
                "currency": str(row.get("currency") or "").strip(),
                "notes": str(row.get("notes") or "").strip(),
                "source": "data/market_universe.csv",
            }
            for row in csv_rows
        }

    configured = load_yaml(config_path)
    return {
        _configured_ticker(item): {
            "ticker": _configured_ticker(item),
            "company_name": _configured_company_name(item),
            "sector": "",
            "region": "",
            "currency": "",
            "notes": "",
            "source": "config/market_scanner.yaml",
        }
        for item in configured.get("default_universe", [])
        if _configured_ticker(item)
    }


def classify_market_candidate(analysis: dict[str, Any]) -> dict[str, Any]:
    score_total = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    data_quality = compute_data_quality(analysis)
    validation_status = str(analysis.get("ticker_validation_status") or "")
    coverage_status = str(analysis.get("ticker_coverage_status") or "")
    valuation_status = compute_valuation_status(analysis)
    prefilter_passed, prefilter_reason = market_prefilter(analysis)
    quality_too_expensive = analysis.get("quality_but_too_expensive") is True
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    cycle_hot = cycle_level in {"HIGH", "EXTREME"}

    if valuation_status in {"TOO_EXPENSIVE", "EXTREMELY_EXPENSIVE"} or quality_too_expensive:
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "candidate_status": "TOO_EXPENSIVE",
            "candidate_reason": "Qualité possible, mais valorisation trop exigeante. À analyser manuellement seulement.",
        }

    if (
        prefilter_passed
        and data_quality == "HIGH"
        and score_total >= 8.5
        and conviction >= 85
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("liquidation_status") == "GREEN"
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and not cycle_hot
    ):
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "candidate_status": "MANUAL_REVIEW_TOP_CANDIDATE",
            "candidate_reason": "À analyser manuellement avant ajout au portefeuille. Aucun achat automatique.",
        }

    if (score_total >= 7 or conviction >= 60) and data_quality in {"HIGH", "MEDIUM"}:
        reason = prefilter_reason
        if cycle_hot:
            reason = f"{reason}; risque cycle/bulle/tendance {cycle_level}: allocation potentielle à limiter"
        if coverage_status in {"LOW_FREE_DATA_COVERAGE", "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"}:
            reason = f"{reason}; données gratuites incomplètes à valider avant promotion"
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "candidate_status": "PROMISING_BUT_INCOMPLETE",
            "candidate_reason": f"Profil prometteur mais incomplet: {reason}",
        }

    return {
        "data_quality": data_quality,
        "valuation_status": valuation_status,
        "candidate_status": "REJECTED",
        "candidate_reason": f"Rejet mécanique du scanner: {prefilter_reason}",
    }


def market_prefilter(analysis: dict[str, Any]) -> tuple[bool, str]:
    reasons: list[str] = []
    market_cap = safe_float(analysis.get("market_cap"))
    eps_hist = safe_float(analysis.get("eps_growth_5y"))
    eps_est = safe_float(analysis.get("eps_growth_estimated_3_5y"))
    margins = safe_float(analysis.get("profit_margins"))
    forward_pe = safe_float(analysis.get("forward_pe"))
    peg = safe_float(analysis.get("peg"))
    price_above_sma = analysis.get("price_above_sma_200")
    stock_return_1y = safe_float(analysis.get("stock_return_1y"))
    benchmark_return_1y = safe_float(analysis.get("benchmark_return_1y"))
    relevance = benchmark_relevance_level(analysis)
    underperformance = (
        stock_return_1y - benchmark_return_1y
        if stock_return_1y is not None and benchmark_return_1y is not None
        else None
    )

    if market_cap is not None and market_cap < 10_000_000_000:
        reasons.append("market cap sous 10 G$ si disponible")
    if eps_hist is not None and eps_hist <= 0 and eps_est is not None and eps_est <= 0:
        reasons.append("croissance EPS non positive")
    if margins is not None and margins <= 0:
        reasons.append("marges négatives")
    if forward_pe is not None and forward_pe > 80:
        reasons.append("forward PE très élevé")
    if peg is not None and peg > 4:
        reasons.append("PEG extrême")
    underperformance_threshold = -0.35 if relevance == "LOW" else -0.20
    if price_above_sma is False and underperformance is not None and underperformance <= underperformance_threshold:
        reasons.append(f"prix sous SMA 200 avec forte sous-performance (pertinence benchmark {relevance})")
    if compute_data_quality(analysis) == "LOW":
        reasons.append("données insuffisantes")

    if reasons:
        return False, "; ".join(reasons)
    return True, "préfiltre de qualité respecté avec les données disponibles"


def compute_valuation_status(analysis: dict[str, Any]) -> str:
    ratio = safe_float(analysis.get("price_to_fair_value"))
    peg = safe_float(analysis.get("peg"))
    if (ratio is not None and ratio > 1.70) or (peg is not None and peg > 4):
        return "EXTREMELY_EXPENSIVE"
    if analysis.get("quality_but_too_expensive") is True or (ratio is not None and ratio > 1.40) or (peg is not None and peg > 3):
        return "TOO_EXPENSIVE"
    if (ratio is not None and ratio > 1.20) or (peg is not None and peg > 2.5):
        return "MODERATELY_EXPENSIVE"
    return "NOT_EXPENSIVE"


def build_market_candidate_rows(
    analyses: dict[str, dict[str, Any]], universe: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for analysis in sorted(analyses.values(), key=_candidate_sort_key, reverse=True):
        ticker = analysis.get("ticker")
        metadata = universe.get(ticker, {})
        rows.append(
            {
                "ticker": ticker,
                "ticker_display": analysis.get("ticker_display", ticker),
                "resolved_ticker": analysis.get("resolved_ticker", ticker),
                "company_name": metadata.get("company_name", ""),
                "score_total": analysis.get("score_total"),
                "score_confidence_range": analysis.get("score_confidence_range"),
                "score_confidence_label": analysis.get("score_confidence_label"),
                "conviction_score": analysis.get("conviction_score"),
                "conviction_confidence_range": analysis.get("conviction_confidence_range"),
                "conviction_confidence_label": analysis.get("conviction_confidence_label"),
                "expected_cagr_quality": analysis.get("expected_cagr_quality"),
                "opportunity_cost_status": analysis.get("opportunity_cost_status"),
                "benchmark_ticker": analysis.get("benchmark_ticker"),
                "benchmark_relevance_level": analysis.get("benchmark_relevance_level"),
                "ticker_validation_status": analysis.get("ticker_validation_status"),
                "ticker_coverage_status": analysis.get("ticker_coverage_status"),
                "free_data_coverage_class": analysis.get("free_data_coverage_class"),
                "suggested_yahoo_tickers": analysis.get("suggested_yahoo_tickers"),
                "cycle_bubble_risk_level": analysis.get("cycle_bubble_risk_level"),
                "cycle_bubble_score": analysis.get("cycle_bubble_score"),
                "double_counting_risk_level": analysis.get("double_counting_risk_level"),
                "double_counting_adjustment": analysis.get("double_counting_adjustment"),
                "hidden_cluster_risk_level": analysis.get("hidden_cluster_risk_level"),
                "hidden_cluster_adjustment": analysis.get("hidden_cluster_adjustment"),
                "candidate_status": analysis.get("candidate_status"),
                "reason": analysis.get("candidate_reason"),
            }
        )
    return rows


def _candidate_sort_key(analysis: dict[str, Any]) -> tuple[int, float, float]:
    status_rank = {
        "MANUAL_REVIEW_TOP_CANDIDATE": 4,
        "PROMISING_BUT_INCOMPLETE": 3,
        "TOO_EXPENSIVE": 2,
        "REJECTED": 1,
    }.get(str(analysis.get("candidate_status")), 0)
    return (
        status_rank,
        safe_float(analysis.get("conviction_score")) or 0.0,
        safe_float(analysis.get("score_total")) or 0.0,
    )


def _configured_ticker(item: Any) -> str:
    if isinstance(item, dict):
        return normalize_ticker(item.get("ticker"))
    return normalize_ticker(item)


def _configured_company_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("company_name") or "").strip()
    return DEFAULT_COMPANY_NAMES.get(normalize_ticker(item), "")
    if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "candidate_status": "REJECTED",
            "candidate_reason": "Ticker ou nom de compagnie à valider avant toute analyse de promotion.",
        }
