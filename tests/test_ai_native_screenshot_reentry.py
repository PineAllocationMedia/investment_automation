"""Synthetic visual Work-unavailable -> human screenshot -> guided PI continuation.

Tests the original manual M1/M3/IR/PI contracts, not real Blossom access,
source authenticity, ChatGPT Project invocation, archiving or trading.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests


class ManualScreenshotReentryTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.visual = BlossomSessionBridgeTests()

    def cli(self, packet, output="guided-operator"):
        instream = StringIO(json.dumps(packet, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        code = main(["--output", output], instream=instream,
                    outstream=out, errstream=err)
        return code, out.getvalue(), err.getvalue()

    def unavailable(self):
        return {
            "capture_mode": "WORK_BROWSER", "view_status": "UNAVAILABLE",
            "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
            "raw_html": "SECRET_WORK_BROWSER_TOKEN_NEVER_TRANSFER",
        }

    def screenshot(self, **changes):
        # An explicitly supplied screenshot transcript. This contains no
        # browser session, screenshot pixels, page URL or credential field.
        raw = self.visual.report(mode="USER_SCREENSHOT")
        for key in ("browser_hostname", "work_reported_signed_in", "raw_html"):
            raw.pop(key, None)
        raw.update(changes)
        return raw

    def after_original_ir(self, *, memory=False):
        request = self.fx.request(
            portfolio_needed=True, subject_id="SYN-ISSUER")
        start = {
            "request": request,
            "work_portfolio_result": {
                "work_blossom_inputs": self.unavailable()},
        }
        if memory:
            start["memory_inputs"] = {
                "report_id": "SYN-SCREENSHOT-R1",
                "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            }
        rc, body, err = self.cli(start)
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(body)
        self.assertEqual(first["specialist_step"], "IR_REQUEST")
        ir = self.fx.ir()
        resume = first["operator_packet_private"]["continuation_private"]
        self.assertNotIn("SECRET_WORK_BROWSER_TOKEN_NEVER_TRANSFER",
                         json.dumps(resume))
        returned = {
            "continuation_private": resume,
            "specialist_result": {"IR_CAPSULE": ir},
        }
        rc, body, err = self.cli(returned)
        self.assertEqual((rc, err), (0, ""))
        pending = json.loads(body)
        self.assertEqual(
            pending["operator_packet_private"]["session"]["status"],
            "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        self.assertIsNone(pending["specialist_step"])
        self.assertIsNone(
            pending["operator_packet_private"]["continuation_private"])
        # The saved pre-return CC resume, plus independent original IR, is the
        # only source of truth for explicitly restarting the screenshot route.
        pending_session = deepcopy(resume["resume_input"])
        pending_session["specialist_result"] = {"IR_CAPSULE": deepcopy(ir)}
        self.assertEqual(
            set(pending_session["work_blossom_inputs"]),
            {"capture_mode", "view_status", "analysis_id", "analysis_as_of"})
        return pending_session, ir

    def test_stalled_ir_then_screenshot_resumes_pi_then_final_report(self):
        pending, original_ir = self.after_original_ir()
        untouched = deepcopy(pending)
        screenshot = self.screenshot()
        screenshot_before = deepcopy(screenshot)
        rc, body, err = self.cli({
            "pending_session": pending,
            "screenshot_work_inputs": screenshot,
        })
        self.assertEqual((rc, err), (0, ""))
        resumed = json.loads(body)
        self.assertEqual(resumed["specialist_step"], "PI_REQUEST")
        self.assertIn("Recipient: Portfolio Intelligence (PI)",
                      resumed["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", resumed["specialist_prompt_private"])
        self.assertNotIn("SECRET_WORK_BROWSER_TOKEN_NEVER_TRANSFER", body)
        self.assertNotIn('"resume_input"',
                         resumed["specialist_prompt_private"])
        self.assertEqual(pending, untouched)
        self.assertEqual(screenshot, screenshot_before)
        operator = resumed["operator_packet_private"]
        self.assertEqual(operator["session"]["status"],
                         "AWAITING_MANUAL_PI_DELTA")
        next_step = operator["continuation_private"]
        self.assertEqual(
            next_step["next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"],
            original_ir)
        self.assertEqual(
            next_step["next_handoff"]["PI_REQUEST"][
                "P_LEDGER_FOR_REVIEW_PRIVATE"]["source_type"],
            "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertNotIn("work_blossom_inputs",
                         next_step["resume_input"])
        self.assertEqual(
            next_step["resume_input"]["observation_inputs"]["positions"][0][
                "security_id"], "SYNTHETIC-HOLDING:TSX")
        returned = {
            "continuation_private": next_step,
            "specialist_result": {
                "PI_DELTA": self.fx.pi(),
                "FORWARD_UNCHANGED": deepcopy(original_ir),
            },
        }
        rc, final, err = self.cli(returned)
        self.assertEqual((rc, err), (0, ""))
        finished = json.loads(final)
        self.assertIsNone(finished["specialist_step"])
        self.assertIsNone(
            finished["operator_packet_private"]["continuation_private"])
        self.assertIn("Investment decision research",
                      finished["operator_packet_private"]["report_private"])
        self.assertNotIn("SECRET_WORK_BROWSER_TOKEN_NEVER_TRANSFER", final)
        self.assertEqual(finished["trading_authority"], "NONE")
        self.assertEqual(finished["project_invocation"], "NONE")

    def test_private_guided_closeout_can_resume_after_manual_visual_fallback(self):
        pending, original_ir = self.after_original_ir(memory=True)
        rc, body, err = self.cli({
            "pending_session": pending,
            "screenshot_work_inputs": self.screenshot(),
        }, "guided-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        next_step = json.loads(body)
        self.assertEqual(next_step["status"],
                         "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_PENDING_MANUAL_HANDOFF")
        self.assertIsNone(next_step["private_integrated_closeout"])
        pi = next_step["guided_operator_private"]
        self.assertEqual(pi["specialist_step"], "PI_REQUEST")
        rc, body, err = self.cli({
            "continuation_private": pi["operator_packet_private"][
                "continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fx.pi(),
                "FORWARD_UNCHANGED": deepcopy(original_ir),
            },
        }, "guided-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        complete = json.loads(body)
        self.assertEqual(complete["status"],
                         "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        archive = complete["private_integrated_closeout"]
        self.assertEqual(archive["status"],
                         "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        self.assertEqual(archive[
            "private_portfolio_snapshot_envelope"]["private_snapshot"][
            "original_observation_inputs"]["source_type"],
            "PRIVATE_SCREENSHOT_TRANSCRIPTION")
        self.assertEqual(archive["storage"], "NONE")
        self.assertEqual(complete["archive_protection"], "NOT_ESTABLISHED")

    def test_pi_only_unavailable_work_can_resume_with_new_screenshot(self):
        request = self.fx.request(
            research_needed=False, portfolio_needed=True)
        pending = {
            "request": request,
            "work_blossom_inputs": {
                key: val for key, val in self.unavailable().items()
                if key != "raw_html"
            },
        }
        code, status, err = self.cli(pending, "status")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(status)["status"],
                         "AWAITING_MANUAL_PORTFOLIO_SCREENSHOT")
        rc, body, err = self.cli({
            "pending_session": pending,
            "screenshot_work_inputs": self.screenshot(),
        })
        self.assertEqual((rc, err), (0, ""))
        packet = json.loads(body)
        self.assertEqual(packet["specialist_step"], "PI_REQUEST")
        step = packet["operator_packet_private"]["continuation_private"]
        self.assertNotIn("FORWARD_UNCHANGED",
                         step["next_handoff"]["PI_REQUEST"])
        rc, body, err = self.cli({
            "continuation_private": step,
            "specialist_result": {"PI_DELTA": self.fx.pi()},
        })
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(
            json.loads(body)["operator_packet_private"]["session"]["status"],
            "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")

    def test_wrong_phase_mixed_sources_and_browser_claim_fail_closed(self):
        pending, _ = self.after_original_ir()
        invalid = []
        no_ir = deepcopy(pending)
        no_ir.pop("specialist_result")
        invalid.append((no_ir, self.screenshot(), "SCREENSHOT_REENTRY_NOT_PENDING"))
        bad_scope = deepcopy(pending)
        bad_scope["work_blossom_inputs"]["analysis_id"] = "NOT-THE-CASE"
        invalid.append((bad_scope, self.screenshot(), "SCREENSHOT_REENTRY_INPUT_INVALID"))
        mixed = deepcopy(pending)
        mixed["observation_inputs"] = {}
        invalid.append((mixed, self.screenshot(), "SCREENSHOT_REENTRY_INPUT_INVALID"))
        for work, errcode in (
            (self.screenshot(analysis_id="OTHER"), "SCREENSHOT_REENTRY_CASE_MISMATCH"),
            (self.screenshot(capture_mode="WORK_BROWSER"), "SCREENSHOT_REENTRY_SOURCE_INVALID"),
            (self.screenshot(raw_html="SENSITIVE_TOKEN"), "SCREENSHOT_REENTRY_SOURCE_INVALID"),
            (self.screenshot(browser_hostname="www.blossomsocial.com"),
             "SCREENSHOT_REENTRY_SOURCE_INVALID"),
            (self.screenshot(work_reported_signed_in=True),
             "SCREENSHOT_REENTRY_SOURCE_INVALID"),
        ):
            invalid.append((pending, work, errcode))
        for earlier, sight, expected in invalid:
            with self.subTest(expected=expected, new_fields=list(sight)):
                rc, output, err = self.cli({
                    "pending_session": earlier,
                    "screenshot_work_inputs": sight,
                })
                self.assertEqual((rc, output), (2, ""))
                self.assertIn(expected, err)
                self.assertNotIn("SENSITIVE_TOKEN", err)
                self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", err)


if __name__ == "__main__":
    unittest.main()
