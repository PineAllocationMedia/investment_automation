"""Order multiple D4D3A source correspondences by SEC acceptance events.

This D4D3B adapter builds a descriptive temporal source-evidence series only.
It does not establish durable class/security identity, ticker permanence,
legal-right continuity, absence of corporate actions, Property 4 qualification,
or admission authority.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_common_stock_class_bridge import (
    ClassBridgeAssessmentStatus,
    CurrentCommonStockClassBridgeEvidence,
    SecCurrentCommonStockClassBridgeAssessment,
    SecCurrentCommonStockClassBridgeRequest,
    assess_sec_current_common_stock_class_bridge,
)
from .sec_current_registered_listing_bridge import (
    BridgeAssessmentStatus,
    CurrentRegisteredListingBridgeEvidence,
    SecCurrentRegisteredListingBridgeAssessment,
    SecCurrentRegisteredListingBridgeRequest,
    assess_sec_current_registered_listing_bridge,
)
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_property4_temporal_boundary import SourceEventBoundaryRelation
from .sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsRequest,
    SecSection12RightsSourceTopic,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive


CONTRACT_VERSION = "2026-09-27-sec-temporal-common-stock-source-series-v1"
SEC_NASDAQ_TEMPORAL_COMMON_STOCK_SOURCE_SERIES_V1 = (
    "SEC_NASDAQ_TEMPORAL_COMMON_STOCK_SOURCE_SERIES_V1"
)
MIN_RIGHTS_REQUESTS = 2
MAX_RIGHTS_REQUESTS = 32


class SecTemporalCommonStockSourceSeriesRequestError(ValueError):
    """Invalid closed D4D3B request or incorrect typed public input."""


class TemporalCommonStockSourceSeriesStatus(StrEnum):
    CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES = (
        "CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES"
    )
    INSUFFICIENT_TEMPORAL_OBSERVATIONS = "INSUFFICIENT_TEMPORAL_OBSERVATIONS"
    INCOMPLETE_TEMPORAL_SOURCE_SERIES = "INCOMPLETE_TEMPORAL_SOURCE_SERIES"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_TEMPORAL_PROFILE = "UNSUPPORTED_TEMPORAL_PROFILE"
    UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE = "UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE"


class TemporalCommonStockSourceObservationStatus(StrEnum):
    CAPTURED_SOURCE_CORRESPONDENCE_OBSERVATION = (
        "CAPTURED_SOURCE_CORRESPONDENCE_OBSERVATION"
    )
    INCOMPLETE_SOURCE_CORRESPONDENCE_OBSERVATION = (
        "INCOMPLETE_SOURCE_CORRESPONDENCE_OBSERVATION"
    )
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class TemporalCommonStockSourceSeriesIssue(StrEnum):
    D4C2_CURRENT_BRIDGE_UNAVAILABLE = "D4C2_CURRENT_BRIDGE_UNAVAILABLE"
    D4C2_SOURCE_CONFLICT = "D4C2_SOURCE_CONFLICT"
    D4C2_UNSUPPORTED_PROFILE = "D4C2_UNSUPPORTED_PROFILE"
    D4C2_NO_SUPPORTED_CANDIDATE = "D4C2_NO_SUPPORTED_CANDIDATE"
    D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID = (
        "D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID"
    )
    D4D3A_UPSTREAM_UNAVAILABLE = "D4D3A_UPSTREAM_UNAVAILABLE"
    D4D3A_SOURCE_CONFLICT = "D4D3A_SOURCE_CONFLICT"
    D4D3A_UNSUPPORTED_PROFILE = "D4D3A_UNSUPPORTED_PROFILE"
    D4D3A_NO_CLASS_CANDIDATE = "D4D3A_NO_CLASS_CANDIDATE"
    D4D3A_POSITIVE_CANDIDATE_COUNT_INVALID = (
        "D4D3A_POSITIVE_CANDIDATE_COUNT_INVALID"
    )
    D4C2_REPLAY_DISAGREEMENT = "D4C2_REPLAY_DISAGREEMENT"
    CURRENT_BOUNDARY_DISAGREEMENT = "CURRENT_BOUNDARY_DISAGREEMENT"
    SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY = (
        "SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY"
    )
    ACCESSION_NOT_IN_TEMPORAL_BOUNDARY = "ACCESSION_NOT_IN_TEMPORAL_BOUNDARY"
    AMBIGUOUS_TEMPORAL_BOUNDARY_ACCESSION = (
        "AMBIGUOUS_TEMPORAL_BOUNDARY_ACCESSION"
    )
    AMBIGUOUS_SOURCE_ACCEPTANCE_TIMESTAMP = (
        "AMBIGUOUS_SOURCE_ACCEPTANCE_TIMESTAMP"
    )
    MISSING_SOURCE_ACCEPTANCE_TIMESTAMP = "MISSING_SOURCE_ACCEPTANCE_TIMESTAMP"
    SAME_ACCESSION_SEMANTIC_CONFLICT = "SAME_ACCESSION_SEMANTIC_CONFLICT"
    INSUFFICIENT_DISTINCT_ACCESSIONS = "INSUFFICIENT_DISTINCT_ACCESSIONS"


class TemporalCommonStockSourceSignal(StrEnum):
    CANONICAL_CLASS_LABEL_STABLE = "CANONICAL_CLASS_LABEL_STABLE"
    EXACT_D3A_TITLE_VARIATION = "EXACT_D3A_TITLE_VARIATION"
    D3A_TITLE_SUFFIX_VARIATION = "D3A_TITLE_SUFFIX_VARIATION"
    EXACT_D4D2B_HEADING_VARIATION = "EXACT_D4D2B_HEADING_VARIATION"
    RIGHTS_PASSAGE_SEMANTICS_VARIATION = "RIGHTS_PASSAGE_SEMANTICS_VARIATION"
    RIGHTS_TOPIC_SET_VARIATION = "RIGHTS_TOPIC_SET_VARIATION"


_CONFLICT_ISSUES = frozenset((
    TemporalCommonStockSourceSeriesIssue.D4C2_SOURCE_CONFLICT,
    TemporalCommonStockSourceSeriesIssue.D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID,
    TemporalCommonStockSourceSeriesIssue.D4D3A_SOURCE_CONFLICT,
    TemporalCommonStockSourceSeriesIssue.D4D3A_POSITIVE_CANDIDATE_COUNT_INVALID,
    TemporalCommonStockSourceSeriesIssue.D4C2_REPLAY_DISAGREEMENT,
    TemporalCommonStockSourceSeriesIssue.CURRENT_BOUNDARY_DISAGREEMENT,
    TemporalCommonStockSourceSeriesIssue.AMBIGUOUS_TEMPORAL_BOUNDARY_ACCESSION,
    TemporalCommonStockSourceSeriesIssue.AMBIGUOUS_SOURCE_ACCEPTANCE_TIMESTAMP,
    TemporalCommonStockSourceSeriesIssue.SAME_ACCESSION_SEMANTIC_CONFLICT,
))


def _identity(domain, value):
    return digest(("pam:sec-temporal-common-stock-source-series:"
                   + domain + ":v1\0").encode("ascii") + canonical_json(value))


def _instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ordered(issues):
    return tuple(sorted(set(issues), key=lambda issue: issue.value))


@dataclass(frozen=True, slots=True)
class SecTemporalCommonStockSourceSeriesRequest:
    registered_listing_bridge_request: SecCurrentRegisteredListingBridgeRequest
    rights_claims_requests: tuple[SecSection12RightsSourceClaimsRequest, ...]

    def __post_init__(self):
        if (type(self.registered_listing_bridge_request)
                is not SecCurrentRegisteredListingBridgeRequest):
            raise SecTemporalCommonStockSourceSeriesRequestError(
                "Exact D4C2 request required")
        if type(self.rights_claims_requests) is not tuple:
            raise SecTemporalCommonStockSourceSeriesRequestError(
                "Bounded tuple of exact D4D2B requests required")
        request_count = len(self.rights_claims_requests)
        if (not MIN_RIGHTS_REQUESTS <= request_count <= MAX_RIGHTS_REQUESTS
                or any(type(item) is not SecSection12RightsSourceClaimsRequest
                       for item in self.rights_claims_requests)):
            raise SecTemporalCommonStockSourceSeriesRequestError(
                "Bounded tuple of exact D4D2B requests required")
        receipt_ids = tuple(item.filing_receipt_id for item in self.rights_claims_requests)
        if len(set(receipt_ids)) != len(receipt_ids):
            raise SecTemporalCommonStockSourceSeriesRequestError(
                "Every selected filing receipt ID must be unique")


@dataclass(frozen=True, slots=True)
class TemporalCommonStockSourceObservation:
    """One accession-level source observation, never a continuity assertion."""

    profile: str
    source_acceptance_timestamp: str | None
    source_acceptance_timestamps: tuple[str, ...]
    accession: str
    source_cik: str
    source_symbol: str
    canonical_source_class_label: str | None
    canonical_source_class_labels: tuple[str, ...]
    exact_d3a_titles: tuple[str, ...]
    exact_d3a_title_suffixes: tuple[str | None, ...]
    exact_d4d2b_class_headings: tuple[str, ...]
    d3a_source_security_scope_ids: tuple[str, ...]
    d4d3a_candidate_semantic_id: str | None
    competing_d4d3a_candidate_semantic_ids: tuple[str, ...]
    d4d3a_candidate_evidence_ids: tuple[str, ...]
    d4d3a_assessment_semantic_ids: tuple[str, ...]
    d4d3a_assessment_evidence_ids: tuple[str, ...]
    filing_receipt_ids: tuple[str, ...]
    rights_claims_semantic_ids: tuple[str, ...]
    rights_claims_evidence_ids: tuple[str, ...]
    d4d2b_source_class_scope_ids: tuple[str, ...]
    passage_semantic_ids: tuple[str, ...]
    passage_evidence_ids: tuple[str, ...]
    rights_passage_source_semantic_ids: tuple[str, ...]
    source_topics: tuple[SecSection12RightsSourceTopic, ...]
    temporal_filing_semantic_id: str | None
    temporal_filing_evidence_id: str | None
    source_acceptance_occurrence_ids: tuple[str, ...]
    status: TemporalCommonStockSourceObservationStatus
    issues: tuple[TemporalCommonStockSourceSeriesIssue, ...]

    @property
    def semantic_id(self):
        return _identity("observation-semantics", {
            "contract": CONTRACT_VERSION,
            "profile": self.profile,
            "source_acceptance_timestamp": self.source_acceptance_timestamp,
            "source_acceptance_timestamps": self.source_acceptance_timestamps,
            "accession": self.accession,
            "source_cik": self.source_cik,
            "source_symbol": self.source_symbol,
            "canonical_source_class_label": self.canonical_source_class_label,
            "canonical_source_class_labels": self.canonical_source_class_labels,
            "exact_d3a_titles": self.exact_d3a_titles,
            "exact_d3a_title_suffixes": self.exact_d3a_title_suffixes,
            "exact_d4d2b_class_headings": self.exact_d4d2b_class_headings,
            "d3a_source_security_scope_ids": self.d3a_source_security_scope_ids,
            "d4d3a_candidate_semantic_id": self.d4d3a_candidate_semantic_id,
            "competing_d4d3a_candidate_semantic_ids":
                self.competing_d4d3a_candidate_semantic_ids,
            "d4d3a_assessment_semantic_ids": self.d4d3a_assessment_semantic_ids,
            "rights_claims_semantic_ids": self.rights_claims_semantic_ids,
            "d4d2b_source_class_scope_ids": self.d4d2b_source_class_scope_ids,
            "passage_semantic_ids": self.passage_semantic_ids,
            "rights_passage_source_semantic_ids":
                self.rights_passage_source_semantic_ids,
            "source_topics": self.source_topics,
            "temporal_filing_semantic_id": self.temporal_filing_semantic_id,
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("observation-evidence", {
            "semantic_id": self.semantic_id,
            "d4d3a_candidate_evidence_ids": self.d4d3a_candidate_evidence_ids,
            "d4d3a_assessment_evidence_ids": self.d4d3a_assessment_evidence_ids,
            "filing_receipt_ids": self.filing_receipt_ids,
            "rights_claims_evidence_ids": self.rights_claims_evidence_ids,
            "passage_evidence_ids": self.passage_evidence_ids,
            "temporal_filing_evidence_id": self.temporal_filing_evidence_id,
            "source_acceptance_occurrence_ids":
                self.source_acceptance_occurrence_ids,
        })


@dataclass(frozen=True, slots=True)
class SecTemporalCommonStockSourceSeriesAssessment:
    contract_version: str
    status: TemporalCommonStockSourceSeriesStatus
    profile: str
    current_authority_boundary: str | None
    registered_listing_bridge: SecCurrentRegisteredListingBridgeAssessment
    class_bridge_assessments: tuple[SecCurrentCommonStockClassBridgeAssessment, ...]
    observations: tuple[TemporalCommonStockSourceObservation, ...]
    distinct_accession_count: int
    descriptive_signals: tuple[TemporalCommonStockSourceSignal, ...]
    issues: tuple[TemporalCommonStockSourceSeriesIssue, ...]

    @property
    def semantic_id(self):
        return _identity("series-semantics", {
            "contract": self.contract_version,
            "profile": self.profile,
            "d4c2_semantic_id": self.registered_listing_bridge.semantic_id,
            "current_authority_boundary": self.current_authority_boundary,
            "d4d3a_assessment_semantic_ids": tuple(sorted({
                item.semantic_id for item in self.class_bridge_assessments})),
            "ordered_observation_semantic_ids": tuple(
                item.semantic_id for item in self.observations),
            "distinct_accession_count": self.distinct_accession_count,
            "descriptive_signals": self.descriptive_signals,
            "status": self.status,
            "issues": self.issues,
        })

    @property
    def evidence_id(self):
        return _identity("series-evidence", {
            "semantic_id": self.semantic_id,
            "d4c2_evidence_id": self.registered_listing_bridge.evidence_id,
            "d4d3a_assessment_evidence_ids": tuple(sorted(
                item.evidence_id for item in self.class_bridge_assessments)),
            "ordered_observation_evidence_ids": tuple(
                item.evidence_id for item in self.observations),
        })


def _positive_candidates(assessment):
    return tuple(candidate for candidate in assessment.candidates
                 if candidate.status is BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)


def _class_positive_candidates(assessment):
    return tuple(candidate for candidate in assessment.candidates
                 if candidate.status is
                 ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)


def _common_bridge_issues(common):
    if common.status is BridgeAssessmentStatus.SOURCE_CONFLICT:
        return {TemporalCommonStockSourceSeriesIssue.D4C2_SOURCE_CONFLICT}
    if common.status is BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE:
        return {TemporalCommonStockSourceSeriesIssue.D4C2_UNSUPPORTED_PROFILE}
    if common.status is BridgeAssessmentStatus.NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE:
        return {TemporalCommonStockSourceSeriesIssue.D4C2_NO_SUPPORTED_CANDIDATE}
    if common.status is not BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED:
        return {TemporalCommonStockSourceSeriesIssue.D4C2_CURRENT_BRIDGE_UNAVAILABLE}
    if len(_positive_candidates(common)) != 1:
        return {TemporalCommonStockSourceSeriesIssue.D4C2_SUCCESSFUL_CANDIDATE_COUNT_INVALID}
    return set()


def _class_bridge_issues(assessment):
    if assessment.status is ClassBridgeAssessmentStatus.SOURCE_CONFLICT:
        return {TemporalCommonStockSourceSeriesIssue.D4D3A_SOURCE_CONFLICT}
    if assessment.status is ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE:
        return {TemporalCommonStockSourceSeriesIssue.D4D3A_UNSUPPORTED_PROFILE}
    if assessment.status is ClassBridgeAssessmentStatus.NO_SUPPORTED_CLASS_CANDIDATE:
        return {TemporalCommonStockSourceSeriesIssue.D4D3A_NO_CLASS_CANDIDATE}
    if assessment.status is not (
            ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED):
        return {TemporalCommonStockSourceSeriesIssue.D4D3A_UPSTREAM_UNAVAILABLE}
    if len(_class_positive_candidates(assessment)) != 1:
        return {
            TemporalCommonStockSourceSeriesIssue.D4D3A_POSITIVE_CANDIDATE_COUNT_INVALID
        }
    return set()


def _replay_agrees(common, common_candidate, assessment):
    replay = assessment.current_listing_bridge
    issues = set()
    if replay.current_authority_boundary != common.current_authority_boundary:
        issues.add(TemporalCommonStockSourceSeriesIssue.CURRENT_BOUNDARY_DISAGREEMENT)
    replay_candidates = _positive_candidates(replay)
    replay_identity_disagrees = (
        replay.semantic_id != common.semantic_id
        or replay.evidence_id != common.evidence_id
    )
    candidate_disagrees = False
    if common_candidate is not None:
        candidate_disagrees = (
            len(replay_candidates) != 1
            or replay_candidates[0].semantic_id != common_candidate.semantic_id
            or replay_candidates[0].evidence_id != common_candidate.evidence_id
        )
    elif replay_candidates:
        candidate_disagrees = True
    if replay_identity_disagrees or candidate_disagrees:
        issues.add(TemporalCommonStockSourceSeriesIssue.D4C2_REPLAY_DISAGREEMENT)
    return issues


def _passage_source_semantics(assessment, candidate):
    by_id = {passage.semantic_id: passage
             for passage in assessment.rights_source_claims.passages}
    signatures = []
    for passage_id in candidate.passage_semantic_ids:
        passage = by_id.get(passage_id)
        if passage is None:
            return None
        signatures.append(_identity("rights-passage-source-semantics", {
            "structural_element_kind": passage.structural_element_kind,
            "source_text_sha256": passage.source_text_sha256,
            "matched_topics": passage.matched_topics,
            "matched_topic_anchor_ids": passage.matched_topic_anchor_ids,
            "issues": passage.issues,
        }))
    return tuple(signatures)


def _observation(accession, members, common):
    issues = set()
    assessments = tuple(item[0] for item in members)
    candidates = tuple(item[1] for item in members)
    requested_receipt_ids = tuple(sorted(item[2] for item in members))
    candidate_semantic_ids = tuple(sorted({item.semantic_id for item in candidates}))
    if len(candidate_semantic_ids) != 1:
        issues.add(
            TemporalCommonStockSourceSeriesIssue.SAME_ACCESSION_SEMANTIC_CONFLICT)

    filings = tuple(item for item in common.temporal_boundary.filings
                    if item.accession == accession)
    filing = filings[0] if len(filings) == 1 else None
    if not filings:
        issues.add(TemporalCommonStockSourceSeriesIssue.ACCESSION_NOT_IN_TEMPORAL_BOUNDARY)
    elif len(filings) != 1:
        issues.add(
            TemporalCommonStockSourceSeriesIssue.AMBIGUOUS_TEMPORAL_BOUNDARY_ACCESSION)

    timestamps = ()
    occurrence_ids = ()
    if filing is not None:
        controlled_receipt_ids = {
            capture.receipt.receipt_id
            for capture in filing.controlled_captures_by_boundary
        }
        if any(receipt_id not in controlled_receipt_ids
               for receipt_id in requested_receipt_ids):
            issues.add(TemporalCommonStockSourceSeriesIssue.
                       SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY)
        supported_events = tuple(
            event for event in filing.source_acceptance_events
            if event.relation is SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY
        )
        timestamps = tuple(sorted(
            {event.acceptance_timestamp for event in supported_events},
            key=lambda value: (_instant(value), value),
        ))
        occurrence_ids = tuple(sorted(event.occurrence_id for event in supported_events))
        if not timestamps:
            issues.add(
                TemporalCommonStockSourceSeriesIssue.MISSING_SOURCE_ACCEPTANCE_TIMESTAMP)
        elif len(timestamps) != 1:
            issues.add(TemporalCommonStockSourceSeriesIssue.
                       AMBIGUOUS_SOURCE_ACCEPTANCE_TIMESTAMP)

    passage_source_semantics = []
    for assessment, candidate, _receipt_id in members:
        signatures = _passage_source_semantics(assessment, candidate)
        if signatures is None:
            issues.add(TemporalCommonStockSourceSeriesIssue.D4D3A_SOURCE_CONFLICT)
        else:
            passage_source_semantics.append(signatures)

    canonical_labels = tuple(sorted({candidate.canonical_source_class_label
                                     for candidate in candidates
                                     if candidate.canonical_source_class_label is not None}))
    if issues & _CONFLICT_ISSUES:
        status = TemporalCommonStockSourceObservationStatus.SOURCE_CONFLICT
    elif issues:
        status = (TemporalCommonStockSourceObservationStatus.
                  INCOMPLETE_SOURCE_CORRESPONDENCE_OBSERVATION)
    else:
        status = (TemporalCommonStockSourceObservationStatus.
                  CAPTURED_SOURCE_CORRESPONDENCE_OBSERVATION)
    ordered_issues = _ordered(issues)
    return TemporalCommonStockSourceObservation(
        SEC_NASDAQ_TEMPORAL_COMMON_STOCK_SOURCE_SERIES_V1,
        timestamps[0] if len(timestamps) == 1 else None,
        timestamps,
        accession,
        candidates[0].source_cik,
        candidates[0].source_symbol,
        canonical_labels[0] if len(canonical_labels) == 1 else None,
        canonical_labels,
        tuple(sorted({candidate.exact_d3a_title for candidate in candidates})),
        tuple(sorted({candidate.exact_d3a_title_suffix for candidate in candidates},
                     key=lambda value: (value is not None, value or ""))),
        tuple(sorted({candidate.exact_d4d2b_class_heading for candidate in candidates
                      if candidate.exact_d4d2b_class_heading is not None})),
        tuple(sorted({candidate.d3a_source_security_scope_id
                      for candidate in candidates})),
        candidate_semantic_ids[0] if len(candidate_semantic_ids) == 1 else None,
        candidate_semantic_ids,
        tuple(sorted({candidate.evidence_id for candidate in candidates})),
        tuple(sorted({assessment.semantic_id for assessment in assessments})),
        tuple(sorted({assessment.evidence_id for assessment in assessments})),
        requested_receipt_ids,
        tuple(sorted({candidate.rights_claims_semantic_id
                      for candidate in candidates})),
        tuple(sorted({candidate.rights_claims_evidence_id
                      for candidate in candidates})),
        tuple(sorted({candidate.d4d2b_source_class_scope_id
                      for candidate in candidates
                      if candidate.d4d2b_source_class_scope_id is not None})),
        tuple(sorted({item for candidate in candidates
                      for item in candidate.passage_semantic_ids})),
        tuple(sorted({item for candidate in candidates
                      for item in candidate.passage_evidence_ids})),
        (passage_source_semantics[0]
         if passage_source_semantics
         and len(set(passage_source_semantics)) == 1 else
         tuple(sorted({item for signatures in passage_source_semantics
                       for item in signatures}))),
        tuple(sorted({topic for candidate in candidates
                      for topic in candidate.source_topics}, key=lambda item: item.value)),
        None if filing is None else filing.temporal_filing_semantic_id,
        None if filing is None else filing.temporal_filing_evidence_id,
        occurrence_ids,
        status,
        ordered_issues,
    )


def _observation_key(observation):
    if observation.source_acceptance_timestamp is None:
        return (1, datetime.max.replace(tzinfo=None), observation.accession,
                observation.semantic_id)
    parsed = _instant(observation.source_acceptance_timestamp)
    return (0, parsed, observation.accession, observation.semantic_id)


def _signals(observations):
    if (len(observations) < MIN_RIGHTS_REQUESTS
            or any(item.status is not TemporalCommonStockSourceObservationStatus.
                   CAPTURED_SOURCE_CORRESPONDENCE_OBSERVATION
                   for item in observations)):
        return ()
    signals = set()
    if len({item.canonical_source_class_label for item in observations}) == 1:
        signals.add(TemporalCommonStockSourceSignal.CANONICAL_CLASS_LABEL_STABLE)
    if len({item.exact_d3a_titles for item in observations}) > 1:
        signals.add(TemporalCommonStockSourceSignal.EXACT_D3A_TITLE_VARIATION)
    if len({item.exact_d3a_title_suffixes for item in observations}) > 1:
        signals.add(TemporalCommonStockSourceSignal.D3A_TITLE_SUFFIX_VARIATION)
    if len({item.exact_d4d2b_class_headings for item in observations}) > 1:
        signals.add(TemporalCommonStockSourceSignal.EXACT_D4D2B_HEADING_VARIATION)
    if len({item.rights_passage_source_semantic_ids for item in observations}) > 1:
        signals.add(TemporalCommonStockSourceSignal.RIGHTS_PASSAGE_SEMANTICS_VARIATION)
    if len({item.source_topics for item in observations}) > 1:
        signals.add(TemporalCommonStockSourceSignal.RIGHTS_TOPIC_SET_VARIATION)
    return tuple(sorted(signals, key=lambda item: item.value))


def _series_status(common, issues, observations, selected_count,
                   positive_selection_count):
    issue_set = set(issues)
    if issue_set & _CONFLICT_ISSUES:
        return TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT
    if (TemporalCommonStockSourceSeriesIssue.D4C2_UNSUPPORTED_PROFILE in issue_set
            or TemporalCommonStockSourceSeriesIssue.D4D3A_UNSUPPORTED_PROFILE
            in issue_set):
        return TemporalCommonStockSourceSeriesStatus.UNSUPPORTED_TEMPORAL_PROFILE
    if common.status is not BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED:
        return (TemporalCommonStockSourceSeriesStatus.
                UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE)
    if (positive_selection_count < selected_count
            or any(item.status is not TemporalCommonStockSourceObservationStatus.
                   CAPTURED_SOURCE_CORRESPONDENCE_OBSERVATION
                   for item in observations)
            or issue_set - {
                TemporalCommonStockSourceSeriesIssue.INSUFFICIENT_DISTINCT_ACCESSIONS
            }):
        return TemporalCommonStockSourceSeriesStatus.INCOMPLETE_TEMPORAL_SOURCE_SERIES
    if len(observations) < MIN_RIGHTS_REQUESTS:
        return TemporalCommonStockSourceSeriesStatus.INSUFFICIENT_TEMPORAL_OBSERVATIONS
    return (TemporalCommonStockSourceSeriesStatus.
            CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES)


def assess_sec_temporal_common_stock_source_series(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecTemporalCommonStockSourceSeriesRequest,
) -> SecTemporalCommonStockSourceSeriesAssessment:
    """Freshly replay D4C2 and every D4D3A request into one ordered series."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecTemporalCommonStockSourceSeriesRequest):
        raise SecTemporalCommonStockSourceSeriesRequestError(
            "Exact typed archives/request required")

    common = assess_sec_current_registered_listing_bridge(
        current_archive,
        submissions_archive,
        filing_archive,
        ticker_exchange_archive,
        nasdaq_listed_archive,
        request.registered_listing_bridge_request,
    )
    ordered_requests = tuple(sorted(
        request.rights_claims_requests,
        key=lambda item: item.filing_receipt_id,
    ))
    assessments = tuple(
        assess_sec_current_common_stock_class_bridge(
            current_archive,
            submissions_archive,
            filing_archive,
            ticker_exchange_archive,
            nasdaq_listed_archive,
            SecCurrentCommonStockClassBridgeRequest(
                request.registered_listing_bridge_request,
                rights_request,
            ),
        )
        for rights_request in ordered_requests
    )

    issues = _common_bridge_issues(common)
    common_candidates = _positive_candidates(common)
    common_candidate = common_candidates[0] if len(common_candidates) == 1 else None
    by_accession = {}
    positive_selection_count = 0
    for rights_request, assessment in zip(ordered_requests, assessments):
        assessment_issues = _class_bridge_issues(assessment)
        issues.update(assessment_issues)
        replay_issues = _replay_agrees(common, common_candidate, assessment)
        issues.update(replay_issues)
        positive_candidates = _class_positive_candidates(assessment)
        if assessment_issues or replay_issues or len(positive_candidates) != 1:
            continue
        candidate = positive_candidates[0]
        if candidate.filing_receipt_id != rights_request.filing_receipt_id:
            issues.add(TemporalCommonStockSourceSeriesIssue.
                       SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY)
            continue
        positive_selection_count += 1
        by_accession.setdefault(candidate.accession, []).append(
            (assessment, candidate, rights_request.filing_receipt_id))

    observations = tuple(_observation(accession, tuple(by_accession[accession]), common)
                         for accession in sorted(by_accession))
    observations = tuple(sorted(observations, key=_observation_key))
    issues.update(issue for observation in observations for issue in observation.issues)
    if len(observations) < MIN_RIGHTS_REQUESTS:
        issues.add(TemporalCommonStockSourceSeriesIssue.INSUFFICIENT_DISTINCT_ACCESSIONS)
    descriptive_signals = _signals(observations)
    ordered_issues = _ordered(issues)
    status = _series_status(
        common, ordered_issues, observations, len(ordered_requests),
        positive_selection_count)
    return SecTemporalCommonStockSourceSeriesAssessment(
        CONTRACT_VERSION,
        status,
        SEC_NASDAQ_TEMPORAL_COMMON_STOCK_SOURCE_SERIES_V1,
        common.current_authority_boundary,
        common,
        assessments,
        observations,
        len(observations),
        descriptive_signals,
        ordered_issues,
    )
