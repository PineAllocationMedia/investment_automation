"""Synthetic P11B/F2: CEO-visible-scope attestation is not account verification."""
from copy import deepcopy
import unittest

from ai_native.session_bridge import complete_manual_session
from ai_native.attested_visible_concentration import (
    prepare_attested_visible_concentration, render_attested_visible_concentration,
)
from ai_native.public_portfolio_reference import prepare_public_portfolio_reference
from scripts.r1_manual_session_cli import evaluate
from tests.test_ai_native_public_portfolio_reference import PublicReferenceTests


class AttestedVisibleConcentrationTests(unittest.TestCase):
    def setUp(self):
        self.fx = PublicReferenceTests()

    def packet(self, *, complete=True):
        packet = self.fx.data()
        if complete:
            packet["observation_as_of"] = "2026-10-29"
            packet["captured_at"] = "2026-10-29T10:00:00-04:00"
            packet["coverage"] = {k: True for k in packet["coverage"]}
            for row, weight in zip(
                    packet["positions_visible"], ("40.00", "30.00", "20.00", "10.00")):
                row["weight_pct"] = weight
            packet["displayed_weight_sum_pct"] = "100.00"
        return packet

    def attestation(self):
        return {"analysis_id": "SYN-REF-1",
                "analysis_as_of": "2026-10-29",
                "scope_attestation": "CEO_ATTESTS_VISIBLE_SCOPE_AS_DISPLAYED"}

    def test_complete_report_is_view_only_not_personal_brokerage(self):
        inputs = {"request": self.fx.req(),
                  "public_reference_inputs": self.packet(),
                  "public_scope_attestation_inputs": self.attestation()}
        before = deepcopy(inputs)
        out = complete_manual_session(**inputs)
        self.assertEqual(inputs, before)
        self.assertEqual(out["status"], "PUBLIC_REFERENCE_DESCRIPTIVE_REPORT_READY")
        review = out["public_scope_attested_concentration_private"]
        self.assertEqual(review["status"], "CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION")
        self.assertEqual(review["top_one_visible_line_pct"], "40.00")
        self.assertEqual(review["top_five_visible_lines_pct"], "100.00")
        self.assertEqual(review["denominator"], "DISPLAYED_VIEW_ONLY")
        self.assertEqual(review["brokerage_ownership"], "NOT_PROVEN")
        self.assertEqual(review["post_contribution_weights"], "UNAVAILABLE")
        self.assertIn("première ligne 40.00 %", out["final_report_private"])
        self.assertNotIn("SYN_ACCOUNT_MUST_NOT_LEAK_IN_REPORT", out["final_report_private"])
        self.assertEqual(out["storage"], "NONE")
        # Existing CLI path, no new service/automation.
        self.assertEqual(evaluate(inputs)["public_scope_attested_concentration_private"], review)

    def test_incomplete_view_does_not_claim_a_denominator_or_cash_zero(self):
        out = complete_manual_session(
            self.fx.req(), public_reference_inputs=self.packet(complete=False),
            public_scope_attestation_inputs=self.attestation())
        review = out["public_scope_attested_concentration_private"]
        self.assertEqual(review["status"], "DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED")
        self.assertIsNone(review["top_one_visible_line_pct"])
        self.assertIsNone(review["top_five_visible_lines_pct"])
        self.assertIn("cash_visible", review["blockers"])
        self.assertIn("displayed_sum_not_100_within_rounding", review["blockers"])
        self.assertIn("Dénominateur de la vue INSUFFISANT", out["final_report_private"])

    def test_minor_rounding_accepted_but_never_rescaled(self):
        p = self.packet()
        p["positions_visible"][0]["weight_pct"] = "40.01"
        p["displayed_weight_sum_pct"] = "100.01"
        out = complete_manual_session(
            self.fx.req(), public_reference_inputs=p,
            public_scope_attestation_inputs=self.attestation())
        review = out["public_scope_attested_concentration_private"]
        self.assertEqual(review["status"], "CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION")
        self.assertEqual(review["displayed_sum_pct"], "100.01")
        self.assertEqual(review["top_one_visible_line_pct"], "40.01")

    def test_attestation_case_conflict_missing_reference_and_pi_promotion_fail(self):
        p = self.packet()
        att = self.attestation()
        bad = deepcopy(att)
        bad["analysis_id"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "CASE_OR_SCOPE"):
            prepare_attested_visible_concentration(
                prepare_public_portfolio_reference(
                    p, analysis_id="SYN-REF-1", analysis_as_of="2026-10-29"), bad)
        with self.assertRaisesRegex(ValueError, "ATTESTED_VIEW_REQUIRES_PUBLIC_REFERENCE"):
            complete_manual_session(self.fx.req(), public_scope_attestation_inputs=att)
        with self.assertRaisesRegex(ValueError, "PUBLIC_REFERENCE_ONLY_CC_OR_IR_ROUTE"):
            complete_manual_session(
                self.fx.req(portfolio=True), public_reference_inputs=p,
                public_scope_attestation_inputs=att)

    def test_unattested_legacy_route_unchanged_and_renderer_rejects_promotion(self):
        p = self.packet()
        out = complete_manual_session(self.fx.req(), public_reference_inputs=p)
        self.assertIsNone(out["public_scope_attested_concentration_private"])
        self.assertNotIn("Périmètre de vue attesté", out["final_report_private"])
        result = prepare_attested_visible_concentration(
            prepare_public_portfolio_reference(
                p, analysis_id="SYN-REF-1", analysis_as_of="2026-10-29"),
            self.attestation())
        result["brokerage_ownership"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "REPORT_AUTHORITY_INVALID"):
            render_attested_visible_concentration(result)

    def test_combined_ir_route_carries_only_descriptive_attestation(self):
        out = complete_manual_session(
            self.fx.req(research=True), ir_capsule=self.fx.ir(),
            public_reference_inputs=self.packet(),
            public_scope_attestation_inputs=self.attestation())
        self.assertIn("Périmètre de vue attesté", out["final_report_private"])
        self.assertEqual(out["public_scope_attested_concentration_private"]["storage"], "NONE")
        self.assertNotIn("CEO_ATTESTS_VISIBLE_SCOPE_AS_DISPLAYED",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))


if __name__ == "__main__":
    unittest.main()
