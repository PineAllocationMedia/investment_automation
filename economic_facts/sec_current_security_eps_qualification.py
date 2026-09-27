"""Narrow CURRENT SEC/Nasdaq security and diluted-EPS qualification.

This PR5B adapter freshly replays the controlled D4D3B evidence graph and makes
one route-local qualification decision.  It is not final economic admission and
does not qualify share basis, reporting subject, quote semantics, price, or
Expected Return inputs.
"""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum, StrEnum
import re

from .current_authority import AssessmentStatus
from .nasdaq_listed_archive import NasdaqListedArchive
from .sec_archive import SecArchive
from .sec_class_eps_claims import (
    ExtractionStatus as ClassEPSExtractionStatus,
    SourceFactKind,
)
from .sec_current_common_stock_class_bridge import ClassBridgeAssessmentStatus
from .sec_current_registered_listing_bridge import BridgeAssessmentStatus
from .sec_current_registered_listing_bridge import (
    SecCurrentRegisteredListingBridgeAssessment,
    assess_sec_current_registered_listing_bridge,
)
from .sec_eps_series import AdmissionBlocker, ResolutionStatus
from .sec_filing_archive import SecFilingArchive, canonical_json, digest
from .sec_property4_temporal_boundary import (
    BoundaryAssessmentStatus,
    FilingBoundaryStatus,
)
from .sec_registered_securities import ExtractionStatus as RegisteredSecurityExtractionStatus
from .sec_submissions_archive import SecSubmissionsArchive
from .sec_temporal_common_stock_source_series import (
    SecTemporalCommonStockSourceSeriesAssessment,
    SecTemporalCommonStockSourceSeriesRequest,
    TemporalCommonStockSourceSeriesIssue,
    TemporalCommonStockSourceSeriesStatus,
    assess_sec_temporal_common_stock_source_series,
)
from .sec_ticker_exchange_archive import SecTickerExchangeArchive


CONTRACT_VERSION = "2026-09-27-sec-current-security-eps-qualification-v1"
PARTICIPATION_PROFILE_VERSION = (
    "2026-09-27-ordinary-residual-common-participation-v1"
)
RELEVANT_CLASS_COVERAGE_PROFILE_VERSION = (
    "2026-09-27-all-class-eps-relevant-common-coverage-v1"
)
EPS_APPLICABILITY_PROFILE_VERSION = (
    "2026-09-27-retained-c3-version-eps-applicability-v1"
)
ROUTE_PROFILE = "SEC_NASDAQ_CURRENT_ORDINARY_COMMON_EPS_QUALIFICATION_V1"

_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_COMMON_TITLE = re.compile(
    r"(?:COMMON STOCK|CLASS [A-Z0-9] COMMON STOCK)"
    r"(?:, (?:\$[0-9]+(?:\.[0-9]{1,10})? PAR VALUE(?: PER SHARE)?|"
    r"PAR VALUE \$[0-9]+(?:\.[0-9]{1,10})?(?: PER SHARE)?|NO PAR VALUE))?",
    re.ASCII,
)

_DISTRIBUTION_SENTENCES = frozenset((
    "HOLDERS OF OUR COMMON STOCK ARE ENTITLED TO RECEIVE DIVIDENDS WHEN, AS AND IF "
    "DECLARED BY OUR BOARD OF DIRECTORS OUT OF FUNDS LEGALLY AVAILABLE THEREFOR, "
    "SUBJECT TO THE PRIOR RIGHTS OF HOLDERS OF ANY PREFERRED STOCK.",
))
_LIQUIDATION_SENTENCES = frozenset((
    "UPON OUR LIQUIDATION, DISSOLUTION OR WINDING UP, AFTER PAYMENT OF OUR DEBTS AND "
    "OTHER LIABILITIES AND ANY PREFERENCES OF PREFERRED STOCK, HOLDERS OF OUR COMMON "
    "STOCK ARE ENTITLED TO SHARE RATABLY IN THE REMAINING ASSETS.",
))
_OPTIONAL_SENTENCES = frozenset((
    "EACH HOLDER OF OUR COMMON STOCK IS ENTITLED TO ONE VOTE PER SHARE ON EACH MATTER "
    "SUBMITTED TO STOCKHOLDERS.",
    "OUR COMMON STOCK IS NOT REDEEMABLE OR CONVERTIBLE AND HAS NO SINKING FUND.",
))
class SecCurrentSecurityEPSQualificationRequestError(ValueError):
    """Invalid closed selector request or untyped public argument."""


class QualificationStatus(StrEnum):
    CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED = (
        "CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED"
    )
    QUALIFICATION_BLOCKED = "QUALIFICATION_BLOCKED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_QUALIFICATION_PROFILE = "UNSUPPORTED_QUALIFICATION_PROFILE"
    UPSTREAM_CURRENT_AUTHORITY_UNAVAILABLE = "UPSTREAM_CURRENT_AUTHORITY_UNAVAILABLE"


