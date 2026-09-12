"""Single-receipt issuer evidence by exact agreement; never model admission.

Only archive reads are permitted. Capture time is receipt-derived, and historical
resolution is deliberately unavailable. Unknown contexts are not comparable.
"""
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
import json
import re

from .sec_archive import (ACQUISITION_CONTRACT_VERSION, LIVE_ACQUISITION_CONTRACT_VERSION,
                          ArchiveError, SecArchive, digest)
from .sec_diluted_eps import (CONCEPT, NAMESPACE, Extraction,
                              _semantic_json, extract_diluted_eps)

SERIES_CONTRACT_VERSION = "2026-09-11-sec-annual-diluted-eps-series-v1"
SERIES_RESOLVER_VERSION = "2026-09-11-sec-current-reported-consensus-v1"


class ResolutionMode(Enum):
    CURRENT_AS_REPORTED = "CURRENT_AS_REPORTED"
    HISTORICAL_AS_OF = "HISTORICAL_AS_OF"


class PeriodPolicy(Enum):
    FIXED_MONTH_END_365_366 = "2026-09-11-fixed-month-end-365-366-v1"


class CaptureAuthority(Enum):
    LIVE_LOCAL_CAPTURE = "LIVE_LOCAL_CAPTURE"
    OFFLINE_SUPPLIED_CAPTURE = "OFFLINE_SUPPLIED_CAPTURE"


class ResolutionStatus(Enum):
    RESOLVED_ISSUER_EVIDENCE = "RESOLVED_ISSUER_EVIDENCE"
    UNAVAILABLE = "UNAVAILABLE"


class SelectionReason(Enum):
    EXACT_REPORTED_VALUE_AGREEMENT = "EXACT_REPORTED_VALUE_AGREEMENT"


