from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .market_scanner import compute_valuation_status, market_prefilter
from .utils import file_age_hours, load_yaml, normalize_ticker, read_csv_records, safe_float, today_iso, write_csv_records
from .watchlist_engine import compute_data_quality


DISCOVERY_SCOPE_NOTE = (
    "La découverte externe analyse une liste auto-entretenue de titres provenant de sources gratuites configurées. "
    "Elle exclut les titres déjà dans le portfolio, la watchlist ou le market_universe, et ne couvre pas tout le marché."
)

DISCOVERY_COLUMNS = [
    "ticker",
    "ticker_display",
    "resolved_ticker",
    "company_name",
    "score_total",
    "conviction_score",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "data_quality",
    "valuation_status",
    "cycle_bubble_risk_level",
    "discovery_status",
    "reason",
    "suggested_action",
]

DISCOVERY_STATUSES = {
    "ADD_TO_MARKET_UNIVERSE_REVIEW",
    "STRONG_BUT_WAIT",
    "TOO_EXPENSIVE",
    "INSUFFICIENT_DATA",
    "NOT_ALIGNED_NOW",
}

DISCOVERY_CACHE_COLUMNS = ["ticker", "company_name", "source", "priority", "last_seen"]
DISCOVERY_MAINTENANCE_COLUMNS = [
    "ticker",
    "ticker_display",
    "company_name",
    "source",
    "maintenance_status",
    "reason",
    "suggested_action",
]

DISCOVERY_MAINTENANCE_STATUSES = {
    "ACTIVE_TOP_IDEA",
    "KEEP_WATCHING",
    "QUARANTINE",
    "REMOVE_CANDIDATE",
    "IGNORE_FOR_NOW",
}

DEFAULT_DISCOVERY_COMPANY_NAMES = {
    "WM": "Waste Management Inc.",
    "RSG": "Republic Services Inc.",
    "CTAS": "Cintas Corporation",
    "ODFL": "Old Dominion Freight Line Inc.",
    "FAST": "Fastenal Company",
    "MSI": "Motorola Solutions Inc.",
    "HEI": "HEICO Corporation",
    "TDG": "TransDigm Group Incorporated",
    "IDXX": "IDEXX Laboratories Inc.",
    "SYK": "Stryker Corporation",
    "WAT": "Waters Corporation",
    "IQV": "IQVIA Holdings Inc.",
    "VEEV": "Veeva Systems Inc.",
    "PAYX": "Paychex Inc.",
    "FI": "Fiserv Inc.",
    "MSCI": "MSCI Inc.",
    "ICE": "Intercontinental Exchange Inc.",
    "CME": "CME Group Inc.",
    "CBOE": "Cboe Global Markets Inc.",
    "AON": "Aon plc",
    "AJG": "Arthur J. Gallagher & Co.",
    "CB": "Chubb Limited",
    "SHW": "The Sherwin-Williams Company",
    "MCD": "McDonald's Corporation",
    "CMG": "Chipotle Mexican Grill Inc.",
    "ORLY": "O'Reilly Automotive Inc.",
    "AZO": "AutoZone Inc.",
    "EQIX": "Equinix Inc.",
    "AMT": "American Tower Corporation",
    "PANW": "Palo Alto Networks Inc.",
    "FTNT": "Fortinet Inc.",
    "TYL": "Tyler Technologies Inc.",
    "RACE": "Ferrari N.V.",
    "RELX": "RELX PLC",
    "ATD.TO": "Alimentation Couche-Tard Inc.",
    "CNR.TO": "Canadian National Railway Company",
    "CP.TO": "Canadian Pacific Kansas City Limited",
    "IFC.TO": "Intact Financial Corporation",
    "TFII.TO": "TFI International Inc.",
}


