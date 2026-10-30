"""One bounded, synthetic integrated preflight for the R1 test-5 prerequisites.

This is a developer/operator regression, NOT a fifth CEO operational trial,
broker/source authentication, CC Project settings inspection, or 36-choice
acceptance. Do not store a real account/case in this fixture.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import stat
import tempfile
import unittest

from ai_native.session_bridge import complete_manual_session
from ai_native.known_costs import tally_supplied_costs
from scripts.pamalised_private_file_export import export_private_pdf
from tests import test_ai_native_session_bridge as _bridge_fixtures
from tests import test_ai_native_public_portfolio_reference as _public_fixtures
from tests import test_ai_native_known_costs as _cost_fixtures

_HAS_PDF = (importlib.util.find_spec("reportlab") is not None
            and importlib.util.find_spec("pypdf") is not None)


class R1IntegratedPreflight(unittest.TestCase):
    """Check cross-component behavior; never infer authentic readiness."""

    def setUp(self):
        self.fx = _bridge_fixtures.SessionBridgeTests()

    def _case(self, *, high_cagr=False):
        req = self.fx.request(
            portfolio_needed=True,
            strategy_id="high-cagr" if high_cagr else "EXPLORATORY",
        )
        ir = self.fx.ir()
        ir["facts"][0]["claim"] = "SYNTHETIC_R1_PREFLIGHT_SOURCE_MARKER"
        pi = self.fx.pi(forwarded_ir=deepcopy(ir))
        return {"request": req, "ir_capsule": ir, "pi_delta": pi}

    def test_one_human_handoff_at_a_time_and_original_ir_preserved(self):
        case = self._case()
        original = deepcopy(case)
        start = complete_manual_session(case["request"])
        self.assertEqual(start["status"], "AWAITING_MANUAL_IR_CAPSULE")
        self.assertIn("IR_REQUEST", start["handoffs_private"]["copy_ready_private"])
        self.assertNotIn("PI_REQUEST", start["handoffs_private"]["copy_ready_private"])

        after_ir = complete_manual_session(
            case["request"], ir_capsule=case["ir_capsule"])
        self.assertEqual(after_ir["status"], "AWAITING_MANUAL_PI_DELTA")
        self.assertEqual(
            after_ir["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],
            case["ir_capsule"],
        )
        complete = complete_manual_session(**case)
        self.assertEqual(
            complete["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertIn("SYNTHETIC_R1_PREFLIGHT_SOURCE_MARKER",
                      complete["final_report_private"])
        self.assertIn("SYNTHETIC_R1_PREFLIGHT_SOURCE_MARKER",
                      complete["executive_report_private"])
        self.assertEqual(complete["method_load_verification"], "NOT_PERFORMED")
        self.assertEqual(complete["project_invocation"], "NONE")
        self.assertEqual(case, original)

    @unittest.skipUnless(_HAS_PDF, "optional ReportLab+pypdf PDF stack unavailable")
    def test_final_pamalised_pdf_is_one_private_readable_artifact(self):
        from pypdf import PdfReader

        case = self._case()
        before = deepcopy(case)
        request = case["request"]
        # This is intentionally authored by the synthetic test, NOT generated
        # by the deterministic PDF renderer as imaginary AI analysis.
        presentation = {
            "analysis_id": request["analysis_id"],
            "as_of": request["as_of"],
            "opening_paragraph": (
                "Cette étude synthétique explore le mandat transmis à CC. "
                "Elle conserve les faits IR originaux et distingue les "
                "observations PI des comptes réellement authentifiés."
            ),
            "support_refs": ["F1"],
            "visuals": [{
                "kind": "evidence_flow",
                "title": "Schéma des faits transmis pour comparaison",
                "fact_ids": ["F1"],
            }],
        }
        payload = {**case, "presentation_inputs": presentation}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "synthetic_r1_pamalised.pdf"
            status = export_private_pdf(
                case_json=json.dumps(payload, ensure_ascii=False),
                destination=target, authorized=True,
            )
            self.assertEqual(status, "PDF_CREATED_LOCALLY_NOT_DELIVERED_TO_CC_WORK")
            data = target.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertTrue(data.rstrip().endswith(b"%%EOF"))
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            self.assertEqual(len(list(Path(folder).iterdir())), 1)
            pdf = PdfReader(BytesIO(data))
            self.assertGreaterEqual(len(pdf.pages), 4)
            rendered = "\n".join(page.extract_text() for page in pdf.pages)
            for expected in (
                "Cette étude synthétique explore le mandat",
                "L’essentiel en 60 secondes",
                "Les opportunités retenues",
                "Ce que cela change dans le portefeuille",
                "Risques et points de bascule",
                "Durabilité et radar",
                "Suivi, performance et traçabilité",
                "SYNTHETIC_R1_PREFLIGHT_SOURCE_MARKER",
                "ARCHIVE_NOT_SAVED",
            ):
                self.assertIn(expected, rendered)
            self.assertNotIn("BIBLIOTHÈQUE DE MODULES VISUELS", rendered)
            self.assertNotIn("RÈGLES DE PRODUCTION DES VISUELS", rendered)
        self.assertEqual(case, before)

    @unittest.skipUnless(_HAS_PDF, "optional ReportLab PDF stack unavailable")
    def test_pending_or_modified_ir_creates_no_artifact(self):
        case = self._case()
        altered = deepcopy(case)
        altered["pi_delta"]["forwarded_ir"]["facts"][0]["claim"] = "ALTERED"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "unsafe.pdf"
            for obj in (
                {"request": case["request"]},
                {"request": case["request"], "ir_capsule": case["ir_capsule"]},
                altered,
            ):
                with self.subTest(stage=len(obj)), self.assertRaisesRegex(
                        ValueError, "PDF_EXPORT_SOURCE_NOT_READY"):
                    export_private_pdf(
                        case_json=json.dumps(obj), destination=path,
                        authorized=True,
                    )
                self.assertFalse(path.exists())

    def test_public_blossom_profile_cannot_provide_private_room(self):
        fx = _public_fixtures.PublicReferenceTests()
        public = fx.data()
        request = fx.req()
        before = deepcopy(public)
        outcome = complete_manual_session(
            request, public_reference_inputs=public)
        self.assertEqual(outcome["status"],
                         "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY")
        self.assertIsNone(outcome["portfolio_observation_private"])
        self.assertIsNone(outcome["gross_contribution_private"])
        self.assertEqual(outcome["public_reference_private"]["private_holdings_import"],
                         "NONE")
        self.assertEqual(outcome["public_reference_private"]["allocation_authority"],
                         "NONE")
        self.assertEqual(public, before)
        with self.assertRaisesRegex(ValueError,
                                    "PUBLIC_REFERENCE_CANNOT_BECOME_PRIVATE_PORTFOLIO"):
            complete_manual_session(request, public_reference_inputs=public,
                                    observation_inputs={})

    def test_unsourced_zero_cost_stays_unknown_not_free(self):
        fx = _cost_fixtures.CostTallyTests()
        args = fx.args()
        args["charges_by_destination"]["VFV:TSX"]["purchase_tax"]["source_ref"] = "UNKNOWN"
        actual = tally_supplied_costs(**args)
        self.assertEqual(actual["status"], "INCOMPLETE_COST_INPUTS")
        self.assertIn("VFV:TSX:purchase_tax:SOURCE_NOT_SUPPLIED",
                      actual["missing_components"])
        self.assertNotIn("total_supplied_costs_base", actual)

    def test_high_cagr_er_gap_is_separate_from_room(self):
        case = self._case(high_cagr=True)
        case["pi_delta"]["room_status"] = "ROOM_EVIDENCE_SUPPORTED"
        result = complete_manual_session(**case)
        review = result["high_cagr_destination_review_private"]
        self.assertEqual(
            review["independent_dependencies"]["economic"],
            "ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_NOT_ESTABLISHED")
        self.assertEqual(review["allocation_percentage"], None)
        self.assertEqual(review["trade_authority"], "NONE")
        self.assertEqual(review["decision_stage"],
                         "EVIDENCE_GAP_NOT_AN_ALLOCATION_DECISION")
        self.assertIn("Deux blocages independants", result["final_report_private"])
        self.assertIn("PAS reparer l'ER manquant", result["final_report_private"])


if __name__ == "__main__":
    unittest.main()
