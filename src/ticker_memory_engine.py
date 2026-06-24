from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import normalize_ticker, read_csv_records, safe_float, today_iso, write_csv_records


TICKER_MEMORY_COLUMNS = [
    "ticker",
    "ticker_display",
    "input_tickers",
    "resolved_ticker",
    "company_name_found",
    "sector",
    "sector_name",
    "industry",
    "region",
    "currency",
    "quote_currency",
    "asset_type",
    "factor_exposure",
    "ticker_validation_status",
    "ticker_coverage_status",
    "free_data_coverage_class",
    "free_data_coverage_score",
    "ticker_memory_status",
    "ticker_memory_action",
    "last_seen",
    "seen_this_run",
    "source",
    "notes",
]

UNKNOWN_VALUES = {"", "UNKNOWN", "N/D", "NA", "NONE", "NULL", "DONNEE PAS DISPO", "DONNÉE PAS DISPO"}


def load_ticker_memory(path: str | Path) -> dict[str, dict[str, Any]]:
    rows = read_csv_records(path)
    memory: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker") or row.get("resolved_ticker"))
        if ticker:
            memory[ticker] = dict(row)
    return memory


def apply_ticker_memory_to_sector_map(
    configured_sectors: dict[str, str],
    tickers: list[str],
    memory: dict[str, dict[str, Any]],
) -> dict[str, str]:
    enriched = dict(configured_sectors)
    for ticker in tickers:
        canonical = normalize_ticker(ticker)
        if _has_value(enriched.get(canonical)):
            continue
        row = memory.get(canonical, {})
        remembered_sector = _first_useful(row, ["sector", "sector_name", "industry"])
        if remembered_sector:
            enriched[canonical] = remembered_sector
    return enriched


