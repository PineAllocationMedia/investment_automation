"""Test #3 F1: no silent shortcut from unqualified issuers to no decision."""
from copy import deepcopy
import unittest

from ai_native.high_cagr_destination_path import (
    prepare_high_cagr_destination_review, render_high_cagr_destination_review,
)
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_session_bridge import SessionBridgeTests


class HighCagrDecisionPathTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def case(self, *, research=True, room="ROOM_UNAVAILABLE"):
        request = self.fx.request(strategy_id="high-cagr", portfolio_needed=True,
                                  research_needed=research)
        pi = self.fx.pi(room_status=room)
        case = {"request": request, "pi_delta": pi}
        if research:
            ir = self.fx.ir()
            case["ir_capsule"] = ir
            case["pi_delta"]["forwarded_ir"] = deepcopy(ir)
        return case

    def test_f1_ir_pi_route_examines_all_three_without_allocation(self):
        p = self.case()
        original = deepcopy(p)
        out = complete_manual_session(**p)
        self.assertEqual(p, original)
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        view = out["high_cagr_destination_review_private"]
        self.assertEqual(view["existing_policy_hierarchy"], [
            "QUALIFIED_INDIVIDUAL_OPPORTUNITY", "VFV_NORMAL_BENCHMARK_FALLBACK",
            "EXCEPTIONAL_TEMPORARY_RESERVE"])
        self.assertEqual(view["company_branch"], "RESEARCH_PRESENT_ADMISSION_UNVERIFIED")
        self.assertEqual(view["vfv_branch"], "ELIGIBILITY_AND_COST_CHECK_REQUIRED")
        self.assertEqual(view["allocation_percentage"], None)
        self.assertEqual(view["trade_authority"], "NONE")
        self.assertEqual(out["integrated_private"]["high_cagr_destination_review_private"],
                         view)
        for report in ("final_report_private", "executive_report_private"):
            self.assertIn("VFV, repli normal", out[report])
            self.assertIn("Reserve temporaire exceptionnelle", out[report])
            self.assertIn("NON ETABLIS", out[report])
            self.assertNotIn("100 % VFV", out[report])
        self.assertNotIn("VFV_NORMAL_BENCHMARK_FALLBACK",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))

    def test_fourth_trial_independent_er_and_room_dependencies(self):
        for status in ("ROOM_UNAVAILABLE", "ROOM_CONDITIONAL", "ROOM_EVIDENCE_SUPPORTED"):
            with self.subTest(status=status):
                output = complete_manual_session(**self.case(room=status))
                trace = output["high_cagr_destination_review_private"]
                self.assertEqual(
                    trace["independent_dependencies"]["economic"],
                    "ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_NOT_ESTABLISHED")
                self.assertEqual(
                    trace["primary_next_action"],
                    "ESTABLISH_ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_WITH_PRIMARY_EVIDENCE")
                self.assertEqual(trace["review_next"], trace["primary_next_action"])
                self.assertEqual(trace["decision_stage"],
                                 "EVIDENCE_GAP_NOT_AN_ALLOCATION_DECISION")
                self.assertIsNone(trace["allocation_percentage"])
                self.assertIn("Deux blocages independants",
                              output["final_report_private"])
                self.assertIn("PAS reparer l'ER manquant",
                              output["final_report_private"])
                self.assertIn("EVIDENCE_GAP", output["final_report_private"])
                self.assertNotIn("100 % VFV", output["final_report_private"])

    def test_pi_only_prioritizes_research_not_a_portfolio_screenshot(self):
        result = complete_manual_session(**self.case(research=False))
        trace = result["high_cagr_destination_review_private"]
        self.assertEqual(trace["independent_dependencies"]["economic"],
                         "ORIGINAL_IR_AND_VFV_COMPARABLE_TOTAL_ER_NOT_SUPPLIED")
        self.assertEqual(trace["primary_next_action"],
                         "OBTAIN_ISSUER_LEVEL_IR_AND_COMPARABLE_VFV_RETURN_EVIDENCE")
        self.assertIn("Deux blocages independants",
                      result["executive_report_private"])

    def test_fake_resolution_of_er_or_room_is_rejected(self):
        case = self.case()
        original = prepare_high_cagr_destination_review(
            request=case["request"], ir_capsule=case["ir_capsule"],
            pi_delta=case["pi_delta"])
        for key, fake in (
            ("decision_stage", "SUPPORTED_ACTION"),
            ("review_next", "BUY_VFV"),
            ("independent_dependencies", {
                "economic": "VERIFIED",
                "personal_room": "CERTIFIED",
                "vfv_account_costs_tax": "VERIFIED"}),
        ):
            forged = deepcopy(original)
            forged[key] = fake
            with self.subTest(key=key), self.assertRaisesRegex(
                    ValueError, "RENDER_AUTHORITY_INVALID"):
                render_high_cagr_destination_review(forged)

    def test_pi_only_route_does_not_claim_issuer_qualification(self):
        out = complete_manual_session(**self.case(research=False, room="ROOM_CONDITIONAL"))
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(out["high_cagr_destination_review_private"]["company_branch"],
                         "RESEARCH_NOT_PROVIDED")
        self.assertIn("Recherche IR originale non fournie", out["final_report_private"])
        self.assertIn("VFV, repli normal", out["executive_report_private"])

    def test_other_strategy_reports_do_not_gain_high_cagr_policy(self):
        p = self.case(research=False)
        p["request"]["strategy_id"] = "balanced"
        out = complete_manual_session(**p)
        self.assertNotIn("high_cagr_destination_review_private", out)
        self.assertNotIn("VFV, repli normal", out["final_report_private"])

    def test_invalid_dates_scope_and_forgery_fail(self):
        p = self.case()
        for variant in ("bad_mode", "bad_pi", "future_pi", "no_ceo"):
            args = deepcopy(p)
            if variant == "bad_mode":
                args["request"]["strategy_id"] = "balanced"
            elif variant == "bad_pi":
                args["pi_delta"]["analysis_id"] = "OTHER"
            elif variant == "future_pi":
                args["pi_delta"]["portfolio_as_of"] = "2026-11-01"
            else:
                args["request"]["ceo_initiated"] = False
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                prepare_high_cagr_destination_review(
                    request=args["request"], ir_capsule=args.get("ir_capsule"),
                    pi_delta=args["pi_delta"])
        clean = prepare_high_cagr_destination_review(
            request=p["request"], ir_capsule=p["ir_capsule"], pi_delta=p["pi_delta"])
        clean["allocation_percentage"] = "100"
        with self.assertRaisesRegex(ValueError, "RENDER_AUTHORITY"):
            render_high_cagr_destination_review(clean)


if __name__ == "__main__":
    unittest.main()