def load_discovery_universe(config_path: str | Path, excluded_tickers: set[str] | None = None) -> dict[str, dict[str, Any]]:
    excluded_tickers = {normalize_ticker(ticker) for ticker in (excluded_tickers or set())}
    configured = load_yaml(config_path).get("discovery_universe", [])
    rows: dict[str, dict[str, Any]] = {}
    for item in configured:
        ticker = _configured_ticker(item)
        if not ticker or ticker in excluded_tickers:
            continue
        rows[ticker] = {
            "ticker": ticker,
            "company_name": _configured_company_name(item),
            "sector": "",
            "region": "",
            "currency": "",
            "notes": "",
            "source": "config/market_scanner.yaml:discovery_universe",
        }
    return rows


def load_auto_discovery_universe(
    config_path: str | Path,
    cache_path: str | Path,
    excluded_tickers: set[str] | None = None,
    refresh: bool = False,
) -> dict[str, dict[str, Any]]:
    excluded_tickers = {normalize_ticker(ticker) for ticker in (excluded_tickers or set())}
    config = load_yaml(config_path)
    curated = load_discovery_universe(config_path, excluded_tickers)
    auto_config = config.get("auto_discovery", {}) if isinstance(config.get("auto_discovery"), dict) else {}
    if auto_config.get("enabled") is False:
        return curated

    cache_path = Path(cache_path)
    auto_rows = _load_or_fetch_auto_rows(config, cache_path, refresh=refresh)
    auto_rows = _prune_excluded_auto_rows(auto_rows, excluded_tickers, cache_path)
    max_auto = int(safe_float(auto_config.get("max_auto_candidates_for_analysis")) or 80)
    combined = dict(curated)
    added = 0
    for row in sorted(auto_rows, key=_auto_source_sort_key, reverse=True):
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker or ticker in excluded_tickers or ticker in combined:
            continue
        combined[ticker] = {
            "ticker": ticker,
            "company_name": str(row.get("company_name") or "").strip(),
            "sector": "",
            "region": "",
            "currency": "",
            "notes": "",
            "source": str(row.get("source") or "auto_discovery"),
            "discovery_priority": safe_float(row.get("priority")) or 0.0,
        }
        added += 1
        if added >= max_auto:
            break
    return combined


def _prune_excluded_auto_rows(rows: list[dict[str, Any]], excluded_tickers: set[str], cache_path: Path) -> list[dict[str, Any]]:
    if not rows or not excluded_tickers:
        return rows
    kept = [row for row in rows if normalize_ticker(row.get("ticker")) not in excluded_tickers]
    if len(kept) != len(rows) and cache_path.exists():
        write_csv_records(cache_path, kept, DISCOVERY_CACHE_COLUMNS)
    return kept


