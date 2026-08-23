from __future__ import annotations

from pathlib import Path
from typing import Any

from .portfolio_loader import account_tax_category, normalize_account_type
from .utils import normalize_ticker, read_csv_records, safe_float, today_iso, write_csv_records


PORTFOLIO_STATE_COLUMNS = [
    "date",
    "ticker",
    "account_type",
    "account_tax_category",
    "shares",
    "average_cost",
    "average_cost_currency",
    "average_cost_cad",
    "acquisition_value_cad",
    "current_price_cad",
    "current_value_cad",
]

PORTFOLIO_CHANGE_COLUMNS = [
    "date",
    "ticker",
    "account_type",
    "account_tax_category",
    "change_type",
    "shares_before",
    "shares_after",
    "shares_change",
    "average_cost_before",
    "average_cost_after",
    "average_cost_currency_before",
    "average_cost_currency_after",
    "estimated_change_value_cad",
    "current_value_cad_after",
    "reason",
    "source",
]

PORTFOLIO_CHANGE_SUMMARY_COLUMNS = [
    "account_type",
    "account_tax_category",
    "ticker",
    "buy_or_add_count",
    "sell_or_reduce_count",
    "transfer_count",
    "cost_update_count",
    "net_shares_change",
    "estimated_net_add_value_cad",
    "first_change_date",
    "last_change_date",
]

EPSILON = 1e-6


