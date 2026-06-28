from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from .canadian_data_fetcher import CanadianDataFetcher, canadian_ticker_metadata
from .utils import CACHE_DIR, load_json, safe_float, save_json


BANK_OF_CANADA_FX_SERIES = {
    "USD": "FXUSDCAD",
    "EUR": "FXEURCAD",
    "GBP": "FXGBPCAD",
    "CHF": "FXCHFCAD",
    "JPY": "FXJPYCAD",
}

SEC_USER_AGENT = "investment_automation/1.0 contact: local-user@example.com"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

SEC_REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
SEC_NET_INCOME_TAGS = ["NetIncomeLoss"]
SEC_GROSS_PROFIT_TAGS = ["GrossProfit"]
SEC_OPERATING_INCOME_TAGS = ["OperatingIncomeLoss"]
SEC_OPERATING_CASH_FLOW_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
SEC_CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
]
SEC_DILUTED_SHARES_TAGS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
]
SEC_BASIC_SHARES_TAGS = ["WeightedAverageNumberOfSharesOutstandingBasic"]
SEC_SHARE_REPURCHASE_TAGS = [
    "PaymentsForRepurchaseOfCommonStock",
    "PaymentsForRepurchaseOfEquity",
    "PaymentsForRepurchaseOfCommonStocks",
]
SEC_STOCK_BASED_COMPENSATION_TAGS = [
    "ShareBasedCompensation",
    "ShareBasedCompensationArrangementByShareBasedPaymentAwardOptionsGrantsInPeriodGross",
]
SEC_ASSETS_TAGS = ["Assets"]
SEC_EQUITY_TAGS = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]
SEC_CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
SEC_TOTAL_DEBT_TAGS = [
    "LongTermDebtAndFinanceLeaseObligations",
    "DebtAndFinanceLeaseObligations",
    "LongTermDebt",
]
SEC_CURRENT_DEBT_TAGS = [
    "ShortTermBorrowings",
    "ShortTermDebt",
    "LongTermDebtCurrent",
    "LongTermDebtAndFinanceLeaseObligationsCurrent",
]
SEC_NONCURRENT_DEBT_TAGS = [
    "LongTermDebtNoncurrent",
    "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
]
SEC_DILUTED_EPS_TAGS = ["EarningsPerShareDiluted"]


