"""Synthetic-only, privacy-minimal tests for an explicitly manual R1 intake review."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.intake_review import prepare_intake_review
from scripts.r1_manual_session_cli import main


class IntakeReviewTests(unittest.TestCase):
    def template(self):
        out, err = StringIO(), StringIO()
        code = main(["--output", "request-template"], instream=StringIO(),
                    outstream=out, errstream=err)
        self.assertEqual((code, err.getvalue()), (0, ""))
        return json.loads(out.getvalue())

    def review_cli(self, case, *, raw=False):
        stdin = StringIO(case if raw else json.dumps(case))
        out, err = StringIO(), StringIO()
        code = main(["--output", "intake-review"], instream=stdin,
                    outstream=out, errstream=err)
        return code, out.getvalue(), err.getvalue()

    def complete(self, *, strategy="high-cagr", research=True, portfolio=True):
        case = self.template()
        case["request"].update({
            "ceo_initiated": True, "analysis_id": "SYN-CASE-01",
            "as_of": "2026-10-29", "kind": "DECISION",
            "objective": "Synthetic research only; confidential sentinel",
            "strategy_id": strategy, "research_needed": research,
            "portfolio_needed": portfolio,
        })
        return case

    def test_inert_template_reports_missing_fields_without_values(self):
        draft = self.template()
        original = deepcopy(draft)
        code, body, err = self.review_cli(draft)
        self.assertEqual((code, err), (0, ""))
        review = json.loads(body)
        self.assertEqual(review["status"], "INTAKE_INCOMPLETE_NOT_SENT")
        self.assertIn("request.ceo_initiated", review["missing_or_invalid_fields"])
        self.assertIn("request.research_needed", review["missing_or_invalid_fields"])
        self.assertIn("request.as_of", review["missing_or_invalid_fields"])
        self.assertIsNone(review["route_if_valid"])
        self.assertEqual(review["ceo_initiation"], "NOT_ASSERTED")
        self.assertEqual(review["project_invocation"], "NONE")
        self.assertEqual(review["storage"], "NONE")
        self.assertEqual(draft, original)

    def test_filled_ceo_intake_shows_existing_ir_pi_route_and_policy_gate(self):
        case = self.complete()
        original = deepcopy(case)
        code, body, err = self.review_cli(case)
        self.assertEqual((code, err), (0, ""))
        review = json.loads(body)
        self.assertEqual(review["status"], "INTAKE_STRUCTURALLY_READY_NOT_SENT")
        self.assertEqual(review["missing_or_invalid_fields"], [])
        self.assertEqual(review["route_if_valid"], "CC_IR_PI_CC")
        self.assertEqual(review["strategy_policy_authority"],
                         "V2_HIGH_CAGR_EXISTING_SCOPE_ONLY")
        self.assertEqual(review["method_load_verification"], "NOT_PERFORMED")
        self.assertIn("CONFIRM_ACCOUNT_FX_COST", review["human_review_codes"])
        self.assertNotIn("SYN-CASE-01", body)
        self.assertNotIn("Synthetic research only", body)
        self.assertEqual(case, original)

    def test_pi_only_and_direct_routes_reuse_existing_m1_validator(self):
        pi = prepare_intake_review(self.complete(research=False))
        direct = prepare_intake_review(self.complete(research=False, portfolio=False))
        self.assertEqual(pi["route_if_valid"], "CC_PI_CC")
        self.assertEqual(direct["route_if_valid"], "CC_DIRECT")
        self.assertEqual(pi["project_invocation"], "NONE")
        self.assertEqual(direct["trading_authority"], "NONE")

    def test_selected_six_modes_never_get_unapproved_financial_authority(self):
        for mode in ("balanced", "family-office", "rational-aggressive",
                     "intelligent-dividend-harvester", "modern-adaptive-browne"):
            with self.subTest(mode=mode):
                review = prepare_intake_review(self.complete(strategy=mode))
                self.assertEqual(review["status"], "INTAKE_STRUCTURALLY_READY_NOT_SENT")
                self.assertEqual(review["strategy_policy_authority"],
                                 "R1_POLICY_REQUIRES_CEO_APPROVAL")
                self.assertIn("MODE_POLICY_NOT_APPROVED_OR_RECOGNIZED",
                              review["human_review_codes"])
                self.assertEqual(review["readiness"], "NOT_EVALUATED")

    def test_strategic_objective_is_not_silently_accepted_as_mode(self):
        for mode in ("income", "capital-preservation"):
            with self.subTest(mode=mode):
                review = prepare_intake_review(self.complete(strategy=mode))
                self.assertEqual(review["status"], "INTAKE_INCOMPLETE_NOT_SENT")
                self.assertIn("request.strategy_id", review["missing_or_invalid_fields"])
                self.assertIsNone(review["route_if_valid"])

    def test_bad_date_and_non_boolean_route_are_not_made_executable(self):
        case = self.complete()
        case["request"].update({"as_of": "2026-02-30", "portfolio_needed": "yes"})
        review = prepare_intake_review(case)
        self.assertIn("request.as_of", review["missing_or_invalid_fields"])
        self.assertIn("request.portfolio_needed", review["missing_or_invalid_fields"])
        self.assertIsNone(review["route_if_valid"])

    def test_other_contract_errors_return_fixed_code_not_private_values(self):
        case = self.complete()
        case["request"]["investor_profile_private"] = {
            "summary": "PRIVATE_PROFILE_SENTINEL", "preferences": {"bad": "secret"}}
        code, body, err = self.review_cli(case)
        self.assertEqual((code, err), (0, ""))
        review = json.loads(body)
        self.assertIn("REQUEST_CONTRACT_REVIEW_REQUIRED",
                      review["missing_or_invalid_fields"])
        self.assertEqual(review["status"], "INTAKE_INCOMPLETE_NOT_SENT")
        self.assertNotIn("PRIVATE_PROFILE_SENTINEL", body)
        self.assertNotIn("secret", body)

    def test_extra_envelopes_and_duplicate_json_fail_without_sensitive_echo(self):
        case = self.complete()
        case["ir_capsule"] = {"secret": "PRIVATE_IR_SENTINEL"}
        code, body, err = self.review_cli(case)
        self.assertEqual((code, body), (2, ""))
        self.assertIn("INPUT_CONTRACT_REJECTED", err)
        self.assertNotIn("PRIVATE_IR_SENTINEL", err)
        code, body, err = self.review_cli(
            '{"request":{"ceo_initiated":false,"ceo_initiated":true}}', raw=True)
        self.assertEqual((code, body), (2, ""))
        self.assertIn("DUPLICATE_JSON_FIELD", err)

    def test_followup_baseline_is_advisory_not_fake_history(self):
        case = self.complete(strategy="EXPLORATORY", portfolio=False)
        case["request"]["kind"] = "FOLLOWUP"
        result = prepare_intake_review(case)
        self.assertEqual(result["status"], "INTAKE_STRUCTURALLY_READY_NOT_SENT")
        self.assertIn("CHECK_FOLLOWUP_BASELINE", result["human_review_codes"])
        self.assertEqual(result["strategy_policy_authority"],
                         "EXPLORATORY_NO_STRATEGY_POLICY")


if __name__ == "__main__":
    unittest.main()
