"""On-demand R1 CC→PI new-cash scenario is visible before the PI review.

Synthetic only: supplied Work screenshot/ledger, no real brokerage, source
authentication, allocation policy, price, fee quote, Project call or trade.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests


class NewCapitalPIHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.work = BlossomSessionBridgeTests()

    def cash_request(self):
        return {
            "contribution_base": "123.45",
            "allocations_pct": {"SYNTHETIC-HOLDING:TSX": "100.00"},
            "currency": "CAD",
            "as_of": "2026-10-28",
            "scope_complete": True,
            "cash_accounted_for": True,
            "same_currency_basis_verified": True,
            "instrument_identity_verified": True,
        }

    def initial(self, *, ir=True, work=True):
        packet = {
            "request": self.fx.request(
                research_needed=ir, portfolio_needed=True),
            "contribution_inputs": self.cash_request(),
        }
        if work:
            packet["work_blossom_inputs"] = self.work.report()
        else:
            packet["contribution_inputs"]["positions_base"] = {
                "SYNTHETIC-HOLDING:TSX": "80.00", "P-CASH": "20.00",
            }
        return packet

    def cli(self, packet):
        stdin, stdout, stderr = (StringIO(json.dumps(packet)), StringIO(), StringIO())
        code = main(["--output", "guided-operator"], instream=stdin,
                    outstream=stdout, errstream=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_pi_only_validated_work_cash_scenario_is_in_actual_pi_prompt(self):
        first = self.initial(ir=False)
        unchanged = deepcopy(first)
        session = complete_manual_session(
            first["request"],
            work_blossom_inputs=first["work_blossom_inputs"],
            contribution_inputs=first["contribution_inputs"])
        self.assertEqual(session["status"], "AWAITING_MANUAL_PI_DELTA")
        pi = session["handoffs_private"]["pi_request_private"]
        preview = pi["NEW_CAPITAL_FOR_REVIEW_PRIVATE"]
        self.assertEqual(preview["status"],
                         "CALLER_SUPPLIED_SCENARIO_NOT_ALLOCATION_POLICY")
        summary = preview["new_capital_summary_private"]
        self.assertEqual(summary["analysis_id"], "CASE-A")
        self.assertEqual(summary["portfolio_as_of"], "2026-10-28")
        self.assertEqual(summary["gross_status"], "GROSS_PROJECTION_ONLY")
        self.assertEqual(summary["allocations_pct"],
                         {"SYNTHETIC-HOLDING:TSX": "100.00"})
        self.assertEqual(summary["cost_status"], "NOT_SUPPLIED")
        self.assertEqual(preview["policy_or_trade_authority"], "NONE")
        self.assertNotIn("contribution_base", preview)
        self.assertNotIn("123.45", json.dumps(preview))
        self.assertNotIn("positions_base", preview)
        self.assertIn("P_LEDGER_FOR_REVIEW_PRIVATE", pi)
        self.assertNotIn("FORWARD_UNCHANGED", pi)

        rc, raw, err = self.cli(first)
        self.assertEqual((rc, err), (0, ""))
        guided = json.loads(raw)
        self.assertEqual(guided["specialist_step"], "PI_REQUEST")
        self.assertIn("NEW_CAPITAL_FOR_REVIEW_PRIVATE",
                      guided["specialist_prompt_private"])
        self.assertNotIn("123.45", guided["specialist_prompt_private"])
        self.assertNotIn('"resume_input"', guided["specialist_prompt_private"])
        self.assertEqual(first, unchanged)

        finished = complete_manual_session(
            first["request"], pi_delta=self.fx.pi(),
            contribution_inputs=first["contribution_inputs"],
            work_blossom_inputs=first["work_blossom_inputs"])
        self.assertEqual(finished["status"],
                         "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(finished["gross_contribution_private"]["status"],
                         "GROSS_PROJECTION_ONLY")
        self.assertIn("100.00",
                      finished["final_report_private"])
        self.assertEqual(finished["project_invocation"], "NONE")

    def test_combined_route_never_leaks_cash_to_ir_but_pi_gets_it_after_ir(self):
        first = self.initial()
        ir = self.fx.ir()
        before_ir = complete_manual_session(
            first["request"],
            work_blossom_inputs=first["work_blossom_inputs"],
            contribution_inputs=first["contribution_inputs"])
        self.assertEqual(before_ir["status"], "AWAITING_MANUAL_IR_CAPSULE")
        self.assertNotIn("NEW_CAPITAL_FOR_REVIEW_PRIVATE",
                         before_ir["handoffs_private"]["ir_request_private"])
        self.assertIsNone(
            before_ir["handoffs_private"]["pi_request_private"])
        after_ir = complete_manual_session(
            first["request"], ir_capsule=deepcopy(ir),
            work_blossom_inputs=first["work_blossom_inputs"],
            contribution_inputs=first["contribution_inputs"])
        self.assertEqual(after_ir["status"], "AWAITING_MANUAL_PI_DELTA")
        pi = after_ir["handoffs_private"]["pi_request_private"]
        self.assertEqual(pi["FORWARD_UNCHANGED"], ir)
        self.assertEqual(pi["NEW_CAPITAL_FOR_REVIEW_PRIVATE"][
            "new_capital_summary_private"]["gross_status"],
            "GROSS_PROJECTION_ONLY")
        finished = complete_manual_session(
            first["request"], ir_capsule=deepcopy(ir),
            pi_delta=self.fx.pi(forwarded_ir=deepcopy(ir)),
            work_blossom_inputs=first["work_blossom_inputs"],
            contribution_inputs=first["contribution_inputs"])
        self.assertEqual(
            finished["gross_contribution_private"]["status"],
            "GROSS_PROJECTION_ONLY")
        self.assertEqual(
            finished["integrated_private"]["gross_contribution_private"],
            finished["gross_contribution_private"])
        self.assertEqual(finished["readiness"], "NOT_EVALUATED")

    def test_no_authenticated_ledger_means_no_early_pi_cash_preview(self):
        first = self.initial(ir=False, work=False)
        session = complete_manual_session(
            first["request"], contribution_inputs=first["contribution_inputs"])
        self.assertEqual(session["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertNotIn("NEW_CAPITAL_FOR_REVIEW_PRIVATE",
                         session["handoffs_private"]["pi_request_private"])
        # Existing final math on independently supplied amounts still works,
        # but those unverified numbers are not shown as M3-observed PI evidence.
        finished = complete_manual_session(
            first["request"], contribution_inputs=first["contribution_inputs"],
            pi_delta=self.fx.pi())
        self.assertEqual(finished["gross_contribution_private"]["status"],
                         "GROSS_PROJECTION_ONLY")

    def test_incomplete_or_contradictory_portfolio_source_never_mints_preview(self):
        first = self.initial(ir=False)
        inconsistent = deepcopy(first)
        inconsistent["contribution_inputs"]["currency"] = "USD"
        with self.assertRaisesRegex(
                ValueError, "PI_CONTRIBUTION_CURRENCY_CONFLICTS_WITH_OBSERVATION"):
            complete_manual_session(
                inconsistent["request"],
                contribution_inputs=inconsistent["contribution_inputs"],
                work_blossom_inputs=inconsistent["work_blossom_inputs"])
        incomplete = deepcopy(first)
        incomplete["work_blossom_inputs"]["coverage_evidence"]["all_rows_visible"] = False
        with self.assertRaisesRegex(
                ValueError, "PI_CONTRIBUTION_SCOPE_CONFLICTS_WITH_OBSERVATION"):
            complete_manual_session(
                incomplete["request"], contribution_inputs=incomplete["contribution_inputs"],
                work_blossom_inputs=incomplete["work_blossom_inputs"])


if __name__ == "__main__":
    unittest.main()