class OfficialDataFetcher:
    """Small wrapper for free official sources used as a reliability layer."""

    def __init__(self, cache_dir: str | Path = CACHE_DIR, timeout_seconds: int = 8) -> None:
        self.cache_dir = Path(cache_dir) / "official_sources"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = timeout_seconds
        self._sec_ticker_map_memory: dict[str, dict[str, Any]] | None = None
        self._sec_ticker_map_attempted = False

    def fetch_bank_of_canada_fx_rate(self, currency: str, refresh: bool = False) -> dict[str, Any] | None:
        currency = str(currency or "").strip().upper()
        series = BANK_OF_CANADA_FX_SERIES.get(currency)
        if not series:
            return None
        cache_path = self.cache_dir / f"bank_of_canada_{series}.json"
        cached = _fresh_cached_json(cache_path, max_age=timedelta(hours=24), refresh=refresh)
        if cached:
            rate = parse_bank_of_canada_fx_payload(series, cached.get("raw_payload") or cached)
            if rate is not None:
                return {
                    "currency": currency,
                    "rate": rate,
                    "series": series,
                    "source": "Bank of Canada Valet API",
                    "fetched_at": cached.get("fetched_at"),
                }

        url = f"https://www.bankofcanada.ca/valet/observations/{series}/json?recent=5"
        try:
            raw_payload = self._get_json(url)
        except Exception:
            stale = load_json(cache_path)
            if stale:
                rate = parse_bank_of_canada_fx_payload(series, stale.get("raw_payload") or stale)
                if rate is not None:
                    return {
                        "currency": currency,
                        "rate": rate,
                        "series": series,
                        "source": "Bank of Canada Valet API (cache)",
                        "fetched_at": stale.get("fetched_at"),
                    }
            return None
        record = {
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "raw_payload": raw_payload,
        }
        save_json(cache_path, record)
        rate = parse_bank_of_canada_fx_payload(series, raw_payload)
        if rate is None:
            return None
        return {
            "currency": currency,
            "rate": rate,
            "series": series,
            "source": "Bank of Canada Valet API",
            "fetched_at": record["fetched_at"],
        }

    def fetch_sec_fundamentals(self, ticker: str, refresh: bool = False) -> dict[str, Any]:
        if canadian_ticker_metadata(ticker):
            return CanadianDataFetcher(
                self.cache_dir.parent,
                timeout_seconds=10,
            ).fetch_fundamentals(ticker, refresh=refresh)
        if not is_sec_supported_ticker(ticker):
            return {"available": False, "reason": "Ticker non couvert par SEC EDGAR companyfacts."}
        normalized = normalize_sec_ticker(ticker)
        ticker_map = self._fetch_sec_ticker_map(refresh=refresh)
        company = ticker_map.get(normalized)
        if not company:
            return {"available": False, "reason": "Ticker absent de la table SEC company_tickers."}
        cik = int(company["cik"])
        cache_path = self.cache_dir / f"sec_companyfacts_{cik:010d}.json"
        companyfacts = _fresh_cached_json(cache_path, max_age=timedelta(hours=24), refresh=refresh)
        if not companyfacts:
            try:
                companyfacts = self._get_json(SEC_COMPANY_FACTS_URL.format(cik=cik))
                save_json(
                    cache_path,
                    {
                        "fetched_at": datetime.now().isoformat(timespec="seconds"),
                        "raw_payload": companyfacts,
                    },
                )
            except Exception:
                cached = load_json(cache_path)
                companyfacts = cached.get("raw_payload") if isinstance(cached, dict) else None
        elif "raw_payload" in companyfacts:
            companyfacts = companyfacts.get("raw_payload")
        if not isinstance(companyfacts, dict):
            return {"available": False, "reason": "Données SEC EDGAR indisponibles."}
        parsed = parse_sec_companyfacts(companyfacts)
        if not parsed.get("fields"):
            return {"available": False, "reason": "Données SEC EDGAR présentes mais non exploitables."}
        parsed.update(
            {
                "available": True,
                "source": "SEC EDGAR companyfacts",
                "sec_edgar_cik": cik,
                "sec_edgar_company_name": company.get("company_name") or companyfacts.get("entityName"),
            }
        )
        return parsed

    def _fetch_sec_ticker_map(self, refresh: bool = False) -> dict[str, dict[str, Any]]:
        if self._sec_ticker_map_memory is not None and not refresh:
            return self._sec_ticker_map_memory
        if self._sec_ticker_map_attempted and not refresh:
            return {}
        self._sec_ticker_map_attempted = True
        cache_path = self.cache_dir / "sec_company_tickers.json"
        cached = _fresh_cached_json(cache_path, max_age=timedelta(days=7), refresh=refresh)
        raw_map = cached.get("raw_payload") if isinstance(cached, dict) and "raw_payload" in cached else cached
        if not raw_map:
            try:
                raw_map = self._get_json(SEC_COMPANY_TICKERS_URL)
                save_json(
                    cache_path,
                    {
                        "fetched_at": datetime.now().isoformat(timespec="seconds"),
                        "raw_payload": raw_map,
                    },
                )
            except Exception:
                stale = load_json(cache_path)
                raw_map = stale.get("raw_payload") if isinstance(stale, dict) else None
        parsed = parse_sec_ticker_map(raw_map)
        if parsed:
            self._sec_ticker_map_memory = parsed
        return parsed

    def _get_json(self, url: str) -> dict[str, Any]:
        response = requests.get(
            url,
            headers={"User-Agent": SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


def parse_bank_of_canada_fx_payload(series: str, payload: dict[str, Any]) -> float | None:
    observations = payload.get("observations") if isinstance(payload, dict) else None
    if not isinstance(observations, list):
        return None
    for observation in reversed(observations):
        if not isinstance(observation, dict):
            continue
        value_payload = observation.get(series)
        if not isinstance(value_payload, dict):
            continue
        rate = safe_float(value_payload.get("v"))
        if rate is not None and rate > 0:
            return rate
    return None


def parse_sec_ticker_map(raw_map: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_map, dict):
        return {}
    parsed: dict[str, dict[str, Any]] = {}
    for row in raw_map.values():
        if not isinstance(row, dict):
            continue
        ticker = normalize_sec_ticker(row.get("ticker"))
        cik = safe_float(row.get("cik_str"))
        if not ticker or cik is None:
            continue
        parsed[ticker] = {
            "cik": int(cik),
            "company_name": row.get("title"),
        }
    return parsed


def parse_sec_companyfacts(companyfacts: dict[str, Any]) -> dict[str, Any]:
    facts = companyfacts.get("facts", {}).get("us-gaap", {}) if isinstance(companyfacts, dict) else {}
    if not isinstance(facts, dict):
        return {"fields": []}

    revenue = _annual_series(facts, SEC_REVENUE_TAGS)
    net_income = _annual_series(facts, SEC_NET_INCOME_TAGS)
    gross_profit = _annual_series(facts, SEC_GROSS_PROFIT_TAGS)
    operating_income = _annual_series(facts, SEC_OPERATING_INCOME_TAGS)
    operating_cash_flow = _annual_series(facts, SEC_OPERATING_CASH_FLOW_TAGS)
    capex = _annual_series(facts, SEC_CAPEX_TAGS)
    free_cash_flow = _free_cash_flow_series(operating_cash_flow, capex)
    diluted_shares = _annual_series(facts, SEC_DILUTED_SHARES_TAGS)
    basic_shares = _annual_series(facts, SEC_BASIC_SHARES_TAGS)
    share_count_series = diluted_shares or basic_shares
    share_repurchases = _annual_series(facts, SEC_SHARE_REPURCHASE_TAGS)
    stock_based_compensation = _annual_series(facts, SEC_STOCK_BASED_COMPENSATION_TAGS)
    fcf_per_share_series = _per_share_series(free_cash_flow, share_count_series)
    diluted_eps = _annual_series(facts, SEC_DILUTED_EPS_TAGS)

    assets = _latest_instant_value(facts, SEC_ASSETS_TAGS)
    equity = _latest_instant_value(facts, SEC_EQUITY_TAGS)
    cash = _latest_instant_value(facts, SEC_CASH_TAGS)
    debt = _latest_instant_value(facts, SEC_TOTAL_DEBT_TAGS)
    if debt is None:
        current_debt = _latest_instant_value(facts, SEC_CURRENT_DEBT_TAGS) or 0.0
        noncurrent_debt = _latest_instant_value(facts, SEC_NONCURRENT_DEBT_TAGS) or 0.0
        debt = current_debt + noncurrent_debt if current_debt or noncurrent_debt else None

    latest_revenue = _latest_value(revenue)
    previous_revenue = _previous_value(revenue)
    latest_net_income = _latest_value(net_income)
    previous_net_income = _previous_value(net_income)
    latest_gross_profit = _latest_value(gross_profit)
    latest_operating_income = _latest_value(operating_income)
    latest_operating_cash_flow = _latest_value(operating_cash_flow)
    latest_capex = _capex_outflow(_latest_value(capex))
    latest_free_cash_flow = _latest_value(free_cash_flow)
    previous_free_cash_flow = _previous_value(free_cash_flow)
    latest_shares = _latest_value(share_count_series)
    latest_share_repurchases = _cash_outflow(_latest_value(share_repurchases))
    latest_stock_based_compensation = _latest_value(stock_based_compensation)
    latest_eps = _latest_value(diluted_eps)

    result: dict[str, Any] = {"fields": []}
    _set_ratio(result, "profit_margins", latest_net_income, latest_revenue)
    _set_ratio(result, "gross_margins", latest_gross_profit, latest_revenue)
    _set_ratio(result, "operating_margins", latest_operating_income, latest_revenue)
    _set_number(result, "total_revenue", latest_revenue)
    _set_number(result, "net_income", latest_net_income)
    _set_growth(result, "revenue_growth", latest_revenue, previous_revenue)
    _set_growth(result, "earnings_growth", latest_net_income, previous_net_income)
    _set_ratio(result, "return_on_equity", latest_net_income, equity)
    _set_ratio(result, "return_on_assets", latest_net_income, assets)
    _set_number(result, "total_cash", cash)
    _set_number(result, "total_debt", debt)
    _set_number(result, "operating_cash_flow", latest_operating_cash_flow)
    _set_number(result, "capital_expenditures", latest_capex)
    _set_number(result, "free_cash_flow", latest_free_cash_flow)
    _set_ratio(result, "free_cash_flow_margin", latest_free_cash_flow, latest_revenue)
    _set_ratio(result, "fcf_conversion", latest_free_cash_flow, latest_net_income)
    _set_growth(result, "free_cash_flow_growth", latest_free_cash_flow, previous_free_cash_flow)
    _set_number(result, "diluted_average_shares", latest_shares)
    _set_growth(result, "share_count_growth_1y", latest_shares, _previous_value(share_count_series))
    _set_number(result, "share_count_cagr_3y", _series_cagr(share_count_series, 3))
    _set_number(result, "share_count_cagr_5y", _series_cagr(share_count_series, 5))
    _set_number(result, "share_repurchases", latest_share_repurchases)
    _set_number(result, "stock_based_compensation", latest_stock_based_compensation)
    _set_ratio(result, "sbc_to_revenue", latest_stock_based_compensation, latest_revenue)
    _set_number(result, "fcf_per_share", _latest_value(fcf_per_share_series))
    _set_growth(result, "fcf_per_share_growth", _latest_value(fcf_per_share_series), _previous_value(fcf_per_share_series))
    if debt is not None and equity is not None and equity > 0:
        _set_number(result, "debt_to_equity", (debt / equity) * 100)
    if debt is not None and cash is not None and latest_free_cash_flow is not None and latest_free_cash_flow > 0:
        _set_number(result, "net_debt_to_fcf", (debt - cash) / latest_free_cash_flow)
    _set_number(result, "diluted_eps_ttm_or_annual", latest_eps)

    metadata = _latest_metadata(
        revenue
        + net_income
        + gross_profit
        + operating_income
        + operating_cash_flow
        + capex
        + share_count_series
        + share_repurchases
        + stock_based_compensation
        + diluted_eps
    )
    if metadata:
        result["sec_edgar_latest_filing_date"] = metadata.get("filed")
        result["sec_edgar_latest_fiscal_year"] = metadata.get("fy")
    result["fields"] = sorted(result["fields"])
    return result


def normalize_sec_ticker(ticker: Any) -> str:
    return str(ticker or "").strip().upper().replace(".", "-")


def is_sec_supported_ticker(ticker: str) -> bool:
    raw = str(ticker or "").strip().upper()
    if not raw or raw.endswith("=X") or "." in raw:
        return False
    ticker = normalize_sec_ticker(raw)
    if "." in str(ticker):
        return False
    return bool(re.fullmatch(r"[A-Z0-9][A-Z0-9-]{0,9}", ticker))


def _fresh_cached_json(path: Path, max_age: timedelta, refresh: bool) -> dict[str, Any] | None:
    if refresh or not path.exists():
        return None
    payload = load_json(path)
    if not payload:
        return None
    fetched_at = _parse_datetime(payload.get("fetched_at")) if isinstance(payload, dict) else None
    if fetched_at is None:
        return payload if isinstance(payload, dict) else None
    if datetime.now() - fetched_at <= max_age:
        return payload
    return None


def _annual_series(facts: dict[str, Any], tags: list[str]) -> list[dict[str, Any]]:
    by_year: dict[str, dict[str, Any]] = {}
    for tag in tags:
        for entry in _fact_entries(facts, tag):
            if str(entry.get("form") or "").upper() not in {"10-K", "10-K/A"}:
                continue
            if str(entry.get("fp") or "").upper() not in {"FY", ""}:
                continue
            fiscal_year = _fiscal_year_key(entry)
            if not fiscal_year:
                continue
            current = by_year.get(fiscal_year)
            if current is None or _entry_sort_key(entry) > _entry_sort_key(current):
                by_year[fiscal_year] = entry
    return sorted(by_year.values(), key=_entry_sort_key)


def _latest_instant_value(facts: dict[str, Any], tags: list[str]) -> float | None:
    entries: list[dict[str, Any]] = []
    for tag in tags:
        entries.extend(_fact_entries(facts, tag))
    entries = [entry for entry in entries if entry.get("end")]
    entries.sort(key=_entry_sort_key)
    return safe_float(entries[-1].get("val")) if entries else None


def _fact_entries(facts: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    fact = facts.get(tag)
    if not isinstance(fact, dict):
        return []
    units = fact.get("units")
    if not isinstance(units, dict):
        return []
    rows: list[dict[str, Any]] = []
    for unit_rows in units.values():
        if not isinstance(unit_rows, list):
            continue
        for row in unit_rows:
            if not isinstance(row, dict):
                continue
            value = safe_float(row.get("val"))
            if value is None:
                continue
            parsed = dict(row)
            parsed["val"] = value
            parsed["tag"] = tag
            rows.append(parsed)
    return rows


def _latest_value(series: list[dict[str, Any]]) -> float | None:
    return safe_float(series[-1].get("val")) if series else None


def _previous_value(series: list[dict[str, Any]]) -> float | None:
    return safe_float(series[-2].get("val")) if len(series) >= 2 else None


def _capex_outflow(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    return abs(number)


def _cash_outflow(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    return abs(number)


def _free_cash_flow_series(
    operating_cash_flow: list[dict[str, Any]],
    capex: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    capex_by_year = {_fiscal_year_key(row): row for row in capex if _fiscal_year_key(row)}
    rows: list[dict[str, Any]] = []
    for row in operating_cash_flow:
        fiscal_year = _fiscal_year_key(row)
        if not fiscal_year or fiscal_year not in capex_by_year:
            continue
        ocf = safe_float(row.get("val"))
        capex_outflow = _capex_outflow(capex_by_year[fiscal_year].get("val"))
        if ocf is None or capex_outflow is None:
            continue
        fcf_row = dict(row)
        fcf_row["val"] = ocf - capex_outflow
        fcf_row["tag"] = "FreeCashFlowDerived"
        rows.append(fcf_row)
    return sorted(rows, key=_entry_sort_key)


def _per_share_series(
    numerator: list[dict[str, Any]],
    shares: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    shares_by_year = {_fiscal_year_key(row): row for row in shares if _fiscal_year_key(row)}
    rows: list[dict[str, Any]] = []
    for row in numerator:
        fiscal_year = _fiscal_year_key(row)
        if not fiscal_year or fiscal_year not in shares_by_year:
            continue
        numerator_value = safe_float(row.get("val"))
        share_count = safe_float(shares_by_year[fiscal_year].get("val"))
        if numerator_value is None or share_count is None or share_count <= 0:
            continue
        per_share = dict(row)
        per_share["val"] = numerator_value / share_count
        per_share["tag"] = "PerShareDerived"
        rows.append(per_share)
    return sorted(rows, key=_entry_sort_key)


def _series_cagr(series: list[dict[str, Any]], years: int) -> float | None:
    if len(series) <= years:
        return None
    latest = safe_float(series[-1].get("val"))
    old = safe_float(series[-1 - years].get("val"))
    if latest is None or old is None or latest <= 0 or old <= 0:
        return None
    return (latest / old) ** (1 / years) - 1


def _latest_metadata(series: list[dict[str, Any]]) -> dict[str, Any]:
    if not series:
        return {}
    return sorted(series, key=_entry_sort_key)[-1]


def _set_number(result: dict[str, Any], field: str, value: Any) -> None:
    number = safe_float(value)
    if number is None:
        return
    result[field] = number
    result.setdefault("fields", []).append(field)


def _set_ratio(result: dict[str, Any], field: str, numerator: Any, denominator: Any) -> None:
    top = safe_float(numerator)
    bottom = safe_float(denominator)
    if top is None or bottom is None or bottom == 0:
        return
    _set_number(result, field, top / bottom)


def _set_growth(result: dict[str, Any], field: str, latest: Any, previous: Any) -> None:
    latest_number = safe_float(latest)
    previous_number = safe_float(previous)
    if latest_number is None or previous_number is None or previous_number == 0:
        return
    _set_number(result, field, latest_number / abs(previous_number) - 1)


def _entry_sort_key(entry: dict[str, Any]) -> tuple[int, str, str]:
    year = safe_float(entry.get("fy")) or safe_float(str(entry.get("end") or "")[:4]) or 0
    return int(year), str(entry.get("end") or ""), str(entry.get("filed") or "")


def _fiscal_year_key(entry: dict[str, Any]) -> str:
    fy = safe_float(entry.get("fy"))
    if fy is not None:
        return str(int(fy))
    end = str(entry.get("end") or "")
    return end[:4] if len(end) >= 4 else ""


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None
