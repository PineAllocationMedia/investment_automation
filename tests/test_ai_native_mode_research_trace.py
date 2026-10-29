import copy
import unittest

from ai_native.mode_research_trace import prepare_mode_research_trace
from ai_native.integrated_flow import assemble_manual_run
from ai_native.strategy_authority import R1_MODES
from ai_native.strategy_research_brief import prepare_strategy_research_brief


class ModeResearchTraceTests(unittest.TestCase):
    def request(self, mode="balanced"):
        return {"analysis_id": "SYN-MODE-RESEARCH", "as_of": "2026-10-29",
                "strategy_id": mode, "method_version": "UNKNOWN_NOT_LOADED",
                "kind": "DECISION", "objective": "Synthetic mode-specific analysis"}

    def ir(self, mode="balanced", **changes):
        rows = [
            {"id": "SYN-F1", "claim": "Synthetic illustrative source only",
             "status": "INDICATIVE"},
            {"id": "SYN-F2", "claim": "Synthetic illustrative countercase",
             "status": "MISSING"},
        ]
        packet = {"analysis_id": "SYN-MODE-RESEARCH", "research_as_of": "2026-10-29",
                  "summary": ["Research is incomplete"], "facts": rows,
                  "limitations": "Sources unverified", "countercase": "SYN countercase",
                  "decision_line": "No financial decision", "next_action": "Review evidence"}
        packet.update(changes)
        return packet

    @staticmethod
    def responses(mode="balanced", ids1=None, ids2=None, status2="UNKNOWN"):
        ids1 = ["SYN-F1"] if ids1 is None else ids1
        ids2 = [] if ids2 is None else ids2
        return {"analysis_id": "SYN-MODE-RESEARCH",
                "research_as_of": "2026-10-29", "strategy_id": mode,
                "answers": [
                    {"question_index": 1, "status": "SPECIALIST_REPORTED",
                     "ir_fact_ids": ids1},
                    {"question_index": 2, "status": status2,
                     "ir_fact_ids": ids2},
                ]}

    def test_six_modes_use_the_original_fixed_questions(self):
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                packet = self.ir(mode, MODE_RESEARCH_RESPONSES=self.responses(mode))
                trace = prepare_mode_research_trace(request=self.request(mode), ir_capsule=packet)
                expected = prepare_strategy_research_brief(mode)["ir_research_questions"]
                self.assertEqual([x["question_text"] for x in trace["questions_private"]], expected)
                self.assertEqual(trace["questions_private"][0]["review_stage"], "EVIDENCE_RESOLUTION")
                self.assertEqual(trace["questions_private"][1]["review_stage"], "NOT_ASSESSED")
                self.assertEqual(trace["investment_or_trade_authority"], "NONE")

    def test_missing_optional_responses_not_fabricated(self):
        self.assertIsNone(prepare_mode_research_trace(
            request=self.request(), ir_capsule=self.ir()))
        out = assemble_manual_run(self.request(), self.ir())
        self.assertIsNone(out["mode_research_trace_private"])
        self.assertNotIn("Mode-specific IR research", out["markdown"])

    def test_direct_m7a_report_uses_source_unverified_stage(self):
        packet = self.ir(MODE_RESEARCH_RESPONSES=self.responses())
        before = copy.deepcopy(packet)
        out = assemble_manual_run(self.request(), packet)
        self.assertEqual(out["mode_research_trace_private"]["status"],
                         "PRIVATE_MODE_RESEARCH_TRACE_NOT_CERTIFIED")
        self.assertIn("Mode-specific IR research", out["markdown"])
        self.assertIn("EVIDENCE_RESOLUTION", out["markdown"])
        self.assertIn("NOT_ASSESSED", out["markdown"])
        self.assertNotIn("SYN-F1", out["markdown"].split("## Mode-specific IR research")[1].split("## Supporting observations")[0])
        self.assertEqual(packet, before)

    def test_wrong_mode_and_date_rejected(self):
        for changes in ({"strategy_id": "high-cagr"},
                        {"research_as_of": "2026-10-28"},
                        {"analysis_id": "DIFFERENT"}):
            with self.subTest(changes=changes):
                bad = self.responses()
                bad.update(changes)
                with self.assertRaisesRegex(ValueError, "MODE_RESEARCH_ID_DATE_OR_STRATEGY_MISMATCH"):
                    prepare_mode_research_trace(
                        request=self.request(),
                        ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=bad))

    def test_unknown_fact_id_and_duplicate_question_rejected(self):
        for bad in (self.responses(ids1=["SYN-NOT-A-FACT"]),
                    self.responses(ids1=["SYN-F1", "SYN-F1"])):
            with self.assertRaisesRegex(ValueError, "MODE_RESEARCH_ANSWER_LINKS_INVALID"):
                prepare_mode_research_trace(
                    request=self.request(), ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=bad))
        duplicate = self.responses()
        duplicate["answers"][1]["question_index"] = 1
        with self.assertRaisesRegex(ValueError, "MODE_RESEARCH_ANSWER_LINKS_INVALID"):
            prepare_mode_research_trace(
                request=self.request(), ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=duplicate))

    def test_unknown_requires_no_fact_links_and_reported_needs_one(self):
        for status2, refs in (("UNKNOWN", ["SYN-F2"]),
                              ("SPECIALIST_REPORTED", [])):
            with self.subTest(status2=status2):
                bad = self.responses(ids2=refs, status2=status2)
                with self.assertRaisesRegex(ValueError, "MODE_RESEARCH_ANSWER_LINKS_INVALID"):
                    prepare_mode_research_trace(
                        request=self.request(), ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=bad))

    def test_missing_or_rights_uncertain_source_alignment_stays_unresolved(self):
        from ai_native.fact_evidence_alignment import align_ir_facts_to_sources
        facts = self.ir()["facts"]
        source_annex = {"status": "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED",
                        "analysis_id": "SYN-MODE-RESEARCH",
                        "analysis_as_of": "2026-10-29",
                        "source_authentication": "NOT_PERFORMED_BY_CODE",
                        "observations_private": []}
        alignment = align_ir_facts_to_sources(
            analysis_id="SYN-MODE-RESEARCH",
            analysis_as_of="2026-10-29", ir_facts=facts, source_annex=source_annex)
        trace = prepare_mode_research_trace(
            request=self.request(), fact_alignment=alignment,
            ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=self.responses()))
        self.assertEqual(trace["questions_private"][0]["review_stage"], "EVIDENCE_RESOLUTION")

    def test_structurally_aligned_never_accepted_as_certified(self):
        alignment = {
            "status": "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
            "analysis_id": "SYN-MODE-RESEARCH", "analysis_as_of": "2026-10-29",
            "source_authentication": "NOT_PERFORMED",
            "facts_private": [
                {"fact_id_private": "SYN-F1", "ir_reported_status": "INDICATIVE",
                 "review_flags": [], "alignment": "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"},
                {"fact_id_private": "SYN-F2", "ir_reported_status": "MISSING",
                 "review_flags": ["NO_OBSERVATION_FOR_IR_FACT"],
                 "alignment": "REVIEW_REQUIRED"},
            ]}
        trace = prepare_mode_research_trace(
            request=self.request(), fact_alignment=alignment,
            ir_capsule=self.ir(MODE_RESEARCH_RESPONSES=self.responses()))
        self.assertEqual(trace["questions_private"][0]["review_stage"],
                         "HUMAN_RESEARCH_REVIEW_ONLY")
        self.assertEqual(trace["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(trace["method_load"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
