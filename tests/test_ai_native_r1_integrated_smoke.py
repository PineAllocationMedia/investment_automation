"""One manual CC→IR→PI→CC construction smoke, all data synthetic.

No mock of the session assembler or financial helpers. This is neither an
authentic-source verification nor the eventual 36-decision acceptance exercise.
The fixture contains no actual account identifiers, credentials or holdings.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_construction_contracts import R1ConstructionContracts


class RealManualConstructionSmoke(unittest.TestCase):
    def setUp(self):
        # Reuse existing synthetic M1/M2/M3 fixture generation: do not make
        # an independent calculation model just to make this test pass.
        self.fx = R1ConstructionContracts()

    def case(self):
        request = self.fx.request(True, True)
        ir = self.fx.capsule()
        observation = self.fx.observation()
        exposure = self.fx.classes()
        source = {"analysis_id":"SYN-X", "analysis_as_of":"2026-10-28",
                  "observations":[self.fx.source()]}
        valuation = self.fx.valuation()
        alternate = deepcopy(valuation)
        alternate["security_id"] = "DEF:TSX"
        for stage, price in (("BEAR", "64"), ("BASE", "100"), ("BULL", "121")):
            alternate["scenarios"][stage]["terminal_price_per_share"] = price
        comparison = {
            "analysis_id":"SYN-X", "analysis_as_of":"2026-10-28",
            "strategy_id":"EXPLORATORY", "account_currency":"CAD",
            "candidates":[
                {"candidate_id":"SYN-A", "role":"SECURITY",
                 "research_method_version":"SYNTHETIC_R1",
                 "research_status":"SPECIALIST_REPORTED",
                 "portfolio_room_status":"NOT_EVALUATED",
                 "principal_failure_ref":"SYN-COUNTERCASE-A",
                 "valuation_inputs":valuation},
                {"candidate_id":"SYN-B", "role":"SECURITY",
                 "research_method_version":"SYNTHETIC_R1",
                 "research_status":"SPECIALIST_REPORTED",
                 "portfolio_room_status":"NOT_EVALUATED",
                 "principal_failure_ref":"SYN-COUNTERCASE-B",
                 "valuation_inputs":alternate},
            ],
        }
        triage = {
            "analysis_id":"SYN-X", "analysis_as_of":"2026-10-28",
            "strategy_id":"EXPLORATORY", "universe_scope":"WATCHLIST",
            "universe_note":"Synthetic nominated subset, not discovered market",
            "candidates":[
                {"candidate_id":"C-1", "economic_issuer":"ABC", "instrument":"ABC:TSX",
                 "target_type":"ISSUER", "origin_scope":"WATCHLIST",
                 "research_question":"Verify economics before considering new capital",
                 "ir_fact_ids":["F-1"],
                 "open_questions":["Original-source comparability"],
                 "known_risks":["Unknown business durability"]},
            ],
        }
        room = {
            "review_as_of":"2026-10-28", "strategy_id":"EXPLORATORY",
            "capital_source":"NEW_CONTRIBUTION", "account_scope":"SYN-SCOPE",
            "account_type":"TFSA", "candidate_economic_issuer_id":"ABC",
            "candidate_security_id":"ABC:TSX", "horizon_years":5,
            "research_axes":{axis:{"status":"SPECIALIST_REPORTED",
                "rationale":"Synthetic test observation, not independently verified",
                "ir_fact_ids":["F-1"]} for axis in
                ("QUALITY","DURABILITY","EXPECTED_RETURN","CONFIDENCE")},
            "portfolio_checks":{name:{"status":"SPECIALIST_REPORTED",
                "finding":"Synthetic and conditional", "source_ref":"SYN-PI-INPUT"}
                for name in ("CONCENTRATION","CORRELATED_DRIVERS",
                             "ALTERNATIVES","ACCOUNT_COSTS")},
            "analyst_view":"SYN-PRIVATE-ANALYST-VIEW",
            "strongest_countercase":"Unverified economics",
            "next_verification":"Confirm originals and account costs",
        }
        capital = {
            "positions_base":{"ABC:TSX":"300.00","FUND:TSX":"600.00","P-CASH":"100.00"},
            "allocations_pct":{"ABC:TSX":"60","FUND:TSX":"40"},
            "contribution_base":"1000.00", "currency":"CAD",
            "as_of":"2026-10-28", "scope_complete":True,
            "cash_accounted_for":True, "same_currency_basis_verified":True,
            "instrument_identity_verified":True,
        }
        kinds=("commission","bid_ask_spread","fx_conversion",
               "purchase_tax","other_fees")
        costs={
            key:{name:{"amount_base":"0.00","source_ref":"SYN-ZERO-COST"}
                 for name in kinds}
            for key in ("ABC:TSX","FUND:TSX")
        }
        costs["ABC:TSX"]["commission"]={"amount_base":"5.00","source_ref":"SYN-COST"}
        cost_inputs={
            "charges_by_destination":costs, "cost_currency":"CAD",
            "cost_quote_as_of":"2026-10-28", "analysis_as_of":"2026-10-28",
            "funding":"FROM_CONTRIBUTION",
        }
        pi = {
            "analysis_id":"SYN-X", "portfolio_as_of":"2026-10-28",
            "room_status":"ROOM_CONDITIONAL",
            "summary":"Synthetic scoped portfolio only",
            "limitations":"Fund look-through incomplete; fees are only supplied estimates",
            "next_action":"Human verification before any decision",
            "forwarded_ir":deepcopy(ir),
        }
        return {
            "request":request, "ir_capsule":ir, "pi_delta":pi,
            "observation_inputs":observation,
            "exposure_classifications":exposure,
            "source_evidence_inputs":source,
            "opportunity_triage_inputs":triage,
            "valuation_inputs":valuation,
            "candidate_comparison_inputs":comparison,
            "room_assessment_inputs":room,
            "contribution_inputs":capital,
            "cost_inputs":cost_inputs,
        }

    def test_real_manual_integrated_route_contains_private_report_seams(self):
        args=self.case()
        original=deepcopy(args)
        out=complete_manual_session(**args)
        self.assertEqual(args,original, "Inputs and forwarded IR must be unchanged")
        self.assertEqual(out["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(out["storage"],"NONE")
        self.assertEqual(out["project_invocation"],"NONE")
        self.assertEqual(out["source_authentication"],"NOT_PERFORMED")
        self.assertEqual(out["readiness"],"NOT_EVALUATED")
        self.assertEqual(out["portfolio_room_review_private"]["status"],"ROOM_CONDITIONAL")
        self.assertEqual(out["portfolio_exposures_private"]["unclassified_or_unknown_fund_pct"],"45.00")
        self.assertEqual(out["integrated_private"]["valuation_scenarios_private"]["source_authentication"],"NOT_PERFORMED")
        self.assertEqual(out["integrated_private"]["candidate_comparison_private"]["recommendation_or_ranking"],"NOT_AUTHORIZED")
        self.assertEqual(out["integrated_private"]["opportunity_triage_private"]["ranking_or_buy_recommendation"],"NONE")
        self.assertEqual(out["integrated_private"]["memory_proposal_nonprivate"]["archive_status"],"PROPOSED_NOT_COMMITTED")
        report=out["final_report_private"]
        for label in ("Investment decision research", "Source reconciliation:",
                      "Research candidate triage", "Valuation scenarios",
                      "Cross-candidate scenario arithmetic", "New contributions",
                      "Portfolio Room"):
            with self.subTest(label=label):
                self.assertIn(label,report)
        self.assertIn("BASE: 10.00 pp",report)
        self.assertIn("45.00% of scoped portfolio",report)
        for sensitive in ("SYN-PRIVATE-ANALYST-VIEW","SYN-COUNTERCASE-A",
                          "1000.00","300.00","600.00","SYN-COST"):
            self.assertNotIn(sensitive,report)
        public=str(out["integrated_private"]["memory_proposal_nonprivate"])
        self.assertNotIn("SYN-PRIVATE-ANALYST-VIEW",public)
        self.assertNotIn("1000.00",public)

    def test_historical_fund_lookthrough_stays_out_of_current_cc_room(self):
        # The entire real M3-to-M4 route must not keep old ETF constituents
        # in its current known issuer/sector percentages.
        case = self.case()
        case["exposure_classifications"]["P2"]["as_of"] = "2026-10-27"
        before = deepcopy(case)
        result = complete_manual_session(**case)
        self.assertEqual(case, before)
        exposures = result["portfolio_exposures_private"]
        self.assertEqual(exposures["known_exposure_pct"], "30.00")
        self.assertEqual(exposures["unclassified_or_unknown_fund_pct"], "60.00")
        self.assertEqual(exposures["cash_pct"], "10.00")
        self.assertEqual(exposures["economic_issuer_pct_private"], {"ABC": "30.00"})
        self.assertEqual(
            exposures["historical_fund_scenario_private"][
                "economic_issuer_pct_of_current_scope_private"],
            {"ABC": "15.00"})
        self.assertEqual(result["portfolio_room_review_private"]["status"],
                         "ROOM_UNAVAILABLE")
        report = result["final_report_private"]
        self.assertIn("Fund constituent evidence predates", report)
        self.assertIn("Known supplied candidate-issuer exposure: UNKNOWN", report)
        self.assertNotIn("S2", report)
        self.assertNotIn("600.00", report)
        self.assertNotIn("historical_fund_scenario_private", report)
        self.assertNotIn(
            "historical_fund_scenario_private",
            str(result["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(result["storage"], "NONE")
        self.assertEqual(result["project_invocation"], "NONE")

    def test_pi_missing_stays_pending_after_real_observation_and_research(self):
        args=self.case()
        args.pop("pi_delta")
        out=complete_manual_session(**args)
        self.assertEqual(out["status"],"AWAITING_MANUAL_PI_DELTA")
        self.assertIsNone(out["final_report_private"])
        self.assertIsNone(out["integrated_private"])
        self.assertEqual(out["project_invocation"],"NONE")
        self.assertEqual(out["storage"],"NONE")

    def with_ir_pillars(self):
        """Reuse the full real M1/M2/M3/M4 synthetic construction case."""
        case = self.case()
        ir = case["ir_capsule"]
        ir["PILLAR_ASSESSMENTS"] = {
            "analysis_id": "SYN-X", "research_as_of": "2026-10-27",
            "strategy_id": "EXPLORATORY",
            "pillars": {
                name: {
                    "status": "SPECIALIST_REPORTED",
                    "ir_fact_ids": ["F-1"],
                    "rationale_private": "SYNTHETIC_PRIVATE_PILLAR_RATIONALE",
                    "countercase_private": "SYNTHETIC_PRIVATE_PILLAR_COUNTERCASE",
                }
                for name in ("QUALITY", "DURABILITY", "EXPECTED_RETURN", "CONFIDENCE")
            },
        }
        case["pi_delta"]["forwarded_ir"] = deepcopy(ir)
        return case

    def test_real_integrated_five_pillars_report_without_scores_or_private_notes(self):
        case = self.with_ir_pillars()
        saved = deepcopy(case)
        result = complete_manual_session(**case)
        self.assertEqual(case, saved)
        self.assertEqual(result["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        report = result["final_report_private"]
        self.assertIn("Five-pillar integrated view", report)
        for axis in ("Quality", "Durability", "Expected Return", "Confidence"):
            self.assertIn("- " + axis + ": IR EVIDENCE_RESOLUTION", report)
        self.assertIn("SAME_REPORTED_LINKS_EVIDENCE_RESOLUTION", report)
        self.assertIn("- Portfolio Room: ROOM_CONDITIONAL (observed 2026-10-28)", report)
        self.assertNotIn("SYNTHETIC_PRIVATE_PILLAR_RATIONALE", report)
        self.assertNotIn("SYNTHETIC_PRIVATE_PILLAR_COUNTERCASE", report)
        self.assertNotIn("SYN-PRIVATE-ANALYST-VIEW", report)
        self.assertNotIn("SYN-SCOPE", report)
        self.assertEqual(result["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"],
                         saved["ir_capsule"])
        self.assertEqual(result["readiness"], "NOT_EVALUATED")

    def test_five_pillar_view_absent_without_both_original_specialist_reviews(self):
        no_ir_trace = complete_manual_session(**self.case())
        self.assertIn("Portfolio Room", no_ir_trace["final_report_private"])
        self.assertNotIn("Five-pillar integrated view", no_ir_trace["final_report_private"])
        no_room = self.with_ir_pillars()
        no_room.pop("room_assessment_inputs")
        result = complete_manual_session(**no_room)
        self.assertIn("Four research pillars", result["final_report_private"])
        self.assertNotIn("Five-pillar integrated view", result["final_report_private"])

    def test_five_pillar_flags_disagreement_without_adding_scores(self):
        case = self.with_ir_pillars()
        case["ir_capsule"]["PILLAR_ASSESSMENTS"]["pillars"]["QUALITY"] = {
            "status": "UNKNOWN", "ir_fact_ids": [],
            "rationale_private": "SYNTHETIC_PRIVATE_PILLAR_RATIONALE",
            "countercase_private": "SYNTHETIC_PRIVATE_PILLAR_COUNTERCASE",
        }
        case["room_assessment_inputs"]["research_axes"]["DURABILITY"]["ir_fact_ids"] = []
        case["pi_delta"]["forwarded_ir"] = deepcopy(case["ir_capsule"])
        result = complete_manual_session(**case)
        report = result["final_report_private"]
        self.assertIn("Quality: IR NOT_ASSESSED; PI SPECIALIST_REPORTED; IR_NOT_ASSESSED", report)
        self.assertIn("Durability: IR EVIDENCE_RESOLUTION; PI SPECIALIST_REPORTED; "
                      "FACT_LINK_DIVERGENCE_REQUIRES_REVIEW", report)
        self.assertIn("Portfolio Room: ROOM_UNAVAILABLE", report)
        self.assertNotIn("SYNTHETIC_PRIVATE_PILLAR_RATIONALE", report)

    def test_five_pillar_rejects_cross_case_strategy_and_ledger_date_spoof(self):
        from ai_native.reporting import render_report
        case = self.with_ir_pillars()
        result = complete_manual_session(**case)
        report = {
            "kind": "DECISION", "analysis_id": "SYN-X", "as_of": "2026-10-28",
            "strategy": "EXPLORATORY", "method_version": "R1",
            "status": "CONDITIONAL", "objective": "Synthetic",
            "decision_line": "No investment", "summary": ["Synthetic"],
            "facts": [], "countercase": "Unknown",
            "limitations": "Unverified", "next_action": "Human review",
            "pillar_trace_private": result["integrated_private"]["pillar_trace_private"],
            "portfolio_room_review_private": result["portfolio_room_review_private"],
            "portfolio_observation_private": result["portfolio_observation_private"],
        }
        with self.assertRaisesRegex(ValueError, "FIVE_PILLAR_AUTHORITY_OR_ID_MISMATCH"):
            changed = deepcopy(report)
            changed["portfolio_room_review_private"]["strategy_id"] = "OTHER"
            render_report(changed)
        with self.assertRaisesRegex(ValueError, "FIVE_PILLAR_ROOM_P_LEDGER_MISMATCH"):
            changed = deepcopy(report)
            changed["portfolio_room_review_private"]["observed_on"] = "2026-10-27"
            render_report(changed)

    def test_mismatched_canonical_date_never_creates_final_report(self):
        args=self.case()
        args["pi_delta"]["portfolio_as_of"]="2026-10-29"
        with self.assertRaisesRegex(ValueError,"OBSERVATION_PI_DATE_MISMATCH|NEWER_THAN_CUTOFF"):
            complete_manual_session(**args)

    def test_forwarded_ir_must_remain_exact_original(self):
        args=self.case()
        args["pi_delta"]["forwarded_ir"]["facts"][0]["claim"]="MUTATED"
        with self.assertRaisesRegex(ValueError,"FORWARDED_IR|PACKET_INCOMPLETE|MISMATCH"):
            complete_manual_session(**args)


if __name__ == "__main__":
    unittest.main()
