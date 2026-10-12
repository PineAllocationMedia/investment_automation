"""Capture-bound research observations; no native qualification or admission.

Reuse assessment: REUSE SecArchive/extraction and exact numeric serialization;
BUILD only independent selection/adjudication. Standard library, no new costs or
components. Memory is proportional to the two-concept extraction inventory;
Chromebook runtime/resource compatibility is not established by Mac validation.
"""
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
import re
from typing import ClassVar

from .sec_archive import ArchiveError, SecArchive, LIVE_ACQUISITION_CONTRACT_VERSION, endpoint_for
from .sec_revenue_operating_income import (
    extract_revenue_operating_income, _identity, CONCEPTS, EXTRACTION_VERSION,
)

CONTRACT_VERSION = '2026-10-11-current-annual-reported-fact-research-candidate-v1'
SELECTION_VERSION = '2026-10-11-apparent-endpoint-exact-calendar-consensus-v1'
IDENTITY_VERSION = '2026-10-11-research-candidate-identities-v1'
EVIDENCE_KIND = 'CURRENT_ANNUAL_REPORTED_REVENUE_OPERATING_INCOME_RESEARCH_CANDIDATE'
AUTHORITY = 'CURRENT_CAPTURE_RESEARCH_CANDIDATE_ONLY'
LIMITATIONS = (
    'LATEST_OBSERVED_SUPPORTED_ANNUAL_WITHIN_ONE_CAPTURE_ONLY',
    'NO_COMPLETE_ISSUER_COVERAGE_OR_ABSOLUTELY_NEWEST_PERIOD_CLAIM',
    'SOURCE_PRESENTED_REVENUE_NOT_UNIVERSAL_TOTAL_REVENUE',
    'NO_SECURITY_CLASS_OR_LEGAL_ECONOMIC_CONTINUITY',
    'NO_CORPORATE_ACTION_SHARE_BASIS_OR_REPORTING_SUBJECT_CONTINUITY',
    'NO_HISTORICAL_COMPARABILITY_GROWTH_OR_MARGIN_TREND',
    'NO_NORMALIZATION_QUALITY_DURABILITY_OR_CONFIDENCE_CONCLUSION',
    'NO_ORDINARY_COMPOUNDER_OR_NATIVE_QUALITY_EXPECTED_RETURN_ADMISSION',
    'NO_PIT_HISTORICAL_AS_OF_PUBLICATION_TIME_OR_MARKET_QUOTE_AUTHORITY',
    'NO_RATIO_SCORE_RANKING_RECOMMENDATION_PORTFOLIO_EXECUTION_OR_PRODUCTION',
    'UNAVAILABLE_IS_NOT_A_NEGATIVE_ISSUER_JUDGMENT',
    'LIVE_PROVENANCE_NOT_CRYPTOGRAPHIC_REMOTE_SEC_ATTESTATION',
)


class ResearchCandidateError(ArchiveError):
    """Public input or integrity error, never economic unavailability."""


class ResearchCandidateStatus(str, Enum):
    CANDIDATE_COHERENT = 'CANDIDATE_COHERENT'
    EVIDENCE_UNAVAILABLE = 'EVIDENCE_UNAVAILABLE'
    EVIDENCE_UNSUPPORTED = 'EVIDENCE_UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class ResearchCandidateReason(str, Enum):
    NO_APPARENT_ANNUAL_PERIOD = 'NO_APPARENT_ANNUAL_PERIOD'
    REVENUE_UNAVAILABLE = 'REVENUE_UNAVAILABLE'
    OPERATING_INCOME_UNAVAILABLE = 'OPERATING_INCOME_UNAVAILABLE'
    FINITE_VALUE_UNAVAILABLE = 'FINITE_VALUE_UNAVAILABLE'
    NO_COMMON_ANNUAL_ACCESSION = 'NO_COMMON_ANNUAL_ACCESSION'
    ANNUAL_ENDPOINT_UNLOCATABLE = 'ANNUAL_ENDPOINT_UNLOCATABLE'
    ANNUAL_INTERVAL_UNSUPPORTED = 'ANNUAL_INTERVAL_UNSUPPORTED'
    ANNUAL_INTERVAL_AMBIGUOUS = 'ANNUAL_INTERVAL_AMBIGUOUS'
    UNSUPPORTED_FILING_CONTEXT = 'UNSUPPORTED_FILING_CONTEXT'
    UNSUPPORTED_UNIT_OR_ROW_CONTEXT = 'UNSUPPORTED_UNIT_OR_ROW_CONTEXT'
    POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED = 'POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED'
    INVALID_FILING_CHRONOLOGY = 'INVALID_FILING_CHRONOLOGY'
    COMMON_FILING_METADATA_CONFLICT = 'COMMON_FILING_METADATA_CONFLICT'
    COMPETING_REVENUE_VALUES = 'COMPETING_REVENUE_VALUES'
    COMPETING_OPERATING_INCOME_VALUES = 'COMPETING_OPERATING_INCOME_VALUES'


