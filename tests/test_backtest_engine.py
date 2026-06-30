import unittest

import pandas as pd

from tests.helpers import full_strong_analysis
from src.backtest_engine import BacktestConfig, _total_return_price_frame, simulate_monthly_model_backtest


class BacktestEngineTest(unittest.TestCase):
    def test_total_return_price_frame_prefers_adj_close(self):
        dates = pd.date_range("2026-01-01", periods=3, freq="B")
        raw = pd.DataFrame(
            {
                ("VFV.TO", "Close"): [100, 101, 102],
                ("VFV.TO", "Adj Close"): [95, 97, 99],
                ("MSFT", "Close"): [200, 202, 204],
            },
            index=dates,
        )
        raw.columns = pd.MultiIndex.from_tuples(raw.columns)

        prices, basis = _total_return_price_frame(raw, ["VFV.TO", "MSFT"])

        self.assertEqual(prices["VFV.TO"].iloc[-1], 99)
        self.assertEqual(basis["VFV.TO"], "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY")
        self.assertEqual(prices["MSFT"].iloc[-1], 204)
        self.assertEqual(basis["MSFT"], "PRICE_CLOSE")

    def test_simulation_allocates_all_monthly_capital_and_compares_vfv(self):
        dates = pd.date_range("2018-01-01", periods=260 * 3, freq="B")
        prices = pd.DataFrame(
            {
                "MSFT": [100 + i * 0.08 for i in range(len(dates))],
                "VFV.TO": [50 + i * 0.03 for i in range(len(dates))],
            },
            index=dates,
        )
        prices.attrs["price_return_basis"] = "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY"
        msft = full_strong_analysis("MSFT")
        msft["capital_allocation_score"] = 80
        msft["data_reliability_level"] = "HIGH"
        msft["final_position_action"] = "BUY / ADD"
        result = simulate_monthly_model_backtest(
            {"MSFT": msft, "VFV.TO": {"ticker": "VFV.TO"}},
            prices,
            BacktestConfig(years=1, monthly_capital=500, mode="high-cagr", min_vfv_percent=0.10),
        )

        self.assertEqual(result["summary"]["months"], 12)
        self.assertAlmostEqual(sum(row["amount"] for row in result["allocation_rows"] if row["date"] == result["monthly_rows"][0]["date"]), 500)
        self.assertGreater(result["summary"]["final_value"], 0)
        self.assertGreater(result["summary"]["vfv_final_value"], 0)
        self.assertEqual(result["summary"]["price_return_basis"], "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY")
        self.assertIn("gross_return", result["summary"])
        self.assertIn("net_return_after_friction", result["summary"])
        self.assertIn("friction_rows", result)
        self.assertGreaterEqual(result["summary"]["gross_return"], result["summary"]["net_return_after_friction"])

    def test_simulation_falls_back_to_vfv_when_no_candidate_is_eligible(self):
        dates = pd.date_range("2018-01-01", periods=260 * 3, freq="B")
        prices = pd.DataFrame(
            {
                "MSFT": [100 + i * 0.02 for i in range(len(dates))],
                "VFV.TO": [50 + i * 0.03 for i in range(len(dates))],
            },
            index=dates,
        )
        msft = full_strong_analysis("MSFT")
        msft["thesis_status"] = "BROKEN"
        result = simulate_monthly_model_backtest(
            {"MSFT": msft, "VFV.TO": {"ticker": "VFV.TO"}},
            prices,
            BacktestConfig(years=1, monthly_capital=500, mode="high-cagr", min_vfv_percent=0.10),
        )

        first_month_allocations = [row for row in result["allocation_rows"] if row["date"] == result["monthly_rows"][0]["date"]]
        self.assertEqual(first_month_allocations[0]["ticker"], "VFV.TO")
        self.assertEqual(first_month_allocations[0]["amount"], 500)


if __name__ == "__main__":
    unittest.main()
