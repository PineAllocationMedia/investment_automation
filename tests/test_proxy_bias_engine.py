import unittest

from src.proxy_bias_engine import build_proxy_bias_report, proxy_bias_summary


def numeric_history(field, errors, tickers=None, true_value="100", confidence="HIGH"):
    tickers = tickers or [f"T{i}" for i in range(len(errors))]
    rows = []
    for ticker, error in zip(tickers, errors):
        proxy_value = 100 * (1 + error)
        rows.append(
            {
                "ticker": ticker,
                "field": field,
                "true_value": true_value,
                "proxy_value": proxy_value,
                "relative_difference": error,
                "error_pct": error * 100,
                "comparison_status": "REVIEW_PROXY" if abs(error) >= 0.10 else "CLOSE",
                "confidence": confidence,
            }
        )
    return rows


class ProxyBiasEngineTest(unittest.TestCase):
    def test_detects_systematic_numeric_bias_without_applying_it(self):
        rows = numeric_history(
            "roic_5y_avg",
            [-0.16, -0.17, -0.15, -0.18, -0.16, -0.17, -0.15, -0.16],
            tickers=["MSFT", "MA", "AAPL", "GOOGL", "AVGO", "INTU", "COST", "NVDA"],
            true_value="25",
        )

        report = build_proxy_bias_report(rows)
        roic = next(row for row in report if row["field"] == "roic_5y_avg")

        self.assertEqual(roic["status"], "BIAS_CANDIDATE_SAFE_SIGNAL")
        self.assertEqual(roic["proxy_direction"], "PROXY_TOO_LOW")
        self.assertGreater(float(roic["suggested_factor"]), 1.0)
        self.assertLessEqual(float(roic["suggested_factor"]), 1.25)
        self.assertEqual(proxy_bias_summary(report)["status"], "SYSTEMATIC_BIAS_SIGNAL")

    def test_noisy_numeric_errors_do_not_create_bias_signal(self):
        rows = numeric_history(
            "eps_growth_5y",
            [-0.18, 0.16, -0.12, 0.18, -0.15, 0.14],
            tickers=["MSFT", "MA", "AAPL", "GOOGL", "AVGO", "INTU"],
            true_value="20",
        )

        report = build_proxy_bias_report(rows)
        eps = next(row for row in report if row["field"] == "eps_growth_5y")

        self.assertEqual(eps["status"], "CONTRADICTORY_OR_NOISY")
        self.assertEqual(eps["confidence"], "LOW")

    def test_insufficient_samples_do_not_create_bias_signal(self):
        rows = numeric_history(
            "fair_value",
            [-0.20, -0.18, -0.19],
            tickers=["MSFT", "MA", "AAPL"],
            true_value="300",
        )

        report = build_proxy_bias_report(rows)
        fair_value = next(row for row in report if row["field"] == "fair_value")

        self.assertEqual(fair_value["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(fair_value["suggested_factor"], "")

    def test_boolean_bias_is_review_only_without_multiplicative_factor(self):
        rows = [
            {
                "ticker": ticker,
                "field": "moat_clear",
                "true_value": "TRUE",
                "proxy_value": "FALSE",
                "comparison_status": "REVIEW_PROXY",
                "confidence": "HIGH",
            }
            for ticker in ["MSFT", "MA", "AAPL", "GOOGL", "AVGO", "INTU"]
        ]

        report = build_proxy_bias_report(rows)
        moat = next(row for row in report if row["field"] == "moat_clear")

        self.assertEqual(moat["status"], "BOOLEAN_RULE_REVIEW")
        self.assertEqual(moat["suggested_factor"], "")
        self.assertIn("aucun facteur multiplicatif", moat["recommendation"])

    def test_low_confidence_rows_are_ignored(self):
        rows = numeric_history(
            "peg_manual",
            [-0.20, -0.18, -0.19, -0.21, -0.17, -0.20],
            tickers=["MSFT", "MA", "AAPL", "GOOGL", "AVGO", "INTU"],
            true_value="2",
            confidence="LOW",
        )

        report = build_proxy_bias_report(rows)
        peg = next(row for row in report if row["field"] == "peg_manual")

        self.assertEqual(peg["status"], "INSUFFICIENT_HISTORY")
        self.assertEqual(peg["ignored_low_confidence_count"], 6)


if __name__ == "__main__":
    unittest.main()
