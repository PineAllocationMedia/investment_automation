"""Synthetic PI-only guided manual handoff -> private M3 copy.

No authenticated source, secure archive, Project invocation or trade. All M3,
manual resume and Git-pinned prompt checks reuse real existing modules.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.portfolio_snapshot_transfer import (
    seal_private_portfolio_snapshot, verify_private_portfolio_snapshot,
)
from scripts.r1_manual_session_cli import (
    main, evaluate, _check_guided_current_m3_observation,
)
from tests.test_ai_native_portfolio_observation import ObservationTests
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests


class GuidedPortfolioCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()
        self.work = BlossomSessionBridgeTests()

    def cli(self, packet, output="guided-portfolio-closeout"):
        inp = StringIO(json.dumps(packet, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        code = main(["--output", output], instream=inp,
                    outstream=out, errstream=err)
        return code, out.getvalue(), err.getvalue()

    def case(self):
        return {
            "request": self.fx.request(
                research_needed=False, portfolio_needed=True,
                account_context={"type": "SYNTHETIC_PRIVATE"}),
            "observation_inputs": self.obs.kwargs(
                analysis_id="CASE-A", analysis_as_of="2026-10-28"),
        }

    def test_shared_m3_preflight_uses_the_original_request_for_both_routes(self):
        """PR388 regression: request binding used to be missing (NameError).

        Confirm original M3 admission in PI-only and IR+PI pending routes,
        before receiving any synthetic specialist result. Source/acceptance
        remain independently unverified.
        """
        pi_only = self.case()
        combined = deepcopy(pi_only)
        combined["request"]["research_needed"] = True
        for original in (pi_only, combined):
            with self.subTest(research=original["request"]["research_needed"]):
                checked_session = evaluate(original)
                _check_guided_current_m3_observation(
                    original, checked_session)
                bad_request = deepcopy(original)
                bad_request["request"]["analysis_id"] = "OTHER-CASE"
                with self.assertRaisesRegex(
                    ValueError,
                    "GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED",
                ):
                    _check_guided_current_m3_observation(
                        bad_request, checked_session)

    def test_pi_only_complete_manual_handoff_to_single_private_snapshot(self):
        initial = self.case()
        original = deepcopy(initial)
        code, body, err = self.cli(initial)
        self.assertEqual((code, err), (0, ""))
        first = json.loads(body)
        self.assertEqual(
            first["status"],
            "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_PENDING_MANUAL_PI")
        self.assertIsNone(first["private_portfolio_closeout"])
        guided = first["guided_operator_private"]
        self.assertEqual(guided["specialist_step"], "PI_REQUEST")
        self.assertIn("Recipient: Portfolio Intelligence (PI)",
                      guided["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", guided["specialist_prompt_private"])
        self.assertNotIn('"resume_input"', guided["specialist_prompt_private"])
        self.assertEqual(guided["copy_to_specialist"], "specialist_prompt_private")
        self.assertEqual(initial, original)

        returned = {
            "continuation_private": guided["operator_packet_private"][
                "continuation_private"],
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        }
        unchanged = deepcopy(returned)
        code, final_body, err = self.cli(returned)
        self.assertEqual((code, err), (0, ""))
        last = json.loads(final_body)
        self.assertEqual(
            last["status"], "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        self.assertIsNone(last["guided_operator_private"]["specialist_step"])
        self.assertIsNone(last["guided_operator_private"][
            "operator_packet_private"]["continuation_private"])
        private = last["private_portfolio_closeout"]
        self.assertEqual(
            private["status"], "PRIVATE_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        self.assertEqual(
            private["private_portfolio_snapshot_envelope"],
            seal_private_portfolio_snapshot(initial["observation_inputs"]))
        self.assertEqual(
            verify_private_portfolio_snapshot(
                private["private_portfolio_snapshot_envelope"]),
            initial["observation_inputs"])
        self.assertEqual(
            private["operator_packet_private"]["session"]["status"],
            "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertIsInstance(private["operator_packet_private"]["report_private"], str)
        self.assertEqual(private["archive_protection"], "NOT_ESTABLISHED")
        self.assertEqual(last["trading_authority"], "NONE")
        self.assertEqual(last["storage"], "NONE")
        self.assertEqual(last["project_invocation"], "NONE")
        self.assertNotIn("private_case_envelope", final_body)
        self.assertNotIn("IR_CAPSULE", final_body)
        self.assertEqual(returned, unchanged)

    def test_missing_private_observation_fails_before_prompt_but_normal_guide_survives(self):
        missing = {"request": self.case()["request"]}
        code, body, err = self.cli(missing)
        self.assertEqual((code, body), (2, ""))
        self.assertIn("GUIDED_PRIVATE_CLOSEOUT_CURRENT_OBSERVATION_REQUIRED", err)
        self.assertNotIn("SYNTHETIC_PRIVATE", err)
        code, body, err = self.cli(missing, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(body)["specialist_step"], "PI_REQUEST")
        self.assertNotIn("private_portfolio_closeout", body)

    def test_pi_only_snapshot_mode_rejects_ir_or_non_ceo_request(self):
        combined = self.case()
        combined["request"]["research_needed"] = True
        ir_only = self.case()
        ir_only["request"]["portfolio_needed"] = False
        ir_only.pop("observation_inputs")
        unauthorised = self.case()
        unauthorised["request"]["ceo_initiated"] = False
        for packet, error_code in (
            (combined, "GUIDED_PORTFOLIO_CLOSEOUT_PI_ONLY_REQUIRED"),
            (ir_only, "GUIDED_PORTFOLIO_CLOSEOUT_PI_ONLY_REQUIRED"),
            (unauthorised, "CEO_INITIATION_REQUIRED"),
        ):
            with self.subTest(error_code=error_code):
                code, body, err = self.cli(packet)
                self.assertEqual((code, body), (2, ""))
                self.assertIn(error_code, err)
                self.assertNotIn("SYNTHETIC_PRIVATE", err)

    def test_unavailable_work_manual_screenshot_then_same_pi_closeout(self):
        original = {
            "request": self.case()["request"],
            "work_portfolio_result": {"work_blossom_inputs": {
                "capture_mode": "WORK_BROWSER",
                "view_status": "UNAVAILABLE",
                "analysis_id": "CASE-A",
                "analysis_as_of": "2026-10-28",
                "raw_html": "RAW_WORK_TOKEN_NEVER_FORWARDED",
            }},
        }
        code, body, err = self.cli(original, "guided-operator")
        self.assertEqual((code, err), (0, ""))
        blocked = json.loads(body)
        self.assertEqual(
            blocked["operator_packet_private"]["session"]["status"],
            "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        retry = blocked["screenshot_reentry_input_private"]
        self.assertIsNone(retry["screenshot_work_inputs"])
        self.assertNotIn("RAW_WORK_TOKEN_NEVER_FORWARDED", json.dumps(retry))
        screenshot = self.work.report(mode="USER_SCREENSHOT")
        for key in ("raw_html", "browser_hostname", "work_reported_signed_in"):
            screenshot.pop(key, None)
        retry["screenshot_work_inputs"] = screenshot
        code, body, err = self.cli(retry)
        self.assertEqual((code, err), (0, ""))
        pending = json.loads(body)
        self.assertEqual(pending["status"],
                         "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_PENDING_MANUAL_PI")
        self.assertIsNone(pending["private_portfolio_closeout"])
        self.assertEqual(pending["guided_operator_private"]["specialist_step"],
                         "PI_REQUEST")
        continuation = pending["guided_operator_private"][
            "operator_packet_private"]["continuation_private"]
        self.assertEqual(continuation["resume_input"][
            "observation_inputs"]["source_type"],
            "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertNotIn("RAW_WORK_TOKEN_NEVER_FORWARDED", body)
        code, body, err = self.cli({
            "continuation_private": continuation,
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        })
        self.assertEqual((code, err), (0, ""))
        final = json.loads(body)
        self.assertEqual(final["status"],
                         "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        record = verify_private_portfolio_snapshot(
            final["private_portfolio_closeout"][
                "private_portfolio_snapshot_envelope"])
        self.assertEqual(record["source_type"],
                         "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertNotIn("RAW_WORK_TOKEN_NEVER_FORWARDED", body)
        self.assertNotIn("work_blossom_inputs", body)

    def test_work_browser_validated_capture_never_enters_portfolio_copy_raw(self):
        packet = {
            "request": self.case()["request"],
            "work_portfolio_result": {
                "work_blossom_inputs": self.work.report()
            },
        }
        code, body, err = self.cli(packet)
        self.assertEqual((code, err), (0, ""))
        pending = json.loads(body)
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", body)
        continuation = pending["guided_operator_private"][
            "operator_packet_private"]["continuation_private"]
        code, body, err = self.cli({
            "continuation_private": continuation,
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        })
        self.assertEqual((code, err), (0, ""))
        final = json.loads(body)
        original = verify_private_portfolio_snapshot(
            final["private_portfolio_closeout"][
                "private_portfolio_snapshot_envelope"])
        self.assertEqual(original["source_type"], "AUTHORIZED_BLOSSOM_TRANSCRIPTION")
        self.assertNotIn("raw_html", body)
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", body)
        self.assertEqual(final["storage"], "NONE")


if __name__ == "__main__":
    unittest.main()
