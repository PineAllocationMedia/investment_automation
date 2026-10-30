"""Synthetic CC→IR→CC guided research-and-private-copy contract, no live Projects.

No research source authentication, method installation, secure archive, trading,
automatic Project invocation or real-case acceptance is performed.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.private_case_integrity import verify_private_case_envelope
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class GuidedResearchCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def cli(self, packet, output="guided-research-closeout"):
        inp = StringIO(json.dumps(packet, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        rc = main(["--output", output], instream=inp,
                  outstream=out, errstream=err)
        return rc, out.getvalue(), err.getvalue()

    def case(self):
        return {
            "request": self.fx.request(
                subject_id="SYN-RESEARCH-ONLY",
                strategy_id="high-cagr"),
            "memory_inputs": {
                "report_id": "R-SYN-GUIDED-IR",
                "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }

    def test_new_ir_only_session_reuses_verified_prompt_then_original_private_copy(self):
        initial = self.case()
        initial_copy = deepcopy(initial)
        rc, first_text, err = self.cli(initial)
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(first_text)
        self.assertEqual(
            first["status"], "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_PENDING_MANUAL_IR")
        self.assertIsNone(first["private_research_closeout"])
        guided = first["guided_operator_private"]
        self.assertEqual(guided["specialist_step"], "IR_REQUEST")
        self.assertIn("Recipient: Investment Research (IR)",
                      guided["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", guided["specialist_prompt_private"])
        self.assertNotIn('"resume_input"', guided["specialist_prompt_private"])
        self.assertEqual(guided["copy_to_specialist"], "specialist_prompt_private")
        self.assertEqual(initial, initial_copy)

        original_ir = self.fx.ir()
        original_ir["facts"][0]["claim"] = "PRIVATE_RESEARCH_CLAIM_NOT_PUBLIC"
        returned = {
            "continuation_private": guided["operator_packet_private"][
                "continuation_private"],
            "specialist_result": {"IR_CAPSULE": deepcopy(original_ir)},
        }
        before = deepcopy(returned)
        rc, final_text, err = self.cli(returned)
        self.assertEqual((rc, err), (0, ""))
        last = json.loads(final_text)
        self.assertEqual(
            last["status"], "PRIVATE_GUIDED_RESEARCH_CLOSEOUT_COPY_NOT_STORED")
        self.assertIsNone(last["guided_operator_private"]["specialist_step"])
        self.assertIsNone(last["guided_operator_private"][
            "operator_packet_private"]["continuation_private"])
        final_copy = last["private_research_closeout"]
        self.assertEqual(
            final_copy["status"], "PRIVATE_RESEARCH_CLOSEOUT_COPY_NOT_STORED")
        self.assertEqual(
            final_copy, json.loads(self.cli(returned, "private-closeout")[1]))
        retained = verify_private_case_envelope(
            final_copy["private_case_envelope"])
        self.assertEqual(retained["original_ir_capsule"], original_ir)
        self.assertEqual(retained["original_request"]["analysis_id"], "CASE-A")
        self.assertIn("Investment decision research",
                      final_copy["operator_packet_private"]["report_private"])
        self.assertEqual(last["archive_protection"], "NOT_ESTABLISHED")
        self.assertEqual(last["project_invocation"], "NONE")
        self.assertEqual(last["storage"], "NONE")
        self.assertEqual(last["trading_authority"], "NONE")
        self.assertNotIn("private_portfolio_snapshot_envelope", final_text)
        self.assertEqual(returned, before)

    def test_ir_only_missing_memory_or_invalid_metadata_fails_before_prompt(self):
        original = self.case()
        missing = deepcopy(original)
        missing.pop("memory_inputs")
        invalid = deepcopy(original)
        invalid["memory_inputs"]["report_id"] = "INVALID ID"
        too_old = deepcopy(original)
        too_old["memory_inputs"]["recorded_at"] = "2026-10-27"
        unknown_key = deepcopy(original)
        unknown_key["memory_inputs"]["unexpected_private_field"] = "SECRET"
        impossible_parent = deepcopy(original)
        impossible_parent["memory_inputs"]["accessible_parent"] = {
            "report_id": "SYN-OTHER"}
        for packet, expected in (
            (unknown_key, "GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID"),
            (impossible_parent, "GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID"),
            (missing, "GUIDED_PRIVATE_CLOSEOUT_MEMORY_REQUIRED"),
            (invalid, "GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID"),
            (too_old, "GUIDED_PRIVATE_CLOSEOUT_MEMORY_METADATA_INVALID"),
        ):
            with self.subTest(expected=expected):
                rc, output, error = self.cli(packet)
                self.assertEqual((rc, output), (2, ""))
                self.assertIn(expected, error)
                self.assertNotIn("SYN-RESEARCH-ONLY", error)

        # The ordinary guided route preserves its older, broader research use.
        rc, text, err = self.cli(missing, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        self.assertNotIn("private_research_closeout", text)
        self.assertEqual(json.loads(text)["specialist_step"], "IR_REQUEST")

    def test_ir_only_archive_does_not_silently_admit_pi_or_skip_ceo_mandate(self):
        combined = self.case()
        combined["request"]["portfolio_needed"] = True
        pi_only = self.case()
        pi_only["request"].update(research_needed=False, portfolio_needed=True)
        # PI-only has no research memory by the existing M1 contract.
        pi_only.pop("memory_inputs")
        uninitiated = self.case()
        uninitiated["request"]["ceo_initiated"] = False
        for packet, expected in (
            (combined, "GUIDED_RESEARCH_CLOSEOUT_IR_ONLY_REQUIRED"),
            (pi_only, "GUIDED_RESEARCH_CLOSEOUT_IR_ONLY_REQUIRED"),
            (uninitiated, "CEO_INITIATION_REQUIRED"),
        ):
            with self.subTest(expected=expected):
                rc, output, err = self.cli(packet)
                self.assertEqual((rc, output), (2, ""))
                self.assertIn(expected, err)
                self.assertNotIn("SYN-RESEARCH-ONLY", err)


if __name__ == "__main__":
    unittest.main()
