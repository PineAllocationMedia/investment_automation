from dataclasses import replace
import math
import unittest
from unittest.mock import patch

from src import expected_return_approved_policy_v1 as approved
from src.expected_return_policy import DistributionRule


class ApprovedPolicyTests(unittest.TestCase):
    def test_exact_owner_approved_artifact_and_pin(self):
        assessment = approved.get_owner_approved_policy_proposal()
        proposal = assessment.proposal
        self.assertEqual(assessment.proposal_hash,
                         "e24728b937e8c57de56c530303eeb102595410fd5bf96f0b129cd0a61cafbf23")
        self.assertEqual(proposal.proposal_id, approved.OWNER_APPROVED_POLICY_VERSION)
        self.assertEqual(proposal.mature_policy.log_growth.bear, math.log1p(0.00))
        self.assertEqual(proposal.mature_policy.log_growth.base, math.log1p(0.03))
        self.assertEqual(proposal.mature_policy.log_growth.bull, math.log1p(0.05))
        self.assertEqual(tuple(vars for vars in (
            proposal.terminal_policy.terminal_pe.bear,
            proposal.terminal_policy.terminal_pe.base,
            proposal.terminal_policy.terminal_pe.bull)), (12.0, 16.0, 20.0))
        app = proposal.mature_policy.applicability
        self.assertEqual((app.profile, app.currency, app.accounting_basis,
                          app.valid_from, app.valid_through),
                         ("ORDINARY_COMPOUNDER", "USD", "US_GAAP",
                          "2026-09-29", "9999-12-31"))
        self.assertIs(proposal.payer_distribution_policy.rule,
                      DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT)
        self.assertIs(proposal.nonpayer_distribution_policy.rule,
                      DistributionRule.CONTINUED_VERIFIED_NONPAYER)
        self.assertEqual(dict(proposal.policy_hashes), {
            "mature_growth": "e19dda11ff8da0990b100da92f4f1a99eb0fe00b830d20672e551f731274aab9",
            "terminal_valuation": "034728d883692f0c3ad379699a6be0a09d3022e8257e4875b5487a0f4d6b0e87",
            "payer_distribution": "28d7692e11c328824971b2fc07f305d7d59181997033a0711de755ac00f8fe74",
            "nonpayer_distribution": "49fa1381b249930b3e0e0e08945cd493a69d1a3d342a714673ed1e12bf72d9a0",
        })

    def test_any_reviewed_policy_content_change_breaks_the_pin(self):
        changed = replace(
            approved.MATURE_GROWTH_POLICY,
            rationale=approved.MATURE_GROWTH_POLICY.rationale + " changed",
        )
        with patch.object(approved, "MATURE_GROWTH_POLICY", changed), \
             self.assertRaisesRegex(RuntimeError, "proposal hash mismatch"):
            approved.get_owner_approved_policy_proposal()


if __name__ == "__main__":
    unittest.main()
