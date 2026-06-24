from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from .utils import CACHE_DIR, load_json, safe_float, save_json


STOCKANALYSIS_USER_AGENT = "investment-automation-local/1.0"
STOCKANALYSIS_SOURCE_NAME = "StockAnalysis Canadian financial pages"

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


class CanadianDataFetcher:
    """Best-effort Canadian fallback for TSX/TSXV fundamentals.

    This is deliberately conservative. It never replaces good yfinance price
    data, and absolute statement values are mostly used only when missing
    because some free HTML pages report financials in millions.
    """

    def __init__(
        self,
        cache_dir: str | Path = CACHE_DIR,
        timeout_seconds: int = 7,
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

        cache_path = self.cache_dir / f"stockanalysis_{meta['exchange']}_{meta['symbol']}.json"
        cached = _fresh_cached_json(cache_path, self.max_cache_age, refresh=refresh)
        if cached:
            parsed = cached.get("parsed_payload") if isinstance(cached, dict) else None
            if isinstance(parsed, dict) and parsed.get("available"):
                parsed = dict(parsed)
                parsed["fetched_at"] = cached.get("fetched_at")
                parsed["source"] = parsed.get("source") or STOCKANALYSIS_SOURCE_NAME
                return parsed

        urls = _stockanalysis_urls(str(meta["exchange"]), str(meta["symbol"]))
        raw_pages: dict[str, str] = {}
        errors: list[str] = []
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
        save_json(
            cache_path,
            {
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
                "urls": urls,
                "parsed_payload": parsed,
                "errors": errors,
            },
        )
        return parsed


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
