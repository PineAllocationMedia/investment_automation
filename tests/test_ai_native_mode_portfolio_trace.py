import copy
import unittest

from ai_native.mode_portfolio_trace import prepare_mode_portfolio_trace
from ai_native.strategy_authority import R1_MODES
from ai_native.strategy_research_brief import prepare_strategy_research_brief
from ai_native.integrated_flow import assemble_manual_run
from ai_native.session_bridge import complete_manual_session


class ModePortfolioTraceTests(unittest.TestCase):
    def request(self, strategy="balanced", **kw):
        result = {"analysis_id": "SYN-PI-MODE", "as_of": "2026-10-29",
                  "strategy_id": strategy, "kind": "DECISION",
                  "objective": "Synthetic portfolio only", "ceo_initiated": True,
                  "research_needed": False, "portfolio_needed": True}
        result.update(kw)
        return result

    def response(self, strategy="balanced", *, second_status="UNKNOWN", second_ids=None):
        return {"analysis_id": "SYN-PI-MODE", "portfolio_as_of": "2026-10-29",
                "strategy_id": strategy, "answers": [
                    {"question_index": 1, "status": "SPECIALIST_REPORTED", "p_ids": ["P-01"]},
                    {"question_index": 2, "status": second_status,
                     "p_ids": [] if second_ids is None else second_ids},
                ]}

    def pi(self, **changes):
        delta = {"analysis_id": "SYN-PI-MODE", "portfolio_as_of": "2026-10-29",
                 "room_status": "ROOM_CONDITIONAL", "summary": "SYN no broker proof",
                 "limitations": "SYN costs unknown", "next_action": "Review account data"}
        delta.update(changes)
        return delta

    def ledger(self, complete=True):
        return {"status": "SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA" if complete else "OBSERVATION_LEDGER_ONLY",
                "analysis_id": "SYN-PI-MODE", "analysis_as_of": "2026-10-29",
                "observed_on": "2026-10-29", "private_scope": True,
                "verification": "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED",
                "source_retrieval": "NONE", "decision_authority": "CEO_ONLY",
                "missing_or_qualified": [] if complete else ["CASH_NOT_VISIBLE"],
                "p_ledger_private": [{
                    "p_id": "P-01", "security_id": "SYN-ETF",
                    "field_statuses": {
                        "security_id": "VERIFIED_VISIBLE", "market_value_base": "VERIFIED_VISIBLE",
                        "currency": "VERIFIED_VISIBLE", "account_scope": "VERIFIED_VISIBLE",
                    },
                }],
            }

    def test_six_modes_reuse_unchanged_pi_questions(self):
        for mode in R1_MODES:
            with self.subTest(mode=mode):
                d = self.pi(MODE_PORTFOLIO_RESPONSES=self.response(mode))
                trace = prepare_mode_portfolio_trace(request=self.request(mode), pi_delta=d)
                self.assertEqual([r["question_text"] for r in trace["questions_private"]],
                                 prepare_strategy_research_brief(mode)["pi_portfolio_questions"])
                self.assertEqual(trace["questions_private"][0]["review_stage"], "EVIDENCE_RESOLUTION")
                self.assertEqual(trace["questions_private"][1]["review_stage"], "NOT_ASSESSED")
                self.assertEqual(trace["investment_or_trade_authority"], "NONE")

    def test_absence_does_not_invent_answers(self):
        self.assertIsNone(prepare_mode_portfolio_trace(
            request=self.request(), pi_delta=self.pi()))

    def test_complete_caller_ledger_only_human_review(self):
        delta = self.pi(MODE_PORTFOLIO_RESPONSES=self.response())
        original = copy.deepcopy(delta)
        trace = prepare_mode_portfolio_trace(
            request=self.request(), pi_delta=delta, observation=self.ledger())
        self.assertEqual(trace["questions_private"][0]["review_stage"],
                         "HUMAN_PORTFOLIO_REVIEW_ONLY")
        self.assertEqual(trace["source_authentication"], "NOT_PERFORMED")
        self.assertEqual(trace["portfolio_room_authority"], "NONE")
        self.assertEqual(delta, original)

    def test_partial_ledger_remains_unresolved(self):
        trace = prepare_mode_portfolio_trace(
            request=self.request(),
            pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=self.response()),
            observation=self.ledger(complete=False))
        self.assertEqual(trace["questions_private"][0]["review_stage"], "EVIDENCE_RESOLUTION")

    def test_unknown_ids_rejected_if_ledger_supplied(self):
        response = self.response()
        response["answers"][0]["p_ids"] = ["P-MISSING"]
        with self.assertRaisesRegex(ValueError, "MODE_PI_UNKNOWN_P_ID"):
            prepare_mode_portfolio_trace(
                request=self.request(),
                pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=response),
                observation=self.ledger())

    def test_strategy_date_and_question_conflicts_fail_closed(self):
        for modification in (
            {"strategy_id": "high-cagr"},
            {"analysis_id": "WRONG"},
            {"portfolio_as_of": "2026-10-28"},
        ):
            response = self.response()
            response.update(modification)
            with self.subTest(modification=modification):
                with self.assertRaisesRegex(ValueError, "MODE_PI_ID_DATE_OR_STRATEGY_MISMATCH"):
                    prepare_mode_portfolio_trace(
                        request=self.request(),
                        pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=response))
        response = self.response()
        response["answers"][1]["question_index"] = 1
        with self.assertRaisesRegex(ValueError, "MODE_PI_ANSWER_LINKS_INVALID"):
            prepare_mode_portfolio_trace(
                request=self.request(), pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=response))

    def test_unknown_status_requires_empty_references(self):
        for status, ids in (("UNKNOWN", ["P-01"]), ("SPECIALIST_REPORTED", [])):
            with self.subTest(status=status):
                response = self.response(second_status=status, second_ids=ids)
                with self.assertRaisesRegex(ValueError, "MODE_PI_ANSWER_LINKS_INVALID"):
                    prepare_mode_portfolio_trace(
                        request=self.request(),
                        pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=response))

    def test_pi_only_session_report_does_not_expose_holdings(self):
        response = self.response()
        out = complete_manual_session(
            self.request(), pi_delta=self.pi(MODE_PORTFOLIO_RESPONSES=response))
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(out["mode_portfolio_trace_private"]["observation_link_status"], "NO_P_LEDGER")
        report = out["final_report_private"]
        self.assertIn("Mode-specific PI research", report)
        self.assertIn("EVIDENCE_RESOLUTION", report)
        self.assertNotIn("P-01", report)

    def test_combined_ir_pi_route_preserves_original_and_marks_no_ledger(self):
        request = self.request(research_needed=True)
        original = {"analysis_id": "SYN-PI-MODE", "research_as_of": "2026-10-29",
                    "summary": ["SYN not verified"], "facts": [],
                    "limitations": "Sources absent", "countercase": "SYN uncertainty",
                    "decision_line": "No decision", "next_action": "Review sources"}
        pi = self.pi(MODE_PORTFOLIO_RESPONSES=self.response(), forwarded_ir=copy.deepcopy(original))
        before = copy.deepcopy((original, pi))
        result = complete_manual_session(request, ir_capsule=original, pi_delta=pi)
        self.assertEqual(result["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertEqual(result["mode_portfolio_trace_private"]["questions_private"][0]["review_stage"],
                         "EVIDENCE_RESOLUTION")
        self.assertIn("Mode-specific PI research", result["final_report_private"])
        self.assertEqual((original, pi), before)

    def test_direct_m7a_reuses_optional_pi_trace(self):
        req = {"analysis_id": "SYN-PI-MODE", "as_of": "2026-10-29",
               "strategy_id": "balanced", "method_version": "UNKNOWN_NOT_LOADED",
               "kind": "DECISION", "objective": "Synthetic comparison"}
        ir = {"analysis_id": "SYN-PI-MODE", "research_as_of": "2026-10-29",
              "summary": ["SYN uncertainty"], "facts": [],
              "limitations": "Source not checked", "countercase": "No data",
              "decision_line": "No conclusion", "next_action": "Read source"}
        pi = self.pi(MODE_PORTFOLIO_RESPONSES=self.response(), forwarded_ir=copy.deepcopy(ir))
        out = assemble_manual_run(req, ir, pi_delta=pi)
        self.assertEqual(out["mode_portfolio_trace_private"]["status"],
                         "PRIVATE_MODE_PI_TRACE_NOT_AUTHENTICATED")
        self.assertIn("Mode-specific PI research", out["markdown"])


if __name__ == "__main__":
    unittest.main()
