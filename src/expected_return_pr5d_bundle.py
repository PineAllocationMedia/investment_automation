"""Pure PR5D2 composite replay; no PR4B1 roots or Expected Return calculation."""
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from economic_facts.nasdaq_listed_archive import NasdaqListedArchive
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_current_eps_comparability_qualification import ComparableEPSPeriodDecision
from economic_facts.sec_current_verified_nonpayer import (
    RouteLocalVerifiedNonpayerQualification,
    RouteLocalVerifiedNonpayerStatus,
    SecCurrentVerifiedNonpayerRequest,
    qualify_sec_current_verified_nonpayer,
)
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_ordinary_compounder_profile import (
    OrdinaryCompounderMethodProfileQualification,
    OrdinaryCompounderProfileStatus,
    SecOrdinaryCompounderProfileRequest,
    qualify_sec_ordinary_compounder_profile,
)
from economic_facts.sec_quote_eps_basis_bridge import (
    ReconciledBasisAction,
    SecQuoteEPSBasisBridgeRequest,
    ShareBasisBridgeQualification,
    ShareBasisBridgeStatus,
    qualify_sec_quote_eps_basis_bridge,
)
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_ticker_exchange_archive import SecTickerExchangeArchive
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from economic_facts.yahoo_split_history_archive import YahooSplitHistoryArchive

from .expected_return_approved_policy_v1 import (
    OWNER_APPROVED_POLICY_VERSION,
    OWNER_APPROVED_PROPOSAL_HASH,
    get_owner_approved_policy_proposal,
)
from .expected_return_policy import DistributionRule, applicable

CONTRACT_VERSION = "2026-09-29-pr5d2-real-expected-return-roots-v1"
ASSEMBLER_VERSION = "2026-09-29-pr5d2-fresh-replay-bundle-v1"
_HASH = re.compile(r"[0-9a-f]{64}")


class PR5D2BundleError(ValueError):
    """Invalid closed request or identity projection."""


class PR5D2BundleStatus(StrEnum):
    PR5D_REAL_ROOTS_ESTABLISHED = "PR5D_REAL_ROOTS_ESTABLISHED"
    PR5D_ROOTS_UNAVAILABLE = "PR5D_ROOTS_UNAVAILABLE"
    PR5D_ROOTS_UNSUPPORTED = "PR5D_ROOTS_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class PR5D2BundleReason(StrEnum):
    BASIS_BRIDGE_NOT_ESTABLISHED = "BASIS_BRIDGE_NOT_ESTABLISHED"
    NONPAYER_NOT_ESTABLISHED = "NONPAYER_NOT_ESTABLISHED"
    PROFILE_NOT_ESTABLISHED = "PROFILE_NOT_ESTABLISHED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    ROUTE_IDENTITY_MISMATCH = "ROUTE_IDENTITY_MISMATCH"
    UPSTREAM_COMPARABILITY_MISMATCH = "UPSTREAM_COMPARABILITY_MISMATCH"
    CURRENCY_OR_ACCOUNTING_BASIS_MISMATCH = "CURRENCY_OR_ACCOUNTING_BASIS_MISMATCH"
    APPROVED_POLICY_HASH_MISMATCH = "APPROVED_POLICY_HASH_MISMATCH"
    APPROVED_POLICY_NOT_APPLICABLE = "APPROVED_POLICY_NOT_APPLICABLE"
    NONPAYER_POLICY_NOT_SELECTED = "NONPAYER_POLICY_NOT_SELECTED"


LIMITATIONS = (
    "NO_PR4B1_OBSERVED_PRICE_ROOT",
    "NO_PR4B1_REPORTED_DILUTED_EPS_ROOTS",
    "NO_PR4B1_VERIFIED_NONPAYER_ROOT",
    "NO_EXPECTED_RETURN_CALCULATION",
    "NO_FINAL_ECONOMIC_ADMISSION",
    "PR5E_FINAL_ADMISSION_REQUIRED",
    "NO_RECOMMENDATION_OR_ALLOCATION",
)


