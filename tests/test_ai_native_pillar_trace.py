"""Synthetic contract tests for the R1 optional four-pillar IR-to-CC seam."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.integrated_flow import assemble_manual_run
from ai_native.pillar_trace import PILLARS, prepare_pillar_trace
from ai_native.reporting import render_report
from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import main


class FourPillarTraceTests(unittest.TestCase):
    def request(self, **patch):
        value = {
            "analysis_id": "SYN-PILLAR-1", "as_of": "2026-10-28",
            "objective": "Evaluate a fictional business",
            "strategy_id": "high-cagr", "method_version": "SYN-METHOD-1",
            "kind": "DECISION",
        }
        value.update(patch)
        return value

    def ir(self, **patch):
        axes = {
            key: {"status": "SPECIALIST_REPORTED", "ir_fact_ids": ["SYN-F1"],
                  "rationale_private": "PRIVATE-SYNTHETIC-RATIONALE",
                  "countercase_private": "PRIVATE-SYNTHETIC-COUNTERCASE"}
            for key in PILLARS
        }
        value = {
            "analysis_id": "SYN-PILLAR-1", "research_as_of": "2026-10-27",
            "summary": ["Fictional operations require checking."],
            "facts": [{"id": "SYN-F1", "status": "INDICATIVE",
                       "claim": "Synthetic fact, no authentic source."}],
            "decision_line": "No investability claim.",
            "limitations": "Not verified", "countercase": "Other explanations possible.",
            "next_action": "Read an original source before further work.",
            "PILLAR_ASSESSMENTS": {
                "analysis_id": "SYN-PILLAR-1",
                "research_as_of": "2026-10-27",
                "strategy_id": "high-cagr",
                "pillars": axes,
            },
        }
        value.update(patch)
        return value

    def aligned(self, **patch):
        value = {
            "status": "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
            "analysis_id": "SYN-PILLAR-1", "analysis_as_of": "2026-10-28",
            "source_authentication": "NOT_PERFORMED",
            "facts_private": [{"fact_id_private": "SYN-F1",
                               "ir_reported_status": "INDICATIVE",
                               "review_flags": [],
                               "alignment": "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"}],
        }
        value.update(patch)
        return value

    def test_absent_optional_packet_preserves_legacy_flow(self):
        ir = self.ir()
        del ir["PILLAR_ASSESSMENTS"]
        self.assertIsNone(prepare_pillar_trace(request=self.request(), ir_capsule=ir))
        result = assemble_manual_run(self.request(), ir)
        self.assertIsNone(result["pillar_trace_private"])
        self.assertNotIn("Four research pillars", result["markdown"])

    def test_source_missing_retains_private_rationale_and_conditional_report(self):
        ir = self.ir()
        original = deepcopy(ir)
        result = assemble_manual_run(self.request(), ir)
        self.assertEqual(ir, original)
        trace = result["pillar_trace_private"]
        self.assertEqual(trace["pillars_private"]["EXPECTED_RETURN"]["review_stage"], "EVIDENCE_RESOLUTION")
        self.assertEqual(result["status"], "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE")
        self.assertIn("Four research pillars", result["markdown"])
        self.assertIn("Portfolio Room is a separate", result["markdown"])
        self.assertIn("4", str(len(trace["pillars_private"])))
        self.assertNotIn("PRIVATE-SYNTHETIC-RATIONALE", result["markdown"])
        self.assertNotIn("PRIVATE-SYNTHETIC-COUNTERCASE", result["markdown"])
        self.assertNotIn("PRIVATE-SYNTHETIC", str(result["memory_proposal_nonprivate"]))
        self.assertIn("CONDITIONAL", result["markdown"])

    def test_structural_alignment_only_yields_human_not_certified_stage(self):
        result = prepare_pillar_trace(request=self.request(), ir_capsule=self.ir(),
                                      fact_alignment=self.aligned())
        self.assertEqual(result["pillars_private"]["QUALITY"]["review_stage"],
                         "HUMAN_RESEARCH_REVIEW_ONLY")
        self.assertEqual(result["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(result["expected_return_certification"], "NOT_ESTABLISHED")
        self.assertEqual(result["investment_or_trade_authority"], "NONE")

    def test_disputed_or_review_flagged_fact_never_reaches_human_stage(self):
        ir = self.ir()
        ir["facts"][0]["status"] = "CONFLICTED"
        self.assertEqual(prepare_pillar_trace(
            request=self.request(), ir_capsule=ir
        )["pillars_private"]["QUALITY"]["review_stage"], "EVIDENCE_RESOLUTION")
        ir = self.ir()
        alignment = self.aligned()
        alignment["facts_private"][0]["review_flags"] = ["SOURCE_UNAVAILABLE"]
        alignment["facts_private"][0]["alignment"] = "REVIEW_REQUIRED"
        self.assertEqual(prepare_pillar_trace(
            request=self.request(), ir_capsule=ir, fact_alignment=alignment
        )["pillars_private"]["QUALITY"]["review_stage"], "EVIDENCE_RESOLUTION")

    def test_unknown_pillar_is_not_economic_failure(self):
        ir = self.ir()
        ir["PILLAR_ASSESSMENTS"]["pillars"]["CONFIDENCE"]["status"] = "UNKNOWN"
        trace = prepare_pillar_trace(request=self.request(), ir_capsule=ir)
        self.assertEqual(trace["pillars_private"]["CONFIDENCE"]["review_stage"], "NOT_ASSESSED")
        text = assemble_manual_run(self.request(), ir)["markdown"]
        self.assertIn("not assessed", text)

    def test_reject_mismatched_identity_date_and_strategy(self):
        for name, value in (
            ("analysis_id", "WRONG"),
            ("research_as_of", "2026-10-26"),
            ("strategy_id", "balanced"),
        ):
            with self.subTest(name=name):
                ir = self.ir()
                ir["PILLAR_ASSESSMENTS"][name] = value
                with self.assertRaisesRegex(ValueError, "PILLAR_ID_DATE_OR_STRATEGY_MISMATCH"):
                    prepare_pillar_trace(request=self.request(), ir_capsule=ir)

    def test_future_research_and_invalid_calendar_date_fail(self):
        with self.assertRaisesRegex(ValueError, "PILLAR_ID_DATE_OR_STRATEGY_MISMATCH"):
            prepare_pillar_trace(request=self.request(), ir_capsule=self.ir(research_as_of="2026-10-29"))
        with self.assertRaisesRegex(ValueError, "canonical date"):
            prepare_pillar_trace(request=self.request(), ir_capsule=self.ir(research_as_of="2026-02-30"))

    def test_reject_unknown_duplicate_and_missing_supported_fact_links(self):
        for links in (["GHOST"], ["SYN-F1", "SYN-F1"], []):
            with self.subTest(links=links):
                ir = self.ir()
                ir["PILLAR_ASSESSMENTS"]["pillars"]["QUALITY"]["ir_fact_ids"] = links
                with self.assertRaisesRegex(ValueError, "PILLAR_QUALITY_"):
                    prepare_pillar_trace(request=self.request(), ir_capsule=ir)

    def test_exact_four_pillars_and_private_notes_required(self):
        ir = self.ir()
        del ir["PILLAR_ASSESSMENTS"]["pillars"]["DURABILITY"]
        with self.assertRaisesRegex(ValueError, "EXACT_FOUR"):
            prepare_pillar_trace(request=self.request(), ir_capsule=ir)
        ir = self.ir()
        ir["PILLAR_ASSESSMENTS"]["pillars"]["QUALITY"]["rationale_private"] = ""
        with self.assertRaisesRegex(ValueError, "rationale_private"):
            prepare_pillar_trace(request=self.request(), ir_capsule=ir)
        ir = self.ir()
        ir["PILLAR_ASSESSMENTS"]["allowed_to_trade"] = True
        with self.assertRaisesRegex(ValueError, "EXACT_SCHEMA"):
            prepare_pillar_trace(request=self.request(), ir_capsule=ir)

    def test_alignment_coverage_and_source_authority_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "ALIGNMENT_AUTHORITY"):
            prepare_pillar_trace(request=self.request(), ir_capsule=self.ir(),
                                 fact_alignment=self.aligned(source_authentication="CERTIFIED"))
        with self.assertRaisesRegex(ValueError, "ALIGNMENT_COVERAGE"):
            prepare_pillar_trace(request=self.request(), ir_capsule=self.ir(),
                                 fact_alignment=self.aligned(facts_private=[]))

    def test_m1_ir_pi_handoff_preserves_original_capsule_and_report(self):
        request = dict(self.request(), ceo_initiated=True, research_needed=True, portfolio_needed=True)
        ir = self.ir()
        pi = {"analysis_id": "SYN-PILLAR-1", "portfolio_as_of": "2026-10-28",
              "room_status": "ROOM_UNAVAILABLE",
              "summary": "Incomplete synthetic positions.",
              "limitations": "Unknown weights.",
              "forwarded_ir": deepcopy(ir)}
        original = deepcopy((ir, pi))
        result = complete_manual_session(request, ir_capsule=ir, pi_delta=pi)
        self.assertEqual((ir, pi), original)
        self.assertEqual(result["handoffs_private"]["pi_request_private"]["FORWARD_UNCHANGED"], ir)
        self.assertIn("Four research pillars", result["final_report_private"])
        self.assertEqual(result["project_invocation"], "NONE")

    def test_report_rejects_pillar_authority_spoof_and_status_injection(self):
        out = assemble_manual_run(self.request(), self.ir())
        packet = {
            "kind": "DECISION", "analysis_id": "SYN-PILLAR-1",
            "as_of": "2026-10-28", "strategy": "high-cagr",
            "method_version": "SYN-METHOD-1", "status": "CONDITIONAL",
            "objective": "Synthetic", "decision_line": "Not a decision",
            "summary": ["Unknown"], "facts": self.ir()["facts"],
            "countercase": "Unverified", "limitations": "Unverified",
            "next_action": "Inspect", "pillar_trace_private": deepcopy(out["pillar_trace_private"]),
        }
        packet["pillar_trace_private"]["source_authentication"] = "CERTIFIED"
        with self.assertRaisesRegex(ValueError, "PILLAR_REPORT_AUTHORITY"):
            render_report(packet)
        packet["pillar_trace_private"] = deepcopy(out["pillar_trace_private"])
        packet["pillar_trace_private"]["pillars_private"]["QUALITY"]["review_stage"] = "PRODUCTION_READY"
        with self.assertRaisesRegex(ValueError, "PILLAR_REPORT_AXIS_STATUS"):
            render_report(packet)

    def test_local_cli_report_routes_private_pillars_only_on_explicit_request(self):
        request = dict(self.request(), ceo_initiated=True, research_needed=True,
                       portfolio_needed=False)
        packet = {"request": request, "ir_capsule": self.ir()}
        stdout, stderr = StringIO(), StringIO()
        code = main(["--output", "report"], instream=StringIO(json.dumps(packet)),
                    outstream=stdout, errstream=stderr)
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertIn("Four research pillars", stdout.getvalue())
        self.assertNotIn("PRIVATE-SYNTHETIC-RATIONALE", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
