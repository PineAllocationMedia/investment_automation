"""Strict issuer-level SEC source qualification for one annual nonpayer period.

The positive result requires exact zero agreement for both reviewed dividend-per-
share concepts. It is upstream source evidence only, never a PR4B1 root or final
economic admission.
"""
from calendar import monthrange
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
import json
import re

from .sec_archive import (ACQUISITION_CONTRACT_VERSION,
                          LIVE_ACQUISITION_CONTRACT_VERSION, ArchiveError,
                          SecArchive, digest)
from .sec_common_stock_dividends import (
    CONCEPTS, DECLARED_CONCEPT, NAMESPACE, PAID_CONCEPT,
    CommonStockDividendExtraction, _semantic_json, extract_common_stock_dividends,
)

VERIFIED_NONPAYER_CONTRACT_VERSION = "2026-09-28-sec-verified-nonpayer-source-v1"
VERIFIED_NONPAYER_RESOLVER_VERSION = "2026-09-28-exact-two-concept-zero-consensus-v1"


class NonpayerPeriodPolicy(Enum):
    FIXED_MONTH_END_365_366 = "2026-09-11-fixed-month-end-365-366-v1"


class VerifiedNonpayerStatus(Enum):
    VERIFIED_NONPAYER_SOURCE_ESTABLISHED = "VERIFIED_NONPAYER_SOURCE_ESTABLISHED"
    UNAVAILABLE = "UNAVAILABLE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"


class ConceptDecisionStatus(Enum):
    EXACT_ZERO_ESTABLISHED = "EXACT_ZERO_ESTABLISHED"
    UNAVAILABLE = "UNAVAILABLE"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNSUPPORTED_SOURCE_PROFILE = "UNSUPPORTED_SOURCE_PROFILE"


class VerifiedNonpayerReason(Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    ARCHIVE_INTEGRITY_ERROR = "ARCHIVE_INTEGRITY_ERROR"
    DECLARED_CONCEPT_UNAVAILABLE = "DECLARED_CONCEPT_UNAVAILABLE"
    PAID_CONCEPT_UNAVAILABLE = "PAID_CONCEPT_UNAVAILABLE"
    MISSING_REQUIRED_ANNUAL_PERIOD = "MISSING_REQUIRED_ANNUAL_PERIOD"
    NONZERO_DECLARED_DIVIDEND = "NONZERO_DECLARED_DIVIDEND"
    NONZERO_PAID_DIVIDEND = "NONZERO_PAID_DIVIDEND"
    INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE = "INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE"
    UNRESOLVED_VALUE_CONFLICT = "UNRESOLVED_VALUE_CONFLICT"
    UNSUPPORTED_NEGATIVE_VALUE = "UNSUPPORTED_NEGATIVE_VALUE"
    UNIT_MISMATCH = "UNIT_MISMATCH"
    CIK_MISMATCH = "CIK_MISMATCH"
    UNSUPPORTED_CALENDAR = "UNSUPPORTED_CALENDAR"
    INVALID_FILING_CHRONOLOGY = "INVALID_FILING_CHRONOLOGY"
    INSUFFICIENT_FILING_IDENTITY = "INSUFFICIENT_FILING_IDENTITY"
    UNRESOLVED_CONTEXT = "UNRESOLVED_CONTEXT"
    UNSUPPORTED_FORM = "UNSUPPORTED_FORM"
    NON_FY_PERIOD = "NON_FY_PERIOD"
    MALFORMED_SOURCE = "MALFORMED_SOURCE"
    LATER_ANNUAL_PERIOD_PRESENT = "LATER_ANNUAL_PERIOD_PRESENT"
    OFFLINE_CAPTURE_ONLY = "OFFLINE_CAPTURE_ONLY"


class VerifiedNonpayerResolutionError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason.value)


@dataclass(frozen=True, slots=True)
class VerifiedNonpayerRequest:
    contract_version: str
    receipt_id: str
    cik: str
    latest_required_fiscal_end: str
    expected_unit: str
    period_policy: NonpayerPeriodPolicy


