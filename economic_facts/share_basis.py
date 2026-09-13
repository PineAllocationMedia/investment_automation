"""Pure, fictional split-only denomination qualification; reported values pass through.

The SEC profile boundary is delegated to exact PR4C4 replay. The economic records
below carry security/class anchors, periods and observation references, not
jurisdiction-specific identifiers. No real admission capability is constructed.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import cmp_to_key
import hashlib
import json
from math import gcd
import re
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from . import security_identity as identity_profile
from . import sec_eps_series as series_profile
from .sec_eps_series import AdmissionBlocker, ResolvedAnnualDilutedEPSSeries
from .security_identity import (
    SecurityIdentityQualification, SecurityIdentityRequest, SyntheticIdentityEvidenceBundle,
    qualify_security_identity,
)

SHARE_BASIS_CONTRACT_VERSION = "2026-09-13-share-basis-contract-v1"
SHARE_BASIS_QUALIFIER_VERSION = "2026-09-13-synthetic-split-only-qualifier-v1"
SYNTHETIC_EVIDENCE_VERSION = "2026-09-13-synthetic-share-basis-evidence-v1"
EXTRACTION_VERSION = "2026-09-13-synthetic-share-basis-claims-v1"


class Authority(Enum):
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"


class TransformationMode(Enum):
    NONE = "NONE"


class ShareBasisMode(Enum):
    CURRENT_SNAPSHOT = "CURRENT_SNAPSHOT"
    HISTORICAL_AS_OF = "HISTORICAL_AS_OF"


class ShareBasisOutcome(Enum):
    COMPARABLE_BASIS_ESTABLISHED = "COMPARABLE_BASIS_ESTABLISHED"
    BASIS_UNAVAILABLE = "BASIS_UNAVAILABLE"
    BASIS_UNSUPPORTED = "BASIS_UNSUPPORTED"


class ShareBasisReason(Enum):
    SECURITY_IDENTITY_NOT_QUALIFIED = "SECURITY_IDENTITY_NOT_QUALIFIED"
    IDENTITY_BOUNDARY_NOT_QUALIFIED = "IDENTITY_BOUNDARY_NOT_QUALIFIED"
    BASELINE_BASIS_UNRESOLVED = "BASELINE_BASIS_UNRESOLVED"
    CORPORATE_ACTION_COVERAGE_GAP = "CORPORATE_ACTION_COVERAGE_GAP"
    EVENT_SECURITY_UNRESOLVED = "EVENT_SECURITY_UNRESOLVED"
    EVENT_TERMS_UNRESOLVED = "EVENT_TERMS_UNRESOLVED"
    EVENT_EFFECTIVE_DATE_UNRESOLVED = "EVENT_EFFECTIVE_DATE_UNRESOLVED"
    EVENT_IMPLEMENTATION_UNCONFIRMED = "EVENT_IMPLEMENTATION_UNCONFIRMED"
    EVENT_ORDER_UNRESOLVED = "EVENT_ORDER_UNRESOLVED"
    CORPORATE_ACTION_CONFLICT = "CORPORATE_ACTION_CONFLICT"
    SECURITY_CONTINUATION_UNRESOLVED = "SECURITY_CONTINUATION_UNRESOLVED"
    FRACTIONAL_TREATMENT_UNRESOLVED = "FRACTIONAL_TREATMENT_UNRESOLVED"
    REPORTED_BASIS_UNRESOLVED = "REPORTED_BASIS_UNRESOLVED"
    REPORTED_EVENT_TREATMENT_UNRESOLVED = "REPORTED_EVENT_TREATMENT_UNRESOLVED"
    REPORTED_BASIS_CONFLICT = "REPORTED_BASIS_CONFLICT"
    SUPPORTING_VERSION_COVERAGE_GAP = "SUPPORTING_VERSION_COVERAGE_GAP"
    MIXED_REPORTED_BASES = "MIXED_REPORTED_BASES"
    BASIS_NORMALIZATION_REQUIRED = "BASIS_NORMALIZATION_REQUIRED"
    UNSUPPORTED_CORPORATE_ACTION = "UNSUPPORTED_CORPORATE_ACTION"
    FRACTIONAL_SETTLEMENT_UNSUPPORTED = "FRACTIONAL_SETTLEMENT_UNSUPPORTED"
    HISTORICAL_BASIS_UNSUPPORTED = "HISTORICAL_BASIS_UNSUPPORTED"
    SYNTHETIC_EVIDENCE_ONLY = "SYNTHETIC_EVIDENCE_ONLY"


class CorporateActionKind(Enum):
    FORWARD_SPLIT = "FORWARD_SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    SHARE_CLASS_CONVERSION = "SHARE_CLASS_CONVERSION"
    MERGER_SECURITY_EXCHANGE = "MERGER_SECURITY_EXCHANGE"
    SPIN_OFF = "SPIN_OFF"
    RECAPITALIZATION = "RECAPITALIZATION"
    REDENOMINATION = "REDENOMINATION"
    UNUSUAL_CONSOLIDATION = "UNUSUAL_CONSOLIDATION"
    OTHER_BASIS_AFFECTING = "OTHER_BASIS_AFFECTING"


class EventLifecycle(Enum):
    ANNOUNCED = "ANNOUNCED"
    APPROVED = "APPROVED"
    EFFECTIVE = "EFFECTIVE"
    CANCELLED = "CANCELLED"


class NoticeRelationshipKind(Enum):
    AMENDS = "AMENDS"
    SUPERSEDES = "SUPERSEDES"


class Implementation(Enum):
    CONFIRMED = "CONFIRMED"
    NEVER_IMPLEMENTED = "NEVER_IMPLEMENTED"
    UNRESOLVED = "UNRESOLVED"


class RatioOrientation(Enum):
    NEW_UNITS_PER_OLD_UNITS = "NEW_UNITS_PER_OLD_UNITS"
    UNRESOLVED = "UNRESOLVED"


class SecurityContinuation(Enum):
    SAME_SECURITY_AND_CLASS = "SAME_SECURITY_AND_CLASS"
    UNRESOLVED = "UNRESOLVED"


class ActionStructure(Enum):
    PURE_SPLIT = "PURE_SPLIT"
    ASSOCIATED_RESTRUCTURING = "ASSOCIATED_RESTRUCTURING"
    UNRESOLVED = "UNRESOLVED"


class FractionalTreatment(Enum):
    NO_FRACTIONAL_SETTLEMENT = "NO_FRACTIONAL_SETTLEMENT"
    CASH_SETTLEMENT = "CASH_SETTLEMENT"
    UNRESOLVED = "UNRESOLVED"


class CoverageStatus(Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class ReportedEventTreatment(Enum):
    INCORPORATED = "INCORPORATED"
    NOT_INCORPORATED = "NOT_INCORPORATED"
    UNRESOLVED = "UNRESOLVED"


class BasisCompatibility(Enum):
    TARGET_BASIS = "TARGET_BASIS"
    DIFFERENT_BASIS = "DIFFERENT_BASIS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True, slots=True)
class IdentityQualificationWitness:
    request: SecurityIdentityRequest
    evidence: SyntheticIdentityEvidenceBundle


@dataclass(frozen=True, slots=True)
class ShareBasisRequest:
    contract_version: str
    mode: ShareBasisMode
    series_semantic_hash: str
    series_evidence_hash: str
    identity_semantic_hash: str
    identity_evidence_hash: str
    transformation_mode: TransformationMode = TransformationMode.NONE


@dataclass(frozen=True, slots=True)
class SplitRatio:
    new_units: int
    old_units: int
    orientation: RatioOrientation


@dataclass(frozen=True, slots=True)
class NoticeRelationship:
    kind: NoticeRelationshipKind
    target_notice_id: str


@dataclass(frozen=True, slots=True)
class CorporateActionEvidence:
    notice_id: str
    event_id: str
    security_anchor: str
    class_id: str
    kind: CorporateActionKind
    lifecycle: EventLifecycle
    recorded_at: str
    scheduled_at: str | None
    effective_at: str | None
    implementation: Implementation
    ratio: SplitRatio | None
    successor_basis_id: str
    continuation: SecurityContinuation
    structure: ActionStructure
    fractional_treatment: FractionalTreatment
    relationships: tuple[NoticeRelationship, ...]


@dataclass(frozen=True, slots=True)
class BaselineBasisAnchor:
    basis_id: str
    security_anchor: str
    class_id: str
    anchored_on: str


@dataclass(frozen=True, slots=True)
class CoverageGap:
    start: str
    end: str
    kinds: tuple[CorporateActionKind, ...]
    description: str


@dataclass(frozen=True, slots=True)
class CorporateActionCoverage:
    security_anchor: str
    class_id: str
    start: str
    through: str
    status: CoverageStatus
    kinds: tuple[CorporateActionKind, ...]
    gaps: tuple[CoverageGap, ...]
    event_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ObservationReference:
    period_start: str
    period_end: str
    version_id: str
    observation_id: str


@dataclass(frozen=True, slots=True)
class EventTreatmentEvidence:
    event_id: str
    treatment: ReportedEventTreatment


@dataclass(frozen=True, slots=True)
class ReportedEPSBasisEvidence:
    references: tuple[ObservationReference, ...]
    security_anchor: str
    class_id: str
    basis_id: str | None
    event_treatments: tuple[EventTreatmentEvidence, ...]


@dataclass(frozen=True, slots=True)
class ShareBasisSnapshot:
    series_semantic_hash: str
    series_evidence_hash: str
    identity_semantic_hash: str
    identity_evidence_hash: str
    baseline: BaselineBasisAnchor | None
    coverage: CorporateActionCoverage | None
    events: tuple[CorporateActionEvidence, ...]
    reported_bases: tuple[ReportedEPSBasisEvidence, ...]


@dataclass(frozen=True, slots=True)
class SyntheticSourceEvidence:
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
    claims: ShareBasisSnapshot


@dataclass(frozen=True, slots=True)
class SyntheticShareBasisEvidenceBundle:
    contract_version: str
    identity_witness: IdentityQualificationWitness
    documents: tuple[SyntheticSourceEvidence, ...]


@dataclass(frozen=True, slots=True)
class ShareBasisEpoch:
    basis_id: str
    security_anchor: str
    class_id: str
    effective_at: str
    predecessor_basis_id: str | None
    event_id: str | None
    split_ratio: SplitRatio | None
    semantic_hash: str


@dataclass(frozen=True, slots=True)
class PeriodShareBasisDecision:
    period_start: str
    period_end: str
    reported_value: Decimal
    annual_supporting_observation_ids: tuple[str, ...]
    filing_version_ids: tuple[str, ...]
    filing_version_observations: tuple[ObservationReference, ...]
    reported_basis_evidence: tuple[ReportedEPSBasisEvidence, ...]
    relevant_events: tuple[CorporateActionEvidence, ...]
    candidate_basis: ShareBasisEpoch | None
    qualified_target_basis: ShareBasisEpoch | None
    compatibility: BasisCompatibility
    blockers: tuple[ShareBasisReason, ...]


@dataclass(frozen=True, slots=True)
class ShareBasisQualification:
    contract_version: str
    qualifier_version: str
    authority: Authority
    transformation_mode: TransformationMode
    series_semantic_hash: str
    series_evidence_hash: str
    identity_semantic_hash: str
    identity_evidence_hash: str
    qualification_boundary: str
    outcome: ShareBasisOutcome
    reasons: tuple[ShareBasisReason, ...]
    limitations: tuple[ShareBasisReason, ...]
    downstream_blockers: tuple[AdmissionBlocker, ...]
    epochs: tuple[ShareBasisEpoch, ...]
    candidate_basis: ShareBasisEpoch | None
    qualified_target_basis: ShareBasisEpoch | None
    period_decisions: tuple[PeriodShareBasisDecision, ...]
    considered_evidence_ids: tuple[str, ...]
    considered_events: tuple[CorporateActionEvidence, ...]
    excluded_notice_ids: tuple[str, ...]
    informational_event_ids: tuple[str, ...]
    semantic_hash: str
    evidence_hash: str


class ShareBasisContractError(ValueError):
    """Closed input corruption, linkage or attempted transformation error."""


_R = ShareBasisReason
_SPLITS = frozenset({CorporateActionKind.FORWARD_SPLIT, CorporateActionKind.REVERSE_SPLIT})


def _require(condition, message):
    if not condition:
        raise ShareBasisContractError(message)


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
        # Exact representation, including sign and exponent; no Decimal operation.
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
    return hashlib.sha256(_json((SHARE_BASIS_CONTRACT_VERSION, SHARE_BASIS_QUALIFIER_VERSION,
                                 domain, value))).hexdigest()


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
    except (ValueError, TypeError) as exc:
        raise ShareBasisContractError("Invalid date") from exc


def _time(value):
    _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?Z", value),
             "Canonical UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.isoformat().replace("+00:00", "Z") == value, "Canonical UTC timestamp required")
        return parsed
    except ValueError as exc:
        raise ShareBasisContractError("Invalid timestamp") from exc


def _instant(value):
    return _day(value) if len(value) == 10 else _time(value)


def _compare(left, right):
    """-1/0/1 or None: a date cannot order an instant on that same day."""
    a, b = _instant(left), _instant(right)
    if type(a) is type(b):
        return (a > b) - (a < b)
    da = a.date() if type(a) is datetime else a
    db = b.date() if type(b) is datetime else b
    return None if da == db else (da > db) - (da < db)


def _anchor(value, kind):
    return re.fullmatch(r"synthetic:" + kind + r":[a-z0-9][a-z0-9_-]*", value) is not None


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "Duplicate source JSON key")
        result[key] = value
    return result


def _invalid_number(value):
    raise ShareBasisContractError("Non-integer source number")


def _verify_source(source):
    _require(source.source_version == SYNTHETIC_EVIDENCE_VERSION
             and source.extraction_version == EXTRACTION_VERSION, "Unknown evidence version")
    _require(_anchor(source.source_reference, "document"), "Synthetic source reference required")
    _require(source.source_locator == "/claims", "Source locator mismatch")
    _require(hashlib.sha256(source.source_bytes).hexdigest() == source.content_sha256, "Source hash mismatch")
    # Metadata is part of the fictional envelope, making detached chronology edits corrupt.
    expected = {f.name: getattr(source, f.name) for f in fields(source)
                if f.name not in {"source_bytes", "content_sha256"}}
    try:
        parsed = json.loads(source.source_bytes, object_pairs_hook=_pairs,
                            parse_float=_invalid_number, parse_constant=_invalid_number)
        _require(_json(parsed) == _json(expected), "Source claims/metadata mismatch")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ShareBasisContractError("Invalid synthetic source") from exc
    _require(_time(source.published_at) <= _time(source.available_at) <= _time(source.captured_at),
             "Invalid publication/availability/capture order")
    return _hash("source-evidence", source)


def _canonical_ratio(ratio):
    if ratio is None:
        return None
    _require(ratio.new_units > 0 and ratio.old_units > 0, "Positive integer split terms required")
    common = gcd(ratio.new_units, ratio.old_units)
    return SplitRatio(ratio.new_units // common, ratio.old_units // common, ratio.orientation)


def _event_core(event):
    return (event.event_id, event.security_anchor, event.class_id, event.kind, event.lifecycle,
            event.scheduled_at, event.effective_at, event.implementation, _canonical_ratio(event.ratio),
            event.successor_basis_id, event.continuation, event.structure, event.fractional_treatment)


def _notice_inventory(events, published_at):
    notices = {}
    for event in _records(events):
        _require(_anchor(event.notice_id, "notice") and _anchor(event.event_id, "event"),
                 "Synthetic event/notice reference required")
        _require(event.notice_id not in notices, "Conflicting bytes for one notice identity")
        _require(_time(event.recorded_at) <= _time(published_at), "Notice after source publication")
        for value in (event.scheduled_at, event.effective_at):
            if value is not None:
                _instant(value)
        _canonical_ratio(event.ratio)
        notices[event.notice_id] = event
    edges = {key: {r.target_notice_id for r in event.relationships} for key, event in notices.items()}
    for key, targets in edges.items():
        _require(targets <= notices.keys(), "Missing related notice")
        for target in targets:
            _require(notices[key].event_id == notices[target].event_id, "Cross-event notice relationship")
    visited, active = set(), set()

    def visit(key):
        _require(key not in active, "Notice relationship cycle")
        if key in visited:
            return
        active.add(key)
        for target in edges[key]:
            visit(target)
        active.remove(key)
        visited.add(key)

    for key in edges:
        visit(key)
    for key, targets in edges.items():
        for target in targets:
            _require(_time(notices[target].recorded_at) < _time(notices[key].recorded_at),
                     "Correction must follow related notice")
    excluded = set().union(*edges.values()) if edges else set()
    return notices, excluded


def _epochs(snapshot, security_anchor, class_id, oldest, boundary, published_at):
    reasons, epochs, information = set(), [], set()
    baseline, coverage = snapshot.baseline, snapshot.coverage
    if baseline is not None:
        _day(baseline.anchored_on)
    if (baseline is None or not _anchor(baseline.basis_id, "basis")
            or (baseline.security_anchor, baseline.class_id) != (security_anchor, class_id)
            or _day(baseline.anchored_on) > _day(oldest)):
        reasons.add(_R.BASELINE_BASIS_UNRESOLVED)
    notices, excluded = _notice_inventory(snapshot.events, published_at)
    event_ids = {e.event_id for e in notices.values()}
    if coverage is not None:
        _require(_day(coverage.start) <= _day(coverage.through), "Reversed coverage interval")
        for gap in coverage.gaps:
            _require(_day(gap.start) <= _day(gap.end), "Reversed coverage gap")
    if (coverage is None or baseline is None or coverage.status is not CoverageStatus.COMPLETE
            or (coverage.security_anchor, coverage.class_id) != (security_anchor, class_id)
            or set(coverage.kinds) != set(CorporateActionKind) or coverage.gaps
            or set(coverage.event_ids) != event_ids
            or _day(coverage.start) > _day(baseline.anchored_on)
            or _day(coverage.through) < _time(boundary).date()):
        reasons.add(_R.CORPORATE_ACTION_COVERAGE_GAP)
    effective = []
    for event_id in sorted(event_ids):
        history = [e for e in notices.values() if e.event_id == event_id]
        current = [e for e in history if e.notice_id not in excluded]
        if len({_json(_event_core(e)) for e in current}) != 1:
            reasons.add(_R.CORPORATE_ACTION_CONFLICT)
            continue
        event = sorted(current, key=lambda e: e.notice_id)[0]  # Equivalent citations only.
        implemented = [e for e in history if e.implementation is Implementation.CONFIRMED]
        if implemented and (event.lifecycle is not EventLifecycle.EFFECTIVE
                            or event.implementation is not Implementation.CONFIRMED):
            reasons.add(_R.CORPORATE_ACTION_CONFLICT)
        if (event.security_anchor, event.class_id) != (security_anchor, class_id):
            reasons.add(_R.EVENT_SECURITY_UNRESOLVED)
        # Explicitly future proposals are informational only with complete coverage.
        when = event.effective_at if event.lifecycle is EventLifecycle.EFFECTIVE else event.scheduled_at
        if when is not None and _compare(when, boundary) == 1 and not implemented:
            information.add(event_id)
            continue
        if (event.lifecycle is EventLifecycle.CANCELLED
                and event.implementation is Implementation.NEVER_IMPLEMENTED and not implemented):
            information.add(event_id)
            continue
        if event.kind not in _SPLITS or event.structure is ActionStructure.ASSOCIATED_RESTRUCTURING:
            reasons.add(_R.UNSUPPORTED_CORPORATE_ACTION)
        if event.lifecycle is not EventLifecycle.EFFECTIVE or event.implementation is not Implementation.CONFIRMED:
            reasons.add(_R.EVENT_IMPLEMENTATION_UNCONFIRMED)
        if event.effective_at is None or _compare(event.effective_at, boundary) is None:
            reasons.add(_R.EVENT_EFFECTIVE_DATE_UNRESOLVED)
        elif _compare(event.effective_at, boundary) == 1:
            # A claimed implementation cannot precede its effective chronology.
            reasons.add(_R.CORPORATE_ACTION_CONFLICT)
        if event.implementation is Implementation.CONFIRMED and event.effective_at is not None:
            if _compare(event.effective_at, event.recorded_at) not in (-1, 0):
                reasons.add(_R.EVENT_IMPLEMENTATION_UNCONFIRMED)
        if event.continuation is not SecurityContinuation.SAME_SECURITY_AND_CLASS:
            reasons.add(_R.SECURITY_CONTINUATION_UNRESOLVED)
        if event.fractional_treatment is FractionalTreatment.CASH_SETTLEMENT:
            reasons.add(_R.FRACTIONAL_SETTLEMENT_UNSUPPORTED)
        elif event.fractional_treatment is not FractionalTreatment.NO_FRACTIONAL_SETTLEMENT:
            reasons.add(_R.FRACTIONAL_TREATMENT_UNRESOLVED)
        ratio = event.ratio
        if (ratio is None or ratio.orientation is not RatioOrientation.NEW_UNITS_PER_OLD_UNITS
                or ratio.new_units == ratio.old_units
                or (event.kind is CorporateActionKind.FORWARD_SPLIT and ratio.new_units < ratio.old_units)
                or (event.kind is CorporateActionKind.REVERSE_SPLIT and ratio.new_units > ratio.old_units)
                or event.structure is ActionStructure.UNRESOLVED):
            reasons.add(_R.EVENT_TERMS_UNRESOLVED)
        if not _anchor(event.successor_basis_id, "basis"):
            reasons.add(_R.EVENT_TERMS_UNRESOLVED)
        if baseline is not None and event.effective_at is not None:
            # An event before the anchor is already represented by the explicit baseline.
            relation = _compare(event.effective_at, baseline.anchored_on)
            if relation == -1:
                information.add(event_id)
                continue
            if relation in (0, None):
                reasons.add(_R.BASELINE_BASIS_UNRESOLVED)
        effective.append(event)
    for n, a in enumerate(effective):
        for b in effective[n + 1:]:
            if a.effective_at is None or b.effective_at is None:
                continue
            if _compare(a.effective_at, b.effective_at) in (0, None):
                reasons.add(_R.EVENT_ORDER_UNRESOLVED)
    if reasons:
        return reasons, (), (), tuple(sorted(excluded)), tuple(sorted(information))
    # Pairwise checks proved that chronological keys have no ambiguous ties.
    ordered = tuple(sorted(effective, key=cmp_to_key(
        lambda a, b: _compare(a.effective_at, b.effective_at))))
    baseline_core = (baseline.basis_id, security_anchor, class_id, baseline.anchored_on)
    epochs.append(ShareBasisEpoch(*baseline_core, None, None, None, _hash("baseline-basis", baseline_core)))
    for event in ordered:
        previous = epochs[-1]
        if event.successor_basis_id in {e.basis_id for e in epochs}:
            reasons.add(_R.CORPORATE_ACTION_CONFLICT)
            break
        ratio = _canonical_ratio(event.ratio)
        core = (event.successor_basis_id, security_anchor, class_id, event.effective_at,
                previous.basis_id, event.event_id, ratio)
        epochs.append(ShareBasisEpoch(*core, _hash("successor-basis", (previous.semantic_hash, core))))
    return reasons, tuple(epochs) if not reasons else (), ordered, tuple(sorted(excluded)), tuple(sorted(information))


def _references(period):
    return _records(ObservationReference(period.period_start, period.period_end, v.semantic_id, o)
                    for v in period.filing_versions for o in v.observation_ids)


def _canonical_report(claim):
    return replace(claim, references=_records(claim.references), event_treatments=_records(claim.event_treatments))


def _inspect_reports(snapshot, series, security_anchor, class_id, epochs, ordered):
    claims = _records(_canonical_report(c) for c in snapshot.reported_bases)
    all_refs = {r for p in series.periods for r in _references(p)}
    all_event_ids = {e.event_id for e in snapshot.events}
    incorporated_ids = {e.event_id for e in ordered}
    # Events proven implemented before the explicit anchor are already part of
    # its denomination. Cancelled or future proposals cannot be incorporated.
    if snapshot.baseline is not None:
        incorporated_ids.update(e.event_id for e in snapshot.events
            if e.implementation is Implementation.CONFIRMED and e.effective_at is not None
            and _compare(e.effective_at, snapshot.baseline.anchored_on) == -1)
    for claim in claims:
        _require(bool(claim.references) and set(claim.references) <= all_refs, "Broken observation/version linkage")
        _require({t.event_id for t in claim.event_treatments} <= all_event_ids, "Unknown treatment event reference")
    target = epochs[-1] if epochs else None
    index = {e.basis_id: n for n, e in enumerate(epochs)}
    rows = []
    for period in series.periods:
        reasons, basis_ids, relevant_claims = set(), set(), []
        for reference in _references(period):
            matches = [c for c in claims if reference in c.references]
            if not matches:
                reasons.update((_R.SUPPORTING_VERSION_COVERAGE_GAP, _R.REPORTED_BASIS_UNRESOLVED))
            meanings = {(c.security_anchor, c.class_id, c.basis_id, c.event_treatments) for c in matches}
            if len(meanings) > 1:
                reasons.add(_R.REPORTED_BASIS_CONFLICT)
            for claim in matches:
                relevant_claims.append(claim)
                if (claim.security_anchor, claim.class_id) != (security_anchor, class_id):
                    reasons.add(_R.REPORTED_BASIS_CONFLICT)
                if epochs and any(t.treatment is ReportedEventTreatment.INCORPORATED
                                  and t.event_id not in incorporated_ids for t in claim.event_treatments):
                    reasons.add(_R.REPORTED_BASIS_CONFLICT)
                if claim.basis_id is not None:
                    basis_ids.add(claim.basis_id)
                if claim.basis_id not in index:
                    reasons.add(_R.REPORTED_BASIS_UNRESOLVED)
                elif target is not None and claim.basis_id != target.basis_id:
                    reasons.add(_R.BASIS_NORMALIZATION_REQUIRED)
                for n, event in enumerate(ordered, start=1):
                    treatments = {t.treatment for t in claim.event_treatments if t.event_id == event.event_id}
                    if not treatments or ReportedEventTreatment.UNRESOLVED in treatments:
                        reasons.add(_R.REPORTED_EVENT_TREATMENT_UNRESOLVED)
                    if len(treatments) > 1:
                        reasons.add(_R.REPORTED_BASIS_CONFLICT)
                    if claim.basis_id in index and treatments:
                        expected = (ReportedEventTreatment.INCORPORATED if index[claim.basis_id] >= n
                                    else ReportedEventTreatment.NOT_INCORPORATED)
                        if treatments != {expected} and ReportedEventTreatment.UNRESOLVED not in treatments:
                            reasons.add(_R.REPORTED_BASIS_CONFLICT)
        if len(basis_ids) > 1:
            reasons.add(_R.MIXED_REPORTED_BASES)
        compatibility = (BasisCompatibility.DIFFERENT_BASIS if reasons == {_R.BASIS_NORMALIZATION_REQUIRED}
                         else BasisCompatibility.UNRESOLVED if reasons or target is None
                         else BasisCompatibility.TARGET_BASIS)
        rows.append((reasons, _records(relevant_claims), compatibility, basis_ids))
    return rows


def _replay_identity_profile(series, identity, witness):
    """The only source-profile interpretation: call the unchanged PR4C4 qualifier."""
    try:
        replay = qualify_security_identity(series, witness.request, witness.evidence)
    except identity_profile.IdentityContractError as exc:
        raise ShareBasisContractError("Invalid upstream identity witness or series") from exc
    # PR4C3's economic projection is reproducible from the series. Use its exact
    # pinned encoder; its full evidence hash requires the original archive and
    # extraction, which this pure qualification boundary deliberately does not read.
    semantic = dict(contract=series.contract_version, resolver=series.resolver_version,
        cik=series.cik, namespace=series.namespace, concept=series.concept, unit=series.unit,
        accounting_basis=series.accounting_basis, mode=series.mode, period_policy=series.period_policy,
        periods=[(p.period_start, p.period_end, p.value) for p in series.periods])
    _require(series_profile._hash(semantic) == series.semantic_hash, "Upstream series semantic hash mismatch")
    _require(_json(replay) == _json(identity), "Identity qualification does not match exact replay")


def qualify_share_basis(
    series: ResolvedAnnualDilutedEPSSeries,
    identity: SecurityIdentityQualification,
    request: ShareBasisRequest,
    evidence: SyntheticShareBasisEvidenceBundle,
) -> ShareBasisQualification:
    """Qualify one evidenced denomination without any operation on reported EPS.

    Each mandatory snapshot must independently cover baseline through boundary and
    every retained filing observation. Later identity validity requires a newly
    supplied exact successful PR4C4 replay at that boundary; no silent extension.
    """
    for value, kind in ((series, ResolvedAnnualDilutedEPSSeries), (identity, SecurityIdentityQualification),
                        (request, ShareBasisRequest), (evidence, SyntheticShareBasisEvidenceBundle)):
        _typed(value, kind)
    _require(request.contract_version == SHARE_BASIS_CONTRACT_VERSION
             and evidence.contract_version == SYNTHETIC_EVIDENCE_VERSION, "Unknown share-basis contract")
    _require((request.series_semantic_hash, request.series_evidence_hash,
              request.identity_semantic_hash, request.identity_evidence_hash)
             == (series.semantic_hash, series.evidence_hash, identity.semantic_hash, identity.evidence_hash),
             "Request/upstream identity mismatch")
    _replay_identity_profile(series, identity, evidence.identity_witness)
    documents = _records(evidence.documents)
    source_ids = tuple(sorted({_verify_source(d) for d in documents}))
    boundary_time = max((_time(series.authority_as_of),
                         *(_time(d.captured_at) for d in documents),
                         *((_time(identity.qualification_as_of),) if identity.qualification_as_of else ())))
    boundary = boundary_time.isoformat().replace("+00:00", "Z")
    reasons = set()
    if identity.outcome is not identity_profile.IdentityOutcome.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE:
        reasons.add(_R.SECURITY_IDENTITY_NOT_QUALIFIED)
    if identity.qualification_as_of is None or boundary_time > _time(identity.qualification_as_of):
        reasons.add(_R.IDENTITY_BOUNDARY_NOT_QUALIFIED)
    if request.mode is ShareBasisMode.HISTORICAL_AS_OF:
        reasons.add(_R.HISTORICAL_BASIS_UNSUPPORTED)
    security_anchor = identity.security.anchor if identity.security else evidence.identity_witness.request.security_anchor
    class_id = identity.security.common_class.class_id if identity.security else ""
    if not documents:
        reasons.update((_R.CORPORATE_ACTION_COVERAGE_GAP, _R.BASELINE_BASIS_UNRESOLVED,
                        _R.SUPPORTING_VERSION_COVERAGE_GAP, _R.REPORTED_BASIS_UNRESOLVED))
    inspections, report_rows, excluded, information = [], [], set(), set()
    for source in documents:
        snapshot = source.claims
        _require((snapshot.series_semantic_hash, snapshot.series_evidence_hash,
                  snapshot.identity_semantic_hash, snapshot.identity_evidence_hash)
                 == (series.semantic_hash, series.evidence_hash, identity.semantic_hash, identity.evidence_hash),
                 "Source/upstream identity mismatch")
        inspected = _epochs(snapshot, security_anchor, class_id, series.periods[0].period_start,
                            boundary, source.published_at)
        inspections.append(inspected)
        reasons.update(inspected[0])
        excluded.update(inspected[3])
        information.update(inspected[4])
        report_rows.append(_inspect_reports(snapshot, series, security_anchor, class_id,
                                           inspected[1], inspected[2]))
    # Complete snapshots cannot hide a missing event or manufacture completeness by union.
    cores = [(tuple(e.semantic_hash for e in x[1]),
              _records(_event_core(e) for e in d.claims.events if e.notice_id not in x[3]))
             for x, d in zip(inspections, documents)]
    if len({_json(c) for c in cores}) > 1:
        reasons.add(_R.CORPORATE_ACTION_CONFLICT)
    epochs = inspections[0][1] if inspections and len({_json(c) for c in cores}) == 1 else ()
    candidate = epochs[-1] if epochs else None
    events = _records(e for d in documents for e in d.claims.events)
    period_rows = []
    all_bases = set()
    for n, period in enumerate(series.periods):
        local = set()
        claims = _records(c for rows in report_rows for c in rows[n][1])
        for rows in report_rows:
            local.update(rows[n][0])
            all_bases.update(rows[n][3])
        # Disagreement between otherwise complete snapshots is still a source conflict.
        for reference in _references(period):
            meanings = {(c.security_anchor, c.class_id, c.basis_id, c.event_treatments)
                        for c in claims if reference in c.references}
            if len(meanings) > 1:
                local.add(_R.REPORTED_BASIS_CONFLICT)
        reasons.update(local)
        period_rows.append((local, claims))
    if len(all_bases) > 1:
        reasons.add(_R.MIXED_REPORTED_BASES)
    outcome = (ShareBasisOutcome.BASIS_UNSUPPORTED if any(
        r in reasons for r in (_R.UNSUPPORTED_CORPORATE_ACTION, _R.FRACTIONAL_SETTLEMENT_UNSUPPORTED,
                              _R.HISTORICAL_BASIS_UNSUPPORTED)) else ShareBasisOutcome.BASIS_UNAVAILABLE
        ) if reasons else ShareBasisOutcome.COMPARABLE_BASIS_ESTABLISHED
    target = candidate if not reasons else None
    decisions = tuple(PeriodShareBasisDecision(p.period_start, p.period_end, p.value,
        p.supporting_observation_ids, p.version_ids, _references(p), claims, events,
        candidate, target,
        BasisCompatibility.TARGET_BASIS if not reasons else
        BasisCompatibility.DIFFERENT_BASIS if local == {_R.BASIS_NORMALIZATION_REQUIRED}
        else BasisCompatibility.UNRESOLVED, _reasons(reasons | local))
        for p, (local, claims) in zip(series.periods, period_rows))
    limitations = (_R.SYNTHETIC_EVIDENCE_ONLY,)
    blockers = tuple(sorted(set(series.downstream_admission_blockers) | set(identity.downstream_blockers),
                            key=lambda b: b.value))
    # Upstream semantic IDs bind exact economic EPS meaning. Observation IDs and
    # Decimal spelling belong in evidence, not economic semantic identity.
    semantic = (series.semantic_hash, identity.semantic_hash, request.mode, outcome, _reasons(reasons),
                tuple(e.semantic_hash for e in epochs),
                _records(_event_core(e) for e in events if e.notice_id not in excluded),
                tuple((p.period_start, p.period_end,
                       _records((c.basis_id, c.event_treatments) for c in claims))
                      for p, (_, claims) in zip(series.periods, period_rows)))
    semantic_hash = _hash("qualification-semantics", semantic)
    evidence_hash = _hash("qualification-evidence", (semantic_hash, request, series, identity, source_ids,
        evidence.identity_witness, boundary, decisions, events, tuple(sorted(excluded)), tuple(sorted(information)),
        blockers, limitations))
    return ShareBasisQualification(SHARE_BASIS_CONTRACT_VERSION, SHARE_BASIS_QUALIFIER_VERSION,
        Authority.SYNTHETIC_TEST_ONLY, TransformationMode.NONE, series.semantic_hash, series.evidence_hash,
        identity.semantic_hash, identity.evidence_hash, boundary, outcome, _reasons(reasons), limitations,
        blockers, epochs, candidate, target, decisions, source_ids, events, tuple(sorted(excluded)),
        tuple(sorted(information)), semantic_hash, evidence_hash)
