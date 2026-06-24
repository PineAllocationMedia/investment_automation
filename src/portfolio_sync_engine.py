from __future__ import annotations

from pathlib import Path
from typing import Any

from .account_performance_engine import ACCOUNT_PERFORMANCE_COLUMNS, build_account_performance_rows
from .portfolio_change_tracker import (
    PORTFOLIO_CHANGE_COLUMNS,
    PORTFOLIO_CHANGE_SUMMARY_COLUMNS,
    update_portfolio_change_history,
)
from .portfolio_inferred_transactions import INFERRED_TRANSACTION_COLUMNS, update_inferred_transactions_from_changes
from .portfolio_transactions import (
    PORTFOLIO_TRANSACTION_REPORT_COLUMNS,
    PORTFOLIO_TRANSACTION_SUMMARY_COLUMNS,
    summarize_portfolio_transactions,
)
from .utils import today_iso, write_csv_records


def sync_portfolio_state_from_rows(
    portfolio_lot_rows: list[dict[str, Any]],
    data_dir: str | Path,
    reports_dir: str | Path,
    *,
    market_data: dict[str, dict[str, Any]] | None = None,
    portfolio_transaction_rows: list[dict[str, Any]] | None = None,
    sp500_proxy_price: float | None = None,
    sp500_proxy_price_basis: str = "PRICE_CLOSE",
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Update portfolio change history without running a full allocation analysis."""

    data_dir = Path(data_dir)
    reports_dir = Path(reports_dir)
    as_of_date = as_of_date or today_iso()

    latest_changes, full_history, summary_rows = update_portfolio_change_history(
        portfolio_lot_rows,
        data_dir / "portfolio_state_snapshot.csv",
        data_dir / "portfolio_change_history.csv",
        as_of_date=as_of_date,
    )
    inferred_rows = update_inferred_transactions_from_changes(
        full_history,
        data_dir / "portfolio_inferred_transactions.csv",
        sp500_proxy_price=sp500_proxy_price,
        sp500_proxy_price_basis=sp500_proxy_price_basis,
        as_of_date=as_of_date,
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    write_csv_records(reports_dir / "latest_portfolio_changes.csv", latest_changes, PORTFOLIO_CHANGE_COLUMNS)
    write_csv_records(reports_dir / "latest_portfolio_change_history.csv", full_history, PORTFOLIO_CHANGE_COLUMNS)
    write_csv_records(
        reports_dir / "latest_portfolio_change_summary.csv",
        summary_rows,
        PORTFOLIO_CHANGE_SUMMARY_COLUMNS,
    )
    write_csv_records(
        reports_dir / "latest_portfolio_inferred_transactions.csv",
        inferred_rows,
        INFERRED_TRANSACTION_COLUMNS,
    )
    updated_files = [
        str(data_dir / "portfolio_state_snapshot.csv"),
        str(data_dir / "portfolio_change_history.csv"),
        str(data_dir / "portfolio_inferred_transactions.csv"),
        str(reports_dir / "latest_portfolio_changes.csv"),
        str(reports_dir / "latest_portfolio_change_history.csv"),
        str(reports_dir / "latest_portfolio_change_summary.csv"),
        str(reports_dir / "latest_portfolio_inferred_transactions.csv"),
    ]

    transaction_rows = portfolio_transaction_rows or []
    transaction_summary_rows = summarize_portfolio_transactions(transaction_rows)
    if portfolio_transaction_rows is not None:
        write_csv_records(
            reports_dir / "latest_portfolio_transactions.csv",
            transaction_rows,
            PORTFOLIO_TRANSACTION_REPORT_COLUMNS,
        )
        write_csv_records(
            reports_dir / "latest_portfolio_transaction_summary.csv",
            transaction_summary_rows,
            PORTFOLIO_TRANSACTION_SUMMARY_COLUMNS,
        )
        updated_files.extend(
            [
                str(reports_dir / "latest_portfolio_transactions.csv"),
                str(reports_dir / "latest_portfolio_transaction_summary.csv"),
            ]
        )

    account_performance_rows: list[dict[str, Any]] = []
    if market_data is not None:
        account_performance_rows = build_account_performance_rows(
            portfolio_lot_rows,
            market_data,
            data_dir / "account_performance_history.csv",
            cash_flow_rows=inferred_rows,
            transaction_rows=transaction_rows,
            as_of_date=as_of_date,
        )
        write_csv_records(
            reports_dir / "latest_account_performance_vs_sp500.csv",
            account_performance_rows,
            ACCOUNT_PERFORMANCE_COLUMNS,
        )
        updated_files.extend(
            [
                str(data_dir / "account_performance_history.csv"),
                str(reports_dir / "latest_account_performance_vs_sp500.csv"),
            ]
        )

    return {
        "as_of_date": as_of_date,
        "latest_changes": latest_changes,
        "change_history": full_history,
        "change_summary": summary_rows,
        "inferred_transactions": inferred_rows,
        "portfolio_transactions": transaction_rows,
        "portfolio_transaction_summary": transaction_summary_rows,
        "account_performance_rows": account_performance_rows,
        "latest_change_count": len(latest_changes),
        "history_count": len(full_history),
        "inferred_transaction_count": len(inferred_rows),
        "account_performance_count": len(account_performance_rows),
        "updated_files": updated_files,
    }
