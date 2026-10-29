import copy
import unittest

from ai_native.strategy_authority import assess_r1_mode, R1_MODES
from ai_native.request_assembly import prepare_manual_handoffs
from ai_native.integrated_flow import assemble_manual_run
from ai_native.reporting import render_report


class R1StrategyAuthorityTests(unittest.TestCase):
    def test_exact_six_modes_and_no_automatic_policy_approval(self):
        self.assertEqual(len(R1_MODES), 6)
        self.assertEqual(len(set(R1_MODES)), 6)
        for mode in R1_MODES:
            result = assess_r1_mode(mode)
            self.assertEqual(result["decision_grade"], "NOT_ESTABLISHED")
            self.assertEqual(result["method_load"], "NOT_VERIFIED")
            if mode == "high-cagr":
                self.assertEqual(result["policy_authority"], "V2_HIGH_CAGR_EXISTING_SCOPE_ONLY")
            else:
                self.assertEqual(result["policy_authority"], "R1_POLICY_REQUIRES_CEO_APPROVAL")

    def test_old_objectives_cannot_be_silent_seventh_and_eighth_modes(self):
        for old_objective in ("income", "capital-preservation"):
            with self.subTest(old_objective=old_objective):
                with self.assertRaisesRegex(ValueError, "R1_OBJECTIVE_NOT_STRATEGY"):
                    assess_r1_mode(old_objective)

    def test_unrecognized_and_exploratory_labels_do_not_gain_policy(self):
        self.assertEqual(
            assess_r1_mode("EXPLORATORY")["policy_authority"],
            "EXPLORATORY_NO_STRATEGY_POLICY",
        )
        self.assertEqual(
            assess_r1_mode("future-unapproved-mode")["policy_authority"],
            "UNRECOGNIZED_R1_MODE_NO_AUTHORITY",
        )

    @staticmethod
    def request(mode):
        return {
            "ceo_initiated": True, "analysis_id": "SYN-MODES-1",
            "as_of": "2026-10-29", "kind": "DECISION",
            "objective": "Synthetic research, no allocation",
            "strategy_id": mode, "research_needed": True,
            "portfolio_needed": True, "ir_method_version": "CLAIMED_LOADED",
            "pi_method_version": "CLAIMED_LOADED",
        }

    def test_policy_gate_present_in_both_original_handoffs_and_not_caller_override(self):
        request = self.request("modern-adaptive-browne")
        request["r1_strategy_policy_authority"] = "APPROVED"  # must be ignored
        original = copy.deepcopy(request)
        first = prepare_manual_handoffs(request)
        gate = first["strategy_policy_gate"]
        self.assertEqual(gate["policy_authority"], "R1_POLICY_REQUIRES_CEO_APPROVAL")
        self.assertEqual(first["ir_request_private"]["r1_strategy_policy_authority"], gate["policy_authority"])
        self.assertEqual(first["ir_request_private"]["r1_strategy_method_load"], "NOT_VERIFIED")
        self.assertEqual(first["method_load_verification"], "NOT_PERFORMED")
        self.assertEqual(first["ir_request_private"]["method_version"], "CLAIMED_LOADED")
        capsule = {"analysis_id": "SYN-MODES-1", "research_as_of": "2026-10-29",
                   "facts": [], "summary": ["Not verified"]}
        second = prepare_manual_handoffs(request, ir_capsule=capsule)
        self.assertEqual(second["pi_request_private"]["r1_strategy_policy_authority"], gate["policy_authority"])
        self.assertEqual(second["pi_request_private"]["FORWARD_UNCHANGED"], capsule)
        self.assertEqual(request, original)

    def test_unapproved_r1_mode_is_conditional_even_if_method_label_supplied(self):
        request = {
            "analysis_id": "SYN-MODES-1", "as_of": "2026-10-29",
            "objective": "Synthetic only", "strategy_id": "balanced",
            "kind": "DECISION", "method_version": "FAKE_LOADED",
        }
        ir = {
            "analysis_id": "SYN-MODES-1", "research_as_of": "2026-10-29",
            "summary": ["Synthetic, not certified"], "facts": [],
            "limitations": "No original sources.", "countercase": "Unknown",
            "decision_line": "No trading decision", "next_action": "Human policy review",
        }
        out = assemble_manual_run(request, ir)
        self.assertEqual(out["strategy_policy_gate"]["policy_authority"], "R1_POLICY_REQUIRES_CEO_APPROVAL")
        self.assertIn("**R1 strategy policy:** R1_POLICY_REQUIRES_CEO_APPROVAL", out["markdown"])
        self.assertIn("**Status:** CONDITIONAL", out["markdown"])
        self.assertNotIn("APPROVED_BY_CEO", out["markdown"])

    def test_report_rejects_forged_policy_gate(self):
        packet = {
            "kind": "DECISION", "analysis_id": "SYN", "as_of": "2026-10-29",
            "strategy": "balanced", "method_version": "unknown", "status": "CONDITIONAL",
            "objective": "Synthetic", "decision_line": "No authority",
            "summary": ["One"], "facts": [], "countercase": "None",
            "limitations": "None", "next_action": "Review",
            "strategy_policy_gate": {"policy_authority": "APPROVED"},
        }
        with self.assertRaisesRegex(ValueError, "REPORT_R1_STRATEGY_POLICY_GATE_MISMATCH"):
            render_report(packet)


if __name__ == "__main__":
    unittest.main()
