"""Synthetic v1.4 regression: client-attested Blossom view is never brokerage proof.

Run in a trusted repository checkout:
    python -m unittest -v tests.test_ai_native_workflow_v14_attestation
No real positions, accounts, source URLs, or private values appear here.
"""
from copy import deepcopy
import unittest

from ai_native.attested_visible_concentration import (
    prepare_attested_visible_concentration,
    render_attested_visible_concentration,
)


class WorkflowV14AttestationTests(unittest.TestCase):
    def reference(self, weights, *, coverage_complete=True, observation_date="2026-10-29"):
        return {
            "status": "PUBLIC_REFERENCE_DESCRIPTIVE_ONLY",
            "ownership_authority": "NOT_ESTABLISHED",
            "source_authentication": "NOT_PERFORMED",
            "private_holdings_import": "NONE",
            "allocation_authority": "NONE",
            "trading_authority": "NONE",
            "storage": "NONE",
            "analysis_id": "SYN-V14-001",
            "analysis_as_of": "2026-10-30",
            "observation_as_of": observation_date,
            "coverage": {
                k: coverage_complete for k in (
                    "all_rows_visible", "other_group_expanded_or_absent",
                    "cash_visible", "weights_comparable",
                    "account_filter_visible", "sync_date_visible"
                )
            },
            "positions_private": [
                {"weight_pct": weight, "visibility": "VISIBLE"}
                for weight in weights
            ],
            "displayed_weight_sum_pct": str(sum(map(float, weights))),
        }

    @staticmethod
    def attestation():
        return {
            "analysis_id": "SYN-V14-001",
            "analysis_as_of": "2026-10-30",
            "scope_attestation": "CEO_ATTESTS_VISIBLE_SCOPE_AS_DISPLAYED",
        }

    def test_twenty_line_100_point_3_view_is_not_normalized_or_promoted(self):
        # Fictitious numbers, structurally analogous to a rounded UI view.
        reference = self.reference(["5.00"] * 19 + ["5.30"])
        original = deepcopy(reference)
        result = prepare_attested_visible_concentration(reference, self.attestation())
        self.assertEqual(reference, original)
        self.assertEqual(result["displayed_sum_pct"], "100.30")
        self.assertEqual(result["status"], "DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED")
        self.assertIn("displayed_sum_not_100_within_rounding", result["blockers"])
        self.assertIsNone(result["top_five_visible_lines_pct"])
        self.assertEqual(result["monetary_denominator"], "UNKNOWN")
        self.assertEqual(result["brokerage_ownership"], "NOT_PROVEN")
        self.assertEqual(result["post_contribution_weights"], "UNAVAILABLE")
        self.assertEqual(result["storage"], "NONE")

    def test_complete_synthetic_display_can_be_conditionally_described(self):
        reference = self.reference(["40.00", "30.00", "20.00", "10.00"])
        reference["displayed_weight_sum_pct"] = "100.00"
        result = prepare_attested_visible_concentration(reference, self.attestation())
        self.assertEqual(result["status"], "CONDITIONAL_ATTESTED_DISPLAY_VIEW_CONCENTRATION")
        self.assertEqual(result["top_one_visible_line_pct"], "40.00")
        self.assertEqual(result["top_five_visible_lines_pct"], "100.00")
        self.assertEqual(result["denominator"], "DISPLAYED_VIEW_ONLY")
        self.assertIn("aucune allocation", render_attested_visible_concentration(result))

    def test_unknown_sync_date_prevents_complete_scope_claim(self):
        reference = self.reference(["60.00", "40.00"], observation_date="UNKNOWN")
        reference["displayed_weight_sum_pct"] = "100.00"
        result = prepare_attested_visible_concentration(reference, self.attestation())
        self.assertEqual(result["status"], "DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED")
        self.assertIn("observation_as_of", result["blockers"])
        self.assertEqual(result["personal_account_verification"], "NOT_PERFORMED")

    def test_case_mismatch_and_authority_promotion_fail_closed(self):
        reference = self.reference(["60.00", "40.00"])
        reference["displayed_weight_sum_pct"] = "100.00"
        bad_attestation = self.attestation()
        bad_attestation["analysis_id"] = "DIFFERENT"
        with self.assertRaisesRegex(ValueError, "CASE_OR_SCOPE"):
            prepare_attested_visible_concentration(reference, bad_attestation)
        bad_reference = deepcopy(reference)
        bad_reference["ownership_authority"] = "BROKER_VERIFIED"
        with self.assertRaisesRegex(ValueError, "REFERENCE_AUTHORITY_INVALID"):
            prepare_attested_visible_concentration(bad_reference, self.attestation())


if __name__ == "__main__":
    unittest.main()
