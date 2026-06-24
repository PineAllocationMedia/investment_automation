from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import load_yaml, normalize_ticker, read_csv_records, safe_float, write_csv_records


WATCHLIST_COLUMNS = ["ticker", "notes", "manual_priority"]
WATCHLIST_STATUSES = {
    "HIGH_PRIORITY_WATCH",
    "INTERESTING_BUT_WAIT",
    "TOO_EXPENSIVE",
    "INSUFFICIENT_DATA",
    "AVOID_FOR_NOW",
}


def create_watchlist_template(path: str | Path, tickers: list[str]) -> None:
    rows = [{"ticker": ticker, "notes": "", "manual_priority": "MEDIUM"} for ticker in tickers]
    write_csv_records(path, rows, WATCHLIST_COLUMNS)


def load_watchlist(config_path: str | Path, csv_path: str | Path) -> dict[str, dict[str, Any]]:
    csv_rows = [
        row
        for row in read_csv_records(csv_path)
        if normalize_ticker(row.get("ticker"))
    ]
    if csv_rows:
        return {
            normalize_ticker(row.get("ticker")): {
                "ticker": normalize_ticker(row.get("ticker")),
                "notes": str(row.get("notes") or "").strip(),
                "manual_priority": _priority(row.get("manual_priority")),
                "source": "data/watchlist.csv",
            }
            for row in csv_rows
        }

    configured = load_yaml(config_path).get("watchlist", [])
    return {
        normalize_ticker(ticker): {
            "ticker": normalize_ticker(ticker),
            "notes": "",
            "manual_priority": "MEDIUM",
            "source": "config/watchlist.yaml",
        }
        for ticker in configured
        if normalize_ticker(ticker)
    }


def classify_watchlist_analysis(analysis: dict[str, Any]) -> dict[str, Any]:
    score_total = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    missing_count = int(analysis.get("score_missing_data_count") or 0)
    data_quality = compute_data_quality(analysis)
    validation_status = str(analysis.get("ticker_validation_status") or "")
    coverage_status = str(analysis.get("ticker_coverage_status") or "")
    quality_too_expensive = analysis.get("quality_but_too_expensive") is True
    price_to_fair_value = safe_float(analysis.get("price_to_fair_value"))
    peg = safe_float(analysis.get("peg"))
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    cycle_hot = cycle_level in {"HIGH", "EXTREME"}
    valuation_extreme = quality_too_expensive or (peg is not None and peg > 3) or (
        price_to_fair_value is not None and price_to_fair_value > 1.40
    )

    if validation_status in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return {
            "watchlist_status": "INSUFFICIENT_DATA",
            "data_quality": data_quality,
            "watchlist_reason": "Ticker ou nom de compagnie à valider avant de juger la candidate.",
        }

    if missing_count > 5 or data_quality == "LOW":
        reason = "Trop de données critiques manquent pour juger la candidate."
        if coverage_status in {"LOW_FREE_DATA_COVERAGE", "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"}:
            reason = "Ticker probablement valide, mais données gratuites insuffisantes; rapport BNCD/Morningstar ou validation manuelle utile."
        return {
            "watchlist_status": "INSUFFICIENT_DATA",
            "data_quality": data_quality,
            "watchlist_reason": reason,
        }

    if valuation_extreme and score_total >= 8:
        return {
            "watchlist_status": "TOO_EXPENSIVE",
            "data_quality": data_quality,
            "watchlist_reason": "Qualité intéressante, mais valorisation trop exigeante.",
        }

    if (
        score_total >= 8.5
        and conviction >= 85
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and not valuation_extreme
        and not cycle_hot
    ):
        return {
            "watchlist_status": "HIGH_PRIORITY_WATCH",
            "data_quality": data_quality,
            "watchlist_reason": "Candidate de très haute qualité à surveiller de près, sans achat automatique.",
        }

    if score_total >= 8 and conviction >= 70:
        reason = "Profil intéressant, mais il manque un meilleur point d’entrée ou des validations."
        if cycle_hot:
            reason = f"{reason} Risque cycle/bulle/tendance {cycle_level}: sizing à limiter si ajoutée."
        return {
            "watchlist_status": "INTERESTING_BUT_WAIT",
            "data_quality": data_quality,
            "watchlist_reason": reason,
        }

    return {
        "watchlist_status": "AVOID_FOR_NOW",
        "data_quality": data_quality,
        "watchlist_reason": "La thèse, la qualité, la valorisation ou la confiance ne suffisent pas encore.",
    }


def build_watchlist_report_rows(analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for analysis in sorted(analyses.values(), key=_watchlist_sort_key, reverse=True):
        rows.append(
            {
                "ticker": analysis.get("ticker"),
                "ticker_display": analysis.get("ticker_display", analysis.get("ticker")),
                "resolved_ticker": analysis.get("resolved_ticker", analysis.get("ticker")),
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
                "watchlist_status": analysis.get("watchlist_status"),
                "reason": analysis.get("watchlist_reason"),
            }
        )
    return rows


def compute_data_quality(analysis: dict[str, Any]) -> str:
    missing_count = int(analysis.get("score_missing_data_count") or 0)
    current_price = safe_float(analysis.get("current_price"))
    auto_quality = str(analysis.get("auto_source_quality") or "").upper()
    reliability_level = str(analysis.get("data_reliability_level") or "").upper()
    manual_overrides = analysis.get("manual_override_fields") or []
    if reliability_level == "LOW":
        return "LOW"
    if auto_quality == "LOW" and not manual_overrides:
        return "LOW"
    if missing_count <= 1 and current_price is not None:
        if auto_quality == "MEDIUM" and not manual_overrides:
            return "MEDIUM"
        if reliability_level == "MEDIUM":
            return "MEDIUM"
        return "HIGH"
    if missing_count <= 3:
        return "MEDIUM"
    return "LOW"


def _priority(value: Any) -> str:
    text = str(value or "MEDIUM").strip().upper()
    return text if text in {"HIGH", "MEDIUM", "LOW"} else "MEDIUM"


def _watchlist_sort_key(analysis: dict[str, Any]) -> tuple[int, float, float]:
    status_rank = {
        "HIGH_PRIORITY_WATCH": 5,
        "INTERESTING_BUT_WAIT": 4,
        "TOO_EXPENSIVE": 3,
        "INSUFFICIENT_DATA": 2,
        "AVOID_FOR_NOW": 1,
    }.get(str(analysis.get("watchlist_status")), 0)
    return (
        status_rank,
        safe_float(analysis.get("conviction_score")) or 0.0,
        safe_float(analysis.get("score_total")) or 0.0,
    )
