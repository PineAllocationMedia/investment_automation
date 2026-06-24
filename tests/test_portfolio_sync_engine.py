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


if __name__ == "__main__":
    unittest.main()