@dataclass(frozen=True, slots=True)
class PR5D2RealExpectedReturnRootsRequest:
    basis_bridge_request: SecQuoteEPSBasisBridgeRequest
    expected_basis_bridge_semantic_id: str
    expected_basis_bridge_evidence_id: str
    nonpayer_request: SecCurrentVerifiedNonpayerRequest
    expected_nonpayer_semantic_id: str
    expected_nonpayer_evidence_id: str
    profile_request: SecOrdinaryCompounderProfileRequest
    expected_profile_semantic_id: str
    expected_profile_evidence_id: str

    def __post_init__(self):
        if (type(self.basis_bridge_request) is not SecQuoteEPSBasisBridgeRequest
                or type(self.nonpayer_request) is not SecCurrentVerifiedNonpayerRequest
                or type(self.profile_request) is not SecOrdinaryCompounderProfileRequest):
            raise PR5D2BundleError("Exact typed qualification selectors required")
        for field in fields(self):
            if field.name.startswith("expected_"):
                value = getattr(self, field.name)
                if type(value) is not str or _HASH.fullmatch(value) is None:
                    raise PR5D2BundleError("Exact replay identities required")


@dataclass(frozen=True, slots=True)
class PR5D2RealExpectedReturnRoots:
    contract_version: str
    assembler_version: str
    status: PR5D2BundleStatus
    reasons: tuple[PR5D2BundleReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    canonical_selected_common_class: str | None
    period_decisions: tuple[ComparableEPSPeriodDecision, ...]
    historical_qualified_basis_identity: str | None
    quote_price: Decimal | None
    quote_timestamp: str | None
    quote_currency: str | None
    quote_unit: str | None
    accounting_basis: str | None
    basis_multiplier_numerator: int | None
    basis_multiplier_denominator: int | None
    reconciled_corporate_actions: tuple[ReconciledBasisAction, ...]
    nonpayer_period_start: str | None
    nonpayer_period_end: str | None
    nonpayer_status_identity: str | None
    ordinary_compounder_profile_identity: str | None
    approved_policy_version: str
    approved_proposal_hash: str
    selected_nonpayer_distribution_policy_hash: str
    mature_policy_hash: str
    terminal_policy_hash: str
    upstream_semantic_ids: tuple[str, ...]
    upstream_evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    basis_bridge: ShareBasisBridgeQualification
    nonpayer: RouteLocalVerifiedNonpayerQualification
    profile: OrdinaryCompounderMethodProfileQualification

    @property
    def semantic_id(self):
        return _identity("bundle-semantics", {
            "contract": self.contract_version,
            "assembler": self.assembler_version,
            "status": self.status,
            "reasons": self.reasons,
            "issuer_key": self.route_local_issuer_key,
            "security_key": self.route_local_security_key,
            "class": self.canonical_selected_common_class,
            "period_decisions": self.period_decisions,
            "historical_basis": self.historical_qualified_basis_identity,
            "quote_price": self.quote_price,
            "quote_timestamp": self.quote_timestamp,
            "quote_currency": self.quote_currency,
            "quote_unit": self.quote_unit,
            "accounting_basis": self.accounting_basis,
            "basis_multiplier": (self.basis_multiplier_numerator,
                                 self.basis_multiplier_denominator),
            "actions": self.reconciled_corporate_actions,
            "nonpayer_period": (self.nonpayer_period_start, self.nonpayer_period_end),
            "nonpayer_status_identity": self.nonpayer_status_identity,
            "profile_identity": self.ordinary_compounder_profile_identity,
            "approved_policy_version": self.approved_policy_version,
            "approved_proposal_hash": self.approved_proposal_hash,
            "selected_nonpayer_policy_hash": self.selected_nonpayer_distribution_policy_hash,
            "mature_policy_hash": self.mature_policy_hash,
            "terminal_policy_hash": self.terminal_policy_hash,
            "upstream_semantic_ids": self.upstream_semantic_ids,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("bundle-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_ids": self.upstream_evidence_ids,
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        sign, digits, exponent = value.as_tuple()
        return {"decimal_tuple": [sign, list(digits), exponent]}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise PR5D2BundleError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((ASSEMBLER_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _upstream_accounting_basis(comparability):
    """Read the accounting basis from PR5B's resolved EPS series evidence."""
    current = (comparability.upstream_security_eps.upstream_registered_listing_bridge
               .temporal_boundary.current_evidence)
    series = current.resolution.series
    if series is None:
        return None
    if ((series.namespace, series.concept, series.unit, series.accounting_basis)
            != ("us-gaap", "EarningsPerShareDiluted", "USD/shares", "US_GAAP")):
        return None
    return series.accounting_basis


def assemble_expected_return_pr5d_bundle(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    quote_archive: YahooQuoteArchive,
    split_history_archive: YahooSplitHistoryArchive,
    request: PR5D2RealExpectedReturnRootsRequest,
) -> PR5D2RealExpectedReturnRoots:
    """Freshly replay each PR5D2 qualification and assemble inspectable roots only."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(quote_archive) is not YahooQuoteArchive
            or type(split_history_archive) is not YahooSplitHistoryArchive
            or type(request) is not PR5D2RealExpectedReturnRootsRequest):
        raise PR5D2BundleError("Exact typed archives/request required")
    bridge = qualify_sec_quote_eps_basis_bridge(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, quote_archive,
        split_history_archive, request.basis_bridge_request)
    nonpayer = qualify_sec_current_verified_nonpayer(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, request.nonpayer_request)
    profile = qualify_sec_ordinary_compounder_profile(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, request.profile_request)
    policy = get_owner_approved_policy_proposal()
    proposal = policy.proposal
    reasons = set()
    if bridge.status is not ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED:
        reasons.add(PR5D2BundleReason.BASIS_BRIDGE_NOT_ESTABLISHED)
    if nonpayer.status is not RouteLocalVerifiedNonpayerStatus.VERIFIED_NONPAYER_ESTABLISHED:
        reasons.add(PR5D2BundleReason.NONPAYER_NOT_ESTABLISHED)
    if profile.status is not OrdinaryCompounderProfileStatus.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED:
        reasons.add(PR5D2BundleReason.PROFILE_NOT_ESTABLISHED)
    if (bridge.semantic_id != request.expected_basis_bridge_semantic_id
            or bridge.evidence_id != request.expected_basis_bridge_evidence_id
            or nonpayer.semantic_id != request.expected_nonpayer_semantic_id
            or nonpayer.evidence_id != request.expected_nonpayer_evidence_id
            or profile.semantic_id != request.expected_profile_semantic_id
            or profile.evidence_id != request.expected_profile_evidence_id):
        reasons.add(PR5D2BundleReason.REPLAY_IDENTITY_MISMATCH)
    identities = {
        (bridge.route_local_issuer_key, bridge.route_local_security_key),
        (nonpayer.route_local_issuer_key, nonpayer.route_local_security_key),
        (profile.upstream_comparability.route_local_issuer_key,
         profile.upstream_comparability.route_local_security_key),
    }
    if len(identities) != 1:
        reasons.add(PR5D2BundleReason.ROUTE_IDENTITY_MISMATCH)
    comparabilities = (
        bridge.upstream_comparability,
        nonpayer.upstream_comparability,
        profile.upstream_comparability,
    )
    comparability_requests = (
        request.basis_bridge_request.comparability_request,
        request.nonpayer_request.comparability_request,
        request.profile_request.comparability_request,
    )
    if (len({item.semantic_id for item in comparabilities}) != 1
            or len({item.evidence_id for item in comparabilities}) != 1
            or len(set(comparability_requests)) != 1):
        reasons.add(PR5D2BundleReason.UPSTREAM_COMPARABILITY_MISMATCH)
    quote = bridge.upstream_quote
    accounting_basis = _upstream_accounting_basis(bridge.upstream_comparability)
    if (quote.currency != "USD" or accounting_basis != "US_GAAP"
            or profile.profile != "ORDINARY_COMPOUNDER"):
        reasons.add(PR5D2BundleReason.CURRENCY_OR_ACCOUNTING_BASIS_MISMATCH)
    if (policy.proposal_hash != OWNER_APPROVED_PROPOSAL_HASH
            or proposal.proposal_id != OWNER_APPROVED_POLICY_VERSION):
        reasons.add(PR5D2BundleReason.APPROVED_POLICY_HASH_MISMATCH)
    try:
        quote_date = datetime.fromisoformat(quote.provider_market_timestamp.replace(
            "Z", "+00:00")).date()
    except (AttributeError, ValueError):
        quote_date = None
    policies = (
        proposal.mature_policy, proposal.terminal_policy,
        proposal.nonpayer_distribution_policy,
    )
    if quote_date is None or not all(applicable(
            item, currency="USD", accounting_basis=accounting_basis, as_of=quote_date)
            for item in policies):
        reasons.add(PR5D2BundleReason.APPROVED_POLICY_NOT_APPLICABLE)
    if (proposal.nonpayer_distribution_policy.rule
            is not DistributionRule.CONTINUED_VERIFIED_NONPAYER):
        reasons.add(PR5D2BundleReason.NONPAYER_POLICY_NOT_SELECTED)

    conflict = (PR5D2BundleReason.REPLAY_IDENTITY_MISMATCH in reasons
                or PR5D2BundleReason.ROUTE_IDENTITY_MISMATCH in reasons
                or PR5D2BundleReason.UPSTREAM_COMPARABILITY_MISMATCH in reasons
                or bridge.status is ShareBasisBridgeStatus.SOURCE_CONFLICT
                or nonpayer.status is RouteLocalVerifiedNonpayerStatus.SOURCE_CONFLICT
                or profile.status is OrdinaryCompounderProfileStatus.SOURCE_CONFLICT)
    unsupported = (
        bridge.status is ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED
        or nonpayer.status is RouteLocalVerifiedNonpayerStatus.NONPAYER_UNSUPPORTED
        or profile.status is OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED)
    if conflict:
        status = PR5D2BundleStatus.SOURCE_CONFLICT
    elif unsupported:
        status = PR5D2BundleStatus.PR5D_ROOTS_UNSUPPORTED
    elif reasons:
        status = PR5D2BundleStatus.PR5D_ROOTS_UNAVAILABLE
    else:
        status = PR5D2BundleStatus.PR5D_REAL_ROOTS_ESTABLISHED
    positive = status is PR5D2BundleStatus.PR5D_REAL_ROOTS_ESTABLISHED
    upstream_semantics = tuple(sorted({
        bridge.semantic_id, bridge.upstream_comparability.semantic_id,
        bridge.upstream_quote.semantic_id, bridge.recent_share_basis_source.semantic_id,
        bridge.yahoo_split_history.semantic_id, nonpayer.semantic_id,
        nonpayer.upstream_nonpayer_source.semantic_hash, profile.semantic_id,
        OWNER_APPROVED_PROPOSAL_HASH,
    }))
    upstream_evidence = tuple(sorted({
        bridge.evidence_id, bridge.upstream_comparability.evidence_id,
        bridge.upstream_quote.evidence_id, bridge.recent_share_basis_source.evidence_id,
        bridge.yahoo_split_history.evidence_id, nonpayer.evidence_id,
        nonpayer.upstream_nonpayer_source.evidence_hash, profile.evidence_id,
    }))
    return PR5D2RealExpectedReturnRoots(
        CONTRACT_VERSION, ASSEMBLER_VERSION, status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        bridge.route_local_issuer_key if positive else None,
        bridge.route_local_security_key if positive else None,
        nonpayer.canonical_source_class_label if positive else None,
        bridge.upstream_comparability.period_decisions,
        bridge.historical_basis_identity if positive else None,
        quote.price if positive else None,
        quote.provider_market_timestamp if positive else None,
        quote.currency if positive else None,
        quote.unit if positive else None,
        accounting_basis if positive else None,
        bridge.eps_to_quote_basis_multiplier_numerator if positive else None,
        bridge.eps_to_quote_basis_multiplier_denominator if positive else None,
        bridge.reconciled_actions,
        nonpayer.period_start if positive else None,
        nonpayer.period_end if positive else None,
        nonpayer.semantic_id if positive else None,
        profile.semantic_id if positive else None,
        OWNER_APPROVED_POLICY_VERSION,
        OWNER_APPROVED_PROPOSAL_HASH,
        proposal.nonpayer_distribution_policy.policy_hash,
        proposal.mature_policy.policy_hash,
        proposal.terminal_policy.policy_hash,
        upstream_semantics, upstream_evidence, LIMITATIONS,
        bridge, nonpayer, profile,
    )
