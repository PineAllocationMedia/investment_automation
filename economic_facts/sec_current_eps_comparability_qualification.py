"""PR5C qualification of one real comparable five-period EPS presentation.

This module freshly replays PR5B, PR5C0A, PR5C0B and one controlled SEC
five-period presentation.  It establishes historical presentation comparability
only.  It never establishes the basis of a later/current market quote.
"""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum, StrEnum

from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_current_security_eps_qualification import (
    QualificationStatus as SecurityQualificationStatus,
    SecCurrentSecurityEPSQualification,
    SecCurrentSecurityEPSQualificationRequest,
    qualify_sec_current_security_eps,
)
from .sec_eps_series import FilingVersionReference
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_five_year_eps_presentation import (
    PresentationStatus,
    SecFiveYearEPSPresentation,
    SecFiveYearEPSPresentationRequest,
    extract_sec_five_year_eps_presentation,
)
from .sec_reporting_subject_source_claims import (
    ReportingSubjectClaimKind,
    ReportingSubjectSourceStatus,
    SecReportingSubjectSourceAssessment,
    SecReportingSubjectSourceRequest,
    build_sec_reporting_subject_source_foundation,
)
from .sec_share_basis_source_claims import (
    CorporateActionKind,
    CorporateActionLifecycle,
    RetrospectivePresentationScope,
    SecShareBasisSourceAssessment,
    SecShareBasisSourceRequest,
    SecurityClassSourceScope,
    ShareBasisClaimKind,
    ShareBasisSourceStatus,
    build_sec_share_basis_source_foundation,
)
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_ticker_exchange_archive import SecTickerExchangeArchive


CONTRACT_VERSION = "2026-09-28-sec-current-eps-comparability-v1"
QUALIFIER_VERSION = "2026-09-28-positive-five-period-presentation-v1"
QUALIFICATION_MODE = "CURRENT_SEC_SINGLE_PRESENTATION_HISTORICAL_COMPARABILITY"


class SecCurrentEPSComparabilityError(ValueError):
    """Invalid closed request, replay identity, or public argument."""


class ComparabilityOutcome(StrEnum):
    COMPARABLE_REAL_EPS_ESTABLISHED = "COMPARABLE_REAL_EPS_ESTABLISHED"
    COMPARABILITY_UNAVAILABLE = "COMPARABILITY_UNAVAILABLE"
    COMPARABILITY_UNSUPPORTED = "COMPARABILITY_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class DimensionOutcome(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTED = "CONFLICTED"


