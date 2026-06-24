import tempfile
import unittest
from pathlib import Path

from src.account_performance_engine import build_account_performance_rows


class AccountPerformanceTest(unittest.TestCase):
    def test_creates_baseline_then_compares_account_to_sp500_proxy(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            first = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1100, "acquisition_value_cad": 1000}],
                {"VFV.TO": {"current_price": 100}},
                history,
                as_of_date="2026-01-01",
            )
            second = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1210, "acquisition_value_cad": 1000}],
                {"VFV.TO": {"current_price": 105}},
                history,
                as_of_date="2026-06-01",
            )

        first_tfsa = next(row for row in first if row["account_type"] == "TFSA1")
        second_tfsa = next(row for row in second if row["account_type"] == "TFSA1")
        self.assertEqual(first_tfsa["comparison_status"], "BASELINE_CREATED")
        self.assertEqual(second_tfsa["comparison_status"], "AHEAD_OF_SP500")
        self.assertAlmostEqual(second_tfsa["portfolio_return_since_tracking"], 0.10)
        self.assertAlmostEqual(second_tfsa["sp500_return_since_tracking"], 0.05)
        self.assertAlmostEqual(second_tfsa["excess_return_vs_sp500"], 0.05)
        self.assertAlmostEqual(second_tfsa["portfolio_twr"], 0.10)
        self.assertAlmostEqual(second_tfsa["sp500_twr"], 0.05)
        self.assertAlmostEqual(second_tfsa["twr_excess_vs_sp500"], 0.05)
        self.assertEqual(second_tfsa["preferred_performance_read"], "TWR_EXCESS")

    def test_sp500_comparison_prefers_adjusted_total_return_proxy_when_available(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1000, "acquisition_value_cad": 1000}],
                {
                    "VFV.TO": {
                        "current_price": 90,
                        "total_return_price": 100,
                        "total_return_basis": "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY",
                        "total_return_price_history": {"2026-01-01": 100},
                    }
                },
                history,
                as_of_date="2026-01-01",
            )
            rows = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1100, "acquisition_value_cad": 1000}],
                {
                    "VFV.TO": {
                        "current_price": 90,
                        "total_return_price": 110,
                        "total_return_basis": "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY",
                        "total_return_price_history": {"2026-01-01": 100, "2026-06-01": 110},
                    }
                },
                history,
                as_of_date="2026-06-01",
            )

        tfsa = next(row for row in rows if row["account_type"] == "TFSA1")
        self.assertEqual(tfsa["benchmark_return_basis"], "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY")
        self.assertAlmostEqual(tfsa["sp500_return_since_tracking"], 0.10)
        self.assertAlmostEqual(tfsa["sp500_twr"], 0.10)
        self.assertAlmostEqual(tfsa["twr_excess_vs_sp500"], 0.0)

    def test_flags_sp500_comparison_as_approximate_when_cost_basis_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1000, "acquisition_value_cad": 900}],
                {"VFV.TO": {"current_price": 100}},
                history,
                as_of_date="2026-01-01",
            )
            rows = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1500, "acquisition_value_cad": 1300}],
                {"VFV.TO": {"current_price": 105}},
                history,
                as_of_date="2026-06-01",
            )

        tfsa = next(row for row in rows if row["account_type"] == "TFSA1")
        self.assertEqual(tfsa["comparison_status"], "APPROXIMATE_CONTRIBUTIONS_CHANGED")
        self.assertEqual(tfsa["simple_return_status"], "FLOW_DISTORTED_BY_CONTRIBUTIONS")
        self.assertIn("rendement simple masqué", tfsa["preferred_performance_summary"])
        self.assertIn("approximative", tfsa["interpretation"])

    def test_flow_adjusted_comparison_accounts_for_inferred_contributions(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1000, "acquisition_value_cad": 1000}],
                {"VFV.TO": {"current_price": 100}},
                history,
                as_of_date="2026-01-01",
            )
            rows = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1600, "acquisition_value_cad": 1500}],
                {"VFV.TO": {"current_price": 120}},
                history,
                cash_flow_rows=[
                    {
                        "date": "2026-03-01",
                        "account_type": "TFSA1",
                        "external_flow_cad": 500,
                        "sp500_proxy_price_at_flow": 110,
                    }
                ],
                as_of_date="2026-06-01",
            )

        tfsa = next(row for row in rows if row["account_type"] == "TFSA1")
        self.assertEqual(tfsa["flow_adjusted_status"], "BEHIND_SP500_FLOW_ADJUSTED")
        self.assertAlmostEqual(tfsa["sp500_equivalent_value_cad"], 1745.45, places=2)
        self.assertAlmostEqual(tfsa["value_added_vs_sp500_cad"], -145.45, places=2)
        self.assertEqual(tfsa["xirr_status"], "XIRR_FLOW_ADJUSTED_BEHIND_SP500")
        self.assertLess(tfsa["xirr_excess_vs_sp500"], 0)
        self.assertIn("flux déduit", tfsa["xirr_method"])

    def test_xirr_prefers_explicit_contribution_rows_over_inferred_same_day(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1000, "acquisition_value_cad": 1000}],
                {"VFV.TO": {"current_price": 100}},
                history,
                as_of_date="2026-01-01",
            )
            rows = build_account_performance_rows(
                [{"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1700, "acquisition_value_cad": 1500}],
                {"VFV.TO": {"current_price": 120}},
                history,
                cash_flow_rows=[
                    {
                        "date": "2026-06-01",
                        "account_type": "TFSA1",
                        "external_flow_cad": 700,
                        "sp500_proxy_price_at_flow": 120,
                    }
                ],
                transaction_rows=[
                    {
                        "date": "2026-06-01",
                        "account_type": "TFSA1",
                        "net_contribution_cad": 500,
                    }
                ],
                as_of_date="2026-06-01",
            )

        tfsa = next(row for row in rows if row["account_type"] == "TFSA1")
        self.assertEqual(tfsa["xirr_flow_count"], 1)
        self.assertIn("flux réel", tfsa["xirr_method"])
        self.assertNotIn("flux déduit", tfsa["xirr_method"])

    def test_twr_neutralizes_contributions_for_each_account_and_total(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "account_performance_history.csv"
            build_account_performance_rows(
                [
                    {"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1000, "acquisition_value_cad": 900},
                    {"ticker": "GOOGL", "account_type": "TFSA2", "current_value_cad": 500, "acquisition_value_cad": 500},
                ],
                {"VFV.TO": {"current_price": 100}},
                history,
                as_of_date="2026-01-01",
            )
            rows = build_account_performance_rows(
                [
                    {"ticker": "MSFT", "account_type": "TFSA1", "current_value_cad": 1100, "acquisition_value_cad": 900},
                    {"ticker": "GOOGL", "account_type": "TFSA2", "current_value_cad": 750, "acquisition_value_cad": 750},
                ],
                {"VFV.TO": {"current_price": 110}},
                history,
                cash_flow_rows=[
                    {
                        "date": "2026-03-01",
                        "account_type": "TFSA2",
                        "external_flow_cad": 250,
                        "sp500_proxy_price_at_flow": 110,
                    }
                ],
                as_of_date="2026-03-01",
            )

        tfsa1 = next(row for row in rows if row["account_type"] == "TFSA1")
        tfsa2 = next(row for row in rows if row["account_type"] == "TFSA2")
        total = next(row for row in rows if row["account_type"] == "ALL_ACCOUNTS")
        self.assertAlmostEqual(tfsa1["portfolio_twr"], 0.10)
        self.assertAlmostEqual(tfsa2["portfolio_twr"], 0.0)
        self.assertAlmostEqual(tfsa2["sp500_twr"], 0.10)
        self.assertAlmostEqual(tfsa2["twr_excess_vs_sp500"], -0.10)
        self.assertEqual(tfsa2["twr_status"], "TWR_FLOW_ADJUSTED_BEHIND_SP500")
        self.assertAlmostEqual(total["portfolio_twr"], 0.066667)
        self.assertEqual(total["preferred_performance_read"], "TWR_EXCESS")


if __name__ == "__main__":
    unittest.main()
