import unittest

from src.underperformance_engine import build_underperformance_attribution


class UnderperformanceEngineTest(unittest.TestCase):
    def test_one_year_underperformance_with_clean_process_is_regime_lag(self):
        result = build_underperformance_attribution(
            model_metrics={
                "allocation_sample_count": 8,
                "span_days": 365,
                "avg_vfv": 0.12,
                "avg_core": 0.88,
                "avg_allocation_turnover": 0.15,
                "primary_change_rate": 0.10,
                "avg_max_single": 0.35,
                "high_cycle_day_rate": 0.15,
                "extreme_cycle_day_rate": 0.0,
                "low_data_day_rate": 0.0,
                "avg_decision_quality": 78,
                "health_status": "STRONG",
            },
            account_performance_rows=[
                {
                    "account_type": "ALL_ACCOUNTS",
                    "twr_status": "TWR_FLOW_ADJUSTED_BEHIND_SP500",
                    "twr_excess_vs_sp500": -0.06,
                }
            ],
            backtest_summaries=[{"excess_value_vs_vfv": 1000}],
            mode="high-cagr",
        )

        self.assertEqual(result["status"], "TEMPORARY_REGIME_LAG")
        self.assertEqual(result["correction_governor"], "THROTTLE_SAFE_TUNING")
        self.assertFalse(result["can_auto_apply_safe_tuning"])

    def test_multi_year_underperformance_with_process_issues_allows_gradual_safe_tuning(self):
        result = build_underperformance_attribution(
            model_metrics={
                "allocation_sample_count": 18,
                "span_days": 850,
                "avg_vfv": 0.38,
                "avg_core": 0.52,
                "avg_allocation_turnover": 0.58,
                "primary_change_rate": 0.60,
                "avg_max_single": 0.36,
                "high_cycle_day_rate": 0.12,
                "extreme_cycle_day_rate": 0.0,
                "low_data_day_rate": 0.0,
                "avg_decision_quality": 72,
                "health_status": "TOO_DEFENSIVE",
            },
            account_performance_rows=[
                {
                    "account_type": "ALL_ACCOUNTS",
                    "twr_status": "TWR_FLOW_ADJUSTED_BEHIND_SP500",
                    "twr_excess_vs_sp500": -0.08,
                }
            ],
            backtest_summaries=[{"excess_value_vs_vfv": -500}, {"excess_value_vs_vfv": -1000}],
            mode="high-cagr",
        )

        self.assertEqual(result["status"], "CORRECTION_LIKELY_NEEDED")
        self.assertEqual(result["correction_governor"], "ALLOW_SAFE_TUNING")
        self.assertTrue(result["can_auto_apply_safe_tuning"])
        self.assertEqual(result["max_safe_changes_allowed"], 2)

    def test_five_year_underperformance_blocks_auto_rewrite(self):
        result = build_underperformance_attribution(
            model_metrics={
                "allocation_sample_count": 36,
                "span_days": 1900,
                "avg_vfv": 0.40,
                "avg_core": 0.50,
                "avg_allocation_turnover": 0.62,
                "primary_change_rate": 0.65,
                "avg_max_single": 0.58,
                "high_cycle_day_rate": 0.70,
                "extreme_cycle_day_rate": 0.35,
                "low_data_day_rate": 0.22,
                "avg_decision_quality": 50,
                "health_status": "NEEDS_REVIEW",
            },
            account_performance_rows=[
                {
                    "account_type": "ALL_ACCOUNTS",
                    "twr_status": "TWR_FLOW_ADJUSTED_BEHIND_SP500",
                    "twr_excess_vs_sp500": -0.12,
                }
            ],
            backtest_summaries=[{"excess_value_vs_vfv": -500}, {"excess_value_vs_vfv": -1000}],
            mode="high-cagr",
        )

        self.assertEqual(result["status"], "MANUAL_STRATEGIC_REVIEW_NEEDED")
        self.assertEqual(result["correction_governor"], "MANUAL_REVIEW_ONLY")
        self.assertFalse(result["can_auto_apply_safe_tuning"])


if __name__ == "__main__":
    unittest.main()
