import copy
import unittest

from ai_native.strategy_return_parity import check_specialist_mode_echo
from ai_native.request_assembly import prepare_manual_handoffs
from ai_native.integrated_flow import assemble_manual_run
from ai_native.session_bridge import complete_manual_session


class SpecialistModeEchoTests(unittest.TestCase):
    def request(self, **changes):
        req = dict(ceo_initiated=True, analysis_id="SYN-MODE-ECHO",
                   as_of="2026-10-29", kind="DECISION",
                   objective="Synthetic research only",
                   strategy_id="balanced", research_needed=True,
                   portfolio_needed=True)
        req.update(changes)
        return req

    def ir(self, **changes):
        capsule = {
            "analysis_id": "SYN-MODE-ECHO", "research_as_of": "2026-10-29",
            "summary": ["SYN uncertain"], "facts": [],
            "decision_line": "No investment decision",
            "limitations": "No original source observed",
            "countercase": "SYN incomplete evidence",
            "next_action": "Verify actual sources manually",
        }
        capsule.update(changes)
        return capsule

    def pi(self, ir=None, **changes):
        delta = {
            "analysis_id": "SYN-MODE-ECHO", "portfolio_as_of": "2026-10-29",
            "room_status": "ROOM_CONDITIONAL", "summary": "SYN portfolio unverified",
            "limitations": "SYN scope unknown", "next_action": "Confirm account scope",
            "forwarded_ir": ir if ir is not None else self.ir(),
        }
        delta.update(changes)
        return delta

    def m7a_request(self):
        return dict(analysis_id="SYN-MODE-ECHO", as_of="2026-10-29",
                    kind="DECISION", objective="Synthetic research only",
                    strategy_id="balanced", method_version="UNKNOWN_NOT_LOADED")

    def test_helper_reports_echo_but_not_authentication(self):
        self.assertEqual(check_specialist_mode_echo(
            "balanced", {"strategy_id": "BALANCED"}, specialist="IR"),
            "MATCHED_SELF_REPORTED_NOT_AUTHENTICATED")
        self.assertEqual(check_specialist_mode_echo(
            "high-cagr", {"analysis_id": "SYN"}, specialist="PI"),
            "NOT_ECHOED_MODE_NOT_VERIFIED")

    def test_m1_refuses_wrong_ir_mode_before_forwarding(self):
        with self.assertRaisesRegex(ValueError, "IR_STRATEGY_MODE_MISMATCH"):
            prepare_manual_handoffs(
                self.request(), ir_capsule=self.ir(strategy_id="high-cagr")
            )

    def test_m1_forwards_original_and_annotates_unverified_echo(self):
        ir = self.ir()
        original = copy.deepcopy(ir)
        out = prepare_manual_handoffs(self.request(), ir_capsule=ir)
        pi = out["pi_request_private"]
        self.assertEqual(pi["FORWARD_UNCHANGED"], original)
        self.assertEqual(pi["forwarded_ir_mode_echo"], "NOT_ECHOED_MODE_NOT_VERIFIED")
        self.assertEqual(ir, original)

    def test_m7a_rejects_wrong_ir_mode_even_if_case_identity_matches(self):
        with self.assertRaisesRegex(ValueError, "IR_STRATEGY_MODE_MISMATCH"):
            assemble_manual_run(self.m7a_request(), self.ir(strategy_id="high-cagr"))

    def test_m7a_rejects_wrong_pi_mode_even_when_ir_forwarded_identical(self):
        ir = self.ir(strategy_id="balanced")
        with self.assertRaisesRegex(ValueError, "PI_STRATEGY_MODE_MISMATCH"):
            assemble_manual_run(
                self.m7a_request(), ir,
                pi_delta=self.pi(ir, strategy_id="modern-adaptive-browne"),
            )

    def test_m7a_absent_echo_stays_conditional_with_limitation(self):
        result = assemble_manual_run(self.m7a_request(), self.ir())
        self.assertEqual(result["specialist_mode_echo"]["IR"], "NOT_ECHOED_MODE_NOT_VERIFIED")
        self.assertIn("IR mode echo: NOT_ECHOED_MODE_NOT_VERIFIED", result["markdown"])
        self.assertIn("CONDITIONAL", result["markdown"])

    def test_pi_only_wrong_mode_refused_without_ir(self):
        req = self.request(research_needed=False, portfolio_needed=True)
        with self.assertRaisesRegex(ValueError, "PI_STRATEGY_MODE_MISMATCH"):
            complete_manual_session(
                req, pi_delta=self.pi(strategy_id="high-cagr"),
            )

    def test_pi_only_matched_echo_does_not_upgrade_method_or_authority(self):
        req = self.request(research_needed=False, portfolio_needed=True)
        result = complete_manual_session(
            req, pi_delta=self.pi(strategy_id="balanced")
        )
        self.assertEqual(result["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(result["specialist_mode_echo"]["PI"],
                         "MATCHED_SELF_REPORTED_NOT_AUTHENTICATED")
        self.assertIn("no independent specialist authentication", result["final_report_private"])
        self.assertIn("R1_POLICY_REQUIRES_CEO_APPROVAL", result["final_report_private"])

    def test_ir_pi_route_rejects_wrong_pi_even_when_ir_return_missing(self):
        with self.assertRaisesRegex(ValueError, "PI_STRATEGY_MODE_MISMATCH"):
            complete_manual_session(
                self.request(), pi_delta=self.pi(strategy_id="high-cagr")
            )

    def test_invalid_echo_and_old_objective_refused(self):
        with self.assertRaisesRegex(ValueError, "IR_STRATEGY_MODE_ECHO_INVALID"):
            check_specialist_mode_echo("balanced", {"strategy_id": None}, specialist="IR")
        with self.assertRaisesRegex(ValueError, "R1_OBJECTIVE_NOT_STRATEGY"):
            check_specialist_mode_echo("income", {}, specialist="PI")


if __name__ == "__main__":
    unittest.main()
