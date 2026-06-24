import unittest

from src.proxy_calibration import (
    build_proxy_calibration_report,
    build_proxy_calibration_summary,
    clear_proxy_calibration_values,
    create_proxy_calibration_template,
    load_proxy_calibration_inputs,
)


class ProxyCalibrationTest(unittest.TestCase):
    def test_numeric_proxy_match_and_review(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "raw_auto_proxy_values": {
                    "roic_5y_avg": 19.0,
                    "fair_value": 280.0,
                },
                "raw_auto_proxy_source_notes": [
                    "roic_5y_avg: proxy ROE yfinance",
                    "fair_value: juste valeur heuristique",
                ],
            }
        }
        inputs = [
            {"ticker": "MSFT", "company_name": "Microsoft", "field": "roic_5y_avg", "true_value": "20", "source": "test"},
            {"ticker": "MSFT", "company_name": "Microsoft", "field": "fair_value", "true_value": "400", "source": "test"},
        ]

        rows = build_proxy_calibration_report([analyses], inputs)

        self.assertEqual(rows[0]["comparison_status"], "MATCH")
        self.assertEqual(rows[1]["comparison_status"], "REVIEW_PROXY")

    def test_boolean_proxy_review_when_opposite(self):
        rows = build_proxy_calibration_report(
            [
                {
                    "MA": {
                        "ticker": "MA",
                        "raw_auto_proxy_values": {"moat_clear": True},
                    }
                }
            ],
            [{"ticker": "MA", "company_name": "Mastercard", "field": "moat_clear", "true_value": "FALSE"}],
        )

        self.assertEqual(rows[0]["comparison_status"], "REVIEW_PROXY")

    def test_template_is_one_line_per_company_and_loadable(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_calibration.csv"
            create_proxy_calibration_template(path, [{"ticker": "AAPL", "company_name": "Apple"}])
            rows = load_proxy_calibration_inputs(path)
            raw_text = path.read_text()

        self.assertGreater(len(rows), 5)
        self.assertEqual(rows[0]["ticker"], "AAPL")
        self.assertIn("field", rows[0])
        self.assertEqual(len(raw_text.splitlines()), 2)

    def test_friendly_row_loads_true_values_for_multiple_fields(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_calibration.csv"
            path.write_text(
                "ticker,company_name,roic_5y_avg_true,moat_clear_true,source,source_date,confidence,notes\n"
                "MSFT,Microsoft,20,TRUE,Morningstar,2026-05-01,HIGH,test\n",
                encoding="utf-8",
            )
            rows = load_proxy_calibration_inputs(path)

        roic = next(row for row in rows if row["field"] == "roic_5y_avg")
        moat = next(row for row in rows if row["field"] == "moat_clear")
        self.assertEqual(roic["true_value"], "20")
        self.assertEqual(moat["true_value"], "TRUE")

    def test_x_marker_is_treated_as_missing_value(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_calibration.csv"
            path.write_text(
                "ticker,company_name,eps_growth_5y_true,source,source_date,confidence,notes\n"
                "MSFT,Microsoft,X,Morningstar,2026-05-01,HIGH,test\n",
                encoding="utf-8",
            )
            rows = load_proxy_calibration_inputs(path)

        eps = next(row for row in rows if row["field"] == "eps_growth_5y")
        self.assertEqual(eps["true_value"], "")

    def test_summary_flags_repeated_bad_proxy_as_recalibration_candidate(self):
        report_rows = [
            {
                "ticker": "A",
                "field": "roic_5y_avg",
                "true_value": "15",
                "proxy_value": "30",
                "difference": 15,
                "relative_difference": 1.0,
                "comparison_status": "REVIEW_PROXY",
            },
            {
                "ticker": "B",
                "field": "roic_5y_avg",
                "true_value": "20",
                "proxy_value": "35",
                "difference": 15,
                "relative_difference": 0.75,
                "comparison_status": "REVIEW_PROXY",
            },
            {
                "ticker": "C",
                "field": "roic_5y_avg",
                "true_value": "18",
                "proxy_value": "31",
                "difference": 13,
                "relative_difference": 0.7222,
                "comparison_status": "REVIEW_PROXY",
            },
        ]

        summary = build_proxy_calibration_summary(report_rows)
        roic = next(row for row in summary if row["field"] == "roic_5y_avg")

        self.assertEqual(roic["reliability_status"], "RECALIBRATION_CANDIDATE")
        self.assertEqual(roic["bias_direction"], "PROXY_TOO_HIGH")

    def test_clear_proxy_calibration_values_keeps_template_shape(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_calibration.csv"
            create_proxy_calibration_template(path, [{"ticker": "MSFT", "company_name": "Microsoft"}])
            text = path.read_text()
            path.write_text(text.replace("MSFT,Microsoft,", "MSFT,Microsoft,20,"), encoding="utf-8")
            cleared = clear_proxy_calibration_values(path)
            rows = load_proxy_calibration_inputs(path)

        self.assertGreaterEqual(cleared, 1)
        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["field"], "roic_5y_avg")
        self.assertEqual(rows[0]["true_value"], "")


if __name__ == "__main__":
    unittest.main()