def update_portfolio_change_history(
    current_rows: list[dict[str, Any]],
    snapshot_path: str | Path,
    history_path: str | Path,
    as_of_date: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    as_of_date = as_of_date or today_iso()
    snapshot_path = Path(snapshot_path)
    history_path = Path(history_path)
    previous_snapshot = read_csv_records(snapshot_path)
    previous_map = _rows_by_key(previous_snapshot)
    current_snapshot = build_portfolio_state_rows(current_rows, as_of_date=as_of_date)
    current_map = _rows_by_key(current_snapshot)
    existing_history = read_csv_records(history_path)

    if not previous_snapshot:
        detected_changes = _baseline_changes(current_snapshot, as_of_date)
        changes_to_append = detected_changes if not existing_history else []
    else:
        detected_changes = detect_portfolio_changes(previous_map, current_map, as_of_date)
        changes_to_append = _uncommitted_changes(detected_changes, existing_history)

    full_history = [*existing_history, *changes_to_append]
    write_csv_records(history_path, full_history, PORTFOLIO_CHANGE_COLUMNS)
    write_csv_records(snapshot_path, current_snapshot, PORTFOLIO_STATE_COLUMNS)
    return changes_to_append, full_history, summarize_portfolio_change_history(full_history)


def build_portfolio_state_rows(rows: list[dict[str, Any]], as_of_date: str | None = None) -> list[dict[str, Any]]:
    as_of_date = as_of_date or today_iso()
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker"))
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        if not ticker:
            continue
        shares = safe_float(row.get("shares")) or 0.0
        current_value = safe_float(row.get("current_value_cad") or row.get("current_value")) or 0.0
        acquisition_value_cad = safe_float(row.get("acquisition_value_cad"))
        average_cost_cad = safe_float(row.get("average_cost_cad"))
        average_cost = safe_float(row.get("average_cost"))
        average_cost_currency = str(row.get("average_cost_currency") or "").strip().upper()
        if not average_cost_currency and (average_cost_cad is not None or acquisition_value_cad is not None):
            average_cost_currency = "CAD"
        if average_cost is None and average_cost_currency == "CAD":
            average_cost = average_cost_cad
        acquisition_value = safe_float(row.get("acquisition_value"))
        if acquisition_value is None and average_cost is not None:
            acquisition_value = shares * average_cost
        if acquisition_value_cad is None and average_cost_cad is not None:
            acquisition_value_cad = shares * average_cost_cad
        key = (ticker, account_type)
        bucket = buckets.setdefault(
            key,
            {
                "date": as_of_date,
                "ticker": ticker,
                "account_type": account_type,
                "account_tax_category": account_tax_category(account_type),
                "shares": 0.0,
                "average_cost": "",
                "average_cost_currency": "",
                "average_cost_cad": "",
                "acquisition_value_cad": 0.0,
                "current_price_cad": row.get("current_price_cad"),
                "current_value_cad": 0.0,
                "_average_cost_source_total": 0.0,
                "_average_cost_source_complete": True,
                "_average_cost_currency": average_cost_currency,
            },
        )
        bucket["shares"] += shares
        bucket["current_value_cad"] += current_value
        bucket["acquisition_value_cad"] += acquisition_value_cad or 0.0
        if shares > EPSILON:
            if acquisition_value is None:
                bucket["_average_cost_source_complete"] = False
            else:
                bucket["_average_cost_source_total"] += acquisition_value
        row_currency = average_cost_currency
        if row_currency:
            current_currency = bucket.get("_average_cost_currency") or row_currency
            bucket["_average_cost_currency"] = current_currency if current_currency == row_currency else "MIXED"

    output: list[dict[str, Any]] = []
    for bucket in buckets.values():
        shares = safe_float(bucket.get("shares")) or 0.0
        acquisition_value_cad = safe_float(bucket.get("acquisition_value_cad")) or 0.0
        average_cost_cad = acquisition_value_cad / shares if shares > EPSILON and acquisition_value_cad > 0 else None
        average_cost_currency = str(bucket.get("_average_cost_currency") or "")
        source_cost_total = safe_float(bucket.get("_average_cost_source_total")) or 0.0
        source_cost_complete = bool(bucket.get("_average_cost_source_complete"))
        average_cost = (
            source_cost_total / shares
            if shares > EPSILON
            and source_cost_total > 0
            and source_cost_complete
            and average_cost_currency not in {"", "MIXED"}
            else None
        )
        output.append(
            {
                "date": bucket.get("date"),
                "ticker": bucket.get("ticker"),
                "account_type": bucket.get("account_type"),
                "account_tax_category": bucket.get("account_tax_category"),
                "shares": round(shares, 8),
                "average_cost": round(average_cost, 4) if average_cost is not None else "",
                "average_cost_currency": average_cost_currency if average_cost is not None or average_cost_cad is not None else "",
                "average_cost_cad": round(average_cost_cad, 4) if average_cost_cad is not None else "",
                "acquisition_value_cad": round(acquisition_value_cad, 2) if acquisition_value_cad > 0 else "",
                "current_price_cad": _round_or_blank(bucket.get("current_price_cad"), 4),
                "current_value_cad": round(safe_float(bucket.get("current_value_cad")) or 0.0, 2),
            }
        )
    return sorted(output, key=lambda item: (str(item.get("ticker") or ""), str(item.get("account_type") or "")))


def detect_portfolio_changes(
    previous_map: dict[tuple[str, str], dict[str, Any]],
    current_map: dict[tuple[str, str], dict[str, Any]],
    as_of_date: str,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for key in sorted(set(previous_map) | set(current_map)):
        previous = previous_map.get(key, {})
        current = current_map.get(key, {})
        ticker = normalize_ticker(current.get("ticker") or previous.get("ticker"))
        account_type = normalize_account_type(current.get("account_type") or previous.get("account_type")) or "UNKNOWN"
        shares_before = safe_float(previous.get("shares")) or 0.0
        shares_after = safe_float(current.get("shares")) or 0.0
        shares_change = shares_after - shares_before
        if abs(shares_change) > EPSILON:
            if shares_before <= EPSILON and shares_after > EPSILON:
                change_type = "POSITION_ADDED"
                reason = "Nouvelle position detectee dans portfolio.csv pour ce compte."
            elif shares_after <= EPSILON and shares_before > EPSILON:
                change_type = "POSITION_CLOSED"
                reason = "Position retiree ou mise a zero dans portfolio.csv pour ce compte."
            elif shares_change > 0:
                change_type = "SHARES_INCREASED"
                reason = "Nombre d'actions augmente dans portfolio.csv depuis la derniere analyse."
            else:
                change_type = "SHARES_DECREASED"
                reason = "Nombre d'actions diminue dans portfolio.csv depuis la derniere analyse."
            changes.append(_change_row(as_of_date, ticker, account_type, change_type, previous, current, reason))
            continue

        if shares_after > EPSILON and _cost_basis_changed(previous, current):
            changes.append(
                _change_row(
                    as_of_date,
                    ticker,
                    account_type,
                    "COST_BASIS_UPDATED",
                    previous,
                    current,
                    "Cout moyen ou devise du cout moyen modifie dans portfolio.csv.",
                )
            )

    return _classify_possible_transfers(changes)


def summarize_portfolio_change_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker"))
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        key = (account_type, ticker)
        bucket = buckets.setdefault(
            key,
            {
                "account_type": account_type,
                "account_tax_category": account_tax_category(account_type),
                "ticker": ticker,
                "buy_or_add_count": 0,
                "sell_or_reduce_count": 0,
                "transfer_count": 0,
                "cost_update_count": 0,
                "net_shares_change": 0.0,
                "estimated_net_add_value_cad": 0.0,
                "first_change_date": "",
                "last_change_date": "",
            },
        )
        change_type = str(row.get("change_type") or "")
        shares_change = safe_float(row.get("shares_change")) or 0.0
        estimated_value = safe_float(row.get("estimated_change_value_cad")) or 0.0
        if change_type in {"BASELINE", "POSITION_ADDED", "SHARES_INCREASED"}:
            bucket["buy_or_add_count"] += 1
        elif change_type in {"POSITION_CLOSED", "SHARES_DECREASED"}:
            bucket["sell_or_reduce_count"] += 1
        elif change_type in {"POSSIBLE_TRANSFER_IN", "POSSIBLE_TRANSFER_OUT"}:
            bucket["transfer_count"] += 1
        elif change_type == "COST_BASIS_UPDATED":
            bucket["cost_update_count"] += 1
        bucket["net_shares_change"] += shares_change
        bucket["estimated_net_add_value_cad"] += estimated_value if shares_change >= 0 else -estimated_value
        date = str(row.get("date") or "").strip()
        if date:
            if not bucket["first_change_date"] or date < bucket["first_change_date"]:
                bucket["first_change_date"] = date
            if not bucket["last_change_date"] or date > bucket["last_change_date"]:
                bucket["last_change_date"] = date

    output = []
    for row in buckets.values():
        output.append(
            {
                **row,
                "net_shares_change": round(safe_float(row.get("net_shares_change")) or 0.0, 8),
                "estimated_net_add_value_cad": round(safe_float(row.get("estimated_net_add_value_cad")) or 0.0, 2),
            }
        )
    return sorted(output, key=lambda item: (str(item.get("account_type") or ""), str(item.get("ticker") or "")))


def _baseline_changes(current_snapshot: list[dict[str, Any]], as_of_date: str) -> list[dict[str, Any]]:
    changes = []
    for current in current_snapshot:
        if (safe_float(current.get("shares")) or 0.0) <= EPSILON:
            continue
        changes.append(
            _change_row(
                as_of_date,
                normalize_ticker(current.get("ticker")),
                normalize_account_type(current.get("account_type")) or "UNKNOWN",
                "BASELINE",
                {},
                current,
                "Point de depart automatique: premiere analyse avec historique de portefeuille active.",
            )
        )
    return changes


def _change_row(
    date: str,
    ticker: str,
    account_type: str,
    change_type: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    shares_before = safe_float(previous.get("shares")) or 0.0
    shares_after = safe_float(current.get("shares")) or 0.0
    shares_change = shares_after - shares_before
    current_price_cad = safe_float(current.get("current_price_cad")) or safe_float(previous.get("current_price_cad"))
    current_value_before = safe_float(previous.get("current_value_cad")) or 0.0
    current_value_after = safe_float(current.get("current_value_cad")) or 0.0
    estimated_value = abs(shares_change) * current_price_cad if current_price_cad is not None else None
    if estimated_value is None and abs(shares_change) > EPSILON:
        estimated_value = abs(current_value_after - current_value_before)
    return {
        "date": date,
        "ticker": ticker,
        "account_type": account_type,
        "account_tax_category": account_tax_category(account_type),
        "change_type": change_type,
        "shares_before": round(shares_before, 8),
        "shares_after": round(shares_after, 8),
        "shares_change": round(shares_change, 8),
        "average_cost_before": _round_or_blank(_stable_source_cost(previous), 4),
        "average_cost_after": _round_or_blank(_stable_source_cost(current), 4),
        "average_cost_currency_before": previous.get("average_cost_currency", ""),
        "average_cost_currency_after": current.get("average_cost_currency", ""),
        "estimated_change_value_cad": round(estimated_value, 2) if estimated_value is not None else "",
        "current_value_cad_after": _round_or_blank(current.get("current_value_cad"), 2),
        "reason": reason,
        "source": "AUTO_FROM_PORTFOLIO_DIFF",
    }


def _classify_possible_transfers(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unmatched_positive = [
        row
        for row in changes
        if row.get("change_type") in {"POSITION_ADDED", "SHARES_INCREASED"}
        and (safe_float(row.get("shares_change")) or 0.0) > EPSILON
    ]
    unmatched_negative = [
        row
        for row in changes
        if row.get("change_type") in {"POSITION_CLOSED", "SHARES_DECREASED"}
        and (safe_float(row.get("shares_change")) or 0.0) < -EPSILON
    ]
    matched_negative_indexes: set[int] = set()
    for positive in unmatched_positive:
        positive_delta = safe_float(positive.get("shares_change")) or 0.0
        for index, negative in enumerate(unmatched_negative):
            if index in matched_negative_indexes:
                continue
            if positive.get("ticker") != negative.get("ticker"):
                continue
            negative_delta = abs(safe_float(negative.get("shares_change")) or 0.0)
            if abs(positive_delta - negative_delta) > EPSILON:
                continue
            positive["change_type"] = "POSSIBLE_TRANSFER_IN"
            negative["change_type"] = "POSSIBLE_TRANSFER_OUT"
            positive["reason"] = "Transfert possible detecte: meme ticker ajoute dans un compte et retire d'un autre."
            negative["reason"] = "Transfert possible detecte: meme ticker retire d'un compte et ajoute dans un autre."
            matched_negative_indexes.add(index)
            break
    return changes


def _rows_by_key(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker"))
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        if ticker:
            output[(ticker, account_type)] = row
    return output


def _cost_basis_changed(previous: dict[str, Any], current: dict[str, Any]) -> bool:
    previous_currency = str(previous.get("average_cost_currency") or "").strip().upper()
    current_currency = str(current.get("average_cost_currency") or "").strip().upper()
    previous_cost = _stable_source_cost(previous)
    current_cost = _stable_source_cost(current)

    if previous_currency and current_currency and previous_currency != current_currency:
        return True
    if previous_cost is None and current_cost is None:
        return False
    if previous_cost is None:
        # Legacy foreign-currency snapshots left average_cost blank. Their CAD
        # value is FX-sensitive, so populate the new stable field without
        # manufacturing a user edit during migration.
        return False
    if current_cost is None:
        return True
    return abs(previous_cost - current_cost) >= 0.01


def _stable_source_cost(row: dict[str, Any]) -> float | None:
    source_cost = safe_float(row.get("average_cost"))
    if source_cost is not None:
        return source_cost
    currency = str(row.get("average_cost_currency") or "").strip().upper()
    if currency == "CAD":
        return safe_float(row.get("average_cost_cad"))
    return None


def _uncommitted_changes(
    detected_changes: list[dict[str, Any]],
    existing_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    latest_by_position: dict[tuple[str, str], dict[str, Any]] = {}
    for row in existing_history:
        latest_by_position[_change_position_key(row)] = row

    output: list[dict[str, Any]] = []
    for change in detected_changes:
        position_key = _change_position_key(change)
        latest = latest_by_position.get(position_key)
        if latest is not None and _change_identity(latest) == _change_identity(change):
            continue
        output.append(change)
        latest_by_position[position_key] = change
    return output


def _change_position_key(row: dict[str, Any]) -> tuple[str, str]:
    return (
        normalize_ticker(row.get("ticker")),
        normalize_account_type(row.get("account_type")) or "UNKNOWN",
    )


def _change_identity(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        str(row.get("date") or "").strip(),
        *_change_position_key(row),
        str(row.get("change_type") or "").strip().upper(),
        _identity_number(row.get("shares_before"), 8),
        _identity_number(row.get("shares_after"), 8),
        _identity_number(row.get("average_cost_before"), 4),
        _identity_number(row.get("average_cost_after"), 4),
        str(row.get("average_cost_currency_before") or "").strip().upper(),
        str(row.get("average_cost_currency_after") or "").strip().upper(),
    )


def _identity_number(value: Any, digits: int) -> float | None:
    number = safe_float(value)
    return round(number, digits) if number is not None else None


def _round_or_blank(value: Any, digits: int) -> Any:
    number = safe_float(value)
    return round(number, digits) if number is not None else ""
