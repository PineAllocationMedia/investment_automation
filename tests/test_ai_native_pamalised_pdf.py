"""PAMalised optional PDF output: synthetic-only in-memory verification."""
from __future__ import annotations

from copy import deepcopy
from io import BytesIO, StringIO
import importlib.util
import json
import unittest

from ai_native.pamalised_pdf import render_pamalised_pdf
from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests

_HAS_PDF = (importlib.util.find_spec("reportlab") is not None
            and importlib.util.find_spec("pypdf") is not None)


@unittest.skipUnless(_HAS_PDF, "optional PDF dependency not installed")
class PamalisedPdfTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = SessionBridgeTests()

    def _cli(self, payload):
        out = BytesIO()
        class Sink:
            buffer = out
            def write(self, string):
                out.write(string.encode("utf-8"))
        err = StringIO()
        code = main(["--output", "pamalised-pdf"],
                    instream=StringIO(json.dumps(payload)),
                    outstream=Sink(), errstream=err)
        return code, out.getvalue(), err.getvalue()

    def test_completed_ir_pi_pdf_is_searchable_and_read_only(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        ir = self.fixtures.ir()
        ir["facts"][0]["claim"] = "PAM_PDF_SENTINEL"
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        before = deepcopy((request, ir, pi))
        code, pdf, err = self._cli({"request": request,
                                    "ir_capsule": ir, "pi_delta": pi})
        self.assertEqual((code, err), (0, ""))
        self.assertTrue(pdf.startswith(b"%PDF-"))
        reader = PdfReader(BytesIO(pdf))
        self.assertGreaterEqual(len(reader.pages), 1)
        content = "\n".join(page.extract_text() for page in reader.pages)
        self.assertIn("PAM_PDF_SENTINEL", content)
        self.assertIn("ARCHIVE_NOT_SAVED", content)
        self.assertIn("EXPECTED RETURN", content)
        self.assertEqual((request, ir, pi), before)

    def test_pending_does_not_fabricate_file(self):
        code, body, err = self._cli({"request": self.fixtures.request(portfolio_needed=True)})
        self.assertEqual((code, err), (0, ""))
        self.assertIn(b"REPORT_NOT_AVAILABLE", body)
        self.assertNotIn(b"%PDF-", body)

    def test_untrusted_detail_and_mismatch_fail_closed(self):
        detail = "# Synthetic\n<script>unsafe</script>\n"
        intro = ("# PAM R1 — Synthèse décisionnelle\n"
                 "## La conclusion\nAucun achat.\n"
                 "## Dossier détaillé et traçabilité (annexe)\n"
                 "Rapport original ci-dessous.\n\n")
        kw = dict(executive_report=intro + detail, detailed_report=detail,
                  analysis_id="SYNTH", as_of="2026-10-30",
                  strategy="high-cagr", report_status="EXPLORATORY")
        pdf = render_pamalised_pdf(**kw)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        with self.assertRaisesRegex(ValueError, "PAMALISED_VALIDATED_REPORT_PAIR_REQUIRED"):
            render_pamalised_pdf(**{**kw, "detailed_report": detail + "tampered"})


if __name__ == "__main__":
    unittest.main()
