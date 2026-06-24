import tempfile
import unittest
from pathlib import Path

from src.account_charts import (
    account_chart_rows_for_report,
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

            self.assertEqual([row["account_type"] for row in chart_rows], ["FHSA", "TFSA1"])
            self.assertTrue((Path(directory) / "account_TFSA1.svg").exists())
            self.assertTrue((Path(directory) / "account_FHSA.svg").exists())
            self.assertEqual(chart_rows[1]["positions_count"], 2)
            self.assertIn("MSFT", chart_rows[1]["top_positions"])

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
