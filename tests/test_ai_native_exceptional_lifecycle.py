"""Synthetic exceptional High-CAGR position lifecycle seam, no live portfolio."""
from copy import deepcopy
import unittest

from ai_native.exceptional_lifecycle import prepare_exceptional_lifecycle_review
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from tests.test_ai_native_construction_contracts import R1ConstructionContracts


class ExceptionalLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.fx = R1ConstructionContracts()

    def case(self):
        request = self.fx.request(True, True)
        request["strategy_id"] = "high-cagr"
        request["exceptional_lifecycle_review_requested"] = True
        ir = self.fx.capsule()
        pi = {
            "analysis_id": "SYN-X", "portfolio_as_of": "2026-10-28",
            "room_status": "ROOM_UNAVAILABLE", "summary": "Synthetic unverified PI",
            "limitations": "Private scope only, no broker authentication",
            "next_action": "Human thesis and costs check",
            "forwarded_ir": deepcopy(ir),
        }
        lifecycle = {
            "analysis_id": "SYN-X", "review_as_of": "2026-10-28",
            "strategy_id": "high-cagr", "account_scope": "SYN-SCOPE",
            "position_p_id": "P1", "security_id": "ABC:TSX",
            "thesis_event": "STRUCTURAL_THESIS_BREAK",
            "analyst_reported_view": "REVIEW_EXIT",
            "original_ir_fact_ids": ["F-1"],
            "current_evidence_refs": ["SYN-REPORT-CURRENT"],
            "fees_status": "UNKNOWN", "fx_status": "UNKNOWN",
            "tax_status": "UNKNOWN",
            "original_thesis_private": "SYNTHETIC_PRIVATE_BASELINE",
            "strongest_countercase_private": "SYNTHETIC_PRIVATE_COUNTERCASE",
            "next_human_check_private": "SYNTHETIC_PRIVATE_REVIEW_REQUIRED",
        }
        return dict(request=request, ir_capsule=ir, pi_delta=pi,
                    observation_inputs=self.fx.observation(),
                    lifecycle_inputs=lifecycle)

    def test_explicit_high_cagr_review_reaches_private_cc_no_trade(self):
        args = self.case()
        snapshot = deepcopy(args)
        out = complete_manual_session(**args)
        self.assertEqual(args, snapshot)
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        review = out["exceptional_lifecycle_review_private"]
        self.assertEqual(review["trade_authority"], "NONE_CEO_ONLY")
        self.assertEqual(review["allocation_or_sale_proposal"], "NONE")
        self.assertEqual(review["status"], "EVIDENCE_RESOLUTION_NO_ACTION")
        self.assertIn("FEES_STATUS_UNKNOWN", review["missing_or_qualified"])
        self.assertEqual(out["integrated_private"]["exceptional_lifecycle_review_private"], review)
        text = out["final_report_private"]
        self.assertIn("Exceptional position lifecycle — High-CAGR", text)
        self.assertIn("specialist-reported hypothesis: REVIEW_EXIT", text)
        for private in ("SYN-SCOPE", "ABC:TSX", "SYNTHETIC_PRIVATE_BASELINE",
                        "SYNTHETIC_PRIVATE_COUNTERCASE", "SYNTHETIC_PRIVATE_REVIEW_REQUIRED"):
            self.assertNotIn(private, text)
            self.assertNotIn(private, str(out["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(out["readiness"], "NOT_EVALUATED")
        self.assertEqual(out["project_invocation"], "NONE")

    def test_complete_looking_packet_remains_human_review_not_trade(self):
        args = self.case()
        for k in ("fees_status", "fx_status", "tax_status"):
            args["lifecycle_inputs"][k] = "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"
        out = complete_manual_session(**args)
        review = out["exceptional_lifecycle_review_private"]
        self.assertEqual(review["status"], "HUMAN_THESIS_AND_COST_REVIEW_ONLY")
        self.assertEqual(review["trade_authority"], "NONE_CEO_ONLY")
        self.assertNotIn("order", review)
        self.assertNotIn("allocation_pct", review)

    def test_no_unrequested_or_other_strategy_lifecycle(self):
        for mutation in ("no_request", "not_high_cagr", "pi_only", "missing_pi"):
            args = self.case()
            if mutation == "no_request":
                args["request"].pop("exceptional_lifecycle_review_requested")
            if mutation == "not_high_cagr":
                args["request"]["strategy_id"] = "EXPLORATORY"
                args["lifecycle_inputs"]["strategy_id"] = "EXPLORATORY"
            if mutation == "pi_only":
                args["request"]["research_needed"] = False
                args.pop("ir_capsule")
            if mutation == "missing_pi":
                args.pop("pi_delta")
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                complete_manual_session(**args)

    def test_volatility_alone_is_not_exceptional_sale_hypothesis(self):
        args = self.case()
        args["lifecycle_inputs"]["thesis_event"] = "VOLATILITY_ONLY"
        for proposed in ("REVIEW_TRIM", "REVIEW_EXIT"):
            args["lifecycle_inputs"]["analyst_reported_view"] = proposed
            with self.subTest(proposed=proposed), self.assertRaisesRegex(
                ValueError, "LIFECYCLE_NO_PRICE_OR_UNCERTAINTY_ONLY_SELL_REVIEW"
            ):
                complete_manual_session(**args)
        args["lifecycle_inputs"]["analyst_reported_view"] = "HOLD"
        report = complete_manual_session(**args)["exceptional_lifecycle_review_private"]
        self.assertIn("NO_STRUCTURAL_SELL_THESIS_FROM_EVENT",
                      report["missing_or_qualified"])

    def test_wrong_position_account_dates_and_original_ir_fact_rejected(self):
        for key, value in (("position_p_id", "UNKNOWN-P"),
                           ("security_id", "WRONG:TSX"),
                           ("account_scope", "ANOTHER-ACCOUNT"),
                           ("review_as_of", "2026-10-27"),
                           ("original_ir_fact_ids", ["INVENTED-FACT"])):
            args = self.case()
            args["lifecycle_inputs"][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                complete_manual_session(**args)
        args = self.case()
        args["observation_inputs"]["private_scope"] = False
        with self.assertRaises(ValueError):
            complete_manual_session(**args)

    def test_conflicted_original_fact_preserves_unresolved(self):
        args = self.case()
        args["ir_capsule"]["facts"][0]["status"] = "CONFLICTED"
        args["pi_delta"]["forwarded_ir"] = deepcopy(args["ir_capsule"])
        out = complete_manual_session(**args)
        self.assertIn("ORIGINAL_IR_FACTS_UNRESOLVED",
                      out["exceptional_lifecycle_review_private"]["missing_or_qualified"])

    def test_report_rejects_authority_spoof(self):
        out = complete_manual_session(**self.case())
        review = out["exceptional_lifecycle_review_private"]
        packet = {
            "kind": "DECISION", "analysis_id": "SYN-X", "as_of": "2026-10-28",
            "strategy": "high-cagr", "method_version": "R1",
            "status": "CONDITIONAL", "objective": "Synthetic review",
            "decision_line": "No action", "summary": ["Unknown"],
            "facts": [], "countercase": "Uncertain",
            "limitations": "Not authenticated", "next_action": "Human review",
        }
        for field, bad in (("trade_authority", "EXECUTE"),
                           ("source_authentication", "VERIFIED"),
                           ("analysis_id", "OTHER")):
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "LIFECYCLE_REPORT_AUTHORITY_OR_ID_MISMATCH"
            ):
                changed = deepcopy(review)
                changed[field] = bad
                render_report({**packet, "exceptional_lifecycle_review_private": changed})


if __name__ == "__main__":
    unittest.main()
