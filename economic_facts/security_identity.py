"""Pure synthetic identity mechanics. Never a real admission capability.

Every source is a complete, closed synthetic snapshot, checked against its bytes.
All supplied snapshots must independently agree at their joint capture boundary;
there is no latest-wins rule, partial-source stitching, or caller as-of override.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import hashlib
import json
import re
from types import UnionType
from typing import get_args, get_origin, get_type_hints

from .sec_eps_series import (
    AdmissionBlocker, CaptureAuthorityAssessment, FilingVersionReference,
    ResolvedAnnualDilutedEPS, ResolvedAnnualDilutedEPSSeries,
    PeriodPolicy, ResolutionMode, ResolutionStatus, SERIES_CONTRACT_VERSION, SERIES_RESOLVER_VERSION,
)

IDENTITY_CONTRACT_VERSION = "2026-09-12-security-identity-contract-v1"
IDENTITY_QUALIFIER_VERSION = "2026-09-12-single-common-class-identity-qualifier-v1"
SYNTHETIC_EVIDENCE_VERSION = "2026-09-12-synthetic-security-identity-evidence-v1"
EXTRACTION_VERSION = "2026-09-12-synthetic-identity-claims-v1"


class Authority(Enum):
    SYNTHETIC_TEST_ONLY = "SYNTHETIC_TEST_ONLY"


class IdentityMode(Enum):
    CURRENT_SNAPSHOT = "CURRENT_SNAPSHOT"
    HISTORICAL_AS_OF = "HISTORICAL_AS_OF"


class IdentityOutcome(Enum):
    IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE = "IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE"
    IDENTITY_UNAVAILABLE = "IDENTITY_UNAVAILABLE"
    IDENTITY_UNSUPPORTED = "IDENTITY_UNSUPPORTED"


class IdentityReason(Enum):
    ISSUER_IDENTIFIER_MISMATCH = "ISSUER_IDENTIFIER_MISMATCH"
    TICKER_ONLY_IDENTITY_INSUFFICIENT = "TICKER_ONLY_IDENTITY_INSUFFICIENT"
    SECURITY_IDENTIFIER_UNRESOLVED = "SECURITY_IDENTIFIER_UNRESOLVED"
    SHARE_CLASS_UNRESOLVED = "SHARE_CLASS_UNRESOLVED"
    COMMON_CLASS_INVENTORY_INCOMPLETE = "COMMON_CLASS_INVENTORY_INCOMPLETE"
    MULTIPLE_COMMON_CLASSES_UNSUPPORTED = "MULTIPLE_COMMON_CLASSES_UNSUPPORTED"
    EPS_CLASS_APPLICABILITY_UNRESOLVED = "EPS_CLASS_APPLICABILITY_UNRESOLVED"
    PARTICIPATION_RIGHTS_UNRESOLVED = "PARTICIPATION_RIGHTS_UNRESOLVED"
    INSTRUMENT_TYPE_UNSUPPORTED = "INSTRUMENT_TYPE_UNSUPPORTED"
    DEPOSITARY_RECEIPT_UNSUPPORTED = "DEPOSITARY_RECEIPT_UNSUPPORTED"
    LISTING_UNRESOLVED = "LISTING_UNRESOLVED"
    DUAL_LISTING_UNSUPPORTED = "DUAL_LISTING_UNSUPPORTED"
    LISTING_MIGRATION_UNSUPPORTED = "LISTING_MIGRATION_UNSUPPORTED"
    LISTING_CURRENCY_OR_UNIT_UNRESOLVED = "LISTING_CURRENCY_OR_UNIT_UNRESOLVED"
    LISTING_PROFILE_UNSUPPORTED = "LISTING_PROFILE_UNSUPPORTED"
    EFFECTIVE_INTERVAL_UNRESOLVED = "EFFECTIVE_INTERVAL_UNRESOLVED"
    IDENTITY_EVIDENCE_CONFLICT = "IDENTITY_EVIDENCE_CONFLICT"
    SECURITY_CONTINUITY_UNRESOLVED = "SECURITY_CONTINUITY_UNRESOLVED"
    CORPORATE_REORGANIZATION_UNSUPPORTED = "CORPORATE_REORGANIZATION_UNSUPPORTED"
    HISTORICAL_IDENTITY_UNSUPPORTED = "HISTORICAL_IDENTITY_UNSUPPORTED"
    SYNTHETIC_EVIDENCE_ONLY = "SYNTHETIC_EVIDENCE_ONLY"


class InstrumentType(Enum):
    ORDINARY_COMMON_EQUITY = "ORDINARY_COMMON_EQUITY"
    PREFERRED_EQUITY = "PREFERRED_EQUITY"
    FUND = "FUND"
    PARTNERSHIP_UNIT = "PARTNERSHIP_UNIT"
    WARRANT = "WARRANT"
    OPTION = "OPTION"
    CONVERTIBLE_SECURITY = "CONVERTIBLE_SECURITY"
    DEPOSITARY_RECEIPT = "DEPOSITARY_RECEIPT"
    ADR = "ADR"
    ADS = "ADS"
    CDR = "CDR"
    COMPOSITE = "COMPOSITE"
    UNKNOWN = "UNKNOWN"


class InventoryCoverage(Enum):
    COMPLETE_WITHIN_INTERVAL = "COMPLETE_WITHIN_INTERVAL"
    INCOMPLETE = "INCOMPLETE"


class Participation(Enum):
    ORDINARY_RESIDUAL_COMMON = "ORDINARY_RESIDUAL_COMMON"
    DIFFERENT_PARTICIPATION_RIGHTS = "DIFFERENT_PARTICIPATION_RIGHTS"
    UNRESOLVED = "UNRESOLVED"


class Continuity(Enum):
    UNCHANGED_SECURITY = "UNCHANGED_SECURITY"
    REORGANIZATION = "REORGANIZATION"
    SUCCESSOR = "SUCCESSOR"
    UNRESOLVED = "UNRESOLVED"


class ListingKind(Enum):
    DIRECT = "DIRECT"
    DEPOSITARY = "DEPOSITARY"
    INFERRED = "INFERRED"


class QuoteUnit(Enum):
    MAJOR_CURRENCY_UNIT = "MAJOR_CURRENCY_UNIT"
    MINOR_CURRENCY_UNIT = "MINOR_CURRENCY_UNIT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class EffectiveInterval:
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class IssuerClaim:
    anchor: str
    cik: str
    descriptive_name: str
    interval: EffectiveInterval


@dataclass(frozen=True, slots=True)
class CommonClass:
    class_id: str
    legal_designation: str
    economic_designation: str
    participation: Participation


@dataclass(frozen=True, slots=True)
class CommonClassInventory:
    issuer_anchor: str
    interval: EffectiveInterval
    coverage: InventoryCoverage
    classes: tuple[CommonClass, ...]


@dataclass(frozen=True, slots=True)
class SecurityClaim:
    anchor: str
    issuer_anchor: str
    instrument_type: InstrumentType
    common_class: CommonClass
    interval: EffectiveInterval
    secondary_identifiers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ListingClaim:
    anchor: str
    security_anchor: str
    venue: str
    symbol: str
    quote_currency: str
    quote_unit: QuoteUnit
    kind: ListingKind
    interval: EffectiveInterval


@dataclass(frozen=True, slots=True)
class ListingInventory:
    security_anchor: str
    interval: EffectiveInterval
    coverage: InventoryCoverage
    listing_anchors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SymbolContinuity:
    listing_anchor: str
    security_anchor: str
    venue: str
    previous_symbol: str
    next_symbol: str
    effective_on: str


@dataclass(frozen=True, slots=True)
class EPSApplicabilityClaim:
    series_semantic_hash: str
    series_evidence_hash: str
    period: EffectiveInterval
    security_anchor: str
    class_id: str
    version_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IdentitySnapshot:
    issuer: IssuerClaim
    securities: tuple[SecurityClaim, ...]
    class_inventory: CommonClassInventory | None
    listings: tuple[ListingClaim, ...]
    listing_inventory: ListingInventory | None
    symbol_continuities: tuple[SymbolContinuity, ...]
    eps_applicability: tuple[EPSApplicabilityClaim, ...]
    continuity: Continuity


@dataclass(frozen=True, slots=True)
class SyntheticSourceEvidence:
    source_kind: Authority
    source_reference: str
    source_version: str
    source_locator: str
    extraction_version: str
    published_at: str
    available_at: str
    captured_at: str
    source_bytes: bytes
    content_sha256: str
    claims: IdentitySnapshot


@dataclass(frozen=True, slots=True)
class SyntheticIdentityEvidenceBundle:
    contract_version: str
    documents: tuple[SyntheticSourceEvidence, ...]


@dataclass(frozen=True, slots=True)
class SecurityIdentityRequest:
    contract_version: str
    mode: IdentityMode
    series_semantic_hash: str
    series_evidence_hash: str
    security_anchor: str
    listing_anchor: str


@dataclass(frozen=True, slots=True)
class IssuerIdentity:
    anchor: str
    cik: str
    descriptive_names: tuple[str, ...]
    interval: EffectiveInterval
    evidence_ids: tuple[str, ...]
    semantic_hash: str


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    anchor: str
    issuer_anchor: str
    instrument_type: InstrumentType
    common_class: CommonClass
    interval: EffectiveInterval
    secondary_identifiers: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    semantic_hash: str


@dataclass(frozen=True, slots=True)
class ListingIdentity:
    anchor: str
    security_anchor: str
    venue: str
    symbol: str
    quote_currency: str
    quote_unit: QuoteUnit
    interval: EffectiveInterval
    evidence_ids: tuple[str, ...]
    semantic_hash: str


@dataclass(frozen=True, slots=True)
class EPSClassApplicabilityDecision:
    period: EffectiveInterval
    security_anchor: str
    class_id: str
    version_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SecurityIdentityQualification:
    contract_version: str
    qualifier_version: str
    authority: Authority
    series_semantic_hash: str
    series_evidence_hash: str
    issuer: IssuerIdentity | None
    security: SecurityIdentity | None
    listing: ListingIdentity | None
    applicability_decisions: tuple[EPSClassApplicabilityDecision, ...]
    qualification_as_of: str | None
    outcome: IdentityOutcome
    reasons: tuple[IdentityReason, ...]
    downstream_blockers: tuple[AdmissionBlocker, ...]
    limitations: tuple[IdentityReason, ...]
    considered_evidence_ids: tuple[str, ...]
    semantic_hash: str
    evidence_hash: str


class IdentityContractError(ValueError):
    """Malformed closed inputs or broken byte/series linkage, not weak evidence."""


_R = IdentityReason
_SUPPORTED_VENUES = frozenset({"MIC:XNYS", "MIC:XNAS"})
_DEPOSITARY = frozenset({InstrumentType.DEPOSITARY_RECEIPT, InstrumentType.ADR,
                        InstrumentType.ADS, InstrumentType.CDR})
_REQUIRED_BLOCKERS = frozenset(b for b in AdmissionBlocker
                              if b is not AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED)
_INPUT_RECORDS = frozenset({EffectiveInterval, IssuerClaim, CommonClass, CommonClassInventory,
    SecurityClaim, ListingClaim, ListingInventory, SymbolContinuity, EPSApplicabilityClaim,
    IdentitySnapshot, SyntheticSourceEvidence, SyntheticIdentityEvidenceBundle, SecurityIdentityRequest,
    ResolvedAnnualDilutedEPSSeries, ResolvedAnnualDilutedEPS, FilingVersionReference,
    CaptureAuthorityAssessment})


def _require(condition, message):
    if not condition:
        raise IdentityContractError(message)


def _typed(value, expected):
    """Exact recursive types: bool/int, mutable containers and subclasses never coerce."""
    origin, args = get_origin(expected), get_args(expected)
    if origin is UnionType:
        matches = [t for t in args if type(value) is t]
        _require(len(matches) == 1, "Invalid optional record")
        return _typed(value, matches[0])
    if origin is tuple:
        _require(type(value) is tuple, "Immutable tuple required")
        for item in value:
            _typed(item, args[0])
        return
    _require(type(value) is expected, "Exact closed type required")
    if expected in _INPUT_RECORDS:
        for key, kind in get_type_hints(expected).items():
            _typed(getattr(value, key), kind)
    elif is_dataclass(value):
        raise IdentityContractError("Unknown input record")
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
        digits = list(digits)
        if not any(digits):
            return {"decimal": "0"}
        while digits[-1] == 0:
            digits.pop()
            exponent += 1
        return {"decimal": ("-" if sign else "") + "".join(map(str, digits)) + "e" + str(exponent)}
    if type(value) in (list, tuple):
        return [_project(v) for v in value]
    if type(value) is dict:
        return {k: _project(v) for k, v in value.items()}
    return value


def _json(value):
    return json.dumps(_project(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _hash(domain, value):
    return hashlib.sha256(_json((IDENTITY_CONTRACT_VERSION, IDENTITY_QUALIFIER_VERSION,
                                 domain, value))).hexdigest()


def _unique(values):
    return tuple(sorted(set(values)))


def _records(values):
    # Equal source claims are transport duplicates; contradictory claims survive.
    by_content = {_json(v): v for v in values}
    return tuple(by_content[k] for k in sorted(by_content))


def _day(value):
    try:
        parsed = date.fromisoformat(value)
        _require(parsed.isoformat() == value, "Canonical ISO date required")
        return parsed
    except (ValueError, TypeError) as exc:
        raise IdentityContractError("Invalid effective date") from exc


def _time(value):
    _require(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{6})?Z", value),
             "Canonical UTC timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.isoformat().replace("+00:00", "Z") == value, "Canonical UTC timestamp required")
        return parsed
    except ValueError as exc:
        raise IdentityContractError("Invalid chronology") from exc


def _covers(interval, start, end):
    return _day(interval.start) <= start <= end <= _day(interval.end)


def _anchor(value, kind):
    return re.fullmatch(r"synthetic:" + kind + r":[a-z0-9][a-z0-9_-]*", value) is not None


def _validate_dates(value):
    if type(value) is EffectiveInterval:
        _require(_day(value.start) <= _day(value.end), "Reversed effective interval")
    elif type(value) is SymbolContinuity:
        _day(value.effective_on)
    elif is_dataclass(value):
        for f in fields(value):
            _validate_dates(getattr(value, f.name))
    elif type(value) is tuple:
        for item in value:
            _validate_dates(item)


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, "Duplicate source JSON key")
        result[key] = value
    return result


def _nonfinite(value):
    raise IdentityContractError("Nonfinite source JSON")


def _verify_source(source):
    _require(source.source_kind is Authority.SYNTHETIC_TEST_ONLY, "Synthetic source required")
    _require(source.source_version == SYNTHETIC_EVIDENCE_VERSION
             and source.extraction_version == EXTRACTION_VERSION, "Unknown source/extraction version")
    _require(_anchor(source.source_reference, "document"), "Synthetic document reference required")
    _require(source.source_locator == "/claims", "Source locator mismatch")
    _require(hashlib.sha256(source.source_bytes).hexdigest() == source.content_sha256, "Source hash mismatch")
    try:
        parsed = json.loads(source.source_bytes, object_pairs_hook=_pairs, parse_constant=_nonfinite)
        expected = {"schema_version": SYNTHETIC_EVIDENCE_VERSION, "claims": source.claims}
        _require(_json(parsed) == _json(expected), "Closed source claims/locator mismatch")
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise IdentityContractError("Invalid synthetic source") from exc
    _require(_time(source.published_at) <= _time(source.available_at) <= _time(source.captured_at),
             "Invalid publication/availability/capture order")
    _validate_dates(source.claims)
    return _hash("source-evidence", source)


def _validate_series(series, request):
    _typed(series, ResolvedAnnualDilutedEPSSeries)
    _require(series.contract_version == SERIES_CONTRACT_VERSION
             and series.resolver_version == SERIES_RESOLVER_VERSION
             and series.status is ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
             and series.mode is ResolutionMode.CURRENT_AS_REPORTED, "Resolved current PR4C3 series required")
    _require((series.namespace, series.concept, series.unit, series.accounting_basis)
             == ("us-gaap", "EarningsPerShareDiluted", "USD/shares", "US_GAAP")
             and series.period_policy is PeriodPolicy.FIXED_MONTH_END_365_366,
             "Unsupported upstream series semantics")
    _require(re.fullmatch(r"[0-9]{10}", series.cik), "Exact series CIK required")
    for value in (series.semantic_hash, series.evidence_hash):
        _require(re.fullmatch(r"[0-9a-f]{64}", value), "SHA-256 series identity required")
    _require((request.series_semantic_hash, request.series_evidence_hash)
             == (series.semantic_hash, series.evidence_hash), "Request/series identity mismatch")
    _require(_REQUIRED_BLOCKERS <= set(series.downstream_admission_blockers), "Upstream blockers missing")
    _require(series.authority_as_of == series.capture_authority.captured_at, "Series authority mismatch")
    _time(series.authority_as_of)
    _require(len(series.periods) == 5, "Exactly five resolved periods required")
    previous = None
    for period in series.periods:
        start, end = _day(period.period_start), _day(period.period_end)
        _require((end - start).days + 1 == period.inclusive_days and period.inclusive_days in (365, 366),
                 "Invalid upstream period")
        _require(previous is None or start == previous + timedelta(days=1), "Nonconsecutive upstream periods")
        previous = end
        _require(bool(period.filing_versions) and len(set(period.version_ids)) == len(period.version_ids)
                 and set(period.version_ids) == {v.semantic_id for v in period.filing_versions}
                 and len(period.version_ids) == len(period.filing_versions), "Invalid upstream filing inventory")
        observations = {o for v in period.filing_versions for o in v.observation_ids}
        _require(observations == set(period.supporting_observation_ids)
                 and len(set(period.supporting_observation_ids)) == len(period.supporting_observation_ids)
                 and all(v.observation_ids for v in period.filing_versions)
                 and period.representative_observation_id in observations, "Invalid upstream observation inventory")
    _require(series.latest_required_fiscal_end == series.periods[-1].period_end, "Invalid latest period")


def _security_core(claim):
    return (claim.anchor, claim.issuer_anchor, claim.instrument_type, claim.common_class, claim.interval)


def _inspect_snapshot(snapshot, series, request, boundary):
    reasons = set()
    start, end = _day(series.periods[0].period_start), boundary.date()
    issuer = snapshot.issuer
    if issuer.cik != series.cik or not _anchor(issuer.anchor, "issuer"):
        reasons.add(_R.ISSUER_IDENTIFIER_MISMATCH)
    if not _covers(issuer.interval, start, end):
        reasons.add(_R.EFFECTIVE_INTERVAL_UNRESOLVED)
    if snapshot.continuity in (Continuity.REORGANIZATION, Continuity.SUCCESSOR):
        reasons.add(_R.CORPORATE_REORGANIZATION_UNSUPPORTED)
    elif snapshot.continuity is not Continuity.UNCHANGED_SECURITY:
        reasons.add(_R.SECURITY_CONTINUITY_UNRESOLVED)

    securities = _records(snapshot.securities)
    if any(s.instrument_type in _DEPOSITARY for s in securities):
        reasons.add(_R.DEPOSITARY_RECEIPT_UNSUPPORTED)
    if any(s.instrument_type is not InstrumentType.ORDINARY_COMMON_EQUITY for s in securities):
        reasons.add(_R.INSTRUMENT_TYPE_UNSUPPORTED)
    security_cores = {_json(_security_core(s)) for s in securities}
    if len(security_cores) != 1:
        reasons.add(_R.SECURITY_CONTINUITY_UNRESOLVED)
        if len(security_cores) > 1:
            reasons.add(_R.IDENTITY_EVIDENCE_CONFLICT)
    security = securities[0] if len(security_cores) == 1 else None
    if security is None or not _anchor(security.anchor, "security"):
        reasons.update((_R.SECURITY_IDENTIFIER_UNRESOLVED, _R.TICKER_ONLY_IDENTITY_INSUFFICIENT))
    elif security.anchor != request.security_anchor:
        reasons.add(_R.SECURITY_IDENTIFIER_UNRESOLVED)
    if security is not None:
        if security.issuer_anchor != issuer.anchor:
            reasons.add(_R.ISSUER_IDENTIFIER_MISMATCH)
        if not _covers(security.interval, start, end):
            reasons.update((_R.EFFECTIVE_INTERVAL_UNRESOLVED, _R.SECURITY_CONTINUITY_UNRESOLVED))
        common = security.common_class
        if not all((common.class_id.strip(), common.legal_designation.strip(), common.economic_designation.strip())):
            reasons.add(_R.SHARE_CLASS_UNRESOLVED)
        if common.participation is not Participation.ORDINARY_RESIDUAL_COMMON:
            reasons.add(_R.PARTICIPATION_RIGHTS_UNRESOLVED)
    inventory = snapshot.class_inventory
    if (inventory is None or inventory.coverage is not InventoryCoverage.COMPLETE_WITHIN_INTERVAL
            or not _covers(inventory.interval, start, end)):
        reasons.add(_R.COMMON_CLASS_INVENTORY_INCOMPLETE)
    if inventory is not None:
        if inventory.issuer_anchor != issuer.anchor:
            reasons.add(_R.ISSUER_IDENTIFIER_MISMATCH)
        classes = _records(inventory.classes)
        if len(classes) > 1:
            reasons.add(_R.MULTIPLE_COMMON_CLASSES_UNSUPPORTED)
        if len({c.class_id for c in classes}) != len(classes):
            reasons.add(_R.IDENTITY_EVIDENCE_CONFLICT)
        if any(c.participation is not Participation.ORDINARY_RESIDUAL_COMMON for c in classes):
            reasons.add(_R.PARTICIPATION_RIGHTS_UNRESOLVED)
        if security is not None and classes != (security.common_class,):
            reasons.add(_R.SHARE_CLASS_UNRESOLVED)

    listings = _records(snapshot.listings)
    listing_inventory = snapshot.listing_inventory
    if (listing_inventory is None or listing_inventory.coverage is not InventoryCoverage.COMPLETE_WITHIN_INTERVAL
            or not _covers(listing_inventory.interval, start, end)
            or listing_inventory.security_anchor != request.security_anchor
            or set(listing_inventory.listing_anchors) != {l.anchor for l in listings}):
        reasons.add(_R.LISTING_UNRESOLVED)
    for listing in listings:
        if not _anchor(listing.anchor, "listing") or listing.security_anchor != request.security_anchor:
            reasons.add(_R.LISTING_UNRESOLVED)
        if listing.symbol == listing.security_anchor:
            reasons.add(_R.TICKER_ONLY_IDENTITY_INSUFFICIENT)
        if listing.venue not in _SUPPORTED_VENUES or not listing.symbol.strip():
            reasons.add(_R.LISTING_UNRESOLVED)
        if listing.venue and listing.venue not in _SUPPORTED_VENUES:
            reasons.add(_R.LISTING_PROFILE_UNSUPPORTED)
        if listing.quote_currency != "USD" or listing.quote_unit is not QuoteUnit.MAJOR_CURRENCY_UNIT:
            reasons.add(_R.LISTING_CURRENCY_OR_UNIT_UNRESOLVED)
        if ((listing.quote_currency and listing.quote_currency != "USD")
                or listing.quote_unit is QuoteUnit.MINOR_CURRENCY_UNIT):
            reasons.add(_R.LISTING_PROFILE_UNSUPPORTED)
        if listing.kind is ListingKind.DEPOSITARY:
            reasons.add(_R.DEPOSITARY_RECEIPT_UNSUPPORTED)
        elif listing.kind is not ListingKind.DIRECT:
            reasons.add(_R.LISTING_UNRESOLVED)
    # Distinguish simultaneous venues from sequential migration. Neither can be
    # hidden by selecting only the request's preferred listing.
    for n, a in enumerate(listings):
        for b in listings[n + 1:]:
            if (a.anchor, a.venue) != (b.anchor, b.venue):
                overlap = max(_day(a.interval.start), _day(b.interval.start)) <= min(
                    _day(a.interval.end), _day(b.interval.end))
                reasons.add(_R.DUAL_LISTING_UNSUPPORTED if overlap else _R.LISTING_MIGRATION_UNSUPPORTED)
    ordered = sorted(listings, key=lambda l: (l.interval.start, l.interval.end, l.symbol))
    expected_continuities = []
    for a, b in zip(ordered, ordered[1:]):
        if _day(b.interval.start) <= _day(a.interval.end):
            reasons.add(_R.IDENTITY_EVIDENCE_CONFLICT)
            if a.anchor != b.anchor:
                reasons.add(_R.DUAL_LISTING_UNSUPPORTED)
        elif _day(b.interval.start) != _day(a.interval.end) + timedelta(days=1):
            reasons.add(_R.EFFECTIVE_INTERVAL_UNRESOLVED)
        if (a.anchor, a.security_anchor, a.venue) == (b.anchor, b.security_anchor, b.venue):
            expected_continuities.append(SymbolContinuity(a.anchor, a.security_anchor, a.venue,
                                                         a.symbol, b.symbol, b.interval.start))
    if _records(snapshot.symbol_continuities) != _records(expected_continuities):
        reasons.add(_R.SECURITY_CONTINUITY_UNRESOLVED)
    active = [l for l in listings if _covers(l.interval, end, end)]
    if len({(l.anchor, l.venue) for l in active}) > 1:
        reasons.add(_R.DUAL_LISTING_UNSUPPORTED)
    current = active[0] if len(active) == 1 else None
    if current is None or current.anchor != request.listing_anchor:
        reasons.add(_R.LISTING_UNRESOLVED)
        reasons.add(_R.EFFECTIVE_INTERVAL_UNRESOLVED)

    applications = _records(replace(a, version_ids=_unique(a.version_ids),
                                   observation_ids=_unique(a.observation_ids))
                            for a in snapshot.eps_applicability)
    decisions = []
    required_periods = {(p.period_start, p.period_end) for p in series.periods}
    for claim in applications:
        if ((claim.period.start, claim.period.end) not in required_periods
                or (claim.series_semantic_hash, claim.series_evidence_hash)
                != (series.semantic_hash, series.evidence_hash)):
            reasons.add(_R.EPS_CLASS_APPLICABILITY_UNRESOLVED)
    for period in series.periods:
        matches = [a for a in applications if (a.period.start, a.period.end)
                   == (period.period_start, period.period_end)]
        if len(matches) != 1:
            reasons.add(_R.EPS_CLASS_APPLICABILITY_UNRESOLVED)
            if len(matches) > 1:
                reasons.add(_R.IDENTITY_EVIDENCE_CONFLICT)
            continue
        claim = matches[0]
        if (security is None or claim.security_anchor != request.security_anchor
                or claim.class_id != security.common_class.class_id
                or set(claim.version_ids) != set(period.version_ids)
                or set(claim.observation_ids) != set(period.supporting_observation_ids)):
            reasons.add(_R.EPS_CLASS_APPLICABILITY_UNRESOLVED)
        decisions.append(EPSClassApplicabilityDecision(claim.period, claim.security_anchor, claim.class_id,
                          _unique(claim.version_ids), _unique(claim.observation_ids), ()))
    return reasons, security, current, tuple(decisions)


def qualify_security_identity(series: ResolvedAnnualDilutedEPSSeries,
                              request: SecurityIdentityRequest,
                              evidence: SyntheticIdentityEvidenceBundle) -> SecurityIdentityQualification:
    """Verify complete fictional snapshots; return no identities on any failure.

    The boundary is max(series authority, every mandatory snapshot capture).
    Dates are inclusive, date-precision assertions. No real or historical authority.
    """
    _typed(request, SecurityIdentityRequest)
    _require(request.contract_version == IDENTITY_CONTRACT_VERSION, "Unknown identity contract")
    _validate_series(series, request)
    blockers = tuple(sorted(set(series.downstream_admission_blockers), key=lambda b: b.value))
    limitations = (_R.SYNTHETIC_EVIDENCE_ONLY,)
    reasons, source_ids, inspected = set(), (), ()
    issuer_result = security_result = listing_result = None
    decisions, boundary_text = (), None
    if request.mode is IdentityMode.HISTORICAL_AS_OF:
        reasons.add(_R.HISTORICAL_IDENTITY_UNSUPPORTED)
    else:
        _typed(evidence, SyntheticIdentityEvidenceBundle)
        _require(evidence.contract_version == SYNTHETIC_EVIDENCE_VERSION, "Unknown evidence contract")
        documents = evidence.documents
        source_ids = _unique(_verify_source(d) for d in documents)
        boundary = max((_time(series.authority_as_of), *(_time(d.captured_at) for d in documents)))
        boundary_text = boundary.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if not documents:
            reasons.update((_R.SECURITY_IDENTIFIER_UNRESOLVED, _R.COMMON_CLASS_INVENTORY_INCOMPLETE,
                            _R.EPS_CLASS_APPLICABILITY_UNRESOLVED, _R.LISTING_UNRESOLVED))
        inspected = tuple(_inspect_snapshot(d.claims, series, request, boundary) for d in documents)
        for result in inspected:
            reasons.update(result[0])
        # Mandatory complete snapshots must agree; never union partial attestations.
        cores = []
        for document, (_, security, listing, applicability) in zip(documents, inspected):
            if security is not None and listing is not None:
                issuer = document.claims.issuer
                cores.append((issuer.anchor, issuer.cik, issuer.interval, _security_core(security),
                              listing, applicability, _records(document.claims.listings),
                              replace(document.claims.class_inventory,
                                  classes=_records(document.claims.class_inventory.classes))
                              if document.claims.class_inventory else None,
                              replace(document.claims.listing_inventory,
                                  listing_anchors=_unique(document.claims.listing_inventory.listing_anchors))
                              if document.claims.listing_inventory else None))
        if len({_json(c) for c in cores}) > 1:
            reasons.add(_R.IDENTITY_EVIDENCE_CONFLICT)
        if not reasons:
            first = documents[0].claims
            _, security, listing, applicability = inspected[0]
            issuer_semantic = (first.issuer.anchor, first.issuer.cik, first.issuer.interval)
            issuer_result = IssuerIdentity(*issuer_semantic[:2],
                _unique(d.claims.issuer.descriptive_name for d in documents), first.issuer.interval,
                source_ids, _hash("issuer", issuer_semantic))
            security_result = SecurityIdentity(*_security_core(security),
                _unique(i for d in documents for s in d.claims.securities for i in s.secondary_identifiers),
                source_ids, _hash("security", _security_core(security)))
            listing_result = ListingIdentity(listing.anchor, listing.security_anchor, listing.venue,
                listing.symbol, listing.quote_currency, listing.quote_unit, listing.interval,
                source_ids, _hash("listing", listing))
            decisions = tuple(EPSClassApplicabilityDecision(a.period, a.security_anchor, a.class_id,
                              a.version_ids, a.observation_ids, source_ids) for a in applicability)
    ordered_reasons = tuple(sorted(reasons, key=lambda r: r.value))
    unsupported = any(r.value.endswith("_UNSUPPORTED") for r in reasons)
    outcome = (IdentityOutcome.IDENTITY_UNSUPPORTED if unsupported else IdentityOutcome.IDENTITY_UNAVAILABLE
               ) if reasons else IdentityOutcome.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE
    semantic = (series.semantic_hash, request.mode, request.security_anchor, request.listing_anchor,
                outcome, ordered_reasons,
                issuer_result.semantic_hash if issuer_result else None,
                security_result.semantic_hash if security_result else None,
                listing_result.semantic_hash if listing_result else None,
                tuple((d.period, d.security_anchor, d.class_id) for d in decisions))
    semantic_hash = _hash("qualification-semantics", semantic)
    evidence_hash = _hash("qualification-evidence", (semantic_hash, request, series, source_ids,
                          boundary_text, decisions, ordered_reasons, blockers, limitations))
    return SecurityIdentityQualification(IDENTITY_CONTRACT_VERSION, IDENTITY_QUALIFIER_VERSION,
        Authority.SYNTHETIC_TEST_ONLY, series.semantic_hash, series.evidence_hash,
        issuer_result, security_result, listing_result, decisions, boundary_text, outcome,
        ordered_reasons, blockers, limitations, source_ids, semantic_hash, evidence_hash)
