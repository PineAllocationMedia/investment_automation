from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .portfolio_loader import normalize_account_type
from .utils import read_csv_records, safe_float, write_csv_records


ACCOUNT_PERFORMANCE_COLUMNS = [
    "account_type",
    "current_value_cad",
    "acquisition_value_cad",
    "unrealized_gain_cad",
    "unrealized_gain_percent",
    "sp500_proxy",
    "benchmark_return_basis",
    "tracking_start_date",
    "portfolio_return_since_tracking",
    "sp500_return_since_tracking",
    "excess_return_vs_sp500",
    "portfolio_twr",
    "sp500_twr",
    "twr_excess_vs_sp500",
    "twr_status",
    "twr_period_count",
    "twr_method",
    "portfolio_xirr",
    "sp500_xirr",
    "xirr_excess_vs_sp500",
    "xirr_status",
    "xirr_flow_count",
    "xirr_method",
    "flow_adjusted_start_date",
    "external_flows_cad",
    "sp500_equivalent_value_cad",
    "value_added_vs_sp500_cad",
    "value_added_vs_sp500_percent",
    "flow_adjusted_status",
    "comparison_status",
    "simple_return_status",
    "preferred_performance_read",
    "preferred_performance_summary",
    "cash_flow_history_status",
    "interpretation",
]

ACCOUNT_PERFORMANCE_HISTORY_COLUMNS = [
    "date",
    "account_type",
    "current_value_cad",
    "acquisition_value_cad",
    "sp500_proxy",
    "sp500_proxy_price",
    "sp500_proxy_return_price",
    "sp500_proxy_return_basis",
]


def build_account_performance_rows(
    portfolio_rows: list[dict[str, Any]],
    market_data: dict[str, dict[str, Any]],
    history_path: str | Path,
    *,
    cash_flow_rows: list[dict[str, Any]] | None = None,
    transaction_rows: list[dict[str, Any]] | None = None,
    as_of_date: str | None = None,
    benchmark_ticker: str = "VFV.TO",
) -> list[dict[str, Any]]:
    """Compare each account with a S&P 500 proxy from the local tracking start.

    This is intentionally approximate. Without complete dated transactions, the
    most honest comparison is: current unrealized performance versus cost basis,
    plus a tracked comparison from the first analysis date onward.
    """

    as_of_date = as_of_date or date.today().isoformat()
    benchmark_payload = market_data.get(benchmark_ticker) or {}
    benchmark_price = _benchmark_return_price(benchmark_payload)
    benchmark_basis = _benchmark_return_basis(benchmark_payload)
    benchmark_price_history = _benchmark_return_price_history(benchmark_payload)
    accounts = _aggregate_accounts(portfolio_rows)
    if accounts:
        accounts["ALL_ACCOUNTS"] = _total_account(accounts)

    history_path = Path(history_path)
    history_rows = read_csv_records(history_path)
    history_rows = _upsert_history_rows(
        history_rows,
        accounts,
        as_of_date,
        benchmark_ticker,
        safe_float(benchmark_payload.get("current_price")),
        benchmark_price,
        benchmark_basis,
    )
    write_csv_records(history_path, history_rows, ACCOUNT_PERFORMANCE_HISTORY_COLUMNS)
    performance_cash_flows = _performance_cash_flow_rows(cash_flow_rows or [], transaction_rows or [])

    rows: list[dict[str, Any]] = []
    for account_type, account in sorted(accounts.items()):
        rows.append(
            _performance_row(
                account_type,
                account,
                history_rows,
                performance_cash_flows,
                as_of_date,
                benchmark_ticker,
                benchmark_price,
                benchmark_basis,
                benchmark_price_history,
            )
        )
    return rows


