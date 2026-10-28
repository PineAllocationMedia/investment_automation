import unittest

from ai_native.integrated_flow import assemble_manual_run


class ManualIntegrationTests(unittest.TestCase):
    def request(self, **overrides):
        d = {"analysis_id": "SYN-001", "as_of": "2026-10-28", "objective": "Synthetic comparison",
             "strategy_id": "high-cagr", "method_version": "CANDIDATE_R1", "kind": "DECISION"}
        d.update(overrides)
        return d

    def ir(self, **overrides):
        d = {"analysis_id": "SYN-001", "research_as_of": "2026-10-27",
             "summary": ["Synthetic comparison remains uncertain."],
             "facts": [{"id": "SYN-F1", "claim": "Synthetic growth observation", "status": "INDICATIVE"}],
             "limitations": "No decision-grade valuation.", "countercase": "Competitive risks unknown.",
             "decision_line": "No executable conclusion.", "next_action": "Verify original filings."}
        d.update(overrides)
        return d

    def pi(self, **overrides):
        d = {"analysis_id": "SYN-001", "portfolio_as_of": "2026-10-28",
             "room_status": "ROOM_CONDITIONAL", "summary": "Incomplete synthetic scope.",
             "limitations": "Unverified account completeness.", "forwarded_ir": self.ir()}
        d.update(overrides)
        return d

    def check_fact(self, **changes):
        d = {"id": "CF1", "economic_issuer": "SYN", "metric": "OPERATING_INCOME", "value": "25",
             "currency": "USD", "unit": "MILLIONS", "accounting_basis": "US_GAAP",
             "consolidation": "CONSOLIDATED", "period_start": "2025-01-01",
             "period_end": "2025-12-31", "observed_at": "2026-01-15",
             "source_url": "https://example.com/a", "rights_status": "PERMITTED",
             "verification_status": "INDICATIVE"}
        d.update(changes)
        return d

    def test_research_to_report_preserves_uncertainty(self):
        out = assemble_manual_run(self.request(), self.ir())
        self.assertIn("[SYN-F1 / INDICATIVE]", out["markdown"])
        self.assertEqual(out["portfolio_room_status"], "NOT_EVALUATED")
        self.assertEqual(out["memory_proposal_nonprivate"]["archive_status"], "PROPOSED_NOT_COMMITTED")
        self.assertEqual(out["handoff"], "MANUAL_TRANSFER_NOT_PROJECT_AUTOMATION")

    def test_ir_analysis_id_mismatch_blocks(self):
        with self.assertRaisesRegex(ValueError, "IR analysis_id mismatch"):
            assemble_manual_run(self.request(), self.ir(analysis_id="DIFFERENT"))

    def test_future_ir_cannot_be_merged_at_older_cutoff(self):
        with self.assertRaisesRegex(ValueError, "IR research is newer"):
            assemble_manual_run(self.request(), self.ir(research_as_of="2026-11-01"))

    def test_pi_requires_same_identity_and_not_future(self):
        with self.assertRaisesRegex(ValueError, "PI analysis_id mismatch"):
            assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(analysis_id="BAD"))
        with self.assertRaisesRegex(ValueError, "Portfolio observation is newer"):
            assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(portfolio_as_of="2026-10-29"))

    def test_missing_method_is_not_claimed_loaded(self):
        out = assemble_manual_run(self.request(method_version="UNKNOWN_NOT_LOADED"), self.ir())
        self.assertIn("method was not loaded", out["markdown"])
        self.assertIn("CONDITIONAL", out["markdown"])

    def test_calculation_calls_m5_without_certifying_sources(self):
        reqs = [{"operation": "OPERATING_MARGIN", "left": self.check_fact(),
                 "right": self.check_fact(id="CF2", metric="REVENUE", value="100")}]
        out = assemble_manual_run(self.request(), self.ir(), calculation_requests=reqs)
        self.assertEqual(out["calculation_checks"][0]["value"], "25.00")
        self.assertEqual(out["calculation_checks"][0]["source_verification"], "NOT_PERFORMED")

    def test_incompatible_financial_data_becomes_conditional(self):
        reqs = [{"operation": "OPERATING_MARGIN", "left": self.check_fact(),
                 "right": self.check_fact(id="CF2", metric="REVENUE", currency="CAD")}]
        out = assemble_manual_run(self.request(), self.ir(), calculation_requests=reqs)
        self.assertEqual(out["calculation_checks"][0]["status"], "UNAVAILABLE")
        self.assertIn("CONDITIONAL", out["markdown"])

    def test_forwarded_ir_must_be_unchanged(self):
        with self.assertRaisesRegex(ValueError, "PACKET_INCOMPLETE"):
            assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(forwarded_ir={"altered": True}))

    def test_private_contribution_requires_pi(self):
        with self.assertRaisesRegex(ValueError, "without a PI"):
            assemble_manual_run(self.request(), self.ir(), contribution_inputs={})

    def test_m3_contribution_gross_only(self):
        ci = {"positions_base": {"ABC:TSX": "400.00", "VFV:TSX": "600.00"},
              "allocations_pct": {"ABC:TSX": "60", "VFV:TSX": "40"},
              "contribution_base": "1000.00", "currency": "CAD", "as_of": "2026-10-28",
              "scope_complete": True, "cash_accounted_for": True,
              "same_currency_basis_verified": True, "instrument_identity_verified": True}
        out = assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(), contribution_inputs=ci)
        self.assertEqual(out["gross_contribution_private"]["projected_total"], "2000.00")
        self.assertIn("gross", out["markdown"].lower())
        self.assertNotIn("400.00", str(out["memory_proposal_nonprivate"]))

    def test_pi_date_must_match_contribution_basis(self):
        with self.assertRaisesRegex(ValueError, "exact PI"):
            assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(),
                                contribution_inputs={"as_of": "2026-10-27"})

    def test_followup_without_prior_does_not_invent_baseline(self):
        out = assemble_manual_run(self.request(kind="FOLLOWUP"), self.ir(changes=[]))
        self.assertIn("BASELINE_NOT_AVAILABLE", out["markdown"])
        self.assertIn("no fixed reporting window", out["markdown"])

    def test_conflicted_facts_keep_conditional_status(self):
        ir = self.ir(facts=[{"id": "SYN-F1", "claim": "Inconsistent value", "status": "CONFLICTED"}])
        self.assertIn("CONDITIONAL", assemble_manual_run(self.request(), ir)["markdown"])

    def test_invalid_evidence_id_is_rejected_by_m4(self):
        ir = self.ir(facts=[{"id": "SYN-F1", "claim": "A", "status": "INDICATIVE"},
                            {"id": "SYN-F1", "claim": "B", "status": "MISSING"}])
        with self.assertRaisesRegex(ValueError, "duplicate evidence ID"):
            assemble_manual_run(self.request(), ir)


    def test_funded_contribution_is_private_and_conditional(self):
        ci = {"positions_base": {"ABC:TSX": "400.00", "VFV:TSX": "600.00"},
              "allocations_pct": {"ABC:TSX": "60", "VFV:TSX": "40"},
              "contribution_base": "1000.00", "currency": "CAD", "as_of": "2026-10-28",
              "scope_complete": True, "cash_accounted_for": True,
              "same_currency_basis_verified": True, "instrument_identity_verified": True}
        types = ("commission", "bid_ask_spread", "fx_conversion", "purchase_tax", "other_fees")
        costs = {dest: {kind: {"amount_base": "0.00", "source_ref": "SYN-ZERO"}
                        for kind in types} for dest in ci["allocations_pct"]}
        costs["ABC:TSX"]["commission"] = {"amount_base": "5.00", "source_ref": "SYN-FEE"}
        out = assemble_manual_run(
            self.request(), self.ir(), pi_delta=self.pi(), contribution_inputs=ci,
            cost_inputs=dict(charges_by_destination=costs, cost_currency="CAD",
                             cost_quote_as_of="2026-10-28",
                             analysis_as_of="2026-10-28", funding="FROM_CONTRIBUTION"))
        self.assertEqual(out["funded_contribution_private"]["conditional_purchase_budget_base"], "995.00")
        self.assertEqual(out["funded_contribution_private"]["conditional_projection_private"]["allocations_base"],
                         {"ABC:TSX": "597.00", "VFV:TSX": "398.00"})
        self.assertEqual(out["funded_contribution_private"]["execution_status"],
                         "UNAVAILABLE_NOT_EXECUTION_CERTIFIED")
        self.assertNotIn("597.00", str(out["memory_proposal_nonprivate"]))
        self.assertNotIn("597.00", out["markdown"])
        self.assertIn("CONDITIONAL", out["markdown"])

    def test_unknown_funding_stays_unavailable(self):
        ci = {"positions_base": {"A": "50.00"}, "allocations_pct": {"A": "100"},
              "contribution_base": "10.00", "currency": "CAD", "as_of": "2026-10-28",
              "scope_complete": True, "cash_accounted_for": True,
              "same_currency_basis_verified": True, "instrument_identity_verified": True}
        kinds = ("commission", "bid_ask_spread", "fx_conversion", "purchase_tax", "other_fees")
        costs = {"A": {k: {"amount_base": "0.00", "source_ref": "SYN-ZERO"} for k in kinds}}
        out = assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(),
                                  contribution_inputs=ci,
                                  cost_inputs=dict(charges_by_destination=costs,
                                                   cost_currency="CAD",
                                                   cost_quote_as_of="2026-10-28",
                                                   analysis_as_of="2026-10-28", funding="UNKNOWN"))
        self.assertEqual(out["funded_contribution_private"]["status"], "UNAVAILABLE_FUNDING_UNKNOWN")
        self.assertNotIn("conditional_projection_private", out["funded_contribution_private"])

    def test_user_requested_prior_research_comparison_is_private_only(self):
        prior = {
            "schema_version":"RESEARCH_HISTORY_R1", "analysis_id":"SYN-OLD",
            "as_of":"2026-10-01", "recorded_at":"2026-10-02",
            "method_version":"CANDIDATE_R1", "strategy_id":"high-cagr",
            "original_request":{"analysis_id":"SYN-OLD", "as_of":"2026-10-01",
                                "subject_id":"SYN-ISSUER", "method_version":"CANDIDATE_R1",
                                "strategy_id":"high-cagr"},
            "original_ir_capsule":{"analysis_id":"SYN-OLD", "research_as_of":"2026-09-30",
                                   "facts":[{"id":"OLD-F1","claim":"SENSITIVE PRIOR CLAIM",
                                             "status":"INDICATIVE"}]},
        }
        request = self.request(kind="FOLLOWUP", subject_id="SYN-ISSUER",
                               prior_analysis_id="SYN-OLD")
        result = assemble_manual_run(
            request, self.ir(),
            historical_comparison_inputs={"prior_case":prior, "subject_id":"SYN-ISSUER",
                                          "fact_links":[{"prior_fact_id":"OLD-F1",
                                                         "current_fact_id":"SYN-F1"}]})
        annex = result["historical_research_comparison_private"]
        self.assertEqual(annex["status"], "STRUCTURAL_REVIEW_PREPARED")
        self.assertEqual(annex["economic_change_status"], "NOT_EVALUATED")
        self.assertIn("SENSITIVE PRIOR CLAIM", str(annex))
        self.assertNotIn("SENSITIVE PRIOR CLAIM", result["markdown"])
        self.assertNotIn("SENSITIVE PRIOR CLAIM", str(result["memory_proposal_nonprivate"]))
        self.assertIn("CONDITIONAL", result["markdown"])

    def test_historical_comparison_requires_explicit_followup(self):
        with self.assertRaisesRegex(ValueError, "HISTORICAL_COMPARISON_REQUIRES_FOLLOWUP"):
            assemble_manual_run(self.request(), self.ir(),
                                historical_comparison_inputs={"prior_case":None,
                                                              "subject_id":"ISSUER",
                                                              "fact_links":[]})


    def test_m5_alignment_flags_unsupported_ir_verified_label_privately(self):
        verified = {"id":"SYN-F1", "claim":"SYN PRIVATE FACT", "status":"VERIFIED",
                    "source_url":"https://example.org/synthetic-report",
                    "period":"2025", "checked_by":"SYN_RESEARCHER", "checked_at":"2026-10-28"}
        out = assemble_manual_run(
            self.request(), self.ir(facts=[verified]),
            source_evidence_inputs={"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                                    "observations":[]})
        audit = out["fact_source_alignment_private"]
        self.assertEqual(audit["facts_needing_review"], 1)
        self.assertEqual(audit["evidence_upgrade"], "NONE")
        self.assertIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX",
                      audit["facts_private"][0]["review_flags"])
        self.assertIn("CONDITIONAL", out["markdown"])
        self.assertIn("do not structurally align", out["markdown"])
        self.assertNotIn("SYN PRIVATE FACT", str(audit))
        self.assertNotIn("SYN PRIVATE FACT", str(out["memory_proposal_nonprivate"]))

    def test_m5_alignment_preserves_indicative_with_clean_caller_source(self):
        observation = dict(
            observation_id="O1", fact_id="SYN-F1", source_id="S1",
            economic_issuer="SYN", instrument="SYN:NYSE", metric="EPS",
            period_start="2025-01-01", period_end="2025-12-31",
            currency="USD", unit="PER_SHARE", definition_basis="US_GAAP",
            consolidation="GROUP", value="1.00", observed_at="2026-10-28",
            published_at="2026-02-01", original_checked_at="2026-10-28",
            source_kind="ISSUER_OR_REGULATOR", classification="SOURCE_FACT",
            source_locator="https://example.org/synthetic-source",
            rights_status="PERMITTED", verification_status="INDICATIVE")
        out = assemble_manual_run(
            self.request(), self.ir(),
            source_evidence_inputs={"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                                    "observations":[observation]})
        audit = out["fact_source_alignment_private"]
        self.assertEqual(audit["facts_needing_review"], 0)
        self.assertEqual(audit["decision_grade_status"], "NOT_ESTABLISHED")
        self.assertEqual(audit["facts_private"][0]["ir_reported_status"], "INDICATIVE")
        self.assertNotIn("https://example.org/synthetic-source", str(audit))
        self.assertNotIn("https://example.org/synthetic-source",
                         str(out["memory_proposal_nonprivate"]))

    def test_m5_alignment_flags_uncertain_rights_without_source_promotion(self):
        observation = dict(
            observation_id="O1", fact_id="SYN-F1", source_id="S1",
            economic_issuer="SYN", instrument="SYN:NYSE", metric="EPS",
            period_start="2025-01-01", period_end="2025-12-31",
            currency="USD", unit="PER_SHARE", definition_basis="US_GAAP",
            consolidation="GROUP", value="1.00", observed_at="2026-10-28",
            published_at="2026-02-01", original_checked_at="2026-10-28",
            source_kind="ISSUER_OR_REGULATOR", classification="SOURCE_FACT",
            source_locator="https://example.org/synthetic-source",
            rights_status="UNCERTAIN", verification_status="VERIFIED")
        verified = {"id":"SYN-F1","claim":"SYN PRIVATE FACT","status":"VERIFIED",
                    "source_url":"https://example.org/synthetic-source",
                    "period":"2025","checked_by":"SYN_RESEARCHER","checked_at":"2026-10-28"}
        out = assemble_manual_run(
            self.request(), self.ir(facts=[verified]),
            source_evidence_inputs={"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                                    "observations":[observation]})
        flags = out["fact_source_alignment_private"]["facts_private"][0]["review_flags"]
        self.assertIn("SOURCE_INCOMPLETE", flags)
        self.assertIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX", flags)
        self.assertIn("CONDITIONAL", out["markdown"])



    def synthetic_opportunity_inputs(self):
        row = {"observation_id":"SYN-O1", "fact_id":"SYN-F1", "source_id":"SYN-SEC",
               "economic_issuer":"SYN-CO", "instrument":"SYN:NYSE",
               "metric":"REVENUE", "period_start":"2025-01-01", "period_end":"2025-12-31",
               "currency":"USD", "unit":"MILLIONS", "definition_basis":"US_GAAP",
               "consolidation":"GROUP", "value":"100.00", "observed_at":"2026-10-28",
               "published_at":"2026-02-01", "original_checked_at":"2026-10-28",
               "source_kind":"ISSUER_OR_REGULATOR", "classification":"SOURCE_FACT",
               "source_locator":"https://example.org/syn-source", "rights_status":"PERMITTED",
               "verification_status":"INDICATIVE"}
        evidence = {"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                    "observations":[row]}
        research = {"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                    "strategy_id":"high-cagr", "universe_scope":"WATCHLIST",
                    "universe_note":"Synthetic supplied subset",
                    "candidates":[{"candidate_id":"C1", "economic_issuer":"SYN-CO",
                                   "instrument":"SYN:NYSE", "target_type":"ISSUER",
                                   "origin_scope":"WATCHLIST",
                                   "research_question":"Research customer economics",
                                   "ir_fact_ids":["SYN-F1"],
                                   "open_questions":["Primary durability evidence?"],
                                   "known_risks":["Concentration"]}]}
        return evidence, research

    def test_m2_opportunity_triage_is_private_nonranking(self):
        evidence, research = self.synthetic_opportunity_inputs()
        out = assemble_manual_run(self.request(), self.ir(),
                                  source_evidence_inputs=evidence,
                                  opportunity_triage_inputs=research)
        triage = out["opportunity_triage_private"]
        self.assertEqual(triage["status"], "PRIVATE_RESEARCH_TRIAGE_PREPARED_NOT_RANKED")
        self.assertEqual(triage["stage_counts"], {"EVIDENCE_RESOLUTION":0, "HUMAN_DEEP_DIVE":1})
        self.assertEqual(triage["ranking_or_buy_recommendation"], "NONE")
        self.assertIn("Research candidate triage", out["markdown"])
        self.assertIn("1 queued for human deep dive", out["markdown"])
        self.assertIn("**C1**", out["markdown"])
        self.assertNotIn("C1", str(out["memory_proposal_nonprivate"]))
        self.assertIn("CONDITIONAL", out["markdown"])
        self.assertIn("private analyst follow-up queues", out["markdown"])
        self.assertNotIn("SYN-CO", out["markdown"])
        self.assertNotIn("SYN-CO", str(out["memory_proposal_nonprivate"]))

    def test_m2_opportunity_triage_cannot_invent_source_annex(self):
        _, research = self.synthetic_opportunity_inputs()
        with self.assertRaisesRegex(ValueError, "OPPORTUNITY_TRIAGE_REQUIRES_SOURCE_ANNEX"):
            assemble_manual_run(self.request(), self.ir(),
                                opportunity_triage_inputs=research)

    def test_m2_opportunity_triage_preserves_source_gap_without_ranking(self):
        evidence, research = self.synthetic_opportunity_inputs()
        evidence["observations"] = []
        out = assemble_manual_run(self.request(), self.ir(),
                                  source_evidence_inputs=evidence,
                                  opportunity_triage_inputs=research)
        triage = out["opportunity_triage_private"]
        self.assertEqual(triage["stage_counts"]["EVIDENCE_RESOLUTION"], 1)
        self.assertIn("NO_SOURCE_OBSERVATION", triage["candidates_private_in_supplied_order"][0]["review_reasons"])
        self.assertIn("NO_SOURCE_OBSERVATION", out["markdown"])
        self.assertIn("evidence resolution", out["markdown"])
        self.assertEqual(triage["source_authentication"], "NOT_PERFORMED")



    def embedded_source_inputs(self, **row_changes):
        row = dict(
            observation_id="SYN-O1", fact_id="SYN-F1", source_id="SYN-S1",
            economic_issuer="SYN", instrument="SYN:NYSE", metric="EPS",
            period_start="2025-01-01", period_end="2025-12-31",
            currency="USD", unit="PER_SHARE", definition_basis="US_GAAP",
            consolidation="GROUP", value="1.00", observed_at="2026-10-28",
            published_at="2026-02-01", original_checked_at="2026-10-28",
            source_kind="ISSUER_OR_REGULATOR", classification="SOURCE_FACT",
            source_locator="https://example.org/private-synthetic-source",
            rights_status="PERMITTED", verification_status="INDICATIVE",
        )
        row.update(row_changes)
        return {"analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
                "observations":[row]}

    def test_embedded_ir_evidence_flows_to_private_alignment_without_reentry(self):
        import copy
        evidence = self.embedded_source_inputs()
        capsule = self.ir(research_as_of="2026-10-28", EVIDENCE_ANNEX=evidence)
        before = copy.deepcopy(capsule)
        out = assemble_manual_run(self.request(), capsule)
        self.assertEqual(capsule, before)
        self.assertEqual(out["source_evidence_annex_private"]["observation_count"], 1)
        self.assertEqual(out["fact_source_alignment_private"]["facts_needing_review"], 0)
        self.assertEqual(out["source_verification"], "NOT_PERFORMED_BY_INTEGRATION")
        self.assertIn("not independently certified", out["markdown"])
        self.assertNotIn("private-synthetic-source", str(out["memory_proposal_nonprivate"]))

    def test_embedded_and_explicit_source_annexes_are_not_silently_combined(self):
        evidence = self.embedded_source_inputs()
        capsule = self.ir(research_as_of="2026-10-28", EVIDENCE_ANNEX=evidence)
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_SOURCE_ANNEX"):
            assemble_manual_run(self.request(), capsule,
                                source_evidence_inputs=evidence)

    def test_embedded_source_packet_must_match_request_identity_and_date(self):
        for key, other in (("analysis_id", "WRONG"), ("analysis_as_of", "2026-10-27")):
            evidence = self.embedded_source_inputs()
            evidence[key] = other
            with self.subTest(key=key), self.assertRaisesRegex(
                ValueError, "SOURCE_ANNEX_ANALYSIS_OR_DATE_MISMATCH"
            ):
                assemble_manual_run(self.request(), self.ir(EVIDENCE_ANNEX=evidence))

    def test_ir_cannot_claim_an_observation_made_after_research_cutoff(self):
        with self.assertRaisesRegex(ValueError, "IR_SOURCE_OBSERVED_AFTER_RESEARCH_AS_OF"):
            assemble_manual_run(self.request(), self.ir(EVIDENCE_ANNEX=self.embedded_source_inputs()))

    def test_embedded_source_cannot_reference_unknown_ir_fact(self):
        evidence = self.embedded_source_inputs(fact_id="NOT_AN_IR_FACT")
        with self.assertRaisesRegex(ValueError, "SOURCE_ANNEX_UNKNOWN_IR_FACT_ID"):
            assemble_manual_run(self.request(),
                                self.ir(research_as_of="2026-10-28", EVIDENCE_ANNEX=evidence))

    def test_embedded_source_requires_mapping(self):
        with self.assertRaisesRegex(ValueError, "IR_EVIDENCE_ANNEX_MAPPING_REQUIRED"):
            assemble_manual_run(self.request(), self.ir(EVIDENCE_ANNEX=[]))


    def test_source_review_flags_surface_in_final_report_without_label_upgrade(self):
        obs = self.embedded_source_inputs(rights_status="UNCERTAIN",
                                          verification_status="VERIFIED")
        reported_verified = {
            "id":"SYN-F1", "claim":"Synthetic reported EPS", "status":"VERIFIED",
            "source_url":"https://example.org/private-synthetic-source",
            "period":"FY2025", "checked_by":"Synthetic analyst",
            "checked_at":"2026-10-28",
        }
        capsule = self.ir(research_as_of="2026-10-28",
                          facts=[reported_verified], EVIDENCE_ANNEX=obs)
        out = assemble_manual_run(self.request(), capsule)
        text = out["markdown"]
        self.assertIn("Source reconciliation:", text)
        self.assertIn("1/1 facts require human source-use review", text)
        self.assertIn("SOURCE_INCOMPLETE", text)
        self.assertIn("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX", text)
        self.assertIn("[SYN-F1 / VERIFIED]", text)
        self.assertIn("Status:** CONDITIONAL", text)
        self.assertEqual(capsule["facts"][0]["status"], "VERIFIED")
        self.assertNotIn("private-synthetic-source", str(out["memory_proposal_nonprivate"]))

    def test_source_review_clean_structural_alignment_still_not_authentication(self):
        out = assemble_manual_run(
            self.request(),
            self.ir(research_as_of="2026-10-28",
                    EVIDENCE_ANNEX=self.embedded_source_inputs()))
        self.assertIn("0/1 facts", out["markdown"])
        self.assertIn("not independently authenticated", out["markdown"])
        self.assertEqual(out["source_verification"], "NOT_PERFORMED_BY_INTEGRATION")


    def test_report_shows_new_contribution_percentages_without_private_balances(self):
        ci = {"positions_base": {"ABC:TSX": "400.00", "VFV:TSX": "600.00"},
              "allocations_pct": {"ABC:TSX": "60", "VFV:TSX": "40"},
              "contribution_base": "1000.00", "currency": "CAD", "as_of": "2026-10-28",
              "scope_complete": True, "cash_accounted_for": True,
              "same_currency_basis_verified": True, "instrument_identity_verified": True}
        out = assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(), contribution_inputs=ci)
        self.assertIn("60% of new capital", out["markdown"])
        self.assertIn("40% of new capital", out["markdown"])
        self.assertIn("Costs/funding NOT ASSESSED", out["markdown"])
        self.assertNotIn("400.00", out["markdown"])
        self.assertNotIn("600.00", out["markdown"])
        self.assertNotIn("1000.00", out["markdown"])
        self.assertNotIn("ABC:TSX", str(out["memory_proposal_nonprivate"]))

    def test_unavailable_gross_contribution_shows_no_made_up_weights(self):
        ci = {"positions_base": {"ABC:TSX": "400.00"},
              "allocations_pct": {"ABC:TSX": "100"},
              "contribution_base": "1000.00", "currency": "CAD", "as_of": "2026-10-28",
              "scope_complete": False, "cash_accounted_for": True,
              "same_currency_basis_verified": True, "instrument_identity_verified": True}
        out = assemble_manual_run(self.request(), self.ir(), pi_delta=self.pi(), contribution_inputs=ci)
        self.assertIn("Gross contribution projection UNAVAILABLE", out["markdown"])
        self.assertNotIn("100% of new capital", out["markdown"])


    def valuation_inputs(self, **patch):
        rows = {}
        for name, terminal in (("BEAR", "81"), ("BASE", "121"), ("BULL", "144")):
            rows[name] = {
                "valuation_method":"OTHER_EXPLICIT", "assumption_basis":"PAM_ASSUMPTION",
                "rationale_ref":"SYN-R", "terminal_price_per_share":terminal,
                "terminal_value_ref":"SYN-TERMINAL",
                "annual_distributions_per_share":None,
            }
        obj = {
            "analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
            "security_id":"SYN:TSX", "currency":"CAD",
            "quoted_at":"2026-10-28", "quote_source_ref":"SYN-QUOTE",
            "price_per_share":"100.00", "horizon_years":2,
            "security_basis_confirmed_by_caller":True,
            "currency_basis_confirmed_by_caller":True,
            "scenarios":rows,
        }
        obj.update(patch)
        return obj

    def test_m2_valuation_scenario_measures_reach_m4_report_with_limits(self):
        out = assemble_manual_run(self.request(), self.ir(),
                                  valuation_inputs=self.valuation_inputs())
        text = out["markdown"]
        self.assertIn("BEAR: -10.00% annualized", text)
        self.assertIn("BASE: 10.00% annualized", text)
        self.assertIn("BULL: 20.00% annualized", text)
        self.assertIn("price-only CAGR", text)
        self.assertIn("not probability-weighted Expected Return", text)
        self.assertIn("Status:** CONDITIONAL", text)
        self.assertEqual(out["valuation_scenarios_private"]["source_authentication"],
                         "NOT_PERFORMED")
        self.assertNotIn("SYN-TERMINAL", str(out["memory_proposal_nonprivate"]))

    def test_m2_valuation_incompatible_basis_is_unavailable_not_er(self):
        out = assemble_manual_run(
            self.request(), self.ir(),
            valuation_inputs=self.valuation_inputs(currency_basis_confirmed_by_caller=False))
        self.assertIn("BASE: UNAVAILABLE", out["markdown"])
        self.assertNotIn("BASE: 10.00% annualized", out["markdown"])

    def test_m2_valuation_wrong_analysis_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "VALUATION_ANALYSIS_OR_DATE_MISMATCH"):
            assemble_manual_run(self.request(), self.ir(),
                                valuation_inputs=self.valuation_inputs(analysis_id="OTHER"))


    def test_m2_fundamental_dossier_is_shown_in_report_not_public_memory(self):
        from unittest.mock import patch
        import copy
        from ai_native.reporting import _fundamental_lines
        source_input = self.embedded_source_inputs()
        capsule = self.ir(EVIDENCE_ANNEX=source_input, research_as_of="2026-10-28")
        # M2 factual extraction itself is covered by the fundamental dossier
        # tests; this test checks the real M7a→M4 report handoff.
        fake = {
            "status":"INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED",
            "analysis_id":"SYN-001", "analysis_as_of":"2026-10-28",
            "metric_pairs_private":{"REVENUE":{"status":"INDICATIVE_COMPARABLE"}},
            "descriptive_metrics_private":{"reported_revenue_change_pct":"20.00"},
            "qualitative_axes_private":{
                k:{"status":"UNKNOWN","ir_fact_ids":[]} for k in
                ("COMPETITIVE_POSITION","REINVESTMENT","PERMANENT_LOSS")},
            "limitations":["CFO_LESS_CAPEX_UNAVAILABLE_OR_NONCOMPARABLE"],
            "organic_growth_status":"UNKNOWN_ACQUISITIONS_AND_MIX_NOT_EVALUATED",
            "normalized_owner_earnings_status":"NOT_ESTABLISHED",
            "quality_or_durability_verdict":"NOT_AUTOMATICALLY_ESTABLISHED",
            "expected_return_or_trade":"NOT_ESTABLISHED",
            "evidence_authority":"CALLER_REPORTED_ONLY_NOT_ORIGINAL_AUTHENTICATED",
            "writes":"NONE",
        }
        original = copy.deepcopy(capsule)
        with patch("ai_native.integrated_flow.prepare_fundamental_dossier",
                   return_value=fake) as called:
            out = assemble_manual_run(
                self.request(), capsule,
                fundamental_inputs={"economic_issuer":"SYN","instrument":"SYN:TSX",
                    "period_pairs":{"REVENUE":["OLD","NEW"]},
                    "annual_periods_comparable_reported":True,
                    "qualitative_axes":{k:{} for k in
                        ("COMPETITIVE_POSITION","REINVESTMENT","PERMANENT_LOSS")}},
            )
        self.assertTrue(called.called)
        self.assertEqual(capsule, original)
        self.assertIn("20.00%", out["markdown"])
        self.assertIn("Fundamental economics — indicative", out["markdown"])
        self.assertEqual(out["fundamental_dossier_private"], fake)
        self.assertNotIn("20.00", str(out["memory_proposal_nonprivate"]))
        self.assertIn("Status:** CONDITIONAL", out["markdown"])


    def comparison_args(self, *, foreign=False):
        import copy
        first = self.valuation_inputs()
        second = copy.deepcopy(first)
        second["security_id"] = "SYN-B:TSX"
        for name, value in (("BEAR","64"), ("BASE","100"), ("BULL","121")):
            second["scenarios"][name]["terminal_price_per_share"] = value
        if foreign:
            second["currency"] = "USD"
        return {"analysis_id":"SYN-001","analysis_as_of":"2026-10-28",
                "strategy_id":"high-cagr","account_currency":"CAD","candidates":[
                    {"candidate_id":"A","role":"SECURITY","research_method_version":"M2",
                     "research_status":"SPECIALIST_REPORTED","portfolio_room_status":"NOT_EVALUATED",
                     "principal_failure_ref":"PRIVATE-LOSS","valuation_inputs":first},
                    {"candidate_id":"B","role":"SECURITY","research_method_version":"M2",
                     "research_status":"SPECIALIST_REPORTED","portfolio_room_status":"NOT_EVALUATED",
                     "principal_failure_ref":"PRIVATE-LOSS","valuation_inputs":second}]}

    def test_m2_candidate_spreads_reach_m4_without_public_memory(self):
        case=assemble_manual_run(self.request(),self.ir(),candidate_comparison_inputs=self.comparison_args())
        self.assertIn("BASE: 10.00 pp",case["markdown"])
        self.assertIn("not ranked",case["markdown"])
        self.assertEqual(case["candidate_comparison_private"]["forward_alpha_or_superiority"],"NOT_ESTABLISHED")
        self.assertNotIn("PRIVATE-LOSS",case["markdown"])
        self.assertNotIn("PRIVATE-LOSS",str(case["memory_proposal_nonprivate"]))
        self.assertIn("Status:** CONDITIONAL",case["markdown"])

    def test_m2_candidate_comparison_requires_same_currency_basis(self):
        case=assemble_manual_run(self.request(),self.ir(),
                                 candidate_comparison_inputs=self.comparison_args(foreign=True))
        self.assertIn("BASE: NOT_COMPARABLE",case["markdown"])
        self.assertNotIn("BASE: 10.00 pp",case["markdown"])

    def test_m2_candidate_wrong_mandate_rejected(self):
        d=self.comparison_args()
        d["strategy_id"]="UNKNOWN_STRATEGY"
        with self.assertRaisesRegex(ValueError,"CANDIDATE_COMPARISON_MANDATE_MISMATCH"):
            assemble_manual_run(self.request(),self.ir(),candidate_comparison_inputs=d)

if __name__ == "__main__":
    unittest.main()
