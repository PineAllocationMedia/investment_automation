from __future__ import annotations

import contextlib
import html
import io
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

from .asset_type_engine import is_etf_asset
from .benchmark_relevance_engine import COMMON_BENCHMARK_TICKERS
from .canadian_data_fetcher import (
    RATIO_OR_GROWTH_FIELDS as CANADIAN_RATIO_OR_GROWTH_FIELDS,
    CANADIAN_AUTHORITY_TIMEOUT_SECONDS,
    CanadianDataFetcher,
    is_canadian_market_candidate,
)
from .fund_price_fallback_engine import fetch_fund_price_fallback
from .official_data_fetcher import OfficialDataFetcher
from .utils import CACHE_DIR, file_age_hours, load_json, safe_float, save_json


STATEMENT_DERIVED_FIELDS = {
    "profit_margins",
    "gross_margins",
    "operating_margins",
    "total_revenue",
    "net_income",
    "revenue_growth",
    "earnings_growth",
    "return_on_equity",
    "return_on_assets",
    "total_cash",
    "total_debt",
    "debt_to_equity",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "net_debt_to_fcf",
    "shares_outstanding",
    "diluted_average_shares",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_repurchases",
    "stock_based_compensation",
    "buyback_yield",
    "sbc_to_revenue",
    "fcf_per_share",
    "fcf_per_share_growth",
    "trailing_pe",
    "peg",
}

CACHE_SCHEMA_VERSION = 11
DEFAULT_RETRY_ATTEMPTS = 2
DEFAULT_RETRY_BASE_DELAY_SECONDS = 0.35
DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD = 4
DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS = 180
LAST_KNOWN_GOOD_DIR_NAME = "last_known_good"

SEC_RECENT_MAX_AGE_DAYS = 548
SEC_CONFLICT_RELATIVE_THRESHOLD = 0.30
SEC_BALANCE_SHEET_PRIORITY_FIELDS = {"total_cash", "total_debt", "debt_to_equity", "net_debt_to_fcf"}
SEC_CONFIRM_OR_FILL_FIELDS = {
    "profit_margins",
    "gross_margins",
    "operating_margins",
    "total_revenue",
    "net_income",
    "revenue_growth",
    "earnings_growth",
    "return_on_equity",
    "return_on_assets",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "diluted_average_shares",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_repurchases",
    "stock_based_compensation",
    "buyback_yield",
    "sbc_to_revenue",
    "fcf_per_share",
    "fcf_per_share_growth",
}

CANADIAN_CONFIRM_OR_FILL_FIELDS = SEC_CONFIRM_OR_FILL_FIELDS | SEC_BALANCE_SHEET_PRIORITY_FIELDS
CANADIAN_CONFIRM_OR_FILL_FIELDS = CANADIAN_CONFIRM_OR_FILL_FIELDS | {"total_assets", "total_liabilities", "low_12m"}
CANADIAN_ABSOLUTE_FIELDS = CANADIAN_CONFIRM_OR_FILL_FIELDS - CANADIAN_RATIO_OR_GROWTH_FIELDS
CANADIAN_CONFLICT_RELATIVE_THRESHOLD = 0.15

MARKET_FIELDS = [
    "current_price",
    "high_12m",
    "low_12m",
    "drawdown_from_12m_high",
    "high_8m",
    "drawdown_from_8m_high",
    "sma_200",
    "price_above_sma_200",
    "trailing_pe",
    "forward_pe",
    "forward_eps",
    "trailing_eps",
    "number_of_analyst_opinions",
    "peg",
    "profit_margins",
    "stock_return_1y",
    "stock_cagr_3y",
    "stock_cagr_5y",
    "stock_cagr_10y",
    "market_cap",
    "beta",
    "dividend_yield",
    "payout_ratio",
    "quote_type",
    "quote_type_display",
    "fund_family",
    "fund_category",
    "return_on_equity",
    "return_on_assets",
    "total_revenue",
    "net_income",
    "revenue_growth",
    "earnings_growth",
    "revenue_quarterly_growth",
    "earnings_quarterly_growth",
    "gross_margins",
    "operating_margins",
    "total_debt",
    "total_assets",
    "total_liabilities",
    "total_cash",
    "debt_to_equity",
    "operating_cash_flow",
    "capital_expenditures",
    "free_cash_flow",
    "free_cash_flow_margin",
    "free_cash_flow_growth",
    "fcf_conversion",
    "net_debt_to_fcf",
    "shares_outstanding",
    "diluted_average_shares",
    "share_count_growth_1y",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_repurchases",
    "stock_based_compensation",
    "buyback_yield",
    "sbc_to_revenue",
    "fcf_per_share",
    "fcf_per_share_growth",
    "long_name",
    "business_summary",
    "website",
    "company_city",
    "company_state",
    "full_time_employees",
    "sector_name",
    "industry",
    "country",
    "currency",
    "price_5y_ago",
    "price_10y_ago",
    "cagr_5y",
    "cagr_10y",
    "adjusted_current_price",
    "adjusted_price_5y_ago",
    "adjusted_price_10y_ago",
    "adjusted_stock_return_1y",
    "adjusted_stock_cagr_3y",
    "adjusted_stock_cagr_5y",
    "adjusted_stock_cagr_10y",
    "adjusted_cagr_5y",
    "adjusted_cagr_10y",
    "total_return_price",
    "total_return_price_history",
    "total_return_basis",
    "data_source_notes",
    "fundamental_fallback_fields",
    "statement_fallback_used",
    "official_data_sources",
    "official_fundamental_fields",
    "official_confirmed_fields",
    "official_data_conflicts",
    "official_source_policy",
    "canadian_data_sources",
    "canadian_fundamental_fields",
    "canadian_confirmed_fields",
    "canadian_data_conflicts",
    "canadian_source_policy",
    "canadian_source_health",
    "canadian_coverage_status",
    "canadian_latest_period",
    "canadian_checked_at",
    "sec_edgar_cik",
    "sec_edgar_company_name",
    "sec_edgar_latest_filing_date",
    "sec_edgar_latest_fiscal_year",
    "data_fill_rate",
    "news_red_flags",
    "news_red_flag_count",
    "news_checked_at",
    "news_context_headlines",
    "news_context_sources",
    "news_context_urls",
    "news_context_published_at",
    "news_context_checked_at",
    "news_context_source_channels",
    "news_context_search_queries",
    "market_data_fetch_status",
    "market_data_fetch_attempts",
    "market_data_fetch_attempted_at",
    "market_data_fallback_level",
    "market_data_warning_flags",
    "market_data_circuit_breaker_open",
    "market_data_last_error",
    "market_data_last_success_at",
    "last_known_good_at",
    "last_known_good_source",
]

FX_TO_CAD_TICKERS = {
    "USD": "USDCAD=X",
    "EUR": "EURCAD=X",
    "GBP": "GBPCAD=X",
    "CHF": "CHFCAD=X",
    "JPY": "JPYCAD=X",
}

FX_TO_CAD_FALLBACK_RATES = {
    "USD": 1.35,
    "EUR": 1.47,
    "GBP": 1.72,
    "CHF": 1.52,
    "JPY": 0.009,
}

PUBLIC_NEWS_CONTEXT_TIMEOUT_SECONDS = 4
PUBLIC_NEWS_CONTEXT_MAX_ITEMS = 6


class MarketDataFetchError(RuntimeError):
    def __init__(self, ticker: str, attempts: int, original_error: Exception | None) -> None:
        self.ticker = ticker
        self.attempts = attempts
        self.original_error = original_error
        message = str(original_error or "Source de marché indisponible.")
        super().__init__(message)


