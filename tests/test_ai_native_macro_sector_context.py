"""Synthetic M2 macro/sector review and real CC→IR→report construction seams.

No market data is retrieved; tests do not demonstrate true economic causality.
"""
import copy
import unittest

from ai_native.macro_sector_context import prepare_macro_sector_context
from ai_native.source_fusion import assemble_source_fusion
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from tests.test_ai_native_construction_contracts import R1ConstructionContracts
from tests.test_ai_native_reporting import ReportingTests


class MacroSectorContextTests(unittest.TestCase):
    def setUp(self):
        self.fx = R1ConstructionContracts()

    def observation(self, **changes):
        row = self.fx.source()
        row.update(changes)
        return row

    def source(self, **changes):
        return assemble_source_fusion(
            analysis_id="SYN-X", analysis_as_of="2026-10-28",
            observations=[self.observation(**changes)])

    def driver(self, **changes):
        row = {"driver_id":"SYN-RATES","scope":"MACRO",
               "reported_effect":"HEADWIND_REPORTED",
               "ir_fact_ids":["F-1"],"source_observation_ids":["OBS1"],
               "hypothesis_private":"CONFIDENTIAL_HYPOTHESIS: higher funding cost?",
               "countercase_private":"CONFIDENTIAL_COUNTERCASE: already priced?",
               "next_check_private":"CONFIDENTIAL_CHECK: verify company cash flows"}
        row.update(changes)
        return row

    def args(self, source=None, drivers=None):
        return {"analysis_id":"SYN-X","analysis_as_of":"2026-10-28",
                "strategy_id":"EXPLORATORY",
                "drivers":[self.driver()] if drivers is None else drivers,
                "ir_facts":self.fx.capsule()["facts"],
                "source_annex":self.source() if source is None else source}

    def input(self, **changes):
        p={"analysis_id":"SYN-X","analysis_as_of":"2026-10-28",
           "strategy_id":"EXPLORATORY","drivers":[self.driver()]}
        p.update(changes)
        return p

    def test_uncertain_secondary_source_keeps_context_in_evidence_resolution(self):
        data=self.args(); before=copy.deepcopy(data)
        out=prepare_macro_sector_context(**data)
        self.assertEqual(out["status"],"PRIVATE_MACRO_SECTOR_CONTEXT_PREPARED_NOT_CERTIFIED")
        self.assertEqual(out["stage_counts"]["EVIDENCE_RESOLUTION"],1)
        self.assertIn("SOURCE_RIGHTS_NOT_ESTABLISHED",
                      out["drivers_private_in_supplied_order"][0]["review_reasons"])
        self.assertIn("PRIMARY_SOURCE_NOT_DOCUMENTED",
                      out["drivers_private_in_supplied_order"][0]["review_reasons"])
        self.assertEqual(out["market_timing_or_price_prediction"],"NONE")
        self.assertEqual(out["ranking_or_trading_authority"],"NONE")
        self.assertEqual(data,before)

    def test_usable_caller_reported_primary_source_only_queues_human_causal_review(self):
        source=self.source(source_kind="ISSUER_OR_REGULATOR",rights_status="PERMITTED",
                           original_checked_at="2026-10-27")
        out=prepare_macro_sector_context(**self.args(source=source))
        self.assertEqual(out["stage_counts"]["HUMAN_CAUSAL_REVIEW"],1)
        self.assertEqual(out["causal_inference"],"ANALYST_HYPOTHESIS_NOT_CERTIFIED")
        self.assertEqual(out["source_authentication"],"NOT_PERFORMED")

    def test_no_observation_or_unknown_effect_remains_unresolved(self):
        inputs=self.args(drivers=[self.driver(source_observation_ids=[],reported_effect="UNKNOWN")])
        out=prepare_macro_sector_context(**inputs)
        reasons=out["drivers_private_in_supplied_order"][0]["review_reasons"]
        self.assertIn("NO_LINKED_SOURCE_OBSERVATIONS",reasons)
        self.assertIn("DIRECTIONAL_EFFECT_UNKNOWN",reasons)
        self.assertEqual(out["stage_counts"]["EVIDENCE_RESOLUTION"],1)

    def test_unknown_fact_source_or_cross_fact_links_rejected(self):
        for drivers,err in (
            ([self.driver(ir_fact_ids=["OTHER"])],"CONTEXT_UNKNOWN_OR_MISSING_IR_FACT"),
            ([self.driver(source_observation_ids=["OTHER"])],"CONTEXT_UNKNOWN_SOURCE_OBSERVATION"),
            ([self.driver(ir_fact_ids=["F-1","F-1"])],"CONTEXT_DUPLICATE_LINK"),
            ([self.driver(scope="MARKET_TIMING")],"CONTEXT_SCOPE_OR_EFFECT_INVALID"),
        ):
            with self.subTest(err=err),self.assertRaisesRegex(ValueError,err):
                prepare_macro_sector_context(**self.args(drivers=drivers))
        bad_source=self.source()
        bad_source["observations_private"][0]["fact_id"]="OTHER"
        with self.assertRaisesRegex(ValueError,"CONTEXT_OBSERVATION_ID_OR_FACT_INVALID"):
            prepare_macro_sector_context(**self.args(source=bad_source))

    def test_no_candidate_ranking_or_duplicate_driver(self):
        with self.assertRaisesRegex(ValueError,"CONTEXT_DUPLICATE_DRIVER"):
            prepare_macro_sector_context(**self.args(drivers=[self.driver(),self.driver()]))
        with self.assertRaisesRegex(ValueError,"CONTEXT_DRIVER_EXACT_SCHEMA_REQUIRED"):
            prepare_macro_sector_context(**self.args(drivers=[dict(self.driver(),trade="BUY")]))

    def test_real_manual_route_renders_context_without_private_causal_claims(self):
        request=self.fx.request()
        ir=self.fx.capsule()
        source={"analysis_id":"SYN-X","analysis_as_of":"2026-10-28",
                "observations":[self.observation()]}
        context=self.input()
        original=copy.deepcopy((request,ir,source,context))
        result=complete_manual_session(
            request,ir_capsule=ir,source_evidence_inputs=source,
            macro_sector_inputs=context)
        self.assertEqual(result["status"],"M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual((request,ir,source,context),original)
        private=result["integrated_private"]["macro_sector_context_private"]
        self.assertEqual(private["stage_counts"]["EVIDENCE_RESOLUTION"],1)
        self.assertIn("Macro and sector context",result["final_report_private"])
        self.assertIn("SYN-RATES [MACRO]: HEADWIND_REPORTED",result["final_report_private"])
        self.assertIn("EVIDENCE_RESOLUTION",result["final_report_private"])
        self.assertNotIn("CONFIDENTIAL_HYPOTHESIS",result["final_report_private"])
        self.assertNotIn("CONFIDENTIAL_COUNTERCASE",result["final_report_private"])
        self.assertNotIn("CONFIDENTIAL_CHECK",result["final_report_private"])
        self.assertNotIn("CONFIDENTIAL_HYPOTHESIS",str(result["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(result["project_invocation"],"NONE")
        self.assertEqual(result["storage"],"NONE")

    def test_no_source_annex_and_mandate_mismatch_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"MACRO_SECTOR_REQUIRES_SOURCE_ANNEX"):
            complete_manual_session(self.fx.request(),ir_capsule=self.fx.capsule(),
                                    macro_sector_inputs=self.input())
        source={"analysis_id":"SYN-X","analysis_as_of":"2026-10-28",
                "observations":[self.observation()]}
        with self.assertRaisesRegex(ValueError,"MACRO_SECTOR_MANDATE_MISMATCH"):
            complete_manual_session(self.fx.request(),ir_capsule=self.fx.capsule(),
                                    source_evidence_inputs=source,
                                    macro_sector_inputs=self.input(strategy_id="OTHER"))

    def test_source_observed_after_ir_capsule_as_of_is_not_backdated(self):
        source={"analysis_id":"SYN-X","analysis_as_of":"2026-10-28",
                "observations":[self.observation(observed_at="2026-10-28")]}
        with self.assertRaisesRegex(
            ValueError,"MACRO_SECTOR_OBSERVATION_AFTER_IR_RESEARCH_AS_OF"):
            complete_manual_session(self.fx.request(),ir_capsule=self.fx.capsule(),
                                    source_evidence_inputs=source,
                                    macro_sector_inputs=self.input())

    def test_no_ir_route_or_missing_ir_handoff_cannot_claim_finished_report(self):
        with self.assertRaisesRegex(ValueError,"MACRO_SECTOR_REQUIRES_IR_ROUTE"):
            complete_manual_session(self.fx.request(False,True),
                                    macro_sector_inputs=self.input())
        out=complete_manual_session(self.fx.request(),macro_sector_inputs=self.input())
        self.assertEqual(out["status"],"AWAITING_MANUAL_IR_CAPSULE")
        self.assertIsNone(out["final_report_private"])

    def test_report_rejects_forged_certification_or_counts(self):
        context=prepare_macro_sector_context(**self.args())
        def packet(**edits):
            p=ReportingTests().packet(
                analysis_id="SYN-X",strategy="EXPLORATORY",
                macro_sector_context_private=context)
            p.update(edits)
            return p
        text=render_report(packet())
        self.assertIn("Macro and sector context",text)
        clone=copy.deepcopy(context)
        clone["market_timing_or_price_prediction"]="CERTIFIED_ENTRY_SIGNAL"
        with self.assertRaisesRegex(ValueError,"CONTEXT_REPORT_AUTHORITY"):
            render_report(packet(macro_sector_context_private=clone))
        clone=copy.deepcopy(context)
        clone["driver_count"]=7
        with self.assertRaisesRegex(ValueError,"CONTEXT_REPORT_COUNT_MISMATCH"):
            render_report(packet(macro_sector_context_private=clone))


if __name__ == "__main__":
    unittest.main()
