from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from .utils import CACHE_DIR, load_json, safe_float, save_json


STOCKANALYSIS_USER_AGENT = "investment-automation-local/1.0"
STOCKANALYSIS_SOURCE_NAME = "StockAnalysis Canadian financial pages"
SEDARPLUS_SOURCE_NAME = "SEDAR+ public filings"
TMX_SOURCE_NAME = "TMX Money market data"
CANADIAN_AUTHORITY_TIMEOUT_SECONDS = 10
CANADIAN_SOURCE_CONFLICT_THRESHOLD = 0.15
SEDARPLUS_BASE_URL = "https://www.sedarplus.ca"
TMX_QUOTE_URL = "https://app.tmxmoney.com/quote/{symbol}"
TMX_GRAPHQL_URL = "https://app-money.tmx.com/graphql"

CANADIAN_SUFFIX_EXCHANGE = {
    ".TO": "tsx",
    ".V": "tsxv",
    ".CN": "cse",
    ".NE": "neo",
}

RATIO_OR_GROWTH_FIELDS = {
    "profit_margins",
    "gross_margins",
    "operating_margins",
    "revenue_growth",
    "earnings_growth",
    "return_on_equity",
    "return_on_assets",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "net_debt_to_fcf",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "sbc_to_revenue",
    "fcf_per_share_growth",
    "debt_to_equity",
}

CANADIAN_NUMERIC_FIELDS = RATIO_OR_GROWTH_FIELDS | {
    "total_revenue",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_cash",
    "total_debt",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "diluted_eps_ttm_or_annual",
    "trailing_pe",
    "forward_pe",
    "peg",
    "dividend_yield",
    "market_cap",
    "high_12m",
    "low_12m",
}