def apply_ticker_memory_to_exposure_map(
    configured_exposures: dict[str, dict[str, Any]],
    tickers: list[str],
    memory: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    enriched = {ticker: dict(value) for ticker, value in configured_exposures.items()}
    for ticker in tickers:
        canonical = normalize_ticker(ticker)
        row = memory.get(canonical, {})
        if not row:
            continue
        current = dict(enriched.get(canonical, {}))
        if not _has_value(current.get("region")):
            current["region"] = row.get("region") or "Unknown"
        if not _has_value(current.get("currency")):
            current["currency"] = row.get("currency") or row.get("quote_currency") or "Unknown"
        if not current.get("factor_exposure") and row.get("factor_exposure"):
            current["factor_exposure"] = _parse_factor_exposure(row.get("factor_exposure"))
        current.setdefault("factor_exposure", [])
        enriched[canonical] = current
    return enriched


def build_ticker_memory_rows(
    analysis_groups: dict[str, dict[str, dict[str, Any]]],
    existing_memory: dict[str, dict[str, Any]] | None = None,
    date: str | None = None,
) -> list[dict[str, Any]]:
    existing_memory = existing_memory or {}
    date = date or today_iso()
    rows_by_ticker = {ticker: dict(row) for ticker, row in existing_memory.items()}

    seen: set[str] = set()
    for universe, group in analysis_groups.items():
        for ticker, analysis in sorted(group.items()):
            canonical = normalize_ticker(ticker)
            if not canonical:
                continue
            seen.add(canonical)
            previous = rows_by_ticker.get(canonical, {})
            rows_by_ticker[canonical] = _memory_row_from_analysis(canonical, analysis, previous, universe, date)

    for ticker, row in list(rows_by_ticker.items()):
        if ticker in seen:
            continue
        rows_by_ticker[ticker] = {
            **row,
            "seen_this_run": "FALSE",
            "ticker_memory_status": row.get("ticker_memory_status") or "CARRIED_FORWARD",
            "ticker_memory_action": "Conserve en mémoire locale; non utilisé si les données fraîches couvrent déjà le titre.",
        }

    return [rows_by_ticker[ticker] for ticker in sorted(rows_by_ticker)]


def update_ticker_memory(path: str | Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    write_csv_records(path, rows, TICKER_MEMORY_COLUMNS)
    return rows


def compact_ticker_memory_rows(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    review_rows = [
        row
        for row in rows
        if row.get("seen_this_run") == "TRUE"
        and row.get("ticker_memory_status")
        in {
            "NEEDS_TICKER_REVIEW",
            "LOW_FREE_COVERAGE",
            "CLASSIFICATION_CHANGED_REVIEW",
        }
    ]
    fallback_rows = [
        row
        for row in rows
        if row.get("seen_this_run") == "TRUE" and row.get("ticker_memory_status") == "FALLBACK_AVAILABLE"
    ]
    active_rows = [row for row in rows if row.get("seen_this_run") == "TRUE" and row.get("ticker_memory_status") == "ACTIVE"]
    return (review_rows + fallback_rows + active_rows)[:limit]


def ticker_memory_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "aucune mémoire ticker encore disponible."
    active = [row for row in rows if row.get("seen_this_run") == "TRUE"]
    review = [
        row
        for row in active
        if row.get("ticker_memory_status") in {"NEEDS_TICKER_REVIEW", "LOW_FREE_COVERAGE", "CLASSIFICATION_CHANGED_REVIEW"}
    ]
    fallback = [row for row in active if row.get("ticker_memory_status") == "FALLBACK_AVAILABLE"]
    if review:
        tickers = ", ".join(str(row.get("ticker") or "") for row in review[:5])
        return f"{len(review)} ticker(s) à valider ou mal couverts: {tickers}."
    if fallback:
        return f"{len(fallback)} ticker(s) ont une mémoire de secours disponible si les données fraîches manquent."
    return f"{len(active)} ticker(s) suivis; rien de problématique à signaler."


def _memory_row_from_analysis(
    ticker: str,
    analysis: dict[str, Any],
    previous: dict[str, Any],
    universe: str,
    date: str,
) -> dict[str, Any]:
    row = dict(previous)
    current = {
        "ticker": ticker,
        "ticker_display": analysis.get("ticker_display") or ticker,
        "input_tickers": analysis.get("input_tickers") or ticker,
        "resolved_ticker": analysis.get("resolved_ticker") or ticker,
        "company_name_found": _first_useful(
            analysis,
            ["company_name_found", "long_name", "short_name", "asset_name", "company_name"],
        ),
        "sector": analysis.get("sector"),
        "sector_name": analysis.get("sector_name"),
        "industry": analysis.get("industry"),
        "region": analysis.get("region") or analysis.get("country"),
        "currency": analysis.get("currency"),
        "quote_currency": analysis.get("quote_currency") or analysis.get("currency"),
        "asset_type": analysis.get("asset_type") or "EQUITY",
        "factor_exposure": _join_list(analysis.get("factor_exposure")),
        "ticker_validation_status": analysis.get("ticker_validation_status"),
        "ticker_coverage_status": analysis.get("ticker_coverage_status"),
        "free_data_coverage_class": analysis.get("free_data_coverage_class"),
        "free_data_coverage_score": analysis.get("free_data_coverage_score"),
        "last_seen": date,
        "seen_this_run": "TRUE",
        "source": universe,
    }
    for key, value in current.items():
        if key in {"ticker", "last_seen", "seen_this_run", "source"} or _has_value(value):
            row[key] = value

    status, action = _memory_status_and_action(analysis, previous, row)
    row["ticker_memory_status"] = status
    row["ticker_memory_action"] = action
    row["notes"] = _memory_notes(analysis)
    return {column: row.get(column, "") for column in TICKER_MEMORY_COLUMNS}


def _memory_status_and_action(
    analysis: dict[str, Any],
    previous: dict[str, Any],
    current: dict[str, Any],
) -> tuple[str, str]:
    validation = str(analysis.get("ticker_validation_status") or "").upper()
    coverage = str(analysis.get("ticker_coverage_status") or "").upper()
    coverage_class = str(analysis.get("free_data_coverage_class") or "").upper()
    score = safe_float(analysis.get("free_data_coverage_score"))

    if validation in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"} or coverage in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return (
            "NEEDS_TICKER_REVIEW",
            "Valider le ticker exact dans Yahoo Finance avant d'utiliser ce titre pour une grosse décision.",
        )
    if coverage in {"NEEDS_BNCD_OR_MANUAL_CONFIRMATION", "LOW_FREE_DATA_COVERAGE"} or coverage_class == "VALID_TICKER_POOR_FREE_COVERAGE" or (score is not None and score < 0.55):
        return (
            "LOW_FREE_COVERAGE",
            "Ticker probablement valide, mais données gratuites faibles; utiliser BNCD/Morningstar ou validation manuelle si le titre devient important.",
        )
    if _classification_changed(previous, current):
        return (
            "CLASSIFICATION_CHANGED_REVIEW",
            "Classification différente de la mémoire précédente; l'agent garde les données fraîches, mais une validation manuelle peut être utile.",
        )
    if _previous_has_fallback(previous) and any(not _has_value(analysis.get(key)) for key in ["sector", "region", "currency"]):
        return (
            "FALLBACK_AVAILABLE",
            "Mémoire locale disponible comme secours pour secteur/région/devise si une source gratuite devient incomplète.",
        )
    return (
        "ACTIVE",
        "Mémoire mise à jour; elle sert seulement de filet de secours et ne remplace pas les données fraîches.",
    )


def _classification_changed(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    if not previous:
        return False
    for key in ["asset_type", "region", "currency"]:
        old = _norm_text(previous.get(key))
        new = _norm_text(current.get(key))
        if old and new and old != new:
            return True
    old_sector = _norm_text(_first_useful(previous, ["sector", "sector_name", "industry"]))
    new_sector = _norm_text(_first_useful(current, ["sector", "sector_name", "industry"]))
    return bool(old_sector and new_sector and old_sector != new_sector and _sector_change_is_material(old_sector, new_sector))


def _sector_change_is_material(old: str, new: str) -> bool:
    if old in new or new in old:
        return False
    broad_groups = [
        {"TECHNOLOGY", "SOFTWARE", "CLOUD", "SEMICONDUCTORS", "INFORMATION TECHNOLOGY"},
        {"HEALTHCARE", "HEALTH CARE", "PHARMA", "PHARMACEUTICAL"},
        {"INDUSTRIAL", "INDUSTRIALS", "ENGINEERING", "MACHINERY"},
        {"FINANCIAL", "FINANCIALS", "BANK", "PAYMENTS", "ASSET MANAGEMENT"},
        {"CONSUMER", "RETAIL", "DISCRETIONARY", "STAPLES"},
    ]
    for group in broad_groups:
        if any(token in old for token in group) and any(token in new for token in group):
            return False
    return True


def _previous_has_fallback(previous: dict[str, Any]) -> bool:
    return bool(
        _has_value(previous.get("sector"))
        or _has_value(previous.get("sector_name"))
        or _has_value(previous.get("industry"))
        or _has_value(previous.get("region"))
        or _has_value(previous.get("currency"))
    )


def _memory_notes(analysis: dict[str, Any]) -> str:
    issues = _join_list(analysis.get("ticker_issue_reasons"))
    if issues:
        return issues
    return "Classification locale modérée; les données fraîches restent prioritaires."


def _first_useful(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if _has_value(value):
            return str(value).strip()
    return ""


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, list):
        return bool(value)
    text = str(value).strip()
    return text.upper() not in UNKNOWN_VALUES


def _parse_factor_exposure(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").replace(",", ";").split(";") if part.strip()]


def _join_list(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value if str(item))
    return str(value or "")


def _norm_text(value: Any) -> str:
    if not _has_value(value):
        return ""
    return " ".join(str(value).upper().replace("&", " ").replace("-", " ").split())
