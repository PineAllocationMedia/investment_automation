from __future__ import annotations

from pathlib import Path
from typing import Any

from .portfolio_loader import account_tax_category, normalize_account_type
from .utils import normalize_ticker, read_csv_records, safe_float, write_csv_records


PORTFOLIO_TRANSACTION_COLUMNS = [
    "date",
    "ticker",
    "account_type",
    "transaction_type",
    "shares",
    "price",
    "price_currency",
    "fees",
    "fees_currency",
    "cash_amount",
    "cash_currency",
    "notes",
]

PORTFOLIO_TRANSACTION_REPORT_COLUMNS = [
    "date",
    "ticker",
    "account_type",
    "account_tax_category",
    "transaction_type",
    "shares",
    "price",
    "price_currency",
    "price_cad",
    "fees",
    "fees_currency",
    "fees_cad",
    "cash_amount",
    "cash_currency",
    "cash_amount_cad",
    "trade_value_cad",
    "net_trade_cash_flow_cad",
    "net_contribution_cad",
    "income_cad",
    "notes",
]

PORTFOLIO_TRANSACTION_SUMMARY_COLUMNS = [
    "account_type",
    "account_tax_category",
    "ticker",
    "buy_value_cad",
    "sell_value_cad",
    "net_buy_sell_cad",
    "net_contributions_cad",
    "income_cad",
    "net_shares_change",
    "first_transaction_date",
    "last_transaction_date",
    "transaction_count",
]

TRANSACTION_TYPES = {
    "BUY",
    "SELL",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "CASH_CONTRIBUTION",
    "CASH_WITHDRAWAL",
    "DIVIDEND",
}

TRANSACTION_TYPE_ALIASES = {
    "ACHAT": "BUY",
    "AJOUT": "BUY",
    "ADD": "BUY",
    "VENTE": "SELL",
    "VENDRE": "SELL",
    "SALE": "SELL",
    "COTISATION": "CASH_CONTRIBUTION",
    "CONTRIBUTION": "CASH_CONTRIBUTION",
    "DEPOT": "CASH_CONTRIBUTION",
    "DÉPÔT": "CASH_CONTRIBUTION",
    "RETRAIT": "CASH_WITHDRAWAL",
    "WITHDRAWAL": "CASH_WITHDRAWAL",
    "DIVIDENDE": "DIVIDEND",
    "TRANSFERT_ENTRANT": "TRANSFER_IN",
    "TRANSFERT_SORTANT": "TRANSFER_OUT",
}

TRANSACTION_CURRENCIES = {"CAD", "USD", "EUR", "GBP", "CHF", "JPY"}


