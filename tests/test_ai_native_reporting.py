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


    def valuation_packet(self, **changes):
        from ai_native.valuation_scenarios import evaluate_valuation_scenarios
        assumptions = {}
        for name, terminal in (("BEAR", "81"), ("BASE", "121"), ("BULL", "144")):
            assumptions[name] = {
                "valuation_method":"OTHER_EXPLICIT",
                "assumption_basis":"PAM_ASSUMPTION",
                "rationale_ref":"SYN-RATIONALE",
                "terminal_price_per_share":terminal,
                "terminal_value_ref":"SYN-TERMINAL",
                "annual_distributions_per_share":None,
            }
        inputs = {
            "analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
            "security_id":"SYN:TSX", "currency":"CAD",
            "quoted_at":"2026-10-28", "quote_source_ref":"SYN-QUOTE",
            "price_per_share":"100.00", "horizon_years":2,
            "security_basis_confirmed_by_caller":True,
            "currency_basis_confirmed_by_caller":True,
            "scenarios":assumptions,
        }
        inputs.update(changes)
        return evaluate_valuation_scenarios(**inputs)

    def test_scenarios_in_report_as_price_only_not_expected_return(self):
        result = self.valuation_packet()
        before = dict(result)
        report = render_report(self.packet(valuation_scenarios_private=result))
        self.assertIn("BEAR: -10.00% annualized", report)
        self.assertIn("BASE: 10.00% annualized", report)
        self.assertIn("BULL: 20.00% annualized", report)
        self.assertIn("price-only CAGR", report)
        self.assertIn("not probability-weighted Expected Return", report)
        self.assertIn("not forecast alpha versus VFV", report)
        self.assertEqual(result, before)
        self.assertNotIn("SYN-TERMINAL", report)

    def test_explicit_zero_distributions_show_irrs_not_price_only(self):
        from ai_native.valuation_scenarios import evaluate_valuation_scenarios
        scenarios = {}
        for name, terminal in (("BEAR", "81"), ("BASE", "121"), ("BULL", "144")):
            scenarios[name] = {
                "valuation_method":"OTHER_EXPLICIT",
                "assumption_basis":"PAM_ASSUMPTION", "rationale_ref":"SYN-RATIONALE",
                "terminal_price_per_share":terminal, "terminal_value_ref":"SYN-TERMINAL",
                "annual_distributions_per_share":[
                    {"amount_per_share":"0.00", "source_ref":"SYN-DIST"} for _ in range(2)],
            }
        item = self.valuation_packet(scenarios=scenarios)
        self.assertEqual(item["scenarios_private"]["BASE"]["return_measure"],
                         "YEAR_END_CASHFLOW_IRR_CONDITIONAL")
        report = render_report(self.packet(valuation_scenarios_private=item))
        self.assertIn("cash-flow IRR", report)
        self.assertNotIn("price-only CAGR", report)

    def test_unconfirmed_security_basis_never_shows_numbers(self):
        item = self.valuation_packet(security_basis_confirmed_by_caller=False)
        report = render_report(self.packet(valuation_scenarios_private=item))
        self.assertIn("BEAR: UNAVAILABLE", report)
        self.assertIn("BASE: UNAVAILABLE", report)
        self.assertNotIn("10.00% annualized", report)

    def test_valuation_report_rejects_forged_authority_and_dates(self):
        for key, value in (
            ("analysis_id", "WRONG"),
            ("analysis_as_of", "2026-10-27"),
            ("source_authentication", "AUTHENTICATED"),
            ("trade_or_portfolio_authority", "EXECUTE"),
            ("expected_return_status", "CERTIFIED"),
            ("benchmark_expected_return_status", "CERTIFIED"),
            ("quoted_at", "2026-10-29"),
        ):
            with self.subTest(key=key):
                item = self.valuation_packet()
                item[key] = value
                with self.assertRaisesRegex(ValueError, "VALUATION_REPORT"):
                    render_report(self.packet(valuation_scenarios_private=item))

    def test_valuation_report_rejects_tampered_scenario_values_and_set(self):
        for key, value in (
            ("scenario_return_pct_annual", "NaN"),
            ("scenario_return_pct_annual", "Infinity"),
            ("scenario_return_pct_annual", "200000000000000000"),
            ("return_measure", "CERTIFIED_EXPECTED_RETURN"),
            ("assumption_validation", "INDEPENDENTLY_CERTIFIED"),
            ("reason_codes", ["\n# FAKE APPROVAL"]),
        ):
            with self.subTest(key=key):
                item = self.valuation_packet()
                item["scenarios_private"]["BASE"][key] = value
                with self.assertRaisesRegex(ValueError, "VALUATION_REPORT"):
                    render_report(self.packet(valuation_scenarios_private=item))
        item = self.valuation_packet()
        del item["scenarios_private"]["BEAR"]
        with self.assertRaisesRegex(ValueError, "VALUATION_REPORT_SCENARIO_SET_INVALID"):
            render_report(self.packet(valuation_scenarios_private=item))

    def test_valuation_report_rejects_inconsistent_distribution_labels(self):
        item = self.valuation_packet()
        item["scenarios_private"]["BASE"]["annual_distributions_status"] = "EXPLICITLY_SUPPLIED"
        with self.assertRaisesRegex(ValueError, "VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH"):
            render_report(self.packet(valuation_scenarios_private=item))
        item = self.valuation_packet()
        item["scenarios_private"]["BASE"]["reason_codes"] = []
        with self.assertRaisesRegex(ValueError, "VALUATION_REPORT_DISTRIBUTION_BASIS_MISMATCH"):
            render_report(self.packet(valuation_scenarios_private=item))

    def test_valuation_without_scenarios_does_not_claim_forecast(self):
        report = render_report(self.packet())
        self.assertNotIn("Valuation scenarios — conditional", report)

if __name__ == "__main__":
    unittest.main()
