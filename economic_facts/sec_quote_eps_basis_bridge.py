"""Free bounded multi-source bridge from PR5C EPS basis to PR5D1 quote basis."""
from collections import Counter
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from fractions import Fraction
import hashlib
import json
import re

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_eps_comparability_qualification import (
    ComparabilityOutcome,
    RealEPSComparabilityQualification,
    SecCurrentEPSComparabilityRequest,
    qualify_sec_current_eps_comparability,
)
from .sec_filing_archive import SecFilingArchive
from .sec_share_basis_source_claims import (
    CorporateActionKind,
    CorporateActionLifecycle,
    SecShareBasisSourceAssessment,
    SecShareBasisSourceRequest,
    SecurityClassSourceScope,
    ShareBasisSourceIssue,
    build_sec_share_basis_source_foundation,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_submissions_inventory import InventoryStatus
from .sec_ticker_exchange_archive import SecTickerExchangeArchive
from .yahoo_current_quote import (
    CurrentQuoteStatus,
    QualifiedCurrentQuote,
    YahooCurrentQuoteQualificationRequest,
    qualify_yahoo_current_quote,
)
from .yahoo_quote_archive import YahooQuoteArchive
from .yahoo_split_history import (
    SplitHistoryStatus,
    YahooSplitEvent,
    YahooSplitHistoryExtraction,
    extract_yahoo_split_history,
)
from .yahoo_split_history_archive import YahooSplitHistoryArchive

CONTRACT_VERSION = "2026-09-29-free-bounded-share-basis-bridge-v1"
QUALIFIER_VERSION = "2026-09-29-sec-yahoo-action-reconciliation-v1"
QUALIFICATION_MODE = "FREE_BOUNDED_MULTI_SOURCE_SHARE_BASIS_BRIDGE_V1"
SUPPORTED_FORMS = frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A"))
SUPPORTED_ACTIONS = frozenset((
    CorporateActionKind.STOCK_SPLIT,
    CorporateActionKind.REVERSE_STOCK_SPLIT,
    CorporateActionKind.STOCK_DIVIDEND,
))
_HASH = re.compile(r"[0-9a-f]{64}")


class ShareBasisBridgeError(ValueError):
    """Invalid closed request or identity projection."""


class ShareBasisBridgeStatus(StrEnum):
    BASIS_BRIDGE_ESTABLISHED = "BASIS_BRIDGE_ESTABLISHED"
    BASIS_BRIDGE_UNAVAILABLE = "BASIS_BRIDGE_UNAVAILABLE"
    BASIS_BRIDGE_UNSUPPORTED = "BASIS_BRIDGE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class ShareBasisBridgeReason(StrEnum):
    PR5C_NOT_ESTABLISHED = "PR5C_NOT_ESTABLISHED"
    PR5D1_NOT_ESTABLISHED = "PR5D1_NOT_ESTABLISHED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    ROUTE_IDENTITY_MISMATCH = "ROUTE_IDENTITY_MISMATCH"
    DIRECT_LISTING_ROUTE_MISMATCH = "DIRECT_LISTING_ROUTE_MISMATCH"
    PRESENTATION_ACCEPTANCE_MISSING = "PRESENTATION_ACCEPTANCE_MISSING"
    PRESENTATION_ACCEPTANCE_DUPLICATE = "PRESENTATION_ACCEPTANCE_DUPLICATE"
    PRESENTATION_AFTER_QUOTE = "PRESENTATION_AFTER_QUOTE"
    FILING_REFERENCE_CLOSURE_INCOMPLETE = "FILING_REFERENCE_CLOSURE_INCOMPLETE"
    RECENT_INVENTORY_NOT_MONOTONIC_CONTINUATION = (
        "RECENT_INVENTORY_NOT_MONOTONIC_CONTINUATION"
    )
    RECENT_SEC_SNAPSHOT_BEFORE_QUOTE_CAPTURE = (
        "RECENT_SEC_SNAPSHOT_BEFORE_QUOTE_CAPTURE"
    )
    RECENT_FILING_WINDOW_INCOMPLETE = "RECENT_FILING_WINDOW_INCOMPLETE"
    RECENT_SUBMISSIONS_CAPTURE_AFTER_BOUNDARY = "RECENT_SUBMISSIONS_CAPTURE_AFTER_BOUNDARY"
    RECENT_FILING_CAPTURE_AFTER_BOUNDARY = "RECENT_FILING_CAPTURE_AFTER_BOUNDARY"
    SHARE_BASIS_SOURCE_UNAVAILABLE = "SHARE_BASIS_SOURCE_UNAVAILABLE"
    SHARE_BASIS_SOURCE_UNSUPPORTED = "SHARE_BASIS_SOURCE_UNSUPPORTED"
    YAHOO_SPLIT_HISTORY_UNAVAILABLE = "YAHOO_SPLIT_HISTORY_UNAVAILABLE"
    YAHOO_SPLIT_HISTORY_UNSUPPORTED = "YAHOO_SPLIT_HISTORY_UNSUPPORTED"
    SPLIT_HISTORY_INTERVAL_MISMATCH = "SPLIT_HISTORY_INTERVAL_MISMATCH"
    SPLIT_HISTORY_SYMBOL_MISMATCH = "SPLIT_HISTORY_SYMBOL_MISMATCH"
    ACTION_ON_PRESENTATION_BOUNDARY_DATE = "ACTION_ON_PRESENTATION_BOUNDARY_DATE"
    ACTION_LIFECYCLE_UNRESOLVED = "ACTION_LIFECYCLE_UNRESOLVED"
    ACTION_DATE_UNRESOLVED = "ACTION_DATE_UNRESOLVED"
    ACTION_RATIO_UNRESOLVED = "ACTION_RATIO_UNRESOLVED"
    ACTION_CLASS_MISMATCH = "ACTION_CLASS_MISMATCH"
    UNSUPPORTED_BASIS_ACTION = "UNSUPPORTED_BASIS_ACTION"
    SEC_ACTION_MISSING_YAHOO_CONFIRMATION = "SEC_ACTION_MISSING_YAHOO_CONFIRMATION"
    YAHOO_ACTION_MISSING_SEC_CONFIRMATION = "YAHOO_ACTION_MISSING_SEC_CONFIRMATION"
    ACTION_RATIO_CONFLICT = "ACTION_RATIO_CONFLICT"
    ACTION_EFFECTIVE_DATE_CONFLICT = "ACTION_EFFECTIVE_DATE_CONFLICT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


LIMITATIONS = (
    "BOUNDED_FREE_SOURCE_CONTINUITY_ONLY",
    "NO_UNIVERSAL_CORPORATE_ACTION_COMPLETENESS_CLAIM",
    "NO_PAID_CORPORATE_ACTION_MASTER_FEED",
    "PR5E_FINAL_ADMISSION_REQUIRED",
    "NO_HISTORICAL_AS_OF_AUTHORITY",
    "NO_EXPECTED_RETURN",
)


@dataclass(frozen=True, slots=True)
class SecQuoteEPSBasisBridgeRequest:
    comparability_request: SecCurrentEPSComparabilityRequest
    expected_comparability_semantic_id: str
    expected_comparability_evidence_id: str
    quote_request: YahooCurrentQuoteQualificationRequest
    expected_quote_semantic_id: str
    expected_quote_evidence_id: str
    recent_share_basis_request: SecShareBasisSourceRequest
    expected_recent_share_basis_semantic_id: str
    expected_recent_share_basis_evidence_id: str
    split_history_receipt_id: str
    expected_split_history_semantic_id: str
    expected_split_history_evidence_id: str

    def __post_init__(self):
        if (type(self.comparability_request) is not SecCurrentEPSComparabilityRequest
                or type(self.quote_request) is not YahooCurrentQuoteQualificationRequest
                or type(self.recent_share_basis_request) is not SecShareBasisSourceRequest):
            raise ShareBasisBridgeError("Exact typed replay selectors required")
        for field in fields(self):
            if field.name.startswith("expected_") or field.name == "split_history_receipt_id":
                value = getattr(self, field.name)
                if type(value) is not str or _HASH.fullmatch(value) is None:
                    raise ShareBasisBridgeError("Exact lowercase SHA-256 identities required")


@dataclass(frozen=True, slots=True)
class ReconciledBasisAction:
    action_kind: CorporateActionKind
    selected_common_class: str
    effective_date: str
    new_units: int
    old_units: int
    sec_claim_semantic_ids: tuple[str, ...]
    sec_claim_evidence_ids: tuple[str, ...]
    yahoo_event_semantic_id: str
    yahoo_event_evidence_id: str


@dataclass(frozen=True, slots=True)
class ShareBasisBridgeQualification:
    contract_version: str
    qualifier_version: str
    qualification_mode: str
    status: ShareBasisBridgeStatus
    reasons: tuple[ShareBasisBridgeReason, ...]
    historical_basis_identity: str | None
    quote_semantic_id: str
    quote_evidence_id: str
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    presentation_acceptance_boundary: str | None
    quote_boundary: str | None
    sec_inventory_snapshot_boundary: str | None
    route_inventory_semantic_id: str
    route_inventory_evidence_id: str
    filing_window_accessions: tuple[str, ...]
    considered_sec_action_claim_ids: tuple[str, ...]
    yahoo_split_history_semantic_id: str
    yahoo_split_history_evidence_id: str
    reconciled_actions: tuple[ReconciledBasisAction, ...]
    eps_to_quote_basis_multiplier_numerator: int | None
    eps_to_quote_basis_multiplier_denominator: int | None
    limitations: tuple[str, ...]
    upstream_comparability: RealEPSComparabilityQualification
    upstream_quote: QualifiedCurrentQuote
    recent_share_basis_source: SecShareBasisSourceAssessment
    yahoo_split_history: YahooSplitHistoryExtraction

    @property
    def semantic_id(self):
        return _identity("bridge-semantics", {
            "contract": self.contract_version,
            "qualifier": self.qualifier_version,
            "mode": self.qualification_mode,
            "status": self.status,
            "reasons": self.reasons,
            "historical_basis_identity": self.historical_basis_identity,
            "quote_semantic_id": self.quote_semantic_id,
            "issuer_key": self.route_local_issuer_key,
            "security_key": self.route_local_security_key,
            "presentation_acceptance_boundary": self.presentation_acceptance_boundary,
            "quote_boundary": self.quote_boundary,
            "sec_inventory_snapshot_boundary": self.sec_inventory_snapshot_boundary,
            "route_inventory_semantic_id": self.route_inventory_semantic_id,
            "filing_window_accessions": self.filing_window_accessions,
            "considered_sec_action_claim_ids": self.considered_sec_action_claim_ids,
            "yahoo_split_history_semantic_id": self.yahoo_split_history_semantic_id,
            "reconciled_actions": self.reconciled_actions,
            "multiplier": (self.eps_to_quote_basis_multiplier_numerator,
                           self.eps_to_quote_basis_multiplier_denominator),
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("bridge-evidence", {
            "semantic_id": self.semantic_id,
            "comparability_evidence_id": self.upstream_comparability.evidence_id,
            "route_inventory_evidence_id": self.route_inventory_evidence_id,
            "quote_evidence_id": self.quote_evidence_id,
            "recent_share_basis_evidence_id": self.recent_share_basis_source.evidence_id,
            "yahoo_split_history_evidence_id": self.yahoo_split_history_evidence_id,
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        return str(value)
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise ShareBasisBridgeError("Unsupported identity value")


def _identity(domain, value):
    raw = json.dumps(_project((QUALIFIER_VERSION, domain, value)), sort_keys=True,
                     separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _instant(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc)


def _canonical_instant(value):
    parsed = _instant(value)
    return None if parsed is None else parsed.isoformat().replace("+00:00", "Z")


def _normalize_label(value):
    return " ".join(re.sub(r"[^A-Z0-9]+", " ", value.upper()).split())


def _action_date(claim):
    for candidate in (claim.market_effective_date, claim.effective_date, claim.ex_date):
        if candidate is not None:
            return candidate.normalized_date
    return None


def _class_matches(claim, selected_label):
    if claim.class_link.scope is not SecurityClassSourceScope.NAMED_COMMON_CLASS_EXPLICIT:
        return False
    selected = _normalize_label(selected_label)
    return selected in claim.class_link.normalized_source_labels


def _claim_group_key(claim):
    return claim.accession, claim.source_local_action_key


def _claim_signature(claim):
    ratio = None if claim.ratio is None else (
        claim.ratio.new_units, claim.ratio.old_units)
    return (
        claim.action_kind, claim.lifecycle, _action_date(claim), ratio,
        claim.class_link.scope, claim.class_link.normalized_source_labels,
    )


def _coalesce_source_local_actions(claims):
    """Collapse PR5C0B's action/ratio/date claim projections into one action."""
    grouped = {}
    for claim in claims:
        grouped.setdefault(_claim_group_key(claim), []).append(claim)
    actions = []
    conflict = False
    for key, members in sorted(grouped.items()):
        signatures = {_claim_signature(item) for item in members}
        if len(signatures) != 1:
            conflict = True
            continue
        representative = min(members, key=lambda item: item.semantic_id)
        actions.append((
            representative,
            tuple(sorted({item.semantic_id for item in members})),
            tuple(sorted({item.evidence_id for item in members})),
        ))
    return tuple(actions), conflict


def _filing_window(assessment, start, end):
    selected = []
    for occurrence in assessment.submissions_inventory.occurrences:
        row = dict(occurrence.fields)
        accepted = _instant(row.get("acceptanceDateTime"))
        if (row.get("form") in SUPPORTED_FORMS and accepted is not None
                and start < accepted <= end):
            selected.append((row["accessionNumber"], occurrence))
    return tuple(sorted(selected, key=lambda item: (item[0], item[1].occurrence_id)))


def _is_monotonic_inventory_continuation(route_inventory, recent_inventory):
    """Require the recent graph to preserve the exact PR5C route inventory."""
    if (route_inventory.parent.cik != recent_inventory.parent.cik
            or route_inventory.parent.endpoint != recent_inventory.parent.endpoint
            or route_inventory.metadata_json != recent_inventory.metadata_json):
        return False
    route_rows = Counter(item.semantic_id for item in route_inventory.occurrences)
    recent_rows = Counter(item.semantic_id for item in recent_inventory.occurrences)
    if any(recent_rows[item] < count for item, count in route_rows.items()):
        return False
    route_references = Counter(item.fields for item in route_inventory.references)
    recent_references = Counter(item.fields for item in recent_inventory.references)
    return not any(recent_references[item] < count
                   for item, count in route_references.items())


def _classify_status(reasons):
    conflicts = {
        ShareBasisBridgeReason.REPLAY_IDENTITY_MISMATCH,
        ShareBasisBridgeReason.ROUTE_IDENTITY_MISMATCH,
        ShareBasisBridgeReason.DIRECT_LISTING_ROUTE_MISMATCH,
        ShareBasisBridgeReason.RECENT_INVENTORY_NOT_MONOTONIC_CONTINUATION,
        ShareBasisBridgeReason.ACTION_RATIO_CONFLICT,
        ShareBasisBridgeReason.ACTION_EFFECTIVE_DATE_CONFLICT,
        ShareBasisBridgeReason.SOURCE_CONFLICT,
    }
    unsupported = {
        ShareBasisBridgeReason.SHARE_BASIS_SOURCE_UNSUPPORTED,
        ShareBasisBridgeReason.YAHOO_SPLIT_HISTORY_UNSUPPORTED,
        ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION,
    }
    if reasons & conflicts:
        return ShareBasisBridgeStatus.SOURCE_CONFLICT
    if reasons & unsupported:
        return ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED
    if reasons:
        return ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE
    return ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED


def qualify_sec_quote_eps_basis_bridge(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    quote_archive: YahooQuoteArchive,
    split_history_archive: YahooSplitHistoryArchive,
    request: SecQuoteEPSBasisBridgeRequest,
) -> ShareBasisBridgeQualification:
    """Fresh replay plus bounded SEC/Yahoo continuity or exact action reconciliation."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(quote_archive) is not YahooQuoteArchive
            or type(split_history_archive) is not YahooSplitHistoryArchive
            or type(request) is not SecQuoteEPSBasisBridgeRequest):
        raise ShareBasisBridgeError("Exact typed archives/request required")
    comparability = qualify_sec_current_eps_comparability(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive,
        request.comparability_request)
    quote = qualify_yahoo_current_quote(
        quote_archive, current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, request.quote_request)
    recent_basis = build_sec_share_basis_source_foundation(
        submissions_archive, filing_archive, request.recent_share_basis_request)
    split_history = extract_yahoo_split_history(
        split_history_archive, request.split_history_receipt_id)
    reasons = set()
    if comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED:
        reasons.add(ShareBasisBridgeReason.PR5C_NOT_ESTABLISHED)
    if quote.status is not CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED:
        reasons.add(ShareBasisBridgeReason.PR5D1_NOT_ESTABLISHED)
    if (comparability.semantic_id != request.expected_comparability_semantic_id
            or comparability.evidence_id != request.expected_comparability_evidence_id
            or quote.semantic_id != request.expected_quote_semantic_id
            or quote.evidence_id != request.expected_quote_evidence_id
            or recent_basis.semantic_id != request.expected_recent_share_basis_semantic_id
            or recent_basis.evidence_id != request.expected_recent_share_basis_evidence_id
            or split_history.semantic_id != request.expected_split_history_semantic_id
            or split_history.evidence_id != request.expected_split_history_evidence_id):
        reasons.add(ShareBasisBridgeReason.REPLAY_IDENTITY_MISMATCH)
    if ((comparability.route_local_issuer_key, comparability.route_local_security_key)
            != (quote.route_local_issuer_key, quote.route_local_security_key)):
        reasons.add(ShareBasisBridgeReason.ROUTE_IDENTITY_MISMATCH)
    if (request.quote_request.security_request
            != request.comparability_request.security_eps_request
            or recent_basis.source_cik
            != comparability.upstream_share_basis_source.source_cik):
        reasons.add(ShareBasisBridgeReason.ROUTE_IDENTITY_MISMATCH)
    selected_symbol = comparability.upstream_security_eps.direct_listing.source_symbol
    if selected_symbol != quote.symbol:
        reasons.add(ShareBasisBridgeReason.DIRECT_LISTING_ROUTE_MISMATCH)

    inventory = recent_basis.submissions_inventory
    route_inventory = comparability.upstream_share_basis_source.submissions_inventory
    presentation_accession = comparability.presentation.accession
    occurrences = [item for item in inventory.occurrences
                   if dict(item.fields).get("accessionNumber") == presentation_accession]
    acceptance_values = tuple(dict(item.fields).get("acceptanceDateTime") for item in occurrences)
    presentation_boundary = None
    if not occurrences or any(_instant(value) is None for value in acceptance_values):
        reasons.add(ShareBasisBridgeReason.PRESENTATION_ACCEPTANCE_MISSING)
    elif len(occurrences) != 1 or len(set(acceptance_values)) != 1:
        reasons.add(ShareBasisBridgeReason.PRESENTATION_ACCEPTANCE_DUPLICATE)
    else:
        presentation_boundary = _canonical_instant(acceptance_values[0])
    start = _instant(presentation_boundary)
    quote_time = _instant(quote.provider_market_timestamp)
    quote_capture = _instant(quote.captured_at)
    current_boundary = _instant(
        comparability.upstream_security_eps.current_authority_boundary)
    sec_snapshot = _instant(inventory.parent.captured_at)
    sec_snapshot_boundary = _canonical_instant(inventory.parent.captured_at)
    if start is not None and quote_time is not None and start > quote_time:
        reasons.add(ShareBasisBridgeReason.PRESENTATION_AFTER_QUOTE)
    if inventory.status is not InventoryStatus.CAPTURED_REFERENCE_CLOSURE_COMPLETE:
        reasons.add(ShareBasisBridgeReason.FILING_REFERENCE_CLOSURE_INCOMPLETE)
    if not _is_monotonic_inventory_continuation(route_inventory, inventory):
        reasons.add(
            ShareBasisBridgeReason.RECENT_INVENTORY_NOT_MONOTONIC_CONTINUATION)
    if (sec_snapshot is None or quote_capture is None
            or sec_snapshot < quote_capture):
        reasons.add(
            ShareBasisBridgeReason.RECENT_SEC_SNAPSHOT_BEFORE_QUOTE_CAPTURE)
    if current_boundary is not None:
        inventory_receipts = (inventory.parent, *inventory.children)
        if any((_instant(item.captured_at) is None
                or _instant(item.captured_at) > current_boundary)
               for item in inventory_receipts):
            reasons.add(
                ShareBasisBridgeReason.RECENT_SUBMISSIONS_CAPTURE_AFTER_BOUNDARY)

    window = ()
    if start is not None and sec_snapshot is not None:
        window = _filing_window(recent_basis, start, sec_snapshot)
        sources = {item.accession: item for item in recent_basis.filing_universe}
        for accession in sorted({item[0] for item in window}):
            source = sources.get(accession)
            if source is None or len(source.captures) != 1:
                reasons.add(ShareBasisBridgeReason.RECENT_FILING_WINDOW_INCOMPLETE)
                continue
            captured = _instant(source.captures[0].receipt.captured_at)
            if captured is None or captured > current_boundary:
                reasons.add(ShareBasisBridgeReason.RECENT_FILING_CAPTURE_AFTER_BOUNDARY)
    window_accessions = {item[0] for item in window}
    scoped_conflicts = tuple(
        item for item in recent_basis.conflicts
        if item.accession is None or item.accession in window_accessions)
    scoped_issues = tuple(
        item for item in recent_basis.source_issues
        if item.accession is None or item.accession in window_accessions)
    unsupported_issues = {
        ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_INVENTORY,
        ShareBasisSourceIssue.UNSUPPORTED_DOCUMENT_REPRESENTATION,
        ShareBasisSourceIssue.MALFORMED_OR_AMBIGUOUS_TEXT,
        ShareBasisSourceIssue.SOURCE_SAFETY_BOUND_EXCEEDED,
        ShareBasisSourceIssue.AMBIGUOUS_RATIO_ORIENTATION,
        ShareBasisSourceIssue.AMBIGUOUS_ACTION_DATE,
        ShareBasisSourceIssue.INVALID_RATIO_TERMS,
        ShareBasisSourceIssue.UNINTERPRETED_BASIS_AFFECTING_LANGUAGE,
    }
    if scoped_conflicts:
        reasons.add(ShareBasisBridgeReason.SOURCE_CONFLICT)
    if any(item.issue in unsupported_issues for item in scoped_issues):
        reasons.add(ShareBasisBridgeReason.SHARE_BASIS_SOURCE_UNSUPPORTED)
    if split_history.status is SplitHistoryStatus.SOURCE_CONFLICT:
        reasons.add(ShareBasisBridgeReason.SOURCE_CONFLICT)
    elif split_history.status is SplitHistoryStatus.SPLIT_HISTORY_UNSUPPORTED:
        reasons.add(ShareBasisBridgeReason.YAHOO_SPLIT_HISTORY_UNSUPPORTED)
    elif split_history.status is not SplitHistoryStatus.SPLIT_HISTORY_EXTRACTED:
        reasons.add(ShareBasisBridgeReason.YAHOO_SPLIT_HISTORY_UNAVAILABLE)

    if start is not None and quote_time is not None:
        if (split_history.receipt.requested_start_epoch != int(start.timestamp())
                or split_history.receipt.requested_end_epoch != int(quote_time.timestamp())):
            reasons.add(ShareBasisBridgeReason.SPLIT_HISTORY_INTERVAL_MISMATCH)
    if (split_history.receipt.requested_symbol != selected_symbol
            or (split_history.returned_symbol is not None
                and split_history.returned_symbol != selected_symbol)):
        reasons.add(ShareBasisBridgeReason.SPLIT_HISTORY_SYMBOL_MISMATCH)

    selected_class = (comparability.upstream_security_eps.participation
                      .canonical_source_class_label)
    considered = []
    effective_sec = []
    if start is not None and quote_time is not None and selected_class is not None:
        start_date = start.date().isoformat()
        quote_date = quote_time.date().isoformat()
        window_claims = tuple(claim for claim in recent_basis.explicit_claims
                              if claim.accession in window_accessions)
        considered.extend(claim.semantic_id for claim in window_claims)
        source_actions, source_action_conflict = _coalesce_source_local_actions(
            window_claims)
        if source_action_conflict:
            reasons.add(ShareBasisBridgeReason.SOURCE_CONFLICT)
        for claim, semantic_ids, evidence_ids in source_actions:
            action_date = _action_date(claim)
            if claim.lifecycle is CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE:
                continue
            if claim.lifecycle in {
                CorporateActionLifecycle.ANNOUNCED_OR_PROPOSED_REFERENCE,
                CorporateActionLifecycle.APPROVED_REFERENCE,
            }:
                if action_date is None:
                    reasons.add(ShareBasisBridgeReason.ACTION_LIFECYCLE_UNRESOLVED)
                    continue
                if action_date == start_date:
                    reasons.add(
                        ShareBasisBridgeReason.ACTION_ON_PRESENTATION_BOUNDARY_DATE)
                    continue
                if action_date <= quote_date:
                    reasons.add(ShareBasisBridgeReason.ACTION_LIFECYCLE_UNRESOLVED)
                continue
            if claim.lifecycle is CorporateActionLifecycle.UNRESOLVED_LIFECYCLE:
                reasons.add(ShareBasisBridgeReason.ACTION_LIFECYCLE_UNRESOLVED)
                continue
            if action_date is None:
                reasons.add(ShareBasisBridgeReason.ACTION_DATE_UNRESOLVED)
                continue
            if action_date == start_date:
                reasons.add(ShareBasisBridgeReason.ACTION_ON_PRESENTATION_BOUNDARY_DATE)
                continue
            if action_date < start_date or action_date > quote_date:
                continue
            if claim.action_kind not in SUPPORTED_ACTIONS:
                reasons.add(ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION)
                continue
            if claim.ratio is None:
                reasons.add(ShareBasisBridgeReason.ACTION_RATIO_UNRESOLVED)
                continue
            if not _class_matches(claim, selected_class):
                reasons.add(ShareBasisBridgeReason.ACTION_CLASS_MISMATCH)
                continue
            effective_sec.append((action_date, claim, semantic_ids, evidence_ids))

    canonical_actions = {}
    for action_date, claim, semantic_ids, evidence_ids in effective_sec:
        key = (
            action_date, claim.action_kind,
            claim.ratio.new_units, claim.ratio.old_units,
            claim.class_link.normalized_source_labels,
        )
        if key not in canonical_actions:
            canonical_actions[key] = [claim, set(), set()]
        canonical_actions[key][1].update(semantic_ids)
        canonical_actions[key][2].update(evidence_ids)
    effective_sec = tuple(
        (key[0], values[0], tuple(sorted(values[1])), tuple(sorted(values[2])))
        for key, values in sorted(canonical_actions.items(), key=lambda item: item[0])
    )

    yahoo_by_date = {}
    for event in split_history.events:
        yahoo_by_date.setdefault(event.event_timestamp[:10], []).append(event)
    reconciled = []
    used_yahoo = set()
    for action_date, claim, semantic_ids, evidence_ids in effective_sec:
        same_date = yahoo_by_date.get(action_date, [])
        exact = [event for event in same_date
                 if (event.numerator, event.denominator)
                 == (claim.ratio.new_units, claim.ratio.old_units)]
        if not same_date:
            reasons.add(ShareBasisBridgeReason.SEC_ACTION_MISSING_YAHOO_CONFIRMATION)
            continue
        if not exact:
            reasons.add(ShareBasisBridgeReason.ACTION_RATIO_CONFLICT)
            continue
        if len(exact) != 1:
            reasons.add(ShareBasisBridgeReason.SOURCE_CONFLICT)
            continue
        event = exact[0]
        used_yahoo.add(event.semantic_id)
        reconciled.append(ReconciledBasisAction(
            claim.action_kind, selected_class, action_date,
            claim.ratio.new_units, claim.ratio.old_units,
            semantic_ids, evidence_ids, event.semantic_id, event.evidence_id,
        ))
    if effective_sec and split_history.events:
        sec_dates = {item[0] for item in effective_sec}
        yahoo_dates = {event.event_timestamp[:10] for event in split_history.events}
        if sec_dates != yahoo_dates and any(date not in sec_dates for date in yahoo_dates):
            reasons.add(ShareBasisBridgeReason.ACTION_EFFECTIVE_DATE_CONFLICT)
    for event in split_history.events:
        if event.semantic_id not in used_yahoo:
            reasons.add(ShareBasisBridgeReason.YAHOO_ACTION_MISSING_SEC_CONFIRMATION)

    status = _classify_status(reasons)
    multiplier = Fraction(1, 1)
    if status is ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED:
        for action in sorted(reconciled, key=lambda item: (
                item.effective_date, item.sec_claim_semantic_ids)):
            multiplier *= Fraction(action.old_units, action.new_units)
    positive = status is ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED
    return ShareBasisBridgeQualification(
        CONTRACT_VERSION, QUALIFIER_VERSION, QUALIFICATION_MODE, status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        (comparability.historical_share_basis.qualified_basis_identity
         if positive else None),
        quote.semantic_id, quote.evidence_id,
        comparability.route_local_issuer_key if positive else None,
        comparability.route_local_security_key if positive else None,
        presentation_boundary, quote.provider_market_timestamp,
        sec_snapshot_boundary,
        route_inventory.semantic_id, route_inventory.evidence_id,
        tuple(sorted({item[0] for item in window})),
        tuple(sorted(set(considered))),
        split_history.semantic_id, split_history.evidence_id,
        tuple(sorted(reconciled, key=lambda item: (
            item.effective_date, item.sec_claim_semantic_ids))),
        multiplier.numerator if positive else None,
        multiplier.denominator if positive else None,
        LIMITATIONS, comparability, quote, recent_basis, split_history,
    )
