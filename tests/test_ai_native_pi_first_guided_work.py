"""Synthetic PI Work source-first → IR → final PI sequencing, opt-in only.

No real browser, authenticated account, stock research, or Project invocation.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests import test_ai_native_work_blossom_session_bridge as work_fixture


class PiFirstGuidedWorkTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.work = work_fixture.BlossomSessionBridgeTests()

    def call(self, case):
        out, err = StringIO(), StringIO()
        rc = main(["--output", "guided-operator"],
                  instream=StringIO(json.dumps(case)),
                  outstream=out, errstream=err)
        return rc, out.getvalue(), err.getvalue()

    def initial(self):
        return {"request": self.fx.request(
            research_needed=True, portfolio_needed=True,
            portfolio_source_first=True,
            blossom_target_url="https://www.blossomsocial.com/users/SYNTHETIC"
        )}

    def work_return(self, first, packet):
        return {
            "pi_capture_continuation_private":
                first["pi_capture_continuation_private"],
            "work_portfolio_result": packet,
        }

    def test_first_step_is_only_pi_work_not_parallel_ir(self):
        source = self.initial()
        original = deepcopy(source)
        rc, body, err = self.call(source)
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(body)
        self.assertEqual(first["specialist_step"], "PI_WORK_CAPTURE")
        self.assertEqual(first["status"], "PRIVATE_PI_WORK_CAPTURE_PENDING_MANUAL_ONLY")
        self.assertIn("PI-WORK-PORTFOLIO-R1.5", first["specialist_prompt_private"])
        self.assertIn("BLOSSOM_TARGET_URL", first["specialist_prompt_private"])
        self.assertNotIn("IR_REQUEST", first["specialist_prompt_private"])
        self.assertNotIn("SYNTHETIC_ACCOUNT_SECRET", first["specialist_prompt_private"])
        self.assertEqual(first["project_invocation"], "NONE")
        self.assertEqual(first["method_load_verification"], "NOT_PERFORMED")
        self.assertEqual(source, original)

    def test_private_observation_then_ir_then_final_pi(self):
        first = json.loads(self.call(self.initial())[1])
        work = self.work.report()
        result = self.work_return(first, {"work_blossom_inputs": work})
        original = deepcopy(result)
        rc, body, err = self.call(result)
        self.assertEqual((rc, err), (0, ""))
        after_source = json.loads(body)
        self.assertEqual(after_source["specialist_step"], "IR_REQUEST")
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", body)
        resume = after_source["operator_packet_private"]["continuation_private"]
        self.assertNotIn("work_blossom_inputs", json.dumps(resume))
        self.assertIn("observation_inputs", resume["resume_input"])
        self.assertEqual(result, original)

        ir = self.fx.ir()
        after_ir_input = {
            "continuation_private": resume,
            "specialist_result": {"IR_CAPSULE": ir},
        }
        rc, body, err = self.call(after_ir_input)
        self.assertEqual((rc, err), (0, ""))
        after_ir = json.loads(body)
        self.assertEqual(after_ir["specialist_step"], "PI_REQUEST")
        original_ir = after_ir["operator_packet_private"][
            "continuation_private"]["next_handoff"]["PI_REQUEST"]["FORWARD_UNCHANGED"]
        self.assertEqual(original_ir, ir)

        final = {
            "continuation_private": after_ir["operator_packet_private"][
                "continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fx.pi(),
                "FORWARD_UNCHANGED": deepcopy(ir),
            },
        }
        rc, body, err = self.call(final)
        self.assertEqual((rc, err), (0, ""))
        result = json.loads(body)
        self.assertIsNone(result["specialist_prompt_private"])
        self.assertIsNone(result["operator_packet_private"]["continuation_private"])
        self.assertEqual(result["project_invocation"], "NONE")

    def test_unavailable_work_still_allows_original_ir_first(self):
        first = json.loads(self.call(self.initial())[1])
        unavailable = {"capture_mode": "WORK_BROWSER",
                       "view_status": "UNAVAILABLE",
                       "analysis_id": "CASE-A",
                       "analysis_as_of": "2026-10-28"}
        rc, body, err = self.call(self.work_return(
            first, {"work_blossom_inputs": unavailable}))
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(json.loads(body)["specialist_step"], "IR_REQUEST")

    def test_public_reference_is_not_promoted_into_private_portfolio(self):
        first = json.loads(self.call(self.initial())[1])
        rc, body, err = self.call(self.work_return(
            first, {"public_portfolio_reference": {"status": "PUBLIC_REFERENCE_ONLY"}}))
        self.assertEqual((rc, body), (2, ""))
        self.assertIn("PI_FIRST_CAPTURE_PUBLIC_SEPARATE_ROUTE", err)

    def test_invalid_capture_url_identity_or_forged_continuation_blocked(self):
        for url in ("https://evil.example/users/SYN", 
                    "http://www.blossomsocial.com/users/SYN",
                    "https://www.blossomsocial.com/users/SYN?token=private",
                    "https://www.blossomsocial.com/users/"):
            case = self.initial()
            case["request"]["blossom_target_url"] = url
            with self.subTest(url=url):
                rc, body, err = self.call(case)
                self.assertEqual((rc, body), (3, ""))
                self.assertIn("private guided operator packet unavailable", err)
        first = json.loads(self.call(self.initial())[1])
        mismatched = self.work.report(analysis_id="DIFFERENT")
        rc, body, err = self.call(
            self.work_return(first, {"work_blossom_inputs": mismatched}))
        self.assertEqual((rc, body), (2, ""))
        self.assertIn("PI_FIRST_CAPTURE_SOURCE_INVALID", err)
        forged = deepcopy(first["pi_capture_continuation_private"])
        forged["analysis_id"] = "NEW"
        rc, body, err = self.call({
            "pi_capture_continuation_private": forged,
            "work_portfolio_result": {"work_blossom_inputs": self.work.report()},
        })
        self.assertEqual((rc, body), (2, ""))
        self.assertIn("PI_FIRST_CAPTURE_CONTINUATION_INVALID", err)


if __name__ == "__main__":
    unittest.main()