def load_portfolio_transactions(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in read_csv_records(path):
        transaction_type = normalize_transaction_type(raw.get("transaction_type"))
        ticker = normalize_ticker(raw.get("ticker"))
        account_type = normalize_account_type(raw.get("account_type"))
        if not any(str(raw.get(column) or "").strip() for column in PORTFOLIO_TRANSACTION_COLUMNS):
            continue
        rows.append(
            {
                "date": str(raw.get("date") or "").strip(),
                "ticker": ticker,
                "account_type": account_type,
                "transaction_type": transaction_type,
                "shares": safe_float(raw.get("shares")),
                "price": safe_float(raw.get("price")),
                "price_currency": normalize_currency(raw.get("price_currency")),
                "fees": safe_float(raw.get("fees")) or 0.0,
                "fees_currency": normalize_currency(raw.get("fees_currency")),
                "cash_amount": safe_float(raw.get("cash_amount")),
                "cash_currency": normalize_currency(raw.get("cash_currency")),
                "notes": str(raw.get("notes") or "").strip(),
            }
        )
    return rows


def create_portfolio_transactions_template(path: str | Path) -> None:
    rows = [
        {
            "date": "2026-05-12",
            "ticker": "MSFT",
            "account_type": "TFSA1",
            "transaction_type": "BUY",
            "shares": 1,
            "price": 420,
            "price_currency": "USD",
            "fees": 0,
            "fees_currency": "CAD",
            "cash_amount": "",
            "cash_currency": "",
            "notes": "Exemple achat.",
        },
        {
            "date": "2026-05-12",
            "ticker": "VFV.TO",
            "account_type": "FHSA",
            "transaction_type": "SELL",
            "shares": 1,
            "price": 145,
            "price_currency": "CAD",
            "fees": 0,
            "fees_currency": "CAD",
            "cash_amount": "",
            "cash_currency": "",
            "notes": "Exemple vente.",
        },
        {
            "date": "2026-05-12",
            "ticker": "",
            "account_type": "TFSA1",
            "transaction_type": "CASH_CONTRIBUTION",
            "shares": "",
            "price": "",
            "price_currency": "",
            "fees": "",
            "fees_currency": "",
            "cash_amount": 500,
            "cash_currency": "CAD",
            "notes": "Exemple cotisation.",
        },
    ]
    write_csv_records(path, rows, PORTFOLIO_TRANSACTION_COLUMNS)


def create_empty_portfolio_transactions(path: str | Path) -> None:
    write_csv_records(path, [], PORTFOLIO_TRANSACTION_COLUMNS)


def portfolio_transaction_currencies(rows: list[dict[str, Any]]) -> list[str]:
    currencies: list[str] = []
    for row in rows:
        for field in ("price_currency", "fees_currency", "cash_currency"):
            currency = normalize_currency(row.get(field))
            if currency:
                currencies.append(currency)
    return currencies


def build_portfolio_transaction_report_rows(
    rows: list[dict[str, Any]],
    fx_rates_to_cad: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    fx_rates_to_cad = fx_rates_to_cad or {"CAD": 1.0}
    output: list[dict[str, Any]] = []
    for row in rows:
        transaction_type = normalize_transaction_type(row.get("transaction_type"))
        shares = safe_float(row.get("shares")) or 0.0
        price = safe_float(row.get("price"))
        fees = safe_float(row.get("fees")) or 0.0
        cash_amount = safe_float(row.get("cash_amount"))
        price_currency = normalize_currency(row.get("price_currency")) or "CAD"
        fees_currency = normalize_currency(row.get("fees_currency")) or price_currency
        cash_currency = normalize_currency(row.get("cash_currency")) or "CAD"
        price_cad = _to_cad(price, price_currency, fx_rates_to_cad)
        fees_cad = _to_cad(fees, fees_currency, fx_rates_to_cad) or 0.0
        cash_amount_cad = _to_cad(cash_amount, cash_currency, fx_rates_to_cad)
        gross_trade_value = shares * price_cad if shares > 0 and price_cad is not None else None
        trade_value_cad = None
        net_trade_cash_flow_cad = 0.0
        net_contribution_cad = 0.0
        income_cad = 0.0

        if transaction_type == "BUY" and gross_trade_value is not None:
            trade_value_cad = gross_trade_value + fees_cad
            net_trade_cash_flow_cad = -trade_value_cad
        elif transaction_type == "SELL" and gross_trade_value is not None:
            trade_value_cad = max(0.0, gross_trade_value - fees_cad)
            net_trade_cash_flow_cad = trade_value_cad
        elif transaction_type == "TRANSFER_IN" and gross_trade_value is not None:
            trade_value_cad = gross_trade_value
        elif transaction_type == "TRANSFER_OUT" and gross_trade_value is not None:
            trade_value_cad = gross_trade_value
        elif transaction_type == "CASH_CONTRIBUTION" and cash_amount_cad is not None:
            net_contribution_cad = cash_amount_cad
        elif transaction_type == "CASH_WITHDRAWAL" and cash_amount_cad is not None:
            net_contribution_cad = -cash_amount_cad
        elif transaction_type == "DIVIDEND" and cash_amount_cad is not None:
            income_cad = cash_amount_cad

        account_type = normalize_account_type(row.get("account_type"))
        output.append(
            {
                "date": str(row.get("date") or "").strip(),
                "ticker": normalize_ticker(row.get("ticker")),
                "account_type": account_type,
                "account_tax_category": account_tax_category(account_type),
                "transaction_type": transaction_type,
                "shares": shares if shares else "",
                "price": price if price is not None else "",
                "price_currency": price_currency if price is not None else "",
                "price_cad": round(price_cad, 4) if price_cad is not None else "",
                "fees": fees if fees else "",
                "fees_currency": fees_currency if fees else "",
                "fees_cad": round(fees_cad, 2) if fees else "",
                "cash_amount": cash_amount if cash_amount is not None else "",
                "cash_currency": cash_currency if cash_amount is not None else "",
                "cash_amount_cad": round(cash_amount_cad, 2) if cash_amount_cad is not None else "",
                "trade_value_cad": round(trade_value_cad, 2) if trade_value_cad is not None else "",
                "net_trade_cash_flow_cad": round(net_trade_cash_flow_cad, 2),
                "net_contribution_cad": round(net_contribution_cad, 2),
                "income_cad": round(income_cad, 2),
                "notes": str(row.get("notes") or "").strip(),
            }
        )
    return sorted(output, key=lambda item: (str(item.get("date") or ""), str(item.get("ticker") or "")))


def summarize_portfolio_transactions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        ticker = normalize_ticker(row.get("ticker")) or "CASH"
        key = (account_type, ticker)
        bucket = summaries.setdefault(
            key,
            {
                "account_type": account_type,
                "account_tax_category": account_tax_category(account_type),
                "ticker": ticker,
                "buy_value_cad": 0.0,
                "sell_value_cad": 0.0,
                "net_contributions_cad": 0.0,
                "income_cad": 0.0,
                "net_shares_change": 0.0,
                "first_transaction_date": "",
                "last_transaction_date": "",
                "transaction_count": 0,
            },
        )
        transaction_type = normalize_transaction_type(row.get("transaction_type"))
        trade_value = safe_float(row.get("trade_value_cad")) or 0.0
        shares = safe_float(row.get("shares")) or 0.0
        if transaction_type == "BUY":
            bucket["buy_value_cad"] += trade_value
            bucket["net_shares_change"] += shares
        elif transaction_type == "SELL":
            bucket["sell_value_cad"] += trade_value
            bucket["net_shares_change"] -= shares
        elif transaction_type == "TRANSFER_IN":
            bucket["net_shares_change"] += shares
        elif transaction_type == "TRANSFER_OUT":
            bucket["net_shares_change"] -= shares
        bucket["net_contributions_cad"] += safe_float(row.get("net_contribution_cad")) or 0.0
        bucket["income_cad"] += safe_float(row.get("income_cad")) or 0.0
        date = str(row.get("date") or "").strip()
        if date:
            if not bucket["first_transaction_date"] or date < bucket["first_transaction_date"]:
                bucket["first_transaction_date"] = date
            if not bucket["last_transaction_date"] or date > bucket["last_transaction_date"]:
                bucket["last_transaction_date"] = date
        bucket["transaction_count"] += 1

    output = []
    for row in summaries.values():
        buy_value = safe_float(row.get("buy_value_cad")) or 0.0
        sell_value = safe_float(row.get("sell_value_cad")) or 0.0
        output.append(
            {
                **row,
                "buy_value_cad": round(buy_value, 2),
                "sell_value_cad": round(sell_value, 2),
                "net_buy_sell_cad": round(buy_value - sell_value, 2),
                "net_contributions_cad": round(safe_float(row.get("net_contributions_cad")) or 0.0, 2),
                "income_cad": round(safe_float(row.get("income_cad")) or 0.0, 2),
                "net_shares_change": round(safe_float(row.get("net_shares_change")) or 0.0, 6),
            }
        )
    return sorted(output, key=lambda item: (str(item.get("account_type") or ""), str(item.get("ticker") or "")))


def normalize_transaction_type(value: Any) -> str:
    text = str(value or "").strip().upper().replace(" ", "_").replace("-", "_")
    return TRANSACTION_TYPE_ALIASES.get(text, text)


def normalize_currency(value: Any) -> str:
    return str(value or "").strip().upper()


def _to_cad(value: float | None, currency: str, fx_rates_to_cad: dict[str, float]) -> float | None:
    if value is None:
        return None
    rate = fx_rates_to_cad.get(normalize_currency(currency) or "CAD")
    if rate is None:
        return None
    return value * rate