class ResolutionReason(Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"
    SOURCE_STRUCTURE_ERROR = "SOURCE_STRUCTURE_ERROR"
    CIK_MISMATCH = "CIK_MISMATCH"
    FEWER_THAN_FIVE_ANNUAL_PERIODS = "FEWER_THAN_FIVE_ANNUAL_PERIODS"
    MISSING_REQUIRED_LATEST_PERIOD = "MISSING_REQUIRED_LATEST_PERIOD"
    LATER_ANNUAL_PERIOD_PRESENT = "LATER_ANNUAL_PERIOD_PRESENT"
    MISSING_ANNUAL_PERIOD = "MISSING_ANNUAL_PERIOD"
    NONCONSECUTIVE_PERIODS = "NONCONSECUTIVE_PERIODS"
    UNSUPPORTED_CALENDAR = "UNSUPPORTED_CALENDAR"
    CALENDAR_TRANSITION_UNRESOLVED = "CALENDAR_TRANSITION_UNRESOLVED"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    ACCOUNTING_BASIS_MISMATCH = "ACCOUNTING_BASIS_MISMATCH"
    DILUTED_EPS_UNAVAILABLE = "DILUTED_EPS_UNAVAILABLE"
    UNRESOLVED_VALUE_CONFLICT = "UNRESOLVED_VALUE_CONFLICT"
    UNRESOLVED_CONTEXT = "UNRESOLVED_CONTEXT"
    MISSING_ACCESSION = "MISSING_ACCESSION"
    INVALID_ACCESSION = "INVALID_ACCESSION"
    INSUFFICIENT_FILING_IDENTITY = "INSUFFICIENT_FILING_IDENTITY"
    SAME_ACCESSION_VALUE_CONFLICT = "SAME_ACCESSION_VALUE_CONFLICT"
    HISTORICAL_CUTOFF_UNSUPPORTED = "HISTORICAL_CUTOFF_UNSUPPORTED"
    INVALID_VALUE = "INVALID_VALUE"
    INVALID_FILING_CHRONOLOGY = "INVALID_FILING_CHRONOLOGY"
    NOT_ANNUAL_FORM_CANDIDATE = "NOT_ANNUAL_FORM_CANDIDATE"
    OUTSIDE_REQUIRED_INTERVALS = "OUTSIDE_REQUIRED_INTERVALS"
    NON_ANNUAL_PERIOD = "NON_ANNUAL_PERIOD"


class AdmissionBlocker(Enum):
    OFFLINE_CAPTURE_NOT_AUTHENTICATED = "OFFLINE_CAPTURE_NOT_AUTHENTICATED"
    PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED = "PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED"
    SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED = "SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED"
    SPLIT_BASIS_NOT_ESTABLISHED = "SPLIT_BASIS_NOT_ESTABLISHED"
    ECONOMIC_COMPARABILITY_NOT_ESTABLISHED = "ECONOMIC_COMPARABILITY_NOT_ESTABLISHED"
    SNAPSHOT_COVERAGE_ONLY = "SNAPSHOT_COVERAGE_ONLY"
    UPSTREAM_EVIDENCE_ONLY = "UPSTREAM_EVIDENCE_ONLY"


class SeriesResolutionError(ValueError):
    """Invalid request or corrupt source; fixed safe category, never source text."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class SeriesResolutionRequest:
    contract_version: str
    mode: ResolutionMode
    receipt_id: str
    cik: str
    latest_required_fiscal_end: str
    expected_unit: str
    period_policy: PeriodPolicy


@dataclass(frozen=True, slots=True)
class CaptureAuthorityAssessment:
    receipt_id: str
    object_hash: str
    acquisition_contract: str
    captured_at: str
    authority: CaptureAuthority
    limitations: tuple[AdmissionBlocker, ...]


@dataclass(frozen=True, slots=True)
class ObservationExclusion:
    observation_id: str
    reasons: tuple[ResolutionReason, ...]


@dataclass(frozen=True, slots=True)
class FilingVersionReference:
    semantic_id: str
    accession: str
    form: str
    filed: str
    reported_fy: int | None
    reported_fp: str | None
    frame: str | None
    observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResolvedAnnualDilutedEPS:
    period_start: str
    period_end: str
    inclusive_days: int
    value: Decimal
    representative_observation_id: str
    supporting_observation_ids: tuple[str, ...]
    version_ids: tuple[str, ...]
    filing_versions: tuple[FilingVersionReference, ...]
    selection_reason: SelectionReason
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PeriodResolutionDecision:
    period_start: str
    period_end: str
    considered_observation_ids: tuple[str, ...]
    admissible_observation_ids: tuple[str, ...]
    excluded_observations: tuple[ObservationExclusion, ...]
    distinct_values: tuple[Decimal, ...]
    supporting_observation_ids: tuple[str, ...]
    conflicting_observation_ids: tuple[str, ...]
    status: ResolutionStatus
    reasons: tuple[ResolutionReason, ...]


@dataclass(frozen=True, slots=True)
class ResolvedAnnualDilutedEPSSeries:
    contract_version: str
    resolver_version: str
    cik: str
    namespace: str
    concept: str
    unit: str
    accounting_basis: str
    mode: ResolutionMode
    authority_as_of: str
    capture_authority: CaptureAuthorityAssessment
    latest_required_fiscal_end: str
    period_policy: PeriodPolicy
    periods: tuple[ResolvedAnnualDilutedEPS, ...]
    receipt_ids: tuple[str, ...]
    object_hashes: tuple[str, ...]
    accessions: tuple[str, ...]
    status: ResolutionStatus
    downstream_admission_blockers: tuple[AdmissionBlocker, ...]
    semantic_hash: str
    evidence_hash: str


@dataclass(frozen=True, slots=True)
class SeriesResolutionResult:
    status: ResolutionStatus
    reasons: tuple[ResolutionReason, ...]
    series: ResolvedAnnualDilutedEPSSeries | None
    extraction: Extraction | None
    period_decisions: tuple[PeriodResolutionDecision, ...]
    source_authority: CaptureAuthorityAssessment | None
    observation_exclusions: tuple[ObservationExclusion, ...]


_ANNUAL_FORMS = ("10-K", "10-K/A")
_ROW_KEYS = frozenset(("start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"))
_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")


def _ordered(values):
    return tuple(sorted(set(values), key=lambda value: value.value))


def _date(value):
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _annual_interval(end):
    # Month-end end anchors twelve calendar months, including February years.
    start = date(end.year if end.month == 12 else end.year - 1, end.month % 12 + 1, 1)
    return start, end


def _supported(start, end):
    return (start is not None and end is not None and end.year > 1
            and end.day == monthrange(end.year, end.month)[1]
            and start == _annual_interval(end)[0]
            and (end - start).days + 1 in (365, 366))


def _apparent_annual(row):
    """Broad anti-selection envelope, deliberately BEFORE admissibility filters.

    Annual forms can contain quarter rows. Their later dates still prevent an
    older window; only exact annual intervals can supply resolved values. A
    missing form/fp cannot be used to hide a newer period. Full/week-year durations
    in other forms also participate. Unlocatable apparent rows fail closed.
    """
    start, end = _date(row.start), _date(row.end)
    return (row.form in _ANNUAL_FORMS or row.fp == "FY" or row.form is None or row.fp is None
            or (start is not None and end is not None and 364 <= (end - start).days + 1 <= 371))


def _hash(value):
    # Reuse PR4C1's exact Decimal encoder, never binary64 or Decimal.normalize().
    def project(item):
        if isinstance(item, Enum):
            return item.value
        if type(item) in (tuple, list):
            return [project(child) for child in item]
        if type(item) is dict:
            return {key: project(child) for key, child in item.items()}
        return item
    return digest(_semantic_json(project(value)).encode("ascii"))


def _canonical_value(value):
    return Decimal(_semantic_json(value))


def _row_reasons(row, capture_date):
    reasons = set()
    if row.accn is None:
        reasons.add(ResolutionReason.MISSING_ACCESSION)
    elif _ACCESSION.fullmatch(row.accn) is None:
        reasons.add(ResolutionReason.INVALID_ACCESSION)
    if row.form is None or row.fp is None or row.filed is None:
        reasons.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    if (row.form is not None and re.fullmatch(r"[A-Z0-9][A-Z0-9/-]*", row.form) is None
            or row.fp not in ("FY", "Q1", "Q2", "Q3", "Q4")):
        reasons.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    # fy and frame do not select periods. Missing fy is informational; malformed
    # supplied metadata cannot masquerade as a missing optional value.
    if any(item.startswith("INVALID_") for item in row.metadata_limitations):
        reasons.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    filed, end = _date(row.filed), _date(row.end)
    if filed is None or end is None or not end <= filed <= capture_date:
        reasons.add(ResolutionReason.INVALID_FILING_CHRONOLOGY)
    if type(row.value) is not Decimal or not row.value.is_finite():
        reasons.add(ResolutionReason.INVALID_VALUE)
    context = json.loads(row.row_json, parse_float=Decimal)
    if type(context) is not dict or set(context) - _ROW_KEYS:
        reasons.add(ResolutionReason.UNRESOLVED_CONTEXT)
    return reasons


def _resolve_period(start, end, observations, capture_date):
    rows = tuple(row for row in observations if (row.start, row.end) == (start.isoformat(), end.isoformat()))
    blockers, exclusions, comparable, candidates = set(), [], [], []
    for row in rows:
        reasons = _row_reasons(row, capture_date)
        if row.unit != "USD/shares":
            reasons.add(ResolutionReason.UNIT_MISMATCH)
        blockers.update(reasons)
        annual = row.form in _ANNUAL_FORMS and row.fp == "FY"
        if not reasons:
            comparable.append(row)
            if annual:
                candidates.append(row)
        if not annual:
            reasons.add(ResolutionReason.NOT_ANNUAL_FORM_CANDIDATE)
        if reasons:
            exclusions.append(ObservationExclusion(row.observation_id, _ordered(reasons)))
    if not candidates:
        blockers.add(ResolutionReason.MISSING_ANNUAL_PERIOD)
    # Only known comparable contexts contribute values or value-conflict labels.
    values = tuple(sorted({_canonical_value(row.value) for row in comparable}))
    if len(values) > 1:
        blockers.add(ResolutionReason.UNRESOLVED_VALUE_CONFLICT)
    for accession in sorted({row.accn for row in comparable}):
        same = [row for row in comparable if row.accn == accession]
        if len({row.value for row in same}) > 1:
            blockers.add(ResolutionReason.SAME_ACCESSION_VALUE_CONFLICT)
        if (len({(row.form, row.filed, row.fp) for row in same}) > 1
                or len({row.fy for row in same if row.fy is not None}) > 1):
            blockers.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    supporting = tuple(sorted(row.observation_id for row in candidates)) if len(values) == 1 else ()
    decision = PeriodResolutionDecision(start.isoformat(), end.isoformat(),
        tuple(sorted(row.observation_id for row in rows)),
        tuple(sorted(row.observation_id for row in candidates)),
        tuple(sorted(exclusions, key=lambda item: item.observation_id)), values, supporting,
        tuple(sorted(row.observation_id for row in comparable)) if len(values) > 1 else (),
        ResolutionStatus.UNAVAILABLE if blockers else ResolutionStatus.RESOLVED_ISSUER_EVIDENCE,
        _ordered(blockers))
    if blockers:
        return decision, None
    versions = []
    for semantic_id in sorted({row.semantic_id for row in comparable}):
        occurrences = [row for row in comparable if row.semantic_id == semantic_id]
        row = occurrences[0]  # Identical complete semantic rows; no vintage rank.
        versions.append(FilingVersionReference(semantic_id, row.accn, row.form, row.filed,
            row.fy, row.fp, row.frame, tuple(sorted(item.observation_id for item in occurrences))))
    # Semantic ID chooses a citation among agreeing candidates, never a winner.
    representative = min(candidates, key=lambda row: (row.semantic_id, row.source_locator))
    resolved = ResolvedAnnualDilutedEPS(start.isoformat(), end.isoformat(), (end-start).days + 1,
        values[0], representative.observation_id, supporting,
        tuple(version.semantic_id for version in versions), tuple(versions),
        SelectionReason.EXACT_REPORTED_VALUE_AGREEMENT,
        tuple(sorted({item for row in comparable for item in row.metadata_limitations})))
    return decision, resolved


def resolve_annual_diluted_eps(archive: SecArchive, request: SeriesResolutionRequest) -> SeriesResolutionResult:
    """Verify one stored receipt and return evidence or explicit unavailability.

    Malformed requests and corrupt archives raise safe SeriesResolutionError.
    Historical mode returns unsupported without reading any archive bytes.
    No caller observations, as_of, policy callbacks, or authority overrides.
    """
    if (type(archive) is not SecArchive or type(request) is not SeriesResolutionRequest
            or type(request.contract_version) is not str or request.contract_version != SERIES_CONTRACT_VERSION
            or type(request.mode) is not ResolutionMode or type(request.period_policy) is not PeriodPolicy
            or type(request.receipt_id) is not str or re.fullmatch(r"[0-9a-f]{64}", request.receipt_id) is None
            or type(request.cik) is not str or re.fullmatch(r"[0-9]{10}", request.cik) is None
            or type(request.expected_unit) is not str or _date(request.latest_required_fiscal_end) is None):
        raise SeriesResolutionError(ResolutionReason.INVALID_REQUEST)
    if request.mode is ResolutionMode.HISTORICAL_AS_OF:
        return SeriesResolutionResult(ResolutionStatus.UNAVAILABLE,
            (ResolutionReason.HISTORICAL_CUTOFF_UNSUPPORTED,), None, None, (), None, ())
    try:
        receipt = archive.read_receipt(request.receipt_id)
        raw = archive.read_object(receipt)
    except (ArchiveError, OSError):
        raise SeriesResolutionError(ResolutionReason.ARCHIVE_INTEGRITY_ERROR) from None
    if receipt.cik != request.cik:
        raise SeriesResolutionError(ResolutionReason.CIK_MISMATCH)
    try:
        extraction = extract_diluted_eps(raw, receipt)
    except (ArchiveError, ValueError, RecursionError, OverflowError, TypeError):
        raise SeriesResolutionError(ResolutionReason.SOURCE_STRUCTURE_ERROR) from None
    authority_class = {
        LIVE_ACQUISITION_CONTRACT_VERSION: CaptureAuthority.LIVE_LOCAL_CAPTURE,
        ACQUISITION_CONTRACT_VERSION: CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE,
    }[receipt.acquisition_contract_version]  # Archive reader validates closed allowlist.
    limitations = _ordered(item for item in AdmissionBlocker if
        item is not AdmissionBlocker.OFFLINE_CAPTURE_NOT_AUTHENTICATED
        or authority_class is CaptureAuthority.OFFLINE_SUPPLIED_CAPTURE)
    authority = CaptureAuthorityAssessment(receipt.receipt_id, receipt.content_sha256,
        receipt.acquisition_contract_version, receipt.captured_at, authority_class, limitations)
    reasons, decisions, resolved = set(), [], []
    rows = extraction.observations
    latest = _date(request.latest_required_fiscal_end)
    capture_date = _date(receipt.captured_at[:10])
    if request.expected_unit != "USD/shares":
        reasons.add(ResolutionReason.UNIT_MISMATCH)
    if not rows:
        reasons.add(ResolutionReason.DILUTED_EPS_UNAVAILABLE)
    if "MISSING_SOURCE_CIK" in extraction.issues:
        reasons.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    if any((row.namespace, row.concept, row.candidate_accounting_basis) !=
           (NAMESPACE, CONCEPT, "US_GAAP") for row in rows):
        reasons.add(ResolutionReason.ACCOUNTING_BASIS_MISMATCH)
    scoped = [row for row in rows if row.unit == "USD/shares"]
    apparent = [row for row in scoped if _apparent_annual(row)]
    ends = [_date(row.end) for row in apparent]
    if any(_date(row.start) is None or _date(row.end) is None for row in apparent):
        reasons.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
    known_ends = [end for end in ends if end is not None]
    if known_ends and max(known_ends) > latest:
        reasons.add(ResolutionReason.LATER_ANNUAL_PERIOD_PRESENT)
    if latest not in known_ends:
        reasons.add(ResolutionReason.MISSING_REQUIRED_LATEST_PERIOD)
    if latest > capture_date:
        reasons.add(ResolutionReason.INVALID_FILING_CHRONOLOGY)
    supported_periods = {(row.start, row.end) for row in scoped
                         if _supported(_date(row.start), _date(row.end))
                         and row.form in _ANNUAL_FORMS and row.fp == "FY"}
    if len(supported_periods) < 5:
        reasons.add(ResolutionReason.FEWER_THAN_FIVE_ANNUAL_PERIODS)
    if latest.year < 6 or latest.day != monthrange(latest.year, latest.month)[1]:
        reasons.add(ResolutionReason.UNSUPPORTED_CALENDAR)
    else:
        first_start = _annual_interval(date(latest.year - 4, latest.month,
                                            monthrange(latest.year - 4, latest.month)[1]))[0]
        for row in apparent:
            row_start, row_end = _date(row.start), _date(row.end)
            if (row_start is not None and row_end is not None and row_end >= first_start
                    and row_start <= latest and 364 <= (row_end - row_start).days + 1 <= 371
                    and (not _supported(row_start, row_end) or row_end.month != latest.month)):
                reasons.update((ResolutionReason.UNSUPPORTED_CALENDAR,
                                ResolutionReason.CALENDAR_TRANSITION_UNRESOLVED))
        for year in range(latest.year - 4, latest.year + 1):
            end = date(year, latest.month, monthrange(year, latest.month)[1])
            start, end = _annual_interval(end)
            decision, annual = _resolve_period(start, end, rows, capture_date)
            decisions.append(decision)
            reasons.update(decision.reasons)
            if annual is not None:
                resolved.append(annual)
            if ResolutionReason.MISSING_ANNUAL_PERIOD in decision.reasons:
                reasons.add(ResolutionReason.NONCONSECUTIVE_PERIODS)
                if end == latest:
                    reasons.add(ResolutionReason.MISSING_REQUIRED_LATEST_PERIOD)
                # Off-calendar/stub evidence in a missing interval is visible;
                # it cannot be substituted or annualized into the required year.
                alternatives = [row for row in apparent if _date(row.end) is not None
                                and start <= _date(row.end) <= end]
                if alternatives and not decision.considered_observation_ids:
                    reasons.add(ResolutionReason.UNSUPPORTED_CALENDAR)
                    reasons.add(ResolutionReason.CALENDAR_TRANSITION_UNRESOLVED)
        if any(_date(b.period_start) != _date(a.period_end) + timedelta(days=1)
               for a, b in zip(resolved, resolved[1:])):
            reasons.add(ResolutionReason.NONCONSECUTIVE_PERIODS)
    exclusions = [item for decision in decisions for item in decision.excluded_observations]
    considered = {identifier for decision in decisions for identifier in decision.considered_observation_ids}
    for row in rows:
        if row.observation_id in considered:
            continue
        excluded = {ResolutionReason.OUTSIDE_REQUIRED_INTERVALS}
        start, end = _date(row.start), _date(row.end)
        if row.unit != "USD/shares":
            excluded.add(ResolutionReason.UNIT_MISMATCH)
        if start is None or end is None:
            excluded.add(ResolutionReason.INSUFFICIENT_FILING_IDENTITY)
        elif not _supported(start, end):
            excluded.add(ResolutionReason.NON_ANNUAL_PERIOD)
        exclusions.append(ObservationExclusion(row.observation_id, _ordered(excluded)))
    exclusions = tuple(sorted(exclusions, key=lambda item: item.observation_id))
    if reasons:
        return SeriesResolutionResult(ResolutionStatus.UNAVAILABLE, _ordered(reasons), None,
                                      extraction, tuple(decisions), authority, exclusions)
    periods = tuple(resolved)
    assert len(periods) == 5
    semantic = dict(contract=SERIES_CONTRACT_VERSION, resolver=SERIES_RESOLVER_VERSION,
        cik=request.cik, namespace=NAMESPACE, concept=CONCEPT, unit="USD/shares", accounting_basis="US_GAAP",
        mode=request.mode, period_policy=request.period_policy,
        periods=[(item.period_start, item.period_end, item.value) for item in periods])
    evidence = dict(semantic=semantic, request=asdict(request), authority=asdict(authority),
                    extraction=asdict(extraction), decisions=[asdict(item) for item in decisions],
                    periods=[asdict(item) for item in periods], exclusions=[asdict(item) for item in exclusions])
    series = ResolvedAnnualDilutedEPSSeries(SERIES_CONTRACT_VERSION, SERIES_RESOLVER_VERSION,
        request.cik, NAMESPACE, CONCEPT, "USD/shares", "US_GAAP", request.mode, receipt.captured_at,
        authority, request.latest_required_fiscal_end, request.period_policy, periods,
        (receipt.receipt_id,), (receipt.content_sha256,),
        tuple(sorted({version.accession for item in periods for version in item.filing_versions})),
        ResolutionStatus.RESOLVED_ISSUER_EVIDENCE, limitations, _hash(semantic), _hash(evidence))
    return SeriesResolutionResult(series.status, (), series, extraction, tuple(decisions), authority, exclusions)
