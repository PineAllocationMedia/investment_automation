import tempfile
import unittest
from pathlib import Path

from src.account_charts import (
    account_chart_rows_for_report,
    account_charts_markdown,
    build_account_allocation_chart_rows,
)


class AccountChartsTest(unittest.TestCase):
    def test_generates_one_svg_per_account_from_positive_values(self):
        rows = [
            {"ticker": "MSFT", "account_type": "TFSA1", "current_value": 1000},
            {"ticker": "AVGO", "account_type": "TFSA1", "current_value": 500},
            {"ticker": "VFV.TO", "account_type": "FHSA", "current_value": 250},
            {"ticker": "INTU", "account_type": "TFSA1", "current_value": 0},
        ]

        with tempfile.TemporaryDirectory() as directory:
            chart_rows = build_account_allocation_chart_rows(rows, Path(directory))

            self.assertEqual([row["account_type"] for row in chart_rows], ["FHSA", "TFSA1", "ALL_ACCOUNTS"])
            self.assertTrue((Path(directory) / "account_TFSA1.svg").exists())
            self.assertTrue((Path(directory) / "account_FHSA.svg").exists())
            self.assertTrue((Path(directory) / "account_ALL_ACCOUNTS.svg").exists())
            self.assertEqual(chart_rows[1]["positions_count"], 2)
            self.assertIn("MSFT", chart_rows[1]["top_positions"])

    def test_combined_chart_aggregates_duplicate_tickers_once(self):
        rows = [
            {"ticker": "MSFT", "account_type": "TFSA1", "current_value": 300},
            {"ticker": "AAPL", "account_type": "TFSA1", "current_value": 200},
            {"ticker": "MSFT", "account_type": "TFSA2", "current_value": 100},
            {"ticker": "VFV.TO", "account_type": "TFSA2", "current_value": 400},
        ]

        with tempfile.TemporaryDirectory() as directory:
            chart_rows = build_account_allocation_chart_rows(rows, Path(directory))
            combined = next(row for row in chart_rows if row["account_type"] == "ALL_ACCOUNTS")
            svg = (Path(directory) / "account_ALL_ACCOUNTS.svg").read_text(encoding="utf-8")

            self.assertEqual(combined["total_value_cad"], 1000)
            self.assertEqual(combined["positions_count"], 3)
            self.assertEqual(svg.count(">MSFT</text>"), 1)
            self.assertIn("40.0 %", svg)
            self.assertIn("20.0 %", svg)
            markdown = "\n".join(account_charts_markdown(chart_rows))
            self.assertIn("charts/account_TFSA1.svg", markdown)
            self.assertIn("charts/account_TFSA2.svg", markdown)
            self.assertIn("charts/account_ALL_ACCOUNTS.svg", markdown)
            self.assertIn("Total - Portfolio 1 + Portfolio 2", markdown)

    def test_small_positions_are_grouped_as_autres(self):
        rows = [
            {"ticker": "AAPL", "account_type": "TFSA1", "current_value": 1000},
            {"ticker": "MSFT", "account_type": "TFSA1", "current_value": 900},
            {"ticker": "TINY", "account_type": "TFSA1", "current_value": 10},
        ]

        with tempfile.TemporaryDirectory() as directory:
            chart_rows = build_account_allocation_chart_rows(rows, Path(directory))
            svg = (Path(directory) / "account_TFSA1.svg").read_text(encoding="utf-8")

            self.assertIn("Autres", svg)
            self.assertIn("regroupées", chart_rows[0]["note"])

    def test_report_rows_format_total_value(self):
        rows = [{"account_type": "TFSA1", "total_value_cad": 1500, "positions_count": 2}]

        display_rows = account_chart_rows_for_report(rows)

        self.assertEqual(display_rows[0]["total_value_cad"], "1 500.00 $")


if __name__ == "__main__":
    unittest.main()
