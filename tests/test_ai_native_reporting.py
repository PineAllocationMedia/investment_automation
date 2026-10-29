import unittest

from ai_native.reporting import render_report
from ai_native.evidence_math import audit_calculation
import copy


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


    def m5_fact(self, **overrides):
        row = {"id": "PRIVATE-LEFT", "economic_issuer": "SYN", "metric": "OPERATING_INCOME",
               "value": "25", "currency": "USD", "unit": "MILLIONS",
               "accounting_basis": "US_GAAP", "consolidation": "CONSOLIDATED",
               "period_start": "2025-01-01", "period_end": "2025-12-31",
               "observed_at": "2026-01-15", "source_url": "https://example.org/private-m5",
               "rights_status": "PERMITTED", "verification_status": "INDICATIVE"}
        row.update(overrides)
        return row

    def m5_check(self, **right_overrides):
        return audit_calculation(
            "OPERATING_MARGIN", self.m5_fact(),
            self.m5_fact(id="PRIVATE-RIGHT", metric="REVENUE", value="100", **right_overrides),
            as_of="2026-10-28")

    def test_private_report_shows_real_formal_m5_arithmetic_not_original_ir_evidence(self):
        check = self.m5_check()
        report = render_report(self.packet(calculation_checks_private=[check]))
        self.assertIn("Descriptive financial calculations — conditional", report)
        self.assertIn("OPERATING_MARGIN: 25.00%", report)
        self.assertIn("formal arithmetic only", report)
        self.assertIn("original-IR point-in-time availability", report)
        self.assertNotIn("PRIVATE-LEFT", report)
        self.assertNotIn("PRIVATE-RIGHT", report)
        self.assertNotIn("private-m5", report)
        self.assertNotIn("independently verified", report.lower())

    def test_unavailable_m5_calculation_reports_reason_without_fake_value(self):
        check = self.m5_check(currency="CAD")
        report = render_report(self.packet(calculation_checks_private=[check]))
        self.assertIn("OPERATING_MARGIN: UNAVAILABLE", report)
        self.assertIn("CURRENCY_MISMATCH", report)
        self.assertNotIn("25.00%", report)

    def test_no_calculation_section_when_not_supplied(self):
        self.assertNotIn("Descriptive financial calculations",
                         render_report(self.packet()))

    def test_uncertain_rights_caveat_remains_visible(self):
        check = self.m5_check(rights_status="UNCERTAIN")
        report = render_report(self.packet(calculation_checks_private=[check]))
        self.assertIn("source rights require review", report)
        self.assertIn("25.00%", report)

    def test_m5_report_rejects_source_or_decision_authority_spoof(self):
        for key, value in (
            ("source_verification", "INDEPENDENTLY_VERIFIED"),
            ("temporal_authority", "ORIGINAL_IR_CERTIFIED"),
            ("decision_grade", True),
            ("metric", "EXPECTED_RETURN"),
            ("status", "INVESTABLE"),
            ("operation", "BUY_NOW"),
            ("value", "NaN"),
            ("unit", "CAD_PERCENT"),
        ):
            row = self.m5_check()
            row[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(
                ValueError, "CALCULATION_REPORT"):
                render_report(self.packet(calculation_checks_private=[row]))

    def test_m5_report_rejects_injected_reason_and_extra_fields(self):
        row = self.m5_check(currency="CAD")
        row["reason_codes"] = ["CURRENCY_MISMATCH\\n# EXECUTE"]
        with self.assertRaisesRegex(ValueError, "CALCULATION_REPORT_REASONS"):
            render_report(self.packet(calculation_checks_private=[row]))
        row = self.m5_check()
        row["investment_instruction"] = "BUY"
        with self.assertRaisesRegex(ValueError, "CALCULATION_REPORT_FORMAL_SCHEMA"):
            render_report(self.packet(calculation_checks_private=[row]))
        row = self.m5_check()
        row["permission_caveat"] = "SOURCE_USE_UNCERTAIN_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValueError, "CALCULATION_REPORT_RIGHTS_CAVEAT"):
            render_report(self.packet(calculation_checks_private=[row]))

    def test_m5_report_summarizes_more_than_eight_without_leaking_source_details(self):
        result = render_report(self.packet(
            calculation_checks_private=[copy.deepcopy(self.m5_check()) for _ in range(9)]))
        self.assertEqual(result.count("OPERATING_MARGIN: 25.00%"), 8)
        self.assertIn("1 additional check(s)", result)

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

    def test_cost_share_is_private_conditional_not_a_return(self):
        summary = self.new_contribution(
            cost_status="SUPPLIED_COST_TALLY_ONLY",
            funded_status="CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED",
            one_time_supplied_cost_share_pct="0.4975")
        report = render_report(self.packet(new_contribution_summary_private=summary))
        self.assertIn("0.4975% of total NEW cash", report)
        self.assertIn("not annualized, net Expected Return", report)
        self.assertNotIn("1005.00", report)

    def test_invalid_or_unfunded_cost_share_does_not_get_displayed(self):
        for share in ("NaN", "100.0000", "-1.0000", "0.12345", "unknown"):
            with self.subTest(share=share), self.assertRaisesRegex(
                    ValueError, "CONTRIBUTION_REPORT_COST_BURDEN"):
                render_report(self.packet(new_contribution_summary_private=
                    self.new_contribution(
                        cost_status="SUPPLIED_COST_TALLY_ONLY",
                        funded_status="CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED",
                        one_time_supplied_cost_share_pct=share)))
        with self.assertRaisesRegex(ValueError, "CONTRIBUTION_REPORT_COST_BURDEN"):
            render_report(self.packet(new_contribution_summary_private=
                self.new_contribution(one_time_supplied_cost_share_pct="0.5000")))

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


    def fundamental_packet(self, **patch):
        dossier = {
            "status":"INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED",
            "analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
            "economic_issuer":"PRIVATE-SYN-ISSUER", "instrument":"PRIVATE:TSX",
            "metric_pairs_private":{
                "REVENUE":{"status":"INDICATIVE_COMPARABLE"},
                "OPERATING_INCOME":{"status":"INDICATIVE_COMPARABLE"},
                "CFO":{"status":"INDICATIVE_COMPARABLE", "currency":"CAD", "unit":"M_CAD",
                       "period_ends":["2024-12-31","2025-12-31"]},
                "CASH_CAPEX":{"status":"INDICATIVE_COMPARABLE", "currency":"CAD", "unit":"M_CAD",
                              "period_ends":["2024-12-31","2025-12-31"]},
                "DILUTED_AVG_SHARES":{"status":"INDICATIVE_COMPARABLE"},
            },
            "descriptive_metrics_private":{
                "reported_revenue_change_pct":"20.00",
                "reported_operating_margin_pct":["10.00","15.00"],
                "cfo_less_cash_capex_descriptive":["15","17"],
                "cfo_less_capex_label":"NOT_NORMALIZED_OWNER_EARNINGS",
                "diluted_share_count_change_pct":"10.00",
            },
            "qualitative_axes_private":{
                k:{"status":"SPECIALIST_REPORTED","ir_fact_ids":["F1"],
                   "rationale":"PRIVATE-IR-NARRATIVE", "countercase":"PRIVATE-COUNTERCASE"}
                for k in ("COMPETITIVE_POSITION","REINVESTMENT","PERMANENT_LOSS")
            },
            "limitations":[],
            "organic_growth_status":"UNKNOWN_ACQUISITIONS_AND_MIX_NOT_EVALUATED",
            "normalized_owner_earnings_status":"NOT_ESTABLISHED",
            "quality_or_durability_verdict":"NOT_AUTOMATICALLY_ESTABLISHED",
            "expected_return_or_trade":"NOT_ESTABLISHED",
            "evidence_authority":"CALLER_REPORTED_ONLY_NOT_ORIGINAL_AUTHENTICATED",
            "writes":"NONE",
        }
        dossier.update(patch)
        return dossier

    def test_fundamental_metrics_reach_report_only_as_indicative(self):
        item = self.fundamental_packet()
        output = render_report(self.packet(fundamental_dossier_private=item))
        self.assertIn("Reported revenue change", output)
        self.assertIn("20.00%", output)
        self.assertIn("10.00% → 15.00%", output)
        self.assertIn("15 → 17 M_CAD (CAD)", output)
        self.assertIn("not normalized owner earnings", output)
        self.assertIn("Diluted average-share count change: 10.00%", output)
        self.assertIn("NOT ESTABLISHED", output)
        for sensitive in ("PRIVATE-SYN-ISSUER","PRIVATE-IR-NARRATIVE","PRIVATE-COUNTERCASE"):
            self.assertNotIn(sensitive, output)

    def test_fundamental_unavailable_cannot_silently_display_derived_growth(self):
        item = self.fundamental_packet()
        item["metric_pairs_private"]["REVENUE"]["status"] = "UNAVAILABLE"
        with self.assertRaisesRegex(ValueError, "FUNDAMENTAL_REPORT_UNSUPPORTED_DERIVATION"):
            render_report(self.packet(fundamental_dossier_private=item))
        del item["descriptive_metrics_private"]["reported_revenue_change_pct"]
        del item["descriptive_metrics_private"]["reported_operating_margin_pct"]
        output = render_report(self.packet(fundamental_dossier_private=item))
        self.assertIn("Reported revenue growth: UNAVAILABLE", output)
        self.assertNotIn("20.00%", output)

    def test_fundamental_invalid_cashflow_basis_is_rejected(self):
        item = self.fundamental_packet()
        item["metric_pairs_private"]["CFO"]["currency"] = "USD"
        with self.assertRaisesRegex(ValueError, "FUNDAMENTAL_REPORT_CASHFLOW_BASIS_MISMATCH"):
            render_report(self.packet(fundamental_dossier_private=item))

    def test_fundamental_nonauthentic_evidence_cannot_be_relabelled_certified(self):
        for k, v in [
            ("evidence_authority", "INDEPENDENTLY_CERTIFIED"),
            ("quality_or_durability_verdict", "PAM_QUALITY_APPROVED"),
            ("normalized_owner_earnings_status", "ESTABLISHED"),
            ("expected_return_or_trade", "BUY"),
            ("analysis_id", "WRONG"),
            ("analysis_as_of", "2026-10-27"),
        ]:
            with self.subTest(k=k), self.assertRaisesRegex(ValueError, "FUNDAMENTAL_REPORT_ID_OR_AUTHORITY_MISMATCH"):
                render_report(self.packet(fundamental_dossier_private=self.fundamental_packet(**{k:v})))

    def test_fundamental_nonfinite_or_markup_injection_is_rejected(self):
        for value in ["NaN", "Infinity", "1E100", "not-a-number"]:
            item = self.fundamental_packet()
            item["descriptive_metrics_private"]["reported_revenue_change_pct"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "FUNDAMENTAL_REPORT_NUMBER_INVALID"):
                render_report(self.packet(fundamental_dossier_private=item))
        item = self.fundamental_packet()
        item["metric_pairs_private"]["CFO"]["unit"] = "USD\n# FALSE REPORT"
        with self.assertRaisesRegex(ValueError, "FUNDAMENTAL_REPORT_CASHFLOW_UNIT_INVALID"):
            render_report(self.packet(fundamental_dossier_private=item))

    def test_fundamental_rationale_stays_private_even_if_unknown(self):
        item = self.fundamental_packet()
        item["qualitative_axes_private"]["COMPETITIVE_POSITION"]["status"] = "UNKNOWN"
        item["qualitative_axes_private"]["COMPETITIVE_POSITION"]["ir_fact_ids"] = []
        output = render_report(self.packet(fundamental_dossier_private=item))
        self.assertIn("Competitive Position: UNKNOWN (no linked IR facts)", output)
        self.assertNotIn("PRIVATE-IR-NARRATIVE", output)

    def test_report_without_fundamental_inputs_does_not_invent_issuer_economics(self):
        output = render_report(self.packet())
        self.assertNotIn("Fundamental economics — indicative", output)


    def room_review(self, **patch):
        record = {
            "status":"ROOM_CONDITIONAL", "analysis_id":"SYN-001",
            "as_of":"2026-10-28", "observed_on":"2026-10-28",
            "research_axes_private":{k:{"status":"SPECIALIST_REPORTED",
                "ir_fact_ids":["F1"],"rationale":"PRIVATE_RATIONALE"}
                for k in ("QUALITY","DURABILITY","EXPECTED_RETURN","CONFIDENCE")},
            "portfolio_checks_private":{k:{"status":"SPECIALIST_REPORTED",
                "source_ref":"SYN-REF","finding":"PRIVATE_FINDING"}
                for k in ("CONCENTRATION","CORRELATED_DRIVERS","ALTERNATIVES","ACCOUNT_COSTS")},
            "known_candidate_issuer_exposure_pct_private":"25.50",
            "unclassified_lookthrough_pct_private":"30.00",
            "missing_or_qualified":["LOOKTHROUGH_PARTIAL"],
            "account_scope_private":"PRIVATE_ACCOUNT", "analyst_view_private":"PRIVATE_VIEW",
            "portfolio_room_authority":"QUALITATIVE_SPECIALIST_REPORTED_ONLY",
            "independent_evidence_check":"NOT_PERFORMED",
            "contribution_or_sale_proposal":"NONE_NOT_AUTOMATED",
            "trade_authority":"NONE_CEO_ONLY", "public_memory_write":"NONE",
        }
        record.update(patch)
        return record

    def test_portfolio_room_report_preserves_qualifications_and_privacy(self):
        report = render_report(self.packet(portfolio_room_review_private=self.room_review()))
        self.assertIn("ROOM_CONDITIONAL", report)
        self.assertIn("25.50% of the scoped portfolio", report)
        self.assertIn("30.00% of scoped portfolio", report)
        self.assertIn("Quality: SPECIALIST_REPORTED", report)
        self.assertIn("Portfolio account costs: SPECIALIST_REPORTED", report)
        self.assertIn("1 unresolved/qualified", report)
        self.assertIn("No target allocation", report)
        for private in ("PRIVATE_RATIONALE","PRIVATE_FINDING","PRIVATE_VIEW","PRIVATE_ACCOUNT"):
            self.assertNotIn(private, report)

    def test_portfolio_room_unknown_exposure_not_silently_zero(self):
        room = self.room_review(
            status="ROOM_UNAVAILABLE",
            known_candidate_issuer_exposure_pct_private=None,
            unclassified_lookthrough_pct_private=None)
        report = render_report(self.packet(portfolio_room_review_private=room))
        self.assertIn("exposure: UNKNOWN", report)
        self.assertIn("look-through: UNKNOWN", report)
        self.assertNotIn("0% of the scoped portfolio", report)

    def test_portfolio_room_rejects_false_authority_and_mismatched_identity(self):
        for key, val in (
            ("analysis_id","SYN-OTHER"), ("as_of","2026-10-27"),
            ("trade_authority","AUTO_TRADE"), ("public_memory_write","APPROVED"),
            ("portfolio_room_authority","INDEPENDENT_CERTIFICATION"),
            ("independent_evidence_check","VERIFIED"),
            ("contribution_or_sale_proposal","BUY"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "ROOM_REPORT_AUTHORITY_OR_ID"):
                render_report(self.packet(portfolio_room_review_private=self.room_review(**{key:val})))

    def test_portfolio_room_rejects_unsupported_statuses_and_future_data(self):
        for key, val, reason in (
            ("status","ROOM_EVIDENCE_SUPPORTED","STATUS_INVALID"),
            ("observed_on","2026-10-29","FUTURE_OBSERVATION"),
            ("known_candidate_issuer_exposure_pct_private","NaN","PERCENT_INVALID"),
            ("unclassified_lookthrough_pct_private","-1","PERCENT_INVALID"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "ROOM_REPORT_"+reason):
                render_report(self.packet(portfolio_room_review_private=self.room_review(**{key:val})))

    def test_portfolio_room_does_not_accept_missing_axes_or_forged_reasons(self):
        room=self.room_review()
        room["research_axes_private"].pop("EXPECTED_RETURN")
        with self.assertRaisesRegex(ValueError, "ROOM_REPORT_RESEARCH_AXES_INVALID"):
            render_report(self.packet(portfolio_room_review_private=room))
        room=self.room_review(missing_or_qualified=["OK\\n# CERTIFIED"])
        with self.assertRaisesRegex(ValueError, "ROOM_REPORT_LIMITATIONS_INVALID"):
            render_report(self.packet(portfolio_room_review_private=room))


    def triage_summary(self, **patch):
        obj = {
            "status":"PRIVATE_RESEARCH_TRIAGE_PREPARED_NOT_RANKED",
            "analysis_id":"SYN-001","analysis_as_of":"2026-10-28",
            "strategy_id":"high-cagr","universe_scope":"WATCHLIST",
            "universe_note_private":"PRIVATE-WATCHLIST",
            "declared_candidate_count":2,
            "stage_counts":{"EVIDENCE_RESOLUTION":1,"HUMAN_DEEP_DIVE":1},
            "candidates_private_in_supplied_order":[
                {"candidate_id_private":"C2",
                 "research_work_stage":"EVIDENCE_RESOLUTION",
                 "review_reasons":["NO_SOURCE_OBSERVATION"],
                 "selection_status":"CEO_OR_ANALYST_REVIEW_ONLY",
                 "investability":"NOT_EVALUATED",
                 "economic_issuer_private":"PRIVATE-ISSUER-2",
                 "research_question_private":"PRIVATE-QUESTION-2"},
                {"candidate_id_private":"C1",
                 "research_work_stage":"HUMAN_DEEP_DIVE",
                 "review_reasons":[],
                 "selection_status":"CEO_OR_ANALYST_REVIEW_ONLY",
                 "investability":"NOT_EVALUATED",
                 "economic_issuer_private":"PRIVATE-ISSUER-1",
                 "research_question_private":"PRIVATE-QUESTION-1"},
            ],
            "universe_completeness":"NOT_VERIFIED_NOT_GLOBAL_SCREENING",
            "source_authentication":"NOT_PERFORMED",
            "normalized_expected_return":"NOT_ESTABLISHED",
            "ranking_or_buy_recommendation":"NONE",
            "portfolio_allocation":"NONE",
            "external_discovery_or_storage":"NONE",
        }
        obj.update(patch)
        return obj

    def test_research_triage_report_shows_work_not_stock_ranking(self):
        output = render_report(self.packet(opportunity_triage_private=self.triage_summary()))
        self.assertIn("Research candidate triage — private, not ranked", output)
        self.assertIn("1 awaiting evidence resolution", output)
        self.assertIn("1 queued for human deep dive", output)
        self.assertLess(output.index("**C2**"), output.index("**C1**"))
        self.assertIn("NO_SOURCE_OBSERVATION", output)
        self.assertIn("No global market screening", output)
        for private in ("PRIVATE-WATCHLIST","PRIVATE-QUESTION-1","PRIVATE-ISSUER-2"):
            self.assertNotIn(private, output)

    def test_research_triage_rejects_forged_authority(self):
        for key,val in (
            ("analysis_id","OTHER"),
            ("analysis_as_of","2026-10-27"),
            ("strategy_id","UNAPPROVED-STRATEGY"),
            ("status","EXECUTION_READY"),
            ("source_authentication","AUTHENTICATED"),
            ("ranking_or_buy_recommendation","BUY"),
            ("portfolio_allocation","APPROVED"),
            ("normalized_expected_return","CERTIFIED"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "TRIAGE_REPORT_ID_OR_AUTHORITY"):
                render_report(self.packet(opportunity_triage_private=self.triage_summary(**{key:val})))

    def test_research_triage_rejects_count_and_stage_tampering(self):
        for patch in (
            {"declared_candidate_count":3},
            {"stage_counts":{"EVIDENCE_RESOLUTION":0,"HUMAN_DEEP_DIVE":2}},
            {"stage_counts":{"EVIDENCE_RESOLUTION":True,"HUMAN_DEEP_DIVE":1}},
        ):
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError, "TRIAGE_REPORT"):
                render_report(self.packet(opportunity_triage_private=self.triage_summary(**patch)))
        import copy
        case = copy.deepcopy(self.triage_summary())
        case["candidates_private_in_supplied_order"][0]["research_work_stage"]="HUMAN_DEEP_DIVE"
        with self.assertRaisesRegex(ValueError, "TRIAGE_REPORT_CANDIDATE_STATUS"):
            render_report(self.packet(opportunity_triage_private=case))

    def test_research_triage_does_not_render_untrusted_candidate_markup(self):
        item = self.triage_summary()
        item["candidates_private_in_supplied_order"][0]["candidate_id_private"] = "C2\\n# FAKE_APPROVAL"
        output = render_report(self.packet(opportunity_triage_private=item))
        self.assertNotIn("FAKE_APPROVAL", output)
        self.assertIn("candidate #1", output)
        item = self.triage_summary()
        item["candidates_private_in_supplied_order"][0]["review_reasons"] = ["\n# FRAUD"]
        with self.assertRaisesRegex(ValueError, "TRIAGE_REPORT_CANDIDATE_STATUS"):
            render_report(self.packet(opportunity_triage_private=item))

    def test_research_triage_no_packet_does_not_invent_a_screen(self):
        output = render_report(self.packet())
        self.assertNotIn("Research candidate triage — private", output)


    def candidate_case(self, currency="CAD"):
        from ai_native.candidate_comparison import compare_candidates
        rows = {}
        def candidate(name, prices, quote="2026-10-28", unit="CAD"):
            scenarios = {}
            for label, price in zip(("BEAR", "BASE", "BULL"), prices):
                scenarios[label] = {"valuation_method":"OTHER_EXPLICIT", "assumption_basis":"PAM_ASSUMPTION",
                    "rationale_ref":"PRIVATE-RATIONALE","terminal_price_per_share":price,
                    "terminal_value_ref":"PRIVATE-TERMINAL", "annual_distributions_per_share":None}
            return {"candidate_id":name,"role":"SECURITY","research_method_version":"M2",
                    "research_status":"SPECIALIST_REPORTED","portfolio_room_status":"NOT_EVALUATED",
                    "principal_failure_ref":"PRIVATE-FAILURE",
                    "valuation_inputs":{"analysis_id":"SYN-001","analysis_as_of":"2026-10-28",
                        "security_id":name+":TSX","currency":unit,"quoted_at":quote,
                        "quote_source_ref":"PRIVATE-QUOTE","price_per_share":"100","horizon_years":2,
                        "security_basis_confirmed_by_caller":True,"currency_basis_confirmed_by_caller":True,
                        "scenarios":scenarios}}
        return compare_candidates(
            analysis_id="SYN-001", analysis_as_of="2026-10-28", strategy_id="high-cagr",
            account_currency="CAD", candidates=[candidate("A",("81","121","144")),
                                                candidate("B",("64","100","121"),unit=currency)])

    def test_candidate_comparison_report_is_arithmetic_not_ranking(self):
        case = self.candidate_case()
        rendered = render_report(self.packet(candidate_comparison_private=case))
        self.assertIn("Cross-candidate scenario arithmetic",rendered)
        self.assertIn("A minus B",rendered)
        self.assertIn("BEAR: 10.00 pp (price-only CAGR)",rendered)
        self.assertIn("BASE: 10.00 pp (price-only CAGR)",rendered)
        self.assertIn("not ranked",rendered)
        self.assertNotIn("PRIVATE-RATIONALE",rendered)
        self.assertNotIn("PRIVATE-QUOTE",rendered)

    def test_candidate_comparison_missing_fx_is_not_comparable(self):
        output=render_report(self.packet(candidate_comparison_private=self.candidate_case(currency="USD")))
        self.assertIn("BASE: NOT_COMPARABLE",output)
        self.assertNotIn("BASE: 10.00 pp",output)

    def test_candidate_comparison_forged_authority_rejected(self):
        for key,value in (("analysis_id","OTHER"),("source_authentication","VERIFIED"),
                          ("forward_alpha_or_superiority","CERTIFIED"),
                          ("recommendation_or_ranking","BUY"),("trading_authority","EXECUTE")):
            item=self.candidate_case()
            item[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"COMPARISON_REPORT_ID_OR_AUTHORITY"):
                render_report(self.packet(candidate_comparison_private=item))

    def test_candidate_comparison_tampered_spreads_and_pairs_rejected(self):
        item=self.candidate_case()
        item["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]["delta_first_minus_second_pp"]="99"
        with self.assertRaisesRegex(ValueError,"COMPARISON_REPORT_SPREAD_MISMATCH"):
            render_report(self.packet(candidate_comparison_private=item))
        item=self.candidate_case()
        item["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]["delta_first_minus_second_pp"]="NaN"
        with self.assertRaisesRegex(ValueError,"COMPARISON_REPORT_NUMBER_INVALID"):
            render_report(self.packet(candidate_comparison_private=item))
        item=self.candidate_case()
        item["pairwise_scenario_differences_private"][0]["first_candidate_id"]="UNKNOWN"
        with self.assertRaisesRegex(ValueError,"COMPARISON_REPORT_PAIR_MISMATCH"):
            render_report(self.packet(candidate_comparison_private=item))

    def test_candidate_comparison_no_input_does_not_fabricate_a_ranking(self):
        output=render_report(self.packet())
        self.assertNotIn("Cross-candidate scenario arithmetic",output)


    def history(self, **changes):
        x = {"status":"STRUCTURAL_REVIEW_PREPARED",
             "subject_id_private":"PRIVATE-ISSUER","prior_analysis_id_private":"OLD",
             "current_analysis_id_private":"SYN-001","prior_as_of":"2026-10-01",
             "current_as_of":"2026-10-28","strategy_changed":False,"method_changed":False,
             "review_items_private":[{"prior_fact_id":"F-OLD","current_fact_id":"F-CUR",
                 "prior_claim_private":"PRIVATE-OLD-CLAIM","current_claim_private":"PRIVATE-NEW-CLAIM",
                 "prior_evidence_status":"INDICATIVE","current_evidence_status":"CONFLICTED",
                 "text_check":"TEXT_DIFF_NOT_CERTIFIED_ECONOMIC_CHANGE"}],
             "comparability":"ANALYST_MUST_VERIFY_IDENTITY_METRIC_UNITS_PERIODS_AND_RIGHTS",
             "baseline_authentication":"CALLER_SUPPLIED_RECORD_STRUCTURALLY_CHECKED_ONLY",
             "source_authentication":"NOT_PERFORMED","economic_change_status":"NOT_EVALUATED",
             "privacy":"PRIVATE_ONLY"}
        x.update(changes)
        return x

    def test_structural_followup_reaches_private_report(self):
        text=render_report(self.packet(kind="FOLLOWUP",changes=[],prior_analysis_id="OLD",
            historical_research_comparison_private=self.history()))
        self.assertIn("INDICATIVE → CONFLICTED",text)
        self.assertIn("economic change UNVERIFIED",text)
        self.assertIn("no certified thesis change",text)
        self.assertNotIn("PRIVATE-OLD-CLAIM",text)
        self.assertNotIn("PRIVATE-ISSUER",text)

    def test_missing_baseline_or_unlinked_facts_remain_unknown(self):
        a=self.history(status="BASELINE_NOT_AVAILABLE",review_items_private=[])
        del a["prior_analysis_id_private"]
        text=render_report(self.packet(kind="FOLLOWUP",changes=[],historical_research_comparison_private=a))
        self.assertIn("BASELINE_NOT_AVAILABLE: no earlier case",text)
        b=self.history(status="NO_FACT_LINKS_SUPPLIED",review_items_private=[],method_changed=True)
        text=render_report(self.packet(kind="FOLLOWUP",changes=[],
            historical_research_comparison_private=b))
        self.assertIn("NO_FACT_LINKS_SUPPLIED",text)
        self.assertIn("method version changed",text)

    def test_followup_rejects_forged_evidence_status_or_nonfollowup(self):
        for field,value in (("source_authentication","CERTIFIED"),("economic_change_status","TRUE_CHANGE"),
                            ("privacy","PUBLIC")):
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"HISTORY_REPORT_AUTHORITY"):
                render_report(self.packet(kind="FOLLOWUP",changes=[],
                    historical_research_comparison_private=self.history(**{field:value})))
        with self.assertRaisesRegex(ValueError,"HISTORY_REPORT_AUTHORITY"):
            render_report(self.packet(historical_research_comparison_private=self.history()))

    def test_followup_rejects_wrong_dates_and_claim_links(self):
        case=self.history(current_as_of="2026-10-27")
        with self.assertRaisesRegex(ValueError,"HISTORY_REPORT_ID_OR_BASIS"):
            render_report(self.packet(kind="FOLLOWUP",changes=[],
                historical_research_comparison_private=case))
        case=self.history()
        case["review_items_private"][0]["text_check"]="CERTIFIED_ECONOMIC_CHANGE"
        with self.assertRaisesRegex(ValueError,"HISTORY_REPORT_LINK_INVALID"):
            render_report(self.packet(kind="FOLLOWUP",changes=[],
                historical_research_comparison_private=case))
        case=self.history()
        case["review_items_private"][0]["prior_fact_id"]="F-OLD\\n# FORGED"
        with self.assertRaisesRegex(ValueError,"HISTORY_REPORT_LINK_INVALID"):
            render_report(self.packet(kind="FOLLOWUP",changes=[],
                historical_research_comparison_private=case))

if __name__ == "__main__":
    unittest.main()
