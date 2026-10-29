"""Synthetic exceptional High-CAGR position lifecycle seam, no live portfolio."""
from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.exceptional_lifecycle import prepare_exceptional_lifecycle_review
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from scripts.r1_manual_session_cli import main
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
        source = {
            "analysis_id": "SYN-X", "analysis_as_of": "2026-10-28",
            "observations": [{
                "observation_id": "SYN-REPORT-CURRENT", "fact_id": "F-1",
                "source_id": "SYN-CURRENT-SRC", "economic_issuer": "SYN-ISSUER",
                "instrument": "ABC:TSX", "metric": "REVENUE",
                "period_start": "2025-01-01", "period_end": "2025-12-31",
                "currency": "CAD", "unit": "MILLIONS", "definition_basis": "IFRS",
                "consolidation": "GROUP", "value": "100",
                "observed_at": "2026-10-28", "published_at": "2026-03-01",
                "original_checked_at": "2026-10-28",
                "source_kind": "ISSUER_OR_REGULATOR",
                "classification": "SOURCE_FACT", "rights_status": "PERMITTED",
                "verification_status": "INDICATIVE",
                "source_locator": "https://example.org/synthetic-lifecycle-only",
            }],
        }
        return dict(request=request, ir_capsule=ir, pi_delta=pi,
                    observation_inputs=self.fx.observation(),
                    lifecycle_inputs=lifecycle,
                    lifecycle_current_evidence_inputs=source)

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

    def test_requested_lifecycle_cannot_silently_complete_without_review(self):
        args = self.case()
        args.pop("lifecycle_inputs")
        args.pop("lifecycle_current_evidence_inputs")
        with self.assertRaisesRegex(
            ValueError, "LIFECYCLE_REQUESTED_REVIEW_NOT_SUPPLIED"
        ):
            complete_manual_session(**args)
        args.pop("pi_delta")
        pending = complete_manual_session(**args)
        self.assertEqual(pending["status"], "AWAITING_MANUAL_PI_DELTA")

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

    def _review_codes(self, args):
        from ai_native.manual_review_queue import prepare_manual_review_queue
        result = complete_manual_session(**args)
        queue = prepare_manual_review_queue(result)
        return result, queue, [item["code"] for item in queue["items"]]

    def test_lifecycle_cost_unknown_reaches_cc_operator_queue(self):
        args = self.case()
        saved = deepcopy(args)
        result, queue, codes = self._review_codes(args)
        self.assertIn("VERIFY_LIFECYCLE_TRANSACTION_COSTS", codes)
        self.assertEqual(codes.count("VERIFY_LIFECYCLE_TRANSACTION_COSTS"), 1)
        self.assertEqual(queue["trading_authority"], "NONE")
        self.assertEqual(queue["readiness"], "NOT_EVALUATED")
        self.assertLessEqual(queue["item_count"], 13)
        self.assertEqual(args, saved)
        for secret in ("SYN-SCOPE", "ABC:TSX", "SYNTHETIC_PRIVATE_BASELINE",
                       "SYNTHETIC_PRIVATE_COUNTERCASE"):
            self.assertNotIn(secret, str(queue))

    def test_lifecycle_prioritizes_disputed_original_ir_fact(self):
        args = self.case()
        args["ir_capsule"]["facts"][0]["status"] = "CONFLICTED"
        args["pi_delta"]["forwarded_ir"] = deepcopy(args["ir_capsule"])
        _, _, codes = self._review_codes(args)
        self.assertIn("RESOLVE_LIFECYCLE_IR_FACTS", codes)
        self.assertNotIn("VERIFY_LIFECYCLE_TRANSACTION_COSTS", codes)

    def test_lifecycle_prioritizes_missing_current_evidence(self):
        args = self.case()
        args["lifecycle_inputs"]["current_evidence_refs"] = []
        args.pop("lifecycle_current_evidence_inputs")
        _, _, codes = self._review_codes(args)
        self.assertIn("FIND_LIFECYCLE_CURRENT_EVIDENCE", codes)
        self.assertNotIn("VERIFY_LIFECYCLE_TRANSACTION_COSTS", codes)

    def test_lifecycle_scope_uncertain_routes_to_human_check(self):
        args = self.case()
        args["observation_inputs"]["scope_complete"] = False
        _, _, codes = self._review_codes(args)
        self.assertIn("RECONCILE_LIFECYCLE_HOLDINGS_SCOPE", codes)

    def test_lifecycle_volatility_hold_only_requests_nonstructural_review(self):
        args = self.case()
        args["lifecycle_inputs"]["thesis_event"] = "VOLATILITY_ONLY"
        args["lifecycle_inputs"]["analyst_reported_view"] = "HOLD"
        for key in ("fees_status", "fx_status", "tax_status"):
            args["lifecycle_inputs"][key] = "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"
        _, queue, codes = self._review_codes(args)
        self.assertIn("REVIEW_LIFECYCLE_NONSTRUCTURAL_EVENT", codes)
        self.assertNotIn("REVIEW_LIFECYCLE_THESIS_AND_COSTS", codes)
        self.assertEqual(queue["trading_authority"], "NONE")

    def test_lifecycle_complete_looking_case_remains_human_only(self):
        args = self.case()
        for key in ("fees_status", "fx_status", "tax_status"):
            args["lifecycle_inputs"][key] = "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"
        _, queue, codes = self._review_codes(args)
        self.assertIn("REVIEW_LIFECYCLE_THESIS_AND_COSTS", codes)
        self.assertNotIn("VERIFY_LIFECYCLE_TRANSACTION_COSTS", codes)
        self.assertEqual(queue["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(queue["trading_authority"], "NONE")

    def test_explicit_cli_review_queue_routes_fixed_lifecycle_task_not_private_values(self):
        args = self.case()
        saved = deepcopy(args)
        outputs = {}
        for mode in ("status", "review-queue"):
            stdout, stderr = StringIO(), StringIO()
            code = main(["--output", mode],
                        instream=StringIO(json.dumps(args)),
                        outstream=stdout, errstream=stderr)
            self.assertEqual((code, stderr.getvalue()), (0, ""))
            outputs[mode] = stdout.getvalue()
        status = json.loads(outputs["status"])
        review = json.loads(outputs["review-queue"])
        self.assertEqual(status["readiness"], "NOT_EVALUATED")
        self.assertNotIn("items", status)
        self.assertIn("VERIFY_LIFECYCLE_TRANSACTION_COSTS",
                      [item["code"] for item in review["items"]])
        self.assertEqual(review["trading_authority"], "NONE")
        for value in ("SYN-SCOPE", "ABC:TSX", "SYNTHETIC_PRIVATE_BASELINE",
                      "SYNTHETIC_PRIVATE_COUNTERCASE"):
            self.assertNotIn(value, outputs["status"])
            self.assertNotIn(value, outputs["review-queue"])
        self.assertEqual(args, saved)

    def test_lifecycle_review_queue_rejects_spoofed_authority_and_identity(self):
        from ai_native.manual_review_queue import prepare_manual_review_queue
        for key, bad in (
            ("trade_authority", "TRADING_APPROVED"),
            ("source_authentication", "ORIGINAL_VERIFIED"),
            ("portfolio_observed_on", "2026-10-27"),
            ("analysis_id", "ANOTHER_CASE"),
            ("missing_or_qualified", ["USER_GENERATED_PRIVATE_NOTE"]),
            ("missing_or_qualified", [{"UNHASHABLE": "SECRET"}]),
            ("status", "HUMAN_THESIS_AND_COST_REVIEW_ONLY"),
        ):
            with self.subTest(key=key):
                result = complete_manual_session(**self.case())
                changed = deepcopy(result["exceptional_lifecycle_review_private"])
                changed[key] = bad
                result["exceptional_lifecycle_review_private"] = changed
                result["integrated_private"]["exceptional_lifecycle_review_private"] = deepcopy(changed)
                with self.assertRaises(ValueError):
                    prepare_manual_review_queue(result)

    def test_no_lifecycle_review_no_special_operator_task(self):
        from ai_native.manual_review_queue import prepare_manual_review_queue
        args = self.case()
        args["request"].pop("exceptional_lifecycle_review_requested")
        args.pop("lifecycle_inputs")
        args.pop("lifecycle_current_evidence_inputs")
        completed = complete_manual_session(**args)
        queue = prepare_manual_review_queue(completed)
        self.assertFalse(any("LIFECYCLE" in item["code"] for item in queue["items"]))
        pending = self.case()
        pending.pop("pi_delta")
        pending.pop("lifecycle_inputs")
        waiting = complete_manual_session(**pending)
        queue = prepare_manual_review_queue(waiting)
        self.assertIn("TRANSFER_PI_DELTA", [item["code"] for item in queue["items"]])
        self.assertFalse(any("LIFECYCLE" in item["code"] for item in queue["items"]))

    def test_lifecycle_current_sources_are_original_fact_linked_not_authenticated(self):
        args = self.case()
        for field in ("fees_status", "fx_status", "tax_status"):
            args["lifecycle_inputs"][field] = "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"
        result = complete_manual_session(**args)
        review = result["exceptional_lifecycle_review_private"]
        self.assertEqual(review["status"], "HUMAN_THESIS_AND_COST_REVIEW_ONLY")
        annex = review["current_evidence_annex_private"]
        self.assertEqual(annex["source_authentication"], "NOT_PERFORMED_BY_CODE")
        self.assertEqual(annex["observations_private"][0]["claim_use_status"],
                         "CALLER_REPORTED_ONLY")
        self.assertNotIn("CURRENT_EVIDENCE_UNRESOLVED", review["missing_or_qualified"])
        self.assertNotIn("synthetic-lifecycle-only", result["final_report_private"])
        self.assertNotIn("SYN-CURRENT-SRC", result["final_report_private"])
        self.assertEqual(result["readiness"], "NOT_EVALUATED")

    def test_lifecycle_unlinked_reference_remains_evidence_resolution(self):
        args = self.case()
        args.pop("lifecycle_current_evidence_inputs")
        for field in ("fees_status", "fx_status", "tax_status"):
            args["lifecycle_inputs"][field] = "SUPPLIED_NOT_INDEPENDENTLY_CHECKED"
        result, queue, codes = self._review_codes(args)
        review = result["exceptional_lifecycle_review_private"]
        self.assertEqual(review["status"], "EVIDENCE_RESOLUTION_NO_ACTION")
        self.assertIn("CURRENT_EVIDENCE_NOT_STRUCTURALLY_LINKED", review["missing_or_qualified"])
        self.assertIn("FIND_LIFECYCLE_CURRENT_EVIDENCE", codes)
        self.assertEqual(queue["trading_authority"], "NONE")
        self.assertIsNone(review["current_evidence_annex_private"])

    def test_lifecycle_current_source_conflicts_rights_or_future_never_upgrade(self):
        for change in (
            {"rights_status": "UNCERTAIN"},
            {"observed_at": "2026-10-29"},
            {"source_locator": "not-valid-url"},
            {"value": None},
        ):
            with self.subTest(change=change):
                args = self.case()
                args["lifecycle_current_evidence_inputs"]["observations"][0].update(change)
                out, queue, codes = self._review_codes(args)
                review = out["exceptional_lifecycle_review_private"]
                self.assertIn("CURRENT_EVIDENCE_UNRESOLVED", review["missing_or_qualified"])
                self.assertIn("FIND_LIFECYCLE_CURRENT_EVIDENCE", codes)
                self.assertEqual(review["trade_authority"], "NONE_CEO_ONLY")
                self.assertEqual(queue["source_authentication"], "NOT_PERFORMED")

    def test_lifecycle_current_source_wrong_ids_or_fact_links_rejected(self):
        for location, changed in (
            ("annex_case", "OTHER_CASE"),
            ("source_id", "WRONG_CURRENT_OBSERVATION"),
            ("fact_id", "UNKNOWN_ORIGINAL_FACT"),
        ):
            with self.subTest(location=location):
                args = self.case()
                if location == "annex_case":
                    args["lifecycle_current_evidence_inputs"]["analysis_id"] = changed
                elif location == "source_id":
                    args["lifecycle_current_evidence_inputs"]["observations"][0]["observation_id"] = changed
                else:
                    args["lifecycle_current_evidence_inputs"]["observations"][0]["fact_id"] = changed
                with self.assertRaises(ValueError):
                    complete_manual_session(**args)

    def test_current_annex_requires_bounded_original_lifecycle_review(self):
        args = self.case()
        args.pop("lifecycle_inputs")
        with self.assertRaisesRegex(
            ValueError, "LIFECYCLE_CURRENT_EVIDENCE_REQUIRES_REVIEW"
        ):
            complete_manual_session(**args)
        args = self.case()
        args["lifecycle_current_evidence_inputs"]["observations"] = (
            args["lifecycle_current_evidence_inputs"]["observations"] * 25
        )
        with self.assertRaisesRegex(
            ValueError, "LIFECYCLE_CURRENT_ANNEX_BOUNDED_ROWS_REQUIRED"
        ):
            complete_manual_session(**args)
        args = self.case()
        args["lifecycle_inputs"]["current_evidence_refs"] = []
        with self.assertRaisesRegex(
            ValueError, "LIFECYCLE_CURRENT_ANNEX_WITHOUT_REFERENCES"
        ):
            complete_manual_session(**args)

    def test_lifecycle_review_queue_rejects_forged_current_source_trace(self):
        from ai_native.manual_review_queue import prepare_manual_review_queue
        for field, bad in (
            ("source_authentication", "VERIFIED_ORIGINAL"),
            ("analysis_id", "OTHER"),
            ("source_rights_authority", "GRANTED"),
        ):
            with self.subTest(field=field):
                result = complete_manual_session(**self.case())
                altered = deepcopy(result["exceptional_lifecycle_review_private"])
                altered["current_evidence_annex_private"][field] = bad
                result["exceptional_lifecycle_review_private"] = altered
                result["integrated_private"]["exceptional_lifecycle_review_private"] = deepcopy(altered)
                with self.assertRaises(ValueError):
                    prepare_manual_review_queue(result)

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