@dataclass(frozen=True, slots=True)
class DividendConceptDecision:
    concept: str
    period_start: str
    period_end: str
    considered_observation_ids: tuple[str, ...]
    comparable_observation_ids: tuple[str, ...]
    annual_candidate_observation_ids: tuple[str, ...]
    supporting_semantic_ids: tuple[str, ...]
    distinct_values: tuple[Decimal, ...]
    conflicting_observation_ids: tuple[str, ...]
    representative_observation_id: str | None
    status: ConceptDecisionStatus
    reasons: tuple[VerifiedNonpayerReason, ...]


@dataclass(frozen=True, slots=True)
class VerifiedNonpayerSourceResult:
    contract_version: str
    resolver_version: str
    status: VerifiedNonpayerStatus
    reasons: tuple[VerifiedNonpayerReason, ...]
    request: VerifiedNonpayerRequest
    extraction: CommonStockDividendExtraction | None
    decisions: tuple[DividendConceptDecision, ...]
    receipt_id: str
    source_object_hash: str
    captured_at: str
    acquisition_contract_version: str
    namespace: str
    concepts: tuple[str, ...]
    period_start: str
    period_end: str
    unit: str
    semantic_hash: str
    evidence_hash: str
    limitations: tuple[str, ...]


LIMITATIONS = (
    "CURRENT_SNAPSHOT_ONLY",
    "NO_FINAL_ECONOMIC_ADMISSION",
    "NO_PR4B1_VERIFIED_NONPAYER_ROOT",
    "NO_REPORTING_SUBJECT_QUALIFICATION",
    "NO_SELECTED_SECURITY_CLASS_JOIN",
    "NO_SHARE_BASIS_QUALIFICATION",
    "PAYER_ROUTE_NOT_SUPPORTED",
    "UPSTREAM_SOURCE_EVIDENCE_ONLY",
)
_ANNUAL_FORMS = ("10-K", "10-K/A")
_ROW_KEYS = frozenset(("start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"))
_ACCESSION = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")


def _ordered(reasons):
    return tuple(sorted(set(reasons), key=lambda item: item.value))


def _date(value):
    if type(value) is not str:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _annual_interval(end):
    start = date(end.year if end.month == 12 else end.year - 1, end.month % 12 + 1, 1)
    return start, end


def _supported_annual(start, end):
    return (start is not None and end is not None and end.year > 1
            and end.day == monthrange(end.year, end.month)[1]
            and start == _annual_interval(end)[0]
            and (end - start).days + 1 in (365, 366))


def _apparent_annual(row):
    start, end = _date(row.start), _date(row.end)
    if start is not None and end is not None:
        return 364 <= (end - start).days + 1 <= 371
    return row.form in _ANNUAL_FORMS or row.fp == "FY" or row.form is None or row.fp is None


def _canonical_value(value):
    return Decimal(_semantic_json(value))


def _hash(value):
    def project(item):
        if isinstance(item, Enum):
            return item.value
        if type(item) in (tuple, list):
            return [project(child) for child in item]
        if type(item) is dict:
            return {key: project(child) for key, child in item.items()}
        return item
    return digest(_semantic_json(project(value)).encode("ascii"))


def _row_reasons(row, capture_date):
    reasons = set()
    if row.accession is None or _ACCESSION.fullmatch(row.accession) is None:
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if row.form is None or row.fp is None or row.filed is None:
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if (row.form is not None and re.fullmatch(r"[A-Z0-9][A-Z0-9/-]*", row.form) is None
            or row.fp not in ("FY", "Q1", "Q2", "Q3", "Q4")):
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if any(item.startswith("INVALID_") or item in ("MALFORMED_ROW", "MISSING_VALUE")
           for item in row.metadata_limitations):
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    start, end, filed = _date(row.start), _date(row.end), _date(row.filed)
    if start is None or end is None:
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if filed is None or end is None or not end <= filed <= capture_date:
        reasons.add(VerifiedNonpayerReason.INVALID_FILING_CHRONOLOGY)
    if start is not None and end is not None and start > end:
        reasons.add(VerifiedNonpayerReason.INVALID_FILING_CHRONOLOGY)
    if type(row.value) is not Decimal or not row.value.is_finite():
        reasons.add(VerifiedNonpayerReason.MALFORMED_SOURCE)
    try:
        context = json.loads(row.row_json, parse_float=Decimal)
    except (json.JSONDecodeError, TypeError):
        context = None
    if type(context) is not dict or set(context) - _ROW_KEYS:
        reasons.add(VerifiedNonpayerReason.UNRESOLVED_CONTEXT)
    return reasons


