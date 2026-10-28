import unittest

from ai_native.reporting import render_report


class ReportingTests(unittest.TestCase):
    def packet(self, **changes):
        packet = {
            "kind": "DECISION", "analysis_id": "SYN-001", "as_of": "2026-10-28",
            "strategy": "high-cagr", "method_version": "CANDIDATE_R1",
            "status": "EXPLORATORY", "objective": "Compare synthetic businesses",
            "decision_line": "No decision-grade ranking established.",
            "summary": ["A fact conflict blocks numerical comparison."],
            "facts": [{"id": "F1", "claim": "Synthetic unverified margin 12%", "status": "INDICATIVE"}],
            "countercase": "Reported figures may be non-comparable.",
            "limitations": "No verified price or portfolio values.",
            "next_action": "Verify original financial statements.",
        }
        packet.update(changes)
        return packet

    def test_decision_preserves_indicative_status_and_no_url(self):
        text = render_report(self.packet())
        self.assertIn("[F1 / INDICATIVE]", text)
        self.assertIn("SOURCE_NOT_SUPPLIED", text)
        self.assertIn("No source checks", text)

    def test_original_checked_fact_requires_metadata(self):
        with self.assertRaisesRegex(ValueError, "source_url"):
            render_report(self.packet(facts=[{"id": "F1", "claim": "Test", "status": "VERIFIED"}]))

    def test_original_checked_fact_has_attribution(self):
        facts = [{"id": "F1", "claim": "Synthetic report number", "status": "VERIFIED",
                  "source_url": "https://example.com/filing", "period": "FY2025",
                  "checked_by": "Synthetic reviewer", "checked_at": "2026-10-28"}]
        self.assertIn("F1 / VERIFIED", render_report(self.packet(facts=facts)))

    def test_invalid_status_and_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid evidence status"):
            render_report(self.packet(facts=[{"id": "F1", "claim": "x", "status": "CONFIRMED"}]))
        with self.assertRaisesRegex(ValueError, "duplicate evidence ID"):
            render_report(self.packet(facts=[{"id": "F1", "claim": "a", "status": "MISSING"},
                                             {"id": "F1", "claim": "b", "status": "MISSING"}]))

    def test_followup_without_changes_does_not_claim_market_stasis(self):
        text = render_report(self.packet(kind="FOLLOWUP", period_start="2026-10-21",
                                         period_end="2026-10-28", changes=[]))
        self.assertIn("NOT proof", text)
        self.assertIn("User-requested reassessment", text)

    def test_followup_change_keeps_low_confidence_label(self):
        text = render_report(self.packet(kind="FOLLOWUP", period_start="2026-10-21",
                                         period_end="2026-10-28", changes=[
                                             {"subject": "Synthetic company", "finding": "Hypothesis requires checking", "status": "CONFLICTED"}]))
        self.assertIn("[CONFLICTED]", text)

    def test_followup_future_period_rejected(self):
        with self.assertRaisesRegex(ValueError, "ordered"):
            render_report(self.packet(kind="FOLLOWUP", period_start="2026-10-21",
                                      period_end="2026-11-01", changes=[]))

    def test_no_made_up_status_or_missing_baseline(self):
        with self.assertRaisesRegex(ValueError, "unsupported report status"):
            render_report(self.packet(status="PRODUCTION_READY"))
        with self.assertRaisesRegex(ValueError, "summary"):
            render_report(self.packet(summary=[]))

    def test_followup_has_no_mandatory_cadence_or_prior_baseline(self):
        text = render_report(self.packet(kind="FOLLOWUP", changes=[]))
        self.assertIn("no fixed reporting window", text)
        self.assertIn("BASELINE_NOT_AVAILABLE", text)

    def test_followup_can_reference_prior_analysis_after_arbitrary_interval(self):
        text = render_report(self.packet(
            kind="FOLLOWUP", prior_analysis_id="SYN-2025-001",
            period_start="2025-01-01", period_end="2026-10-28", changes=[]))
        self.assertIn("SYN-2025-001", text)

    def test_followup_partial_calendar_window_rejected(self):
        with self.assertRaisesRegex(ValueError, "supplied together"):
            render_report(self.packet(kind="FOLLOWUP", period_start="2026-01-01", changes=[]))

    def test_synthetic_packet_does_not_write_to_disk(self):
        text = render_report(self.packet())
        self.assertIn("No source checks, monitoring, archival", text)



    def source_review(self, **updates):
        row = {"fact_id_private":"F1", "ir_reported_status":"INDICATIVE",
               "observation_ids_private":[], "source_use_statuses":[],
               "review_flags":["NO_OBSERVATION_FOR_IR_FACT"],
               "alignment":"REVIEW_REQUIRED"}
        record = {"status":"PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
                  "analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                  "facts_private":[row], "facts_needing_review":1,
                  "source_authentication":"NOT_PERFORMED",
                  "evidence_upgrade":"NONE", "decision_grade_status":"NOT_ESTABLISHED"}
        record.update(updates)
        return record

    def test_structural_source_flags_are_visible_without_upgrading_ir_label(self):
        text = render_report(self.packet(
            fact_source_alignment_private=self.source_review()))
        self.assertIn("1/1 facts require human source-use review", text)
        self.assertIn("NO_OBSERVATION_FOR_IR_FACT", text)
        self.assertIn("[F1 / INDICATIVE]", text)
        self.assertIn("not independently authenticated", text)

    def test_report_without_annex_marks_ir_verification_as_reported_only(self):
        text = render_report(self.packet())
        self.assertIn("research-reported, not independently authenticated", text)
        self.assertNotIn("Source reconciliation:", text)

    def test_source_review_does_not_accept_conflicting_authority_or_identity(self):
        for key, value in (("analysis_as_of", "2026-10-27"),
                           ("evidence_upgrade", "VERIFIED"),
                           ("source_authentication", "INDEPENDENTLY_CHECKED"),
                           ("facts_needing_review", 0)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "REPORT_SOURCE_REVIEW"):
                render_report(self.packet(fact_source_alignment_private=self.source_review(**{key:value})))

    def test_source_review_rejects_missing_extra_and_mismatched_fact_labels(self):
        record = self.source_review()
        record["facts_private"] = []
        with self.assertRaisesRegex(ValueError, "REPORT_SOURCE_REVIEW_COVERAGE"):
            render_report(self.packet(fact_source_alignment_private=record))
        record = self.source_review()
        record["facts_private"][0]["ir_reported_status"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "REPORT_SOURCE_REVIEW_FACT_MISMATCH"):
            render_report(self.packet(fact_source_alignment_private=record))
        record = self.source_review()
        record["facts_private"][0]["review_flags"] = ["injected markdown\\n# false approval"]
        with self.assertRaisesRegex(ValueError, "REPORT_SOURCE_REVIEW_FLAGS_INVALID"):
            render_report(self.packet(fact_source_alignment_private=record))

    def test_structurally_aligned_source_is_still_not_independently_verified(self):
        record = self.source_review(facts_needing_review=0)
        record["facts_private"][0]["review_flags"] = []
        record["facts_private"][0]["alignment"] = "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"
        text = render_report(self.packet(fact_source_alignment_private=record))
        self.assertIn("0/1 facts", text)
        self.assertNotIn("Source review required:", text)
        self.assertIn("no status was upgraded", text)


    def new_contribution(self, **updates):
        item = {
            "analysis_id":"SYN-001", "portfolio_as_of":"2026-10-28",
            "gross_status":"GROSS_PROJECTION_ONLY",
            "allocations_pct":{"ABC:TSX":"60","VFV:TSX":"40"},
            "cost_status":"NOT_SUPPLIED", "funded_status":"NOT_ASSESSED",
            "source_authentication":"NOT_PERFORMED",
        }
        item.update(updates)
        return item

    def test_new_contribution_report_is_percentage_only_and_gross_labelled(self):
        output = render_report(self.packet(new_contribution_summary_private=self.new_contribution()))
        self.assertIn("60% of new capital", output)
        self.assertIn("40% of new capital", output)
        self.assertIn("NOT ASSESSED", output)
        self.assertIn("not portfolio target weights", output)
        self.assertNotIn("597.00", output)

    def test_new_contribution_funding_is_conditional_not_execution(self):
        output = render_report(self.packet(new_contribution_summary_private=self.new_contribution(
            cost_status="SUPPLIED_COST_TALLY_ONLY",
            funded_status="CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED")))
        self.assertIn("CONDITIONALLY RECONCILED", output)
        self.assertIn("Requote", output)
        self.assertNotIn("executable allocation.", output)

    def test_new_contribution_incomplete_scope_never_displays_percentages(self):
        output = render_report(self.packet(new_contribution_summary_private=self.new_contribution(
            gross_status="UNAVAILABLE", allocations_pct=None,
            cost_status="NOT_SUPPLIED", funded_status="NOT_ASSESSED")))
        self.assertIn("Gross contribution projection UNAVAILABLE", output)
        self.assertNotIn("60% of new capital", output)

    def test_new_contribution_missing_cost_or_funding_is_not_net(self):
        output = render_report(self.packet(new_contribution_summary_private=self.new_contribution(
            cost_status="SUPPLIED_COST_TALLY_ONLY", funded_status="UNAVAILABLE_FUNDING_UNKNOWN")))
        self.assertIn("After-cost funded allocation UNAVAILABLE", output)
        self.assertNotIn("CONDITIONALLY RECONCILED", output)

    def test_tiny_decimal_percentage_does_not_expand_unbounded_string(self):
        output = render_report(self.packet(new_contribution_summary_private=self.new_contribution(
            allocations_pct={"ABC:TSX":"100", "TRACE":"0E-1000000"})))
        self.assertIn("100% of new capital", output)
        self.assertLess(len(output), 4000)

    def test_new_contribution_rejects_forged_or_incompatible_statuses(self):
        for patch in (
            {"analysis_id":"DIFFERENT"},
            {"portfolio_as_of":"2026-10-29"},
            {"source_authentication":"INDEPENDENTLY_VERIFIED"},
            {"funded_status":"EXECUTION_READY"},
            {"allocations_pct":{"ABC:TSX":"75","VFV:TSX":"40"}},
            {"allocations_pct":{"ABC:TSX":"NaN","VFV:TSX":"40"}},
            {"gross_status":"UNAVAILABLE"},
        ):
            with self.subTest(patch=patch), self.assertRaisesRegex(
                ValueError, "CONTRIBUTION_REPORT"):
                render_report(self.packet(new_contribution_summary_private=self.new_contribution(**patch)))

if __name__ == "__main__":
    unittest.main()
