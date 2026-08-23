import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.portfolio_change_tracker import (
    PORTFOLIO_STATE_COLUMNS,
    build_portfolio_state_rows,
    detect_portfolio_changes,
    update_portfolio_change_history,
)
from src.utils import read_csv_records, write_csv_records


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
        previous = [
            {
                "ticker": "AAPL",
                "account_type": "TFSA1",
                "shares": 2,
                "average_cost": 300,
                "average_cost_currency": "USD",
                "average_cost_cad": 405,
            }
        ]
        current = [{**previous[0], "average_cost": 320, "average_cost_cad": 432}]

        changes = detect_portfolio_changes(rows_by_key(previous), rows_by_key(current), "2026-06-12")

        self.assertEqual(changes[0]["change_type"], "COST_BASIS_UPDATED")
        self.assertEqual(changes[0]["average_cost_before"], 300)
        self.assertEqual(changes[0]["average_cost_after"], 320)

    def test_changed_fx_does_not_create_cost_basis_update_for_identical_usd_input(self):
        previous = build_portfolio_state_rows(
            [usd_row(average_cost_cad=135, acquisition_value_cad=270)],
            as_of_date="2026-06-12",
        )
        current = build_portfolio_state_rows(
            [usd_row(average_cost_cad=140, acquisition_value_cad=280)],
            as_of_date="2026-06-13",
        )

        changes = detect_portfolio_changes(rows_by_key(previous), rows_by_key(current), "2026-06-13")

        self.assertEqual(changes, [])
        self.assertEqual(previous[0]["average_cost"], 100)
        self.assertEqual(current[0]["average_cost"], 100)
        self.assertNotEqual(previous[0]["average_cost_cad"], current[0]["average_cost_cad"])

    def test_average_cost_currency_change_is_detected(self):
        previous = build_portfolio_state_rows(
            [usd_row(average_cost_cad=135, acquisition_value_cad=270)],
            as_of_date="2026-06-12",
        )
        current = build_portfolio_state_rows(
            [
                {
                    **usd_row(average_cost_cad=100, acquisition_value_cad=200),
                    "average_cost_currency": "CAD",
                }
            ],
            as_of_date="2026-06-12",
        )

        changes = detect_portfolio_changes(rows_by_key(previous), rows_by_key(current), "2026-06-12")

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["change_type"], "COST_BASIS_UPDATED")
        self.assertEqual(changes[0]["average_cost_currency_before"], "USD")
        self.assertEqual(changes[0]["average_cost_currency_after"], "CAD")

    def test_legacy_foreign_snapshot_migrates_without_false_cost_history(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "portfolio_state_snapshot.csv"
            history = Path(directory) / "portfolio_change_history.csv"
            write_csv_records(
                snapshot,
                [
                    {
                        "date": "2026-06-12",
                        "ticker": "AAPL",
                        "account_type": "TFSA1",
                        "account_tax_category": "TFSA",
                        "shares": 2,
                        "average_cost": "",
                        "average_cost_currency": "USD",
                        "average_cost_cad": 135,
                        "acquisition_value_cad": 270,
                        "current_price_cad": 200,
                        "current_value_cad": 400,
                    }
                ],
                PORTFOLIO_STATE_COLUMNS,
            )

            latest, full_history, _ = update_portfolio_change_history(
                [usd_row(average_cost_cad=140, acquisition_value_cad=280)],
                snapshot,
                history,
                as_of_date="2026-06-13",
            )

            migrated = read_csv_records(snapshot)
            self.assertEqual(latest, [])
            self.assertEqual(full_history, [])
            self.assertEqual(migrated[0]["average_cost"], "100.0")
            self.assertEqual(migrated[0]["average_cost_currency"], "USD")

    def test_retry_with_history_written_and_stale_snapshot_does_not_duplicate_change(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "portfolio_state_snapshot.csv"
            history = Path(directory) / "portfolio_change_history.csv"
            first_rows = [usd_row(shares=10, average_cost_cad=135, acquisition_value_cad=1350)]
            update_portfolio_change_history(first_rows, snapshot, history, as_of_date="2026-06-12")
            stale_snapshot = snapshot.read_text(encoding="utf-8")

            changed_rows = [usd_row(shares=12, average_cost_cad=135, acquisition_value_cad=1620)]
            update_portfolio_change_history(changed_rows, snapshot, history, as_of_date="2026-06-13")
            snapshot.write_text(stale_snapshot, encoding="utf-8")

            latest, full_history, _ = update_portfolio_change_history(
                changed_rows,
                snapshot,
                history,
                as_of_date="2026-06-13",
            )

            self.assertEqual(latest, [])
            self.assertEqual(len(full_history), 2)
            self.assertEqual(full_history[-1]["shares_before"], "10.0")
            self.assertEqual(full_history[-1]["shares_after"], "12.0")

    def test_distinct_same_day_changes_and_repeated_transition_after_reversal_are_preserved(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "portfolio_state_snapshot.csv"
            history = Path(directory) / "portfolio_change_history.csv"
            update_portfolio_change_history(
                [usd_row(shares=10, average_cost_cad=135, acquisition_value_cad=1350)],
                snapshot,
                history,
                as_of_date="2026-06-12",
            )
            for shares in (12, 15, 10, 12):
                update_portfolio_change_history(
                    [usd_row(shares=shares, average_cost_cad=135, acquisition_value_cad=135 * shares)],
                    snapshot,
                    history,
                    as_of_date="2026-06-13",
                )

            full_history = read_csv_records(history)
            transitions = [(row["shares_before"], row["shares_after"]) for row in full_history[1:]]
            self.assertEqual(
                transitions,
                [("10.0", "12.0"), ("12.0", "15.0"), ("15.0", "10.0"), ("10.0", "12.0")],
            )

    def test_exact_history_identity_distinguishes_cost_transitions(self):
        with TemporaryDirectory() as directory:
            snapshot = Path(directory) / "portfolio_state_snapshot.csv"
            history = Path(directory) / "portfolio_change_history.csv"
            update_portfolio_change_history(
                [usd_row(average_cost=100, average_cost_cad=135, acquisition_value_cad=270)],
                snapshot,
                history,
                as_of_date="2026-06-12",
            )
            update_portfolio_change_history(
                [usd_row(average_cost=105, average_cost_cad=141.75, acquisition_value_cad=283.5)],
                snapshot,
                history,
                as_of_date="2026-06-13",
            )
            update_portfolio_change_history(
                [usd_row(average_cost=110, average_cost_cad=148.5, acquisition_value_cad=297)],
                snapshot,
                history,
                as_of_date="2026-06-13",
            )

            full_history = read_csv_records(history)
            self.assertEqual(len(full_history), 3)
            self.assertEqual(
                [(row["average_cost_before"], row["average_cost_after"]) for row in full_history[1:]],
                [("100.0", "105.0"), ("105.0", "110.0")],
            )


def rows_by_key(rows):
    return {(row["ticker"], row["account_type"]): row for row in rows}


def usd_row(
    *,
    shares=2,
    average_cost=100,
    average_cost_cad=135,
    acquisition_value_cad=270,
):
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