class MarketDataFetcher:
    def __init__(
        self,
        cache_dir: str | Path = CACHE_DIR,
        max_cache_age_hours: int = 18,
        retry_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        retry_base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS,
        circuit_breaker_failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        circuit_breaker_cooldown_seconds: int = DEFAULT_CIRCUIT_BREAKER_COOLDOWN_SECONDS,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.max_cache_age_hours = max_cache_age_hours
        self.retry_attempts = max(1, int(retry_attempts))
        self.retry_base_delay_seconds = max(0.0, float(retry_base_delay_seconds))
        self.circuit_breaker_failure_threshold = max(1, int(circuit_breaker_failure_threshold))
        self.circuit_breaker_cooldown_seconds = max(1, int(circuit_breaker_cooldown_seconds))
        self._consecutive_fetch_failures = 0
        self._circuit_opened_at: float | None = None
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.last_known_good_dir = self.cache_dir / LAST_KNOWN_GOOD_DIR_NAME
        self.last_known_good_dir.mkdir(parents=True, exist_ok=True)
        self.official_data = OfficialDataFetcher(self.cache_dir)
        self.canadian_data = CanadianDataFetcher(self.cache_dir, timeout_seconds=CANADIAN_AUTHORITY_TIMEOUT_SECONDS)

    def fetch_all(
        self, tickers: list[str], benchmark_map: dict[str, str], refresh: bool = False
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
        all_benchmarks = sorted({value for value in benchmark_map.values() if value} | COMMON_BENCHMARK_TICKERS)
        market_data = {ticker: self.fetch_ticker(ticker, refresh=refresh) for ticker in sorted(set(tickers))}
        benchmark_data = {ticker: self.fetch_ticker(ticker, refresh=refresh) for ticker in all_benchmarks}
        data_gaps = []
        for ticker, payload in {**market_data, **benchmark_data}.items():
            for field in self.required_fields_for_gap_report(ticker, payload):
                data_gaps.append(
                    {
                        "ticker": ticker,
                        "data_field": field,
                        "importance": "MEDIUM" if field in {"market_cap", "beta", "dividend_yield"} else "HIGH",
                        "impact": "Le moteur continue, mais réduit la confiance ou utilise les données manuelles si disponibles.",
                    }
                )
        return market_data, benchmark_data, data_gaps

    def fetch_fx_rates_to_cad(self, currencies: list[str], refresh: bool = False) -> dict[str, float]:
        rates = {"CAD": 1.0}
        for currency in sorted({str(value or "").upper() for value in currencies}):
            if not currency or currency in rates:
                continue
            fx_ticker = FX_TO_CAD_TICKERS.get(currency)
            if not fx_ticker:
                continue
            official_rate = self.official_data.fetch_bank_of_canada_fx_rate(currency, refresh=refresh)
            rate = safe_float((official_rate or {}).get("rate"))
            if rate is None:
                rate = self._fetch_simple_fx_rate(fx_ticker)
            if rate is None:
                payload = self.fetch_ticker(fx_ticker, refresh=refresh)
                rate = safe_float(payload.get("current_price"))
            if rate is None:
                rate = FX_TO_CAD_FALLBACK_RATES.get(currency)
            if rate is not None and rate > 0:
                rates[currency] = rate
        return rates

    def _fetch_simple_fx_rate(self, fx_ticker: str) -> float | None:
        try:
            import yfinance as yf  # type: ignore

            instrument = yf.Ticker(fx_ticker)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                history = instrument.history(period="5d", auto_adjust=False)
            closes = _series_values(history, "Close")
            closes = [value for value in closes if value is not None and value > 0]
            return closes[-1] if closes else None
        except Exception:
            return None

    def required_fields_for_gap_report(self, ticker: str, payload: dict[str, Any]) -> list[str]:
        important = ["current_price", "sma_200", "stock_return_1y"]
        if ticker.endswith(".TO") or ticker in {
            "VFV.TO",
            "XLY",
            "IGV",
            "XLI",
            "SOXX",
            "IPAY",
            "XLV",
            "KCE",
            "XLK",
            "XLC",
            "XLP",
            "XLF",
            "XLB",
            "ICLN",
            "XLU",
            "XLE",
        }:
            important.append("cagr_5y")
        return [field for field in important if payload.get(field) is None]

    def fetch_ticker(self, ticker: str, refresh: bool = False) -> dict[str, Any]:
        cache_path = self._cache_path(ticker)
        age = file_age_hours(cache_path)
        cached = load_json(cache_path)
        if not refresh and age is not None and age <= self.max_cache_age_hours:
            if self._is_direct_cache_hit(cached):
                if cached.get("cache_schema_version") == CACHE_SCHEMA_VERSION:
                    return self._cached_with_defaults(
                        ticker,
                        cached,
                        fetch_status="FRESH_CACHE",
                        fallback_level="NONE",
                        warning_flags=[],
                    )

        attempts = 0
        payload = self._empty_payload(ticker)
        try:
            if self._is_circuit_open():
                raise MarketDataFetchError(ticker, 0, RuntimeError("Coupe-circuit données de marché actif."))
            fetched, attempts = self._fetch_with_retry(ticker)
            payload.update({key: value for key, value in fetched.items() if key in payload})
            payload["source"] = fetched.get("source") or "yfinance"
            if payload.get("current_price") is None and is_etf_asset(ticker, payload):
                self._fill_from_fund_price_fallback(ticker, payload)
            self._record_fetch_success()
        except Exception as exc:
            attempts = getattr(exc, "attempts", attempts or self.retry_attempts)
            circuit_open = self._is_circuit_open()
            if not circuit_open:
                self._record_fetch_failure()
                circuit_open = self._is_circuit_open()
            warning = f"Actualisation impossible: {exc}"
            warning_flags = ["CIRCUIT_OPEN"] if isinstance(exc, MarketDataFetchError) and exc.attempts == 0 else ["FETCH_FAILED"]
            if circuit_open and "CIRCUIT_OPEN" not in warning_flags:
                warning_flags.append("CIRCUIT_OPEN")
            if self._is_usable_market_payload(cached):
                fallback_payload = self._cache_fallback_payload(
                    ticker,
                    cached,
                    warning,
                    fetch_status="FALLBACK_STALE_CACHE",
                    fallback_level="STALE_CACHE",
                    warning_flags=warning_flags,
                    attempts=attempts,
                    last_error=str(exc),
                    circuit_open=circuit_open,
                )
                self._augment_fallback_payload_with_canadian_sources(ticker, fallback_payload)
                return fallback_payload
            last_known_good = self._load_last_known_good(ticker)
            if self._is_usable_market_payload(last_known_good):
                fallback_payload = self._cache_fallback_payload(
                    ticker,
                    last_known_good,
                    warning,
                    fetch_status="FALLBACK_LAST_KNOWN_GOOD",
                    fallback_level="LAST_KNOWN_GOOD",
                    warning_flags=warning_flags,
                    attempts=attempts,
                    last_error=str(exc),
                    circuit_open=circuit_open,
                    source_override="last_known_good",
                )
                self._augment_fallback_payload_with_canadian_sources(ticker, fallback_payload)
                return fallback_payload
            payload["source"] = "unavailable"
            payload["error"] = str(exc)
            self._fill_from_fund_price_fallback(ticker, payload)
            status = "FALLBACK_FUND_PRICE" if payload.get("source") not in {"unavailable", "empty"} else "UNAVAILABLE"
            fallback_level = "FUND_PRICE" if status == "FALLBACK_FUND_PRICE" else "NONE"
            self._apply_fetch_metadata(
                payload,
                fetch_status=status,
                attempts=attempts,
                fallback_level=fallback_level,
                warning_flags=warning_flags,
                last_error=str(exc),
                circuit_open=circuit_open,
            )

        payload["fetched_at"] = datetime.now().isoformat(timespec="seconds")
        payload["cache_schema_version"] = CACHE_SCHEMA_VERSION
        payload["data_fill_rate"] = data_fill_rate(payload)
        self._apply_fetch_metadata(
            payload,
            fetch_status=payload.get("market_data_fetch_status") or "LIVE_SUCCESS",
            attempts=attempts or 1,
            fallback_level=payload.get("market_data_fallback_level") or "NONE",
            warning_flags=payload.get("market_data_warning_flags") or [],
            last_error=payload.get("market_data_last_error"),
            circuit_open=bool(payload.get("market_data_circuit_breaker_open")),
        )
        save_json(cache_path, payload)
        if self._is_last_known_good_candidate(payload):
            self._save_last_known_good(ticker, payload)
        return payload

    def _cached_with_defaults(
        self,
        ticker: str,
        cached: dict[str, Any],
        warning: str | None = None,
        *,
        fetch_status: str | None = None,
        fallback_level: str | None = None,
        warning_flags: list[str] | None = None,
        attempts: int | None = None,
        last_error: str | None = None,
        circuit_open: bool | None = None,
        source_override: str | None = None,
    ) -> dict[str, Any]:
        payload = self._empty_payload(ticker)
        payload.update({key: value for key, value in cached.items() if key in payload})
        payload["ticker"] = ticker
        if warning:
            payload["source"] = source_override or "stale_cache"
            payload["stale_cache_warning"] = warning
        elif source_override:
            payload["source"] = source_override
        notes = list(payload.get("data_source_notes") or ["cache local yfinance"])
        if source_override == "last_known_good":
            notes.append("derniere bonne donnee connue du cache local")
        payload["data_source_notes"] = sorted(set(notes))
        payload["fundamental_fallback_fields"] = payload.get("fundamental_fallback_fields") or []
        payload["statement_fallback_used"] = bool(payload.get("statement_fallback_used"))
        payload["official_data_sources"] = payload.get("official_data_sources") or []
        payload["official_fundamental_fields"] = payload.get("official_fundamental_fields") or []
        payload["official_confirmed_fields"] = payload.get("official_confirmed_fields") or []
        payload["official_data_conflicts"] = payload.get("official_data_conflicts") or []
        payload["official_source_policy"] = payload.get("official_source_policy") or []
        payload["canadian_data_sources"] = payload.get("canadian_data_sources") or []
        payload["canadian_fundamental_fields"] = payload.get("canadian_fundamental_fields") or []
        payload["canadian_confirmed_fields"] = payload.get("canadian_confirmed_fields") or []
        payload["canadian_data_conflicts"] = payload.get("canadian_data_conflicts") or []
        payload["canadian_source_policy"] = payload.get("canadian_source_policy") or []
        payload["data_fill_rate"] = payload.get("data_fill_rate") or data_fill_rate(payload)
        self._apply_fetch_metadata(
            payload,
            fetch_status=fetch_status or payload.get("market_data_fetch_status") or ("STALE_CACHE" if warning else "CACHE"),
            attempts=attempts,
            fallback_level=fallback_level or payload.get("market_data_fallback_level") or ("STALE_CACHE" if warning else "NONE"),
            warning_flags=warning_flags if warning_flags is not None else payload.get("market_data_warning_flags") or [],
            last_error=last_error,
            circuit_open=circuit_open,
        )
        return payload

    def _fetch_with_retry(self, ticker: str) -> tuple[dict[str, Any], int]:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return self._fetch_with_yfinance(ticker), attempt
            except Exception as exc:
                last_error = exc
                if attempt < self.retry_attempts and self.retry_base_delay_seconds > 0:
                    time.sleep(self.retry_base_delay_seconds * (2 ** (attempt - 1)))
        raise MarketDataFetchError(ticker, self.retry_attempts, last_error)

    def _cache_fallback_payload(
        self,
        ticker: str,
        cached: dict[str, Any],
        warning: str,
        *,
        fetch_status: str,
        fallback_level: str,
        warning_flags: list[str],
        attempts: int,
        last_error: str,
        circuit_open: bool,
        source_override: str | None = None,
    ) -> dict[str, Any]:
        payload = self._cached_with_defaults(
            ticker,
            cached,
            warning,
            fetch_status=fetch_status,
            fallback_level=fallback_level,
            warning_flags=warning_flags,
            attempts=attempts,
            last_error=last_error,
            circuit_open=circuit_open,
            source_override=source_override,
        )
        payload["cache_schema_version"] = CACHE_SCHEMA_VERSION
        return payload

    def _apply_fetch_metadata(
        self,
        payload: dict[str, Any],
        *,
        fetch_status: str,
        attempts: int | None,
        fallback_level: str,
        warning_flags: list[str] | None,
        last_error: str | None,
        circuit_open: bool | None,
    ) -> None:
        payload["market_data_fetch_status"] = fetch_status
        payload["market_data_fetch_attempts"] = attempts
        payload["market_data_fetch_attempted_at"] = datetime.now().isoformat(timespec="seconds")
        payload["market_data_fallback_level"] = fallback_level
        payload["market_data_warning_flags"] = sorted({str(flag) for flag in (warning_flags or []) if flag})
        payload["market_data_circuit_breaker_open"] = bool(circuit_open)
        payload["market_data_last_error"] = last_error
        if fetch_status == "LIVE_SUCCESS":
            payload["market_data_last_success_at"] = payload.get("fetched_at") or datetime.now().isoformat(timespec="seconds")

    def _record_fetch_success(self) -> None:
        self._consecutive_fetch_failures = 0
        self._circuit_opened_at = None

    def _record_fetch_failure(self) -> None:
        self._consecutive_fetch_failures += 1
        if self._consecutive_fetch_failures >= self.circuit_breaker_failure_threshold:
            self._circuit_opened_at = time.monotonic()

    def _is_circuit_open(self) -> bool:
        if self._circuit_opened_at is None:
            return False
        elapsed = time.monotonic() - self._circuit_opened_at
        if elapsed >= self.circuit_breaker_cooldown_seconds:
            self._consecutive_fetch_failures = 0
            self._circuit_opened_at = None
            return False
        return True

    def _cache_path(self, ticker: str) -> Path:
        return self.cache_dir / f"{ticker.replace('/', '_')}.json"

    def _last_known_good_path(self, ticker: str) -> Path:
        return self.last_known_good_dir / f"{ticker.replace('/', '_')}.json"

    def _load_last_known_good(self, ticker: str) -> dict[str, Any]:
        return load_json(self._last_known_good_path(ticker))

    def _save_last_known_good(self, ticker: str, payload: dict[str, Any]) -> None:
        saved = dict(payload)
        saved["last_known_good_at"] = payload.get("fetched_at") or datetime.now().isoformat(timespec="seconds")
        saved["last_known_good_source"] = payload.get("source")
        save_json(self._last_known_good_path(ticker), saved)

    def _is_usable_market_payload(self, payload: dict[str, Any]) -> bool:
        if not payload:
            return False
        source = str(payload.get("source") or "").strip()
        if source in {"", "empty", "unavailable"}:
            return False
        return safe_float(payload.get("current_price")) is not None

    def _is_direct_cache_hit(self, payload: dict[str, Any]) -> bool:
        if not self._is_usable_market_payload(payload):
            return False
        return str(payload.get("source") or "").strip() not in {"stale_cache", "last_known_good"}

    def _is_last_known_good_candidate(self, payload: dict[str, Any]) -> bool:
        if not self._is_usable_market_payload(payload):
            return False
        source = str(payload.get("source") or "").strip()
        if source in {"stale_cache", "last_known_good"}:
            return False
        return payload.get("market_data_fetch_status") in {"LIVE_SUCCESS", "FALLBACK_FUND_PRICE"}

    def _fetch_with_yfinance(self, ticker: str) -> dict[str, Any]:
        import yfinance as yf  # type: ignore

        instrument = yf.Ticker(ticker)
        history, history_period = self._history_with_fallback(instrument)
        closes = _series_values(history, "Close")
        closes = [value for value in closes if value is not None and value > 0]
        if not closes:
            raise RuntimeError("Aucun historique de prix reçu.")
        adjusted_closes = _series_values(history, "Adj Close")
        adjusted_closes = [value for value in adjusted_closes if value is not None and value > 0]
        total_return_closes = adjusted_closes if adjusted_closes else closes
        total_return_basis = "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY" if adjusted_closes else "PRICE_CLOSE_NO_ADJUSTED_CLOSE"
        total_return_history = _series_history(history, "Adj Close" if adjusted_closes else "Close")
        highs = _series_values(history, "High") or closes

        current_price = closes[-1]
        recent_12m = highs[-252:] if len(highs) >= 252 else highs
        recent_8m = highs[-168:] if len(highs) >= 168 else highs
        high_12m = max(recent_12m) if recent_12m else None
        high_8m = max(recent_8m) if recent_8m else None
        sma_200 = sum(closes[-200:]) / min(200, len(closes)) if closes else None

        info: dict[str, Any] = {}
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                info = instrument.info or {}
        except Exception:
            info = {}
        fast_info = _safe_fast_info(instrument)
        current_price = first_number(
            _lookup(fast_info, "lastPrice", "last_price", "regularMarketPrice"),
            info.get("currentPrice"),
            info.get("regularMarketPrice"),
            current_price,
        )

        payload = {
            "current_price": current_price,
            "high_12m": high_12m,
            "drawdown_from_12m_high": (current_price / high_12m - 1) if high_12m else None,
            "high_8m": high_8m,
            "drawdown_from_8m_high": (current_price / high_8m - 1) if high_8m else None,
            "sma_200": sma_200,
            "price_above_sma_200": bool(current_price >= sma_200) if sma_200 else None,
            "trailing_pe": safe_float(info.get("trailingPE")),
            "forward_pe": safe_float(info.get("forwardPE")),
            "forward_eps": safe_float(info.get("forwardEps")),
            "trailing_eps": safe_float(info.get("trailingEps")),
            "number_of_analyst_opinions": _safe_non_negative_int(info.get("numberOfAnalystOpinions")),
            "peg": safe_float(info.get("pegRatio") or info.get("trailingPegRatio")),
            "profit_margins": safe_float(info.get("profitMargins")),
            "stock_return_1y": self._return_from_offset(closes, 252),
            "stock_cagr_3y": self._cagr_from_offset(closes, 252 * 3, 3),
            "stock_cagr_5y": self._cagr_from_offset(closes, 252 * 5, 5),
            "stock_cagr_10y": self._cagr_from_offset(closes, 252 * 10, 10),
            "market_cap": safe_float(info.get("marketCap")),
            "shares_outstanding": safe_float(
                info.get("sharesOutstanding")
                or info.get("impliedSharesOutstanding")
                or info.get("floatShares")
            ),
            "beta": safe_float(info.get("beta")),
            "dividend_yield": safe_float(info.get("dividendYield")),
            "payout_ratio": safe_float(info.get("payoutRatio")),
            "quote_type": info.get("quoteType"),
            "quote_type_display": info.get("typeDisp"),
            "fund_family": info.get("fundFamily"),
            "fund_category": info.get("category"),
            "return_on_equity": safe_float(info.get("returnOnEquity")),
            "return_on_assets": safe_float(info.get("returnOnAssets")),
            "revenue_growth": safe_float(info.get("revenueGrowth")),
            "earnings_growth": safe_float(info.get("earningsGrowth")),
            "revenue_quarterly_growth": safe_float(info.get("revenueQuarterlyGrowth")),
            "earnings_quarterly_growth": safe_float(info.get("earningsQuarterlyGrowth")),
            "gross_margins": safe_float(info.get("grossMargins")),
            "operating_margins": safe_float(info.get("operatingMargins")),
            "total_debt": safe_float(info.get("totalDebt")),
            "total_cash": safe_float(info.get("totalCash")),
            "debt_to_equity": safe_float(info.get("debtToEquity")),
            "long_name": info.get("longName") or info.get("shortName"),
            "business_summary": info.get("longBusinessSummary"),
            "website": info.get("website"),
            "company_city": info.get("city"),
            "company_state": info.get("state"),
            "full_time_employees": safe_float(info.get("fullTimeEmployees")),
            "sector_name": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "currency": info.get("currency"),
            "price_5y_ago": self._price_from_offset(closes, 252 * 5),
            "price_10y_ago": self._price_from_offset(closes, 252 * 10),
            "cagr_5y": self._cagr_from_offset(closes, 252 * 5, 5),
            "cagr_10y": self._cagr_from_offset(closes, 252 * 10, 10),
            "adjusted_current_price": adjusted_closes[-1] if adjusted_closes else None,
            "adjusted_price_5y_ago": self._price_from_offset(adjusted_closes, 252 * 5),
            "adjusted_price_10y_ago": self._price_from_offset(adjusted_closes, 252 * 10),
            "adjusted_stock_return_1y": self._return_from_offset(adjusted_closes, 252),
            "adjusted_stock_cagr_3y": self._cagr_from_offset(adjusted_closes, 252 * 3, 3),
            "adjusted_stock_cagr_5y": self._cagr_from_offset(adjusted_closes, 252 * 5, 5),
            "adjusted_stock_cagr_10y": self._cagr_from_offset(adjusted_closes, 252 * 10, 10),
            "adjusted_cagr_5y": self._cagr_from_offset(adjusted_closes, 252 * 5, 5),
            "adjusted_cagr_10y": self._cagr_from_offset(adjusted_closes, 252 * 10, 10),
            "total_return_price": total_return_closes[-1] if total_return_closes else current_price,
            "total_return_price_history": total_return_history,
            "total_return_basis": total_return_basis,
            "data_source_notes": [f"yfinance history ({history_period})", "yfinance info"],
            "fundamental_fallback_fields": [],
            "statement_fallback_used": False,
            "official_data_sources": [],
            "official_fundamental_fields": [],
            "official_confirmed_fields": [],
            "official_data_conflicts": [],
            "official_source_policy": [],
            "canadian_data_sources": [],
            "canadian_fundamental_fields": [],
            "canadian_confirmed_fields": [],
            "canadian_data_conflicts": [],
            "canadian_source_policy": [],
            "canadian_coverage_status": None,
            "canadian_latest_period": None,
            "canadian_checked_at": None,
            "sec_edgar_cik": None,
            "sec_edgar_company_name": None,
            "sec_edgar_latest_filing_date": None,
            "sec_edgar_latest_fiscal_year": None,
            "news_red_flags": [],
            "news_red_flag_count": 0,
            "news_checked_at": None,
            "news_context_headlines": [],
            "news_context_sources": [],
            "news_context_urls": [],
            "news_context_published_at": [],
            "news_context_checked_at": None,
            "news_context_source_channels": [],
            "news_context_search_queries": [],
        }
        fallback_fields: list[str] = []
        notes: list[str] = list(payload["data_source_notes"])
        news_items = _safe_news_context_items(instrument)
        if news_items:
            _merge_news_context_items(payload, news_items, channel="yfinance/Yahoo Finance")
            notes.append("nouvelles yfinance/Yahoo Finance: titres récents utilisés comme contexte")
        if _should_fetch_public_news_context(payload):
            public_news = _fetch_google_news_rss_context(
                ticker=ticker,
                company_name=str(payload.get("long_name") or info.get("longName") or info.get("shortName") or ""),
            )
            if public_news["items"]:
                _merge_news_context_items(payload, public_news["items"], channel="Google News RSS")
                payload["news_context_search_queries"] = sorted(
                    set((payload.get("news_context_search_queries") or []) + public_news["queries"])
                )
                notes.append("nouvelles Google News RSS: titres récents utilisés comme contexte")
        self._fill_from_fast_info(payload, fast_info, notes, fallback_fields)
        self._fill_from_financial_statements(payload, instrument, notes, fallback_fields)
        self._fill_from_sec_edgar(ticker, payload, notes)
        self._fill_from_canadian_sources(ticker, payload, notes)
        news_flags = _news_red_flags_from_titles(payload.get("news_context_headlines") or [])
        if news_flags:
            payload["news_red_flags"] = news_flags[:5]
            payload["news_red_flag_count"] = len(news_flags)
            payload["news_checked_at"] = datetime.now().isoformat(timespec="seconds")
            notes.append("nouvelles yfinance: signaux de risque détectés")
        payload["data_source_notes"] = sorted(set(notes))
        payload["fundamental_fallback_fields"] = sorted(set(fallback_fields))
        payload["statement_fallback_used"] = bool(set(fallback_fields) & STATEMENT_DERIVED_FIELDS)
        payload["official_data_sources"] = sorted(set(payload.get("official_data_sources") or []))
        payload["official_fundamental_fields"] = sorted(set(payload.get("official_fundamental_fields") or []))
        payload["official_confirmed_fields"] = sorted(set(payload.get("official_confirmed_fields") or []))
        payload["official_data_conflicts"] = sorted(set(payload.get("official_data_conflicts") or []))
        payload["official_source_policy"] = sorted(set(payload.get("official_source_policy") or []))
        payload["canadian_data_sources"] = sorted(set(payload.get("canadian_data_sources") or []))
        payload["canadian_fundamental_fields"] = sorted(set(payload.get("canadian_fundamental_fields") or []))
        payload["canadian_confirmed_fields"] = sorted(set(payload.get("canadian_confirmed_fields") or []))
        payload["canadian_data_conflicts"] = sorted(set(payload.get("canadian_data_conflicts") or []))
        payload["canadian_source_policy"] = sorted(set(payload.get("canadian_source_policy") or []))
        if payload["official_fundamental_fields"] or payload["official_confirmed_fields"]:
            payload["source"] = "yfinance+official"
        payload["data_fill_rate"] = data_fill_rate(payload)
        return payload

    def _history_with_fallback(self, instrument: Any) -> tuple[Any, str]:
        last_error: Exception | None = None
        for period in ["10y", "5y", "3y", "1y", "max"]:
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    history = instrument.history(period=period, auto_adjust=False)
                if history is not None and not getattr(history, "empty", False):
                    return history, period
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Aucun historique de prix reçu.")

    def _fill_from_fast_info(
        self,
        payload: dict[str, Any],
        fast_info: dict[str, Any],
        notes: list[str],
        fallback_fields: list[str],
    ) -> None:
        set_if_missing(
            payload,
            "market_cap",
            _lookup(fast_info, "marketCap", "market_cap"),
            "yfinance fast_info",
            notes,
            fallback_fields,
        )
        set_if_missing(payload, "currency", _lookup(fast_info, "currency"), "yfinance fast_info", notes, fallback_fields)
        shares = first_number(_lookup(fast_info, "shares", "sharesOutstanding"), _lookup(fast_info, "shares_outstanding"))
        set_if_missing(payload, "shares_outstanding", shares, "yfinance fast_info", notes, fallback_fields)
        if payload.get("market_cap") is None and shares is not None and payload.get("current_price") is not None:
            set_if_missing(
                payload,
                "market_cap",
                shares * (safe_float(payload.get("current_price")) or 0.0),
                "yfinance fast_info shares x prix",
                notes,
                fallback_fields,
            )

    def _fill_from_financial_statements(
        self,
        payload: dict[str, Any],
        instrument: Any,
        notes: list[str],
        fallback_fields: list[str],
    ) -> None:
        income = _get_statement(instrument, ["income_stmt", "financials"])
        balance = _get_statement(instrument, ["balance_sheet"])
        cashflow = _get_statement(instrument, ["cashflow", "cash_flow", "cash_flow_statement"])
        if income is None and balance is None and cashflow is None:
            return

        revenue = _statement_values(income, ["Total Revenue", "Operating Revenue"])
        net_income = _statement_values(income, ["Net Income", "Net Income Common Stockholders"])
        gross_profit = _statement_values(income, ["Gross Profit"])
        operating_income = _statement_values(income, ["Operating Income", "EBIT"])
        diluted_eps = _statement_values(income, ["Diluted EPS", "Diluted EPS Diluted EPS"])
        diluted_shares = _statement_values(
            income,
            [
                "Diluted Average Shares",
                "Diluted Shares",
                "Weighted Average Diluted Shares Outstanding",
                "Weighted Average Number Of Diluted Shares Outstanding",
            ],
        )
        basic_shares = _statement_values(
            income,
            [
                "Basic Average Shares",
                "Basic Shares",
                "Weighted Average Shares",
                "Weighted Average Number Of Shares Outstanding Basic",
            ],
        )
        share_count_series = diluted_shares or basic_shares
        operating_cash_flow = _statement_values(
            cashflow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                "Cash Flow From Continuing Operating Activities",
                "Net Cash Provided By Operating Activities",
            ],
        )
        raw_capex = _statement_values(
            cashflow,
            [
                "Capital Expenditure",
                "Capital Expenditures",
                "Capital Expenditure Reported",
                "Purchase Of Property Plant Equipment",
                "Purchase Of PPE",
                "Investments In Property Plant And Equipment",
            ],
        )
        capex_outflow = [_capex_outflow(value) for value in raw_capex]
        free_cash_flow_statement = _statement_values(cashflow, ["Free Cash Flow"])
        free_cash_flow = _free_cash_flow_values(operating_cash_flow, capex_outflow, free_cash_flow_statement)
        raw_share_repurchases = _statement_values(
            cashflow,
            [
                "Repurchase Of Capital Stock",
                "Repurchase Of Common Stock",
                "Common Stock Payments",
                "Payments For Repurchase Of Common Stock",
                "Purchase Of Common Stock",
            ],
        )
        share_repurchases = [_cash_outflow(value) for value in raw_share_repurchases]
        stock_based_compensation = _statement_values(
            cashflow,
            [
                "Stock Based Compensation",
                "Stock Based Compensation Expense",
                "Share Based Compensation",
            ],
        )
        fcf_per_share_series = _per_share_values(free_cash_flow, share_count_series)
        assets = _statement_values(balance, ["Total Assets"])
        equity = _statement_values(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest", "Common Stock Equity"])
        cash = _statement_values(balance, ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"])
        total_debt = _statement_values(balance, ["Total Debt"])
        if not total_debt:
            long_debt = _statement_values(balance, ["Long Term Debt"])
            current_debt = _statement_values(balance, ["Current Debt", "Current Debt And Capital Lease Obligation"])
            if long_debt or current_debt:
                latest_long = long_debt[0] if long_debt else 0.0
                latest_current = current_debt[0] if current_debt else 0.0
                total_debt = [latest_long + latest_current]

        set_if_missing(payload, "profit_margins", ratio_latest(net_income, revenue), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "gross_margins", ratio_latest(gross_profit, revenue), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "operating_margins", ratio_latest(operating_income, revenue), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "total_revenue", first_number(*(revenue[:1])), "yfinance income statement", notes, fallback_fields)
        set_if_missing(payload, "net_income", first_number(*(net_income[:1])), "yfinance income statement", notes, fallback_fields)
        set_if_missing(payload, "revenue_growth", growth_latest(revenue), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "earnings_growth", growth_latest(net_income), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "return_on_equity", return_ratio(net_income, equity), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "return_on_assets", return_ratio(net_income, assets), "yfinance financial statements", notes, fallback_fields)
        set_if_missing(payload, "total_cash", first_number(*cash), "yfinance balance sheet", notes, fallback_fields)
        set_if_missing(payload, "total_debt", first_number(*total_debt), "yfinance balance sheet", notes, fallback_fields)
        set_if_missing(
            payload,
            "operating_cash_flow",
            first_number(*(operating_cash_flow[:1])),
            "yfinance cash flow statement",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "capital_expenditures",
            first_number(*(capex_outflow[:1])),
            "yfinance cash flow statement, capex normalisé en sortie positive",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "free_cash_flow",
            first_number(*(free_cash_flow[:1])),
            "yfinance cash flow statement",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "free_cash_flow_margin",
            ratio_latest(free_cash_flow, revenue),
            "free cash flow / revenus",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "free_cash_flow_growth",
            growth_latest(free_cash_flow),
            "croissance annuelle free cash flow",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "fcf_conversion",
            ratio_latest(free_cash_flow, net_income),
            "free cash flow / net income",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "diluted_average_shares",
            first_number(*(share_count_series[:1])),
            "yfinance income statement share count",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "share_count_growth_1y",
            growth_latest(share_count_series),
            "variation annuelle du nombre moyen d’actions",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "share_count_cagr_3y",
            cagr_from_series(share_count_series, 3),
            "CAGR 3 ans du nombre moyen d’actions",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "share_count_cagr_5y",
            cagr_from_series(share_count_series, 5),
            "CAGR 5 ans du nombre moyen d’actions",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "share_repurchases",
            first_number(*(share_repurchases[:1])),
            "yfinance cash flow statement, rachats normalisés en sortie positive",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "stock_based_compensation",
            first_number(*(stock_based_compensation[:1])),
            "yfinance cash flow statement",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "sbc_to_revenue",
            ratio_latest(stock_based_compensation, revenue),
            "stock based compensation / revenus",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "fcf_per_share",
            first_number(*(fcf_per_share_series[:1])),
            "free cash flow / action moyenne diluée",
            notes,
            fallback_fields,
        )
        set_if_missing(
            payload,
            "fcf_per_share_growth",
            growth_latest(fcf_per_share_series),
            "croissance annuelle FCF par action",
            notes,
            fallback_fields,
        )
        market_cap = safe_float(payload.get("market_cap"))
        latest_repurchases = first_number(*(share_repurchases[:1]))
        if market_cap is not None and market_cap > 0 and latest_repurchases is not None:
            set_if_missing(
                payload,
                "buyback_yield",
                latest_repurchases / market_cap,
                "rachats / capitalisation boursière",
                notes,
                fallback_fields,
            )
        debt = safe_float(payload.get("total_debt"))
        latest_cash = safe_float(payload.get("total_cash"))
        latest_fcf = safe_float(payload.get("free_cash_flow"))
        if debt is not None and latest_cash is not None and latest_fcf is not None and latest_fcf > 0:
            set_if_missing(
                payload,
                "net_debt_to_fcf",
                (debt - latest_cash) / latest_fcf,
                "dette nette / free cash flow",
                notes,
                fallback_fields,
            )
        latest_equity = first_number(*equity)
        if debt is not None and latest_equity is not None and latest_equity > 0:
            set_if_missing(payload, "debt_to_equity", (debt / latest_equity) * 100, "yfinance balance sheet", notes, fallback_fields)
        eps = first_number(*diluted_eps)
        price = safe_float(payload.get("current_price"))
        if eps is not None and eps > 0 and price is not None:
            set_if_missing(payload, "trailing_pe", price / eps, "yfinance income statement EPS", notes, fallback_fields)
        trailing_pe = safe_float(payload.get("trailing_pe"))
        earnings_growth = safe_float(payload.get("earnings_growth"))
        earnings_growth_percent = earnings_growth * 100 if earnings_growth is not None and abs(earnings_growth) <= 5 else earnings_growth
        if trailing_pe is not None and earnings_growth_percent is not None and earnings_growth_percent > 0:
            set_if_missing(
                payload,
                "peg",
                trailing_pe / earnings_growth_percent,
                "approximation gratuite trailing PE / croissance benefices",
                notes,
                fallback_fields,
            )

    def _fill_from_sec_edgar(self, ticker: str, payload: dict[str, Any], notes: list[str]) -> None:
        if is_canadian_market_candidate(ticker, payload):
            return
        official = self.official_data.fetch_sec_fundamentals(ticker)
        if not official.get("available"):
            return
        official_fields: list[str] = []
        confirmed_fields: list[str] = []
        conflicts: list[str] = []
        policy_notes: list[str] = []
        sec_age_days = _age_days(official.get("sec_edgar_latest_filing_date"))
        sec_is_recent = sec_age_days is None or sec_age_days <= SEC_RECENT_MAX_AGE_DAYS

        for field in SEC_CONFIRM_OR_FILL_FIELDS | SEC_BALANCE_SHEET_PRIORITY_FIELDS:
            value = safe_float(official.get(field))
            if value is None:
                continue
            current = safe_float(payload.get(field))
            decision = _sec_field_decision(field, current, value, sec_is_recent)
            if decision == "use":
                payload[field] = value
                official_fields.append(field)
            elif decision == "confirm":
                confirmed_fields.append(field)
            elif decision == "conflict":
                conflicts.append(_source_conflict_text(field, current, value))

        eps = safe_float(official.get("diluted_eps_ttm_or_annual"))
        price = safe_float(payload.get("current_price"))
        if payload.get("trailing_pe") is None and eps is not None and eps > 0 and price is not None:
            payload["trailing_pe"] = price / eps
            official_fields.append("trailing_pe")
        trailing_pe = safe_float(payload.get("trailing_pe"))
        earnings_growth = safe_float(payload.get("earnings_growth"))
        earnings_growth_percent = earnings_growth * 100 if earnings_growth is not None and abs(earnings_growth) <= 5 else earnings_growth
        if payload.get("peg") is None and trailing_pe is not None and earnings_growth_percent is not None and earnings_growth_percent > 0:
            payload["peg"] = trailing_pe / earnings_growth_percent
            official_fields.append("peg")

        if sec_is_recent:
            policy_notes.append("SEC EDGAR récent: utilisé pour remplir les champs manquants et priorisé pour cash/dette.")
        else:
            policy_notes.append("SEC EDGAR ancien: utilisé seulement si la donnée gratuite principale est absente.")
        if confirmed_fields:
            policy_notes.append("SEC EDGAR confirme certains champs yfinance sans les remplacer.")
        if conflicts:
            policy_notes.append("Conflit source détecté: yfinance conservé pour éviter un écrasement ambigu.")

        if not official_fields and not confirmed_fields and not conflicts:
            return
        payload["official_data_sources"] = sorted(
            set((payload.get("official_data_sources") or []) + [str(official.get("source") or "SEC EDGAR companyfacts")])
        )
        payload["official_fundamental_fields"] = sorted(set((payload.get("official_fundamental_fields") or []) + official_fields))
        payload["official_confirmed_fields"] = sorted(set((payload.get("official_confirmed_fields") or []) + confirmed_fields))
        payload["official_data_conflicts"] = sorted(set((payload.get("official_data_conflicts") or []) + conflicts))
        payload["official_source_policy"] = sorted(set((payload.get("official_source_policy") or []) + policy_notes))
        payload["sec_edgar_cik"] = official.get("sec_edgar_cik")
        payload["sec_edgar_company_name"] = official.get("sec_edgar_company_name")
        payload["sec_edgar_latest_filing_date"] = official.get("sec_edgar_latest_filing_date")
        payload["sec_edgar_latest_fiscal_year"] = official.get("sec_edgar_latest_fiscal_year")
        if official_fields:
            notes.append(f"SEC EDGAR companyfacts utilise: {', '.join(sorted(set(official_fields)))}")
        if confirmed_fields:
            notes.append(f"SEC EDGAR companyfacts confirme: {', '.join(sorted(set(confirmed_fields)))}")
        if conflicts:
            notes.append("SEC EDGAR companyfacts conflit: yfinance conservé pour certains champs")

    def _fill_from_canadian_sources(self, ticker: str, payload: dict[str, Any], notes: list[str]) -> None:
        if not is_canadian_market_candidate(ticker, payload):
            return
        if not _needs_canadian_fundamental_fallback(payload):
            payload["canadian_coverage_status"] = "NOT_NEEDED_YFINANCE_SUFFICIENT"
            return
        canadian = self.canadian_data.fetch_fundamentals(
            ticker,
            company_name=str(payload.get("long_name") or ""),
        )
        payload["canadian_checked_at"] = datetime.now().isoformat(timespec="seconds")
        payload["canadian_source_health"] = canadian.get("source_health") or payload.get("canadian_source_health") or []
        if not canadian.get("available"):
            payload["canadian_coverage_status"] = canadian.get("reason") or "NO_CANADIAN_FALLBACK_AVAILABLE"
            return

        used_fields: list[str] = []
        confirmed_fields: list[str] = []
        conflicts: list[str] = list(canadian.get("source_conflicts") or [])
        policy_notes = [
            "Source canadienne gratuite utilisée comme secours: elle remplit surtout les champs manquants et confirme les ratios comparables.",
            "Les valeurs absolues peuvent être publiées en millions; elles ne remplacent pas une bonne donnée yfinance déjà présente.",
            "Hiérarchie canadienne: SEDAR+ puis TMX puis StockAnalysis; les conflits numériques importants sont signalés plutôt qu'écrasés.",
        ]

        for field in CANADIAN_CONFIRM_OR_FILL_FIELDS:
            value = safe_float(canadian.get(field))
            if value is None:
                continue
            current = safe_float(payload.get(field))
            decision = _canadian_field_decision(field, current, value)
            if decision == "use":
                payload[field] = value
                used_fields.append(field)
            elif decision == "confirm":
                confirmed_fields.append(field)
            elif decision == "conflict":
                conflicts.append(_canadian_source_conflict_text(field, current, value))

        source_names = canadian.get("sources") or [str(canadian.get("source") or "StockAnalysis Canadian financial pages")]
        source_names = sorted({str(source) for source in source_names if str(source or "").strip()})
        payload["canadian_coverage_status"] = str(canadian.get("coverage_status") or "USABLE")
        payload["canadian_latest_period"] = canadian.get("latest_period")
        payload["canadian_data_sources"] = sorted(set((payload.get("canadian_data_sources") or []) + source_names))
        payload["canadian_fundamental_fields"] = sorted(set((payload.get("canadian_fundamental_fields") or []) + used_fields))
        payload["canadian_confirmed_fields"] = sorted(set((payload.get("canadian_confirmed_fields") or []) + confirmed_fields))
        payload["canadian_data_conflicts"] = sorted(set((payload.get("canadian_data_conflicts") or []) + conflicts))
        payload["canadian_source_policy"] = sorted(set((payload.get("canadian_source_policy") or []) + policy_notes))

        if not used_fields and not confirmed_fields and not conflicts:
            payload["canadian_coverage_status"] = "AVAILABLE_NO_FIELD_CHANGE"
            return

        payload["official_data_sources"] = sorted(set((payload.get("official_data_sources") or []) + source_names))
        payload["official_fundamental_fields"] = sorted(set((payload.get("official_fundamental_fields") or []) + used_fields))
        payload["official_confirmed_fields"] = sorted(set((payload.get("official_confirmed_fields") or []) + confirmed_fields))
        payload["official_data_conflicts"] = sorted(set((payload.get("official_data_conflicts") or []) + conflicts))
        payload["official_source_policy"] = sorted(set((payload.get("official_source_policy") or []) + policy_notes))

        if used_fields:
            notes.append(f"source canadienne gratuite utilise: {', '.join(sorted(set(used_fields)))}")
        if confirmed_fields:
            notes.append(f"source canadienne gratuite confirme: {', '.join(sorted(set(confirmed_fields)))}")
        if conflicts:
            notes.append("source canadienne gratuite conflit: yfinance conservé pour certains champs comparables")
        if source_names:
            notes.append("sources canadiennes consultees: " + ", ".join(source_names))

    def _fill_from_fund_price_fallback(self, ticker: str, payload: dict[str, Any]) -> None:
        if payload.get("current_price") is not None:
            return
        if not is_etf_asset(ticker, payload):
            return
        fallback = fetch_fund_price_fallback(ticker, is_fund_hint=True)
        if not fallback:
            return
        notes = list(payload.get("data_source_notes") or [])
        notes.extend(fallback.get("data_source_notes") or [])
        filled_fields: list[str] = []
        for field in MARKET_FIELDS:
            if payload.get(field) is None and fallback.get(field) is not None:
                payload[field] = fallback.get(field)
                filled_fields.append(field)
        if fallback.get("source") and filled_fields and payload.get("current_price") is not None:
            previous_source = payload.get("source")
            payload["source"] = fallback["source"] if previous_source in {"unavailable", "empty", None} else f"{previous_source}+fund_fallback"
        if fallback.get("error") and payload.get("error") is None:
            payload["error"] = fallback.get("error")
        if filled_fields:
            notes.append("fallback ETF/FNB gratuit utilise: " + ", ".join(sorted(set(filled_fields))))
        payload["data_source_notes"] = sorted(set(notes))

    def _augment_fallback_payload_with_canadian_sources(self, ticker: str, payload: dict[str, Any]) -> None:
        if not is_canadian_market_candidate(ticker, payload):
            return
        notes = list(payload.get("data_source_notes") or [])
        self._fill_from_canadian_sources(ticker, payload, notes)
        payload["data_source_notes"] = sorted(set(notes))
        for field in [
            "official_data_sources",
            "official_fundamental_fields",
            "official_confirmed_fields",
            "official_data_conflicts",
            "official_source_policy",
            "canadian_data_sources",
            "canadian_fundamental_fields",
            "canadian_confirmed_fields",
            "canadian_data_conflicts",
            "canadian_source_policy",
        ]:
            payload[field] = sorted(set(payload.get(field) or []))
        if payload.get("official_fundamental_fields") or payload.get("official_confirmed_fields"):
            source = str(payload.get("source") or "")
            if "canadian" not in source:
                payload["source"] = f"{source}+canadian" if source else "canadian_fallback"
        payload["data_fill_rate"] = data_fill_rate(payload)

    def _empty_payload(self, ticker: str) -> dict[str, Any]:
        payload = {
            "ticker": ticker,
            "source": "empty",
            "fetched_at": None,
            "error": None,
            "cache_schema_version": CACHE_SCHEMA_VERSION,
        }
        payload.update({field: None for field in MARKET_FIELDS})
        return payload

    def _price_from_offset(self, closes: list[float], offset: int) -> float | None:
        if len(closes) <= offset:
            return None
        return closes[-offset]

    def _return_from_offset(self, closes: list[float], offset: int) -> float | None:
        old_price = self._price_from_offset(closes, offset)
        if old_price is None or old_price <= 0:
            return None
        return closes[-1] / old_price - 1

    def _cagr_from_offset(self, closes: list[float], offset: int, years: int) -> float | None:
        old_price = self._price_from_offset(closes, offset)
        if old_price is None or old_price <= 0:
            return None
        return (closes[-1] / old_price) ** (1 / years) - 1


def benchmark_metrics_for(
    ticker: str,
    benchmark_map: dict[str, str],
    benchmark_data: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    benchmark = benchmark_map.get(ticker) or "VFV.TO"
    payload = benchmark_data.get(benchmark or "", {})
    usable_cagr, usable_period, usable_field = _best_available_benchmark_cagr(payload)
    return {
        "benchmark_ticker": benchmark,
        "benchmark_10y_cagr": first_number(payload.get("adjusted_cagr_10y"), payload.get("cagr_10y")),
        "benchmark_5y_cagr": first_number(payload.get("adjusted_cagr_5y"), payload.get("cagr_5y")),
        "benchmark_3y_cagr": first_number(payload.get("adjusted_stock_cagr_3y"), payload.get("stock_cagr_3y")),
        "benchmark_1y_return": first_number(payload.get("adjusted_stock_return_1y"), payload.get("stock_return_1y")),
        "benchmark_usable_cagr": usable_cagr,
        "benchmark_usable_period": usable_period,
        "benchmark_usable_field": usable_field,
        "benchmark_sma_200": payload.get("sma_200"),
        "benchmark_above_sma_200": payload.get("price_above_sma_200"),
        "benchmark_return_1y": first_number(payload.get("adjusted_stock_return_1y"), payload.get("stock_return_1y")),
        "benchmark_return_basis": payload.get("total_return_basis") or "PRICE_CLOSE",
    }


def _best_available_benchmark_cagr(payload: dict[str, Any]) -> tuple[float | None, str, str]:
    for field, period in [
        ("adjusted_cagr_10y", "10 ans rendement total approx."),
        ("cagr_10y", "10 ans"),
        ("adjusted_cagr_5y", "5 ans rendement total approx."),
        ("cagr_5y", "5 ans"),
        ("adjusted_stock_cagr_3y", "3 ans rendement total approx."),
        ("stock_cagr_3y", "3 ans"),
        ("adjusted_stock_return_1y", "1 an rendement total approx."),
        ("stock_return_1y", "1 an"),
    ]:
        value = safe_float(payload.get(field))
        if value is not None:
            return value, period, field
    return None, "Donnée pas dispo", ""


def _series_values(frame: Any, column: str) -> list[float]:
    try:
        values = frame.get(column, [])
    except Exception:
        values = []
    return [value for value in (safe_float(item) for item in values) if value is not None]


def _series_history(frame: Any, column: str) -> dict[str, float]:
    try:
        series = frame.get(column, [])
    except Exception:
        return {}
    output: dict[str, float] = {}
    try:
        items = series.items()
    except Exception:
        return output
    for index, value in items:
        number = safe_float(value)
        if number is None or number <= 0:
            continue
        try:
            date_key = index.date().isoformat()
        except Exception:
            date_key = str(index)[:10]
        if date_key:
            output[date_key] = number
    return output


def _safe_fast_info(instrument: Any) -> dict[str, Any]:
    try:
        fast_info = instrument.fast_info
    except Exception:
        return {}
    if isinstance(fast_info, dict):
        return dict(fast_info)
    payload: dict[str, Any] = {}
    for key in [
        "lastPrice",
        "last_price",
        "regularMarketPrice",
        "marketCap",
        "market_cap",
        "currency",
        "yearHigh",
        "year_high",
        "shares",
        "sharesOutstanding",
        "shares_outstanding",
    ]:
        try:
            payload[key] = fast_info[key]  # type: ignore[index]
        except Exception:
            try:
                payload[key] = getattr(fast_info, key)
            except Exception:
                continue
    return payload


def _safe_news_context_items(instrument: Any) -> list[dict[str, str]]:
    try:
        news_items = instrument.news or []
    except Exception:
        return []
    output: list[dict[str, str]] = []
    for item in news_items[:12]:
        title = _news_title(item)
        if not title:
            continue
        output.append(
            {
                "title": title,
                "publisher": _news_publisher(item),
                "url": _news_url(item),
                "published_at": _news_published_at(item),
            }
        )
    return output


def _should_fetch_public_news_context(payload: dict[str, Any]) -> bool:
    existing_headlines = payload.get("news_context_headlines") or []
    if len(existing_headlines) >= 3:
        return False
    drawdown_12m = safe_float(payload.get("drawdown_from_12m_high"))
    drawdown_8m = safe_float(payload.get("drawdown_from_8m_high"))
    stock_return_1y = safe_float(payload.get("stock_return_1y"))
    return any(
        [
            drawdown_12m is not None and drawdown_12m <= -0.12,
            drawdown_8m is not None and drawdown_8m <= -0.10,
            payload.get("price_above_sma_200") is False,
            stock_return_1y is not None and stock_return_1y <= -0.08,
        ]
    )


def _fetch_google_news_rss_context(ticker: str, company_name: str = "") -> dict[str, Any]:
    queries = _news_search_queries(ticker, company_name)
    items: list[dict[str, str]] = []
    try:
        import requests  # type: ignore
    except Exception:
        return {"items": items, "queries": queries}

    for query in queries:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote_plus(query)}&hl=en-CA&gl=CA&ceid=CA:en"
        )
        try:
            response = requests.get(
                url,
                timeout=PUBLIC_NEWS_CONTEXT_TIMEOUT_SECONDS,
                headers={"User-Agent": "investment-automation-local/1.0"},
            )
            if response.status_code >= 400:
                continue
            items.extend(_parse_google_news_rss(response.text))
        except Exception:
            continue
        if len(items) >= PUBLIC_NEWS_CONTEXT_MAX_ITEMS:
            break
    return {"items": _dedupe_news_items(items)[:PUBLIC_NEWS_CONTEXT_MAX_ITEMS], "queries": queries}


def _news_search_queries(ticker: str, company_name: str = "") -> list[str]:
    base_ticker = str(ticker or "").split(".")[0].replace("-", " ").strip()
    company = str(company_name or "").strip()
    queries = []
    if company:
        queries.append(f'"{company}" stock earnings guidance margins')
    if base_ticker:
        queries.append(f'"{base_ticker}" stock earnings guidance margins')
    return queries or [f'"{ticker}" stock']


def _parse_google_news_rss(raw_xml: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(raw_xml)
    except Exception:
        return []
    items: list[dict[str, str]] = []
    for item in root.findall(".//item")[:PUBLIC_NEWS_CONTEXT_MAX_ITEMS]:
        title = html.unescape(_child_text(item, "title"))
        if not title:
            continue
        source_node = item.find("source")
        publisher = html.unescape((source_node.text or "").strip()) if source_node is not None else _publisher_from_title(title)
        items.append(
            {
                "title": title,
                "publisher": publisher,
                "url": _child_text(item, "link"),
                "published_at": _child_text(item, "pubDate"),
            }
        )
    return items


def _merge_news_context_items(payload: dict[str, Any], items: list[dict[str, str]], channel: str) -> None:
    merged = _dedupe_news_items(_existing_news_items(payload) + items)
    trimmed = merged[:8]
    payload["news_context_headlines"] = [item["title"] for item in trimmed if item.get("title")]
    payload["news_context_sources"] = sorted({item["publisher"] for item in trimmed if item.get("publisher")})
    payload["news_context_urls"] = [item["url"] for item in trimmed if item.get("url")]
    payload["news_context_published_at"] = [item["published_at"] for item in trimmed if item.get("published_at")]
    payload["news_context_checked_at"] = datetime.now().isoformat(timespec="seconds")
    payload["news_context_source_channels"] = sorted(set((payload.get("news_context_source_channels") or []) + [channel]))


def _existing_news_items(payload: dict[str, Any]) -> list[dict[str, str]]:
    headlines = [str(item) for item in payload.get("news_context_headlines") or []]
    sources = [str(item) for item in payload.get("news_context_sources") or []]
    urls = [str(item) for item in payload.get("news_context_urls") or []]
    dates = [str(item) for item in payload.get("news_context_published_at") or []]
    output = []
    for index, title in enumerate(headlines):
        output.append(
            {
                "title": title,
                "publisher": sources[index] if index < len(sources) else "",
                "url": urls[index] if index < len(urls) else "",
                "published_at": dates[index] if index < len(dates) else "",
            }
        )
    return output


def _dedupe_news_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for item in items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "title": title,
                "publisher": str(item.get("publisher") or "").strip(),
                "url": str(item.get("url") or "").strip(),
                "published_at": str(item.get("published_at") or "").strip(),
            }
        )
    return output


def _child_text(node: Any, tag: str) -> str:
    child = node.find(tag)
    return str(child.text or "").strip() if child is not None else ""


def _publisher_from_title(title: str) -> str:
    if " - " not in title:
        return ""
    return title.rsplit(" - ", 1)[-1].strip()


def _safe_news_red_flags(instrument: Any) -> list[str]:
    return _news_red_flags_from_titles([item.get("title", "") for item in _safe_news_context_items(instrument)])


def _news_red_flags_from_titles(titles: list[str]) -> list[str]:
    flags = []
    for title in titles[:12]:
        lowered = str(title).lower()
        if any(keyword in lowered for keyword in NEWS_RED_FLAG_KEYWORDS):
            flags.append(str(title))
    return flags


NEWS_RED_FLAG_KEYWORDS = {
    "bankruptcy",
    "bankrupt",
    "chapter 11",
    "creditor protection",
    "insolvency",
    "insolvent",
    "restructuring",
    "delisting",
    "trading halt",
    "liquidation",
    "going concern",
    "default",
    "fraud investigation",
    "sec charges",
    "accounting scandal",
    "faillite",
}


def _news_title(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    title = item.get("title") or content.get("title") or ""
    return str(title).strip()


def _news_publisher(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
    publisher = (
        item.get("publisher")
        or item.get("provider")
        or provider.get("displayName")
        or provider.get("name")
        or content.get("publisher")
        or ""
    )
    return str(publisher).strip()


def _news_url(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    canonical = content.get("canonicalUrl") if isinstance(content.get("canonicalUrl"), dict) else {}
    clickthrough = content.get("clickThroughUrl") if isinstance(content.get("clickThroughUrl"), dict) else {}
    url = (
        item.get("link")
        or item.get("url")
        or canonical.get("url")
        or clickthrough.get("url")
        or content.get("url")
        or ""
    )
    return str(url).strip()


def _news_published_at(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    raw = item.get("providerPublishTime") or item.get("publishTime") or content.get("pubDate") or content.get("displayTime")
    if raw is None:
        return ""
    number = safe_float(raw)
    if number is not None and number > 100000:
        try:
            return datetime.fromtimestamp(number).isoformat(timespec="seconds")
        except Exception:
            return str(raw)
    return str(raw).strip()


def _lookup(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in mapping:
            continue
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


def first_number(*values: Any) -> float | None:
    for value in values:
        number = safe_float(value)
        if number is not None:
            return number
    return None


def _safe_non_negative_int(value: Any) -> int:
    number = safe_float(value)
    if number is None or number < 0:
        return 0
    return int(number)


def set_if_missing(
    payload: dict[str, Any],
    field: str,
    value: Any,
    source: str,
    notes: list[str],
    fallback_fields: list[str],
) -> None:
    if payload.get(field) is not None:
        return
    number = safe_float(value)
    if number is None and not isinstance(value, str):
        return
    payload[field] = number if number is not None else value
    fallback_fields.append(field)
    notes.append(f"{field}: {source}")


def _get_statement(instrument: Any, attributes: list[str]) -> Any | None:
    for attribute in attributes:
        try:
            statement = getattr(instrument, attribute)
        except Exception:
            continue
        if statement is not None and not getattr(statement, "empty", True):
            return statement
    return None


def _statement_values(statement: Any | None, labels: list[str]) -> list[float]:
    if statement is None:
        return []
    try:
        index_values = list(statement.index)
    except Exception:
        return []
    normalized = {_normalize_label(label): label for label in index_values}
    selected_label = None
    for label in labels:
        if label in index_values:
            selected_label = label
            break
        selected_label = normalized.get(_normalize_label(label))
        if selected_label is not None:
            break
    if selected_label is None:
        return []
    try:
        row = statement.loc[selected_label]
    except Exception:
        return []
    try:
        raw_values = list(row.values)
    except Exception:
        raw_values = [row]
    values = [safe_float(value) for value in raw_values]
    return [value for value in values if value is not None]


def _capex_outflow(value: Any) -> float:
    number = safe_float(value)
    if number is None:
        return 0.0
    return abs(number)


def _free_cash_flow_values(
    operating_cash_flow: list[float],
    capex_outflow: list[float],
    free_cash_flow_statement: list[float],
) -> list[float]:
    if free_cash_flow_statement:
        return free_cash_flow_statement
    length = min(len(operating_cash_flow), len(capex_outflow))
    if length <= 0:
        return []
    return [operating_cash_flow[index] - capex_outflow[index] for index in range(length)]


def _cash_outflow(value: Any) -> float:
    number = safe_float(value)
    if number is None:
        return 0.0
    return abs(number)


def _per_share_values(numerator: list[float], shares: list[float]) -> list[float]:
    length = min(len(numerator), len(shares))
    values = []
    for index in range(length):
        share_count = safe_float(shares[index])
        value = safe_float(numerator[index])
        if share_count is None or share_count <= 0 or value is None:
            continue
        values.append(value / share_count)
    return values


def ratio_latest(numerator: list[float], denominator: list[float]) -> float | None:
    top = first_number(*(numerator[:1]))
    bottom = first_number(*(denominator[:1]))
    if top is None or bottom is None or bottom == 0:
        return None
    return top / bottom


def growth_latest(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    latest = safe_float(values[0])
    previous = safe_float(values[1])
    if latest is None or previous is None or previous == 0:
        return None
    return latest / abs(previous) - 1


def cagr_from_series(values: list[float], years: int) -> float | None:
    if len(values) <= years:
        return None
    latest = safe_float(values[0])
    old = safe_float(values[years])
    if latest is None or old is None or latest <= 0 or old <= 0:
        return None
    return (latest / old) ** (1 / years) - 1


def return_ratio(returns: list[float], base_values: list[float]) -> float | None:
    latest_return = first_number(*(returns[:1]))
    if latest_return is None:
        return None
    latest_base = first_number(*(base_values[:1]))
    previous_base = first_number(*(base_values[1:2]))
    if latest_base is None or latest_base == 0:
        return None
    denominator = (latest_base + previous_base) / 2 if previous_base is not None and previous_base > 0 else latest_base
    if denominator == 0:
        return None
    return latest_return / denominator


def data_fill_rate(payload: dict[str, Any]) -> float:
    important = [
        "current_price",
        "sma_200",
        "stock_return_1y",
        "market_cap",
        "profit_margins",
        "operating_margins",
        "return_on_equity",
        "revenue_growth",
        "earnings_growth",
        "free_cash_flow",
        "free_cash_flow_margin",
        "fcf_conversion",
        "diluted_average_shares",
        "share_count_growth_1y",
        "share_count_cagr_3y",
        "total_debt",
        "total_cash",
    ]
    filled = sum(1 for field in important if payload.get(field) is not None)
    return round(filled / len(important), 4)


def _sec_field_decision(field: str, current: float | None, official: float, sec_is_recent: bool) -> str:
    if current is None:
        return "use"
    if not sec_is_recent:
        return "confirm" if _relative_difference(current, official) <= SEC_CONFLICT_RELATIVE_THRESHOLD else "conflict"
    if field in SEC_BALANCE_SHEET_PRIORITY_FIELDS:
        return "use"
    difference = _relative_difference(current, official)
    if difference <= SEC_CONFLICT_RELATIVE_THRESHOLD:
        return "confirm"
    return "conflict"


def _source_conflict_text(field: str, yfinance_value: float | None, official_value: float) -> str:
    if yfinance_value is None:
        return f"{field}: SEC={official_value:.4g}, yfinance=N/D"
    difference = _relative_difference(yfinance_value, official_value)
    return f"{field}: yfinance={yfinance_value:.4g}, SEC={official_value:.4g}, ecart={difference:.0%}"


def _canadian_field_decision(field: str, current: float | None, canadian_value: float) -> str:
    if current is None:
        return "use"
    if field in CANADIAN_ABSOLUTE_FIELDS:
        return "skip"
    difference = _relative_difference(current, canadian_value)
    if difference <= CANADIAN_CONFLICT_RELATIVE_THRESHOLD:
        return "confirm"
    return "conflict"


def _canadian_source_conflict_text(field: str, yfinance_value: float | None, canadian_value: float) -> str:
    if yfinance_value is None:
        return f"{field}: source_canadienne={canadian_value:.4g}, yfinance=N/D"
    difference = _relative_difference(yfinance_value, canadian_value)
    return f"{field}: yfinance={yfinance_value:.4g}, source_canadienne={canadian_value:.4g}, ecart={difference:.0%}"


def _needs_canadian_fundamental_fallback(payload: dict[str, Any]) -> bool:
    important = [
        "profit_margins",
        "operating_margins",
        "revenue_growth",
        "earnings_growth",
        "return_on_equity",
        "return_on_assets",
        "free_cash_flow_margin",
        "fcf_conversion",
        "total_debt",
        "total_cash",
    ]
    missing = [field for field in important if payload.get(field) is None]
    if len(missing) >= 3:
        return True
    if data_fill_rate(payload) < 0.92 and missing:
        return True
    source = str(payload.get("source") or "").lower()
    if source in {"empty", "unavailable"} and missing:
        return True
    return False


def _relative_difference(left: float | None, right: float | None) -> float:
    if left is None or right is None:
        return 1.0
    denominator = max(abs(left), abs(right), 1e-9)
    return abs(left - right) / denominator


def _age_days(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text[:10])
    except ValueError:
        return None
    return max(0, (datetime.now() - parsed).days)


def _normalize_label(label: Any) -> str:
    return "".join(ch for ch in str(label).lower() if ch.isalnum())