class QualificationIssue(StrEnum):
    CURRENT_AUTHORITY_UNAVAILABLE = "CURRENT_AUTHORITY_UNAVAILABLE"
    C3_SERIES_UNAVAILABLE = "C3_SERIES_UNAVAILABLE"
    CURRENT_BOUNDARY_MISMATCH = "CURRENT_BOUNDARY_MISMATCH"
    ISSUER_CIK_DISAGREEMENT = "ISSUER_CIK_DISAGREEMENT"
    D4C2_CONFLICT_OR_AMBIGUITY = "D4C2_CONFLICT_OR_AMBIGUITY"
    UNSUPPORTED_REGISTERED_LISTING_ROUTE = "UNSUPPORTED_REGISTERED_LISTING_ROUTE"
    SELECTED_DIRECT_LISTING_NOT_UNIQUE = "SELECTED_DIRECT_LISTING_NOT_UNIQUE"
    D4D3A_D4D3B_SOURCE_CONFLICT = "D4D3A_D4D3B_SOURCE_CONFLICT"
    UPSTREAM_EVIDENCE_INCOMPLETE = "UPSTREAM_EVIDENCE_INCOMPLETE"
    UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION = (
        "UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION"
    )
    AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION = (
        "AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION"
    )
    RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED = (
        "RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED"
    )
    OBSERVED_COMPETING_RELEVANT_COMMON_CLASS = (
        "OBSERVED_COMPETING_RELEVANT_COMMON_CLASS"
    )
    D3B_CLASS_EPS_SOURCE_CONFLICT = "D3B_CLASS_EPS_SOURCE_CONFLICT"
    MISSING_EPS_SOURCE_CORRESPONDENCE = "MISSING_EPS_SOURCE_CORRESPONDENCE"
    RETAINED_C3_VERSION_NOT_CONTROLLED = "RETAINED_C3_VERSION_NOT_CONTROLLED"
    RETAINED_C3_VERSION_PERIOD_MISMATCH = "RETAINED_C3_VERSION_PERIOD_MISMATCH"
    RETAINED_C3_VERSION_VALUE_MISMATCH = "RETAINED_C3_VERSION_VALUE_MISMATCH"
    DIMENSIONED_EPS_CLASS_AMBIGUITY = "DIMENSIONED_EPS_CLASS_AMBIGUITY"
    MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT = (
        "MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT"
    )
    EPS_APPLICABILITY_NOT_ESTABLISHED = "EPS_APPLICABILITY_NOT_ESTABLISHED"
    UNSUPPORTED_SOURCE_EXTRACTION_PROFILE = "UNSUPPORTED_SOURCE_EXTRACTION_PROFILE"
    EVIDENCE_AFTER_CURRENT_BOUNDARY = "EVIDENCE_AFTER_CURRENT_BOUNDARY"
    UNSUPPORTED_INSTRUMENT_PROFILE = "UNSUPPORTED_INSTRUMENT_PROFILE"
    EXTRANEOUS_SELECTED_SOURCE_EVIDENCE = "EXTRANEOUS_SELECTED_SOURCE_EVIDENCE"


class ComponentStatus(StrEnum):
    QUALIFICATION_ESTABLISHED = "QUALIFICATION_ESTABLISHED"
    BLOCKED = "BLOCKED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_PROFILE = "UNSUPPORTED_PROFILE"


class QualificationLimitation(StrEnum):
    NO_FINAL_ADMISSION = "NO_FINAL_ADMISSION"
    NO_SHARE_BASIS_QUALIFICATION = "NO_SHARE_BASIS_QUALIFICATION"
    NO_REPORTING_SUBJECT_QUALIFICATION = "NO_REPORTING_SUBJECT_QUALIFICATION"
    NO_QUOTE_CURRENCY_OR_UNIT = "NO_QUOTE_CURRENCY_OR_UNIT"
    NO_PRICE = "NO_PRICE"
    NO_EXPECTED_RETURN = "NO_EXPECTED_RETURN"
    NO_GLOBAL_DURABLE_ID = "NO_GLOBAL_DURABLE_ID"
    NO_COMPLETE_LISTING_INVENTORY = "NO_COMPLETE_LISTING_INVENTORY"
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    SOURCE_CORRESPONDENCE_ONLY_FOR_PROPERTY_4H = (
        "SOURCE_CORRESPONDENCE_ONLY_FOR_PROPERTY_4H"
    )


@dataclass(frozen=True, slots=True)
class SecCurrentSecurityEPSQualificationRequest:
    temporal_source_series_request: SecTemporalCommonStockSourceSeriesRequest

    def __post_init__(self):
        if (type(self.temporal_source_series_request)
                is not SecTemporalCommonStockSourceSeriesRequest):
            raise SecCurrentSecurityEPSQualificationRequestError(
                "Exact temporal source-series request required")


@dataclass(frozen=True, slots=True)
class OrdinaryCommonParticipationQualification:
    profile_version: str
    status: ComponentStatus
    canonical_source_class_label: str | None
    covered_accessions: tuple[str, ...]
    distribution_passage_semantic_ids: tuple[str, ...]
    liquidation_passage_semantic_ids: tuple[str, ...]
    optional_passage_semantic_ids: tuple[str, ...]
    passage_evidence_ids: tuple[str, ...]
    issues: tuple[QualificationIssue, ...]


@dataclass(frozen=True, slots=True)
class RelevantCommonClassCoverageQualification:
    profile_version: str
    status: ComponentStatus
    coverage_semantics: str
    covered_accessions: tuple[str, ...]
    inspected_d3a_semantic_ids: tuple[str, ...]
    inspected_d3b_semantic_ids: tuple[str, ...]
    selected_d3a_source_scopes: tuple[tuple[str, str], ...]
    all_class_common_share_occurrence_ids: tuple[str, ...]
    issues: tuple[QualificationIssue, ...]


@dataclass(frozen=True, slots=True)
class DirectListingSourceQualification:
    status: ComponentStatus
    source_cik: str | None
    source_symbol: str | None
    bridge_profile: str | None
    bridge_candidate_semantic_id: str | None
    bridge_candidate_evidence_id: str | None
    sec_association_row_semantic_id: str | None
    nasdaq_row_semantic_id: str | None
    issues: tuple[QualificationIssue, ...]


