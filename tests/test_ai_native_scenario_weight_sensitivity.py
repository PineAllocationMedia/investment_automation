"""Synthetic-only tests for isolated R1 displayed-weight scenario arithmetic."""
import copy
import unittest

from ai_native.scenario_weight_sensitivity import evaluate_scenario_weight_sensitivity


class ScenarioSensitivityTests(unittest.TestCase):
    def payload(self):
        return {
            "analysis_id": "SYN-SENS-1",
            "analysis_as_of": "2026-10-30",
            "strategy_id": "modern-adaptive-browne",
            "denominator_evidence": "DISPLAYED_VIEW_DENOMINATOR_CALLER_ATTESTED",
            "positions": [
                {"p_id": "P1", "weight_pct": "60", "function": "GROWTH"},
                {"p_id": "P2", "weight_pct": "40", "function": "DEFLATION_DURATION"},
            ],
            "scenarios": [{
                "scenario_id": "SYN_STOCKS_DOWN_BONDS_UP",
                "as_of": "2026-10-29",
                "assumption_source_ref": "SYNTHETIC_INPUT_ONLY",
                "shocks_pct_by_p_id": {"P1": "-30", "P2": "5"},
            }],
        }

    def test_full_scope_hypothetical_only_and_inputs_immutable(self):
        p = self.payload()
        original = copy.deepcopy(p)
        out = evaluate_scenario_weight_sensitivity(**p)
        self.assertEqual(p, original)
        row = out["scenarios"][0]
        self.assertEqual(row["status"], "COMPLETE_DISPLAYED_VIEW_HYPOTHETICAL_ONLY")
        self.assertEqual(row["scoped_displayed_hypothetical_return_pct"], "-16.00")
        self.assertEqual(row["by_caller_reported_function_pct_points"],
                         {"DEFLATION_DURATION": "2.00", "GROWTH": "-18.00"})
        self.assertEqual(row["unmodeled_weight_pct"], "0.00")
        self.assertEqual(out["policy_authority"], "NONE")
        self.assertEqual(out["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(out["historical_calibration"], "NOT_PERFORMED")
        self.assertEqual(out["investment_allocation_or_trade_authority"], "NONE")
        self.assertFalse(row["is_drawdown_or_loss_bound"])

    def test_simultaneous_losses_are_not_historical_calibration(self):
        p = self.payload()
        p["scenarios"][0]["shocks_pct_by_p_id"] = {"P1": "-30", "P2": "-12"}
        row = evaluate_scenario_weight_sensitivity(**p)["scenarios"][0]
        self.assertEqual(row["scoped_displayed_hypothetical_return_pct"], "-22.80")
        self.assertEqual(row["historical_calibration"], "NOT_PERFORMED")

    def test_missing_shock_and_partial_positions_cannot_be_total_return(self):
        p = self.payload()
        p["scenarios"][0]["shocks_pct_by_p_id"] = {"P1": "-30"}
        row = evaluate_scenario_weight_sensitivity(**p)["scenarios"][0]
        self.assertEqual(row["status"], "PARTIAL_SCOPED_SENSITIVITY_ONLY")
        self.assertEqual(row["partial_contribution_pct_points"], "-18.00")
        self.assertEqual(row["unmodeled_weight_pct"], "40.00")
        self.assertIsNone(row["scoped_displayed_hypothetical_return_pct"])
        p = self.payload()
        p["positions"][1]["weight_pct"] = "20"
        row = evaluate_scenario_weight_sensitivity(**p)["scenarios"][0]
        self.assertEqual(row["status"], "PARTIAL_SCOPED_SENSITIVITY_ONLY")
        self.assertEqual(row["unmodeled_weight_pct"], "20.00")
        self.assertIsNone(row["scoped_displayed_hypothetical_return_pct"])

    def test_100_point_2_is_not_silently_normalized(self):
        p = self.payload()
        p["positions"][1]["weight_pct"] = "40.2"
        out = evaluate_scenario_weight_sensitivity(**p)
        self.assertEqual(out["displayed_weight_total_pct"], "100.20")
        row = out["scenarios"][0]
        self.assertEqual(row["status"], "UNAVAILABLE_WEIGHTS_EXCEED_100_NO_NORMALIZATION")
        self.assertIsNone(row["partial_contribution_pct_points"])
        self.assertIsNone(row["scoped_displayed_hypothetical_return_pct"])

    def test_unknown_denominator_refuses_arithmetic(self):
        p = self.payload()
        p["denominator_evidence"] = "UNKNOWN"
        row = evaluate_scenario_weight_sensitivity(**p)["scenarios"][0]
        self.assertEqual(row["status"], "UNAVAILABLE_DENOMINATOR")
        self.assertIsNone(row["partial_contribution_pct_points"])

    def test_invalid_values_and_unsupported_modes_fail_closed(self):
        for field, val in [("strategy_id", "income"), ("strategy_id", "random-mode")]:
            p = self.payload()
            p[field] = val
            with self.assertRaises(ValueError):
                evaluate_scenario_weight_sensitivity(**p)
        for val in [float("nan"), "NaN", "-1", "101", "20.12345"]:
            p = self.payload()
            p["positions"][0]["weight_pct"] = val
            with self.assertRaises(ValueError):
                evaluate_scenario_weight_sensitivity(**p)
        p = self.payload()
        p["positions"][1]["p_id"] = "P1"
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            evaluate_scenario_weight_sensitivity(**p)
        p = self.payload()
        p["scenarios"][0]["as_of"] = "2026-10-31"
        with self.assertRaisesRegex(ValueError, "AFTER_ANALYSIS"):
            evaluate_scenario_weight_sensitivity(**p)
        p = self.payload()
        p["scenarios"][0]["shocks_pct_by_p_id"]["P3"] = "-10"
        with self.assertRaisesRegex(ValueError, "SUPPLIED_POSITIONS"):
            evaluate_scenario_weight_sensitivity(**p)

    def test_all_six_modes_share_arithmetic_without_policy(self):
        for mode in (
            "high-cagr", "balanced", "family-office", "rational-aggressive",
            "intelligent-dividend-harvester", "modern-adaptive-browne",
        ):
            p = self.payload()
            p["strategy_id"] = mode
            out = evaluate_scenario_weight_sensitivity(**p)
            self.assertEqual(out["policy_authority"], "NONE")
            self.assertEqual(out["scenarios"][0]["scoped_displayed_hypothetical_return_pct"],
                             "-16.00")


if __name__ == "__main__":
    unittest.main()
