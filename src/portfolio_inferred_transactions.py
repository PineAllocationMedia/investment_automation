from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from .portfolio_loader import account_tax_category, normalize_account_type
from .utils import normalize_ticker, read_csv_records, safe_float, today_iso, write_csv_records


INFERRED_TRANSACTION_COLUMNS = [
    "date",
    "ticker",
    "account_type",
    "account_tax_category",
    "inferred_transaction_type",
    "shares_change",
    "estimated_price_cad",
    "estimated_value_cad",
    "external_flow_cad",
    "sp500_proxy",
    "sp500_proxy_price_at_flow",
    "sp500_proxy_price_basis",
    "confidence",
    "source_change_type",
    "source",
    "notes",
]

FLOW_TRANSACTION_TYPES = {
    "INFERRED_BUY",
    "INFERRED_SELL",
}


def update_inferred_transactions_from_changes(
    portfolio_change_history_rows: list[dict[str, Any]],
    path: str | Path,
    *,
    sp500_proxy_price: float | None,
    sp500_proxy_price_basis: str = "PRICE_CLOSE",
    as_of_date: str | None = None,
    sp500_proxy: str = "VFV.TO",
) -> list[dict[str, Any]]:
    """Create a separate approximate transaction log from portfolio.csv diffs."""

    as_of_date = as_of_date or today_iso()
    path = Path(path)
    existing_rows = read_csv_records(path)
    existing_by_key: dict[tuple[Any, ...], deque[dict[str, Any]]] = defaultdict(deque)
    for row in existing_rows:
        existing_by_key[_dedupe_key(row)].append(row)

    output: list[dict[str, Any]] = []
    represented_keys: set[tuple[Any, ...]] = set()

    for change in portfolio_change_history_rows:
        inferred = _inferred_row_from_change(change, as_of_date, sp500_proxy, sp500_proxy_price, sp500_proxy_price_basis)
        if not inferred:
            continue
        key = _dedupe_key(inferred)
        represented_keys.add(key)
        if existing_by_key[key]:
            output.append(existing_by_key[key].popleft())
        else:
            output.append(inferred)

    # Preserve one legacy/orphan row per key, matching the previous behavior,
    # but discard surplus rows for keys whose authoritative multiplicity is now
    # represented by portfolio change history.
    for key, rows in existing_by_key.items():
        if key in represented_keys or not rows:
            continue
        output.append(rows.popleft())

    output = sorted(output, key=lambda row: (str(row.get("date") or ""), str(row.get("account_type") or ""), str(row.get("ticker") or "")))
    write_csv_records(path, output, INFERRED_TRANSACTION_COLUMNS)
    return output


def reportable_inferred_transactions(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get("date") or ""), reverse=True)[:limit]


def _inferred_row_from_change(
    change: dict[str, Any],
    as_of_date: str,
    sp500_proxy: str,
    sp500_proxy_price: float | None,
    sp500_proxy_price_basis: str,
) -> dict[str, Any] | None:
    ticker = normalize_ticker(change.get("ticker"))
    if not ticker:
        return None
    date = str(change.get("date") or "").strip()
    if not date:
        return None
    change_type = str(change.get("change_type") or "").strip().upper()
    inferred_type = _inferred_type(change_type)
    if not inferred_type:
        return None
    account_type = normalize_account_type(change.get("account_type")) or "UNKNOWN"
    shares_change = safe_float(change.get("shares_change")) or 0.0
    estimated_value = safe_float(change.get("estimated_change_value_cad"))
    estimated_price = abs(estimated_value / shares_change) if estimated_value is not None and abs(shares_change) > 1e-9 else None
    external_flow = _external_flow(inferred_type, estimated_value)
    flow_price = sp500_proxy_price if date == as_of_date and inferred_type in FLOW_TRANSACTION_TYPES else None
    return {
        "date": date,
        "ticker": ticker,
        "account_type": account_type,
        "account_tax_category": account_tax_category(account_type),
        "inferred_transaction_type": inferred_type,
        "shares_change": round(shares_change, 8),
        "estimated_price_cad": round(estimated_price, 4) if estimated_price is not None else "",
        "estimated_value_cad": round(estimated_value, 2) if estimated_value is not None else "",
        "external_flow_cad": round(external_flow, 2) if external_flow is not None else "",
        "sp500_proxy": sp500_proxy,
        "sp500_proxy_price_at_flow": round(flow_price, 4) if flow_price is not None else "",
        "sp500_proxy_price_basis": sp500_proxy_price_basis if flow_price is not None else "",
        "confidence": _confidence(inferred_type, date, as_of_date, flow_price),
        "source_change_type": change_type,
        "source": "AUTO_FROM_PORTFOLIO_CHANGE_HISTORY",
        "notes": _notes(inferred_type, date, as_of_date),
    }


def _inferred_type(change_type: str) -> str | None:
    if change_type in {"POSITION_ADDED", "SHARES_INCREASED"}:
        return "INFERRED_BUY"
    if change_type in {"POSITION_CLOSED", "SHARES_DECREASED"}:
        return "INFERRED_SELL"
    if change_type == "POSSIBLE_TRANSFER_IN":
        return "INFERRED_TRANSFER_IN"
    if change_type == "POSSIBLE_TRANSFER_OUT":
        return "INFERRED_TRANSFER_OUT"
    if change_type == "COST_BASIS_UPDATED":
        return "INFERRED_COST_UPDATE"
    if change_type == "BASELINE":
        return "BASELINE"
    return None


def _external_flow(inferred_type: str, estimated_value: float | None) -> float | None:
    if inferred_type == "INFERRED_BUY":
        return estimated_value
    if inferred_type == "INFERRED_SELL" and estimated_value is not None:
        return -estimated_value
    if inferred_type in {"INFERRED_TRANSFER_IN", "INFERRED_TRANSFER_OUT", "INFERRED_COST_UPDATE", "BASELINE"}:
        return 0.0
    return None


def _confidence(inferred_type: str, date: str, as_of_date: str, flow_price: float | None) -> str:
    if inferred_type in {"BASELINE", "INFERRED_COST_UPDATE"}:
        return "INFO_ONLY"
    if inferred_type in {"INFERRED_TRANSFER_IN", "INFERRED_TRANSFER_OUT"}:
        return "MEDIUM"
    if date == as_of_date and flow_price is not None:
        return "MEDIUM"
    return "LOW"


def _notes(inferred_type: str, date: str, as_of_date: str) -> str:
    if inferred_type == "BASELINE":
        return "Point de départ automatique; pas une transaction réelle."
    if inferred_type == "INFERRED_COST_UPDATE":
        return "Changement de coût moyen; pas traité comme flux externe."
    if inferred_type in {"INFERRED_TRANSFER_IN", "INFERRED_TRANSFER_OUT"}:
        return "Transfert possible; pas traité comme flux externe."
    if date != as_of_date:
        return "Transaction déduite d’un ancien changement; prix VFV historique non connu, donc usage limité."
    return "Transaction approximative déduite d’un changement dans portfolio.csv."


def _dedupe_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("date") or ""),
        normalize_ticker(row.get("ticker")),
        normalize_account_type(row.get("account_type")) or "UNKNOWN",
        str(row.get("inferred_transaction_type") or row.get("source_change_type") or ""),
        str(row.get("shares_change") or ""),
        str(row.get("estimated_value_cad") or ""),
    )
