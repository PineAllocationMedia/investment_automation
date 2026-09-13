"""Pure synthetic accounting-subject continuity, with unchanged reported EPS.

SEC interpretation is confined to upstream profile replay. Subject anchors and
inclusive date spans are jurisdiction-neutral. Evidence is fictional, not real
admission, authentication, issuer error detection or historical PIT knowledge.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json
import re
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from . import sec_eps_series as series_profile
from . import security_identity as identity_profile
from . import share_basis as basis_profile
from .sec_archive import ACQUISITION_CONTRACT_VERSION, LIVE_ACQUISITION_CONTRACT_VERSION
from .sec_eps_series import AdmissionBlocker, ResolvedAnnualDilutedEPSSeries
from .security_identity import SecurityIdentityQualification
from .share_basis import (ObservationReference, ShareBasisQualification, ShareBasisRequest,
                          SyntheticShareBasisEvidenceBundle, qualify_share_basis)

REPORTING_SUBJECT_CONTRACT_VERSION = "2026-09-13-reporting-subject-contract-v1"
REPORTING_SUBJECT_QUALIFIER_VERSION = "2026-09-13-synthetic-reporting-subject-qualifier-v1"
SYNTHETIC_EVIDENCE_VERSION = "2026-09-13-synthetic-reporting-subject-evidence-v1"
EXTRACTION_VERSION = "2026-09-13-synthetic-reporting-subject-claims-v1"
SOURCE_PROFILE = "2026-09-13-sec-companyfacts-total-diluted-eps-v1"
MEASUREMENT_PROFILE = "2026-09-13-reported-total-entity-diluted-eps-us-gaap-v1"


class Authority(Enum):
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"


class ReportingSubjectMode(Enum):
    CURRENT_SNAPSHOT = "CURRENT_SNAPSHOT"
    HISTORICAL_AS_OF = "HISTORICAL_AS_OF"


class ComparabilityOutcome(Enum):
    COMPARABLE_WITHIN_SYNTHETIC_SCOPE = "COMPARABLE_WITHIN_SYNTHETIC_SCOPE"
    COMPARABILITY_UNAVAILABLE = "COMPARABILITY_UNAVAILABLE"
    COMPARABILITY_UNSUPPORTED = "COMPARABILITY_UNSUPPORTED"


class ReportingSubjectReason(Enum):
    UPSTREAM_NOT_QUALIFIED = "UPSTREAM_NOT_QUALIFIED"
    UPSTREAM_BOUNDARY_NOT_QUALIFIED = "UPSTREAM_BOUNDARY_NOT_QUALIFIED"
    REPORTING_SUBJECT_COVERAGE_INCOMPLETE = "REPORTING_SUBJECT_COVERAGE_INCOMPLETE"
    REPORTING_SUBJECT_EVIDENCE_CONFLICT = "REPORTING_SUBJECT_EVIDENCE_CONFLICT"
    REPORTING_SUBJECT_DISCONTINUITY = "REPORTING_SUBJECT_DISCONTINUITY"
    HISTORICAL_COMPARABILITY_UNSUPPORTED = "HISTORICAL_COMPARABILITY_UNSUPPORTED"
    SYNTHETIC_EVIDENCE_ONLY = "SYNTHETIC_EVIDENCE_ONLY"


class CoverageStatus(Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True, slots=True)
class ShareBasisQualificationWitness:
    request: ShareBasisRequest
    evidence: SyntheticShareBasisEvidenceBundle


@dataclass(frozen=True, slots=True)
class ReportingSubjectRequest:
    contract_version: str
    mode: ReportingSubjectMode
    series_semantic_hash: str
    series_evidence_hash: str
    identity_semantic_hash: str
    identity_evidence_hash: str
    share_basis_semantic_hash: str
    share_basis_evidence_hash: str


@dataclass(frozen=True, slots=True)
class ReportingSubjectSpan:
    subject_anchor: str
    issuer_anchor: str
    effective_start: str
    effective_end: str
    references: tuple[ObservationReference, ...]


@dataclass(frozen=True, slots=True)
class ReportingSubjectSnapshot:
    series_semantic_hash: str
    series_evidence_hash: str
    coverage: CoverageStatus
    spans: tuple[ReportingSubjectSpan, ...]


@dataclass(frozen=True, slots=True)
class SyntheticReportingSubjectEvidence:
    authority: Authority
    source_reference: str
    source_version: str
    source_locator: str
    extraction_version: str
    published_at: str
    available_at: str
    captured_at: str
    source_bytes: bytes
    content_sha256: str
    claims: ReportingSubjectSnapshot


@dataclass(frozen=True, slots=True)
class SyntheticReportingSubjectEvidenceBundle:
    contract_version: str
    share_basis_witness: ShareBasisQualificationWitness
    documents: tuple[SyntheticReportingSubjectEvidence, ...]


@dataclass(frozen=True, slots=True)
class PeriodReportingSubjectDecision:
    period_start: str
    period_end: str
    reported_value: Decimal
    annual_supporting_observation_ids: tuple[str, ...]
    filing_version_ids: tuple[str, ...]
    filing_version_observations: tuple[ObservationReference, ...]
    assigned_subject_anchors: tuple[str, ...]
    qualified_subject_anchor: str | None
    outcome: ComparabilityOutcome
    reasons: tuple[ReportingSubjectReason, ...]


@dataclass(frozen=True, slots=True)
class EconomicComparabilityQualification:
    contract_version: str
    qualifier_version: str
    authority: Authority
    source_profile: str
    measurement_profile: str
    series_semantic_hash: str
    series_evidence_hash: str
    identity_semantic_hash: str
    identity_evidence_hash: str
    share_basis_semantic_hash: str
    share_basis_evidence_hash: str
    required_start: str
    qualification_boundary: str
    qualified_subject_anchor: str | None
    qualified_issuer_anchor: str | None
    qualified_security_anchor: str | None
    qualified_class_id: str | None
    qualified_share_basis_semantic_hash: str | None
    period_decisions: tuple[PeriodReportingSubjectDecision, ...]
    outcome: ComparabilityOutcome
    reasons: tuple[ReportingSubjectReason, ...]
    limitations: tuple[ReportingSubjectReason, ...]
    downstream_blockers: tuple[AdmissionBlocker, ...]
    considered_evidence_ids: tuple[str, ...]
    semantic_hash: str
    evidence_hash: str


class ReportingSubjectContractError(ValueError):
    """Closed structural, provenance-linkage or replay corruption error."""


_R = ReportingSubjectReason


def _require(condition, message):
    if not condition:
        raise ReportingSubjectContractError(message)


def _typed(value, expected):
    origin, args = get_origin(expected), get_args(expected)
    if origin is UnionType:
        matches = [t for t in args if type(value) is t]
        _require(len(matches) == 1, "Invalid optional closed record")
        return _typed(value, matches[0])
    if origin is tuple:
        _require(type(value) is tuple, "Immutable tuple required")
        for child in value:
            _typed(child, args[0])
        return
    _require(type(value) is expected, "Exact closed type required")
    if is_dataclass(value):
        for name, kind in get_type_hints(expected).items():
            _require(hasattr(value, name), "Missing closed record field")
            _typed(getattr(value, name), kind)
    elif expected is Decimal:
        _require(value.is_finite(), "Finite upstream Decimal required")


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: _project(getattr(value, f.name)) for f in fields(value)}
    if type(value) is bytes:
        return {"sha256": hashlib.sha256(value).hexdigest(), "length": len(value)}
    if type(value) is Decimal:
        sign, digits, exponent = value.as_tuple()
        return {"decimal_tuple": [sign, list(digits), exponent]}
    if type(value) in (tuple, list):
        return [_project(v) for v in value]
    if type(value) is dict:
        return {k: _project(v) for k, v in value.items()}
    return value


def _json(value):
    return json.dumps(_project(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _hash(domain, value):
    return hashlib.sha256(_json((REPORTING_SUBJECT_CONTRACT_VERSION,
        REPORTING_SUBJECT_QUALIFIER_VERSION, domain, value))).hexdigest()


def _records(values):
    distinct = {_json(v): v for v in values}
    return tuple(distinct[k] for k in sorted(distinct))


def _reasons(values):
    return tuple(sorted(set(values), key=lambda r: r.value))


def _day(value):
    try:
        parsed = date.fromisoformat(value)
        _require(parsed.isoformat() == value, "Canonical ISO date required")
        return parsed
    except ValueError as exc:
        raise ReportingSubjectContractError("Invalid date") from exc


def _time(value):
    _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?Z", value),
             "Canonical UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.isoformat().replace("+00:00", "Z") == value, "Canonical UTC timestamp required")
        return parsed
    except ValueError as exc:
        raise ReportingSubjectContractError("Invalid timestamp") from exc


def _anchor(value, kind):
    return re.fullmatch(r"synthetic:" + kind + r":[a-z0-9][a-z0-9_-]*", value) is not None


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "Duplicate source JSON key")
        result[key] = value
    return result


def _invalid_number(value):
    raise ReportingSubjectContractError("Non-integer source number")


def _verify_source(source):
    _require(source.source_version == SYNTHETIC_EVIDENCE_VERSION
             and source.extraction_version == EXTRACTION_VERSION, "Unknown evidence version")
    _require(_anchor(source.source_reference, "document"), "Synthetic source reference required")
    _require(source.source_locator == "/claims", "Source locator mismatch")
    _require(hashlib.sha256(source.source_bytes).hexdigest() == source.content_sha256, "Source hash mismatch")
    expected = {f.name: getattr(source, f.name) for f in fields(source)
                if f.name not in {"source_bytes", "content_sha256"}}
    try:
        parsed = json.loads(source.source_bytes, object_pairs_hook=_pairs,
                            parse_float=_invalid_number, parse_constant=_invalid_number)
        _require(_json(parsed) == _json(expected), "Source claims/metadata mismatch")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ReportingSubjectContractError("Invalid synthetic source") from exc
    _require(_time(source.published_at) <= _time(source.available_at) <= _time(source.captured_at),
             "Invalid publication/availability/capture order")
    return _hash("source-evidence", source)


def _replay_sec_profile(series, identity, share_basis, witness):
    """Only SEC-specific interpretation; existing C5/C4 own their validations."""
    try:
        replay = qualify_share_basis(series, identity, witness.request, witness.evidence)
    except (basis_profile.ShareBasisContractError, identity_profile.IdentityContractError) as exc:
        raise ReportingSubjectContractError("Invalid upstream replay") from exc
    _require(_json(replay) == _json(share_basis), "Share-basis result does not match exact replay")
    capture = series.capture_authority
    offline = capture.authority is series_profile.CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE
    expected = ACQUISITION_CONTRACT_VERSION if offline else LIVE_ACQUISITION_CONTRACT_VERSION
    _require(capture.acquisition_contract == expected, "Capture authority/profile mismatch")
    _require(not offline or AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED
             in series.downstream_admission_blockers, "Offline authority limitation missing")
    # C5 replay includes current C4 profile/series validation and C3 semantic replay.
    # Full C3 evidence authentication still requires its original archive/extraction.


def _references(period):
    return _records(ObservationReference(period.period_start, period.period_end, v.semantic_id, o)
                    for v in period.filing_versions for o in v.observation_ids)


def _inspect(snapshot, series, issuer_anchor, boundary):
    _require((snapshot.series_semantic_hash, snapshot.series_evidence_hash)
             == (series.semantic_hash, series.evidence_hash), "Source/series identity mismatch")
    required = {r for p in series.periods for r in _references(p)}
    assignments = {r: set() for r in required}
    reasons = set()
    if snapshot.coverage is not CoverageStatus.COMPLETE:
        reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
    oldest, end = _day(series.periods[0].period_start), _time(boundary).date()
    intervals = []
    for span in _records(snapshot.spans):
        _require(_anchor(span.subject_anchor, "subject") and _anchor(span.issuer_anchor, "issuer"),
                 "Explicit synthetic subject/issuer anchors required")
        start, stop = _day(span.effective_start), _day(span.effective_end)
        _require(start <= stop, "Reversed subject interval")
        _require(set(span.references) <= required, "Foreign period/version/observation reference")
        _require(issuer_anchor is None or span.issuer_anchor == issuer_anchor, "Subject/issuer link mismatch")
        for ref in span.references:
            assignments[ref].add(span.subject_anchor)
            if start > _day(ref.period_start) or stop < _day(ref.period_end):
                reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
        if start <= end and stop >= oldest:
            intervals.append((max(start, oldest), min(stop, end), span.subject_anchor))
    intervals.sort()
    subjects = {s for _, _, s in intervals}
    if len(subjects) > 1:
        reasons.add(_R.REPORTING_SUBJECT_DISCONTINUITY)
    if any(not values for values in assignments.values()):
        reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
    if any(len(values) > 1 for values in assignments.values()):
        reasons.add(_R.REPORTING_SUBJECT_EVIDENCE_CONFLICT)
    covered_until = None
    for start, stop, subject in intervals:
        if covered_until is None and start > oldest or covered_until is not None and (start - covered_until).days > 1:
            reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
        covered_until = max(covered_until, stop) if covered_until else stop
    if covered_until is None or covered_until < end:
        reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
    for n, (start, stop, subject) in enumerate(intervals):
        if any(other_start <= stop and other_subject != subject
               for other_start, _, other_subject in intervals[n + 1:]):
            reasons.add(_R.REPORTING_SUBJECT_EVIDENCE_CONFLICT)
    # Canonical chronological union per subject, independent of span segmentation.
    merged = []
    for subject in sorted(subjects):
        for start, stop, current in intervals:
            if current != subject:
                continue
            if merged and merged[-1][2] == subject and (start - merged[-1][1]).days <= 1:
                merged[-1] = (merged[-1][0], max(stop, merged[-1][1]), subject)
            else:
                merged.append((start, stop, subject))
    chronology = tuple((a.isoformat(), b.isoformat(), s) for a, b, s in sorted(merged))
    assignment_core = tuple((r, tuple(sorted(assignments[r]))) for r in sorted(required, key=_json))
    period_subjects = tuple(tuple(sorted({s for r in _references(p) for s in assignments[r]}))
                            for p in series.periods)
    return reasons, subjects, chronology, assignment_core, period_subjects


def qualify_reporting_subject(
    series: ResolvedAnnualDilutedEPSSeries,
    identity: SecurityIdentityQualification,
    share_basis: ShareBasisQualification,
    request: ReportingSubjectRequest,
    evidence: SyntheticReportingSubjectEvidenceBundle,
) -> EconomicComparabilityQualification:
    """Evaluate each complete snapshot independently; never extend upstream authority."""
    for value, kind in ((series, ResolvedAnnualDilutedEPSSeries), (identity, SecurityIdentityQualification),
                       (share_basis, ShareBasisQualification), (request, ReportingSubjectRequest),
                       (evidence, SyntheticReportingSubjectEvidenceBundle)):
        _typed(value, kind)
    _require(request.contract_version == REPORTING_SUBJECT_CONTRACT_VERSION
             and evidence.contract_version == SYNTHETIC_EVIDENCE_VERSION, "Unknown contract version")
    pairs = (series.semantic_hash, series.evidence_hash, identity.semantic_hash, identity.evidence_hash,
             share_basis.semantic_hash, share_basis.evidence_hash)
    _require((request.series_semantic_hash, request.series_evidence_hash,
              request.identity_semantic_hash, request.identity_evidence_hash,
              request.share_basis_semantic_hash, request.share_basis_evidence_hash) == pairs,
             "Request/upstream linkage mismatch")
    _replay_sec_profile(series, identity, share_basis, evidence.share_basis_witness)
    documents = _records(evidence.documents)
    source_ids = tuple(sorted(_verify_source(d) for d in documents))
    times = (series.authority_as_of, share_basis.qualification_boundary,
             *((identity.qualification_as_of,) if identity.qualification_as_of else ()),
             *(d.captured_at for d in documents))
    boundary = max(map(_time, times)).isoformat().replace("+00:00", "Z")
    reasons = set()
    if (identity.outcome is not identity_profile.IdentityOutcome.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE
            or share_basis.outcome is not basis_profile.ShareBasisOutcome.COMPARABLE_BASIS_ESTABLISHED
            or share_basis.transformation_mode is not basis_profile.TransformationMode.NONE
            or share_basis.qualified_target_basis is None):
        reasons.add(_R.UPSTREAM_NOT_QUALIFIED)
    if _time(boundary) > _time(share_basis.qualification_boundary):
        reasons.add(_R.UPSTREAM_BOUNDARY_NOT_QUALIFIED)
    if request.mode is ReportingSubjectMode.HISTORICAL_AS_OF:
        reasons.add(_R.HISTORICAL_COMPARABILITY_UNSUPPORTED)
    if not documents:
        reasons.add(_R.REPORTING_SUBJECT_COVERAGE_INCOMPLETE)
    issuer = identity.issuer.anchor if identity.issuer else None
    inspections = tuple(_inspect(d.claims, series, issuer, boundary) for d in documents)
    for inspected in inspections:
        reasons.update(inspected[0])
    if len({_json((x[2], x[3])) for x in inspections}) > 1:
        reasons.add(_R.REPORTING_SUBJECT_EVIDENCE_CONFLICT)
    subjects = {s for x in inspections for s in x[1]}
    if len(subjects) > 1:
        reasons.add(_R.REPORTING_SUBJECT_DISCONTINUITY)
    ordered = _reasons(reasons)
    outcome = (ComparabilityOutcome.COMPARABILITY_UNSUPPORTED if reasons & {
        _R.HISTORICAL_COMPARABILITY_UNSUPPORTED, _R.REPORTING_SUBJECT_DISCONTINUITY}
        else ComparabilityOutcome.COMPARABILITY_UNAVAILABLE) if reasons else ComparabilityOutcome.COMPARABLE_WITHIN_SYNTHETIC_SCOPE
    subject = next(iter(subjects)) if not reasons else None
    decisions = tuple(PeriodReportingSubjectDecision(p.period_start, p.period_end, p.value,
        p.supporting_observation_ids, p.version_ids, _references(p),
        tuple(sorted({s for x in inspections for s in x[4][n]})), subject, outcome, ordered)
        for n, p in enumerate(series.periods))
    limitations = (_R.SYNTHETIC_EVIDENCE_ONLY,)
    blockers = _reasons((*series.downstream_admission_blockers, *identity.downstream_blockers,
                         *share_basis.downstream_blockers))
    target = share_basis.qualified_target_basis
    # Observation IDs and exact Decimal representation remain in evidence; C3's
    # semantic identity already binds exact numeric meaning without rounding.
    semantic = (pairs[0], pairs[2], pairs[4], SOURCE_PROFILE, MEASUREMENT_PROFILE, request.mode,
        subject, series.periods[0].period_start, boundary, outcome, ordered,
        _records(x[2] for x in inspections), tuple((d.period_start, d.period_end,
        d.assigned_subject_anchors, d.qualified_subject_anchor, d.outcome, d.reasons) for d in decisions))
    semantic_hash = _hash("qualification-semantics", semantic)
    evidence_hash = _hash("qualification-evidence", (semantic_hash, request, series, identity, share_basis,
        evidence.share_basis_witness, source_ids, decisions, blockers, limitations))
    return EconomicComparabilityQualification(REPORTING_SUBJECT_CONTRACT_VERSION,
        REPORTING_SUBJECT_QUALIFIER_VERSION, Authority.SYNTHETIC_TEST_ONLY, SOURCE_PROFILE, MEASUREMENT_PROFILE,
        *pairs, series.periods[0].period_start, boundary, subject, issuer if not reasons else None,
        identity.security.anchor if not reasons else None,
        identity.security.common_class.class_id if not reasons else None,
        target.semantic_hash if not reasons else None, decisions, outcome, ordered, limitations,
        blockers, source_ids, semantic_hash, evidence_hash)
