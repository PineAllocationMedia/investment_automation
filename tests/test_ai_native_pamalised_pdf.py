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
from tests import test_ai_native_work_blossom_session_bridge as _work_fixtures

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

    def _completed_m3_case(self, *, ir_requested):
        """Use real synthetic M3/Work data, not a hand-crafted PDF summary."""
        fx = _work_fixtures.BlossomSessionBridgeTests()
        request = self.fixtures.request(
            portfolio_needed=True, research_needed=ir_requested)
        case = {
            "request": request,
            "pi_delta": self.fixtures.pi(),
            "work_blossom_inputs": fx.report(),
            "contribution_inputs": {
                "contribution_base": "123.45",
                "allocations_pct": {"SYNTHETIC-HOLDING:TSX": "100.00"},
                "currency": "CAD", "as_of": "2026-10-28",
                "scope_complete": True, "cash_accounted_for": True,
                "same_currency_basis_verified": True,
                "instrument_identity_verified": True,
            },
            "presentation_inputs": {
                "analysis_id": request["analysis_id"],
                "as_of": request["as_of"],
                "opening_paragraph": (
                    "Cette analyse synthétique examine une contribution "
                    "hypothétique sur un portefeuille daté et incomplet sur "
                    "le plan de son authentification externe."
                ),
                "support_refs": [],
                "visuals": [{
                    "kind": "contribution_bars",
                    "title": "Visualisation de la contribution M3 contrôlée",
                    "fact_ids": [],
                }],
            },
        }
        if ir_requested:
            case["ir_capsule"] = self.fixtures.ir()
            case["pi_delta"]["forwarded_ir"] = deepcopy(case["ir_capsule"])
        return case

    def test_pi_only_m3_reaches_actual_pdf_without_invented_amounts(self):
        from pypdf import PdfReader
        case = self._completed_m3_case(ir_requested=False)
        original = deepcopy(case)
        session = complete_manual_session(
            case["request"], pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"],
            contribution_inputs=case["contribution_inputs"])
        summary = session["new_contribution_summary_private"]
        self.assertEqual(summary["gross_status"], "GROSS_PROJECTION_ONLY")
        self.assertEqual(
            summary["allocations_pct"],
            {"SYNTHETIC-HOLDING:TSX": "100.00"})
        self.assertIsNone(session["integrated_private"])
        code, data, error = self._cli(case)
        self.assertEqual((code, error), (0, ""))
        rendered = "\n".join(p.extract_text() for p in PdfReader(BytesIO(data)).pages)
        self.assertIn("Visualisation de la contribution M3 contrôlée", rendered)
        self.assertIn("SYNTHETIC-HOLDING:TSX", rendered)
        self.assertIn("100.0 %", rendered)
        self.assertIn("projection arithmétique, non recommandation", rendered)
        for forbidden in ("123.45", "SYNTHETIC_ACCOUNT_SECRET",
                          "TOKEN_THAT_MUST_NOT_PASS"):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(case, original)

    def test_ir_pi_m3_summary_reaches_pdf_through_integrated_case(self):
        from pypdf import PdfReader
        case = self._completed_m3_case(ir_requested=True)
        result = complete_manual_session(
            case["request"], ir_capsule=case["ir_capsule"],
            pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"],
            contribution_inputs=case["contribution_inputs"])
        self.assertEqual(result["new_contribution_summary_private"],
                         result["integrated_private"][
                             "new_contribution_summary_private"])
        self.assertEqual(
            result["new_contribution_summary_private"]["gross_status"],
            "GROSS_PROJECTION_ONLY")
        code, pdf, err = self._cli(case)
        self.assertEqual((code, err), (0, ""))
        rendered = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Visualisation de la contribution M3 contrôlée", rendered)
        self.assertIn("SYNTHETIC-HOLDING:TSX", rendered)
        self.assertIn("100.0 %", rendered)
        self.assertIn("Les opportunités retenues", rendered)
        self.assertNotIn("123.45", rendered)

    def _synthetic_m3_with_costs(self, *, complete_costs):
        case = self._completed_m3_case(ir_requested=False)
        categories = (
            "commission", "bid_ask_spread", "fx_conversion",
            "purchase_tax", "other_fees"
        )
        charges = {
            component: {"amount_base": "0.00",
                        "source_ref": "SYN-SOURCE-" + component}
            for component in categories
        }
        charges["commission"] = {
            "amount_base": "5.00",
            "source_ref": "SYN-PRIVATE-FEE-RECORD",
        }
        if not complete_costs:
            charges["purchase_tax"]["source_ref"] = "UNKNOWN"
        case["cost_inputs"] = {
            "charges_by_destination": {"SYNTHETIC-HOLDING:TSX": charges},
            "cost_currency": "CAD",
            "cost_quote_as_of": "2026-10-28",
            "analysis_as_of": "2026-10-28",
            "funding": "FROM_CONTRIBUTION",
        }
        return case

    def test_funded_m3_shows_conditional_cost_burden_not_net_return(self):
        from pypdf import PdfReader
        case = self._synthetic_m3_with_costs(complete_costs=True)
        result = complete_manual_session(
            case["request"], pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"],
            contribution_inputs=case["contribution_inputs"],
            cost_inputs=case["cost_inputs"])
        summary = result["new_contribution_summary_private"]
        self.assertEqual(summary["cost_status"], "SUPPLIED_COST_TALLY_ONLY")
        self.assertEqual(summary["funded_status"],
                         "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")
        self.assertIsNotNone(summary["one_time_supplied_cost_share_pct"])
        code, pdf, error = self._cli(case)
        self.assertEqual((code, error), (0, ""))
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Frais fixes déclarés", text)
        self.assertIn("Budget conditionnel", text)
        self.assertIn("du nouveau capital", text)
        self.assertIn("non annualisée", text)
        self.assertIn("NON CERTIFIÉS", text)
        self.assertNotIn("SYN-PRIVATE-FEE-RECORD", text)

    def test_incomplete_cost_quote_is_not_displayed_as_zero_or_funded(self):
        from pypdf import PdfReader
        case = self._synthetic_m3_with_costs(complete_costs=False)
        result = complete_manual_session(
            case["request"], pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"],
            contribution_inputs=case["contribution_inputs"],
            cost_inputs=case["cost_inputs"])
        summary = result["new_contribution_summary_private"]
        self.assertEqual(summary["cost_status"], "INCOMPLETE_COST_INPUTS")
        self.assertNotEqual(summary["funded_status"],
                            "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")
        code, pdf, error = self._cli(case)
        self.assertEqual((code, error), (0, ""))
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Frais incomplets", text)
        self.assertIn("Net indisponible", text)
        self.assertNotIn("SYN-PRIVATE-FEE-RECORD", text)

    def test_new_capital_pdf_refuses_forged_percentage_and_cost_status(self):
        case = self._completed_m3_case(ir_requested=False)
        result = complete_manual_session(
            case["request"], pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"],
            contribution_inputs=case["contribution_inputs"])
        original = result["new_contribution_summary_private"]
        args = {
            "executive_report": result["executive_report_private"],
            "detailed_report": result["final_report_private"],
            "analysis_id": case["request"]["analysis_id"],
            "as_of": case["request"]["as_of"],
            "strategy": case["request"]["strategy_id"],
            "report_status": "CONDITIONAL",
            "request": case["request"], "pi_delta": case["pi_delta"],
        }
        fake_pct = deepcopy(original)
        fake_pct["allocations_pct"] = {"OTHER-SYNTHETIC:TSX": "100.00"}
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_NEW_CAPITAL_DETAIL_PARITY_INVALID"):
            render_pamalised_pdf(
                **args, new_contribution_summary_private=fake_pct)
        fake_costs = deepcopy(original)
        fake_costs["cost_status"] = "SUPPLIED_COST_TALLY_ONLY"
        fake_costs["funded_status"] = "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
        fake_costs["one_time_supplied_cost_share_pct"] = "0.0000"
        with self.assertRaises(ValueError):
            render_pamalised_pdf(
                **args, new_contribution_summary_private=fake_costs)
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_NEW_CAPITAL_PI_DATE_MISMATCH"):
            render_pamalised_pdf(
                **{**args, "pi_delta": {
                    **case["pi_delta"], "portfolio_as_of": "2026-10-27"}},
                new_contribution_summary_private=original)

    def test_requested_m3_chart_is_omitted_without_actual_m3_calculation(self):
        from pypdf import PdfReader
        case = self._completed_m3_case(ir_requested=False)
        del case["contribution_inputs"]
        result = complete_manual_session(
            case["request"], pi_delta=case["pi_delta"],
            work_blossom_inputs=case["work_blossom_inputs"])
        self.assertIsNone(result["new_contribution_summary_private"])
        code, pdf, err = self._cli(case)
        self.assertEqual((code, err), (0, ""))
        rendered = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertNotIn("Visualisation de la contribution M3 contrôlée",
                         rendered)
        self.assertNotIn("SYNTHETIC-HOLDING:TSX : 100.0 %", rendered)

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

    def test_cc_authored_intro_and_visuals_use_actual_ir_and_m3(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        ir = self.fixtures.ir()
        ir["facts"][0]["claim"] = "FACT_INPUT_ONLY_XYZ"
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        payload = {"request": request, "ir_capsule": ir, "pi_delta": pi,
                   "presentation_inputs": {
                       "analysis_id": request["analysis_id"],
                       "as_of": request["as_of"],
                       "opening_paragraph": (
                           "Le mandat demande une comparaison responsable des "
                           "options synthétiques. Les faits IR sont rapportés "
                           "sans authentification indépendante et la situation "
                           "personnelle reste non vérifiée."
                       ),
                       "support_refs": ["F1"],
                       "visuals": [{"kind": "evidence_flow",
                                    "title": "Schéma des preuves réellement reçues",
                                    "fact_ids": ["F1"]},
                                   {"kind": "contribution_bars",
                                    "title": "Répartition conditionnelle de l'apport",
                                    "fact_ids": []}],
                   }}
        code, pdf, err = self._cli(payload)
        self.assertEqual((code, err), (0, ""))
        txt = "\n".join(x.extract_text() for x in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Le mandat demande une comparaison", txt)
        self.assertIn("Schéma des preuves réellement reçues", txt)
        self.assertIn("FACT_INPUT_ONLY_XYZ", txt)
        self.assertNotIn("Répartition conditionnelle de l'apport", txt)
        # Exact visible first section follows the CC-authored paragraph.
        self.assertLess(txt.index("Le mandat demande une comparaison"),
                        txt.index("L’essentiel en 60 secondes"))
        self.assertIn("Mandat et traçabilité", txt)
        self.assertNotIn("ANALYSE AU", txt)

    def test_bar_chart_uses_only_validated_m3_percentage_projections(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        ir = self.fixtures.ir()
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        session = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        props = dict(executive_report=session["executive_report_private"],
                     detailed_report=session["final_report_private"],
                     analysis_id=request["analysis_id"], as_of=request["as_of"],
                     strategy=request["strategy_id"], report_status="EXPLORATORY",
                     request=request, ir_capsule=ir, pi_delta=pi)
        presentation = {
            "analysis_id": request["analysis_id"], "as_of": request["as_of"],
            "opening_paragraph": ("Une comparaison synthétique a été effectuée "
                                  "à la demande du CEO. Les résultats restent "
                                  "conditionnels aux preuves sources et aux coûts."),
            "support_refs": ["F1"],
            "visuals": [{"kind": "contribution_bars",
                         "title": "Répartition des nouveaux apports selon le modèle",
                         "fact_ids": []}],
        }
        amounts = {"analysis_id": request["analysis_id"],
                   "gross_status": "GROSS_PROJECTION_ONLY",
                   "allocations_pct": {"ETF_TEST": "65", "ISSUER_TEST": "35"}}
        pdf = render_pamalised_pdf(
            **props, presentation_inputs=presentation,
            new_contribution_summary_private=amounts)
        extracted = "\n".join(x.extract_text() for x in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Répartition des nouveaux apports selon le modèle", extracted)
        self.assertIn("ETF_TEST", extracted)
        self.assertIn("65.0 %", extracted)
        self.assertIn("projection arithmétique", extracted.lower())
        invalid = render_pamalised_pdf(
            **props, presentation_inputs=presentation,
            new_contribution_summary_private={
                **amounts, "gross_status": "UNAVAILABLE"})
        extracted_bad = "\n".join(x.extract_text() for x in PdfReader(BytesIO(invalid)).pages)
        self.assertNotIn("Répartition des nouveaux apports selon le modèle", extracted_bad)
        self.assertNotIn("65.0 %", extracted_bad)

    def test_high_cagr_final_diagnostic_is_visible_on_pdf_first_page(self):
        from pypdf import PdfReader
        request = self.fixtures.request(
            strategy_id="high-cagr", portfolio_needed=True)
        ir = self.fixtures.ir()
        ir["decision_line"] = "SYNTHETIC_IR_OPINION_NOT_FINAL"
        pi = self.fixtures.pi(
            room_status="ROOM_EVIDENCE_SUPPORTED",
            forwarded_ir=deepcopy(ir))
        payload = {"request": request, "ir_capsule": ir, "pi_delta": pi}
        original = deepcopy(payload)
        session = complete_manual_session(**payload)
        self.assertEqual(session["high_cagr_destination_review_private"][
            "decision_stage"], "EVIDENCE_GAP_NOT_AN_ALLOCATION_DECISION")
        code, pdf, err = self._cli(payload)
        self.assertEqual((code, err), (0, ""))
        pages = PdfReader(BytesIO(pdf)).pages
        first = pages[0].extract_text()
        full = "\n".join(page.extract_text() for page in pages)
        self.assertIn("EVIDENCE_GAP", first)
        self.assertIn("DEUX VÉRIFICATIONS INDÉPENDANTES", first)
        self.assertIn("Room personnel non authentifié", first)
        self.assertIn("rendement total prospectif", first)
        self.assertIn("Trois destinations examinées", full)
        self.assertIn("SYNTHETIC_IR_OPINION_NOT_FINAL", full)
        self.assertIn("ARCHIVE_NOT_SAVED", full)
        self.assertNotIn("SYNTHETIC_IR_OPINION_NOT_FINAL", first)
        self.assertEqual(payload, original)

    def test_direct_pdf_rejects_forged_high_cagr_decision_and_scope(self):
        request = self.fixtures.request(
            strategy_id="high-cagr", portfolio_needed=True)
        ir = self.fixtures.ir()
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        complete = complete_manual_session(
            request, ir_capsule=ir, pi_delta=pi)
        args = {
            "executive_report": complete["executive_report_private"],
            "detailed_report": complete["final_report_private"],
            "analysis_id": request["analysis_id"],
            "as_of": request["as_of"],
            "strategy": request["strategy_id"],
            "report_status": "EXPLORATORY",
            "request": request, "ir_capsule": ir, "pi_delta": pi,
        }
        genuine = complete["high_cagr_destination_review_private"]
        fake = deepcopy(genuine)
        fake["decision_stage"] = "SUPPORTED_ACTION"
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_HIGH_CAGR_REVIEW_PARITY_MISMATCH"):
            render_pamalised_pdf(
                **args, high_cagr_destination_review_private=fake)
        fake = deepcopy(genuine)
        fake["independent_dependencies"]["economic"] = "CERTIFIED"
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_HIGH_CAGR_REVIEW_PARITY_MISMATCH"):
            render_pamalised_pdf(
                **args, high_cagr_destination_review_private=fake)
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_HIGH_CAGR_REVIEW_SCOPE_INVALID"):
            render_pamalised_pdf(
                **{**args, "request": None},
                high_cagr_destination_review_private=genuine)

    def test_non_high_cagr_pdf_retains_existing_report_policy(self):
        from pypdf import PdfReader
        request = self.fixtures.request(portfolio_needed=True)
        ir = self.fixtures.ir()
        pi = self.fixtures.pi(forwarded_ir=deepcopy(ir))
        code, pdf, err = self._cli(
            {"request": request, "ir_capsule": ir, "pi_delta": pi})
        self.assertEqual((code, err), (0, ""))
        first = PdfReader(BytesIO(pdf)).pages[0].extract_text()
        self.assertNotIn("Trois destinations examinées", first)
        self.assertNotIn("DEUX VÉRIFICATIONS INDÉPENDANTES", first)

    def _synthetic_candidate_ir_case(self, *, have_source):
        """One actual CC→IR combined calculation, never a fake PDF value."""
        from tests import test_ai_native_candidate_comparison as candidate_tests
        fx = candidate_tests.CandidateComparisonTests()
        data, _ = fx.weighted_case()
        data["candidates"][1]["role"] = "REFERENCE_ETF"
        request = self.fixtures.request(
            analysis_id="SYN-C", strategy_id="EXPLORATORY",
            as_of="2026-10-28", portfolio_needed=False)
        ir = self.fixtures.ir(analysis_id="SYN-C")
        payload = {
            "request": request, "ir_capsule": ir,
            "candidate_comparison_inputs": data,
        }
        if have_source:
            observations = []
            for item in data["candidates"]:
                val = item["valuation_inputs"]
                observations.append({
                    "observation_id": val["quote_source_ref"],
                    "fact_id": "SYN-F-" + item["candidate_id"],
                    "source_id": "SYN-S-" + item["candidate_id"],
                    "economic_issuer": item["candidate_id"],
                    "instrument": val["security_id"],
                    "metric": "MARKET_PRICE_PER_SHARE",
                    "period_start": "2026-10-27", "period_end": "2026-10-27",
                    "currency": "CAD", "unit": "PER_SHARE",
                    "definition_basis": "EXCHANGE_LAST_REPORTED",
                    "consolidation": "SECURITY_CLASS", "value": "100",
                    "observed_at": "2026-10-28", "published_at": "2026-10-27",
                    "original_checked_at": "2026-10-28",
                    "source_kind": "SECONDARY", "classification": "SOURCE_FACT",
                    "source_locator": "https://example.org/synthetic-quote",
                    "rights_status": "PERMITTED",
                    "verification_status": "INDICATIVE",
                })
            ir["facts"] = [
                {"id": row["fact_id"], "status": "INDICATIVE",
                 "claim": "Synthetic quote only: " + row["instrument"]}
                for row in observations
            ]
            payload["source_evidence_inputs"] = {
                "analysis_id": "SYN-C", "analysis_as_of": "2026-10-28",
                "observations": observations,
            }
        return payload

    def test_actual_ir_comparison_reaches_pdf_as_conditional_not_alpha(self):
        from pypdf import PdfReader
        case = self._synthetic_candidate_ir_case(have_source=True)
        source = deepcopy(case)
        result = complete_manual_session(**case)
        comp = result["integrated_private"]["candidate_comparison_private"]
        self.assertEqual(comp["pairwise_weighted_cashflow_private"][0]["status"],
                         "CONDITIONAL_TOTAL_CASHFLOW_IRR_SPREAD_ONLY")
        code, pdf, err = self._cli(case)
        self.assertEqual((code, err), (0, ""))
        content = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("Sensibilité économique", content)
        self.assertIn("ÉCART DE RENDEMENT ANNUALISÉ", content)
        self.assertIn("pp", content)
        self.assertIn("probabilité", content)
        self.assertIn("Ni rendement espéré certifié", content)
        self.assertIn("ARCHIVE_NOT_SAVED", content)
        self.assertEqual(case, source)

    def test_unlinked_quotes_show_not_comparable_not_invented_spread(self):
        from pypdf import PdfReader
        case = self._synthetic_candidate_ir_case(have_source=False)
        result = complete_manual_session(**case)
        self.assertEqual(
            result["integrated_private"]["candidate_comparison_private"][
                "pairwise_weighted_cashflow_private"][0]["status"],
            "NOT_COMPARABLE")
        code, pdf, err = self._cli(case)
        self.assertEqual((code, err), (0, ""))
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("NON COMPARABLE", text)
        self.assertIn("Ni rendement espéré certifié", text)

    def test_pdf_rejects_different_pairwise_result_and_no_original_annex(self):
        case = self._synthetic_candidate_ir_case(have_source=True)
        result = complete_manual_session(**case)
        args = {
            "executive_report": result["executive_report_private"],
            "detailed_report": result["final_report_private"],
            "analysis_id": case["request"]["analysis_id"],
            "as_of": case["request"]["as_of"],
            "strategy": case["request"]["strategy_id"],
            "report_status": "CONDITIONAL",
            "request": case["request"], "ir_capsule": case["ir_capsule"],
        }
        actual = result["integrated_private"]["candidate_comparison_private"]
        fabricated = deepcopy(actual)
        fabricated["pairwise_weighted_cashflow_private"][0][
            "first_minus_second_pp"] = "999"
        with self.assertRaises(ValueError):
            render_pamalised_pdf(
                **args, candidate_comparison_private=fabricated)
        changed_detail = args["detailed_report"].replace(
            "## Cross-candidate scenario arithmetic — private, not ranked",
            "## Cross-candidate scenario arithmetic — REMOVED")
        self.assertNotEqual(changed_detail, args["detailed_report"])
        changed_executive = args["executive_report"].replace(
            args["detailed_report"], changed_detail)
        self.assertNotEqual(changed_executive, args["executive_report"])
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_CANDIDATE_SOURCE_DETAIL_PARITY_INVALID"):
            render_pamalised_pdf(
                **{**args, "executive_report": changed_executive,
                   "detailed_report": changed_detail},
                candidate_comparison_private=actual)

    def _private_portfolio_pdf_case(self, *, complete):
        from tests import test_ai_native_observation_bridge as observation_fixtures
        fx = observation_fixtures.ObservationBridgeTests()
        request = fx.req(as_of="2026-10-30", strategy_id="EXPLORATORY")
        observation = fx.observation(
            observed_on="2026-10-27",
            analysis_as_of="2026-10-30",
            captured_at="2026-10-29T10:00:00-04:00",
            scope_complete=complete,
            cash_base="100.00" if complete else None,
            cash_visibility="VERIFIED_VISIBLE" if complete else "NOT_VISIBLE")
        return {"request": request,
                "pi_delta": fx.pi(portfolio_as_of="2026-10-27"),
                "observation_inputs": observation}

    def test_private_scope_and_real_observation_dates_reach_pdf_without_balances(self):
        from pypdf import PdfReader
        case = self._private_portfolio_pdf_case(complete=True)
        source = deepcopy(case)
        completed = complete_manual_session(**case)
        self.assertEqual(completed["portfolio_observation_private"]["status"],
                         "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA")
        code, pdf, error = self._cli(case)
        self.assertEqual((code, error), (0, ""))
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("dénominateur du périmètre", text)
        self.assertIn("2026-10-27", text)
        self.assertIn("2026-10-29", text)
        self.assertIn("Encaisse déclarée visible", text)
        self.assertIn("NON authentifié", text)
        self.assertNotIn("SCOPE-A", text)
        self.assertNotIn("300.00", text)
        self.assertNotIn("400.00", text)
        self.assertEqual(case, source)

    def test_incomplete_private_scope_stays_incomplete_in_pdf(self):
        from pypdf import PdfReader
        case = self._private_portfolio_pdf_case(complete=False)
        completed = complete_manual_session(**case)
        observation = completed["portfolio_observation_private"]
        self.assertEqual(observation["status"], "OBSERVATION_LEDGER_ONLY")
        self.assertIsNone(observation["known_scope_weights_pct"])
        code, pdf, error = self._cli(case)
        self.assertEqual((code, error), (0, ""))
        text = "\n".join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
        self.assertIn("périmètre incomplet", text)
        self.assertIn("Encaisse non visible", text)
        self.assertNotIn("dénominateur du périmètre", text)

    def test_pdf_rejects_private_observation_with_invalid_or_missing_report_evidence(self):
        case = self._private_portfolio_pdf_case(complete=True)
        done = complete_manual_session(**case)
        record = done["portfolio_observation_private"]
        args = {
            "executive_report": done["executive_report_private"],
            "detailed_report": done["final_report_private"],
            "analysis_id": case["request"]["analysis_id"],
            "as_of": case["request"]["as_of"],
            "strategy": case["request"].get("strategy_id", "EXPLORATORY"),
            "report_status": "CONDITIONAL",
            "request": case["request"], "pi_delta": case["pi_delta"],
        }
        # A change that preserves a plausible scoped denominator is not enough:
        # the exact original report must still be the evidence for the PDF.
        altered = deepcopy(record)
        altered["captured_at"] = "2026-10-30T10:00:00-04:00"
        with self.assertRaisesRegex(
                ValueError, "PAMALISED_PRIVATE_OBSERVATION_DETAIL_PARITY_INVALID"):
            render_pamalised_pdf(
                **args, portfolio_observation_private=altered)
        fake = deepcopy(record)
        fake["portfolio_room_status"] = "ROOM_EVIDENCE_SUPPORTED"
        with self.assertRaisesRegex(
                ValueError, "REPORT_P_LEDGER_AUTHORITY_OR_ID_MISMATCH"):
            render_pamalised_pdf(
                **args, portfolio_observation_private=fake)

    def test_presentation_rejects_wrong_case_and_unrecognized_fact_link(self):
        request = self.fixtures.request()
        ir = self.fixtures.ir()
        session = complete_manual_session(request, ir_capsule=ir)
        kw = dict(executive_report=session["executive_report_private"],
                  detailed_report=session["final_report_private"],
                  analysis_id=request["analysis_id"], as_of=request["as_of"],
                  strategy=request["strategy_id"], report_status="EXPLORATORY",
                  request=request, ir_capsule=ir)
        valid = {"analysis_id": request["analysis_id"],
                 "as_of": request["as_of"],
                 "opening_paragraph": ("Le mandat permet une analyse prudente "
                                       "fondée sur les faits remis, sans preuve "
                                       "indépendante des sources financières."),
                 "support_refs": ["F1"], "visuals": []}
        with self.assertRaisesRegex(ValueError, "PAMALISED_PRESENTATION_IDENTITY_MISMATCH"):
            render_pamalised_pdf(
                **kw, presentation_inputs={**valid, "analysis_id": "WRONG"})
        with self.assertRaisesRegex(ValueError, "PAMALISED_OPENING_SUPPORT_REFS_INVALID"):
            render_pamalised_pdf(
                **kw, presentation_inputs={**valid, "support_refs": ["MISSING_F999"]})
        with self.assertRaisesRegex(ValueError, "PAMALISED_EVIDENCE_FLOW_INVALID"):
            render_pamalised_pdf(
                **kw, presentation_inputs={**valid, "visuals": [
                    {"kind": "evidence_flow", "title": "Source inexistante",
                     "fact_ids": ["MISSING_F999"]}]})

    def test_presentation_fields_are_not_accepted_by_other_outputs(self):
        request = self.fixtures.request()
        payload = {"request": request, "presentation_inputs": {
            "analysis_id": request["analysis_id"],
            "as_of": request["as_of"], "opening_paragraph": "Example only."
        }}
        out, err = StringIO(), StringIO()
        code = main(["--output", "status"],
                    instream=StringIO(json.dumps(payload)),
                    outstream=out, errstream=err)
        self.assertEqual(code, 2)
        self.assertIn("PAMALISED_PRESENTATION_PDF_ONLY", err.getvalue())

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
