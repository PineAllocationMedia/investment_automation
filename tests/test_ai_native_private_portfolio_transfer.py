"""Synthetic-only private M3 snapshot export / manual historical comparison.

No private accounts, real Blossom access, file writes, storage service, or
return attribution. Uses actual existing session/CLI/portfolio validators.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.portfolio_snapshot_transfer import (
    seal_private_portfolio_snapshot, verify_private_portfolio_snapshot)
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests
from tests.test_ai_native_work_blossom_session_bridge import BlossomSessionBridgeTests


class PrivatePortfolioTransferTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def cli(self, payload, output="status"):
        stdin = StringIO(json.dumps(payload))
        out, err = StringIO(), StringIO()
        code = main(["--output", output], instream=stdin,
                    outstream=out, errstream=err)
        return code, out.getvalue(), err.getvalue()

    def observation(self, *, prior=False, **patch):
        values = {
            "analysis_id": "PRIOR-CASE" if prior else "CASE-A",
            "observed_on": "2026-10-27" if prior else "2026-10-28",
            "analysis_as_of": "2026-10-27" if prior else "2026-10-28",
            "captured_at": ("2026-10-27T10:00:00-04:00" if prior
                            else "2026-10-28T10:00:00-04:00"),
            "cash_base": "200.00" if prior else "100.00",
        }
        values.update(patch)
        args = self.obs.kwargs(**values)
        args["positions"][0]["market_value_base"] = (
            "200.00" if prior else "300.00")
        return args

    def old_packet(self, *, research=False, **observation_patch):
        request = self.fx.request(
            analysis_id="PRIOR-CASE", as_of="2026-10-27",
            research_needed=research, portfolio_needed=True)
        pi = self.fx.pi(analysis_id="PRIOR-CASE",
                        portfolio_as_of="2026-10-27")
        packet = {"request": request, "pi_delta": pi,
                  "observation_inputs": self.observation(
                      prior=True, **observation_patch)}
        if research:
            ir = self.fx.ir(analysis_id="PRIOR-CASE",
                            research_as_of="2026-10-27")
            packet["ir_capsule"] = ir
            pi["forwarded_ir"] = deepcopy(ir)
        return packet

    def current_packet(self, *, research=False, **observation_patch):
        request = self.fx.request(
            kind="FOLLOWUP", prior_analysis_id="PRIOR-CASE",
            research_needed=research, portfolio_needed=True)
        packet = {"request": request, "pi_delta": self.fx.pi(),
                  "observation_inputs": self.observation(**observation_patch)}
        if research:
            ir = self.fx.ir()
            packet["ir_capsule"] = ir
            packet["pi_delta"]["forwarded_ir"] = deepcopy(ir)
        return packet

    def seal_old(self, *, research=False, **kwargs):
        code, body, err = self.cli(
            self.old_packet(research=research, **kwargs),
            "private-portfolio-snapshot")
        self.assertEqual((code, err), (0, ""))
        return json.loads(body)

    def test_pi_only_manual_archive_then_ceo_followup_reuses_existing_comparison(self):
        prior = self.old_packet()
        unchanged = deepcopy(prior)
        envelope = self.seal_old()
        self.assertEqual(prior, unchanged)
        self.assertEqual(envelope["storage"], "NONE")
        self.assertEqual(envelope["authenticity"],
                         "NOT_ESTABLISHED_UNKEYED_CHECKSUM")
        self.assertEqual(verify_private_portfolio_snapshot(envelope),
                         prior["observation_inputs"])
        current = self.current_packet()
        current["prior_private_portfolio_envelope"] = envelope
        saved = deepcopy(current)
        code, report, err = self.cli(current, "report")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("Largest absolute security-line weight shift: 25.00", report)
        self.assertIn("scoped cash weight change: -25.00", report)
        self.assertNotIn("SCOPE-A", report)
        self.assertNotIn("ABC:TSX", report)
        self.assertEqual(current, saved)
        code, body, err = self.cli(current, "status")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(json.loads(body)["readiness"], "NOT_EVALUATED")
        self.assertNotIn("SCOPE-A", body)
        self.assertNotIn("prior_private_portfolio_envelope", body)

    def test_ir_pi_manual_route_preserves_original_ir_and_private_snapshot(self):
        prior = self.seal_old(research=True)
        current = self.current_packet(research=True)
        current["prior_private_portfolio_envelope"] = prior
        code, body, err = self.cli(current, "operator-packet")
        self.assertEqual((code, err), (0, ""))
        operator = json.loads(body)
        self.assertIsNone(operator["continuation_private"])
        self.assertIn("largest absolute security-line weight shift",
                      operator["report_private"])
        self.assertEqual(operator["session"]["route"], "CC_IR_PI_CC")
        self.assertEqual(operator["storage"], "NONE")
        self.assertEqual(operator["project_invocation"], "NONE")

    def test_work_copy_contains_only_sanitized_m3_observation_not_browser_extras(self):
        work = BlossomSessionBridgeTests().report()
        packet = {
            "request": self.fx.request(
                research_needed=False, portfolio_needed=True),
            "pi_delta": self.fx.pi(),
            "work_portfolio_result": {"work_blossom_inputs": work},
        }
        original = deepcopy(packet)
        code, body, err = self.cli(packet, "private-portfolio-snapshot")
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(packet, original)
        self.assertNotIn("raw_html", body)
        self.assertNotIn("TOKEN_THAT_MUST_NOT_PASS", body)
        raw = verify_private_portfolio_snapshot(json.loads(body))
        self.assertEqual(raw["source_type"], "AUTHORIZED_BLOSSOM_TRANSCRIPTION")
        self.assertEqual(raw["positions"][0]["security_id"],
                         "SYNTHETIC-HOLDING:TSX")
        self.assertEqual(raw["analysis_id"], "CASE-A")
        self.assertNotIn("browser_hostname", raw)
        self.assertNotIn("work_reported_signed_in", raw)

    def test_changed_saved_record_rejected_without_private_echo(self):
        envelope = self.seal_old()
        envelope["private_snapshot"]["original_observation_inputs"][
            "positions"][0]["market_value_base"] = "SECRET_REPLACED_VALUE"
        packet = self.current_packet()
        packet["prior_private_portfolio_envelope"] = envelope
        code, body, err = self.cli(packet, "report")
        self.assertEqual((code, body), (2, ""))
        self.assertIn("PRIVATE_PORTFOLIO_SHA256_MISMATCH", err)
        self.assertNotIn("SECRET_REPLACED_VALUE", err)

    def test_incorrect_prior_identity_kind_and_duplicate_baseline_fail_closed(self):
        prior = self.seal_old()
        for patch, expected in (
            ({"kind": "DECISION"}, "PRIVATE_PORTFOLIO_FOLLOWUP_REQUIRED"),
            ({"ceo_initiated": False}, "PRIVATE_PORTFOLIO_FOLLOWUP_REQUIRED"),
            ({"portfolio_needed": False}, "PRIVATE_PORTFOLIO_FOLLOWUP_REQUIRED"),
            ({"prior_analysis_id": "NOT-OLD"},
             "PRIVATE_PORTFOLIO_BASELINE_ID_MISMATCH"),
        ):
            with self.subTest(patch=patch):
                packet = self.current_packet()
                packet["request"].update(patch)
                packet["prior_private_portfolio_envelope"] = prior
                code, body, err = self.cli(packet, "report")
                self.assertEqual((code, body), (2, ""))
                self.assertIn(expected, err)
        packet = self.current_packet()
        packet["prior_private_portfolio_envelope"] = prior
        packet["prior_portfolio_observation_inputs"] = self.observation(prior=True)
        code, body, err = self.cli(packet, "report")
        self.assertEqual((code, body), (2, ""))
        self.assertIn("PRIVATE_PORTFOLIO_SOURCE_AMBIGUOUS", err)

    def test_incomplete_prior_is_not_upgraded_on_recovery(self):
        old = self.seal_old(
            cash_base=None, cash_visibility="NOT_VISIBLE", scope_complete=False)
        packet = self.current_packet()
        packet["prior_private_portfolio_envelope"] = old
        code, report, err = self.cli(packet, "report")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("incomplete", report.lower())
        self.assertNotIn("Largest absolute security-line weight shift: 25.00", report)
        self.assertNotIn("scoped cash weight change: -25.00", report)

    def test_public_or_unknown_source_never_sealed_as_private_snapshot(self):
        obs = self.observation()
        for patch in ({"source_type": "PUBLIC_BLOSSOM_REFERENCE",
                       "private_scope": False},
                      {"source_type": "NOT_VERIFIED"},
                      {"extra_private_browser_token": "SYNTHETIC_SECRET"}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                seal_private_portfolio_snapshot({**obs, **patch})

    def test_pending_pi_or_missing_observation_cannot_export_private_snapshot(self):
        for p in (
            {"request": self.fx.request(
                research_needed=False, portfolio_needed=True),
             "observation_inputs": self.observation()},
            {"request": self.fx.request(
                research_needed=False, portfolio_needed=True),
             "pi_delta": self.fx.pi()},
        ):
            with self.subTest(keys=tuple(p)):
                code, body, err = self.cli(p, "private-portfolio-snapshot")
                self.assertEqual((code, body), (3, ""))
                self.assertIn("private portfolio snapshot unavailable", err)


if __name__ == "__main__":
    unittest.main()