def classify_discovery_idea(analysis: dict[str, Any]) -> dict[str, Any]:
    score_total = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    data_quality = compute_data_quality(analysis)
    valuation_status = compute_valuation_status(analysis)
    prefilter_passed, prefilter_reason = market_prefilter(analysis)
    cycle_level = str(analysis.get("cycle_bubble_risk_level") or "LOW")
    cycle_hot = cycle_level in {"HIGH", "EXTREME"}
    valuation_extreme = valuation_status in {"TOO_EXPENSIVE", "EXTREMELY_EXPENSIVE"} or analysis.get("quality_but_too_expensive") is True
    missing_count = int(analysis.get("score_missing_data_count") or 0)

    if data_quality == "LOW" or missing_count > 5:
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "discovery_status": "INSUFFICIENT_DATA",
            "discovery_reason": "Trop de données manquent pour proposer ce titre comme idée à ajouter au market_universe.",
            "discovery_suggested_action": "Ne pas ajouter maintenant; chercher des données fiables seulement si le titre t’intéresse déjà.",
        }

    if valuation_extreme and score_total >= 8:
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "discovery_status": "TOO_EXPENSIVE",
            "discovery_reason": "Qualité possible, mais valorisation trop exigeante selon les règles mécaniques.",
            "discovery_suggested_action": "Ne pas ajouter en priorité; reconsidérer si la valorisation devient plus raisonnable.",
        }

    strict_pass = (
        prefilter_passed
        and data_quality == "HIGH"
        and score_total >= 8.5
        and conviction >= 85
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("liquidation_status") == "GREEN"
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and not cycle_hot
    )
    if strict_pass:
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "discovery_status": "ADD_TO_MARKET_UNIVERSE_REVIEW",
            "discovery_reason": (
                "Idée externe très alignée avec le profil high-CAGR selon les données gratuites. "
                "À ajouter seulement au market_universe pour analyse manuelle future, pas au portefeuille."
            ),
            "discovery_suggested_action": "Si la thèse te plaît après lecture manuelle, ajouter le ticker et le nom dans data/market_universe.csv.",
        }

    if score_total >= 8 and conviction >= 70 and data_quality in {"HIGH", "MEDIUM"}:
        blockers = []
        if not prefilter_passed:
            blockers.append(prefilter_reason)
        if cycle_hot:
            blockers.append(f"risque cycle/bulle/tendance {cycle_level}")
        if analysis.get("opportunity_cost_status") != "CLEARLY_BETTER_THAN_VFV":
            blockers.append("avantage face à VFV pas encore clair")
        reason = "; ".join(blockers) if blockers else "profil intéressant, mais pas assez exceptionnel pour une proposition prioritaire"
        return {
            "data_quality": data_quality,
            "valuation_status": valuation_status,
            "discovery_status": "STRONG_BUT_WAIT",
            "discovery_reason": reason,
            "discovery_suggested_action": "Garder comme idée secondaire; ajouter au market_universe seulement si tu veux la suivre de près.",
        }

    return {
        "data_quality": data_quality,
        "valuation_status": valuation_status,
        "discovery_status": "NOT_ALIGNED_NOW",
        "discovery_reason": "Le titre ne passe pas les filtres stricts high-CAGR avec les données disponibles.",
        "discovery_suggested_action": "Ne rien faire.",
    }


