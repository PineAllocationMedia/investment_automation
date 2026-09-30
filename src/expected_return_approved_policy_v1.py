"""Owner-approved PR5D2 Expected Return policy artifact.

Changing any content requires a new reviewed version and proposal-hash pin.
"""
from __future__ import annotations

import math

from .expected_return_policy import (
    EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
    EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION,
    Applicability,
    DistributionPolicy,
    DistributionRule,
    MatureGrowthPolicy,
    ScenarioValues,
    TerminalValuationPolicy,
)
from .expected_return_policy_governance import (
    ExpectedReturnPolicyProposalAssessment,
    build_expected_return_policy_proposal,
)

OWNER_APPROVED_POLICY_VERSION = "2026-09-29-owner-approved-ordinary-nonpayer-v1"
OWNER_APPROVED_PROPOSAL_HASH = (
    "e24728b937e8c57de56c530303eeb102595410fd5bf96f0b129cd0a61cafbf23"
)

APPLICABILITY = Applicability(
    profile="ORDINARY_COMPOUNDER",
    currency="USD",
    accounting_basis="US_GAAP",
    valid_from="2026-09-29",
    valid_through="9999-12-31",
)

MATURE_GROWTH_DECIMAL_ANCHORS = ScenarioValues(0.0, 0.03, 0.05)
MATURE_GROWTH_LOG_ANCHORS = ScenarioValues(
    math.log1p(MATURE_GROWTH_DECIMAL_ANCHORS.bear),
    math.log1p(MATURE_GROWTH_DECIMAL_ANCHORS.base),
    math.log1p(MATURE_GROWTH_DECIMAL_ANCHORS.bull),
)

MATURE_GROWTH_POLICY = MatureGrowthPolicy(
    policy_id="PAM_ER_MATURE_GROWTH_ORDINARY_USD_US_GAAP_V1",
    schema_version=EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
    applicability=APPLICABILITY,
    log_growth=MATURE_GROWTH_LOG_ANCHORS,
    rationale=("Owner-governed mature scenario anchors: decimal growth 0%, 3%, and 5%, "
               "stored as the exact binary64 log1p values required by PR4B1."),
    assumption_id="PAM_ER_MATURE_GROWTH_LOG_ANCHORS_2026_09_29_V1",
)

TERMINAL_VALUATION_POLICY = TerminalValuationPolicy(
    policy_id="PAM_ER_TERMINAL_PE_ORDINARY_USD_US_GAAP_V1",
    schema_version=EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION,
    applicability=APPLICABILITY,
    terminal_pe=ScenarioValues(12.0, 16.0, 20.0),
    rationale=("Owner-governed independent terminal P/E anchors of 12x, 16x, and 20x; "
               "not selected dynamically from issuer or market characteristics."),
    assumption_id="PAM_ER_TERMINAL_PE_ANCHORS_2026_09_29_V1",
)

PAYER_DISTRIBUTION_POLICY = DistributionPolicy(
    policy_id="PAM_ER_MATCHED_ORDINARY_PAYOUT_USD_US_GAAP_V1",
    schema_version=EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
    applicability=APPLICABILITY,
    rule=DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT,
    rationale=("Required complete-proposal payer role retained for future reviewed coverage; "
               "PR5D2 does not activate a real payer route."),
    assumption_id="PAM_ER_MATCHED_ORDINARY_PAYOUT_2026_09_29_V1",
)

NONPAYER_DISTRIBUTION_POLICY = DistributionPolicy(
    policy_id="PAM_ER_CONTINUED_VERIFIED_NONPAYER_USD_US_GAAP_V1",
    schema_version=EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
    applicability=APPLICABILITY,
    rule=DistributionRule.CONTINUED_VERIFIED_NONPAYER,
    rationale=("Owner-approved first real distribution route: continue a freshly verified "
               "latest-period nonpayer state without inventing a distribution."),
    assumption_id="PAM_ER_CONTINUED_NONPAYER_2026_09_29_V1",
)


def _construct() -> ExpectedReturnPolicyProposalAssessment:
    return build_expected_return_policy_proposal(
        proposal_id=OWNER_APPROVED_POLICY_VERSION,
        mature_policy=MATURE_GROWTH_POLICY,
        terminal_policy=TERMINAL_VALUATION_POLICY,
        payer_distribution_policy=PAYER_DISTRIBUTION_POLICY,
        nonpayer_distribution_policy=NONPAYER_DISTRIBUTION_POLICY,
        rationale=("Owner-approved PR5D2 policy bundle for the first USD, US-GAAP, "
                   "ORDINARY_COMPOUNDER route."),
    )


def get_owner_approved_policy_proposal() -> ExpectedReturnPolicyProposalAssessment:
    assessment = _construct()
    if assessment.proposal_hash != OWNER_APPROVED_PROPOSAL_HASH:
        raise RuntimeError("Owner-approved Expected Return policy proposal hash mismatch")
    return assessment