@dataclass(frozen=True, slots=True)
class RetainedEPSVersionApplicabilityDecision:
    period_start: str
    period_end: str
    c3_value: Decimal
    c3_version_semantic_id: str
    c3_observation_ids: tuple[str, ...]
    accession: str
    form: str
    filed: str
    source_values: tuple[str, ...]
    d3b_claim_semantic_ids: tuple[str, ...]
    d3b_assessment_semantic_ids: tuple[str, ...]
    d3b_assessment_evidence_ids: tuple[str, ...]
    source_occurrence_ids: tuple[str, ...]
    status: ComponentStatus
    issues: tuple[QualificationIssue, ...]


@dataclass(frozen=True, slots=True)
class SecCurrentSecurityEPSQualification:
    contract_version: str
    route_profile: str
    status: QualificationStatus
    qualified_admission_blockers: tuple[AdmissionBlocker, ...]
    current_authority_boundary: str | None
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    upstream_temporal_source_series: SecTemporalCommonStockSourceSeriesAssessment | None
    upstream_registered_listing_bridge: SecCurrentRegisteredListingBridgeAssessment
    participation: OrdinaryCommonParticipationQualification
    relevant_class_coverage: RelevantCommonClassCoverageQualification
    direct_listing: DirectListingSourceQualification
    eps_applicability_decisions: tuple[RetainedEPSVersionApplicabilityDecision, ...]
    supporting_semantic_ids: tuple[str, ...]
    supporting_evidence_ids: tuple[str, ...]
    issues: tuple[QualificationIssue, ...]
    limitations: tuple[QualificationLimitation, ...]

    @property
    def semantic_id(self):
        participation_semantics = {
            "profile_version": self.participation.profile_version,
            "status": self.participation.status,
            "canonical_source_class_label":
                self.participation.canonical_source_class_label,
            "covered_accessions": self.participation.covered_accessions,
            "distribution_passage_semantic_ids":
                self.participation.distribution_passage_semantic_ids,
            "liquidation_passage_semantic_ids":
                self.participation.liquidation_passage_semantic_ids,
            "optional_passage_semantic_ids":
                self.participation.optional_passage_semantic_ids,
            "issues": self.participation.issues,
        }
        coverage_semantics = {
            "profile_version": self.relevant_class_coverage.profile_version,
            "status": self.relevant_class_coverage.status,
            "coverage_semantics": self.relevant_class_coverage.coverage_semantics,
            "covered_accessions": self.relevant_class_coverage.covered_accessions,
            "inspected_d3a_semantic_ids":
                self.relevant_class_coverage.inspected_d3a_semantic_ids,
            "inspected_d3b_semantic_ids":
                self.relevant_class_coverage.inspected_d3b_semantic_ids,
            "selected_d3a_source_scopes":
                self.relevant_class_coverage.selected_d3a_source_scopes,
            "issues": self.relevant_class_coverage.issues,
        }
        listing_semantics = {
            "status": self.direct_listing.status,
            "source_cik": self.direct_listing.source_cik,
            "source_symbol": self.direct_listing.source_symbol,
            "bridge_profile": self.direct_listing.bridge_profile,
            "bridge_candidate_semantic_id":
                self.direct_listing.bridge_candidate_semantic_id,
            "sec_association_row_semantic_id":
                self.direct_listing.sec_association_row_semantic_id,
            "nasdaq_row_semantic_id": self.direct_listing.nasdaq_row_semantic_id,
            "issues": self.direct_listing.issues,
        }
        eps_semantics = tuple({
            "period_start": item.period_start,
            "period_end": item.period_end,
            "c3_value": item.c3_value,
            "c3_version_semantic_id": item.c3_version_semantic_id,
            "accession": item.accession,
            "form": item.form,
            "filed": item.filed,
            "source_values": item.source_values,
            "d3b_claim_semantic_ids": item.d3b_claim_semantic_ids,
            "d3b_assessment_semantic_ids": item.d3b_assessment_semantic_ids,
            "status": item.status,
            "issues": item.issues,
        } for item in self.eps_applicability_decisions)
        return _identity("qualification-semantics", {
            "contract": self.contract_version,
            "route_profile": self.route_profile,
            "status": self.status,
            "qualified_admission_blockers": self.qualified_admission_blockers,
            "boundary": self.current_authority_boundary,
            "issuer_key": self.route_local_issuer_key,
            "security_key": self.route_local_security_key,
            "upstream_semantic_id": (
                None if self.upstream_temporal_source_series is None
                else self.upstream_temporal_source_series.semantic_id),
            "registered_listing_bridge_semantic_id":
                self.upstream_registered_listing_bridge.semantic_id,
            "participation": participation_semantics,
            "coverage": coverage_semantics,
            "listing": listing_semantics,
            "eps": eps_semantics,
            "supporting_semantic_ids": self.supporting_semantic_ids,
            "issues": self.issues,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("qualification-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_evidence_id": (
                None if self.upstream_temporal_source_series is None
                else self.upstream_temporal_source_series.evidence_id),
            "registered_listing_bridge_evidence_id":
                self.upstream_registered_listing_bridge.evidence_id,
            "supporting_evidence_ids": self.supporting_evidence_ids,
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        item = value.as_tuple()
        return {"sign": item.sign, "digits": list(item.digits), "exponent": item.exponent}
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    return value


def _identity(domain, value):
    return digest(("pam:sec-current-security-eps-qualification:" + domain
                   + ":v1\0").encode("ascii") + canonical_json(_project(value)))


def _ordered(issues):
    return tuple(sorted(set(issues), key=lambda issue: issue.value))


def _normalized_text(value):
    return " ".join(value.split()).translate(_ASCII_UPPER)


def _common_title(value):
    return (type(value) is str
            and _COMMON_TITLE.fullmatch(_normalized_text(value)) is not None)


def _component_status(issues):
    issue_set = set(issues)
    conflicts = {
        QualificationIssue.ISSUER_CIK_DISAGREEMENT,
        QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY,
        QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT,
        QualificationIssue.AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION,
        QualificationIssue.OBSERVED_COMPETING_RELEVANT_COMMON_CLASS,
        QualificationIssue.D3B_CLASS_EPS_SOURCE_CONFLICT,
        QualificationIssue.MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT,
        QualificationIssue.RETAINED_C3_VERSION_VALUE_MISMATCH,
    }
    unsupported = {
        QualificationIssue.UNSUPPORTED_REGISTERED_LISTING_ROUTE,
        QualificationIssue.UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION,
        QualificationIssue.UNSUPPORTED_SOURCE_EXTRACTION_PROFILE,
        QualificationIssue.UNSUPPORTED_INSTRUMENT_PROFILE,
    }
    if issue_set & conflicts:
        return ComponentStatus.SOURCE_CONFLICT
    if issue_set & unsupported:
        return ComponentStatus.UNSUPPORTED_PROFILE
    if issue_set:
        return ComponentStatus.BLOCKED
    return ComponentStatus.QUALIFICATION_ESTABLISHED


def _upstream_issues(upstream):
    issues = set()
    bridge = upstream.registered_listing_bridge
    boundary = bridge.temporal_boundary
    current = boundary.current_evidence
    if (current.current_authority.status is not AssessmentStatus.EVIDENCE_ESTABLISHED
            or boundary.status is BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE):
        issues.add(QualificationIssue.CURRENT_AUTHORITY_UNAVAILABLE)
    if (current.resolution.status is not ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
            or current.resolution.series is None):
        issues.add(QualificationIssue.C3_SERIES_UNAVAILABLE)
    if bridge.status is BridgeAssessmentStatus.SOURCE_CONFLICT:
        issues.add(QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY)
    elif bridge.status is BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE:
        issues.add(QualificationIssue.UNSUPPORTED_REGISTERED_LISTING_ROUTE)
    elif bridge.status is not BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED:
        issues.add(QualificationIssue.UPSTREAM_EVIDENCE_INCOMPLETE)
    if upstream.status is TemporalCommonStockSourceSeriesStatus.SOURCE_CONFLICT:
        issues.add(QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT)
    elif upstream.status is TemporalCommonStockSourceSeriesStatus.UNSUPPORTED_TEMPORAL_PROFILE:
        issues.add(QualificationIssue.UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION)
    elif upstream.status is not (
            TemporalCommonStockSourceSeriesStatus.
            CAPTURED_TEMPORAL_COMMON_STOCK_SOURCE_SERIES):
        issues.add(QualificationIssue.UPSTREAM_EVIDENCE_INCOMPLETE)
    if any(item in upstream.issues for item in (
            TemporalCommonStockSourceSeriesIssue.SELECTED_RECEIPT_NOT_CONTROLLED_BY_BOUNDARY,
            TemporalCommonStockSourceSeriesIssue.ACCESSION_NOT_IN_TEMPORAL_BOUNDARY,
    )):
        issues.add(QualificationIssue.EVIDENCE_AFTER_CURRENT_BOUNDARY)
    return issues


def _listing_bridge(bridge):
    candidates = tuple(candidate for candidate in bridge.candidates
                       if candidate.status is
                       BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
    issues = set()
    if bridge.status is BridgeAssessmentStatus.SOURCE_CONFLICT:
        issues.add(QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY)
    elif bridge.status is BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE:
        issues.add(QualificationIssue.UNSUPPORTED_REGISTERED_LISTING_ROUTE)
    if len(candidates) != 1:
        issues.add(QualificationIssue.SELECTED_DIRECT_LISTING_NOT_UNIQUE)
    candidate = candidates[0] if len(candidates) == 1 else None
    ordered = _ordered(issues)
    return DirectListingSourceQualification(
        _component_status(ordered),
        None if candidate is None else candidate.source_cik,
        None if candidate is None else candidate.source_symbol,
        None if candidate is None else candidate.profile,
        None if candidate is None else candidate.semantic_id,
        None if candidate is None else candidate.evidence_id,
        None if candidate is None else candidate.sec_association_row_semantic_id,
        None if candidate is None else candidate.nasdaq_row_semantic_id,
        ordered,
    ), candidate


def _has_unsupported_extraction(boundary):
    return any(
        any(item.value in {"D3A_UNSUPPORTED_SOURCE", "D3B_UNSUPPORTED_SOURCE"}
            for item in capture.issues)
        for filing in boundary.temporal_dossier.filings
        for capture in filing.captures
    )


def _unsupported_qualification(bridge):
    issue = QualificationIssue.UNSUPPORTED_SOURCE_EXTRACTION_PROFILE
    issues = (issue,)
    participation = OrdinaryCommonParticipationQualification(
        PARTICIPATION_PROFILE_VERSION, ComponentStatus.UNSUPPORTED_PROFILE,
        None, (), (), (), (), (), issues)
    coverage = RelevantCommonClassCoverageQualification(
        RELEVANT_CLASS_COVERAGE_PROFILE_VERSION, ComponentStatus.UNSUPPORTED_PROFILE,
        "UNDIMENSIONED_ALL_CLASS_COMMON_SHARES_AND_DILUTED_EPS",
        (), (), (), (), (), issues)
    listing, _candidate = _listing_bridge(bridge)
    combined_issues = set(issues) | set(listing.issues)
    boundary = bridge.temporal_boundary
    current = boundary.current_evidence
    if (current.current_authority.status is not AssessmentStatus.EVIDENCE_ESTABLISHED
            or boundary.status is BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE
            or bridge.status is BridgeAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE):
        combined_issues.add(QualificationIssue.CURRENT_AUTHORITY_UNAVAILABLE)
    if (current.resolution.status is not ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
            or current.resolution.series is None):
        combined_issues.add(QualificationIssue.C3_SERIES_UNAVAILABLE)
    if bridge.status is BridgeAssessmentStatus.SOURCE_CONFLICT:
        combined_issues.add(QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY)
    elif bridge.status is BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE:
        combined_issues.add(QualificationIssue.UNSUPPORTED_REGISTERED_LISTING_ROUTE)
    combined = _ordered(combined_issues)
    return SecCurrentSecurityEPSQualification(
        CONTRACT_VERSION,
        ROUTE_PROFILE,
        _qualification_status(combined),
        (),
        bridge.current_authority_boundary,
        None,
        None,
        None,
        bridge,
        participation,
        coverage,
        listing,
        (),
        tuple(sorted({bridge.semantic_id, PARTICIPATION_PROFILE_VERSION,
                      RELEVANT_CLASS_COVERAGE_PROFILE_VERSION,
                      EPS_APPLICABILITY_PROFILE_VERSION})),
        (bridge.evidence_id,),
        combined,
        tuple(sorted(QualificationLimitation, key=lambda item: item.value)),
    )


def _participation(upstream, required_accessions):
    issues = set()
    distribution, liquidation, optional, evidence = set(), set(), set(), set()
    covered = set()
    labels = set()
    assessments_by_accession = {}
    for assessment in upstream.class_bridge_assessments:
        positives = tuple(candidate for candidate in assessment.candidates
                          if candidate.status is
                          ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)
        if assessment.status is ClassBridgeAssessmentStatus.SOURCE_CONFLICT:
            issues.add(QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT)
        elif assessment.status is ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE:
            issues.add(QualificationIssue.UNSUPPORTED_INSTRUMENT_PROFILE)
        if len(positives) != 1:
            continue
        candidate = positives[0]
        assessments_by_accession.setdefault(candidate.accession, []).append(
            (assessment, candidate))
    for accession in required_accessions:
        members = assessments_by_accession.get(accession, ())
        if not members:
            issues.add(QualificationIssue.UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION)
            continue
        accession_distribution = set()
        accession_liquidation = set()
        accession_unknown = set()
        for assessment, candidate in members:
            if candidate.canonical_source_class_label is not None:
                labels.add(candidate.canonical_source_class_label)
            passage_by_id = {item.semantic_id: item
                             for item in assessment.rights_source_claims.passages}
            for passage_id in candidate.passage_semantic_ids:
                passage = passage_by_id.get(passage_id)
                if passage is None:
                    issues.add(QualificationIssue.AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION)
                    continue
                normalized = _normalized_text(passage.exact_source_text)
                evidence.add(passage.evidence_id)
                if normalized in _DISTRIBUTION_SENTENCES:
                    distribution.add(passage.semantic_id)
                    accession_distribution.add(passage.semantic_id)
                elif normalized in _LIQUIDATION_SENTENCES:
                    liquidation.add(passage.semantic_id)
                    accession_liquidation.add(passage.semantic_id)
                elif normalized in _OPTIONAL_SENTENCES:
                    optional.add(passage.semantic_id)
                elif passage.matched_topics:
                    accession_unknown.add(passage.semantic_id)
        if accession_unknown:
            issues.add(QualificationIssue.AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION)
        if not accession_distribution or not accession_liquidation:
            issues.add(QualificationIssue.UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION)
        elif not accession_unknown:
            covered.add(accession)
    if len(labels) != 1:
        issues.add(QualificationIssue.AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION)
    ordered = _ordered(issues)
    return OrdinaryCommonParticipationQualification(
        PARTICIPATION_PROFILE_VERSION,
        _component_status(ordered),
        next(iter(labels)) if len(labels) == 1 else None,
        tuple(sorted(covered)),
        tuple(sorted(distribution)),
        tuple(sorted(liquidation)),
        tuple(sorted(optional)),
        tuple(sorted(evidence)),
        ordered,
    )


def _dossier_filing(boundary, accession):
    matches = tuple(item for item in boundary.temporal_dossier.filings
                    if item.accession == accession)
    return matches[0] if len(matches) == 1 else None


def _boundary_filing(boundary, accession):
    matches = tuple(item for item in boundary.filings if item.accession == accession)
    return matches[0] if len(matches) == 1 else None


def _coverage(upstream, series, listing_candidate):
    issues = set()
    accessions = tuple(sorted({version.accession for period in series.periods
                               for version in period.filing_versions}))
    boundary = upstream.registered_listing_bridge.temporal_boundary
    d3a_ids, d3b_ids, source_scopes, shares_occurrences = set(), set(), set(), set()
    covered = set()
    for accession in accessions:
        accession_issues = set()
        filing = _boundary_filing(boundary, accession)
        if filing is not None and filing.post_boundary_captures:
            accession_issues.add(QualificationIssue.EVIDENCE_AFTER_CURRENT_BOUNDARY)
        if filing is None or not filing.controlled_captures_by_boundary:
            accession_issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
            issues.update(accession_issues)
            continue
        if filing.status is not FilingBoundaryStatus.CONTROLLED_CAPTURE_BY_BOUNDARY:
            if filing.post_boundary_captures:
                accession_issues.add(QualificationIssue.EVIDENCE_AFTER_CURRENT_BOUNDARY)
            accession_issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
        for capture in filing.controlled_captures_by_boundary:
            d3a = capture.registered_security_claims
            d3b = capture.class_eps_claims
            if d3a is None:
                accession_issues.add(QualificationIssue.UPSTREAM_EVIDENCE_INCOMPLETE)
            elif d3a.status is RegisteredSecurityExtractionStatus.SOURCE_CONFLICT:
                accession_issues.add(QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY)
            elif d3a.status is not (
                    RegisteredSecurityExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS):
                accession_issues.add(QualificationIssue.UPSTREAM_EVIDENCE_INCOMPLETE)
            else:
                d3a_ids.add(d3a.semantic_id)
                common_claims = tuple(claim for claim in d3a.claims
                                      if any(_common_title(title) for title in claim.titles))
                if len(common_claims) > 1:
                    accession_issues.add(
                        QualificationIssue.OBSERVED_COMPETING_RELEVANT_COMMON_CLASS)
                if len(common_claims) != 1:
                    accession_issues.add(
                        QualificationIssue.RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED)
                for claim in common_claims:
                    source_scopes.add((accession, claim.source_security_scope_id))
                    if (listing_candidate is None
                            or claim.trading_symbols != (listing_candidate.source_symbol,)
                            or (accession, claim.source_security_scope_id)
                            not in listing_candidate.d3a_filing_source_scopes):
                        accession_issues.add(
                            QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY)
            if d3b is None:
                if any(item.value == "D3B_UNSUPPORTED_SOURCE"
                       for item in capture.issues):
                    accession_issues.add(
                        QualificationIssue.UNSUPPORTED_SOURCE_EXTRACTION_PROFILE)
                else:
                    accession_issues.add(
                        QualificationIssue.RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED)
                continue
            d3b_ids.add(d3b.semantic_id)
            if (d3b.receipt.cik != series.cik
                    or d3b.primary_document.cik != series.cik
                    or any(context.entity_identifier != series.cik
                           for context in d3b.contexts)):
                accession_issues.add(QualificationIssue.ISSUER_CIK_DISAGREEMENT)
            if d3b.status is ClassEPSExtractionStatus.SOURCE_CONFLICT:
                accession_issues.add(QualificationIssue.D3B_CLASS_EPS_SOURCE_CONFLICT)
            elif d3b.status is not ClassEPSExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS:
                accession_issues.add(
                    QualificationIssue.RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED)
            shares = tuple(claim for claim in d3b.claims
                           if claim.fact_kind is SourceFactKind.COMMON_STOCK_SHARES_OUTSTANDING)
            eps = tuple(claim for claim in d3b.claims
                        if claim.fact_kind is SourceFactKind.DILUTED_EPS)
            if any(claim.source_class_scope_id is not None for claim in shares):
                accession_issues.add(
                    QualificationIssue.RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED)
            all_class_shares = tuple(claim for claim in shares
                                     if claim.source_class_scope_id is None and not claim.issues)
            if not all_class_shares:
                accession_issues.add(
                    QualificationIssue.RELEVANT_COMMON_CLASS_COVERAGE_NOT_ESTABLISHED)
            shares_occurrences.update(item for claim in all_class_shares
                                      for item in claim.occurrence_ids)
            dimension_states = {claim.source_class_scope_id is not None for claim in eps}
            if dimension_states == {False, True}:
                accession_issues.add(
                    QualificationIssue.MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT)
            elif True in dimension_states:
                accession_issues.add(QualificationIssue.DIMENSIONED_EPS_CLASS_AMBIGUITY)
        issues.update(accession_issues)
        if not accession_issues:
            covered.add(accession)
    ordered = _ordered(issues)
    return RelevantCommonClassCoverageQualification(
        RELEVANT_CLASS_COVERAGE_PROFILE_VERSION,
        _component_status(ordered),
        "UNDIMENSIONED_ALL_CLASS_COMMON_SHARES_AND_DILUTED_EPS",
        tuple(sorted(covered)),
        tuple(sorted(d3a_ids)),
        tuple(sorted(d3b_ids)),
        tuple(sorted(source_scopes)),
        tuple(sorted(shares_occurrences)),
        ordered,
    )


def _claim_id(assessment, claim):
    return _identity("d3b-source-claim", {
        "assessment_semantic_id": assessment.semantic_id,
        "fact_kind": claim.fact_kind,
        "concept_name": claim.concept_name,
        "context_semantic_id": claim.context_semantic_id,
        "source_class_scope_id": claim.source_class_scope_id,
        "assertions": claim.assertions,
    })


def _eps_decisions(upstream, series, *, route_components_established):
    boundary = upstream.registered_listing_bridge.temporal_boundary
    decisions = []
    for period in series.periods:
        for version in period.filing_versions:
            issues = set()
            if not route_components_established:
                issues.add(QualificationIssue.EPS_APPLICABILITY_NOT_ESTABLISHED)
            source_values, claim_ids, assessment_semantics = set(), set(), set()
            assessment_evidence, occurrence_ids = set(), set()
            filing = _boundary_filing(boundary, version.accession)
            dossier = _dossier_filing(boundary, version.accession)
            if filing is None or dossier is None or not filing.controlled_captures_by_boundary:
                issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
            else:
                inventory_matches = tuple(
                    occurrence for occurrence in dossier.inventory_occurrences
                    if (dict(occurrence.fields).get("form") == version.form
                        and dict(occurrence.fields).get("filingDate") == version.filed)
                )
                if not inventory_matches:
                    issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
                for capture in filing.controlled_captures_by_boundary:
                    d3b = capture.class_eps_claims
                    if d3b is None:
                        if any(item.value == "D3B_UNSUPPORTED_SOURCE"
                               for item in capture.issues):
                            issues.add(QualificationIssue.UNSUPPORTED_SOURCE_EXTRACTION_PROFILE)
                        continue
                    assessment_semantics.add(d3b.semantic_id)
                    assessment_evidence.add(d3b.evidence_id)
                    if (d3b.receipt.cik != series.cik
                            or d3b.primary_document.cik != series.cik):
                        issues.add(QualificationIssue.ISSUER_CIK_DISAGREEMENT)
                    if d3b.primary_document.form != version.form:
                        issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
                    if d3b.status is ClassEPSExtractionStatus.SOURCE_CONFLICT:
                        issues.add(QualificationIssue.D3B_CLASS_EPS_SOURCE_CONFLICT)
                    contexts = {context.semantic_id: context for context in d3b.contexts}
                    eps_claims = tuple(claim for claim in d3b.claims
                                       if claim.fact_kind is SourceFactKind.DILUTED_EPS)
                    period_claims = []
                    for claim in eps_claims:
                        context = contexts.get(claim.context_semantic_id)
                        if context is None:
                            continue
                        if (context.period.start_date, context.period.end_date) == (
                                period.period_start, period.period_end):
                            period_claims.append(claim)
                    if not period_claims:
                        if eps_claims:
                            issues.add(QualificationIssue.RETAINED_C3_VERSION_PERIOD_MISMATCH)
                        else:
                            issues.add(QualificationIssue.MISSING_EPS_SOURCE_CORRESPONDENCE)
                        continue
                    states = {claim.source_class_scope_id is not None
                              for claim in period_claims}
                    if states == {False, True}:
                        issues.add(QualificationIssue.
                                   MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT)
                    elif True in states:
                        issues.add(QualificationIssue.DIMENSIONED_EPS_CLASS_AMBIGUITY)
                    for claim in period_claims:
                        claim_ids.add(_claim_id(d3b, claim))
                        occurrence_ids.update(claim.occurrence_ids)
                        for assertion in claim.assertions:
                            source_values.add(assertion.source_value)
                            try:
                                source_value = Decimal(assertion.source_value)
                            except InvalidOperation:
                                issues.add(QualificationIssue.
                                           MISSING_EPS_SOURCE_CORRESPONDENCE)
                                continue
                            if source_value != period.value:
                                issues.add(QualificationIssue.
                                           RETAINED_C3_VERSION_VALUE_MISMATCH)
            if not claim_ids:
                issues.add(QualificationIssue.MISSING_EPS_SOURCE_CORRESPONDENCE)
            if issues:
                issues.add(QualificationIssue.EPS_APPLICABILITY_NOT_ESTABLISHED)
            ordered = _ordered(issues)
            decisions.append(RetainedEPSVersionApplicabilityDecision(
                period.period_start,
                period.period_end,
                period.value,
                version.semantic_id,
                version.observation_ids,
                version.accession,
                version.form,
                version.filed,
                tuple(sorted(source_values)),
                tuple(sorted(claim_ids)),
                tuple(sorted(assessment_semantics)),
                tuple(sorted(assessment_evidence)),
                tuple(sorted(occurrence_ids)),
                _component_status(ordered),
                ordered,
            ))
    return tuple(decisions)


def _issuer_and_boundary_issues(upstream, series, listing_candidate):
    issues = set()
    bridge = upstream.registered_listing_bridge
    boundary = bridge.temporal_boundary
    current = boundary.current_evidence
    boundaries = {
        value for value in (
            upstream.current_authority_boundary,
            bridge.current_authority_boundary,
            boundary.current_authority_boundary,
            current.current_authority.current_authority_boundary,
            None if series is None else series.authority_as_of,
        ) if value is not None
    }
    if len(boundaries) != 1:
        issues.add(QualificationIssue.CURRENT_BOUNDARY_MISMATCH)
    ciks = {
        value for value in (
            boundary.source_cik,
            current.request.cik,
            None if series is None else series.cik,
            None if listing_candidate is None else listing_candidate.source_cik,
        ) if value is not None
    }
    ciks.update(observation.source_cik for observation in upstream.observations)
    if len(ciks) != 1:
        issues.add(QualificationIssue.ISSUER_CIK_DISAGREEMENT)
    return issues


def _qualification_status(issues):
    issue_set = set(issues)
    if QualificationIssue.CURRENT_AUTHORITY_UNAVAILABLE in issue_set:
        return QualificationStatus.UPSTREAM_CURRENT_AUTHORITY_UNAVAILABLE
    if issue_set & {
        QualificationIssue.ISSUER_CIK_DISAGREEMENT,
        QualificationIssue.D4C2_CONFLICT_OR_AMBIGUITY,
        QualificationIssue.D4D3A_D4D3B_SOURCE_CONFLICT,
        QualificationIssue.AMBIGUOUS_ORDINARY_COMMON_PARTICIPATION,
        QualificationIssue.OBSERVED_COMPETING_RELEVANT_COMMON_CLASS,
        QualificationIssue.D3B_CLASS_EPS_SOURCE_CONFLICT,
        QualificationIssue.MIXED_DIMENSIONED_UNDIMENSIONED_SOURCE_CONFLICT,
        QualificationIssue.RETAINED_C3_VERSION_VALUE_MISMATCH,
    }:
        return QualificationStatus.SOURCE_CONFLICT
    if issue_set & {
        QualificationIssue.UNSUPPORTED_REGISTERED_LISTING_ROUTE,
        QualificationIssue.UNSUPPORTED_ORDINARY_COMMON_PARTICIPATION,
        QualificationIssue.UNSUPPORTED_SOURCE_EXTRACTION_PROFILE,
        QualificationIssue.UNSUPPORTED_INSTRUMENT_PROFILE,
    }:
        return QualificationStatus.UNSUPPORTED_QUALIFICATION_PROFILE
    if issue_set:
        return QualificationStatus.QUALIFICATION_BLOCKED
    return QualificationStatus.CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED


def qualify_sec_current_security_eps(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentSecurityEPSQualificationRequest,
) -> SecCurrentSecurityEPSQualification:
    """Freshly replay and qualify only the closed PR5B CURRENT route."""
    if (type(current_archive) is not SecArchive
            or type(submissions_archive) is not SecSubmissionsArchive
            or type(filing_archive) is not SecFilingArchive
            or type(ticker_exchange_archive) is not SecTickerExchangeArchive
            or type(nasdaq_listed_archive) is not NasdaqListedArchive
            or type(request) is not SecCurrentSecurityEPSQualificationRequest):
        raise SecCurrentSecurityEPSQualificationRequestError(
            "Exact typed archives/request required")

    nested = request.temporal_source_series_request.registered_listing_bridge_request
    preflight = assess_sec_current_registered_listing_bridge(
        current_archive,
        submissions_archive,
        filing_archive,
        ticker_exchange_archive,
        nasdaq_listed_archive,
        nested,
    )
    if _has_unsupported_extraction(preflight.temporal_boundary):
        return _unsupported_qualification(preflight)

    upstream = assess_sec_temporal_common_stock_source_series(
        current_archive,
        submissions_archive,
        filing_archive,
        ticker_exchange_archive,
        nasdaq_listed_archive,
        request.temporal_source_series_request,
    )
    issues = _upstream_issues(upstream)
    listing, listing_candidate = _listing_bridge(upstream.registered_listing_bridge)
    issues.update(listing.issues)
    current = upstream.registered_listing_bridge.temporal_boundary.current_evidence
    series = current.resolution.series

    if series is None:
        participation = OrdinaryCommonParticipationQualification(
            PARTICIPATION_PROFILE_VERSION, ComponentStatus.BLOCKED, None, (), (), (), (), (),
            (QualificationIssue.C3_SERIES_UNAVAILABLE,))
        coverage = RelevantCommonClassCoverageQualification(
            RELEVANT_CLASS_COVERAGE_PROFILE_VERSION, ComponentStatus.BLOCKED,
            "UNDIMENSIONED_ALL_CLASS_COMMON_SHARES_AND_DILUTED_EPS", (), (), (), (), (),
            (QualificationIssue.C3_SERIES_UNAVAILABLE,))
        eps_decisions = ()
    else:
        required_accessions = tuple(sorted({version.accession for period in series.periods
                                            for version in period.filing_versions}))
        observed_accessions = tuple(sorted({item.accession for item in upstream.observations}))
        missing = set(required_accessions) - set(observed_accessions)
        extra = set(observed_accessions) - set(required_accessions)
        if missing:
            issues.add(QualificationIssue.RETAINED_C3_VERSION_NOT_CONTROLLED)
        if extra:
            issues.add(QualificationIssue.EXTRANEOUS_SELECTED_SOURCE_EVIDENCE)
        participation = _participation(upstream, required_accessions)
        coverage = _coverage(upstream, series, listing_candidate)
        eps_decisions = _eps_decisions(
            upstream,
            series,
            route_components_established=(
                participation.status is ComponentStatus.QUALIFICATION_ESTABLISHED
                and coverage.status is ComponentStatus.QUALIFICATION_ESTABLISHED
                and listing.status is ComponentStatus.QUALIFICATION_ESTABLISHED
            ),
        )
        issues.update(_issuer_and_boundary_issues(upstream, series, listing_candidate))
        issues.update(participation.issues)
        issues.update(coverage.issues)
        issues.update(issue for decision in eps_decisions for issue in decision.issues)

    ordered_issues = _ordered(issues)
    status = _qualification_status(ordered_issues)
    positive = status is QualificationStatus.CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED
    boundary = upstream.current_authority_boundary
    issuer_key = None
    security_key = None
    if positive and series is not None and listing_candidate is not None:
        issuer_key = _identity("route-local-issuer-key", {
            "contract": CONTRACT_VERSION,
            "route": ROUTE_PROFILE,
            "cik": series.cik,
            "d1_semantic_hash": current.semantic_hash,
            "boundary": boundary,
        })
        security_key = _identity("route-local-security-key", {
            "contract": CONTRACT_VERSION,
            "route": ROUTE_PROFILE,
            "issuer_key": issuer_key,
            "listing_candidate": listing_candidate.semantic_id,
            "canonical_class_label": participation.canonical_source_class_label,
            "source_scopes": coverage.selected_d3a_source_scopes,
            "temporal_source_series": upstream.semantic_id,
        })

    semantic_ids = {
        upstream.semantic_id,
        upstream.registered_listing_bridge.semantic_id,
        participation.profile_version,
        coverage.profile_version,
        EPS_APPLICABILITY_PROFILE_VERSION,
    }
    evidence_ids = {
        upstream.evidence_id,
        upstream.registered_listing_bridge.evidence_id,
    }
    if listing_candidate is not None:
        semantic_ids.add(listing_candidate.semantic_id)
        evidence_ids.add(listing_candidate.evidence_id)
    for decision in eps_decisions:
        semantic_ids.update(decision.d3b_claim_semantic_ids)
        semantic_ids.update(decision.d3b_assessment_semantic_ids)
        evidence_ids.update(decision.d3b_assessment_evidence_ids)
    evidence_ids.update(participation.passage_evidence_ids)

    return SecCurrentSecurityEPSQualification(
        CONTRACT_VERSION,
        ROUTE_PROFILE,
        status,
        ((AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED,)
         if positive else ()),
        boundary,
        issuer_key,
        security_key,
        upstream,
        upstream.registered_listing_bridge,
        participation,
        coverage,
        listing,
        eps_decisions,
        tuple(sorted(semantic_ids)),
        tuple(sorted(evidence_ids)),
        ordered_issues,
        tuple(sorted(QualificationLimitation, key=lambda item: item.value)),
    )
