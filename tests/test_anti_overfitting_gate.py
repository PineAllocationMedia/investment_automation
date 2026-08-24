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

    def test_proposal_only_policy_blocks_risk_dampener_auto_apply(self):
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

        self.assertEqual(suggestions[0]["overfit_gate_status"], "REVIEW_ONLY")
        self.assertEqual(suggestions[0]["tuning_policy"], "PROPOSAL_ONLY")
        self.assertFalse(suggestions[0]["can_auto_apply"])

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
        context["tuning_policy"] = "GUARDED_AUTO_APPLY"
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

    def test_unversioned_walk_forward_cannot_authorize_tuning(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": 2000, "max_drawdown_on_capital_multiple": -0.24},
            ],
            backtest_monthly_rows=[],
            walk_forward_summary_rows=[
                {
                    "status": "READY_FOR_WALK_FORWARD_REVIEW",
                    "simulated_periods": 6,
                    "usable_walk_forward_periods": 6,
                    "compounded_excess_return_vs_vfv": -0.12,
                    "avg_excess_return_vs_vfv": -0.03,
                    "win_rate_vs_vfv": 0.25,
                }
            ],
            walk_forward_period_rows=[
                {"evaluation_status": "SIMULATED", "excess_return_vs_vfv": -0.02},
                {"evaluation_status": "SIMULATED", "excess_return_vs_vfv": -0.03},
                {"evaluation_status": "SIMULATED", "excess_return_vs_vfv": -0.01},
                {"evaluation_status": "SIMULATED", "excess_return_vs_vfv": -0.04},
            ],
            tuning_history_rows=[],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4},
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

        self.assertEqual(suggestions[0]["walk_forward_status"], "LIMITED")
        self.assertEqual(suggestions[0]["overfit_gate_status"], "REVIEW_ONLY")
        self.assertFalse(suggestions[0]["can_auto_apply"])

    def test_young_walk_forward_remains_review_only(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": 2000, "max_drawdown_on_capital_multiple": -0.24},
            ],
            walk_forward_summary_rows=[
                {
                    "status": "EARLY_SIGNAL_ONLY",
                    "simulated_periods": 1,
                    "usable_walk_forward_periods": 1,
                    "compounded_excess_return_vs_vfv": -0.20,
                    "win_rate_vs_vfv": 0.0,
                }
            ],
            tuning_history_rows=[],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4},
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

        self.assertEqual(suggestions[0]["walk_forward_status"], "LIMITED")
        self.assertEqual(suggestions[0]["overfit_gate_status"], "REVIEW_ONLY")
        self.assertFalse(suggestions[0]["can_auto_apply"])

    def test_weak_walk_forward_regime_remains_review_only(self):
        context = build_anti_overfitting_context(
            model_metrics={"allocation_sample_count": 8, "span_days": 300},
            backtest_summary_rows=[
                {"period_years": 5, "excess_value_vs_vfv": 1000, "max_drawdown_on_capital_multiple": -0.20},
                {"period_years": 10, "excess_value_vs_vfv": 2000, "max_drawdown_on_capital_multiple": -0.24},
            ],
            walk_forward_summary_rows=[
                {
                    "status": "READY_FOR_WALK_FORWARD_REVIEW",
                    "simulated_periods": 6,
                    "usable_walk_forward_periods": 6,
                    "compounded_excess_return_vs_vfv": 0.02,
                    "avg_excess_return_vs_vfv": 0.003,
                    "win_rate_vs_vfv": 0.67,
                    "regime_coverage_status": "HAS_WEAK_REGIME",
                    "regime_count": 3,
                    "weak_regimes": "VFV_WEAK",
                }
            ],
            walk_forward_period_rows=[
                {"evaluation_status": "SIMULATED", "market_regime": "VFV_WEAK", "excess_return_vs_vfv": -0.05},
                {"evaluation_status": "SIMULATED", "market_regime": "VFV_WEAK", "excess_return_vs_vfv": -0.04},
                {"evaluation_status": "SIMULATED", "market_regime": "VFV_POSITIVE", "excess_return_vs_vfv": 0.05},
                {"evaluation_status": "SIMULATED", "market_regime": "VFV_POSITIVE", "excess_return_vs_vfv": 0.06},
            ],
            tuning_history_rows=[],
            mode="high-cagr",
            settings={"min_distinct_allocation_dates": 4},
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


if __name__ == "__main__":
    unittest.main()
