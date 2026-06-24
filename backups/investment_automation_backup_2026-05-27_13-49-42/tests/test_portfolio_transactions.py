import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.portfolio_transactions import (
    PORTFOLIO_TRANSACTION_COLUMNS,
    build_portfolio_transaction_report_rows,
    load_portfolio_transactions,
    normalize_transaction_type,
    summarize_portfolio_transactions,
)
from src.utils import write_csv_records
from src.validators import validate_portfolio_transactions_file


class PortfolioTransactionsTest(unittest.TestCase):
    def test_buy_and_contribution_are_converted_and_summarized_by_account(self):
        rows = [
            {
                "date": "2026-05-12",
                "ticker": "MSFT",
                "account_type": "TFSA1",
                "transaction_type": "BUY",
                "shares": "2",
                "price": "100",
                "price_currency": "USD",
                "fees": "1",
                "fees_currency": "CAD",
                "cash_amount": "",
                "cash_currency": "",
                "notes": "test",
            },
            {
                "date": "2026-05-13",
                "ticker": "",
                "account_type": "TFSA1",
                "transaction_type": "CASH_CONTRIBUTION",
                "shares": "",
                "price": "",
                "price_currency": "",
                "fees": "",
                "fees_currency": "",
                "cash_amount": "500",
                "cash_currency": "CAD",
                "notes": "",
            },
        ]

        loaded = load_transactions_fixture(rows)
        report_rows = build_portfolio_transaction_report_rows(loaded, {"CAD": 1.0, "USD": 1.35})
        summary_rows = summarize_portfolio_transactions(report_rows)

        buy_row = next(row for row in report_rows if row["transaction_type"] == "BUY")
        cash_row = next(row for row in report_rows if row["transaction_type"] == "CASH_CONTRIBUTION")
        msft_summary = next(row for row in summary_rows if row["ticker"] == "MSFT")
        cash_summary = next(row for row in summary_rows if row["ticker"] == "CASH")

        self.assertEqual(buy_row["account_tax_category"], "TFSA")
        self.assertEqual(buy_row["trade_value_cad"], 271.0)
        self.assertEqual(buy_row["net_trade_cash_flow_cad"], -271.0)
        self.assertEqual(cash_row["net_contribution_cad"], 500.0)
        self.assertEqual(msft_summary["buy_value_cad"], 271.0)
        self.assertEqual(msft_summary["net_shares_change"], 2.0)
        self.assertEqual(cash_summary["net_contributions_cad"], 500.0)

    def test_french_transaction_aliases_are_supported(self):
        self.assertEqual(normalize_transaction_type("achat"), "BUY")
        self.assertEqual(normalize_transaction_type("cotisation"), "CASH_CONTRIBUTION")
        self.assertEqual(normalize_transaction_type("vente"), "SELL")

    def test_validation_flags_invalid_transaction_rows(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "portfolio_transactions.csv"
            write_csv_records(
                path,
                [
                    {
                        "date": "12-05-2026",
                        "ticker": "MSFT",
                        "account_type": "CELI",
                        "transaction_type": "BUY",
                        "shares": "0",
                        "price": "abc",
                        "price_currency": "XYZ",
                    }
                ],
                PORTFOLIO_TRANSACTION_COLUMNS,
            )

            errors = validate_portfolio_transactions_file(path)

        self.assertTrue(any("date invalide" in error for error in errors))
        self.assertTrue(any("account_type invalide" in error for error in errors))
        self.assertTrue(any("price invalide" in error for error in errors))
        self.assertTrue(any("price_currency invalide" in error for error in errors))


def load_transactions_fixture(rows):
    with TemporaryDirectory() as directory:
        path = Path(directory) / "portfolio_transactions.csv"
        write_csv_records(path, rows, PORTFOLIO_TRANSACTION_COLUMNS)
        return load_portfolio_transactions(path)


if __name__ == "__main__":
    unittest.main()
