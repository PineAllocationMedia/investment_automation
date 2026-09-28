"""Pure proposal packaging for explicit Expected Return policy candidates."""
from __future__ import annotations

from dataclasses import dataclass, field

from .expected_return_policy import (
    DistributionPolicy,
    DistributionRule,
    MatureGrowthPolicy,
    TerminalValuationPolicy,
    canonical_hash,
    require,
    text,
    validate_policy,
)


EXPECTED_RETURN_POLICY_PROPOSAL_CONTRACT_VERSION = (
    "2026-09-28-expected-return-policy-proposal-v1"
)
PROPOSAL_ONLY = "PROPOSAL_ONLY"

PROPOSAL_LIMITATIONS = (
    "NO_OBSERVED_PRICE_OR_QUOTE_SEMANTICS",
    "NO_DIVIDEND_OR_NONPAYER_VERIFICATION",
    "NO_ORDINARY_COMPOUNDER_QUALIFICATION",
    "NO_SHARE_BASIS_QUALIFICATION",
    "NO_REPORTING_SUBJECT_QUALIFICATION",
    "NO_EXPECTED_RETURN_ADMISSION",
    "NO_INVESTMENT_RECOMMENDATION",
    "NO_AUTHORITATIVE_ECONOMIC_VALUES",
)


@dataclass(frozen=True, slots=True)
class ExpectedReturnPolicyProposal:
    """One immutable candidate set; it carries no policy authority."""

    proposal_id: str
    mature_policy: MatureGrowthPolicy
    terminal_policy: TerminalValuationPolicy
    payer_distribution_policy: DistributionPolicy
    nonpayer_distribution_policy: DistributionPolicy
    rationale: str | None = None
    contract_version: str = field(
        init=False, default=EXPECTED_RETURN_POLICY_PROPOSAL_CONTRACT_VERSION
    )

    def __post_init__(self) -> None:
        _validate_proposal(self)

    @property
    def policy_hashes(self) -> tuple[tuple[str, str], ...]:
        _validate_proposal(self)
        return _policy_hashes(self)

    @property
    def proposal_hash(self) -> str:
        _validate_proposal(self)
        return canonical_hash(
            (
                "ExpectedReturnPolicyProposal",
                self.contract_version,
                self.proposal_id,
                self.rationale,
                _policy_hashes(self),
            )
        )


@dataclass(frozen=True, slots=True)
class ExpectedReturnPolicyProposalAssessment:
    """Closed proposal-only result with explicit nonclaims."""

    proposal: ExpectedReturnPolicyProposal
    status: str = field(init=False, default=PROPOSAL_ONLY)
    limitations: tuple[str, ...] = field(init=False, default=PROPOSAL_LIMITATIONS)

    def __post_init__(self) -> None:
        require(
            type(self.proposal) is ExpectedReturnPolicyProposal,
            "Typed ExpectedReturnPolicyProposal required",
        )
        _validate_proposal(self.proposal)

    @property
    def proposal_hash(self) -> str:
        return self.proposal.proposal_hash


def _policy_hashes(
    proposal: ExpectedReturnPolicyProposal,
) -> tuple[tuple[str, str], ...]:
    return (
        ("mature_growth", proposal.mature_policy.policy_hash),
        ("terminal_valuation", proposal.terminal_policy.policy_hash),
        ("payer_distribution", proposal.payer_distribution_policy.policy_hash),
        ("nonpayer_distribution", proposal.nonpayer_distribution_policy.policy_hash),
    )


def _applicability(policy) -> tuple[str, str, str, str, str]:
    app = policy.applicability
    return (
        app.profile,
        app.currency,
        app.accounting_basis,
        app.valid_from,
        app.valid_through,
    )


def _validate_proposal(proposal: ExpectedReturnPolicyProposal) -> None:
    require(
        type(proposal) is ExpectedReturnPolicyProposal,
        "Typed ExpectedReturnPolicyProposal required",
    )
    require(
        proposal.contract_version == EXPECTED_RETURN_POLICY_PROPOSAL_CONTRACT_VERSION,
        "Unsupported policy proposal contract",
    )
    text(proposal.proposal_id, "proposal_id")
    require(
        proposal.rationale is None or type(proposal.rationale) is str,
        "Proposal rationale must be absent or text",
    )
    if proposal.rationale is not None:
        text(proposal.rationale, "proposal rationale")

    policies = (
        proposal.mature_policy,
        proposal.terminal_policy,
        proposal.payer_distribution_policy,
        proposal.nonpayer_distribution_policy,
    )
    expected_types = (
        MatureGrowthPolicy,
        TerminalValuationPolicy,
        DistributionPolicy,
        DistributionPolicy,
    )
    for policy, expected_type in zip(policies, expected_types):
        require(type(policy) is expected_type, "Exact existing policy type required")
        validate_policy(policy)

    reference_applicability = _applicability(proposal.mature_policy)
    require(
        all(_applicability(policy) == reference_applicability for policy in policies[1:]),
        "All proposal policies must have identical applicability",
    )
    require(
        proposal.payer_distribution_policy.rule
        is DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT,
        "Payer policy must use CONSTANT_MATCHED_ORDINARY_PAYOUT",
    )
    require(
        proposal.nonpayer_distribution_policy.rule
        is DistributionRule.CONTINUED_VERIFIED_NONPAYER,
        "Nonpayer policy must use CONTINUED_VERIFIED_NONPAYER",
    )

    policy_ids = tuple(policy.policy_id for policy in policies)
    require(len(set(policy_ids)) == len(policy_ids), "Duplicate policy ID")
    assumption_ids = tuple(policy.assumption_id for policy in policies)
    require(
        len(set(assumption_ids)) == len(assumption_ids),
        "Duplicate assumption ID",
    )
    hashes = tuple(policy_hash for _, policy_hash in _policy_hashes(proposal))
    require(len(set(hashes)) == len(hashes), "Duplicate policy hash")


def build_expected_return_policy_proposal(
    *,
    proposal_id: str,
    mature_policy: MatureGrowthPolicy,
    terminal_policy: TerminalValuationPolicy,
    payer_distribution_policy: DistributionPolicy,
    nonpayer_distribution_policy: DistributionPolicy,
    rationale: str | None = None,
) -> ExpectedReturnPolicyProposalAssessment:
    """Validate and package one complete candidate set as proposal-only."""

    proposal = ExpectedReturnPolicyProposal(
        proposal_id=proposal_id,
        mature_policy=mature_policy,
        terminal_policy=terminal_policy,
        payer_distribution_policy=payer_distribution_policy,
        nonpayer_distribution_policy=nonpayer_distribution_policy,
        rationale=rationale,
    )
    _validate_proposal(proposal)
    return ExpectedReturnPolicyProposalAssessment(proposal=proposal)