def _decision(concept, start, end, observations, capture_date, expected_unit):
    rows = tuple(row for row in observations
                 if row.concept == concept and (row.start, row.end) ==
                 (start.isoformat(), end.isoformat()))
    reasons, comparable, candidates = set(), [], []
    for row in rows:
        row_reasons = _row_reasons(row, capture_date)
        if row.unit != expected_unit:
            row_reasons.add(VerifiedNonpayerReason.UNIT_MISMATCH)
        reasons.update(row_reasons)
        if not row_reasons:
            comparable.append(row)
            if row.form in _ANNUAL_FORMS and row.fp == "FY":
                candidates.append(row)
    if not candidates:
        reasons.add(VerifiedNonpayerReason.MISSING_REQUIRED_ANNUAL_PERIOD)
        if rows and not any(row.form in _ANNUAL_FORMS for row in rows):
            reasons.add(VerifiedNonpayerReason.UNSUPPORTED_FORM)
        if rows and not any(row.fp == "FY" for row in rows):
            reasons.add(VerifiedNonpayerReason.NON_FY_PERIOD)
    values = tuple(sorted({_canonical_value(row.value) for row in comparable}))
    if len(values) > 1:
        reasons.add(VerifiedNonpayerReason.UNRESOLVED_VALUE_CONFLICT)
    if any(value < 0 for value in values):
        reasons.add(VerifiedNonpayerReason.UNSUPPORTED_NEGATIVE_VALUE)
    if any(value > 0 for value in values):
        reasons.add(VerifiedNonpayerReason.NONZERO_DECLARED_DIVIDEND if concept == DECLARED_CONCEPT
                    else VerifiedNonpayerReason.NONZERO_PAID_DIVIDEND)

    conflict_reasons = {VerifiedNonpayerReason.UNRESOLVED_VALUE_CONFLICT,
                        VerifiedNonpayerReason.UNSUPPORTED_NEGATIVE_VALUE}
    unsupported_reasons = {
        VerifiedNonpayerReason.UNIT_MISMATCH,
        VerifiedNonpayerReason.INVALID_FILING_CHRONOLOGY,
        VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY,
        VerifiedNonpayerReason.UNRESOLVED_CONTEXT,
        VerifiedNonpayerReason.MALFORMED_SOURCE,
    }
    if reasons & conflict_reasons:
        status = ConceptDecisionStatus.SOURCE_CONFLICT
    elif reasons & unsupported_reasons:
        status = ConceptDecisionStatus.UNSUPPORTED_SOURCE_PROFILE
    elif reasons:
        status = ConceptDecisionStatus.UNAVAILABLE
    else:
        status = ConceptDecisionStatus.EXACT_ZERO_ESTABLISHED
    representative = min(candidates, key=lambda row: (row.semantic_id, row.source_locator)) \
        if status is ConceptDecisionStatus.EXACT_ZERO_ESTABLISHED else None
    conflicting = tuple(sorted(row.observation_id for row in comparable)) \
        if reasons & conflict_reasons else ()
    return DividendConceptDecision(
        concept, start.isoformat(), end.isoformat(),
        tuple(sorted(row.observation_id for row in rows)),
        tuple(sorted(row.observation_id for row in comparable)),
        tuple(sorted(row.observation_id for row in candidates)),
        tuple(sorted({row.semantic_id for row in candidates})), values, conflicting,
        representative.observation_id if representative is not None else None,
        status, _ordered(reasons),
    )


