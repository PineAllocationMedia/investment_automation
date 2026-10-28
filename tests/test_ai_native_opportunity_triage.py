import copy
import unittest

from ai_native.opportunity_triage import prepare_opportunity_triage


class OpportunityTriageTests(unittest.TestCase):
    def setup_case(self):
        return {
            "analysis_id": "SYN-R1", "analysis_as_of": "2026-10-28",
            "strategy_id": "high-cagr", "universe_scope": "WATCHLIST",
            "universe_note": "Synthetic manually supplied subset, not global search",
            "ir_facts": [{"id": "F1", "status": "INDICATIVE", "claim": "SENSITIVE"}],
            "source_annex": {
                "status": "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED",
                "analysis_id": "SYN-R1", "analysis_as_of": "2026-10-28",
                "source_authentication": "NOT_PERFORMED_BY_CODE",
                "observations_private": [
                    {"observation_id": "O1", "fact_id": "F1",
                     "claim_use_status": "CALLER_REPORTED_ONLY",
                     "economic_issuer": "SYN-CO", "instrument": "SYN:NYSE",
                     "rights_status": "PERMITTED", "source_kind": "ISSUER_OR_REGULATOR",
                     "classification": "SOURCE_FACT", "value": "500.00"}]},
            "candidates": [
                {"candidate_id": "C1", "economic_issuer": "SYN-CO",
                 "instrument": "SYN:NYSE", "target_type": "ISSUER",
                 "origin_scope": "WATCHLIST", "research_question": "What drives durability?",
                 "ir_fact_ids": ["F1"], "open_questions": ["Check customer churn"],
                 "known_risks": ["Revenue concentration"]}]}

    def test_structural_case_only_human_review_not_buy(self):
        out = prepare_opportunity_triage(**self.setup_case())
        self.assertEqual(out["stage_counts"], {"EVIDENCE_RESOLUTION": 0, "HUMAN_DEEP_DIVE": 1})
        self.assertEqual(out["ranking_or_buy_recommendation"], "NONE")
        self.assertEqual(out["normalized_expected_return"], "NOT_ESTABLISHED")
        self.assertEqual(out["universe_completeness"], "NOT_VERIFIED_NOT_GLOBAL_SCREENING")
        self.assertEqual(out["candidates_private_in_supplied_order"][0]["investability"], "NOT_EVALUATED")

    def test_missing_fact_link_needs_evidence(self):
        data = self.setup_case()
        data["candidates"][0]["ir_fact_ids"] = []
        out = prepare_opportunity_triage(**data)
        self.assertIn("NO_ORIGINAL_IR_FACT_LINKS", out["candidates_private_in_supplied_order"][0]["review_reasons"])
        self.assertEqual(out["stage_counts"]["EVIDENCE_RESOLUTION"], 1)

    def test_unobserved_fact_needs_evidence(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"] = []
        out = prepare_opportunity_triage(**data)
        self.assertIn("NO_SOURCE_OBSERVATION", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_conflict_stays_in_evidence_resolution(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"][0]["claim_use_status"] = "CONFLICTED"
        out = prepare_opportunity_triage(**data)
        self.assertIn("SOURCE_UNRESOLVED_OR_UNUSABLE", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_uncertain_source_rights_never_admitted(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"][0]["rights_status"] = "UNCERTAIN"
        out = prepare_opportunity_triage(**data)
        self.assertIn("SOURCE_RIGHTS_NOT_ESTABLISHED", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_secondary_alone_does_not_prove_primary(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"][0]["source_kind"] = "SECONDARY"
        out = prepare_opportunity_triage(**data)
        self.assertIn("PRIMARY_SOURCE_FACT_NOT_DOCUMENTED", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_issuer_instrument_identity_mismatch_not_silently_mixed(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"][0]["instrument"] = "OTHER:NYSE"
        out = prepare_opportunity_triage(**data)
        self.assertIn("SOURCE_SECURITY_IDENTITY_MISMATCH", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_unknown_original_ir_fact_rejected(self):
        data = self.setup_case()
        data["candidates"][0]["ir_fact_ids"] = ["INVENTED"]
        with self.assertRaisesRegex(ValueError, "CANDIDATE_UNKNOWN_ORIGINAL_IR_FACT"):
            prepare_opportunity_triage(**data)

    def test_duplicate_candidates_blocked(self):
        data = self.setup_case()
        data["candidates"].append(copy.deepcopy(data["candidates"][0]))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CANDIDATE_OR_SECURITY"):
            prepare_opportunity_triage(**data)

    def test_duplicate_observations_blocked(self):
        data = self.setup_case()
        data["source_annex"]["observations_private"].append(copy.deepcopy(data["source_annex"]["observations_private"][0]))
        with self.assertRaisesRegex(ValueError, "SOURCE_OBSERVATION_ID_OR_STATUS_INVALID"):
            prepare_opportunity_triage(**data)

    def test_unresolved_ir_fact_remains_unresolved(self):
        data = self.setup_case()
        data["ir_facts"][0]["status"] = "MISSING"
        out = prepare_opportunity_triage(**data)
        self.assertIn("IR_FACT_UNRESOLVED", out["candidates_private_in_supplied_order"][0]["review_reasons"])

    def test_missing_questions_rejected_to_avoid_fake_completeness(self):
        data = self.setup_case()
        data["candidates"][0]["open_questions"] = []
        with self.assertRaisesRegex(ValueError, "open_questions"):
            prepare_opportunity_triage(**data)

    def test_annex_identity_mismatch_blocked(self):
        data = self.setup_case()
        data["source_annex"]["analysis_id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "OPPORTUNITY_SOURCE_ANNEX_MISMATCH"):
            prepare_opportunity_triage(**data)

    def test_date_must_be_canonical_iso(self):
        data = self.setup_case()
        data["analysis_as_of"] = "2026-10-99"
        data["source_annex"]["analysis_as_of"] = data["analysis_as_of"]
        with self.assertRaisesRegex(ValueError, "ANALYSIS_DATE_INVALID"):
            prepare_opportunity_triage(**data)

    def test_invalid_candidate_count_rejected(self):
        data = self.setup_case()
        data["candidates"] = []
        with self.assertRaisesRegex(ValueError, "CANDIDATE_COUNT_MUST_BE_1_TO_30"):
            prepare_opportunity_triage(**data)

    def test_private_claim_and_numeric_value_not_copied(self):
        out = prepare_opportunity_triage(**self.setup_case())
        self.assertNotIn("SENSITIVE", str(out))
        self.assertNotIn("500.00", str(out))

    def test_never_mutates_input(self):
        data = self.setup_case()
        snapshot = copy.deepcopy(data)
        prepare_opportunity_triage(**data)
        self.assertEqual(data, snapshot)

    def test_two_cases_preserve_supplied_order_no_rank(self):
        data = self.setup_case()
        data["ir_facts"].append({"id": "F2", "status": "INDICATIVE"})
        data["candidates"].insert(0, {
            "candidate_id": "C2", "economic_issuer": "SECOND-CO", "instrument": "SECOND:TSX",
            "target_type": "ISSUER", "origin_scope": "PUBLIC_DISCOVERY",
            "research_question": "What is reinvestment runway?", "ir_fact_ids": ["F2"],
            "open_questions": ["Original financials"], "known_risks": []})
        out = prepare_opportunity_triage(**data)
        self.assertEqual([x["candidate_id_private"] for x in out["candidates_private_in_supplied_order"]], ["C2", "C1"])
        self.assertEqual(out["stage_counts"], {"EVIDENCE_RESOLUTION": 1, "HUMAN_DEEP_DIVE": 1})



    def test_real_triage_results_render_without_issuer_private_details(self):
        from ai_native.reporting import render_report
        triage = prepare_opportunity_triage(**self.setup_case())
        packet = {
            "kind":"DECISION", "analysis_id":"SYN-R1","as_of":"2026-10-28",
            "strategy":"high-cagr","method_version":"M2_SYN","status":"CONDITIONAL",
            "objective":"Synthetic supplied watchlist review",
            "decision_line":"Research only","summary":["Indication only"],
            "facts":[],"countercase":"Research may be incomplete",
            "limitations":"Original source not authenticated",
            "next_action":"Review original issuer source",
            "opportunity_triage_private":triage,
        }
        output = render_report(packet)
        self.assertIn("1 queued for human deep dive", output)
        self.assertIn("C1", output)
        self.assertNotIn("SYN-CO", output)
        self.assertNotIn("What drives durability?", output)
        self.assertNotIn("500.00", output)

if __name__ == "__main__":
    unittest.main()
