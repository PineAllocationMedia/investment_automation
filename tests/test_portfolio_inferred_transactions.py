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

    def test_preserves_two_distinct_same_day_changes_with_same_delta_and_value(self):
        changes = [
            {
                "date": "2026-06-01",
                "ticker": "MSFT",
                "account_type": "TFSA1",
                "change_type": "SHARES_INCREASED",
                "shares_before": 10,
                "shares_after": 12,
                "shares_change": 2,
                "estimated_change_value_cad": 500,
            },
            {
                "date": "2026-06-01",
                "ticker": "MSFT",
                "account_type": "TFSA1",
                "change_type": "SHARES_INCREASED",
                "shares_before": 12,
                "shares_after": 14,
                "shares_change": 2,
                "estimated_change_value_cad": 500,
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio_inferred_transactions.csv"

            first = update_inferred_transactions_from_changes(
                changes,
                path,
                sp500_proxy_price=200,
                as_of_date="2026-06-01",
            )
            second = update_inferred_transactions_from_changes(
                changes,
                path,
                sp500_proxy_price=205,
                as_of_date="2026-06-01",
            )

        self.assertEqual(len(first), 2)
        self.assertEqual(len(second), 2)
        self.assertTrue(all(row["inferred_transaction_type"] == "INFERRED_BUY" for row in second))
        self.assertTrue(all(row["sp500_proxy_price_at_flow"] == "200" for row in second))


if __name__ == "__main__":
    unittest.main()