def _result(request, receipt, extraction, decisions, start, end, reasons):
    reasons = set(reasons)
    conflict_reasons = {VerifiedNonpayerReason.UNRESOLVED_VALUE_CONFLICT,
                        VerifiedNonpayerReason.UNSUPPORTED_NEGATIVE_VALUE}
    unsupported_reasons = {
        VerifiedNonpayerReason.UNIT_MISMATCH,
        VerifiedNonpayerReason.CIK_MISMATCH,
        VerifiedNonpayerReason.UNSUPPORTED_CALENDAR,
        VerifiedNonpayerReason.INVALID_FILING_CHRONOLOGY,
        VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY,
        VerifiedNonpayerReason.UNRESOLVED_CONTEXT,
        VerifiedNonpayerReason.MALFORMED_SOURCE,
    }
    if reasons & conflict_reasons:
        status = VerifiedNonpayerStatus.SOURCE_CONFLICT
    elif reasons & unsupported_reasons:
        status = VerifiedNonpayerStatus.UNSUPPORTED_SOURCE_PROFILE
    elif reasons:
        status = VerifiedNonpayerStatus.UNAVAILABLE
    elif all(item.status is ConceptDecisionStatus.EXACT_ZERO_ESTABLISHED for item in decisions):
        status = VerifiedNonpayerStatus.VERIFIED_NONPAYER_SOURCE_ESTABLISHED
    else:
        status = VerifiedNonpayerStatus.UNAVAILABLE

    semantic_observations = []
    if extraction is not None:
        semantic_observations = sorted({
            (row.concept, row.unit, row.semantic_id) for row in extraction.observations
        })
    semantic = {
        "contract": VERIFIED_NONPAYER_CONTRACT_VERSION,
        "resolver": VERIFIED_NONPAYER_RESOLVER_VERSION,
        "cik": request.cik,
        "namespace": NAMESPACE,
        "concepts": CONCEPTS,
        "period": (start.isoformat(), end.isoformat()),
        "unit": request.expected_unit,
        "period_policy": request.period_policy,
        "status": status,
        "reasons": _ordered(reasons),
        "observations": semantic_observations,
    }
    evidence = {
        "semantic": semantic,
        "request": asdict(request),
        "receipt": asdict(receipt),
        "extraction": asdict(extraction) if extraction is not None else None,
        "decisions": [asdict(item) for item in decisions],
    }
    return VerifiedNonpayerSourceResult(
        VERIFIED_NONPAYER_CONTRACT_VERSION, VERIFIED_NONPAYER_RESOLVER_VERSION,
        status, _ordered(reasons), request, extraction, tuple(decisions),
        receipt.receipt_id, receipt.content_sha256, receipt.captured_at,
        receipt.acquisition_contract_version, NAMESPACE, CONCEPTS,
        start.isoformat(), end.isoformat(), request.expected_unit,
        _hash(semantic), _hash(evidence), LIMITATIONS,
    )