def build_discovery_maintenance_rows(
    analyses: dict[str, dict[str, Any]],
    universe: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for analysis in sorted(analyses.values(), key=_discovery_sort_key, reverse=True):
        status, reason, action = classify_discovery_maintenance(analysis)
        ticker = str(analysis.get("ticker") or "")
        metadata = universe.get(ticker, {})
        rows.append(
            {
                "ticker": ticker,
                "ticker_display": analysis.get("ticker_display", ticker),
                "company_name": metadata.get("company_name", ""),
                "source": metadata.get("source", ""),
                "maintenance_status": status,
                "reason": reason,
                "suggested_action": action,
            }
        )
    return rows


def classify_discovery_maintenance(analysis: dict[str, Any]) -> tuple[str, str, str]:
    current_price = safe_float(analysis.get("current_price"))
    market_cap = safe_float(analysis.get("market_cap"))
    stock_return_1y = safe_float(analysis.get("stock_return_1y"))
    news_red_flags = analysis.get("news_red_flags") or []
    data_quality = str(analysis.get("data_quality") or "").upper()

    if news_red_flags:
        return (
            "QUARANTINE",
            "Nouvelles gratuites avec mots-clés de risque majeur: " + "; ".join(str(item) for item in news_red_flags[:2]),
            "Ne pas ajouter au market_universe sans validation manuelle de la nouvelle.",
        )
    if analysis.get("thesis_status") == "BROKEN" or analysis.get("liquidation_status") == "RED":
        return (
            "REMOVE_CANDIDATE",
            "Thèse cassée ou statut de liquidation rouge selon les règles mécaniques.",
            "Retirer de la découverte active; ne pas ajouter au market_universe.",
        )
    if current_price is None:
        return (
            "QUARANTINE",
            "Prix indisponible avec les données gratuites.",
            "Garder hors recommandations jusqu’à ce que le ticker ou les données soient validés.",
        )
    if current_price < 2:
        return (
            "REMOVE_CANDIDATE",
            "Prix sous 2 $: filtre anti-penny-stock et risque de détérioration/delisting.",
            "Ne pas ajouter au market_universe sauf raison manuelle exceptionnelle.",
        )
    if market_cap is not None and market_cap < 2_000_000_000:
        return (
            "REMOVE_CANDIDATE",
            "Market cap sous 2 G$: trop petit pour le radar high-CAGR core de qualité.",
            "Retirer de la découverte active.",
        )
    if stock_return_1y is not None and stock_return_1y <= -0.75 and analysis.get("price_above_sma_200") is False:
        return (
            "QUARANTINE",
            "Chute très sévère sur 1 an et prix sous SMA 200.",
            "Surveiller seulement après validation fondamentale manuelle.",
        )
    if data_quality == "LOW":
        return (
            "QUARANTINE",
            "Qualité des données insuffisante.",
            "Ne pas proposer comme idée prioritaire tant que les données gratuites restent faibles.",
        )
    if analysis.get("discovery_status") == "ADD_TO_MARKET_UNIVERSE_REVIEW":
        return (
            "ACTIVE_TOP_IDEA",
            "Passe les filtres stricts de découverte high-CAGR.",
            "À lire manuellement; ajouter à data/market_universe.csv seulement si la thèse te convainc.",
        )
    if analysis.get("discovery_status") in {"STRONG_BUT_WAIT", "TOO_EXPENSIVE"}:
        return (
            "KEEP_WATCHING",
            "Titre intéressant mais pas assez parfait aujourd’hui.",
            "Garder dans le radar automatique; ne pas ajouter en priorité.",
        )
    return (
        "IGNORE_FOR_NOW",
        "Ne passe pas les filtres de découverte prioritaires.",
        "Ne rien faire.",
    )


def build_discovery_idea_rows(
    analyses: dict[str, dict[str, Any]],
    universe: dict[str, dict[str, Any]],
    report_only: bool = False,
) -> list[dict[str, Any]]:
    rows = []
    for analysis in sorted(analyses.values(), key=_discovery_sort_key, reverse=True):
        status = str(analysis.get("discovery_status") or "")
        if report_only and status not in {"ADD_TO_MARKET_UNIVERSE_REVIEW", "STRONG_BUT_WAIT", "TOO_EXPENSIVE"}:
            continue
        ticker = analysis.get("ticker")
        metadata = universe.get(ticker, {})
        rows.append(
            {
                "ticker": ticker,
                "ticker_display": analysis.get("ticker_display", ticker),
                "resolved_ticker": analysis.get("resolved_ticker", ticker),
                "company_name": metadata.get("company_name", ""),
                "score_total": analysis.get("score_total"),
                "conviction_score": analysis.get("conviction_score"),
                "expected_cagr_quality": analysis.get("expected_cagr_quality"),
                "opportunity_cost_status": analysis.get("opportunity_cost_status"),
                "data_quality": analysis.get("data_quality"),
                "valuation_status": analysis.get("valuation_status"),
                "cycle_bubble_risk_level": analysis.get("cycle_bubble_risk_level"),
                "discovery_status": status,
                "reason": analysis.get("discovery_reason"),
                "suggested_action": analysis.get("discovery_suggested_action"),
            }
        )
    return rows


def actionable_discovery_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("discovery_status") == "ADD_TO_MARKET_UNIVERSE_REVIEW"]


def _load_or_fetch_auto_rows(config: dict[str, Any], cache_path: Path, refresh: bool) -> list[dict[str, Any]]:
    auto_config = config.get("auto_discovery", {}) if isinstance(config.get("auto_discovery"), dict) else {}
    max_age = safe_float(auto_config.get("cache_max_age_hours")) or 168
    if not refresh and _cache_is_fresh(cache_path, max_age):
        cached = read_csv_records(cache_path)
        if cached:
            return cached

    fetched = _fetch_auto_discovery_rows(auto_config)
    if fetched:
        write_csv_records(cache_path, fetched, DISCOVERY_CACHE_COLUMNS)
        return fetched
    return read_csv_records(cache_path)


