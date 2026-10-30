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

    def test_reference_six_sections_match_actual_ir_pi_payload(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        request["objective"] = "REAL_INPUT_SYNTHETIC_SENTINEL"
        ir = self.fixtures.ir()
        ir["countercase"] = "COUNTERCASE_SYNTHETIC_SENTINEL"
        ir["summary"] = ["THESIS_SYNTHETIC_SENTINEL"]
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        code, data, err = self._cli({"request": request, "ir_capsule": ir,
                                     "pi_delta": pi})
        self.assertEqual((code, err), (0, ""))
        pages = PdfReader(BytesIO(data)).pages
        text = "\n".join(page.extract_text() for page in pages)
        # Six relevant investor-facing sections plus the original evidence annex.
        for section in ("L’essentiel en 60 secondes", "Les opportunités retenues",
                        "Ce que cela change dans le portefeuille",
                        "Risques et points de bascule", "Durabilité et radar",
                        "Suivi, performance et traçabilité"):
            self.assertIn(section, text)
        for marker in ("REAL_INPUT_SYNTHETIC_SENTINEL",
                       "THESIS_SYNTHETIC_SENTINEL",
                       "COUNTERCASE_SYNTHETIC_SENTINEL"):
            self.assertIn(marker, text)
        self.assertNotIn("GABARIT MAÎTRE / VERSION VISUELLE", text)
        self.assertNotIn("BIBLIOTHÈQUE DE MODULES VISUELS", text)
        self.assertNotIn("RÈGLES DE PRODUCTION DES VISUELS", text)
        self.assertIn("ND - dénominateur non confirmé", text)
        self.assertIn("ARCHIVE_NOT_SAVED", text)

    def test_pi_only_omits_issuer_sections_without_data(self):
        from pypdf import PdfReader
        request = self.fixtures.request(research_needed=False,
                                         portfolio_needed=True)
        code, data, err = self._cli({"request": request,
                                     "pi_delta": self.fixtures.pi()})
        self.assertEqual((code, err), (0, ""))
        text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)
        self.assertIn("Ce que cela change dans le portefeuille", text)
        self.assertNotIn("Les opportunités retenues", text)
        self.assertNotIn("Durabilité et radar des marchés", text)
        self.assertIn("NON ÉTABLIE", text)

    def test_identity_disagreement_fails_closed(self):
        detail = "# Private detail\nOriginal fact\n"
        intro = ("# PAM R1 — Synthèse décisionnelle\n"
                 "## La conclusion\nNo supported allocation.\n\n"
                 "## Dossier détaillé et traçabilité (annexe)\n"
                 "Original retained\n\n")
        with self.assertRaisesRegex(ValueError, "PAMALISED_PDF_REQUEST_IDENTITY_MISMATCH"):
            render_pamalised_pdf(
                executive_report=intro + detail, detailed_report=detail,
                analysis_id="EXPECTED", as_of="2026-10-30",
                strategy="high-cagr", report_status="EXPLORATORY",
                request={"analysis_id": "WRONG", "as_of": "2026-10-30",
                         "strategy_id": "high-cagr"})

    def test_bounded_m3_string_percent_projection_is_not_a_buy_order(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        ir = self.fixtures.ir()
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        session = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        base = dict(executive_report=session["executive_report_private"],
                    detailed_report=session["final_report_private"],
                    analysis_id=request["analysis_id"], as_of=request["as_of"],
                    strategy=request["strategy_id"], report_status="EXPLORATORY",
                    request=request, ir_capsule=ir, pi_delta=pi)
        scenario = {"analysis_id": request["analysis_id"],
                    "gross_status": "GROSS_PROJECTION_ONLY",
                    "allocations_pct": {"TEST_ISSUER": "70", "TEST_ETF": "30"}}
        pdf = render_pamalised_pdf(
            **base, new_contribution_summary_private=scenario)
        text = "\n".join(x.extract_text() for x in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("TEST_ISSUER : 70.0 %", text)
        self.assertIn("projection arithmétique, non recommandation", text)
        rejected = render_pamalised_pdf(
            **base, new_contribution_summary_private={
                **scenario, "gross_status": "UNAVAILABLE"})
        again = "\n".join(x.extract_text() for x in PdfReader(BytesIO(rejected)).pages)
        self.assertNotIn("TEST_ISSUER : 70.0 %", again)

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
