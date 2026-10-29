import copy
import json
import unittest

from ai_native.strategy_authority import R1_MODES
from ai_native.strategy_research_brief import prepare_strategy_research_brief
from ai_native.request_assembly import prepare_manual_handoffs


class StrategyResearchBriefTests(unittest.TestCase):
    @staticmethod
    def request(strategy, **extra):
        request = dict(ceo_initiated=True, analysis_id="SYN-MODE-20261029",
                       as_of="2026-10-29", objective="Synthetic research only",
                       kind="DECISION", strategy_id=strategy,
                       research_needed=True, portfolio_needed=True)
        request.update(extra)
        return request

    def test_six_distinct_nonbinding_qualitative_briefs(self):
        self.assertEqual(len(R1_MODES), 6)
        ir_variants, pi_variants = set(), set()
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                brief = prepare_strategy_research_brief(mode)
                self.assertEqual(brief["r1_mode"], mode)
                self.assertEqual(len(brief["ir_research_questions"]), 2)
                self.assertEqual(len(brief["pi_portfolio_questions"]), 2)
                self.assertEqual(brief["method_load"], "NOT_VERIFIED")
                self.assertEqual(brief["allocation_or_sale_authority"], "NONE")
                self.assertEqual(brief["decision_grade_authority"], "NONE")
                self.assertTrue(brief["design_reference_not_loaded_or_approved"].endswith(".md"))
                ir_variants.add(tuple(brief["ir_research_questions"]))
                pi_variants.add(tuple(brief["pi_portfolio_questions"]))
        self.assertEqual((len(ir_variants), len(pi_variants)), (6, 6))

    def test_ir_method_reference_high_cagr_only(self):
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                prepared = prepare_manual_handoffs(self.request(mode))
                ir = prepared["ir_request_private"]
                refs = ir["requested_method_references_not_proof_of_loading"]
                self.assertIn("SOURCE_FUSION_R1", refs)
                self.assertIn("VALUATION_R1", refs)
                self.assertEqual("HIGH_CAGR_METHOD_R1_IF_APPROVED" in refs, mode == "high-cagr")
                self.assertEqual(ir["strategy_research_questions_nonbinding"],
                                 prepared["strategy_research_brief"]["ir_research_questions"])
                self.assertEqual(ir["r1_strategy_policy_authority"],
                                 prepared["strategy_policy_gate"]["policy_authority"])
                self.assertEqual(ir["r1_strategy_method_load"], "NOT_VERIFIED")
                self.assertNotIn("asset_target_weights", ir)

    def test_pi_questions_forward_and_ir_exactly_unchanged(self):
        r = self.request("modern-adaptive-browne")
        original_request = copy.deepcopy(r)
        capsule = {"analysis_id": "SYN-MODE-20261029", "research_as_of": "2026-10-29",
                   "summary": ["Synthetic"], "facts": [{"id": "F1", "status": "MISSING"}]}
        original_capsule = copy.deepcopy(capsule)
        prepared = prepare_manual_handoffs(r, ir_capsule=capsule)
        pi = prepared["pi_request_private"]
        self.assertEqual(pi["FORWARD_UNCHANGED"], original_capsule)
        self.assertEqual(pi["strategy_portfolio_questions_nonbinding"],
                         prepared["strategy_research_brief"]["pi_portfolio_questions"])
        self.assertEqual(pi["strategy_design_reference_not_loaded_or_approved"],
                         prepared["ir_request_private"]["strategy_design_reference_not_loaded_or_approved"])
        self.assertEqual(json.loads(prepared["copy_ready_private"]["PI_REQUEST"])["FORWARD_UNCHANGED"], capsule)
        self.assertEqual(r, original_request)
        self.assertEqual(capsule, original_capsule)

    def test_pi_only_does_not_invent_ir_or_high_cagr_policy(self):
        prepared = prepare_manual_handoffs(self.request("balanced", research_needed=False))
        self.assertEqual(prepared["route"], "CC_PI_CC")
        self.assertIsNone(prepared["ir_request_private"])
        self.assertEqual(prepared["pi_request_private"]["FORWARD_UNCHANGED"], None)
        self.assertIn("cross-asset", " ".join(prepared["pi_request_private"]["strategy_portfolio_questions_nonbinding"]))
        self.assertEqual(prepared["strategy_policy_gate"]["policy_authority"],
                         "R1_POLICY_REQUIRES_CEO_APPROVAL")

    def test_unapproved_old_mode_names_stay_rejected(self):
        for retired in ("capital-preservation", "income"):
            with self.subTest(retired=retired):
                with self.assertRaisesRegex(ValueError, "R1_OBJECTIVE_NOT_STRATEGY"):
                    prepare_manual_handoffs(self.request(retired))

    def test_exploratory_does_not_receive_specific_policy_or_high_cagr_method(self):
        prepared = prepare_manual_handoffs(self.request("EXPLORATORY"))
        ir = prepared["ir_request_private"]
        self.assertIsNone(ir["strategy_design_reference_not_loaded_or_approved"])
        self.assertNotIn("HIGH_CAGR_METHOD_R1_IF_APPROVED",
                         ir["requested_method_references_not_proof_of_loading"])
        self.assertEqual(prepared["strategy_research_brief"]["decision_grade_authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