R = ResearchCandidateReason
S = ResearchCandidateStatus
_UNAVAILABLE = frozenset((R.NO_APPARENT_ANNUAL_PERIOD, R.REVENUE_UNAVAILABLE,
    R.OPERATING_INCOME_UNAVAILABLE, R.FINITE_VALUE_UNAVAILABLE, R.NO_COMMON_ANNUAL_ACCESSION))
_CONFLICT = frozenset((R.INVALID_FILING_CHRONOLOGY, R.COMMON_FILING_METADATA_CONFLICT,
    R.COMPETING_REVENUE_VALUES, R.COMPETING_OPERATING_INCOME_VALUES))
_ACCESSION = re.compile(r'[0-9]{10}-[0-9]{2}-[0-9]{6}')
_ROW_KEYS = frozenset(('val', 'start', 'end', 'fy', 'fp', 'form', 'filed', 'accn', 'frame'))


def _status(reasons):
    if set(reasons) & _CONFLICT:
        return S.SOURCE_CONFLICT
    if set(reasons) - _UNAVAILABLE:
        return S.EVIDENCE_UNSUPPORTED
    return S.EVIDENCE_UNAVAILABLE if reasons else S.CANDIDATE_COHERENT


def _date(value):
    if type(value) is not str or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class ResearchObservationReference:
    observation_id: str
    semantic_id: str
    source_locator: str
    semantic_locator: str
    concept: str
    unit: str
    value: Decimal | None
    start: str | None
    end: str | None
    fy: int | None
    fp: str | None
    form: str | None
    filed: str | None
    accession: str | None
    frame: str | None
    metadata_limitations: tuple[str, ...]
    disposition: str
    exclusion_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResearchSupportingFiling:
    accession: str
    forms: tuple[str, ...]
    filed_dates: tuple[str, ...]
    fiscal_years: tuple[int, ...]
    revenue_observation_ids: tuple[str, ...]
    operating_income_observation_ids: tuple[str, ...]


