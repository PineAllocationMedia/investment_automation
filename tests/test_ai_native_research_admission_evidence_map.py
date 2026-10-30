"""F3: research-depth evidence never auto-promotes to investment admission."""
from copy import deepcopy
import unittest

from ai_native.research_admission_evidence_map import (
    prepare_research_admission_evidence_map, render_research_admission_evidence_map,
)
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_session_bridge import SessionBridgeTests


class ResearchAdmissionEvidenceMapTests(unittest.TestCase):
    def setUp(self):
        self.fixture = SessionBridgeTests()

    def test_ir_only_report_includes_blocker_path_without_investing(self):
        request = self.fixture.request()
        ir = self.fixture.ir()
        before = deepcopy((request, ir))
        out = complete_manual_session(request, ir_capsule=ir)
        self.assertEqual((request, ir), before)
        review = out["research_admission_evidence_map_private"]
        self.assertEqual(review["status"],
                         "F3_CASE_LEVEL_EVIDENCE_PATH_NOT_INVESTMENT_ADMISSION")
        self.assertEqual(review["source_stage"], "SOURCE_ANNEX_NOT_SUPPLIED")
        self.assertEqual(review["economic_stage"], "ISSUER_ECONOMICS_NOT_ASSEMBLED")
        self.assertEqual(review["valuation_stage"], "COMPARABLE_FORWARD_VALUE_NOT_ASSEMBLED")
        self.assertEqual(review["investability_status"], "NOT_ESTABLISHED")
        self.assertIsNone(review["new_contribution_percentage"])
        self.assertEqual(review["policy_and_project_method_load"], "NOT_VERIFIED")
        for key in ("final_report_private", "executive_report_private"):
            self.assertIn("De la recherche a l'admissibilite", out[key])
            self.assertIn("aucune entreprise ni aucun vehicule", out[key])
            self.assertNotIn("100 % VFV", out[key])
        self.assertNotIn("F3_CASE_LEVEL",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(out["storage"], "NONE")

    def test_ir_pi_high_cagr_keeps_existing_three_branch_policy_and_f3(self):
        request = self.fixture.request(strategy_id="high-cagr", portfolio_needed=True)
        ir = self.fixture.ir()
        pi = self.fixture.pi(forwarded_ir=deepcopy(ir))
        out = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        self.assertIn("De la recherche a l'admissibilite",
                      out["executive_report_private"])
        self.assertIn("VFV, repli normal", out["final_report_private"])
        review = out["research_admission_evidence_map_private"]
        self.assertEqual(review["mode_policy_stage"],
                         "EXISTING_V2_HIGH_CAGR_SCOPE_UNVERIFIED")
        self.assertEqual(review["pi_stage"],
                         "PI_ROOM_REPORTED_NOT_ACCOUNT_AUTHENTICATED")
        self.assertEqual(review["trade_authority"], "NONE")

    def test_policy_unapproved_modes_not_silently_promoted(self):
        for mode in ("balanced", "family-office", "rational-aggressive",
                     "intelligent-dividend-harvester", "modern-adaptive-browne"):
            with self.subTest(mode=mode):
                out = complete_manual_session(
                    self.fixture.request(strategy_id=mode),
                    ir_capsule=self.fixture.ir())
                review = out["research_admission_evidence_map_private"]
                self.assertEqual(review["mode_policy_stage"],
                                 "R1_FINANCIAL_POLICY_NOT_APPROVED_OR_NO_MODE_AUTHORITY")
                self.assertEqual(review["investability_status"], "NOT_ESTABLISHED")
                self.assertIsNone(review["new_contribution_percentage"])

    def test_no_ir_and_pi_only_do_not_fabricate_qualification(self):
        request = self.fixture.request(portfolio_needed=True, research_needed=False)
        out = complete_manual_session(request, pi_delta=self.fixture.pi())
        self.assertNotIn("research_admission_evidence_map_private", out)
        self.assertNotIn("De la recherche a l'admissibilite",
                         out["final_report_private"])

    def test_fail_closed_forged_policy_quote_and_source_status(self):
        req = self.fixture.request()
        ir = self.fixture.ir()
        actual = complete_manual_session(req, ir_capsule=ir)["integrated_private"]
        for variant in ("policy", "source", "quote", "date", "room"):
            modified = deepcopy(actual)
            if variant == "policy":
                modified["strategy_policy_gate"]["decision_grade"] = "APPROVED"
            elif variant == "source":
                modified["source_evidence_annex_private"] = {
                    "status": "SOURCE_VERIFIED_BY_CODE"}
            elif variant == "quote":
                modified["valuation_quote_trace_private"] = {
                    "status": "CERTIFIED_EXPECTED_RETURN"}
            elif variant == "date":
                modified["status"] = "SYSTEM_ACCEPTED"
            else:
                modified["portfolio_room_status"] = "BROKER_VERIFIED"
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                prepare_research_admission_evidence_map(
                    request=req, ir_capsule=ir, integrated=modified)

    def test_renderer_rejects_trade_or_method_authority_forgery(self):
        req = self.fixture.request()
        ir = self.fixture.ir()
        assembled = complete_manual_session(req, ir_capsule=ir)["integrated_private"]
        review = prepare_research_admission_evidence_map(
            request=req, ir_capsule=ir, integrated=assembled)
        for key, value in (("trade_authority", "GRANTED"),
                           ("new_contribution_percentage", "100"),
                           ("policy_and_project_method_load", "VERIFIED")):
            forged = deepcopy(review)
            forged[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, "REPORT_AUTHORITY_INVALID"):
                render_research_admission_evidence_map(forged)


if __name__ == "__main__":
    unittest.main()
