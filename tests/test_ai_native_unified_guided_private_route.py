"""One on-demand private CC route -> the THREE existing guided closeout flows.

All data synthetic; local method-blob parity is not Project installation.
No real Work, portfolio authentication, archive, policy approval or trade.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests


class UnifiedGuidedPrivateRouteTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def call(self, packet, mode="guided-private-closeout"):
        stdin = StringIO(json.dumps(packet, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        rc = main(["--output", mode], instream=stdin,
                  outstream=out, errstream=err)
        return rc, out.getvalue(), err.getvalue()

    def same_as_specific(self, packet, specific):
        a = self.call(packet)
        b = self.call(packet, specific)
        self.assertEqual(a, b)
        self.assertEqual((a[0], a[2]), (0, ""))
        return json.loads(a[1])

    def memory(self):
        return {
            "report_id": "R-UNIFIED-CASE",
            "instruction_version": "R1-SYN",
            "recorded_at": "2026-10-28",
        }

    def observation(self):
        return self.obs.kwargs(
            analysis_id="CASE-A", analysis_as_of="2026-10-28")

    def resume(self, response, result):
        return {
            "continuation_private": response["guided_operator_private"][
                "operator_packet_private"]["continuation_private"],
            "specialist_result": result,
        }

    def test_ir_only_new_and_return_parity_without_pi_or_automatic_archive(self):
        initial = {
            "request": self.fx.request(
                subject_id="SYN-UNIFIED-RESEARCH"),
            "memory_inputs": self.memory(),
        }
        unchanged = deepcopy(initial)
        first = self.same_as_specific(initial, "guided-research-closeout")
        self.assertEqual(
            first["status"],
            "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_PENDING_MANUAL_IR")
        self.assertEqual(first["guided_operator_private"]["specialist_step"],
                         "IR_REQUEST")
        self.assertIsNone(first["private_research_closeout"])
        self.assertEqual(initial, unchanged)
        original_ir = self.fx.ir()
        ret = self.resume(first, {"IR_CAPSULE": original_ir})
        final = self.same_as_specific(ret, "guided-research-closeout")
        self.assertEqual(
            final["status"],
            "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_COPY_NOT_STORED")
        self.assertIsNotNone(final["private_research_closeout"][
            "private_case_envelope"])
        self.assertNotIn("private_portfolio_snapshot_envelope",
                         json.dumps(final))
        self.assertEqual(final["storage"], "NONE")
        self.assertEqual(final["trading_authority"], "NONE")

    def test_pi_only_new_and_return_parity_keeps_original_m3_private(self):
        initial = {
            "request": self.fx.request(
                research_needed=False, portfolio_needed=True),
            "observation_inputs": self.observation(),
        }
        first = self.same_as_specific(initial, "guided-portfolio-closeout")
        self.assertEqual(
            first["status"],
            "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_PENDING_MANUAL_PI")
        self.assertEqual(first["guided_operator_private"]["specialist_step"],
                         "PI_REQUEST")
        self.assertIsNone(first["private_portfolio_closeout"])
        ret = self.resume(first, {"PI_DELTA": self.fx.pi()})
        final = self.same_as_specific(ret, "guided-portfolio-closeout")
        self.assertEqual(
            final["status"],
            "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        self.assertIsNotNone(final["private_portfolio_closeout"][
            "private_portfolio_snapshot_envelope"])
        self.assertNotIn("private_case_envelope", json.dumps(final))
        self.assertEqual(final["project_invocation"], "NONE")

    def test_combined_route_ir_first_then_pi_and_both_private_records(self):
        original_ir = self.fx.ir()
        initial = {
            "request": self.fx.request(portfolio_needed=True),
            "memory_inputs": self.memory(),
            "observation_inputs": self.observation(),
        }
        first = self.same_as_specific(initial, "guided-integrated-closeout")
        self.assertEqual(
            first["status"],
            "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_PENDING_MANUAL_HANDOFF")
        self.assertEqual(first["guided_operator_private"]["specialist_step"],
                         "IR_REQUEST")
        self.assertIsNone(first["private_integrated_closeout"])
        self.assertNotIn("private_portfolio_snapshot_envelope",
                         first["guided_operator_private"]["specialist_prompt_private"])
        after_ir = self.same_as_specific(
            self.resume(first, {"IR_CAPSULE": original_ir}),
            "guided-integrated-closeout")
        self.assertEqual(after_ir["guided_operator_private"]["specialist_step"],
                         "PI_REQUEST")
        self.assertIsNone(after_ir["private_integrated_closeout"])
        original_forward = after_ir["guided_operator_private"][
            "operator_packet_private"]["continuation_private"][
            "next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"]
        self.assertEqual(original_forward, original_ir)
        final = self.same_as_specific(
            self.resume(after_ir, {
                "PI_DELTA": self.fx.pi(),
                "FORWARD_UNCHANGED": deepcopy(original_ir),
            }), "guided-integrated-closeout")
        self.assertEqual(
            final["status"],
            "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        record = final["private_integrated_closeout"]
        self.assertIn("private_case_envelope", record)
        self.assertIn("private_portfolio_snapshot_envelope", record)
        self.assertEqual(final["archive_protection"], "NOT_ESTABLISHED")
        self.assertEqual(final["project_invocation"], "NONE")
        self.assertEqual(final["trading_authority"], "NONE")

    def test_no_direct_or_ambiguous_route_and_no_auto_research(self):
        cc_direct = {"request": self.fx.request(
            research_needed=False, portfolio_needed=False)}
        bad_flags = {"request": self.fx.request(
            research_needed=1, portfolio_needed=True)}
        ambiguous = {
            "request": self.fx.request(),
            "session": {"request": self.fx.request()},
        }
        for packet, error in (
            (cc_direct, "GUIDED_PRIVATE_ROUTE_SPECIALIST_REQUIRED"),
            (bad_flags, "GUIDED_PRIVATE_ROUTE_REQUEST_INVALID"),
            (ambiguous, "GUIDED_PRIVATE_ROUTE_REQUEST_INVALID"),
            ({"continuation_private": {}},
             "GUIDED_PRIVATE_ROUTE_REQUEST_INVALID"),
        ):
            with self.subTest(error=error):
                rc, body, err = self.call(packet)
                self.assertEqual((rc, body), (2, ""))
                self.assertIn(error, err)

    def test_archive_prerequisites_still_fail_before_first_specialist(self):
        missing_ir_memory = {"request": self.fx.request()}
        missing_pi_source = {"request": self.fx.request(
            research_needed=False, portfolio_needed=True)}
        combined_missing_source = {
            "request": self.fx.request(portfolio_needed=True),
            "memory_inputs": self.memory(),
        }
        for packet in (
            missing_ir_memory, missing_pi_source, combined_missing_source):
            with self.subTest(route=(packet["request"]["research_needed"],
                                     packet["request"]["portfolio_needed"])):
                self.assertEqual(self.call(packet),
                                 self.call(packet, self._specific(packet)))
                self.assertNotEqual(self.call(packet)[0], 0)

    @staticmethod
    def _specific(packet):
        request = packet["request"]
        if request["research_needed"] and request["portfolio_needed"]:
            return "guided-integrated-closeout"
        if request["research_needed"]:
            return "guided-research-closeout"
        return "guided-portfolio-closeout"

    def test_unavailable_visual_screenshot_reentry_still_uses_pi_engine(self):
        original = {
            "request": self.fx.request(
                research_needed=False, portfolio_needed=True),
            "work_portfolio_result": {
                "work_blossom_inputs": {
                    "capture_mode": "WORK_BROWSER",
                    "view_status": "UNAVAILABLE",
                    "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
                    "raw_html": "SECRET_NEVER_TRANSFER",
                },
            },
        }
        rc, body, err = self.call(original, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        retry = json.loads(body)["screenshot_reentry_input_private"]
        self.assertNotIn("SECRET_NEVER_TRANSFER", json.dumps(retry))
        from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests
        source = BlossomSessionBridgeTests().report(mode="USER_SCREENSHOT")
        for item in ("raw_html", "browser_hostname", "work_reported_signed_in"):
            source.pop(item, None)
        retry["screenshot_work_inputs"] = source
        result = self.same_as_specific(retry, "guided-portfolio-closeout")
        self.assertEqual(result["guided_operator_private"]["specialist_step"],
                         "PI_REQUEST")
        self.assertNotIn("SECRET_NEVER_TRANSFER", json.dumps(result))

    def test_explicit_prior_pi_archive_plus_new_mandate_routes_to_existing_pi(self):
        from ai_native.portfolio_snapshot_transfer import seal_private_portfolio_snapshot
        old = seal_private_portfolio_snapshot(self.observation())
        new = self.observation()
        new.update(analysis_id="CASE-B", analysis_as_of="2026-10-29",
                   observed_on="2026-10-29",
                   captured_at="2026-10-29T10:00:00-04:00")
        request = self.fx.request(
            analysis_id="CASE-B", as_of="2026-10-29",
            kind="FOLLOWUP", prior_analysis_id="CASE-A",
            objective="Manual new private snapshot comparison",
            research_needed=False, portfolio_needed=True)
        packet = {
            "private_portfolio_snapshot_envelope": old,
            "session": {
                "request": request,
                "observation_inputs": new,
            },
        }
        first = self.same_as_specific(packet, "guided-portfolio-closeout")
        self.assertEqual(first["guided_operator_private"]["specialist_step"],
                         "PI_REQUEST")
        self.assertNotIn("prior_private_portfolio_envelope",
                         first["guided_operator_private"]["specialist_prompt_private"])


if __name__ == "__main__":
    unittest.main()