def _fetch_auto_discovery_rows(auto_config: dict[str, Any]) -> list[dict[str, Any]]:
    if auto_config.get("enabled") is False:
        return []
    sources = auto_config.get("sources") or []
    if not isinstance(sources, list):
        return []
    rows_by_ticker: dict[str, dict[str, Any]] = {}
    timeout = safe_float(auto_config.get("source_timeout_seconds")) or 5
    for source in sources:
        if not isinstance(source, dict) or source.get("enabled") is False:
            continue
        for row in _fetch_public_table_source(source, timeout):
            ticker = normalize_ticker(row.get("ticker"))
            if not ticker:
                continue
            current = rows_by_ticker.get(ticker)
            if current and (safe_float(current.get("priority")) or 0) >= (safe_float(row.get("priority")) or 0):
                continue
            rows_by_ticker[ticker] = row
    return sorted(rows_by_ticker.values(), key=_auto_source_sort_key, reverse=True)


def _fetch_public_table_source(source: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    url = str(source.get("url") or "").strip()
    if not url:
        return []
    try:
        import requests
        from bs4 import BeautifulSoup

        response = requests.get(url, timeout=timeout, headers={"User-Agent": "investment-automation-local/1.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception:
        return []

    rows = []
    for table in soup.find_all("table"):
        extracted = _extract_rows_from_table(table, source)
        if extracted:
            rows.extend(extracted)
            break
    return rows


def _extract_rows_from_table(table: Any, source: dict[str, Any]) -> list[dict[str, Any]]:
    source_name = str(source.get("name") or "public_source")
    suffix = str(source.get("ticker_suffix") or "")
    priority = safe_float(source.get("priority")) or 1.0
    rows = table.find_all("tr")
    if not rows:
        return []
    header_cells = rows[0].find_all(["th", "td"])
    headers = [_clean_text(cell.get_text(" ")) for cell in header_cells]
    ticker_index = _find_header_index(headers, {"symbol", "ticker"})
    name_index = _find_header_index(headers, {"company", "security", "name"})
    if ticker_index is None or name_index is None:
        return []

    output = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) <= max(ticker_index, name_index):
            continue
        ticker = _normalize_public_source_ticker(cells[ticker_index].get_text(" "), suffix)
        company_name = _clean_text(cells[name_index].get_text(" "))
        if not ticker or not company_name:
            continue
        output.append(
            {
                "ticker": ticker,
                "company_name": company_name,
                "source": source_name,
                "priority": priority,
                "last_seen": today_iso(),
            }
        )
    return output


def _normalize_public_source_ticker(raw: Any, suffix: str = "") -> str:
    ticker = _clean_text(raw)
    ticker = re.sub(r"\s+", "", ticker)
    ticker = ticker.replace(".", "-")
    ticker = ticker.replace("/", "-")
    ticker = normalize_ticker(ticker)
    if not ticker:
        return ""
    if suffix and "." not in ticker:
        ticker = f"{ticker}{suffix}"
    return ticker


def _find_header_index(headers: list[str], candidates: set[str]) -> int | None:
    normalized = [_header_key(header) for header in headers]
    for index, header in enumerate(normalized):
        if header in candidates:
            return index
    for index, header in enumerate(normalized):
        if any(candidate in header for candidate in candidates):
            return index
    return None


def _header_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _clean_text(value: Any) -> str:
    text = re.sub(r"\[[^\]]+\]", "", str(value or ""))
    return " ".join(text.replace("\xa0", " ").split()).strip()


def _cache_is_fresh(path: Path, max_age_hours: float) -> bool:
    age = file_age_hours(path)
    return age is not None and age <= max_age_hours and bool(read_csv_records(path))


def _auto_source_sort_key(row: dict[str, Any]) -> tuple[float, str]:
    return (safe_float(row.get("priority")) or 0.0, str(row.get("ticker") or ""))


def _discovery_sort_key(analysis: dict[str, Any]) -> tuple[int, float, float]:
    status_rank = {
        "ADD_TO_MARKET_UNIVERSE_REVIEW": 5,
        "STRONG_BUT_WAIT": 4,
        "TOO_EXPENSIVE": 3,
        "INSUFFICIENT_DATA": 2,
        "NOT_ALIGNED_NOW": 1,
    }.get(str(analysis.get("discovery_status")), 0)
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
    return DEFAULT_DISCOVERY_COMPANY_NAMES.get(normalize_ticker(item), "")
