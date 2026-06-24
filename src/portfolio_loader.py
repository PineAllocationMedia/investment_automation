from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import normalize_ticker, read_csv_records, safe_float, write_csv_records


PORTFOLIO_COLUMNS = ["ticker", "shares", "average_cost", "average_cost_currency", "account_type"]
PORTFOLIO_REQUIRED_COLUMNS = ["ticker"]
ACCOUNT_LOCATION_COLUMNS = ["ticker", "account_type", "current_value"]
ACCOUNT_TYPES = {"TFSA", "FHSA", "RRSP", "NON_REGISTERED"}
PORTFOLIO_COST_CURRENCIES = {"CAD", "USD"}
DEFAULT_PORTFOLIO_COST_CURRENCY = "CAD"


def load_portfolio(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in read_csv_records(path):
        ticker = normalize_ticker(raw.get("ticker"))
        if not ticker:
            continue
        rows.append(_portfolio_row(ticker, raw))
    return rows


def merge_portfolio_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        bucket = merged.setdefault(
            ticker,
            {
                "current_value": 0.0,
                "shares": 0.0,
                "acquisition_value": 0.0,
                "average_cost_currency": row.get("average_cost_currency"),
                "account_type": _account_type(row),
            },
        )
        row_account_type = _account_type(row)
        if bucket.get("account_type") in {None, ""}:
            bucket["account_type"] = row_account_type
        elif row_account_type and bucket.get("account_type") != row_account_type:
            bucket["account_type"] = "MIXED"
        bucket["current_value"] += safe_float(row.get("current_value")) or 0.0
        bucket["shares"] += safe_float(row.get("shares")) or 0.0
        row_currency = _portfolio_cost_currency(row)
        if bucket.get("average_cost_currency") in {None, ""}:
            bucket["average_cost_currency"] = row_currency
        elif row_currency and bucket.get("average_cost_currency") != row_currency:
            bucket["average_cost_currency"] = "MIXED"
        if bucket.get("average_cost_currency") != "MIXED":
            bucket["acquisition_value"] += safe_float(row.get("acquisition_value")) or 0.0
    return [_merged_portfolio_row(ticker, values) for ticker, values in sorted(merged.items())]


def enrich_portfolio_with_market_data(
    rows: list[dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    fx_rates_to_cad: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    fx_rates_to_cad = fx_rates_to_cad or {"CAD": 1.0}
    enriched: list[dict[str, Any]] = []
    for row in rows:
        ticker = row["ticker"]
        market = market_data.get(ticker, {})
        current_price = safe_float(market.get("current_price"))
        quote_currency = infer_quote_currency(ticker, market.get("currency"))
        quote_to_cad_rate = fx_rates_to_cad.get(quote_currency) or (1.0 if quote_currency == "CAD" else None)
        current_price_cad = (
            round(current_price * quote_to_cad_rate, 4)
            if current_price is not None and quote_to_cad_rate is not None
            else None
        )
        shares = safe_float(row.get("shares")) or 0.0
        current_value = safe_float(row.get("current_value")) or 0.0
        acquisition_value = safe_float(row.get("acquisition_value"))
        average_cost = safe_float(row.get("average_cost"))
        average_cost_currency = _portfolio_cost_currency(row)
        cost_to_cad_rate = fx_rates_to_cad.get(average_cost_currency) or (1.0 if average_cost_currency == "CAD" else None)
        if acquisition_value is None and shares > 0 and average_cost is not None:
            acquisition_value = round(shares * average_cost, 2)
        if average_cost is None and shares > 0 and acquisition_value is not None:
            average_cost = acquisition_value / shares
        average_cost_cad = (
            round(average_cost * cost_to_cad_rate, 4)
            if average_cost is not None and cost_to_cad_rate is not None
            else None
        )
        acquisition_value_cad = (
            round(acquisition_value * cost_to_cad_rate, 2)
            if acquisition_value is not None and cost_to_cad_rate is not None
            else None
        )
        valuation_source = "no_position"
        valuation_warning = None
        if shares > 0 and current_price is not None and current_price_cad is not None:
            current_value = round(shares * current_price_cad, 2)
            valuation_source = "shares_x_market_price_CAD" if quote_currency == "CAD" else "shares_x_market_price_fx_to_CAD"
        elif shares > 0 and current_value > 0:
            valuation_source = "manual_current_value_fallback"
            valuation_warning = "Prix ou taux FX manquant; valeur actuelle manuelle utilisée."
        elif shares > 0 and acquisition_value_cad is not None:
            current_value = acquisition_value_cad
            valuation_source = "acquisition_value_fallback"
            valuation_warning = "Prix ou taux FX manquant; coût d’acquisition utilisé comme approximation temporaire."
        elif current_value > 0:
            valuation_source = "manual_current_value_legacy"
        enriched.append(
            {
                **row,
                "current_value": current_value,
                "current_value_cad": current_value,
                "shares": shares,
                "average_cost": average_cost,
                "average_cost_cad": average_cost_cad,
                "acquisition_value": acquisition_value,
                "acquisition_value_cad": acquisition_value_cad,
                "portfolio_valuation_source": valuation_source,
                "portfolio_valuation_warning": valuation_warning,
                "quote_currency": quote_currency,
                "quote_to_cad_rate": quote_to_cad_rate,
                "current_price_cad": current_price_cad,
                "average_cost_currency": average_cost_currency if average_cost is not None else None,
                "average_cost_to_cad_rate": cost_to_cad_rate,
                "acquisition_value_currency": average_cost_currency if acquisition_value is not None else None,
                "current_value_currency": "CAD" if current_value > 0 else None,
                "account_type": row.get("account_type"),
            }
        )
    return enriched


def add_position_weights(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    total = sum(safe_float(row.get("current_value")) or 0.0 for row in rows)
    enriched: list[dict[str, Any]] = []
    for row in rows:
        value = safe_float(row.get("current_value")) or 0.0
        enriched.append(
            {
                **row,
                "position_weight": (value / total) if total > 0 else 0.0,
            }
        )
    return enriched, total


def position_weight_map(rows: list[dict[str, Any]]) -> dict[str, float]:
    weighted, _ = add_position_weights(rows)
    return {row["ticker"]: row["position_weight"] for row in weighted}


def load_account_locations(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in read_csv_records(path):
        ticker = normalize_ticker(raw.get("ticker"))
        account_type = normalize_account_type(raw.get("account_type"))
        value = safe_float(raw.get("current_value")) or 0.0
        if not ticker:
            continue
        rows.append(
            {
                "ticker": ticker,
                "account_type": account_type,
                "current_value": value,
            }
        )
    return rows


def create_portfolio_template(path: str | Path) -> None:
    rows = [
        {"ticker": "MSFT", "shares": 3, "average_cost": 250, "average_cost_currency": "USD", "account_type": "TFSA1"},
        {"ticker": "MSFT", "shares": 2, "average_cost": 260, "average_cost_currency": "USD", "account_type": "TFSA2"},
        {"ticker": "AVGO", "shares": 1, "average_cost": 900, "average_cost_currency": "USD", "account_type": "TFSA1"},
        {"ticker": "TSLA", "shares": 2, "average_cost": 250, "average_cost_currency": "USD", "account_type": "TFSA"},
        {"ticker": "LLY", "shares": 1, "average_cost": 800, "average_cost_currency": "USD", "account_type": "TFSA"},
        {"ticker": "INTU", "shares": 0, "average_cost": "", "average_cost_currency": "", "account_type": ""},
        {"ticker": "VFV.TO", "shares": 3, "average_cost": 140, "average_cost_currency": "CAD", "account_type": "FHSA"},
    ]
    write_csv_records(path, rows, PORTFOLIO_COLUMNS)


def create_empty_portfolio(path: str | Path) -> None:
    write_csv_records(path, [], PORTFOLIO_COLUMNS)


def create_account_locations_template(path: str | Path) -> None:
    rows = [
        {"ticker": "MSFT", "account_type": "TFSA", "current_value": 1200},
        {"ticker": "AVGO", "account_type": "TFSA", "current_value": 900},
        {"ticker": "VFV.TO", "account_type": "FHSA", "current_value": 500},
        {"ticker": "BAM", "account_type": "NON_REGISTERED", "current_value": 700},
    ]
    write_csv_records(path, rows, ACCOUNT_LOCATION_COLUMNS)


def create_empty_account_locations(path: str | Path) -> None:
    write_csv_records(path, [], ACCOUNT_LOCATION_COLUMNS)


def account_locations_from_portfolio_rows(
    portfolio_rows: list[dict[str, Any]],
    fallback_account_locations: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    fallback_by_ticker = {normalize_ticker(row.get("ticker")): row for row in (fallback_account_locations or [])}
    locations: list[dict[str, Any]] = []
    for row in portfolio_rows:
        ticker = normalize_ticker(row.get("ticker"))
        if not ticker:
            continue
        account_type = normalize_account_type(row.get("account_type"))
        fallback = fallback_by_ticker.get(ticker, {})
        if not account_type:
            account_type = normalize_account_type(fallback.get("account_type"))
        current_value = safe_float(row.get("current_value")) or safe_float(fallback.get("current_value")) or 0.0
        locations.append(
            {
                "ticker": ticker,
                "account_type": account_type or "UNKNOWN",
                "account_tax_category": account_tax_category(account_type),
                "current_value": current_value,
                "shares": safe_float(row.get("shares")) or 0.0,
            }
        )
    return locations


def _portfolio_row(ticker: str, raw: dict[str, Any]) -> dict[str, Any]:
    raw = repair_portfolio_raw_row(raw)
    shares = safe_float(raw.get("shares")) or 0.0
    current_value = safe_float(_first_present(raw.get("current_value_cad"), raw.get("current_value"))) or 0.0
    average_cost_currency = _portfolio_cost_currency(raw)
    average_cost = safe_float(
        _first_present(
            raw.get("average_cost"),
            raw.get("avg_cost"),
            raw.get("cost_per_share"),
            raw.get("average_cost_cad"),
        )
    )
    acquisition_value = safe_float(
        _first_present(
            raw.get("acquisition_value"),
            raw.get("total_cost"),
            raw.get("cost_basis"),
            raw.get("acquisition_value_cad"),
        )
    )
    if raw.get("average_cost_cad") not in {None, ""}:
        average_cost_currency = "CAD"
    if raw.get("acquisition_value_cad") not in {None, ""}:
        average_cost_currency = "CAD"
    if acquisition_value is None and shares > 0 and average_cost is not None:
        acquisition_value = round(shares * average_cost, 2)
    if average_cost is None and shares > 0 and acquisition_value is not None:
        average_cost = acquisition_value / shares
    return {
        "ticker": ticker,
        "current_value": current_value,
        "current_value_cad": current_value,
        "shares": shares,
        "average_cost": average_cost,
        "average_cost_cad": average_cost if average_cost_currency == "CAD" else None,
        "average_cost_currency": average_cost_currency if average_cost is not None else None,
        "acquisition_value": acquisition_value,
        "acquisition_value_cad": acquisition_value if average_cost_currency == "CAD" else None,
        "acquisition_value_currency": average_cost_currency if acquisition_value is not None else None,
        "account_type": _account_type(raw),
    }


def repair_portfolio_raw_row(raw: dict[str, Any]) -> dict[str, Any]:
    row = dict(raw)
    average_cost_text = str(row.get("average_cost") or "").strip().upper()
    average_cost_currency_text = str(row.get("average_cost_currency") or "").strip().upper()
    account_text = str(row.get("account_type") or row.get("account") or "").strip()
    if (
        average_cost_text in PORTFOLIO_COST_CURRENCIES
        and average_cost_currency_text
        and account_tax_category(average_cost_currency_text) in ACCOUNT_TYPES
        and not account_text
    ):
        row["average_cost"] = ""
        row["average_cost_currency"] = average_cost_text
        row["account_type"] = average_cost_currency_text
    return row


def _merged_portfolio_row(ticker: str, values: dict[str, Any]) -> dict[str, Any]:
    shares = values["shares"]
    acquisition_value = values["acquisition_value"] if values["acquisition_value"] > 0 else None
    average_cost = acquisition_value / shares if shares > 0 and acquisition_value is not None else None
    average_cost_currency = values.get("average_cost_currency")
    if average_cost_currency == "MIXED":
        acquisition_value = None
        average_cost = None
    return {
        "ticker": ticker,
        "current_value": round(values["current_value"], 2),
        "current_value_cad": round(values["current_value"], 2),
        "shares": shares,
        "average_cost": average_cost,
        "average_cost_cad": average_cost if average_cost_currency == "CAD" else None,
        "average_cost_currency": average_cost_currency if average_cost is not None else None,
        "acquisition_value": acquisition_value,
        "acquisition_value_cad": acquisition_value if average_cost_currency == "CAD" else None,
        "acquisition_value_currency": average_cost_currency if acquisition_value is not None else None,
        "account_type": values.get("account_type") or "",
    }


def _portfolio_cost_currency(row: dict[str, Any]) -> str:
    if row.get("average_cost_cad") not in {None, ""} or row.get("acquisition_value_cad") not in {None, ""}:
        return "CAD"
    currency = str(row.get("average_cost_currency") or row.get("cost_currency") or "").strip().upper()
    if currency in PORTFOLIO_COST_CURRENCIES:
        return currency
    return DEFAULT_PORTFOLIO_COST_CURRENCY


def _account_type(row: dict[str, Any]) -> str:
    return normalize_account_type(row.get("account_type") or row.get("account"))


def normalize_account_type(value: Any) -> str:
    return str(value or "").strip().upper()


def account_tax_category(account_type: Any) -> str:
    label = normalize_account_type(account_type)
    if label in {"", "UNKNOWN"}:
        return "UNKNOWN"
    if label == "MIXED":
        return "MIXED"
    if label in ACCOUNT_TYPES:
        return label
    for base in ACCOUNT_TYPES:
        if label.startswith(base):
            suffix = label[len(base) :]
            if suffix.isdigit():
                return base
    return "UNKNOWN"


def is_supported_account_type_label(account_type: Any) -> bool:
    label = normalize_account_type(account_type)
    if not label:
        return True
    return account_tax_category(label) in ACCOUNT_TYPES


def infer_quote_currency(ticker: str, market_currency: Any = None) -> str:
    explicit = str(market_currency or "").strip().upper()
    if explicit:
        return explicit
    normalized = normalize_ticker(ticker)
    if normalized.endswith((".TO", ".V", ".NE", ".CN")):
        return "CAD"
    if normalized.endswith((".PA", ".DE", ".AS", ".MI", ".MC", ".BR", ".HE", ".OL", ".ST")):
        return "EUR"
    if normalized.endswith(".SW"):
        return "CHF"
    if normalized.endswith(".L"):
        return "GBP"
    return "USD"


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if str(value).strip() == "":
            continue
        return value
    return None
