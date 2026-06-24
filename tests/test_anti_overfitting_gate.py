import unittest
from datetime import date

from src.anti_overfitting_gate_engine import (
    apply_anti_overfitting_gate_to_suggestions,
    build_anti_overfitting_context,
)


def recent_only_monthly_rows():
    rows = []
    for index in range(36):
        old_period = index < 25
        if old_period:
            portfolio = 1.0 + index * 0.004
            vfv = 1.0 + index * 0.007
        else:
            portfolio = 1.0 + 25 * 0.004 + (index - 25) * 0.020
            vfv = 1.0 + 25 * 0.007 + (index - 25) * 0.006
        rows.append(
            {
                "period_years": 5,
                "date": f"{2022 + index // 12}-{(index % 12) + 1:02d}-28",
                "capital_multiple": portfolio,
                "vfv_capital_multiple": vfv,
            }
        )
    return rows


class AntiOverfittingGateEngineTest(unittest.TestCase):
    def test_recent_only_evidence_blocks_aggressive_auto_tuning(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": -2000, "max_drawdown_on_capital_multiple": -0.28},
            ],
            backtest_monthly_rows=recent_only_monthly_rows(),
            tuning_history_rows=[],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4, "min_days_between_same_parameter_tuning": 45},
        )
        suggestions = apply_anti_overfitting_gate_to_suggestions(
            [
                {
                    "parameter": "vfv_adjustment",
                    "suggested_delta": -0.01,
                    "safety_level": "SAFE",
                    "can_auto_apply": True,
                    "status": "PENDING_SAFE_APPLY",
                }
            ],
            context,
        )

        self.assertEqual(suggestions[0]["overfit_gate_status"], "REVIEW_ONLY")
        self.assertFalse(suggestions[0]["can_auto_apply"])
        self.assertEqual(suggestions[0]["status"], "REVIEW_ONLY")

    def test_recent_only_evidence_does_not_block_risk_dampener(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": -2000, "max_drawdown_on_capital_multiple": -0.28},
            ],
            backtest_monthly_rows=recent_only_monthly_rows(),
            tuning_history_rows=[],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4},
        )
        suggestions = apply_anti_overfitting_gate_to_suggestions(
            [
                {
                    "parameter": "cycle_budget_adjustment",
                    "suggested_delta": -0.02,
                    "safety_level": "SAFE",
                    "can_auto_apply": True,
                    "status": "PENDING_SAFE_APPLY",
                }
            ],
            context,
        )

        self.assertIn(suggestions[0]["overfit_gate_status"], {"PASS", "PASS_WITH_LIMITS"})
        self.assertTrue(suggestions[0]["can_auto_apply"])

    def test_cooldown_blocks_repeated_same_parameter_tuning(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": 2000, "max_drawdown_on_capital_multiple": -0.24},
            ],
            backtest_monthly_rows=[],
            tuning_history_rows=[
                {
                    "applied_at": date.today().isoformat(),
                    "mode": "high-cagr",
                    "parameter": "vfv_adjustment",
                }
            ],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4, "min_days_between_same_parameter_tuning": 45},
        )
        suggestions = apply_anti_overfitting_gate_to_suggestions(
            [
                {
                    "parameter": "vfv_adjustment",
                    "suggested_delta": -0.01,
                    "safety_level": "SAFE",
                    "can_auto_apply": True,
                    "status": "PENDING_SAFE_APPLY",
                }
            ],
            context,
        )

        self.assertEqual(suggestions[0]["cooldown_status"], "COOLDOWN_ACTIVE")
        self.assertEqual(suggestions[0]["overfit_gate_status"], "REVIEW_ONLY")
        self.assertFalse(suggestions[0]["can_auto_apply"])


if __name__ == "__main__":
    unittest.main()
