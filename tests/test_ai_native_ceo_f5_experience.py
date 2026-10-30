"""F5 synthetic checks for executive placement and genuinely reported effort.

No ChatGPT Project execution, brokerage lookup, or invented elapsed time.
"""
from copy import deepcopy
import unittest

from ai_native.ceo_f5_experience import (
    prepare_human_effort_summary, render_human_effort_line,
    finalize_decision_first_executive,
)
from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import evaluate
from tests.test_ai_native_session_bridge import SessionBridgeTests


class CeoF5ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()

    def effort(self, coverage="CEO_REPORTED_COMPLETE_CYCLE"):
        return {
            "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
            "source": "CEO_REPORTED_ACTIVE_WORK", "coverage": coverage,
            "steps": [
                {"stage": "PI_SOURCE_CAPTURE", "active_seconds": 120},
                {"stage": "HANDOFF_TO_IR", "active_seconds": 60},
                {"stage": "SPECIALIST_RETURN_TO_CC", "active_seconds": 60},
                {"stage": "CC_REVIEW", "active_seconds": 120},
                {"stage": "REPORT_READ", "active_seconds": 480},
            ],
        }

    def test_unmeasured_stays_unknown_not_zero(self):
        req = self.fx.request()
        out = prepare_human_effort_summary(request=req, effort_inputs=None)
        self.assertEqual(out["status"], "NOT_MEASURED")
        self.assertIsNone(out["reported_active_minutes"])
        self.assertIsNone(out["reported_manual_handoffs"])
        self.assertEqual(out["target_read_10_min"], "NOT_ASSESSED")
        self.assertIn("NOT_MEASURED", render_human_effort_line(out))

    def test_complete_ceo_reported_minutes_not_independently_verified(self):
        req = self.fx.request()
        e = self.effort()
        before = deepcopy(e)
        out = prepare_human_effort_summary(request=req, effort_inputs=e)
        self.assertEqual(e, before)
        self.assertEqual(out["reported_manual_handoffs"], 2)
        self.assertEqual(out["reported_active_minutes"], "14.00")
        self.assertEqual(out["reported_read_minutes"], "8.00")
        self.assertEqual(out["target_read_10_min"], "CEO_REPORTED_WITHIN_TARGET")
        self.assertEqual(out["weekly_one_hour_target"], "NOT_ASSESSED_SINGLE_SESSION_ONLY")
        self.assertEqual(out["storage"], "NONE")
        self.assertNotIn("steps", out)

    def test_partial_effort_not_mistaken_for_full_cycle(self):
        inputs = self.effort("PARTIAL_REPORTED_ACTIONS")
        out = prepare_human_effort_summary(request=self.fx.request(),
                                           effort_inputs=inputs)
        self.assertEqual(out["status"], "PARTIAL_MEASURED_SUBTOTAL_ONLY")
        self.assertEqual(out["target_read_10_min"], "NOT_ASSESSED")
        self.assertIn("sous-total partiel", render_human_effort_line(out))

    def test_report_ir_pi_places_f1_f3_f4_f5_before_full_annex(self):
        req = self.fx.request(strategy_id="high-cagr", portfolio_needed=True)
        ir = self.fx.ir()
        pi = self.fx.pi(forwarded_ir=deepcopy(ir))
        e = self.effort()
        out = complete_manual_session(
            req, ir_capsule=ir, pi_delta=pi, human_effort_inputs=e)
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        brief = out["executive_report_private"]
        pos = brief.index("## Points décisifs pour le CEO")
        annex = brief.index("## Dossier détaillé et traçabilité (annexe)")
        self.assertLess(pos, annex)
        for marker in ("**F1 :**", "**F3 :**", "**F4 :**", "**F5 :**"):
            self.assertIn(marker, brief[pos:annex])
        self.assertIn("F5 — Mesure du parcours humain", out["final_report_private"])
        self.assertTrue(brief.endswith(out["final_report_private"].rstrip("\n") + "\n"))
        self.assertEqual(brief.count("## High-CAGR — decision de destination"), 1)
        self.assertEqual(brief.count("## F3 — De la recherche"), 1)
        self.assertIn("14.00 min", brief)
        self.assertEqual(out["human_effort_summary_private"]["reported_manual_handoffs"], 2)
        self.assertEqual(out["integrated_private"]["memory_proposal_nonprivate"]["archive_status"],
                         "PROPOSED_NOT_COMMITTED")
        self.assertEqual(out["storage"], "NONE")

    def test_pi_only_first_read_and_cli_reuse_without_issuer_facts(self):
        req = self.fx.request(strategy_id="balanced",
                              research_needed=False, portfolio_needed=True)
        pi = self.fx.pi()
        packet = {"request": req, "pi_delta": pi}
        out = complete_manual_session(**packet)
        self.assertEqual(out["human_effort_summary_private"]["status"], "NOT_MEASURED")
        summary = out["executive_report_private"]
        self.assertLess(summary.index("## Points décisifs pour le CEO"),
                        summary.index("## Dossier détaillé et traçabilité (annexe)"))
        self.assertTrue(summary.endswith(out["final_report_private"].rstrip("\n") + "\n"))
        self.assertIn("NOT_MEASURED", summary)
        self.assertEqual(evaluate(packet)["status"], out["status"])
        packet["human_effort_inputs"] = self.effort()
        measured = evaluate(packet)
        self.assertEqual(measured["human_effort_summary_private"]["reported_read_minutes"], "8.00")

    def test_ir_only_report_retains_detailed_f3_without_inventing_f1(self):
        out = complete_manual_session(self.fx.request(), ir_capsule=self.fx.ir())
        brief = out["executive_report_private"]
        pos = brief.index("## Points décisifs pour le CEO")
        annex = brief.index("## Dossier détaillé et traçabilité (annexe)")
        self.assertIn("**F3 :**", brief[pos:annex])
        self.assertNotIn("**F1 :**", brief[pos:annex])
        self.assertEqual(brief.count("## F3 — De la recherche"), 1)
        self.assertEqual(out["human_effort_summary_private"]["status"], "NOT_MEASURED")

    def test_bad_inputs_do_not_fabricate_measurements(self):
        for variant in ("wrong_case", "bad_steps", "zero_time",
                        "unbounded", "free_text", "unhashable_coverage"):
            inp = self.effort()
            if variant == "wrong_case":
                inp["analysis_id"] = "OTHER"
            elif variant == "bad_steps":
                inp["steps"] = []
            elif variant == "zero_time":
                inp["steps"][0]["active_seconds"] = 0
            elif variant == "unbounded":
                inp["steps"][0]["active_seconds"] = 90000
            elif variant == "free_text":
                inp["steps"][0]["private_holdings"] = "sensitive text"
            else:
                inp["coverage"] = []
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                prepare_human_effort_summary(request=self.fx.request(),
                                             effort_inputs=inp)
        pending = self.fx.request(portfolio_needed=True)
        with self.assertRaisesRegex(ValueError, "F5_EFFORT_REQUIRES_COMPLETED"):
            complete_manual_session(pending, human_effort_inputs=self.effort())

    def test_report_parity_check_refuses_truncated_annex_or_fake_metadata(self):
        base = "# PAM R1 — Synthèse décisionnelle\n## Dossier détaillé et traçabilité (annexe)\n# FULL\n"
        detail = "# FULL"
        kwargs = dict(
            original_executive=base, original_detail=detail,
            complete_detail=detail + "\n\n## F5\nNOT_MEASURED",
            high_cagr_review=False, admission_review=False,
            public_view_review=False, method_receipt_review=False,
            human_effort_summary=prepare_human_effort_summary(
                request=self.fx.request(), effort_inputs=None))
        result = finalize_decision_first_executive(**kwargs)
        self.assertTrue(result.endswith("## F5\nNOT_MEASURED\n"))
        wrong = deepcopy(kwargs)
        wrong["original_executive"] = base.replace("# FULL", "TRUNCATED")
        with self.assertRaisesRegex(ValueError, "F5_EXECUTIVE_DETAIL_PARITY"):
            finalize_decision_first_executive(**wrong)
        wrong = deepcopy(kwargs)
        wrong["human_effort_summary"]["storage"] = "GITHUB"
        with self.assertRaisesRegex(ValueError, "F5_EFFORT_RENDER_AUTHORITY"):
            finalize_decision_first_executive(**wrong)


if __name__ == "__main__":
    unittest.main()