def _aggregate_accounts(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    accounts: dict[str, dict[str, float]] = {}
    for row in rows:
        current_value = safe_float(row.get("current_value_cad") or row.get("current_value")) or 0.0
        acquisition_value = safe_float(row.get("acquisition_value_cad") or row.get("acquisition_value")) or 0.0
        if current_value <= 0 and acquisition_value <= 0:
            continue
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        bucket = accounts.setdefault(account_type, {"current_value_cad": 0.0, "acquisition_value_cad": 0.0})
        bucket["current_value_cad"] += current_value
        bucket["acquisition_value_cad"] += acquisition_value
    return accounts


def _total_account(accounts: dict[str, dict[str, float]]) -> dict[str, float]:
    return {
        "current_value_cad": sum(row.get("current_value_cad", 0.0) for row in accounts.values()),
        "acquisition_value_cad": sum(row.get("acquisition_value_cad", 0.0) for row in accounts.values()),
    }


def _benchmark_return_price(payload: dict[str, Any]) -> float | None:
    return (
        safe_float(payload.get("total_return_price"))
        or safe_float(payload.get("adjusted_current_price"))
        or safe_float(payload.get("current_price"))
    )


def _benchmark_return_basis(payload: dict[str, Any]) -> str:
    if safe_float(payload.get("total_return_price")) is not None:
        return str(payload.get("total_return_basis") or "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY")
    if safe_float(payload.get("adjusted_current_price")) is not None:
        return "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"
    return "PRICE_CLOSE"


def _benchmark_return_price_history(payload: dict[str, Any]) -> dict[str, float]:
    raw = payload.get("total_return_price_history")
    if not isinstance(raw, dict):
        return {}
    return {str(key)[:10]: value for key, value in ((k, safe_float(v)) for k, v in raw.items()) if value is not None and value > 0}


def _benchmark_price_for_date(
    row_date: str,
    history_rows: list[dict[str, Any]],
    benchmark_price_history: dict[str, float],
    *,
    account_type: str | None = None,
) -> float | None:
    history_price = _price_from_benchmark_history(benchmark_price_history, row_date)
    if history_price not in {None, 0.0}:
        return history_price
    matching_rows = [
        row
        for row in history_rows
        if str(row.get("date") or "") == row_date
        and (account_type is None or str(row.get("account_type") or "") == account_type)
    ]
    matching_rows.extend(row for row in history_rows if str(row.get("date") or "") == row_date and row not in matching_rows)
    for row in matching_rows:
        price = safe_float(row.get("sp500_proxy_return_price"))
        if price in {None, 0.0}:
            price = safe_float(row.get("sp500_proxy_price"))
        if price not in {None, 0.0}:
            return price
    return None


def _price_from_benchmark_history(price_history: dict[str, float], row_date: str) -> float | None:
    if not price_history or not row_date:
        return None
    date_key = row_date[:10]
    direct = safe_float(price_history.get(date_key))
    if direct not in {None, 0.0}:
        return direct
    earlier_dates = [key for key in price_history if key <= date_key]
    if earlier_dates:
        return safe_float(price_history[max(earlier_dates)])
    later_dates = [key for key in price_history if key > date_key]
    if later_dates:
        return safe_float(price_history[min(later_dates)])
    return None


def _upsert_history_rows(
    history_rows: list[dict[str, Any]],
    accounts: dict[str, dict[str, float]],
    as_of_date: str,
    benchmark_ticker: str,
    benchmark_raw_price: float | None,
    benchmark_return_price: float | None,
    benchmark_return_basis: str,
) -> list[dict[str, Any]]:
    kept = [
        row
        for row in history_rows
        if str(row.get("date") or "") != as_of_date
    ]
    for account_type, account in accounts.items():
        kept.append(
            {
                "date": as_of_date,
                "account_type": account_type,
                "current_value_cad": round(account.get("current_value_cad", 0.0), 2),
                "acquisition_value_cad": round(account.get("acquisition_value_cad", 0.0), 2),
                "sp500_proxy": benchmark_ticker,
                "sp500_proxy_price": round(benchmark_raw_price, 4) if benchmark_raw_price is not None else "",
                "sp500_proxy_return_price": round(benchmark_return_price, 4) if benchmark_return_price is not None else "",
                "sp500_proxy_return_basis": benchmark_return_basis,
            }
        )
    return sorted(kept, key=lambda row: (str(row.get("account_type") or ""), str(row.get("date") or "")))


def _performance_row(
    account_type: str,
    account: dict[str, float],
    history_rows: list[dict[str, Any]],
    cash_flow_rows: list[dict[str, Any]],
    as_of_date: str,
    benchmark_ticker: str,
    benchmark_price: float | None,
    benchmark_basis: str,
    benchmark_price_history: dict[str, float],
) -> dict[str, Any]:
    current_value = account.get("current_value_cad", 0.0)
    acquisition_value = account.get("acquisition_value_cad", 0.0)
    unrealized_gain = current_value - acquisition_value if acquisition_value > 0 else None
    unrealized_gain_percent = (unrealized_gain / acquisition_value) if unrealized_gain is not None and acquisition_value > 0 else None
    account_history = [
        row
        for row in history_rows
        if str(row.get("account_type") or "") == account_type and safe_float(row.get("current_value_cad")) is not None
    ]
    baseline = _first_usable_baseline(account_history, as_of_date)
    portfolio_return = None
    benchmark_return = None
    excess_return = None
    flow_adjusted = {}
    tracking_start_date = ""
    status = "BASELINE_CREATED"
    interpretation = (
        "Base de comparaison créée. Les prochaines analyses pourront comparer ce compte au S&P 500 depuis cette date."
    )

    if baseline:
        tracking_start_date = str(baseline.get("date") or "")
        baseline_value = safe_float(baseline.get("current_value_cad"))
        baseline_cost = safe_float(baseline.get("acquisition_value_cad"))
        baseline_benchmark_price = _benchmark_price_for_date(
            tracking_start_date,
            history_rows,
            benchmark_price_history,
            account_type=account_type,
        )
        if baseline_value and baseline_value > 0:
            portfolio_return = (current_value / baseline_value) - 1
        if baseline_benchmark_price and benchmark_price and baseline_benchmark_price > 0:
            benchmark_return = (benchmark_price / baseline_benchmark_price) - 1
        if portfolio_return is not None and benchmark_return is not None:
            excess_return = portfolio_return - benchmark_return
            status = _comparison_status(portfolio_return, benchmark_return, acquisition_value, baseline_cost)
            interpretation = _interpretation(status, excess_return)
        else:
            status = "BENCHMARK_UNAVAILABLE"
            interpretation = "Comparaison S&P 500 indisponible: prix VFV.TO manquant dans l’historique local."
        flow_adjusted = _flow_adjusted_comparison(
            account_type,
            current_value,
            baseline,
            cash_flow_rows,
            history_rows,
            as_of_date,
            benchmark_price,
            benchmark_price_history,
        )
        xirr_comparison = _xirr_comparison(
            account_type,
            current_value,
            baseline,
            cash_flow_rows,
            history_rows,
            as_of_date,
            benchmark_price,
            benchmark_price_history,
        )
        twr_comparison = _twr_comparison(
            account_type,
            baseline,
            cash_flow_rows,
            history_rows,
            as_of_date,
            benchmark_price_history,
        )
    else:
        xirr_comparison = {
            "portfolio_xirr": "",
            "sp500_xirr": "",
            "xirr_excess_vs_sp500": "",
            "xirr_status": "BASELINE_CREATED",
            "xirr_flow_count": 0,
            "xirr_method": "En attente d’une deuxième analyse locale.",
        }
        twr_comparison = _empty_twr("BASELINE_CREATED")

    simple_return_status = _simple_return_status(status, flow_adjusted)
    preferred_performance_read = _preferred_performance_read(
        simple_return_status,
        flow_adjusted,
        xirr_comparison,
        twr_comparison,
    )
    preferred_performance_summary = _preferred_performance_summary(
        preferred_performance_read,
        simple_return_status,
        flow_adjusted,
        xirr_comparison,
        twr_comparison,
        status,
    )
    cash_flow_history_status = _cash_flow_history_status(xirr_comparison, twr_comparison)

    return {
        "account_type": account_type,
        "current_value_cad": round(current_value, 2),
        "acquisition_value_cad": round(acquisition_value, 2) if acquisition_value > 0 else "",
        "unrealized_gain_cad": round(unrealized_gain, 2) if unrealized_gain is not None else "",
        "unrealized_gain_percent": round(unrealized_gain_percent, 6) if unrealized_gain_percent is not None else "",
        "sp500_proxy": benchmark_ticker,
        "benchmark_return_basis": benchmark_basis,
        "tracking_start_date": tracking_start_date,
        "portfolio_return_since_tracking": round(portfolio_return, 6) if portfolio_return is not None else "",
        "sp500_return_since_tracking": round(benchmark_return, 6) if benchmark_return is not None else "",
        "excess_return_vs_sp500": round(excess_return, 6) if excess_return is not None else "",
        "portfolio_twr": twr_comparison.get("portfolio_twr", ""),
        "sp500_twr": twr_comparison.get("sp500_twr", ""),
        "twr_excess_vs_sp500": twr_comparison.get("twr_excess_vs_sp500", ""),
        "twr_status": twr_comparison.get("twr_status", ""),
        "twr_period_count": twr_comparison.get("twr_period_count", ""),
        "twr_method": twr_comparison.get("twr_method", ""),
        "portfolio_xirr": xirr_comparison.get("portfolio_xirr", ""),
        "sp500_xirr": xirr_comparison.get("sp500_xirr", ""),
        "xirr_excess_vs_sp500": xirr_comparison.get("xirr_excess_vs_sp500", ""),
        "xirr_status": xirr_comparison.get("xirr_status", ""),
        "xirr_flow_count": xirr_comparison.get("xirr_flow_count", ""),
        "xirr_method": xirr_comparison.get("xirr_method", ""),
        "flow_adjusted_start_date": flow_adjusted.get("flow_adjusted_start_date", ""),
        "external_flows_cad": flow_adjusted.get("external_flows_cad", ""),
        "sp500_equivalent_value_cad": flow_adjusted.get("sp500_equivalent_value_cad", ""),
        "value_added_vs_sp500_cad": flow_adjusted.get("value_added_vs_sp500_cad", ""),
        "value_added_vs_sp500_percent": flow_adjusted.get("value_added_vs_sp500_percent", ""),
        "flow_adjusted_status": flow_adjusted.get("flow_adjusted_status", "BASELINE_CREATED"),
        "comparison_status": status,
        "simple_return_status": simple_return_status,
        "preferred_performance_read": preferred_performance_read,
        "preferred_performance_summary": preferred_performance_summary,
        "cash_flow_history_status": cash_flow_history_status,
        "interpretation": interpretation,
    }


def _performance_cash_flow_rows(
    inferred_rows: list[dict[str, Any]],
    transaction_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explicit_rows: list[dict[str, Any]] = []
    explicit_account_dates: set[tuple[str, str]] = set()
    for row in transaction_rows:
        flow = safe_float(row.get("net_contribution_cad"))
        if flow in {None, 0.0}:
            continue
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        row_date = str(row.get("date") or "").strip()
        if not row_date:
            continue
        explicit_account_dates.add((account_type, row_date))
        explicit_rows.append(
            {
                "date": row_date,
                "account_type": account_type,
                "external_flow_cad": flow,
                "sp500_proxy_price_at_flow": row.get("sp500_proxy_price_at_flow", ""),
                "performance_flow_source": "EXPLICIT_PORTFOLIO_TRANSACTION",
            }
        )

    fallback_rows: list[dict[str, Any]] = []
    for row in inferred_rows:
        flow = safe_float(row.get("external_flow_cad"))
        if flow in {None, 0.0}:
            continue
        account_type = normalize_account_type(row.get("account_type")) or "UNKNOWN"
        row_date = str(row.get("date") or "").strip()
        if not row_date or (account_type, row_date) in explicit_account_dates:
            continue
        fallback_rows.append({**row, "account_type": account_type, "performance_flow_source": "AUTO_INFERRED_FROM_PORTFOLIO"})
    return sorted(explicit_rows + fallback_rows, key=lambda row: (str(row.get("date") or ""), str(row.get("account_type") or "")))


def _flow_adjusted_comparison(
    account_type: str,
    current_value: float,
    baseline: dict[str, Any],
    cash_flow_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    as_of_date: str,
    current_benchmark_price: float | None,
    benchmark_price_history: dict[str, float],
) -> dict[str, Any]:
    baseline_date = str(baseline.get("date") or "")
    baseline_value = safe_float(baseline.get("current_value_cad"))
    baseline_benchmark_price = _benchmark_price_for_date(
        baseline_date,
        history_rows,
        benchmark_price_history,
        account_type=account_type,
    )
    if not baseline_date or not baseline_value or not baseline_benchmark_price or not current_benchmark_price:
        return {
            "flow_adjusted_start_date": baseline_date,
            "flow_adjusted_status": "BENCHMARK_UNAVAILABLE",
        }

    relevant_flows = _cash_flows_for_account(cash_flow_rows, account_type, baseline_date, as_of_date)
    usable_flows = [row for row in relevant_flows if _flow_is_usable(row, history_rows, benchmark_price_history)]
    missing_benchmark_count = len(relevant_flows) - len(usable_flows)
    benchmark_value = baseline_value * (current_benchmark_price / baseline_benchmark_price)
    external_flows = 0.0
    for row in usable_flows:
        flow = safe_float(row.get("external_flow_cad")) or 0.0
        flow_benchmark_price = _flow_benchmark_price(row, history_rows, benchmark_price_history)
        if flow_benchmark_price and flow_benchmark_price > 0:
            benchmark_value += flow * (current_benchmark_price / flow_benchmark_price)
            external_flows += flow
    value_added = current_value - benchmark_value
    value_added_pct = value_added / benchmark_value if benchmark_value > 0 else None
    status = _flow_adjusted_status(value_added_pct, missing_benchmark_count, relevant_flows)
    return {
        "flow_adjusted_start_date": baseline_date,
        "external_flows_cad": round(external_flows, 2),
        "sp500_equivalent_value_cad": round(benchmark_value, 2),
        "value_added_vs_sp500_cad": round(value_added, 2),
        "value_added_vs_sp500_percent": round(value_added_pct, 6) if value_added_pct is not None else "",
        "flow_adjusted_status": status,
    }


def _xirr_comparison(
    account_type: str,
    current_value: float,
    baseline: dict[str, Any],
    cash_flow_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    as_of_date: str,
    current_benchmark_price: float | None,
    benchmark_price_history: dict[str, float],
) -> dict[str, Any]:
    baseline_date = str(baseline.get("date") or "")
    baseline_value = safe_float(baseline.get("current_value_cad"))
    baseline_benchmark_price = _benchmark_price_for_date(
        baseline_date,
        history_rows,
        benchmark_price_history,
        account_type=account_type,
    )
    start_date = _parse_date(baseline_date)
    end_date = _parse_date(as_of_date)
    if not start_date or not end_date or not baseline_value or baseline_value <= 0 or current_value <= 0:
        return _empty_xirr("XIRR_UNAVAILABLE_BASELINE")
    elapsed_days = (end_date - start_date).days
    if elapsed_days < 7:
        return _empty_xirr("XIRR_WAITING_MORE_HISTORY")

    relevant_flows = _cash_flows_for_account(cash_flow_rows, account_type, baseline_date, as_of_date)
    if _has_inferred_cash_flow_timing(relevant_flows):
        return _empty_xirr("INSUFFICIENT_CASH_FLOW_HISTORY")
    portfolio_cashflows: list[tuple[date, float]] = [(start_date, -baseline_value)]
    for row in relevant_flows:
        flow_date = _parse_date(str(row.get("date") or ""))
        flow = safe_float(row.get("external_flow_cad"))
        if not flow_date or flow in {None, 0.0}:
            continue
        portfolio_cashflows.append((flow_date, -(flow or 0.0)))
    portfolio_cashflows.append((end_date, current_value))
    portfolio_xirr = _xirr(portfolio_cashflows)

    missing_benchmark_count = 0
    benchmark_xirr = None
    xirr_excess = None
    benchmark_value = None
    if baseline_benchmark_price and current_benchmark_price and baseline_benchmark_price > 0 and current_benchmark_price > 0:
        benchmark_value = baseline_value * (current_benchmark_price / baseline_benchmark_price)
        benchmark_cashflows: list[tuple[date, float]] = [(start_date, -baseline_value)]
        for row in relevant_flows:
            flow_date = _parse_date(str(row.get("date") or ""))
            flow = safe_float(row.get("external_flow_cad"))
            if not flow_date or flow in {None, 0.0}:
                continue
            flow_benchmark_price = _flow_benchmark_price(row, history_rows, benchmark_price_history)
            if not flow_benchmark_price or flow_benchmark_price <= 0:
                missing_benchmark_count += 1
                continue
            benchmark_value += (flow or 0.0) * (current_benchmark_price / flow_benchmark_price)
            benchmark_cashflows.append((flow_date, -(flow or 0.0)))
        if not missing_benchmark_count:
            benchmark_cashflows.append((end_date, benchmark_value))
            benchmark_xirr = _xirr(benchmark_cashflows)
            if portfolio_xirr is not None and benchmark_xirr is not None:
                xirr_excess = portfolio_xirr - benchmark_xirr
    else:
        missing_benchmark_count = len(relevant_flows)

    status = _xirr_status(
        portfolio_xirr,
        benchmark_xirr,
        xirr_excess,
        missing_benchmark_count,
        relevant_flows,
        elapsed_days,
    )
    method = _xirr_method_text(relevant_flows, missing_benchmark_count)
    return {
        "portfolio_xirr": round(portfolio_xirr, 6) if portfolio_xirr is not None else "",
        "sp500_xirr": round(benchmark_xirr, 6) if benchmark_xirr is not None else "",
        "xirr_excess_vs_sp500": round(xirr_excess, 6) if xirr_excess is not None else "",
        "xirr_status": status,
        "xirr_flow_count": len(relevant_flows),
        "xirr_method": method,
    }


def _cash_flows_for_account(
    rows: list[dict[str, Any]],
    account_type: str,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for row in rows:
        date = str(row.get("date") or "")
        if not (start_date < date <= end_date):
            continue
        if safe_float(row.get("external_flow_cad")) in {None, 0.0}:
            continue
        row_account = str(row.get("account_type") or "")
        if account_type == "ALL_ACCOUNTS" or row_account == account_type:
            output.append(row)
    return output

def _flow_is_usable(
    row: dict[str, Any],
    history_rows: list[dict[str, Any]],
    benchmark_price_history: dict[str, float] | None = None,
) -> bool:
    return _flow_benchmark_price(row, history_rows, benchmark_price_history or {}) not in {None, 0.0}


def _flow_benchmark_price(
    row: dict[str, Any],
    history_rows: list[dict[str, Any]],
    benchmark_price_history: dict[str, float] | None = None,
) -> float | None:
    row_date = str(row.get("date") or "")
    if not row_date:
        return None
    history_price = _price_from_benchmark_history(benchmark_price_history or {}, row_date)
    if history_price not in {None, 0.0}:
        return history_price
    direct = safe_float(row.get("sp500_proxy_price_at_flow"))
    if direct not in {None, 0.0}:
        return direct
    for history_row in history_rows:
        if str(history_row.get("date") or "") == row_date:
            price = safe_float(history_row.get("sp500_proxy_return_price"))
            if price in {None, 0.0}:
                price = safe_float(history_row.get("sp500_proxy_price"))
            if price not in {None, 0.0}:
                return price
    return None


def _twr_comparison(
    account_type: str,
    baseline: dict[str, Any],
    cash_flow_rows: list[dict[str, Any]],
    history_rows: list[dict[str, Any]],
    as_of_date: str,
    benchmark_price_history: dict[str, float],
) -> dict[str, Any]:
    baseline_date = str(baseline.get("date") or "")
    points = _twr_history_points(account_type, history_rows, baseline_date, as_of_date)
    if len(points) < 2:
        return _empty_twr("TWR_WAITING_MORE_HISTORY")

    baseline_flows = _cash_flows_for_account(cash_flow_rows, account_type, baseline_date, as_of_date)
    if _has_inferred_cash_flow_timing(baseline_flows):
        return _empty_twr("INSUFFICIENT_CASH_FLOW_HISTORY")

    portfolio_growth = 1.0
    benchmark_growth = 1.0
    period_count = 0
    flow_count = 0
    explicit_flow_count = 0
    inferred_flow_count = 0
    missing_benchmark_count = 0
    unusable_period_count = 0

    for start, end in zip(points, points[1:]):
        start_date = str(start.get("date") or "")
        end_date = str(end.get("date") or "")
        start_value = safe_float(start.get("current_value_cad"))
        end_value = safe_float(end.get("current_value_cad"))
        start_benchmark_price = _benchmark_price_for_date(
            start_date,
            history_rows,
            benchmark_price_history,
            account_type=account_type,
        )
        end_benchmark_price = _benchmark_price_for_date(
            end_date,
            history_rows,
            benchmark_price_history,
            account_type=account_type,
        )
        if not start_date or not end_date or not start_value or start_value <= 0 or end_value is None:
            unusable_period_count += 1
            continue

        period_flows = _cash_flows_for_account(cash_flow_rows, account_type, start_date, end_date)
        period_flow_total = sum(safe_float(row.get("external_flow_cad")) or 0.0 for row in period_flows)
        flow_count += len(period_flows)
        explicit_flow_count += sum(
            1 for row in period_flows if row.get("performance_flow_source") == "EXPLICIT_PORTFOLIO_TRANSACTION"
        )
        inferred_flow_count += sum(
            1 for row in period_flows if row.get("performance_flow_source") == "AUTO_INFERRED_FROM_PORTFOLIO"
        )

        adjusted_end_value = end_value - period_flow_total
        period_return = (adjusted_end_value / start_value) - 1
        if period_return <= -1:
            unusable_period_count += 1
            continue
        portfolio_growth *= 1 + period_return

        if start_benchmark_price and end_benchmark_price and start_benchmark_price > 0 and end_benchmark_price > 0:
            benchmark_growth *= end_benchmark_price / start_benchmark_price
        else:
            missing_benchmark_count += 1
        period_count += 1

    if period_count == 0:
        return _empty_twr("TWR_WAITING_MORE_HISTORY")

    portfolio_twr = portfolio_growth - 1
    benchmark_twr = None if missing_benchmark_count else benchmark_growth - 1
    twr_excess = portfolio_twr - benchmark_twr if benchmark_twr is not None else None
    status = _twr_status(twr_excess, missing_benchmark_count, unusable_period_count, flow_count)
    method = _twr_method_text(period_count, flow_count, explicit_flow_count, inferred_flow_count, unusable_period_count)
    return {
        "portfolio_twr": round(portfolio_twr, 6),
        "sp500_twr": round(benchmark_twr, 6) if benchmark_twr is not None else "",
        "twr_excess_vs_sp500": round(twr_excess, 6) if twr_excess is not None else "",
        "twr_status": status,
        "twr_period_count": period_count,
        "twr_method": method,
    }


def _twr_history_points(
    account_type: str,
    history_rows: list[dict[str, Any]],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        row_date = str(row.get("date") or "")
        if str(row.get("account_type") or "") != account_type or not (start_date <= row_date <= end_date):
            continue
        if safe_float(row.get("current_value_cad")) is None:
            continue
        by_date[row_date] = row
    return [by_date[row_date] for row_date in sorted(by_date)]


def _empty_twr(status: str) -> dict[str, Any]:
    return {
        "portfolio_twr": "",
        "sp500_twr": "",
        "twr_excess_vs_sp500": "",
        "twr_status": status,
        "twr_period_count": 0,
        "twr_method": (
            "TWR indisponible: l’historique contient un flux inféré sans date de transaction suffisamment fiable."
            if status == "INSUFFICIENT_CASH_FLOW_HISTORY"
            else "TWR non disponible pour l’instant."
        ),
    }


def _twr_status(
    twr_excess: float | None,
    missing_benchmark_count: int,
    unusable_period_count: int,
    flow_count: int,
) -> str:
    if unusable_period_count:
        return "TWR_APPROXIMATE_UNUSABLE_PERIODS_SKIPPED"
    if missing_benchmark_count:
        return "TWR_PORTFOLIO_ONLY_BENCHMARK_MISSING_PRICES"
    if twr_excess is None:
        return "TWR_BENCHMARK_UNAVAILABLE"
    prefix = "TWR_FLOW_ADJUSTED" if flow_count else "TWR_NO_EXTERNAL_FLOWS"
    if twr_excess >= 0.02:
        return f"{prefix}_AHEAD_OF_SP500"
    if twr_excess <= -0.02:
        return f"{prefix}_BEHIND_SP500"
    return f"{prefix}_SIMILAR_TO_SP500"


def _twr_method_text(
    period_count: int,
    flow_count: int,
    explicit_flow_count: int,
    inferred_flow_count: int,
    unusable_period_count: int,
) -> str:
    parts = [f"TWR approximatif chaîné sur {period_count} période(s) entre snapshots locaux"]
    if flow_count:
        parts.append("neutralise les cotisations/retraits détectés")
    else:
        parts.append("aucun flux externe détecté entre les snapshots")
    if explicit_flow_count:
        parts.append(f"{explicit_flow_count} flux réel(s) venant de portfolio_transactions.csv")
    if inferred_flow_count:
        parts.append(f"{inferred_flow_count} flux déduit(s) automatiquement de portfolio.csv")
    if unusable_period_count:
        parts.append(f"{unusable_period_count} période(s) ignorée(s) faute de données utilisables")
    return "; ".join(parts) + "."


def _empty_xirr(status: str) -> dict[str, Any]:
    return {
        "portfolio_xirr": "",
        "sp500_xirr": "",
        "xirr_excess_vs_sp500": "",
        "xirr_status": status,
        "xirr_flow_count": 0,
        "xirr_method": (
            "XIRR indisponible: l’historique contient un flux inféré sans date de transaction suffisamment fiable."
            if status == "INSUFFICIENT_CASH_FLOW_HISTORY"
            else "XIRR non disponible pour l’instant."
        ),
    }


def _has_inferred_cash_flow_timing(rows: list[dict[str, Any]]) -> bool:
    return any(
        str(row.get("performance_flow_source") or "") == "AUTO_INFERRED_FROM_PORTFOLIO"
        for row in rows
    )


def _cash_flow_history_status(
    xirr_comparison: dict[str, Any],
    twr_comparison: dict[str, Any],
) -> str:
    statuses = {
        str(xirr_comparison.get("xirr_status") or ""),
        str(twr_comparison.get("twr_status") or ""),
    }
    if "INSUFFICIENT_CASH_FLOW_HISTORY" in statuses:
        return "INSUFFICIENT_CASH_FLOW_HISTORY"
    if any("FLOW_ADJUSTED" in status for status in statuses):
        return "EXPLICIT_DATED_FLOWS_USED"
    if statuses <= {"BASELINE_CREATED", "TWR_WAITING_MORE_HISTORY", "XIRR_WAITING_MORE_HISTORY", ""}:
        return "WAITING_FOR_HISTORY"
    return "NO_EXTERNAL_FLOWS_DETECTED"


def _xirr_status(
    portfolio_xirr: float | None,
    benchmark_xirr: float | None,
    xirr_excess: float | None,
    missing_benchmark_count: int,
    relevant_flows: list[dict[str, Any]],
    elapsed_days: int,
) -> str:
    if portfolio_xirr is None:
        return "XIRR_UNAVAILABLE"
    if missing_benchmark_count:
        return "XIRR_PORTFOLIO_ONLY_BENCHMARK_MISSING_PRICES"
    if benchmark_xirr is None or xirr_excess is None:
        return "XIRR_BENCHMARK_UNAVAILABLE"
    if elapsed_days < 90:
        return "XIRR_AVAILABLE_SHORT_HISTORY"
    prefix = "XIRR_NO_EXTERNAL_FLOWS" if not relevant_flows else "XIRR_FLOW_ADJUSTED"
    if xirr_excess >= 0.02:
        return f"{prefix}_AHEAD_OF_SP500"
    if xirr_excess <= -0.02:
        return f"{prefix}_BEHIND_SP500"
    return f"{prefix}_SIMILAR_TO_SP500"


def _xirr_method_text(relevant_flows: list[dict[str, Any]], missing_benchmark_count: int) -> str:
    if not relevant_flows:
        return "XIRR annualisé depuis la première analyse locale, sans flux externe détecté depuis la base."
    explicit_count = sum(1 for row in relevant_flows if row.get("performance_flow_source") == "EXPLICIT_PORTFOLIO_TRANSACTION")
    inferred_count = len(relevant_flows) - explicit_count
    parts = ["XIRR annualisé avec flux datés"]
    if explicit_count:
        parts.append(f"{explicit_count} flux réel(s) provenant de portfolio_transactions.csv")
    if inferred_count:
        parts.append(f"{inferred_count} flux déduit(s) automatiquement de portfolio.csv")
    if missing_benchmark_count:
        parts.append(f"{missing_benchmark_count} flux sans prix VFV exact pour le benchmark")
    return "; ".join(parts) + "."


def _xirr(cashflows: list[tuple[date, float]]) -> float | None:
    clean = [(flow_date, amount) for flow_date, amount in cashflows if amount not in {0, 0.0}]
    if len(clean) < 2 or not any(amount > 0 for _, amount in clean) or not any(amount < 0 for _, amount in clean):
        return None
    start = min(flow_date for flow_date, _ in clean)
    if max(flow_date for flow_date, _ in clean) <= start:
        return None

    def npv(rate: float) -> float:
        total = 0.0
        for flow_date, amount in clean:
            years = (flow_date - start).days / 365.25
            total += amount / ((1.0 + rate) ** years)
        return total

    low = -0.9999
    high = 1.0
    low_value = npv(low)
    high_value = npv(high)
    for _ in range(60):
        if low_value == 0:
            return low
        if high_value == 0:
            return high
        if low_value * high_value < 0:
            break
        high *= 2.0
        if high > 1_000_000:
            return None
        high_value = npv(high)
    else:
        return None

    for _ in range(120):
        mid = (low + high) / 2.0
        mid_value = npv(mid)
        if abs(mid_value) < 1e-7:
            return mid
        if low_value * mid_value <= 0:
            high = mid
            high_value = mid_value
        else:
            low = mid
            low_value = mid_value
    return (low + high) / 2.0


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def _flow_adjusted_status(
    value_added_pct: float | None,
    missing_benchmark_count: int,
    relevant_flows: list[dict[str, Any]],
) -> str:
    if missing_benchmark_count:
        return "APPROXIMATE_MISSING_FLOW_BENCHMARK"
    if not relevant_flows:
        return "NO_EXTERNAL_FLOWS_SINCE_BASELINE"
    if value_added_pct is None:
        return "NOT_AVAILABLE"
    if value_added_pct >= 0.02:
        return "AHEAD_OF_SP500_FLOW_ADJUSTED"
    if value_added_pct <= -0.02:
        return "BEHIND_SP500_FLOW_ADJUSTED"
    return "SIMILAR_TO_SP500_FLOW_ADJUSTED"


def _simple_return_status(status: str, flow_adjusted: dict[str, Any]) -> str:
    flow_status = str(flow_adjusted.get("flow_adjusted_status") or "")
    external_flows = safe_float(flow_adjusted.get("external_flows_cad")) or 0.0
    if status == "BASELINE_CREATED":
        return "BASELINE_CREATED"
    if status == "BENCHMARK_UNAVAILABLE":
        return "BENCHMARK_UNAVAILABLE"
    if status == "APPROXIMATE_CONTRIBUTIONS_CHANGED" or abs(external_flows) > 0.01:
        return "FLOW_DISTORTED_BY_CONTRIBUTIONS"
    if flow_status and flow_status not in {"NO_EXTERNAL_FLOWS_SINCE_BASELINE", "BASELINE_CREATED"}:
        return "FLOW_DISTORTED_BY_CONTRIBUTIONS"
    return "CLEAN_NO_EXTERNAL_FLOW"


def _preferred_performance_read(
    simple_return_status: str,
    flow_adjusted: dict[str, Any],
    xirr_comparison: dict[str, Any],
    twr_comparison: dict[str, Any],
) -> str:
    xirr_status = str(xirr_comparison.get("xirr_status") or "")
    twr_status = str(twr_comparison.get("twr_status") or "")
    flow_status = str(flow_adjusted.get("flow_adjusted_status") or "")
    external_flows = safe_float(flow_adjusted.get("external_flows_cad")) or 0.0
    flow_value = safe_float(flow_adjusted.get("value_added_vs_sp500_cad"))
    if (
        simple_return_status == "FLOW_DISTORTED_BY_CONTRIBUTIONS"
        and "FLOW_ADJUSTED" not in twr_status
    ):
        return "WAIT_FOR_TRANSACTION_DETAILS"
    if twr_status and twr_status not in {
        "BASELINE_CREATED",
        "TWR_WAITING_MORE_HISTORY",
        "TWR_BENCHMARK_UNAVAILABLE",
        "TWR_PORTFOLIO_ONLY_BENCHMARK_MISSING_PRICES",
    }:
        return "TWR_EXCESS"
    if (
        simple_return_status == "FLOW_DISTORTED_BY_CONTRIBUTIONS"
        and flow_value is not None
        and (abs(external_flows) > 0.01 or flow_status not in {"", "NO_EXTERNAL_FLOWS_SINCE_BASELINE"})
    ):
        return "FLOW_ADJUSTED_VALUE_ADDED"
    if simple_return_status == "FLOW_DISTORTED_BY_CONTRIBUTIONS":
        return "WAIT_FOR_TRANSACTION_DETAILS"
    if xirr_status and xirr_status not in {
        "BASELINE_CREATED",
        "XIRR_WAITING_MORE_HISTORY",
        "XIRR_AVAILABLE_SHORT_HISTORY",
        "XIRR_UNAVAILABLE",
        "XIRR_UNAVAILABLE_BASELINE",
        "XIRR_BENCHMARK_UNAVAILABLE",
        "XIRR_PORTFOLIO_ONLY_BENCHMARK_MISSING_PRICES",
    }:
        return "XIRR_EXCESS"
    if simple_return_status == "CLEAN_NO_EXTERNAL_FLOW":
        return "SIMPLE_RETURN"
    return "WAIT_FOR_MORE_HISTORY"


def _preferred_performance_summary(
    preferred_read: str,
    simple_return_status: str,
    flow_adjusted: dict[str, Any],
    xirr_comparison: dict[str, Any],
    twr_comparison: dict[str, Any],
    comparison_status: str,
) -> str:
    if preferred_read == "TWR_EXCESS":
        twr_excess = safe_float(twr_comparison.get("twr_excess_vs_sp500"))
        if twr_excess is None:
            return "Lecture recommandée: TWR disponible, mais l’écart vs VFV.TO n’est pas calculable."
        direction = "devant" if twr_excess >= 0 else "derrière"
        flow_note = ""
        if "FLOW_ADJUSTED" in str(twr_comparison.get("twr_status") or ""):
            flow_note = " après neutralisation des cotisations/retraits détectés"
        return (
            f"Lecture recommandée: TWR, la stratégie du compte est {direction} VFV.TO "
            f"d’environ {abs(twr_excess) * 100:.1f} points depuis le début du suivi{flow_note}."
        )
    if preferred_read == "FLOW_ADJUSTED_VALUE_ADDED":
        value_added = safe_float(flow_adjusted.get("value_added_vs_sp500_cad"))
        value_added_pct = safe_float(flow_adjusted.get("value_added_vs_sp500_percent"))
        status = str(flow_adjusted.get("flow_adjusted_status") or "")
        direction = "devant"
        if status == "BEHIND_SP500_FLOW_ADJUSTED":
            direction = "derrière"
        elif status == "SIMILAR_TO_SP500_FLOW_ADJUSTED":
            direction = "près de"
        pct_text = f" ({value_added_pct * 100:.1f} %)" if value_added_pct is not None else ""
        value_text = f"{abs(value_added):.2f} $" if value_added is not None else "N/D"
        return (
            f"Lecture recommandée: ajusté des cotisations/retraits, le compte est {direction} VFV.TO "
            f"de {value_text}{pct_text}. Le rendement simple est masqué parce qu’il confond flux et performance."
        )
    if preferred_read == "XIRR_EXCESS":
        xirr_excess = safe_float(xirr_comparison.get("xirr_excess_vs_sp500"))
        if xirr_excess is None:
            return "Lecture recommandée: XIRR disponible, mais l’écart vs VFV.TO n’est pas calculable."
        direction = "devant" if xirr_excess >= 0 else "derrière"
        return f"Lecture recommandée: XIRR, le compte est {direction} VFV.TO d’environ {abs(xirr_excess) * 100:.1f} points annualisés."
    if preferred_read == "SIMPLE_RETURN":
        if comparison_status == "AHEAD_OF_SP500":
            return "Lecture recommandée: rendement simple utilisable, le compte est devant VFV.TO depuis le début du suivi local."
        if comparison_status == "BEHIND_SP500":
            return "Lecture recommandée: rendement simple utilisable, le compte est derrière VFV.TO depuis le début du suivi local."
        return "Lecture recommandée: rendement simple utilisable, le compte évolue près de VFV.TO depuis le début du suivi local."
    if simple_return_status == "BASELINE_CREATED":
        return "Lecture recommandée: base créée; attendre une prochaine analyse pour comparer."
    if preferred_read == "WAIT_FOR_TRANSACTION_DETAILS":
        return (
            "Lecture recommandée: rendement simple masqué, car des changements de coût/positions suggèrent des flux. "
            "Ajouter ou laisser détecter des transactions datées permettra une comparaison plus fidèle."
        )
    return "Lecture recommandée: attendre plus d’historique ou des transactions mieux datées avant de conclure."


def _first_usable_baseline(account_history: list[dict[str, Any]], as_of_date: str) -> dict[str, Any] | None:
    earlier = [row for row in account_history if str(row.get("date") or "") < as_of_date]
    if not earlier:
        return None
    return sorted(earlier, key=lambda row: str(row.get("date") or ""))[0]


def _comparison_status(
    portfolio_return: float,
    benchmark_return: float,
    current_cost: float,
    baseline_cost: float | None,
) -> str:
    if baseline_cost and baseline_cost > 0:
        cost_change = abs(current_cost - baseline_cost) / baseline_cost
        if cost_change > 0.02:
            return "APPROXIMATE_CONTRIBUTIONS_CHANGED"
    excess = portfolio_return - benchmark_return
    if excess >= 0.02:
        return "AHEAD_OF_SP500"
    if excess <= -0.02:
        return "BEHIND_SP500"
    return "SIMILAR_TO_SP500"


def _interpretation(status: str, excess_return: float) -> str:
    if status == "APPROXIMATE_CONTRIBUTIONS_CHANGED":
        return (
            "Comparaison approximative: le compte a probablement reçu des cotisations, achats ou ventes depuis la base. "
            "Une mesure exacte demanderait les transactions datées et les prix historiques du benchmark."
        )
    if status == "AHEAD_OF_SP500":
        return f"Le compte est devant le proxy S&P 500 depuis le début du suivi local d’environ {excess_return * 100:.1f} points."
    if status == "BEHIND_SP500":
        return f"Le compte est derrière le proxy S&P 500 depuis le début du suivi local d’environ {abs(excess_return) * 100:.1f} points."
    return "Le compte évolue près du proxy S&P 500 depuis le début du suivi local."