class PeriodOutcome(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    PRESENTATION_PERIOD_MISSING = "PRESENTATION_PERIOD_MISSING"
    PRESENTATION_VALUE_MISMATCH = "PRESENTATION_VALUE_MISMATCH"


class ComparabilityReason(StrEnum):
    PR5B_QUALIFICATION_NOT_ESTABLISHED = "PR5B_QUALIFICATION_NOT_ESTABLISHED"
    C3_SERIES_NOT_AVAILABLE = "C3_SERIES_NOT_AVAILABLE"
    PRESENTATION_NOT_AVAILABLE = "PRESENTATION_NOT_AVAILABLE"
    PRESENTATION_PROFILE_UNSUPPORTED = "PRESENTATION_PROFILE_UNSUPPORTED"
    PRESENTATION_SOURCE_CONFLICT = "PRESENTATION_SOURCE_CONFLICT"
    PRESENTATION_FOREIGN_TO_PR5B_ROUTE = "PRESENTATION_FOREIGN_TO_PR5B_ROUTE"
    SOURCE_GRAPH_FOREIGN_TO_PR5B_ROUTE = "SOURCE_GRAPH_FOREIGN_TO_PR5B_ROUTE"
    PRESENTATION_AFTER_CURRENT_BOUNDARY = "PRESENTATION_AFTER_CURRENT_BOUNDARY"
    FIVE_PERIOD_COVERAGE_NOT_EXACT = "FIVE_PERIOD_COVERAGE_NOT_EXACT"
    PRESENTED_EPS_VALUE_MISMATCH = "PRESENTED_EPS_VALUE_MISMATCH"
    REPORTING_SUBJECT_SOURCE_INCOMPLETE = "REPORTING_SUBJECT_SOURCE_INCOMPLETE"
    REPORTING_SUBJECT_SOURCE_UNSUPPORTED = "REPORTING_SUBJECT_SOURCE_UNSUPPORTED"
    REPORTING_SUBJECT_SOURCE_CONFLICT = "REPORTING_SUBJECT_SOURCE_CONFLICT"
    REPORTING_SUBJECT_TRANSITION_DETECTED = "REPORTING_SUBJECT_TRANSITION_DETECTED"
    SHARE_BASIS_SOURCE_INCOMPLETE = "SHARE_BASIS_SOURCE_INCOMPLETE"
    SHARE_BASIS_SOURCE_UNSUPPORTED = "SHARE_BASIS_SOURCE_UNSUPPORTED"
    SHARE_BASIS_SOURCE_CONFLICT = "SHARE_BASIS_SOURCE_CONFLICT"
    UNSUPPORTED_BASIS_AFFECTING_TRANSFORMATION = (
        "UNSUPPORTED_BASIS_AFFECTING_TRANSFORMATION"
    )
    ACTION_LIFECYCLE_UNRESOLVED = "ACTION_LIFECYCLE_UNRESOLVED"
    ACTION_CLASS_LINKAGE_UNSUPPORTED = "ACTION_CLASS_LINKAGE_UNSUPPORTED"
    SPLIT_TERMS_NOT_EXACT = "SPLIT_TERMS_NOT_EXACT"
    RETROSPECTIVE_PRESENTATION_NOT_ESTABLISHED = (
        "RETROSPECTIVE_PRESENTATION_NOT_ESTABLISHED"
    )
    MULTIPLE_CLASS_BASIS_AMBIGUITY = "MULTIPLE_CLASS_BASIS_AMBIGUITY"


class ComparabilityLimitation(StrEnum):
    HISTORICAL_PRESENTATION_BOUNDARY_ONLY = "HISTORICAL_PRESENTATION_BOUNDARY_ONLY"
    CURRENT_QUOTE_BASIS_NOT_ESTABLISHED = "CURRENT_QUOTE_BASIS_NOT_ESTABLISHED"
    PR5D_QUOTE_TO_EPS_BASIS_BRIDGE_REQUIRED = (
        "PR5D_QUOTE_TO_EPS_BASIS_BRIDGE_REQUIRED"
    )
    PR5E_FINAL_ADMISSION_REQUIRED = "PR5E_FINAL_ADMISSION_REQUIRED"
    NO_EPS_NORMALIZATION = "NO_EPS_NORMALIZATION"
    NO_ACTION_HISTORY_COMPLETENESS_CLAIM = "NO_ACTION_HISTORY_COMPLETENESS_CLAIM"
    EMPTY_ACTION_INVENTORY_IS_NOT_NO_ACTION_EVIDENCE = (
        "EMPTY_ACTION_INVENTORY_IS_NOT_NO_ACTION_EVIDENCE"
    )
    NO_UNIVERSAL_REPORTING_SUBJECT_CONTINUITY = (
        "NO_UNIVERSAL_REPORTING_SUBJECT_CONTINUITY"
    )
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_PRICE_OR_EXPECTED_RETURN = "NO_PRICE_OR_EXPECTED_RETURN"


@dataclass(frozen=True, slots=True)
class SecCurrentEPSComparabilityRequest:
    security_eps_request: SecCurrentSecurityEPSQualificationRequest
    expected_security_eps_semantic_id: str
    expected_security_eps_evidence_id: str
    expected_c3_semantic_id: str
    expected_c3_evidence_id: str
    reporting_subject_source_request: SecReportingSubjectSourceRequest
    expected_reporting_subject_semantic_id: str
    expected_reporting_subject_evidence_id: str
    share_basis_source_request: SecShareBasisSourceRequest
    expected_share_basis_semantic_id: str
    expected_share_basis_evidence_id: str
    presentation_request: SecFiveYearEPSPresentationRequest
    expected_presentation_semantic_id: str
    expected_presentation_evidence_id: str

    def __post_init__(self):
        typed = (
            type(self.security_eps_request) is SecCurrentSecurityEPSQualificationRequest,
            type(self.reporting_subject_source_request) is SecReportingSubjectSourceRequest,
            type(self.share_basis_source_request) is SecShareBasisSourceRequest,
            type(self.presentation_request) is SecFiveYearEPSPresentationRequest,
        )
        hashes = tuple(getattr(self, field.name) for field in fields(self)
                       if field.name.startswith("expected_"))
        if (not all(typed) or any(type(value) is not str or len(value) != 64
                                  or any(character not in "0123456789abcdef"
                                         for character in value)
                                  for value in hashes)):
            raise SecCurrentEPSComparabilityError(
                "Exact typed selectors and lowercase SHA-256 replay identities required")


@dataclass(frozen=True, slots=True)
class HistoricalShareBasisConclusion:
    outcome: DimensionOutcome
    qualified_basis_identity: str | None
    considered_claim_semantic_ids: tuple[str, ...]
    retrospective_claim_semantic_ids: tuple[str, ...]
    reasons: tuple[ComparabilityReason, ...]


@dataclass(frozen=True, slots=True)
class HistoricalReportingSubjectConclusion:
    outcome: DimensionOutcome
    qualified_subject_identity: str | None
    considered_claim_semantic_ids: tuple[str, ...]
    reasons: tuple[ComparabilityReason, ...]


@dataclass(frozen=True, slots=True)
class ComparableEPSPeriodDecision:
    period_start: str
    period_end: str
    c3_value: Decimal
    presented_value: Decimal | None
    presentation_period_label: str | None
    representative_observation_id: str
    supporting_observation_ids: tuple[str, ...]
    version_ids: tuple[str, ...]
    filing_versions: tuple[FilingVersionReference, ...]
    outcome: PeriodOutcome
    reasons: tuple[ComparabilityReason, ...]


@dataclass(frozen=True, slots=True)
class RealEPSComparabilityQualification:
    contract_version: str
    qualifier_version: str
    qualification_mode: str
    security_eps_semantic_id: str
    security_eps_evidence_id: str
    c3_semantic_id: str
    c3_evidence_id: str
    reporting_subject_source_semantic_id: str
    reporting_subject_source_evidence_id: str
    share_basis_source_semantic_id: str
    share_basis_source_evidence_id: str
    presentation_semantic_id: str
    presentation_evidence_id: str
    presentation_boundary: str | None
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    historical_share_basis: HistoricalShareBasisConclusion
    historical_reporting_subject: HistoricalReportingSubjectConclusion
    period_decisions: tuple[ComparableEPSPeriodDecision, ...]
    outcome: ComparabilityOutcome
    reasons: tuple[ComparabilityReason, ...]
    limitations: tuple[ComparabilityLimitation, ...]
    upstream_security_eps: SecCurrentSecurityEPSQualification
    upstream_reporting_subject_source: SecReportingSubjectSourceAssessment
    upstream_share_basis_source: SecShareBasisSourceAssessment
    presentation: SecFiveYearEPSPresentation

    @property
    def semantic_id(self):
        return _identity("qualification-semantics", {
            "contract": self.contract_version,
            "qualifier": self.qualifier_version,
            "mode": self.qualification_mode,
            "security_eps_semantic_id": self.security_eps_semantic_id,
            "c3_semantic_id": self.c3_semantic_id,
            "reporting_subject_source_semantic_id":
                self.reporting_subject_source_semantic_id,
            "share_basis_source_semantic_id": self.share_basis_source_semantic_id,
            "presentation_semantic_id": self.presentation_semantic_id,
            "presentation_boundary": self.presentation_boundary,
            "issuer_key": self.route_local_issuer_key,
            "security_key": self.route_local_security_key,
            "historical_share_basis": self.historical_share_basis,
            "historical_reporting_subject": self.historical_reporting_subject,
            "period_decisions": self.period_decisions,
            "outcome": self.outcome,
            "reasons": self.reasons,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("qualification-evidence", {
            "semantic_id": self.semantic_id,
            "security_eps_evidence_id": self.security_eps_evidence_id,
            "c3_evidence_id": self.c3_evidence_id,
            "reporting_subject_source_evidence_id":
                self.reporting_subject_source_evidence_id,
            "share_basis_source_evidence_id": self.share_basis_source_evidence_id,
            "presentation_evidence_id": self.presentation_evidence_id,
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        parts = value.as_tuple()
        return {"sign": parts.sign, "digits": list(parts.digits),
                "exponent": parts.exponent}
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    return value


def _identity(domain, value):
    return digest(("pam:sec-current-eps-comparability:" + domain + ":v1\0").encode(
        "ascii") + canonical_json(_project(value)))


def _ordered(values):
    return tuple(sorted(set(values), key=lambda item: item.value))


def _series(security):
    return security.upstream_registered_listing_bridge.temporal_boundary.current_evidence.resolution.series


def _verify_replay(request, security, series, subject, basis, presentation):
    identities = (
        (security.semantic_id, request.expected_security_eps_semantic_id),
        (security.evidence_id, request.expected_security_eps_evidence_id),
        (None if series is None else series.semantic_hash, request.expected_c3_semantic_id),
        (None if series is None else series.evidence_hash, request.expected_c3_evidence_id),
        (subject.semantic_id, request.expected_reporting_subject_semantic_id),
        (subject.evidence_id, request.expected_reporting_subject_evidence_id),
        (basis.semantic_id, request.expected_share_basis_semantic_id),
        (basis.evidence_id, request.expected_share_basis_evidence_id),
        (presentation.semantic_id, request.expected_presentation_semantic_id),
        (presentation.evidence_id, request.expected_presentation_evidence_id),
    )
    if any(actual != expected for actual, expected in identities):
        raise SecCurrentEPSComparabilityError("Fresh replay identity mismatch")


def _periods(series, presentation):
    values = {item.period_end: item for item in presentation.values}
    decisions = []
    for period in (() if series is None else series.periods):
        presented = values.get(period.period_end)
        if presented is None:
            outcome = PeriodOutcome.PRESENTATION_PERIOD_MISSING
            reasons = (ComparabilityReason.FIVE_PERIOD_COVERAGE_NOT_EXACT,)
        elif presented.value != period.value:
            outcome = PeriodOutcome.PRESENTATION_VALUE_MISMATCH
            reasons = (ComparabilityReason.PRESENTED_EPS_VALUE_MISMATCH,)
        else:
            outcome = PeriodOutcome.EXACT_MATCH
            reasons = ()
        decisions.append(ComparableEPSPeriodDecision(
            period.period_start, period.period_end, period.value,
            None if presented is None else presented.value,
            None if presented is None else presented.period_label,
            period.representative_observation_id,
            period.supporting_observation_ids, period.version_ids,
            period.filing_versions, outcome, reasons))
    return tuple(decisions)


def _assessment_contains_presentation(assessment, presentation):
    for filing in assessment.filing_universe:
        if filing.accession != presentation.accession:
            continue
        for capture in filing.captures:
            inventory = capture.document_inventory
            if (inventory is not None
                    and any(document.semantic_id == presentation.document_semantic_id
                            for document in inventory.documents)):
                return True
    return False


_BLOCKING_SUBJECT_CLAIMS = frozenset((
    ReportingSubjectClaimKind.PREDECESSOR_SUCCESSOR_TRANSITION,
    ReportingSubjectClaimKind.ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY,
    ReportingSubjectClaimKind.REVERSE_ACQUISITION_REFERENCE,
    ReportingSubjectClaimKind.REVERSE_RECAPITALIZATION_REFERENCE,
    ReportingSubjectClaimKind.PREDECESSOR_PERIOD_LABEL,
    ReportingSubjectClaimKind.SUCCESSOR_PERIOD_LABEL,
    ReportingSubjectClaimKind.CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE,
    ReportingSubjectClaimKind.COMBINED_FINANCIAL_STATEMENTS_REFERENCE,
    ReportingSubjectClaimKind.UNINTERPRETED_RESTRUCTURING_LANGUAGE,
))


def _subject_conclusion(subject, *, route_ok, foreign):
    reasons = set()
    if subject.status is ReportingSubjectSourceStatus.SOURCE_CONFLICT or foreign:
        reasons.add(ComparabilityReason.REPORTING_SUBJECT_SOURCE_CONFLICT)
        outcome = DimensionOutcome.CONFLICTED
    elif subject.status is ReportingSubjectSourceStatus.INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET:
        reasons.add(ComparabilityReason.REPORTING_SUBJECT_SOURCE_INCOMPLETE)
        outcome = DimensionOutcome.UNAVAILABLE
    elif subject.status is ReportingSubjectSourceStatus.UNSUPPORTED_SOURCE_PROFILE:
        reasons.add(ComparabilityReason.REPORTING_SUBJECT_SOURCE_UNSUPPORTED)
        outcome = DimensionOutcome.UNSUPPORTED
    elif any(claim.kind in _BLOCKING_SUBJECT_CLAIMS for claim in subject.explicit_claims):
        reasons.add(ComparabilityReason.REPORTING_SUBJECT_TRANSITION_DETECTED)
        outcome = DimensionOutcome.UNSUPPORTED
    elif not route_ok:
        reasons.add(ComparabilityReason.PR5B_QUALIFICATION_NOT_ESTABLISHED)
        outcome = DimensionOutcome.UNAVAILABLE
    else:
        outcome = DimensionOutcome.ESTABLISHED
    claim_ids = tuple(sorted(claim.semantic_id for claim in subject.explicit_claims))
    qualified = None
    if outcome is DimensionOutcome.ESTABLISHED:
        qualified = _identity("qualified-historical-reporting-subject", {
            "source_cik": subject.source_cik,
            "presentation_semantic_id": None,
            "considered_claims": claim_ids,
        })
    return HistoricalReportingSubjectConclusion(
        outcome, qualified, claim_ids, _ordered(reasons))


_SPLIT_ACTIONS = frozenset((
    CorporateActionKind.STOCK_SPLIT,
    CorporateActionKind.REVERSE_STOCK_SPLIT,
    CorporateActionKind.STOCK_DIVIDEND,
))
_UNSUPPORTED_ACTIONS = frozenset((
    CorporateActionKind.SHARE_CLASS_CONVERSION,
    CorporateActionKind.RECAPITALIZATION,
    CorporateActionKind.MERGER_SECURITY_EXCHANGE,
    CorporateActionKind.SPIN_OFF,
    CorporateActionKind.SHARE_REDENOMINATION,
    CorporateActionKind.SHARE_CONSOLIDATION,
    CorporateActionKind.OTHER_BASIS_AFFECTING_ACTION,
))
_RETROSPECTIVE_KINDS = frozenset((
    ShareBasisClaimKind.RETROACTIVE_PER_SHARE_ADJUSTMENT_REFERENCE,
    ShareBasisClaimKind.HISTORICAL_EPS_ADJUSTED_FOR_ACTION_REFERENCE,
))


def _basis_conclusion(basis, presentation, class_label, *, route_ok, foreign):
    reasons = set()
    retrospective = tuple(claim for claim in basis.explicit_claims
                          if claim.kind in _RETROSPECTIVE_KINDS)
    action_claims = tuple(claim for claim in basis.explicit_claims
                          if claim.action_kind is not None)
    if basis.status is ShareBasisSourceStatus.SOURCE_CONFLICT or foreign:
        reasons.add(ComparabilityReason.SHARE_BASIS_SOURCE_CONFLICT)
        outcome = DimensionOutcome.CONFLICTED
    elif basis.status is ShareBasisSourceStatus.INCOMPLETE_SHARE_BASIS_SOURCE_SET:
        reasons.add(ComparabilityReason.SHARE_BASIS_SOURCE_INCOMPLETE)
        outcome = DimensionOutcome.UNAVAILABLE
    elif basis.status is ShareBasisSourceStatus.UNSUPPORTED_SOURCE_PROFILE:
        reasons.add(ComparabilityReason.SHARE_BASIS_SOURCE_UNSUPPORTED)
        outcome = DimensionOutcome.UNSUPPORTED
    else:
        for claim in action_claims:
            if claim.lifecycle is CorporateActionLifecycle.CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE:
                continue
            if claim.class_link.scope is SecurityClassSourceScope.MULTIPLE_CLASSES_OR_AMBIGUOUS:
                reasons.add(ComparabilityReason.MULTIPLE_CLASS_BASIS_AMBIGUITY)
            if claim.action_kind in _UNSUPPORTED_ACTIONS:
                reasons.add(ComparabilityReason.UNSUPPORTED_BASIS_AFFECTING_TRANSFORMATION)
            elif claim.lifecycle is not CorporateActionLifecycle.EFFECTIVE_OR_IMPLEMENTED_REFERENCE:
                reasons.add(ComparabilityReason.ACTION_LIFECYCLE_UNRESOLVED)
            elif claim.ratio is None or claim.effective_date is None:
                reasons.add(ComparabilityReason.SPLIT_TERMS_NOT_EXACT)
            elif (claim.class_link.scope is not SecurityClassSourceScope.NAMED_COMMON_CLASS_EXPLICIT
                  or class_label not in claim.class_link.normalized_source_labels):
                reasons.add(ComparabilityReason.ACTION_CLASS_LINKAGE_UNSUPPORTED)
            elif claim.action_kind in _SPLIT_ACTIONS:
                matched = tuple(item for item in retrospective
                                if item.accession == presentation.accession
                                and item.document_semantic_id == presentation.document_semantic_id
                                and item.source_local_action_key ==
                                claim.source_local_action_key
                                and item.retrospective_scope is
                                RetrospectivePresentationScope.ALL_PERIODS_PRESENTED
                                and item.class_link.scope is
                                SecurityClassSourceScope.NAMED_COMMON_CLASS_EXPLICIT
                                and class_label in item.class_link.normalized_source_labels)
                if not matched:
                    reasons.add(
                        ComparabilityReason.RETROSPECTIVE_PRESENTATION_NOT_ESTABLISHED)
        if not route_ok:
            reasons.add(ComparabilityReason.PR5B_QUALIFICATION_NOT_ESTABLISHED)
        if reasons & {ComparabilityReason.SHARE_BASIS_SOURCE_CONFLICT}:
            outcome = DimensionOutcome.CONFLICTED
        elif reasons & {
            ComparabilityReason.UNSUPPORTED_BASIS_AFFECTING_TRANSFORMATION,
            ComparabilityReason.MULTIPLE_CLASS_BASIS_AMBIGUITY,
            ComparabilityReason.SHARE_BASIS_SOURCE_UNSUPPORTED,
        }:
            outcome = DimensionOutcome.UNSUPPORTED
        elif reasons:
            outcome = DimensionOutcome.UNAVAILABLE
        else:
            outcome = DimensionOutcome.ESTABLISHED
    claim_ids = tuple(sorted(claim.semantic_id for claim in basis.explicit_claims))
    retro_ids = tuple(sorted(claim.semantic_id for claim in retrospective))
    qualified = None
    if outcome is DimensionOutcome.ESTABLISHED:
        qualified = _identity("qualified-historical-share-basis", {
            "security_class": class_label,
            "presentation_semantic_id": presentation.semantic_id,
            "considered_claims": claim_ids,
            "retrospective_claims": retro_ids,
        })
    return HistoricalShareBasisConclusion(
        outcome, qualified, claim_ids, retro_ids, _ordered(reasons))


def qualify_sec_current_eps_comparability(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentEPSComparabilityRequest,
) -> RealEPSComparabilityQualification:
    """Freshly replay and qualify one historical five-period presentation."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecCurrentEPSComparabilityRequest):
        raise SecCurrentEPSComparabilityError("Exact typed archives/request required")

    security = qualify_sec_current_security_eps(
        current_archive, submissions_archive, filing_archive,
        ticker_exchange_archive, nasdaq_listed_archive, request.security_eps_request)
    subject = build_sec_reporting_subject_source_foundation(
        submissions_archive, filing_archive, request.reporting_subject_source_request)
    basis = build_sec_share_basis_source_foundation(
        submissions_archive, filing_archive, request.share_basis_source_request)
    presentation = extract_sec_five_year_eps_presentation(
        filing_archive, request.presentation_request)
    series = _series(security)
    _verify_replay(request, security, series, subject, basis, presentation)

    reasons = set()
    route_ok = (security.status is SecurityQualificationStatus.
                CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED)
    if not route_ok:
        reasons.add(ComparabilityReason.PR5B_QUALIFICATION_NOT_ESTABLISHED)
    if series is None:
        reasons.add(ComparabilityReason.C3_SERIES_NOT_AVAILABLE)
    if presentation.status is PresentationStatus.PRESENTATION_UNAVAILABLE:
        reasons.add(ComparabilityReason.PRESENTATION_NOT_AVAILABLE)
    elif presentation.status is PresentationStatus.PRESENTATION_UNSUPPORTED:
        reasons.add(ComparabilityReason.PRESENTATION_PROFILE_UNSUPPORTED)
    elif presentation.status is PresentationStatus.SOURCE_CONFLICT:
        reasons.add(ComparabilityReason.PRESENTATION_SOURCE_CONFLICT)

    application_accessions = {
        item.accession for item in security.eps_applicability_decisions
    }
    route_inventory = (security.upstream_registered_listing_bridge.temporal_boundary
                       .temporal_dossier.inventory)
    source_graph_foreign = (
        subject.submissions_inventory.semantic_id != route_inventory.semantic_id
        or basis.submissions_inventory.semantic_id != route_inventory.semantic_id
        or not _assessment_contains_presentation(subject, presentation)
        or not _assessment_contains_presentation(basis, presentation)
    )
    foreign = (presentation.source_cik != subject.source_cik
               or presentation.source_cik != basis.source_cik
               or (security.direct_listing.source_cik is not None
                   and presentation.source_cik != security.direct_listing.source_cik))
    if foreign or presentation.accession not in application_accessions:
        reasons.add(ComparabilityReason.PRESENTATION_FOREIGN_TO_PR5B_ROUTE)
    if source_graph_foreign:
        reasons.add(ComparabilityReason.SOURCE_GRAPH_FOREIGN_TO_PR5B_ROUTE)
    if (security.current_authority_boundary is not None
            and presentation.filing_captured_at > security.current_authority_boundary):
        reasons.add(ComparabilityReason.PRESENTATION_AFTER_CURRENT_BOUNDARY)

    decisions = _periods(series, presentation)
    expected_ends = set() if series is None else {period.period_end for period in series.periods}
    presented_ends = {item.period_end for item in presentation.values}
    if (len(expected_ends) != 5 or len(presented_ends) != 5
            or expected_ends != presented_ends
            or any(item.outcome is PeriodOutcome.PRESENTATION_PERIOD_MISSING
                   for item in decisions)):
        reasons.add(ComparabilityReason.FIVE_PERIOD_COVERAGE_NOT_EXACT)
    if any(item.outcome is PeriodOutcome.PRESENTATION_VALUE_MISMATCH
           for item in decisions):
        reasons.add(ComparabilityReason.PRESENTED_EPS_VALUE_MISMATCH)

    class_label = security.participation.canonical_source_class_label or ""
    subject_conclusion = _subject_conclusion(
        subject, route_ok=route_ok, foreign=foreign or source_graph_foreign)
    if subject_conclusion.outcome is DimensionOutcome.ESTABLISHED:
        subject_conclusion = HistoricalReportingSubjectConclusion(
            subject_conclusion.outcome,
            _identity("qualified-historical-reporting-subject", {
                "route_local_issuer_key": security.route_local_issuer_key,
                "source_cik": subject.source_cik,
                "presentation_semantic_id": presentation.semantic_id,
                "considered_claims": subject_conclusion.considered_claim_semantic_ids,
            }),
            subject_conclusion.considered_claim_semantic_ids,
            subject_conclusion.reasons,
        )
    basis_conclusion = _basis_conclusion(
        basis, presentation, class_label, route_ok=route_ok,
        foreign=foreign or source_graph_foreign)
    reasons.update(subject_conclusion.reasons)
    reasons.update(basis_conclusion.reasons)

    if (reasons & {
            ComparabilityReason.PRESENTATION_SOURCE_CONFLICT,
            ComparabilityReason.PRESENTED_EPS_VALUE_MISMATCH,
            ComparabilityReason.REPORTING_SUBJECT_SOURCE_CONFLICT,
            ComparabilityReason.SHARE_BASIS_SOURCE_CONFLICT,
            ComparabilityReason.PRESENTATION_FOREIGN_TO_PR5B_ROUTE,
            ComparabilityReason.SOURCE_GRAPH_FOREIGN_TO_PR5B_ROUTE,
    } or subject_conclusion.outcome is DimensionOutcome.CONFLICTED
            or basis_conclusion.outcome is DimensionOutcome.CONFLICTED):
        outcome = ComparabilityOutcome.SOURCE_CONFLICT
    elif (reasons & {
            ComparabilityReason.PRESENTATION_PROFILE_UNSUPPORTED,
            ComparabilityReason.REPORTING_SUBJECT_SOURCE_UNSUPPORTED,
            ComparabilityReason.REPORTING_SUBJECT_TRANSITION_DETECTED,
            ComparabilityReason.SHARE_BASIS_SOURCE_UNSUPPORTED,
            ComparabilityReason.UNSUPPORTED_BASIS_AFFECTING_TRANSFORMATION,
            ComparabilityReason.MULTIPLE_CLASS_BASIS_AMBIGUITY,
    } or subject_conclusion.outcome is DimensionOutcome.UNSUPPORTED
            or basis_conclusion.outcome is DimensionOutcome.UNSUPPORTED):
        outcome = ComparabilityOutcome.COMPARABILITY_UNSUPPORTED
    elif reasons:
        outcome = ComparabilityOutcome.COMPARABILITY_UNAVAILABLE
    else:
        outcome = ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED

    if outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED:
        if subject_conclusion.qualified_subject_identity is not None:
            subject_conclusion = HistoricalReportingSubjectConclusion(
                subject_conclusion.outcome, None,
                subject_conclusion.considered_claim_semantic_ids,
                subject_conclusion.reasons)
        if basis_conclusion.qualified_basis_identity is not None:
            basis_conclusion = HistoricalShareBasisConclusion(
                basis_conclusion.outcome, None,
                basis_conclusion.considered_claim_semantic_ids,
                basis_conclusion.retrospective_claim_semantic_ids,
                basis_conclusion.reasons)

    limitations = tuple(ComparabilityLimitation)
    return RealEPSComparabilityQualification(
        CONTRACT_VERSION, QUALIFIER_VERSION, QUALIFICATION_MODE,
        security.semantic_id, security.evidence_id,
        request.expected_c3_semantic_id, request.expected_c3_evidence_id,
        subject.semantic_id, subject.evidence_id, basis.semantic_id, basis.evidence_id,
        presentation.semantic_id, presentation.evidence_id,
        None if presentation.table_sha256 is None else presentation.filing_captured_at,
        security.route_local_issuer_key, security.route_local_security_key,
        basis_conclusion, subject_conclusion, decisions, outcome, _ordered(reasons),
        limitations, security, subject, basis, presentation)