def _jsonable(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) in (tuple, list):
        return [_jsonable(v) for v in value]
    if type(value) is dict:
        return {k: _jsonable(v) for k, v in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class CurrentAnnualReportedFactResearchCandidate:
    status: ResearchCandidateStatus
    reasons: tuple[ResearchCandidateReason, ...]
    source_cik: str
    period_start: str | None
    period_end: str | None
    revenue: Decimal | None
    operating_income: Decimal | None
    capture_receipt_id: str
    source_object_hash: str
    captured_at: str
    source_locator: str
    acquisition_contract_version: str
    observations: tuple[ResearchObservationReference, ...]
    supporting_filings: tuple[ResearchSupportingFiling, ...]
    extraction_inventory_id: str
    extraction_issues: tuple[str, ...]
    conflict_values: tuple[tuple[Decimal, ...], ...]
    contract_version: ClassVar[str] = CONTRACT_VERSION
    selection_version: ClassVar[str] = SELECTION_VERSION
    evidence_kind: ClassVar[str] = EVIDENCE_KIND
    authority: ClassVar[str] = AUTHORITY
    source_kind: ClassVar[str] = 'SEC_COMPANYFACTS_SNAPSHOT'
    namespace: ClassVar[str] = 'us-gaap'
    concepts: ClassVar[tuple[str, ...]] = CONCEPTS
    unit: ClassVar[str] = 'USD'
    accounting_basis: ClassVar[str] = 'US_GAAP'
    temporal_mode: ClassVar[str] = 'CURRENT_CAPTURE_BOUND_ONLY'
    limitations: ClassVar[tuple[str, ...]] = LIMITATIONS

    def __post_init__(self):
        if (type(self.status) is not S or type(self.reasons) is not tuple
                or any(type(r) is not R for r in self.reasons)
                or self.reasons != tuple(sorted(set(self.reasons), key=lambda r: r.value))
                or self.status is not _status(self.reasons)):
            raise ResearchCandidateError('Canonical research state/reasons required')
        if (type(self.observations) is not tuple
                or any(type(o) is not ResearchObservationReference for o in self.observations)
                or type(self.supporting_filings) is not tuple
                or any(type(f) is not ResearchSupportingFiling for f in self.supporting_filings)
                or type(self.extraction_issues) is not tuple
                or type(self.conflict_values) is not tuple
                or any(type(v) is not tuple for v in self.conflict_values)):
            raise ResearchCandidateError('Immutable typed research inventory required')
        for observation in self.observations:
            if (type(observation.metadata_limitations) is not tuple
                    or type(observation.exclusion_reasons) is not tuple
                    or observation.disposition not in
                    ('SELECTED', 'NONSELECTED', 'ORPHAN', 'UNSUPPORTED', 'COMPETING')):
                raise ResearchCandidateError('Immutable observation disposition required')
        for filing in self.supporting_filings:
            if any(type(value) is not tuple for value in (
                    filing.forms, filing.filed_dates, filing.fiscal_years,
                    filing.revenue_observation_ids, filing.operating_income_observation_ids)):
                raise ResearchCandidateError('Immutable supporting filing required')
        coherent = self.status is S.CANDIDATE_COHERENT
        if coherent:
            if (any(type(v) is not Decimal or not v.is_finite()
                    for v in (self.revenue, self.operating_income))
                    or not self.supporting_filings or not self.period_start or not self.period_end):
                raise ResearchCandidateError('Complete coherent research pair required')
        elif self.revenue is not None or self.operating_income is not None:
            raise ResearchCandidateError('Failed candidate cannot publish selected values')

    @property
    def semantic_id(self):
        return _identity(IDENTITY_VERSION + ':semantic', _jsonable({
            'contract': CONTRACT_VERSION, 'selection': SELECTION_VERSION,
            'kind': EVIDENCE_KIND, 'authority': AUTHORITY, 'limitations': LIMITATIONS,
            'status': self.status, 'reasons': self.reasons, 'cik': self.source_cik,
            'namespace': self.namespace, 'concepts': CONCEPTS, 'unit': self.unit,
            'basis': self.accounting_basis, 'temporal': self.temporal_mode,
            'start': self.period_start, 'end': self.period_end,
            'revenue': self.revenue, 'income': self.operating_income,
            'conflict_values': self.conflict_values,
        }))

    @property
    def evidence_id(self):
        return _identity(IDENTITY_VERSION + ':evidence', _jsonable({
            'semantic_id': self.semantic_id, 'result': asdict(self),
            'extraction_version': EXTRACTION_VERSION,
        }))


def evaluate_sec_current_annual_reported_fact_research_candidate(archive, receipt_id):
    """Evaluate only one exact immutable LIVE capture; no native model path."""
    if (type(archive) is not SecArchive or type(receipt_id) is not str
            or re.fullmatch(r'[0-9a-f]{64}', receipt_id) is None):
        raise ResearchCandidateError('Exact archive and lowercase receipt ID required')
    receipt = archive.read_receipt(receipt_id)
    raw = archive.read_object(receipt)
    if (receipt.receipt_id != receipt_id
            or receipt.acquisition_contract_version != LIVE_ACQUISITION_CONTRACT_VERSION
            or receipt.endpoint != endpoint_for(receipt.cik)
            or receipt.source_locator != receipt.endpoint):
        raise ResearchCandidateError('Canonical LIVE Companyfacts capture required')
    extraction = extract_revenue_operating_income(raw, receipt)
    if extraction.source_cik != receipt.cik:
        raise ResearchCandidateError('Receipt and extracted source CIK mismatch')
    rows = extraction.observations
    reasons = set()
    notes = {o.observation_id: set() for o in rows}
    dispositions = {o.observation_id: 'NONSELECTED' for o in rows}
    dates = {o.observation_id: (_date(o.start), _date(o.end)) for o in rows}
    annual = []
    for o in rows:
        start, end = dates[o.observation_id]
        duration = (end - start).days + 1 if start and end else None
        apparent = (o.fp == 'FY' or (duration is not None and 364 <= duration <= 371)
                    or ((not start or not end) and (o.form in ('10-K', '10-K/A') or type(o.fy) is int)))
        if apparent:
            annual.append(o)
        else:
            notes[o.observation_id].add('CLEARLY_NONANNUAL')
    ends = [dates[o.observation_id][1] for o in annual if dates[o.observation_id][1]]
    endpoint = max(ends) if ends else None
    for o in annual:
        if dates[o.observation_id][1] is None:
            reasons.add(R.ANNUAL_ENDPOINT_UNLOCATABLE)
            notes[o.observation_id].add(R.ANNUAL_ENDPOINT_UNLOCATABLE.value)
    if not annual:
        reasons.add(R.NO_APPARENT_ANNUAL_PERIOD)
    target = [o for o in annual if endpoint and dates[o.observation_id][1] == endpoint]
    intervals = set()
    relevant = []
    for o in target:
        start, end = dates[o.observation_id]
        duration = (end - start).days + 1 if start and end else None
        # Explicit quarterly/short facts are exclusions, not fiscal transitions.
        if duration is not None and 0 < duration < 364 and o.fp in ('Q1', 'Q2', 'Q3', 'Q4'):
            notes[o.observation_id].add('CLEARLY_NONANNUAL')
            continue
        relevant.append(o)
        if duration in (365, 366):
            intervals.add((o.start, o.end))
        else:
            reasons.add(R.ANNUAL_INTERVAL_UNSUPPORTED)
            notes[o.observation_id].add(R.ANNUAL_INTERVAL_UNSUPPORTED.value)
    if len(intervals) > 1:
        reasons.add(R.ANNUAL_INTERVAL_AMBIGUOUS)
    if target and not intervals:
        reasons.add(R.ANNUAL_INTERVAL_UNSUPPORTED)
    period_start = next(iter(intervals))[0] if len(intervals) == 1 else None
    capture_day = datetime.fromisoformat(receipt.captured_at.replace('Z', '+00:00')).date()
    admissible = []
    for o in relevant:
        local = notes[o.observation_id]
        start, end = dates[o.observation_id]
        row = json.loads(o.row_json, parse_float=Decimal)
        if set(row) - _ROW_KEYS or o.unit != 'USD':
            local.add(R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT.value)
        if o.form not in ('10-K', '10-K/A') or o.fp != 'FY':
            local.add(R.UNSUPPORTED_FILING_CONTEXT.value)
        filed = _date(o.filed)
        if (type(o.fy) is not int or not filed or type(o.accession) is not str
                or _ACCESSION.fullmatch(o.accession) is None or not start
                or not end or o.metadata_limitations and any(
                    n not in ('MISSING_VALUE', 'INVALID_VALUE', 'NONFINITE_VALUE', 'UNIT_NOT_REVIEWED_USD')
                    for n in o.metadata_limitations)):
            local.add(R.POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED.value)
        if filed and end and not end <= filed <= capture_day:
            local.add(R.INVALID_FILING_CHRONOLOGY.value)
        if o.value is None:
            local.add(R.FINITE_VALUE_UNAVAILABLE.value)
        reasons.update(R(n) for n in local if n in R._value2member_map_)
        if not local and period_start == o.start:
            admissible.append(o)
        elif local:
            dispositions[o.observation_id] = 'UNSUPPORTED'
    by_concept = [tuple(o for o in admissible if o.concept == c) for c in CONCEPTS]
    for group, reason in zip(by_concept, (R.REVENUE_UNAVAILABLE, R.OPERATING_INCOME_UNAVAILABLE)):
        if not group:
            reasons.add(reason)
    common = sorted({o.accession for o in by_concept[0]} & {o.accession for o in by_concept[1]})
    if not common:
        reasons.add(R.NO_COMMON_ANNUAL_ACCESSION)
    paired = [tuple(o for o in group if o.accession in common) for group in by_concept]
    values = [tuple(sorted({o.value for o in group})) for group in paired]
    filings = []
    for acc in common:
        together = tuple(o for group in paired for o in group if o.accession == acc)
        forms = tuple(sorted({o.form for o in together}))
        filed = tuple(sorted({o.filed for o in together}))
        years = tuple(sorted({o.fy for o in together}))
        if any(len(v) != 1 for v in (forms, filed, years)):
            reasons.add(R.COMMON_FILING_METADATA_CONFLICT)
        filings.append(ResearchSupportingFiling(acc, forms, filed, years,
            tuple(sorted(o.observation_id for o in paired[0] if o.accession == acc)),
            tuple(sorted(o.observation_id for o in paired[1] if o.accession == acc))))
    for v, reason in zip(values, (R.COMPETING_REVENUE_VALUES, R.COMPETING_OPERATING_INCOME_VALUES)):
        if len(v) > 1:
            reasons.add(reason)
    ordered = tuple(sorted(reasons, key=lambda r: r.value))
    status = _status(ordered)
    for o in admissible:
        if o.accession not in common:
            dispositions[o.observation_id] = 'ORPHAN'
            notes[o.observation_id].add('NO_PAIRED_CONCEPT_IN_ACCESSION')
        elif status is S.CANDIDATE_COHERENT:
            dispositions[o.observation_id] = 'SELECTED'
        else:
            dispositions[o.observation_id] = 'COMPETING' if status is S.SOURCE_CONFLICT else 'NONSELECTED'
            notes[o.observation_id].update(r.value for r in ordered)
    for o in rows:
        if not notes[o.observation_id] and dispositions[o.observation_id] == 'NONSELECTED':
            notes[o.observation_id].add('OUTSIDE_SELECTED_ANNUAL_INTERVAL')
    refs = tuple(ResearchObservationReference(
        o.observation_id, o.semantic_id, o.source_locator, o.semantic_locator,
        o.concept, o.unit, o.value, o.start, o.end, o.fy, o.fp, o.form, o.filed,
        o.accession, o.frame, o.metadata_limitations, dispositions[o.observation_id],
        tuple(sorted(notes[o.observation_id]))) for o in sorted(rows, key=lambda o: o.observation_id))
    inventory = _identity(IDENTITY_VERSION + ':extraction-inventory', {
        'version': extraction.extraction_version, 'receipt': receipt_id,
        'object': receipt.content_sha256, 'issues': list(extraction.issues),
        'rows': [{'id': o.observation_id, 'semantic': o.semantic_id,
                  'locator': o.source_locator} for o in sorted(rows, key=lambda o: o.observation_id)],
    })
    return CurrentAnnualReportedFactResearchCandidate(status, ordered, receipt.cik,
        period_start, endpoint.isoformat() if endpoint else None,
        values[0][0] if status is S.CANDIDATE_COHERENT else None,
        values[1][0] if status is S.CANDIDATE_COHERENT else None,
        receipt_id, receipt.content_sha256, receipt.captured_at, receipt.source_locator,
        receipt.acquisition_contract_version, refs, tuple(filings), inventory,
        extraction.issues, tuple(v if len(v) > 1 else () for v in values))
