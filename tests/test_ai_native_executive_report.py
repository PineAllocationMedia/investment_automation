"""Synthetic-only regression tests for decision-first R1 reports."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class ExecutiveReportTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def cli(self, packet, output="executive-report"):
        stdin, stdout, stderr = StringIO(json.dumps(packet)), StringIO(), StringIO()
        code = main(["--output", output], instream=stdin, outstream=stdout,
                    errstream=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_ir_and_pi_report_preserves_full_evidence_and_unknown_room(self):
        request = self.fx.request(portfolio_needed=True)
        ir = self.fx.ir()
        ir["facts"][0]["claim"] = "SYNTHETIC_PROOF_SENTINEL"
        pi = self.fx.pi(forwarded_ir=deepcopy(ir))
        original = deepcopy((request, ir, pi))
        session = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        brief = session["executive_report_private"]
        self.assertIn("PAM R1 — Synthèse décisionnelle", brief)
        self.assertIn("INDISPONIBLE", brief)
        self.assertIn("ARCHIVE_NOT_SAVED", brief)
        self.assertIn("SYNTHETIC_PROOF_SENTINEL", brief)
        self.assertIn(session["final_report_private"].rstrip("\n"), brief)
        self.assertNotIn("une allocation recommandée", brief)
        self.assertEqual((request, ir, pi), original)
        code, out, err = self.cli({"request": request, "ir_capsule": ir,
                                   "pi_delta": pi})
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(out, brief)
        self.assertNotIn("SYNTHETIC_PROOF_SENTINEL",
                         self.cli({"request": request, "ir_capsule": ir,
                                   "pi_delta": pi}, "status")[1])

    def test_ir_only_has_no_portfolio_room_claim(self):
        session = complete_manual_session(self.fx.request(), ir_capsule=self.fx.ir())
        self.assertIn("NON ÉVALUÉ", session["executive_report_private"])
        self.assertIn("ARCHIVE_NOT_SAVED", session["executive_report_private"])
        self.assertEqual(session["integrated_private"]["markdown"],
                         session["final_report_private"])

    def test_pi_only_is_not_issuer_research(self):
        request = self.fx.request(research_needed=False, portfolio_needed=True)
        session = complete_manual_session(request, pi_delta=self.fx.pi())
        self.assertIn("INDISPONIBLE", session["executive_report_private"])
        self.assertIn("Portfolio-only interpretation", session["executive_report_private"])
        self.assertIn("NON ÉVALUÉ — aucun fait IR", session["executive_report_private"])
        code, body, err = self.cli({"request": request, "pi_delta": self.fx.pi()})
        self.assertEqual((code, err), (0, ""))
        self.assertIn(session["final_report_private"].rstrip("\n"), body)

    def test_pending_does_not_create_a_decision(self):
        pending = self.fx.request(portfolio_needed=True)
        session = complete_manual_session(pending)
        self.assertIsNone(session["executive_report_private"])
        code, body, err = self.cli({"request": pending})
        self.assertEqual((code, err), (0, ""))
        self.assertIn("REPORT_NOT_AVAILABLE", body)
        self.assertNotIn("Synthèse décisionnelle", body)

    def test_invalid_status_and_detail_rejected(self):
        from ai_native.executive_report import render_executive_report
        with self.assertRaisesRegex(ValueError, "EXECUTIVE_REPORT_DETAIL_REQUIRED"):
            render_executive_report({"status":"CONDITIONAL"}, detailed_report="",
                                    portfolio_room_status="ROOM_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
