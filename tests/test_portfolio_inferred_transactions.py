import tempfile
import unittest
from pathlib import Path

from src.portfolio_inferred_transactions import update_inferred_transactions_from_changes


class PortfolioInferredTransactionsTest(unittest.TestCase):
    def test_infers_buy_and_preserves_sp500_price_for_today_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio_inferred_transactions.csv"
            rows = update_inferred_transactions_from_changes(
                [
                    {
                        "date": "2026-06-01",
                        "ticker": "MSFT",
                        "account_type": "TFSA1",
                        "change_type": "SHARES_INCREASED",
                        "shares_change": 1,
                        "estimated_change_value_cad": 500,
                    }
                ],
                path,
                sp500_proxy_price=200,
                as_of_date="2026-06-01",
            )

        self.assertEqual(rows[0]["inferred_transaction_type"], "INFERRED_BUY")
        self.assertEqual(rows[0]["external_flow_cad"], 500)
        self.assertEqual(rows[0]["sp500_proxy_price_at_flow"], 200)
        self.assertEqual(rows[0]["confidence"], "MEDIUM")

    def test_possible_transfer_does_not_create_external_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio_inferred_transactions.csv"
            rows = update_inferred_transactions_from_changes(
                [
                    {
                        "date": "2026-06-01",
                        "ticker": "MSFT",
                        "account_type": "TFSA2",
                        "change_type": "POSSIBLE_TRANSFER_IN",
                        "shares_change": 1,
                        "estimated_change_value_cad": 500,
                    }
                ],
                path,
                sp500_proxy_price=200,
                as_of_date="2026-06-01",
            )

        self.assertEqual(rows[0]["inferred_transaction_type"], "INFERRED_TRANSFER_IN")
        self.assertEqual(rows[0]["external_flow_cad"], 0.0)
        self.assertEqual(rows[0]["sp500_proxy_price_at_flow"], "")


if __name__ == "__main__":
    unittest.main()
