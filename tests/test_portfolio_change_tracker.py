import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.portfolio_change_tracker import (
    PORTFOLIO_STATE_COLUMNS,
    build_portfolio_state_rows,
    detect_portfolio_changes,
    update_portfolio_change_history,
)
from src.utils import write_csv_records


class PortfolioChangeTrackerTest(unittest.TestCase):
    def test_first_run_creates_baseline_and_next_run_detects_share_increase(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "portfolio_state_snapshot.csv"
            history = Path(directory) / "portfolio_change_history.csv"
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

            latest, full_history, summary = update_portfolio_change_history(first_rows, snapshot, history, as_of_date="2026-05-12")
            self.assertEqual(latest[0]["change_type"], "BASELINE")
            self.assertEqual(full_history[0]["shares_after"], 2)
            self.assertEqual(summary[0]["net_shares_change"], 2)

            second_rows = [{**first_rows[0], "shares": 3, "acquisition_value_cad": 900, "current_value_cad": 1200}]
            latest, full_history, summary = update_portfolio_change_history(second_rows, snapshot, history, as_of_date="2026-06-12")

            self.assertEqual(latest[0]["change_type"], "SHARES_INCREASED")
            self.assertEqual(latest[0]["shares_before"], 2)
            self.assertEqual(latest[0]["shares_after"], 3)
            self.assertEqual(len(full_history), 2)
            self.assertEqual(summary[0]["net_shares_change"], 3)

    def test_transfer_between_numbered_accounts_is_identified(self):
        previous = build_portfolio_state_rows(
            [
                {"ticker": "MSFT", "account_type": "TFSA1", "shares": 2, "current_price_cad": 400, "current_value_cad": 800},
                {"ticker": "MSFT", "account_type": "TFSA2", "shares": 0, "current_price_cad": 400, "current_value_cad": 0},
            ],
            as_of_date="2026-05-12",
        )
        current = build_portfolio_state_rows(
            [
                {"ticker": "MSFT", "account_type": "TFSA1", "shares": 1, "current_price_cad": 400, "current_value_cad": 400},
                {"ticker": "MSFT", "account_type": "TFSA2", "shares": 1, "current_price_cad": 400, "current_value_cad": 400},
            ],
            as_of_date="2026-06-12",
        )

        changes = detect_portfolio_changes(rows_by_key(previous), rows_by_key(current), "2026-06-12")

        self.assertEqual({row["change_type"] for row in changes}, {"POSSIBLE_TRANSFER_IN", "POSSIBLE_TRANSFER_OUT"})

    def test_cost_basis_update_is_detected_without_share_change(self):
        previous = [{"ticker": "AAPL", "account_type": "TFSA1", "shares": 2, "average_cost_cad": 300}]
        current = [{"ticker": "AAPL", "account_type": "TFSA1", "shares": 2, "average_cost_cad": 320}]

        changes = detect_portfolio_changes(rows_by_key(previous), rows_by_key(current), "2026-06-12")

        self.assertEqual(changes[0]["change_type"], "COST_BASIS_UPDATED")


def rows_by_key(rows):
    return {(row["ticker"], row["account_type"]): row for row in rows}


if __name__ == "__main__":
    unittest.main()
