#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from src.canadian_data_fetcher import (
    CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
    SEDARPLUS_ENABLED,
    SEDARPLUS_BASE_URL,
    SEDARPLUS_SOURCE_NAME,
    STOCKANALYSIS_USER_AGENT,
    TMX_GRAPHQL_URL,
    TMX_QUOTE_URL,
    CanadianDataFetcher,
    _parse_tmx_payloads,
    _stockanalysis_urls,
    canadian_ticker_metadata,
    fetch_sedarplus_fundamentals,
    fetch_tmx_fundamentals,
    parse_stockanalysis_pages,
)


TICKERS = ["RHM.NE", "TOI.V", "VFV.TO"]


def _preview(text: str, limit: int = 300) -> str:
    clean = " ".join(str(text or "").replace("\n", " ").replace("\r", " ").split())
    return clean[:limit]


def _field_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload if isinstance(payload, dict) else {}
    return {
        "available": bool(payload.get("available")),
        "fields": payload.get("fields") or [],
        "coverage_status": payload.get("coverage_status") or ("EMPTY_PAYLOAD" if not payload else "N/D"),
        "errors": payload.get("errors") or payload.get("reason") or "",
    }


def _print_json(label: str, value: Any) -> None:
    print(f"{label}: {json.dumps(value, ensure_ascii=False, default=str, sort_keys=True)}")


def _request(method: str, url: str, *, json_body: dict[str, Any] | None = None) -> tuple[dict[str, Any], Any]:
    started = time.perf_counter()
    info: dict[str, Any] = {
        "method": method,
        "url": url,
        "status_code": "REQUEST_NOT_SENT",
        "content_type": "",
        "response_size": 0,
        "latency_ms": None,
        "preview_300": "",
        "error": "",
    }
    try:
        if method.upper() == "POST":
            response = requests.post(
                url,
                json=json_body or {},
                timeout=CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
                headers={"User-Agent": STOCKANALYSIS_USER_AGENT, "Content-Type": "application/json"},
            )
        else:
            response = requests.get(
                url,
                timeout=CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
                headers={"User-Agent": STOCKANALYSIS_USER_AGENT},
            )
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        text = response.text or ""
        info.update(
            {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "response_size": len(response.content or b""),
                "latency_ms": elapsed,
                "preview_300": _preview(text),
            }
        )
        parsed: Any = None
        content_type = str(response.headers.get("content-type") or "").lower()
        if "json" in content_type:
            try:
                parsed = response.json()
            except Exception as exc:  # noqa: BLE001
                info["error"] = f"JSON_PARSE_ERROR: {exc}"
        return info, parsed if parsed is not None else text
    except Exception as exc:  # noqa: BLE001
        info["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info, None


def _diagnose_stockanalysis(ticker: str, meta: dict[str, str]) -> None:
    print("SOURCE StockAnalysis")
    urls = _stockanalysis_urls(meta["exchange"], meta["symbol"])
    _print_json("stockanalysis_urls", urls)
    raw_pages: dict[str, str] = {}
    errors: list[str] = []
    for statement, url in urls.items():
        info, payload = _request("GET", url)
        _print_json(f"http_stockanalysis_{statement}", info)
        if isinstance(info.get("status_code"), int) and int(info["status_code"]) < 400 and isinstance(payload, str):
            raw_pages[statement] = payload
        else:
            errors.append(f"{statement}: HTTP/error {info.get('status_code')} {info.get('error')}".strip())
    parsed = parse_stockanalysis_pages(raw_pages, ticker=ticker, company_name="", urls=urls)
    if not parsed.get("available"):
        parsed["errors"] = errors
    _print_json("parsed_stockanalysis", _field_summary(parsed))


def _diagnose_tmx(ticker: str, meta: dict[str, str]) -> None:
    print("SOURCE TMX")
    symbol = meta["ticker"].upper()
    graphql_query = {
        "query": (
            "query getQuoteBySymbol($symbol:String!) { "
            "getQuoteBySymbol(symbol:$symbol) { "
            "symbol name MarketCap "
            "} }"
        ),
        "variables": {"symbol": symbol},
    }
    raw_payloads: list[Any] = []
    info, payload = _request("POST", TMX_GRAPHQL_URL, json_body=graphql_query)
    _print_json("http_tmx_graphql", info)
    if payload is not None:
        raw_payloads.append(payload)
    rest_url = TMX_QUOTE_URL.format(symbol=symbol)
    info, payload = _request("GET", rest_url)
    _print_json("http_tmx_rest", info)
    if payload is not None and isinstance(info.get("status_code"), int) and int(info["status_code"]) < 400:
        raw_payloads.append(payload)
    parsed_trace = _parse_tmx_payloads(raw_payloads, ticker=ticker)
    _print_json("parsed_tmx_from_traced_payloads", _field_summary(parsed_trace))
    parsed_public = fetch_tmx_fundamentals(ticker) or {}
    _print_json("parsed_tmx_function_return", _field_summary(parsed_public))


def _diagnose_sedarplus(ticker: str, meta: dict[str, str]) -> None:
    print("SOURCE SEDAR+")
    if not SEDARPLUS_ENABLED:
        _print_json(
            "source_health_sedarplus",
            {
                "source": SEDARPLUS_SOURCE_NAME,
                "available": False,
                "status": "DISABLED",
                "reason": "Captcha Radware — source non exploitable",
            },
        )
        print("sedarplus_network_calls_skipped: true")
        return
    symbol = meta["symbol"].upper()
    urls = {
        "search": f"{SEDARPLUS_BASE_URL}/csa-party/api/search?keyword={symbol}",
        "documents": (
            f"{SEDARPLUS_BASE_URL}/csa-party/api/documents"
            f"?issuer={symbol}&documentType=Annual%20Financial%20Statements"
        ),
        "filings": (
            f"{SEDARPLUS_BASE_URL}/csa-party/api/filings"
            f"?search={symbol}&category=Annual%20Financial%20Statements"
        ),
    }
    _print_json("sedarplus_urls", urls)
    for name, url in urls.items():
        info, _payload = _request("GET", url)
        _print_json(f"http_sedarplus_{name}", info)
    parsed_public = fetch_sedarplus_fundamentals(ticker) or {}
    _print_json("parsed_sedarplus_function_return", _field_summary(parsed_public))


def main() -> None:
    print("DIAGNOSTIC_CANADIAN_SOURCES_START")
    print(f"project_root: {PROJECT_ROOT}")
    print(f"import_check: CanadianDataFetcher={CanadianDataFetcher.__name__}")
    print(f"timeout_seconds: {CANADIAN_AUTHORITY_TIMEOUT_SECONDS}")
    for ticker in TICKERS:
        print("=" * 100)
        print(f"TICKER {ticker}")
        meta = canadian_ticker_metadata(ticker)
        _print_json("canadian_ticker_metadata", meta)
        if not meta:
            print(f"SKIP {ticker}: ticker canadien non reconnu")
            continue
        _diagnose_stockanalysis(ticker, meta)
        _diagnose_tmx(ticker, meta)
        _diagnose_sedarplus(ticker, meta)
    print("=" * 100)
    print("DIAGNOSTIC_CANADIAN_SOURCES_END")


if __name__ == "__main__":
    main()
