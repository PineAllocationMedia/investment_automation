"""Synthetic-only checks for read-only PAMalised HTML (not real PDF acceptance)."""
from __future__ import annotations

from copy import deepcopy
from html import escape
from io import StringIO
import json
import unittest

from ai_native.pamalised_report import render_pamalised_html
from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests


class PamalisedHtmlTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def cli(self, payload):
        out, err = StringIO(), StringIO()
        result = main(["--output", "pamalised-html"],
                      instream=StringIO(json.dumps(payload)),
                      outstream=out, errstream=err)
        return result, out.getvalue(), err.getvalue()

    def test_ir_pi_outputs_branded_document_with_full_original_annex(self):
        request = self.fx.request(portfolio_needed=True)
        ir = self.fx.ir()
        ir["facts"][0]["claim"] = "SYNTHETIC_PROOF_SENTINEL"
        pi = self.fx.pi(forwarded_ir=deepcopy(ir))
        inputs = {"request": request, "ir_capsule": ir, "pi_delta": pi}
        session = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        code, body, err = self.cli(inputs)
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(body.startswith("<!doctype html>"))
        self.assertIn("#0B2E24", body)
        self.assertIn("Rapport d’analyse", body)
        self.assertIn("HTML_PRINT_READY_PDF_NOT_GENERATED", body)
        self.assertIn("SYNTHETIC_PROOF_SENTINEL", body)
        self.assertIn(escape(session["final_report_private"].rstrip("\n")), body)
        self.assertNotIn("<script", body)
        self.assertNotIn("<canvas", body)
        self.assertNotIn("src=\"http", body)
        self.assertEqual(inputs["ir_capsule"], ir)

    def test_pi_only_and_ir_only_preserve_true_limitations(self):
        for request, kwargs in (
            (self.fx.request(research_needed=False, portfolio_needed=True),
             {"pi_delta": self.fx.pi()}),
            (self.fx.request(), {"ir_capsule": self.fx.ir()}),
        ):
            with self.subTest(request=request["research_needed"]):
                code, body, err = self.cli({"request": request, **kwargs})
                self.assertEqual((code, err), (0, ""))
                self.assertIn("REPORT_EXPORT_STATUS", body)
                self.assertIn("NON ÉVALUÉ", body) if not request["research_needed"] else None

    def test_pending_session_never_renders_html(self):
        code, body, err = self.cli({"request": self.fx.request(portfolio_needed=True)})
        self.assertEqual((code, err), (0, ""))
        self.assertIn("REPORT_NOT_AVAILABLE", body)
        self.assertNotIn("<!doctype html>", body)

    def test_mismatched_or_malicious_report_cannot_be_rendered_as_html(self):
        detail = "# Synthetic private research\n<script>alert('x')</script>\n"
        prefix = ("# PAM R1 — Synthèse décisionnelle\n"
                  "## La conclusion\nNo supported allocation.\n\n"
                  "## Dossier détaillé et traçabilité (annexe)\n"
                  "Original retained\n\n")
        args = dict(executive_report=prefix + detail,
                    detailed_report=detail, analysis_id="SYNTH",
                    as_of="2026-10-30", strategy="high-cagr",
                    report_status="EXPLORATORY")
        body = render_pamalised_html(**args)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)
        with self.assertRaisesRegex(ValueError, "PAMALISED_VALIDATED_REPORT_PAIR_REQUIRED"):
            render_pamalised_html(**{**args, "detailed_report": detail + "tampered"})
        with self.assertRaisesRegex(ValueError, "PAMALISED_STATUS_INVALID"):
            render_pamalised_html(**{**args, "report_status": "SYSTEM_ACCEPTED"})


if __name__ == "__main__":
    unittest.main()
