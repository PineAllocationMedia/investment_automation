from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Callable
from urllib.parse import quote

from .asset_type_engine import is_etf_asset
from .utils import normalize_ticker, safe_float


HTTP_GET = Callable[..., Any]

OFFICIAL_FUND_FALLBACKS = {
    "FBTC.TO": {
        "url": "https://www.fidelity.ca/en/products/etfs/fbtc/",
        "long_name": "Fidelity Advantage Bitcoin ETF",
        "quote_type": "ETF",
        "quote_type_display": "ETF",
        "currency": "CAD",
        "fund_family": "Fidelity Investments Canada",
        "fund_category": "Bitcoin / Crypto ETF",
    },
    "FBTC": {
        "url": "https://www.fidelity.ca/en/products/etfs/fbtc/",
        "long_name": "Fidelity Advantage Bitcoin ETF",
        "quote_type": "ETF",
        "quote_type_display": "ETF",
        "currency": "CAD",
        "fund_family": "Fidelity Investments Canada",
        "fund_category": "Bitcoin / Crypto ETF",
    },
}


def fetch_fund_price_fallback(
    ticker: Any,
    *,
    is_fund_hint: bool = False,
    getter: HTTP_GET | None = None,
) -> dict[str, Any]:
    """Fetch a free fallback quote/NAV for ETFs and funds only.

    This is intentionally conservative: it never replaces good yfinance data.
    Callers should use it only when the main source failed or returned no price.
    """

    ticker = normalize_ticker(ticker)
    if not ticker:
        return {}
    if not is_fund_hint and ticker not in OFFICIAL_FUND_FALLBACKS and not is_etf_asset(ticker):
        return {}

    getter = getter or _requests_get
    yahoo_payload = _fetch_yahoo_chart_fallback(ticker, getter)
    if yahoo_payload.get("current_price") is not None:
        return yahoo_payload

    official_payload = _fetch_official_fund_fallback(ticker, getter)
    if official_payload:
        if yahoo_payload.get("error") and not official_payload.get("error"):
            official_payload["fallback_previous_error"] = yahoo_payload.get("error")
        return official_payload
    return yahoo_payload


def _fetch_yahoo_chart_fallback(ticker: str, getter: HTTP_GET) -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker)}"
    params = {"range": "10y", "interval": "1d", "events": "history"}
    try:
        response = getter(url, params=params, timeout=8, headers=_headers())
        if getattr(response, "status_code", 200) >= 400:
            return {"source": "yahoo_chart_fallback_failed", "error": f"HTTP {response.status_code}"}
        data = response.json()
    except Exception as exc:
        return {"source": "yahoo_chart_fallback_failed", "error": str(exc)}

    result = (((data or {}).get("chart") or {}).get("result") or [None])[0]
    if not result:
        error = ((data or {}).get("chart") or {}).get("error")
        return {"source": "yahoo_chart_fallback_failed", "error": str(error or "Aucune donnée chart Yahoo.")}

    meta = result.get("meta") or {}
    quote_data = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    closes = [safe_float(value) for value in quote_data.get("close") or []]
    highs = [safe_float(value) for value in quote_data.get("high") or []]
    closes = [value for value in closes if value is not None and value > 0]
    highs = [value for value in highs if value is not None and value > 0]
    current_price = first_number(
        meta.get("regularMarketPrice"),
        meta.get("previousClose"),
        closes[-1] if closes else None,
    )
    if current_price is None:
        return {"source": "yahoo_chart_fallback_failed", "error": "Prix chart Yahoo indisponible."}

    high_12m = max(highs[-252:]) if highs else None
    high_8m = max(highs[-168:]) if highs else None
    sma_200 = sum(closes[-200:]) / min(200, len(closes)) if closes else None
    payload = {
        "source": "yahoo_chart_fallback",
        "current_price": current_price,
        "high_12m": high_12m,
        "drawdown_from_12m_high": (current_price / high_12m - 1) if high_12m else None,
        "high_8m": high_8m,
        "drawdown_from_8m_high": (current_price / high_8m - 1) if high_8m else None,
        "sma_200": sma_200,
        "price_above_sma_200": bool(current_price >= sma_200) if sma_200 else None,
        "stock_return_1y": _return_from_offset(closes, 252),
        "stock_cagr_3y": _cagr_from_offset(closes, 252 * 3, 3),
        "stock_cagr_5y": _cagr_from_offset(closes, 252 * 5, 5),
        "stock_cagr_10y": _cagr_from_offset(closes, 252 * 10, 10),
        "price_5y_ago": _price_from_offset(closes, 252 * 5),
        "price_10y_ago": _price_from_offset(closes, 252 * 10),
        "cagr_5y": _cagr_from_offset(closes, 252 * 5, 5),
        "cagr_10y": _cagr_from_offset(closes, 252 * 10, 10),
        "currency": meta.get("currency"),
        "long_name": meta.get("longName") or meta.get("shortName") or meta.get("symbol"),
        "quote_type": meta.get("instrumentType") or "ETF",
        "quote_type_display": meta.get("instrumentType") or "ETF",
        "data_source_notes": ["Yahoo chart endpoint fallback"],
        "fundamental_fallback_fields": [],
        "statement_fallback_used": False,
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _fetch_official_fund_fallback(ticker: str, getter: HTTP_GET) -> dict[str, Any]:
    metadata = OFFICIAL_FUND_FALLBACKS.get(ticker)
    if not metadata:
        return {}
    payload = dict(metadata)
    payload["source"] = "official_fund_nav_fallback"
    payload["data_source_notes"] = [f"Page officielle fonds: {metadata['url']}"]
    payload["fetched_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        response = getter(metadata["url"], timeout=8, headers=_headers())
        if getattr(response, "status_code", 200) >= 400:
            payload["error"] = f"Page officielle indisponible HTTP {response.status_code}"
            return payload
        text = getattr(response, "text", "") or ""
        nav = _extract_nav_or_price(text)
        if nav is not None:
            payload["current_price"] = nav
            payload["data_source_notes"].append("Prix/NAV extrait automatiquement de la page officielle.")
    except Exception as exc:
        payload["error"] = f"Page officielle non lisible: {exc}"
    return payload


def _extract_nav_or_price(text: str) -> float | None:
    cleaned = re.sub(r"\s+", " ", text or "")
    for keyword in ["NAV", "Net asset value", "Market price", "Price"]:
        pattern = re.compile(rf"{keyword}.{{0,180}}?\$?\s*([0-9]+(?:[,.][0-9]+)?)", re.IGNORECASE)
        for match in pattern.finditer(cleaned):
            value = safe_float(match.group(1))
            if value is not None and value > 0:
                return value
    return None


def _requests_get(url: str, **kwargs: Any) -> Any:
    import requests

    return requests.get(url, **kwargs)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "Mozilla/5.0 investment-automation/1.0",
        "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    }


def first_number(*values: Any) -> float | None:
    for value in values:
        number = safe_float(value)
        if number is not None:
            return number
    return None


def _price_from_offset(closes: list[float], offset: int) -> float | None:
    if len(closes) <= offset:
        return None
    return closes[-offset]


def _return_from_offset(closes: list[float], offset: int) -> float | None:
    old_price = _price_from_offset(closes, offset)
    if old_price is None or old_price <= 0 or not closes:
        return None
    return closes[-1] / old_price - 1


def _cagr_from_offset(closes: list[float], offset: int, years: int) -> float | None:
    old_price = _price_from_offset(closes, offset)
    if old_price is None or old_price <= 0 or not closes:
        return None
    return (closes[-1] / old_price) ** (1 / years) - 1
