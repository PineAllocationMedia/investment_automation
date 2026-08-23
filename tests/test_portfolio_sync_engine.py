import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.portfolio_sync_engine import sync_portfolio_state_from_rows
from src.utils import read_csv_records


class PortfolioSyncEngineTest(unittest.TestCase):
    def test_sync_updates_history_and_report_csv_without_analysis_snapshot(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            reports_dir = root / "reports"
            data_dir.mkdir()
            reports_dir.mkdir()

            first_rows = [
                {
                    "ticker": "MSFT",
                    "account_type": "TFSA1",
                    "shares": 2,
                    "average_cost_cad": 300,
                    "acquisition_value_cad": 600,
                    "current_price_cad": 400,
                    "current_value_cad": 800,
                }
            ]
            sync_portfolio_state_from_rows(first_rows, data_dir, reports_dir, as_of_date="2026-05-28")

            second_rows = [{**first_rows[0], "shares": 3, "acquisition_value_cad": 900, "current_value_cad": 1200}]
            result = sync_portfolio_state_from_rows(
                second_rows,
                data_dir,
                reports_dir,
                market_data={"VFV.TO": {"current_price": 150.0, "total_return_price": 150.0}},
                portfolio_transaction_rows=[
                    {
                        "date": "2026-05-29",
                        "ticker": "MSFT",
                        "account_type": "TFSA1",
                        "account_tax_category": "TFSA",
                        "transaction_type": "BUY",
                        "trade_value_cad": 400.0,
                        "net_contribution_cad": 0.0,
                    }
                ],
                sp500_proxy_price=150.0,
                as_of_date="2026-05-29",
            )

            self.assertEqual(result["latest_change_count"], 1)
            self.assertEqual(result["latest_changes"][0]["change_type"], "SHARES_INCREASED")
            self.assertTrue((reports_dir / "latest_portfolio_changes.csv").exists())
            self.assertTrue((reports_dir / "latest_portfolio_change_history.csv").exists())
            self.assertTrue((reports_dir / "latest_portfolio_inferred_transactions.csv").exists())
            self.assertTrue((reports_dir / "latest_portfolio_transactions.csv").exists())
            self.assertTrue((reports_dir / "latest_portfolio_transaction_summary.csv").exists())
            self.assertTrue((reports_dir / "latest_account_performance_vs_sp500.csv").exists())
            self.assertTrue((data_dir / "account_performance_history.csv").exists())
            self.assertFalse((reports_dir / "latest_analysis_snapshot.json").exists())

            inferred_rows = read_csv_records(data_dir / "portfolio_inferred_transactions.csv")
            self.assertEqual(inferred_rows[-1]["inferred_transaction_type"], "INFERRED_BUY")
            self.assertEqual(inferred_rows[-1]["date"], "2026-05-29")
            account_performance_rows = read_csv_records(reports_dir / "latest_account_performance_vs_sp500.csv")
            self.assertTrue(any(row["account_type"] == "TFSA1" for row in account_performance_rows))

    def test_identical_foreign_portfolio_same_and_later_date_does_not_add_change_history(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            reports_dir = root / "reports"
            data_dir.mkdir()
            reports_dir.mkdir()
            market_data = {"VFV.TO": {"current_price": 150.0, "total_return_price": 150.0}}

            sync_portfolio_state_from_rows(
                [usd_row(average_cost_cad=135, acquisition_value_cad=1350)],
                data_dir,
                reports_dir,
                market_data=market_data,
                sp500_proxy_price=150,
                as_of_date="2026-06-01",
            )
            same_day = sync_portfolio_state_from_rows(
                [usd_row(average_cost_cad=140, acquisition_value_cad=1400)],
                data_dir,
                reports_dir,
                market_data=market_data,
                sp500_proxy_price=150,
                as_of_date="2026-06-01",
            )
            later = sync_portfolio_state_from_rows(
                [usd_row(average_cost_cad=145, acquisition_value_cad=1450)],
                data_dir,
                reports_dir,
                market_data=market_data,
                sp500_proxy_price=150,
                as_of_date="2026-06-02",
            )

            self.assertEqual(same_day["latest_change_count"], 0)
            self.assertEqual(later["latest_change_count"], 0)
            self.assertEqual(len(read_csv_records(data_dir / "portfolio_change_history.csv")), 1)
            performance = read_csv_records(data_dir / "account_performance_history.csv")
            self.assertEqual(len([row for row in performance if row["date"] == "2026-06-01"]), 2)
            self.assertEqual(len([row for row in performance if row["date"] == "2026-06-02"]), 2)

    def test_two_genuine_same_day_edits_and_repeat_remain_exactly_once(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            reports_dir = root / "reports"
            data_dir.mkdir()
            reports_dir.mkdir()
            market_data = {"VFV.TO": {"current_price": 150.0, "total_return_price": 150.0}}

            for shares in (10, 12, 14, 14):
                sync_portfolio_state_from_rows(
                    [usd_row(shares=shares, acquisition_value_cad=135 * shares)],
                    data_dir,
                    reports_dir,
                    market_data=market_data,
                    sp500_proxy_price=150,
                    as_of_date="2026-06-01",
                )

            history = read_csv_records(data_dir / "portfolio_change_history.csv")
            inferred = read_csv_records(data_dir / "portfolio_inferred_transactions.csv")
            performance = read_csv_records(data_dir / "account_performance_history.csv")
            self.assertEqual(len(history), 3)
            self.assertEqual(
                [(row["shares_before"], row["shares_after"]) for row in history[1:]],
                [("10.0", "12.0"), ("12.0", "14.0")],
            )
            self.assertEqual(len(inferred), 3)
            self.assertEqual(len(performance), 2)

    def test_direct_sync_retry_after_history_write_with_stale_snapshot_is_idempotent(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            data_dir = root / "data"
            reports_dir = root / "reports"
            data_dir.mkdir()
            reports_dir.mkdir()
            initial = [usd_row(shares=10, acquisition_value_cad=1350)]
            changed = [usd_row(shares=12, acquisition_value_cad=1620)]

            sync_portfolio_state_from_rows(initial, data_dir, reports_dir, as_of_date="2026-06-01")
            stale_snapshot = (data_dir / "portfolio_state_snapshot.csv").read_text(encoding="utf-8")
            sync_portfolio_state_from_rows(changed, data_dir, reports_dir, as_of_date="2026-06-02")
            (data_dir / "portfolio_state_snapshot.csv").write_text(stale_snapshot, encoding="utf-8")

            retry = sync_portfolio_state_from_rows(changed, data_dir, reports_dir, as_of_date="2026-06-02")

            self.assertEqual(retry["latest_change_count"], 0)
            self.assertEqual(len(read_csv_records(data_dir / "portfolio_change_history.csv")), 2)
            self.assertEqual(len(read_csv_records(data_dir / "portfolio_inferred_transactions.csv")), 2)


def usd_row(*, shares=10, average_cost=100, average_cost_cad=135, acquisition_value_cad=1350):
    return {
        "ticker": "AAPL",
        "account_type": "TFSA1",
        "shares": shares,
        "average_cost": average_cost,
        "average_cost_currency": "USD",
        "acquisition_value": shares * average_cost,
        "average_cost_cad": average_cost_cad,
        "acquisition_value_cad": acquisition_value_cad,
        "current_price_cad": 200,
        "current_value_cad": shares * 200,
    }


if __name__ == "__main__":
    unittest.main()
