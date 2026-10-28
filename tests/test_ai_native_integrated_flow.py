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

if __name__ == "__main__":
    unittest.main()