def resolve_sec_verified_nonpayer(archive: SecArchive,
                                  request: VerifiedNonpayerRequest) -> VerifiedNonpayerSourceResult:
    """Resolve one exact receipt without network, clock, latest selection, or writes."""
    if (type(archive) is not SecArchive or type(request) is not VerifiedNonpayerRequest
            or request.contract_version != VERIFIED_NONPAYER_CONTRACT_VERSION
            or type(request.receipt_id) is not str
            or re.fullmatch(r"[0-9a-f]{64}", request.receipt_id) is None
            or type(request.cik) is not str or re.fullmatch(r"[0-9]{10}", request.cik) is None
            or type(request.latest_required_fiscal_end) is not str
            or _date(request.latest_required_fiscal_end) is None
            or _date(request.latest_required_fiscal_end).year <= 1
            or type(request.expected_unit) is not str
            or type(request.period_policy) is not NonpayerPeriodPolicy):
        raise VerifiedNonpayerResolutionError(VerifiedNonpayerReason.INVALID_REQUEST)
    try:
        receipt = archive.read_receipt(request.receipt_id)
        raw = archive.read_object(receipt)
    except (ArchiveError, OSError):
        raise VerifiedNonpayerResolutionError(VerifiedNonpayerReason.ARCHIVE_INTEGRITY_ERROR) from None

    latest = _date(request.latest_required_fiscal_end)
    start, end = _annual_interval(latest)
    reasons = set()
    if receipt.cik != request.cik:
        reasons.add(VerifiedNonpayerReason.CIK_MISMATCH)
    if request.expected_unit != "USD/shares":
        reasons.add(VerifiedNonpayerReason.UNIT_MISMATCH)
    if not _supported_annual(start, end):
        reasons.add(VerifiedNonpayerReason.UNSUPPORTED_CALENDAR)
    if receipt.acquisition_contract_version == ACQUISITION_CONTRACT_VERSION:
        reasons.add(VerifiedNonpayerReason.OFFLINE_CAPTURE_ONLY)
    elif receipt.acquisition_contract_version != LIVE_ACQUISITION_CONTRACT_VERSION:
        reasons.add(VerifiedNonpayerReason.MALFORMED_SOURCE)

    try:
        extraction = extract_common_stock_dividends(raw, receipt)
    except (ArchiveError, ValueError, RecursionError, OverflowError, TypeError):
        extraction = None
        reasons.add(VerifiedNonpayerReason.MALFORMED_SOURCE)
        return _result(request, receipt, extraction, (), start, end, reasons)

    if "MISSING_SOURCE_CIK" in extraction.issues:
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if DECLARED_CONCEPT + "_UNAVAILABLE" in extraction.issues:
        reasons.add(VerifiedNonpayerReason.DECLARED_CONCEPT_UNAVAILABLE)
    if PAID_CONCEPT + "_UNAVAILABLE" in extraction.issues:
        reasons.add(VerifiedNonpayerReason.PAID_CONCEPT_UNAVAILABLE)

    capture_date = _date(receipt.captured_at[:10])
    if end > capture_date:
        reasons.add(VerifiedNonpayerReason.INVALID_FILING_CHRONOLOGY)
    rows = extraction.observations
    relevant_annual = [row for row in rows if row.unit == request.expected_unit
                       and _apparent_annual(row)]
    if any(_date(row.start) is None or _date(row.end) is None for row in relevant_annual):
        reasons.add(VerifiedNonpayerReason.INSUFFICIENT_FILING_IDENTITY)
    if any((_date(row.end) is not None and _date(row.end) > end)
           or (_date(row.end) is None and row.start is not None and _date(row.start) is not None
               and _date(row.start) > end) for row in relevant_annual):
        reasons.add(VerifiedNonpayerReason.LATER_ANNUAL_PERIOD_PRESENT)
    for row in relevant_annual:
        row_start, row_end = _date(row.start), _date(row.end)
        if (row_end == end and row_start is not None
                and 364 <= (row_end - row_start).days + 1 <= 371
                and not _supported_annual(row_start, row_end)):
            reasons.add(VerifiedNonpayerReason.UNSUPPORTED_CALENDAR)

    decisions = tuple(_decision(concept, start, end, rows, capture_date,
                                request.expected_unit) for concept in CONCEPTS)
    for decision in decisions:
        reasons.update(decision.reasons)

    # Shorter or overlapping positive evidence is contradiction evidence only;
    # it is never summed into an annual value. Later periods are intentionally out.
    for row in rows:
        row_start, row_end = _date(row.start), _date(row.end)
        if row.unit != request.expected_unit:
            continue
        if row_start is None or row_end is None:
            if row.value is not None and row.value != 0:
                reasons.update(_row_reasons(row, capture_date))
            continue
        if (row.start, row.end) == (start.isoformat(), end.isoformat()):
            continue
        overlaps = row_start <= end and row_end >= start
        if not overlaps:
            continue
        row_reasons = _row_reasons(row, capture_date)
        reasons.update(row_reasons)
        if row.value is not None and row.value > 0:
            reasons.add(VerifiedNonpayerReason.INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE)
        if row.value is not None and row.value < 0:
            reasons.add(VerifiedNonpayerReason.UNSUPPORTED_NEGATIVE_VALUE)

    return _result(request, receipt, extraction, decisions, start, end, reasons)
