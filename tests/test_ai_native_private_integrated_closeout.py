"""Synthetic end-to-end R1 private research + portfolio closeout contracts.

No real holdings, source authentication, archive write or Project invocation.
All routes use the existing manual session and M3 validators, not test doubles.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.private_case_integrity import verify_private_case_envelope
from ai_native.portfolio_snapshot_transfer import verify_private_portfolio_snapshot
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests


class PrivateIntegratedCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def cli(self, packet, output):
        ins = StringIO(json.dumps(packet, ensure_ascii=False))
        out, err = StringIO(), StringIO()
        result = main(["--output", output], instream=ins,
                      outstream=out, errstream=err)
        return result, out.getvalue(), err.getvalue()

    def base(self, *, work=False):
        ir = self.fx.ir()
        request = self.fx.request(portfolio_needed=True,
                                  subject_id="SYNTHETIC-ISSUER",
                                  account_context={"token": "PRIVATE_CC_CONTEXT_ONLY"})
        packet = {
            "request": request,
            "ir_capsule": ir,
            "pi_delta": self.fx.pi(forwarded_ir=deepcopy(ir)),
            "memory_inputs": {
                "report_id": "R-SYN-INTEGRATED",
                "instruction_version": "R1-SYN",
                "recorded_at": "2026-10-28",
            },
        }
        if work:
            packet["work_portfolio_result"] = {
                "work_blossom_inputs": BlossomSessionBridgeTests().report()
            }
        else:
            packet["observation_inputs"] = self.obs.kwargs(
                analysis_id="CASE-A", analysis_as_of="2026-10-28")
        return packet

    def test_explicit_combined_closeout_matches_both_original_private_exports(self):
        packet = self.base()
        prior = deepcopy(packet)
        code, body, err = self.cli(packet, "private-integrated-closeout")
        self.assertEqual((code, err), (0, ""))
        combined = json.loads(body)
        self.assertEqual(combined["status"],
                         "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        self.assertEqual(combined["operator_packet_private"]["session"]["route"],
                         "CC_IR_PI_CC")
        self.assertIsNone(combined["operator_packet_private"]["continuation_private"])
        research = json.loads(self.cli(packet, "private-closeout")[1])
        portfolio = json.loads(self.cli(packet, "private-portfolio-snapshot")[1])
        self.assertEqual(combined["private_case_envelope"],
                         research["private_case_envelope"])
        self.assertEqual(combined["operator_packet_private"],
                         research["operator_packet_private"])
        self.assertEqual(combined["private_portfolio_snapshot_envelope"],
                         portfolio)
        restored = verify_private_case_envelope(combined["private_case_envelope"])
        restored_pi = verify_private_portfolio_snapshot(
            combined["private_portfolio_snapshot_envelope"])
        self.assertEqual(restored["analysis_id"], restored_pi["analysis_id"])
        self.assertEqual(restored["as_of"], restored_pi["analysis_as_of"])
        self.assertEqual(restored_pi, packet["observation_inputs"])
        self.assertEqual(combined["storage"], "NONE")
        self.assertEqual(combined["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(combined["archive_protection"], "NOT_ESTABLISHED")
        self.assertEqual(combined["trading_authority"], "NONE")
        self.assertNotIn("PRIVATE_CC_CONTEXT_ONLY",
                         combined["operator_packet_private"]["report_private"])
        self.assertEqual(packet, prior)

        # Old opt-in research closeout still does NOT silently export holdings.
        self.assertNotIn("private_portfolio_snapshot_envelope", research)
        self.assertNotIn("SCOPE-A",
                         json.dumps(research["private_case_envelope"]))
        self.assertNotIn("SCOPE-A", self.cli(packet, "status")[1])

    def test_separately_received_ir_then_pi_resumes_into_one_private_closeout(self):
        original = self.base()
        ir, pi = original.pop("ir_capsule"), original.pop("pi_delta")
        first = self.cli(original, "operator-packet")
        self.assertEqual((first[0], first[2]), (0, ""))
        first_continue = json.loads(first[1])["continuation_private"]
        self.assertEqual(set(first_continue["next_handoff"]), {"IR_REQUEST"})
        second = self.cli({
            "continuation_private": first_continue,
            "specialist_result": {"IR_CAPSULE": ir},
        }, "resume-operator")
        self.assertEqual((second[0], second[2]), (0, ""))
        second_continue = json.loads(second[1])["continuation_private"]
        self.assertEqual(set(second_continue["next_handoff"]), {"PI_REQUEST"})
        final_input = {
            "continuation_private": second_continue,
            "specialist_result": {
                "PI_DELTA": deepcopy(pi),
                "FORWARD_UNCHANGED": deepcopy(ir),
            },
        }
        before = deepcopy(final_input)
        code, body, err = self.cli(final_input, "private-integrated-closeout")
        self.assertEqual((code, err), (0, ""))
        combined = json.loads(body)
        self.assertEqual(combined["status"],
                         "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        self.assertIsNone(combined["operator_packet_private"]["continuation_private"])
        self.assertEqual(verify_private_portfolio_snapshot(
            combined["private_portfolio_snapshot_envelope"]),
            original["observation_inputs"])
        self.assertEqual(verify_private_case_envelope(
            combined["private_case_envelope"])["original_ir_capsule"], ir)
        self.assertEqual(final_input, before)

        tampered = deepcopy(final_input)
        tampered["specialist_result"]["FORWARD_UNCHANGED"]["facts"][0][
            "claim"] = "SECRET_TAMPER"
        code, body, err = self.cli(tampered, "private-integrated-closeout")
        self.assertEqual((code, body), (2, ""))
        self.assertIn("SPECIALIST_FORWARDED_IR_MISMATCH", err)
        self.assertNotIn("SECRET_TAMPER", err)

    def test_complete_sanitized_work_uses_no_browser_token_in_combined_copy(self):
        packet = self.base(work=True)
        before = deepcopy(packet)
        code, body, err = self.cli(packet, "private-integrated-closeout")
        self.assertEqual((code, err), (0, ""))
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", body)
        self.assertNotIn("raw_html", body)
        self.assertNotIn("browser_hostname", body)
        restored = verify_private_portfolio_snapshot(
            json.loads(body)["private_portfolio_snapshot_envelope"])
        self.assertEqual(restored["source_type"],
                         "AUTHORIZED_BLOSSOM_TRANSCRIPTION")
        self.assertEqual(restored["account_scope"], "SYNTHETIC_ACCOUNT_SECRET")
        self.assertNotIn("work_reported_signed_in", restored)
        self.assertEqual(packet, before)

    def test_fail_closed_on_pending_pi_ir_only_missing_observation_or_memory(self):
        complete = self.base()
        variants = []
        ir_only = deepcopy(complete)
        ir_only["request"]["portfolio_needed"] = False
        ir_only.pop("pi_delta")
        ir_only.pop("observation_inputs")
        variants.append(ir_only)
        pending = deepcopy(complete)
        pending.pop("pi_delta")
        variants.append(pending)
        no_observation = deepcopy(complete)
        no_observation.pop("observation_inputs")
        variants.append(no_observation)
        no_memory = deepcopy(complete)
        no_memory.pop("memory_inputs")
        variants.append(no_memory)
        for packet in variants:
            with self.subTest(keys=sorted(packet)):
                code, body, err = self.cli(packet, "private-integrated-closeout")
                self.assertEqual((code, body), (3, ""))
                self.assertIn("private integrated closeout unavailable", err)
                self.assertNotIn("PRIVATE_CC_CONTEXT_ONLY", err)

    def test_pi_only_private_integrated_closeout_has_no_fabricated_ir(self):
        packet = {
            "request": self.fx.request(research_needed=False,
                                       portfolio_needed=True),
            "pi_delta": self.fx.pi(),
            "observation_inputs": self.obs.kwargs(
                analysis_id="CASE-A", analysis_as_of="2026-10-28"),
        }
        code, body, err = self.cli(packet, "private-integrated-closeout")
        self.assertEqual((code, body), (3, ""))
        self.assertIn("private integrated closeout unavailable", err)
        self.assertEqual(self.cli(packet, "private-portfolio-snapshot")[0], 0)

    def test_default_status_never_includes_exported_private_positions(self):
        packet = self.base()
        status = self.cli(packet, "status")
        self.assertEqual((status[0], status[2]), (0, ""))
        self.assertNotIn("SCOPE-A", status[1])
        self.assertNotIn("ABC:TSX", status[1])
        self.assertNotIn("private_case_envelope", status[1])
        self.assertNotIn("private_portfolio_snapshot_envelope", status[1])


    def test_one_guided_initial_session_emits_no_archive_until_final_ir_pi(self):
        original = self.base()
        ir, pi = original.pop("ir_capsule"), original.pop("pi_delta")
        retained = deepcopy(original)
        rc, out, err = self.cli(original, "guided-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(out)
        self.assertEqual(first["status"],
                         "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_PENDING_MANUAL_HANDOFF")
        self.assertIsNone(first["private_integrated_closeout"])
        guided = first["guided_operator_private"]
        self.assertEqual(guided["specialist_step"], "IR_REQUEST")
        self.assertIn("Recipient: Investment Research (IR)",
                      guided["specialist_prompt_private"])
        self.assertIn("METHOD_PATH:", guided["specialist_prompt_private"])
        self.assertNotIn('"resume_input"',
                         guided["specialist_prompt_private"])
        self.assertNotIn("SCOPE-A", guided["specialist_prompt_private"])
        self.assertEqual(guided["storage"], "NONE")
        self.assertEqual(original, retained)

        rc, out, err = self.cli({
            "continuation_private":
                guided["operator_packet_private"]["continuation_private"],
            "specialist_result": {"IR_CAPSULE": ir},
        }, "guided-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        second = json.loads(out)
        self.assertEqual(second["status"],
                         "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_PENDING_MANUAL_HANDOFF")
        self.assertIsNone(second["private_integrated_closeout"])
        pi_guided = second["guided_operator_private"]
        self.assertEqual(pi_guided["specialist_step"], "PI_REQUEST")
        self.assertIn("Recipient: Portfolio Intelligence (PI)",
                      pi_guided["specialist_prompt_private"])
        self.assertEqual(pi_guided["operator_packet_private"][
            "continuation_private"]["next_handoff"]["PI_REQUEST"][
                "FORWARD_UNCHANGED"], ir)

        returned = {
            "continuation_private": pi_guided["operator_packet_private"][
                "continuation_private"],
            "specialist_result": {
                "PI_DELTA": deepcopy(pi),
                "FORWARD_UNCHANGED": deepcopy(ir),
            },
        }
        untouched = deepcopy(returned)
        rc, out, err = self.cli(returned, "guided-integrated-closeout")
        self.assertEqual((rc, err), (0, ""))
        completed = json.loads(out)
        self.assertEqual(completed["status"],
                         "PRIVATE_GUIDED_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        final = completed["private_integrated_closeout"]
        self.assertEqual(final["status"],
                         "PRIVATE_INTEGRATED_CLOSEOUT_COPY_NOT_STORED")
        self.assertEqual(final, json.loads(
            self.cli(returned, "private-integrated-closeout")[1]))
        self.assertIsNone(completed["guided_operator_private"]["specialist_step"])
        self.assertIsNone(completed["guided_operator_private"][
            "operator_packet_private"]["continuation_private"])
        self.assertEqual(verify_private_portfolio_snapshot(
            final["private_portfolio_snapshot_envelope"]),
            retained["observation_inputs"])
        self.assertEqual(verify_private_case_envelope(
            final["private_case_envelope"])["original_ir_capsule"], ir)
        self.assertEqual(returned, untouched)
        self.assertEqual(completed["archive_protection"], "NOT_ESTABLISHED")
        self.assertEqual(completed["project_invocation"], "NONE")
        self.assertEqual(completed["storage"], "NONE")
        self.assertEqual(completed["trading_authority"], "NONE")

    def test_guided_integrated_closeout_only_exports_after_explicit_final_prerequisites(self):
        packet = self.base()
        missing_memory = deepcopy(packet)
        missing_memory.pop("memory_inputs")
        missing_observation = deepcopy(packet)
        missing_observation.pop("observation_inputs")
        for bad in (missing_memory, missing_observation):
            with self.subTest(keys=sorted(bad)):
                rc, out, err = self.cli(bad, "guided-integrated-closeout")
                self.assertEqual((rc, out), (3, ""))
                self.assertIn("private guided operator packet unavailable", err)
                self.assertNotIn("PRIVATE_CC_CONTEXT_ONLY", err)

        # A report-only guided session never silently includes an archive.
        rc, out, err = self.cli(packet, "guided-operator")
        self.assertEqual((rc, err), (0, ""))
        self.assertNotIn("private_integrated_closeout", out)
        self.assertNotIn("private_case_envelope", out)
        self.assertNotIn("private_portfolio_snapshot_envelope", out)

    def test_guided_integrated_closeout_refuses_forged_specialist_original_ir(self):
        packet = self.base()
        original_ir, pi = packet.pop("ir_capsule"), packet.pop("pi_delta")
        first = json.loads(self.cli(packet, "guided-integrated-closeout")[1])
        second = json.loads(self.cli({
            "continuation_private": first["guided_operator_private"][
                "operator_packet_private"]["continuation_private"],
            "specialist_result": {"IR_CAPSULE": original_ir},
        }, "guided-integrated-closeout")[1])
        forged = deepcopy(original_ir)
        forged["facts"][0]["claim"] = "FORGED_PRIVATE_CLAIM_SENTINEL"
        rc, out, err = self.cli({
            "continuation_private": second["guided_operator_private"][
                "operator_packet_private"]["continuation_private"],
            "specialist_result": {
                "PI_DELTA": pi,
                "FORWARD_UNCHANGED": forged,
            },
        }, "guided-integrated-closeout")
        self.assertEqual((rc, out), (2, ""))
        self.assertIn("SPECIALIST_FORWARDED_IR_MISMATCH", err)
        self.assertNotIn("FORGED_PRIVATE_CLAIM_SENTINEL", err)


if __name__ == "__main__":
    unittest.main()