class CanadianDataFetcher:
    """Best-effort Canadian fallback for TSX/TSXV fundamentals.

    This is deliberately conservative. It never replaces good yfinance price
    data, and absolute statement values are mostly used only when missing
    because some free HTML pages report financials in millions.
    """

    def __init__(
        self,
        cache_dir: str | Path = CACHE_DIR,
        timeout_seconds: int = CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
        max_cache_age_hours: int = 168,
    ) -> None:
        self.cache_dir = Path(cache_dir) / "canadian_sources"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self.max_cache_age = timedelta(hours=max_cache_age_hours)

    def fetch_fundamentals(
        self,
        ticker: str,
        *,
        company_name: str = "",
        refresh: bool = False,
    ) -> dict[str, Any]:
        meta = canadian_ticker_metadata(ticker)
        if not meta:
            return {"available": False, "reason": "Ticker non identifié comme cotation canadienne prise en charge."}

        source_payloads: list[dict[str, Any]] = []
        source_health: list[dict[str, Any]] = []

        sedar_payload, sedar_health = self._cached_external_source(
            cache_name=f"sedarplus_{meta['exchange']}_{meta['symbol']}.json",
            source_name=SEDARPLUS_SOURCE_NAME,
            ticker=ticker,
            fetcher=fetch_sedarplus_fundamentals,
            refresh=refresh,
        )
        source_payloads.append(sedar_payload)
        source_health.append(sedar_health)

        tmx_payload, tmx_health = self._cached_external_source(
            cache_name=f"tmx_{meta['exchange']}_{meta['symbol']}.json",
            source_name=TMX_SOURCE_NAME,
            ticker=ticker,
            fetcher=fetch_tmx_fundamentals,
            refresh=refresh,
        )
        source_payloads.append(tmx_payload)
        source_health.append(tmx_health)

        stockanalysis_payload = self._fetch_stockanalysis_fundamentals(
            ticker,
            meta=meta,
            company_name=company_name,
            refresh=refresh,
        )
        source_payloads.append(stockanalysis_payload)
        source_health.append(
            {
                "source": STOCKANALYSIS_SOURCE_NAME,
                "available": bool(stockanalysis_payload.get("available")),
                "latency_ms": stockanalysis_payload.get("source_latency_ms"),
                "status": "OK" if stockanalysis_payload.get("available") else "UNAVAILABLE",
                "fetched_at": stockanalysis_payload.get("fetched_at"),
                "reason": stockanalysis_payload.get("reason") or stockanalysis_payload.get("coverage_status") or "",
            }
        )

        merged = merge_canadian_source_payloads(
            [payload for payload in source_payloads if isinstance(payload, dict)],
            ticker=ticker,
            company_name=company_name,
            source_health=source_health,
        )
        if merged.get("available"):
            return merged
        return {
            "available": False,
            "reason": "Aucune source canadienne gratuite exploitable.",
            "source_health": source_health,
        }

    def _cached_external_source(
        self,
        *,
        cache_name: str,
        source_name: str,
        ticker: str,
        fetcher: Any,
        refresh: bool,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        cache_path = self.cache_dir / cache_name
        cached = _fresh_cached_json(cache_path, self.max_cache_age, refresh=refresh)
        if cached:
            payload = cached.get("parsed_payload") if isinstance(cached, dict) else None
            if isinstance(payload, dict):
                payload = dict(payload)
                payload.setdefault("source", source_name)
                payload.setdefault("fetched_at", cached.get("fetched_at"))
                return payload, {
                    "source": source_name,
                    "available": bool(payload.get("available")),
                    "latency_ms": cached.get("latency_ms"),
                    "status": "CACHE",
                    "fetched_at": cached.get("fetched_at"),
                    "reason": payload.get("reason") or payload.get("coverage_status") or "",
                }

        started = time.perf_counter()
        payload: dict[str, Any] = {}
        error = ""
        try:
            payload = fetcher(ticker) or {}
        except Exception as exc:
            error = str(exc)
            payload = {}
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if payload:
            payload.setdefault("source", source_name)
            payload.setdefault("available", bool(payload.get("fields")))
            payload.setdefault("source_latency_ms", latency_ms)
        else:
            payload = {"available": False, "source": source_name, "reason": error or "Source indisponible ou non exploitable."}
        save_json(
            cache_path,
            {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "latency_ms": latency_ms,
                "parsed_payload": payload,
            },
        )
        return payload, {
            "source": source_name,
            "available": bool(payload.get("available")),
            "latency_ms": latency_ms,
            "status": "OK" if payload.get("available") else "UNAVAILABLE",
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "reason": payload.get("reason") or payload.get("coverage_status") or "",
        }

    def _fetch_stockanalysis_fundamentals(
        self,
        ticker: str,
        *,
        meta: dict[str, str],
        company_name: str,
        refresh: bool,
    ) -> dict[str, Any]:
        cache_path = self.cache_dir / f"stockanalysis_{meta['exchange']}_{meta['symbol']}.json"
        cached = _fresh_cached_json(cache_path, self.max_cache_age, refresh=refresh)
        if cached:
            parsed = cached.get("parsed_payload") if isinstance(cached, dict) else None
            if isinstance(parsed, dict) and parsed.get("available"):
                parsed = dict(parsed)
                parsed["fetched_at"] = cached.get("fetched_at")
                parsed["source"] = parsed.get("source") or STOCKANALYSIS_SOURCE_NAME
                parsed["source_latency_ms"] = cached.get("latency_ms")
                return parsed

        urls = _stockanalysis_urls(str(meta["exchange"]), str(meta["symbol"]))
        raw_pages: dict[str, str] = {}
        errors: list[str] = []
        started = time.perf_counter()
        for statement, url in urls.items():
            try:
                response = requests.get(
                    url,
                    timeout=self.timeout_seconds,
                    headers={"User-Agent": STOCKANALYSIS_USER_AGENT},
                )
                if response.status_code >= 400:
                    errors.append(f"{statement}: HTTP {response.status_code}")
                    continue
                raw_pages[statement] = response.text
            except Exception as exc:
                errors.append(f"{statement}: {exc}")

        parsed = parse_stockanalysis_pages(raw_pages, ticker=ticker, company_name=company_name, urls=urls)
        if not parsed.get("available"):
            parsed["errors"] = errors
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        parsed["source_latency_ms"] = latency_ms
        save_json(
            cache_path,
            {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "latency_ms": latency_ms,
                "urls": urls,
                "parsed_payload": parsed,
                "errors": errors,
            },
        )
        return parsed


def fetch_sedarplus_fundamentals(ticker: str) -> dict[str, Any]:
    """Return best-effort annual Canadian filing fields from SEDAR+ public endpoints.

    The SEDAR+ public surface is not as stable as SEC EDGAR companyfacts, so this
    helper is intentionally defensive: it tries public JSON/document search
    patterns, extracts only fields that clearly match the project schema, and
    returns an empty dict on any missing ticker, network error, or unsupported
    response shape.
    """
    meta = canadian_ticker_metadata(ticker)
    if not meta:
        return {}
    symbol = str(meta["symbol"]).upper()
    payloads = _safe_json_candidates(
        [
            ("GET", f"{SEDARPLUS_BASE_URL}/csa-party/api/search?keyword={symbol}", None),
            (
                "GET",
                f"{SEDARPLUS_BASE_URL}/csa-party/api/documents?issuer={symbol}&documentType=Annual%20Financial%20Statements",
                None,
            ),
            (
                "GET",
                f"{SEDARPLUS_BASE_URL}/csa-party/api/filings?search={symbol}&category=Annual%20Financial%20Statements",
                None,
            ),
        ]
    )
    parsed = _parse_sedarplus_payloads(payloads, ticker=ticker)
    return parsed if parsed.get("available") else {}


def fetch_tmx_fundamentals(ticker: str) -> dict[str, Any]:
    """Return best-effort Canadian market fundamentals from TMX Money.

    TMX is used as a supplemental free Canadian market source for basic fields
    such as P/E, dividend yield, market cap, 52-week high/low, and sector. The
    function fails silently and returns an empty dict when TMX changes its public
    endpoint or the ticker is not found.
    """
    meta = canadian_ticker_metadata(ticker)
    if not meta:
        return {}
    symbol = str(meta["ticker"]).upper()
    raw_payloads: list[Any] = []

    graphql_query = {
        "query": (
            "query getQuoteBySymbol($symbol:String!) { "
            "getQuoteBySymbol(symbol:$symbol) { "
            "symbol name marketCap peRatio priceEarningsRatio dividendYield "
            "fiftyTwoWeekHigh fiftyTwoWeekLow week52High week52Low sector industry "
            "} }"
        ),
        "variables": {"symbol": symbol},
    }
    raw_payloads.extend(_safe_json_candidates([("POST", TMX_GRAPHQL_URL, graphql_query)]))

    try:
        response = requests.get(
            TMX_QUOTE_URL.format(symbol=symbol),
            timeout=CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
            headers={"User-Agent": STOCKANALYSIS_USER_AGENT},
        )
        if response.status_code < 400:
            raw_payloads.append(response.text)
    except Exception:
        return _parse_tmx_payloads(raw_payloads, ticker=ticker)
    parsed = _parse_tmx_payloads(raw_payloads, ticker=ticker)
    return parsed if parsed.get("available") else {}


def canadian_ticker_metadata(ticker: str) -> dict[str, str] | None:
    normalized = str(ticker or "").strip().upper()
    for suffix, exchange in CANADIAN_SUFFIX_EXCHANGE.items():
        if normalized.endswith(suffix):
            return {"ticker": normalized, "symbol": normalized[: -len(suffix)], "suffix": suffix, "exchange": exchange}
    return None


def is_canadian_market_candidate(ticker: str, payload: dict[str, Any] | None = None) -> bool:
    if canadian_ticker_metadata(ticker):
        return True
    payload = payload or {}
    country = str(payload.get("country") or "").strip().lower()
    currency = str(payload.get("currency") or "").strip().upper()
    return country == "canada" and currency == "CAD"


def merge_canadian_source_payloads(
    payloads: list[dict[str, Any]],
    *,
    ticker: str = "",
    company_name: str = "",
    source_health: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    merged: dict[str, Any] = {
        "available": False,
        "ticker": ticker,
        "company_name": company_name,
        "source": "",
        "sources": [],
        "fields": [],
        "confirmed_fields": [],
        "source_conflicts": [],
        "source_health": source_health or [],
        "coverage_status": "NO_USABLE_FIELDS",
    }
    field_sources: dict[str, str] = {}
    latest_periods: list[str] = []

    for payload in payloads:
        if not isinstance(payload, dict) or not payload.get("available"):
            continue
        source = str(payload.get("source") or "Canadian source").strip()
        if source:
            merged["sources"].append(source)
        if payload.get("latest_period"):
            latest_periods.append(str(payload.get("latest_period")))
        candidate_fields = set(payload.get("fields") or []) | {
            field for field in CANADIAN_NUMERIC_FIELDS if safe_float(payload.get(field)) is not None
        }
        for field in sorted(candidate_fields):
            value = safe_float(payload.get(field))
            if value is None:
                continue
            existing = safe_float(merged.get(field))
            if existing is None:
                merged[field] = value
                merged["fields"].append(field)
                field_sources[field] = source
                continue
            difference = _relative_difference(existing, value)
            if difference > CANADIAN_SOURCE_CONFLICT_THRESHOLD:
                merged["source_conflicts"].append(
                    f"{field}: {field_sources.get(field, 'source_canadienne')}={existing:.4g}, "
                    f"{source}={value:.4g}, ecart={difference:.0%}"
                )
            else:
                merged["confirmed_fields"].append(field)
        for text_field in ("sector_name", "industry", "company_name"):
            if not merged.get(text_field) and payload.get(text_field):
                merged[text_field] = payload.get(text_field)

    merged["sources"] = sorted(set(merged["sources"]))
    merged["source"] = "; ".join(merged["sources"])
    merged["fields"] = sorted(set(merged["fields"]))
    merged["confirmed_fields"] = sorted(set(merged["confirmed_fields"]))
    merged["source_conflicts"] = sorted(set(merged["source_conflicts"]))
    if latest_periods:
        merged["latest_period"] = sorted(set(latest_periods))[-1]
    if merged["fields"]:
        merged["available"] = True
        merged["coverage_status"] = "USABLE"
    return merged


def parse_stockanalysis_pages(
    pages: dict[str, str],
    *,
    ticker: str = "",
    company_name: str = "",
    urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    income = _rows_by_label(pages.get("income", ""))
    balance = _rows_by_label(pages.get("balance", ""))
    cashflow = _rows_by_label(pages.get("cashflow", ""))

    revenue = _series(income, ["revenue", "total revenue"])
    net_income = _series(income, ["net income", "net income to common"])
    gross_profit = _series(income, ["gross profit"])
    operating_income = _series(income, ["operating income", "operating earnings", "ebit"])
    assets = _series(balance, ["total assets"])
    equity = _series(balance, ["total equity", "shareholders equity", "stockholders equity"])
    cash = _series(balance, ["cash and equivalents", "cash & equivalents", "cash cash equivalents"])
    total_debt = _series(balance, ["total debt", "long term debt", "debt"])
    operating_cash_flow = _series(cashflow, ["operating cash flow", "cash from operations"])
    capex = [_abs_or_none(value) for value in _series(cashflow, ["capital expenditures", "capital expenditure", "capex"])]
    free_cash_flow = _series(cashflow, ["free cash flow"])
    if not free_cash_flow:
        free_cash_flow = _subtract_series(operating_cash_flow, capex)
    shares = _series(income, ["shares outstanding", "diluted shares outstanding", "shares diluted"])
    share_repurchases = [_abs_or_none(value) for value in _series(cashflow, ["share repurchases", "stock repurchases"])]
    stock_comp = _series(cashflow, ["stock based compensation", "share based compensation"])

    parsed: dict[str, Any] = {
        "available": False,
        "ticker": ticker,
        "source": STOCKANALYSIS_SOURCE_NAME,
        "company_name": company_name,
        "urls": urls or {},
        "fields": [],
        "latest_period": _latest_period_from_html(pages),
        "coverage_status": "NO_USABLE_FIELDS",
    }

    _set(parsed, "total_revenue", _first(revenue))
    _set(parsed, "net_income", _first(net_income))
    _set(parsed, "profit_margins", _ratio(_first(net_income), _first(revenue)))
    _set(parsed, "gross_margins", _ratio(_first(gross_profit), _first(revenue)))
    _set(parsed, "operating_margins", _ratio(_first(operating_income), _first(revenue)))
    _set(parsed, "revenue_growth", _growth(revenue))
    _set(parsed, "earnings_growth", _growth(net_income))
    _set(parsed, "return_on_equity", _ratio(_first(net_income), _first(equity)))
    _set(parsed, "return_on_assets", _ratio(_first(net_income), _first(assets)))
    _set(parsed, "total_cash", _first(cash))
    _set(parsed, "total_debt", _first(total_debt))
    _set(parsed, "debt_to_equity", _debt_to_equity(_first(total_debt), _first(equity)))
    _set(parsed, "operating_cash_flow", _first(operating_cash_flow))
    _set(parsed, "capital_expenditures", _first(capex))
    _set(parsed, "free_cash_flow", _first(free_cash_flow))
    _set(parsed, "free_cash_flow_margin", _ratio(_first(free_cash_flow), _first(revenue)))
    _set(parsed, "free_cash_flow_growth", _growth(free_cash_flow))
    _set(parsed, "fcf_conversion", _ratio(_first(free_cash_flow), _first(net_income)))
    _set(parsed, "net_debt_to_fcf", _net_debt_to_fcf(_first(total_debt), _first(cash), _first(free_cash_flow)))
    _set(parsed, "diluted_average_shares", _first(shares))
    _set(parsed, "share_count_growth_1y", _growth(shares))
    _set(parsed, "share_count_cagr_3y", _cagr(shares, 3))
    _set(parsed, "share_count_cagr_5y", _cagr(shares, 5))
    _set(parsed, "share_repurchases", _first(share_repurchases))
    _set(parsed, "stock_based_compensation", _first(stock_comp))
    _set(parsed, "sbc_to_revenue", _ratio(_first(stock_comp), _first(revenue)))
    fcf_per_share = _per_share_series(free_cash_flow, shares)
    _set(parsed, "fcf_per_share", _first(fcf_per_share))
    _set(parsed, "fcf_per_share_growth", _growth(fcf_per_share))

    parsed["fields"] = sorted(field for field, value in parsed.items() if field not in {"fields", "available"} and safe_float(value) is not None)
    if parsed["fields"]:
        parsed["available"] = True
        parsed["coverage_status"] = "USABLE"
    return parsed


def _safe_json_candidates(candidates: list[tuple[str, str, dict[str, Any] | None]]) -> list[Any]:
    payloads: list[Any] = []
    for method, url, body in candidates:
        try:
            if method.upper() == "POST":
                response = requests.post(
                    url,
                    json=body or {},
                    timeout=CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
                    headers={"User-Agent": STOCKANALYSIS_USER_AGENT, "Content-Type": "application/json"},
                )
            else:
                response = requests.get(
                    url,
                    timeout=CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
                    headers={"User-Agent": STOCKANALYSIS_USER_AGENT},
                )
            if response.status_code >= 400:
                continue
            content_type = str(response.headers.get("content-type") or "").lower()
            if "json" in content_type:
                payloads.append(response.json())
                continue
            text = response.text
            if text.strip().startswith(("{", "[")):
                payloads.append(json.loads(text))
        except Exception:
            continue
    return payloads


def _parse_sedarplus_payloads(payloads: list[Any], *, ticker: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "available": False,
        "ticker": ticker,
        "source": SEDARPLUS_SOURCE_NAME,
        "fields": [],
        "coverage_status": "NO_USABLE_FIELDS",
    }
    if not payloads:
        return parsed

    aliases = {
        "total_revenue": ["revenue", "revenues", "totalRevenue", "total_revenue", "sales"],
        "net_income": ["netIncome", "net_income", "netIncomeLoss", "profitLoss", "earnings"],
        "total_assets": ["totalAssets", "total_assets", "assets"],
        "total_liabilities": ["totalLiabilities", "total_liabilities", "liabilities"],
        "operating_cash_flow": [
            "operatingCashFlow",
            "operating_cash_flow",
            "cashFromOperations",
            "netCashProvidedByOperatingActivities",
        ],
        "free_cash_flow": ["freeCashFlow", "free_cash_flow", "fcf"],
        "diluted_eps_ttm_or_annual": ["dilutedEPS", "diluted_eps", "earningsPerShareDiluted", "eps"],
    }
    for field, keys in aliases.items():
        value = _first_recursive_number(payloads, keys)
        _set(parsed, field, value)

    revenue = safe_float(parsed.get("total_revenue"))
    net_income = safe_float(parsed.get("net_income"))
    operating_cash_flow = safe_float(parsed.get("operating_cash_flow"))
    free_cash_flow = safe_float(parsed.get("free_cash_flow"))
    _set(parsed, "profit_margins", _ratio(net_income, revenue))
    _set(parsed, "free_cash_flow_margin", _ratio(free_cash_flow, revenue))
    _set(parsed, "fcf_conversion", _ratio(free_cash_flow, net_income))
    if free_cash_flow is None and operating_cash_flow is not None:
        # SEDAR+ extracts often expose OCF without clean capex. Do not invent FCF.
        parsed["coverage_status"] = "PARTIAL_OFFICIAL_FIELDS"

    latest_period = _first_recursive_text(payloads, ["fiscalYear", "periodEndDate", "financialYear", "reportDate"])
    if latest_period:
        parsed["latest_period"] = latest_period
    parsed["fields"] = sorted(field for field in CANADIAN_NUMERIC_FIELDS if safe_float(parsed.get(field)) is not None)
    if parsed["fields"]:
        parsed["available"] = True
        parsed["coverage_status"] = "USABLE"
    return parsed


def _parse_tmx_payloads(payloads: list[Any], *, ticker: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "available": False,
        "ticker": ticker,
        "source": TMX_SOURCE_NAME,
        "fields": [],
        "coverage_status": "NO_USABLE_FIELDS",
    }
    aliases = {
        "trailing_pe": ["peRatio", "priceEarningsRatio", "trailingPE", "pe"],
        "dividend_yield": ["dividendYield", "yield", "annualDividendYield"],
        "market_cap": ["marketCap", "marketCapitalization", "market_value"],
        "high_12m": ["fiftyTwoWeekHigh", "week52High", "52WeekHigh"],
        "low_12m": ["fiftyTwoWeekLow", "week52Low", "52WeekLow"],
    }
    for field, keys in aliases.items():
        value = _first_recursive_tmx_number(payloads, keys, market_cap=field == "market_cap")
        if field == "dividend_yield" and value is not None and value > 1:
            value = value / 100
        _set(parsed, field, value)
    sector = _first_recursive_text(payloads, ["sector", "sectorName"])
    if sector:
        parsed["sector_name"] = sector
    industry = _first_recursive_text(payloads, ["industry", "industryName"])
    if industry:
        parsed["industry"] = industry
    parsed["fields"] = sorted(field for field in CANADIAN_NUMERIC_FIELDS if safe_float(parsed.get(field)) is not None)
    if parsed["fields"] or parsed.get("sector_name"):
        parsed["available"] = True
        parsed["coverage_status"] = "USABLE"
    return parsed


def _first_recursive_number(payloads: list[Any], keys: list[str]) -> float | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for payload in payloads:
        for key, value in _walk_key_values(payload):
            if _normalize_key(key) in normalized_keys:
                number = _parse_number(str(value)) if isinstance(value, str) else safe_float(value)
                if number is not None:
                    return number
    return None


def _first_recursive_tmx_number(payloads: list[Any], keys: list[str], *, market_cap: bool = False) -> float | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for payload in payloads:
        for key, value in _walk_key_values(payload):
            if _normalize_key(key) in normalized_keys:
                number = _parse_tmx_number(str(value), market_cap=market_cap) if isinstance(value, str) else safe_float(value)
                if number is not None:
                    return number
    return None


def _first_recursive_text(payloads: list[Any], keys: list[str]) -> str:
    normalized_keys = {_normalize_key(key) for key in keys}
    for payload in payloads:
        for key, value in _walk_key_values(payload):
            if _normalize_key(key) in normalized_keys and str(value or "").strip():
                return str(value).strip()
    return ""


def _walk_key_values(payload: Any) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            rows.append((str(key), value))
            rows.extend(_walk_key_values(value))
    elif isinstance(payload, list):
        for item in payload:
            rows.extend(_walk_key_values(item))
    elif isinstance(payload, str):
        rows.extend(_walk_embedded_json(payload))
        rows.extend(_walk_json_like_pairs(payload))
    return rows


def _walk_embedded_json(text: str) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for match in re.finditer(r"<script[^>]*>(.*?)</script>", text, flags=re.IGNORECASE | re.DOTALL):
        script = match.group(1).strip()
        if not script:
            continue
        for candidate in re.findall(r"(\{.{50,}?\})", script, flags=re.DOTALL):
            try:
                rows.extend(_walk_key_values(json.loads(candidate)))
            except Exception:
                continue
    return rows


def _walk_json_like_pairs(text: str) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for match in re.finditer(r'"([A-Za-z0-9_]+)"\s*:\s*"?([-+0-9.,%KMBTkmbt]+)"?', text):
        rows.append((match.group(1), match.group(2)))
    for match in re.finditer(r'"(sector|sectorName|industry|industryName)"\s*:\s*"([^"]+)"', text, flags=re.IGNORECASE):
        rows.append((match.group(1), match.group(2)))
    return rows


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _parse_tmx_number(value: str, *, market_cap: bool = False) -> float | None:
    text = str(value or "").strip()
    if not text or text in {"-", "—", "N/A"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("$", "").replace(",", "").replace("%", "").strip()
    multiplier = 1.0
    suffix = text[-1:].upper()
    if suffix in {"K", "M", "B", "T"}:
        text = text[:-1]
        if market_cap:
            multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0, "T": 1_000_000_000_000.0}[suffix]
        else:
            multiplier = {"K": 0.001, "M": 1.0, "B": 1000.0, "T": 1_000_000.0}[suffix]
    number = safe_float(text)
    if number is None:
        return None
    number *= multiplier
    return -number if negative else number


def _stockanalysis_urls(exchange: str, symbol: str) -> dict[str, str]:
    base = f"https://stockanalysis.com/quote/{exchange}/{symbol}/financials"
    return {
        "income": f"{base}/",
        "balance": f"{base}/balance-sheet/",
        "cashflow": f"{base}/cash-flow-statement/",
    }


def _fresh_cached_json(path: Path, max_age: timedelta, *, refresh: bool) -> dict[str, Any]:
    if refresh or not path.exists():
        return {}
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime)
    except Exception:
        return {}
    if datetime.now() - modified > max_age:
        return {}
    cached = load_json(path)
    return cached if isinstance(cached, dict) else {}


def _rows_by_label(html: str) -> dict[str, list[float]]:
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    rows: dict[str, list[float]] = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if len(cells) < 2:
            continue
        label = _clean_label(cells[0].get_text(" ", strip=True))
        if not label:
            continue
        values = [_parse_number(cell.get_text(" ", strip=True)) for cell in cells[1:]]
        numbers = [value for value in values if value is not None]
        if numbers:
            rows[label] = numbers
    return rows


def _clean_label(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip().lower())
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _series(rows: dict[str, list[float]], labels: list[str]) -> list[float]:
    normalized = [_clean_label(label) for label in labels]
    for label, values in rows.items():
        if any(label == needle or needle in label for needle in normalized):
            return values
    return []


def _parse_number(value: str) -> float | None:
    text = str(value or "").strip()
    if not text or text in {"-", "—", "N/A"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace("$", "").replace(",", "").replace("%", "").strip()
    multiplier = 1.0
    if text.upper().endswith("B"):
        multiplier = 1000.0
        text = text[:-1]
    elif text.upper().endswith("M"):
        multiplier = 1.0
        text = text[:-1]
    number = safe_float(text)
    if number is None:
        return None
    number *= multiplier
    return -number if negative else number


def _latest_period_from_html(pages: dict[str, str]) -> str:
    for html in pages.values():
        soup = BeautifulSoup(html or "", "html.parser")
        for th in soup.find_all("th"):
            text = th.get_text(" ", strip=True)
            if re.search(r"\b20\d{2}\b|TTM", text, re.IGNORECASE):
                return text
    return ""


def _set(payload: dict[str, Any], field: str, value: float | None) -> None:
    if value is None:
        return
    payload[field] = value


def _first(values: list[float | None]) -> float | None:
    for value in values:
        number = safe_float(value)
        if number is not None:
            return number
    return None


def _abs_or_none(value: float | None) -> float | None:
    number = safe_float(value)
    return abs(number) if number is not None else None


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    numerator = safe_float(numerator)
    denominator = safe_float(denominator)
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _growth(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    latest = safe_float(values[0])
    previous = safe_float(values[1])
    if latest is None or previous is None or previous == 0:
        return None
    return latest / previous - 1


def _cagr(values: list[float], years: int) -> float | None:
    if len(values) <= years:
        return None
    latest = safe_float(values[0])
    old = safe_float(values[years])
    if latest is None or old is None or old <= 0 or latest <= 0:
        return None
    return (latest / old) ** (1 / years) - 1


def _subtract_series(left: list[float], right: list[float]) -> list[float]:
    output: list[float] = []
    for index in range(min(len(left), len(right))):
        left_value = safe_float(left[index])
        right_value = safe_float(right[index])
        if left_value is not None and right_value is not None:
            output.append(left_value - right_value)
    return output


def _per_share_series(numerator: list[float], shares: list[float]) -> list[float]:
    output: list[float] = []
    for index in range(min(len(numerator), len(shares))):
        value = _ratio(numerator[index], shares[index])
        if value is not None:
            output.append(value)
    return output


def _debt_to_equity(debt: float | None, equity: float | None) -> float | None:
    ratio = _ratio(debt, equity)
    return ratio * 100 if ratio is not None else None


def _net_debt_to_fcf(debt: float | None, cash: float | None, fcf: float | None) -> float | None:
    debt = safe_float(debt)
    cash = safe_float(cash)
    fcf = safe_float(fcf)
    if debt is None or cash is None or fcf is None or fcf <= 0:
        return None
    return (debt - cash) / fcf


def _relative_difference(left: float | None, right: float | None) -> float:
    left = safe_float(left)
    right = safe_float(right)
    if left is None or right is None:
        return 0.0
    denominator = max(abs(left), abs(right), 1e-9)
    return abs(left - right) / denominator
