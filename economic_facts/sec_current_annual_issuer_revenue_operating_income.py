"""Native capture-bound issuer facts; no security or investment admission.

REUSE existing SecArchive, extraction and exact serialization; ADAPT PR143's
annual surveillance locally without importing or promoting research candidates.
No new dependency or mandatory external cost. Full JSON extraction plus replay
uses memory proportional to the source/inventory; Chromebook fit is unmeasured.
"""
from dataclasses import asdict, dataclass, fields
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

CONTRACT_VERSION = '2026-10-12-current-annual-issuer-revenue-operating-income-qualification-v1'
QUALIFICATION_VERSION = '2026-10-12-issuer-apparent-annual-endpoint-common-filing-v1'
IDENTITY_VERSION = '2026-10-12-issuer-reported-profitability-evidence-identities-v1'
EVIDENCE_KIND = 'CURRENT_ANNUAL_ISSUER_REVENUE_OPERATING_INCOME_QUALIFICATION_V1'
AUTHORITY = 'CURRENT_ISSUER_REPORTED_PROFITABILITY_EVIDENCE_ONLY'
LIMITATIONS = (
    'LATEST_OBSERVED_SUPPORTED_ANNUAL_WITHIN_ONE_CAPTURE_ONLY',
    'NO_COMPLETE_ISSUER_COVERAGE_OR_ABSOLUTELY_NEWEST_PERIOD_CLAIM',
    'SOURCE_PRESENTED_REVENUE_NOT_UNIVERSAL_TOTAL_REVENUE',
    'NO_SECURITY_CLASS_ELIGIBILITY_OR_INVESTMENT_ADMISSION',
    'NO_ORDINARY_COMPOUNDER_ELIGIBILITY_OR_EPS_COMPARABILITY',
    'NO_CORPORATE_ACTION_SHARE_BASIS_OR_CROSS_PERIOD_REPORTING_SUBJECT_CONTINUITY',
    'NO_CROSS_PERIOD_LEGAL_ENTITY_CONTINUITY',
    'NO_CROSS_ISSUER_OR_CROSS_SECTOR_COMPARABILITY',
    'NO_NORMALIZATION_HISTORICAL_TRENDS_OR_OVERALL_QUALITY',
    'NO_DURABILITY_CONFIDENCE_OR_EXPECTED_RETURN',
    'NO_RANKING_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION',
    'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
    'NO_PIT_HISTORICAL_AS_OF_OR_PUBLICATION_TIME_AUTHORITY',
    'ONLY_ASSOCIATED_CURRENT_ISSUER_RESEARCH_DIAGNOSTIC',
    'UNAVAILABLE_IS_NOT_A_NEGATIVE_ISSUER_JUDGMENT',
    'LIVE_PROVENANCE_NOT_CRYPTOGRAPHIC_REMOTE_SEC_ATTESTATION',
    'NO_STAGE_C_EXIT_CREDIT_WITHOUT_CEO_OPTION_A_SUPPLEMENT',
)


class IssuerQualificationError(ArchiveError):
    """Public input or integrity error, never economic unavailability."""


class IssuerQualificationStatus(str, Enum):
    PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED = 'PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED'
    EVIDENCE_UNAVAILABLE = 'EVIDENCE_UNAVAILABLE'
    EVIDENCE_UNSUPPORTED = 'EVIDENCE_UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class IssuerQualificationReason(str, Enum):
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


R = IssuerQualificationReason
S = IssuerQualificationStatus
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
    return S.EVIDENCE_UNAVAILABLE if reasons else S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED


def _date(value):
    if type(value) is not str or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class IssuerObservationReference:
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
class IssuerAdjudicatedFiling:
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
class IssuerSupportingFiling:
    accession: str
    form: str
    filed: str
    fiscal_year: int
    revenue_observation_ids: tuple[str, ...]
    operating_income_observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ArchiveReplayBinding:
    archive: SecArchive
    receipt_id: str


class _ReplayCarrier:
    # Deliberately not a dataclass field: absent from asdict, repr and identity.
    __slots__ = ('_archive_replay_binding',)

    def __reduce_ex__(self, protocol):
        # Serialization is public facts only. Restored objects are detached and
        # must be recreated through the factory to become consumable evidence.
        return (type(self), tuple(getattr(self, f.name) for f in fields(self)))


@dataclass(frozen=True, slots=True)
class CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1(_ReplayCarrier):
    status: IssuerQualificationStatus
    reasons: tuple[IssuerQualificationReason, ...]
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
    observations: tuple[IssuerObservationReference, ...]
    adjudicated_filings: tuple[IssuerAdjudicatedFiling, ...]
    supporting_filings: tuple[IssuerSupportingFiling, ...]
    selected_revenue_observation_ids: tuple[str, ...]
    selected_operating_income_observation_ids: tuple[str, ...]
    source_byte_length: int
    extraction_inventory_id: str
    extraction_issues: tuple[str, ...]
    conflict_values: tuple[tuple[Decimal, ...], ...]
    contract_version: ClassVar[str] = CONTRACT_VERSION
    qualification_version: ClassVar[str] = QUALIFICATION_VERSION
    identity_version: ClassVar[str] = IDENTITY_VERSION
    extraction_version: ClassVar[str] = EXTRACTION_VERSION
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
            raise IssuerQualificationError('Canonical issuer state/reasons required')
        for collection, record_type in (
                (self.observations, IssuerObservationReference),
                (self.adjudicated_filings, IssuerAdjudicatedFiling),
                (self.supporting_filings, IssuerSupportingFiling)):
            if type(collection) is not tuple or any(type(v) is not record_type for v in collection):
                raise IssuerQualificationError('Immutable typed issuer inventory required')
        if any(type(v) is not tuple for v in (
                self.selected_revenue_observation_ids, self.selected_operating_income_observation_ids,
                self.extraction_issues, self.conflict_values)):
            raise IssuerQualificationError('Immutable issuer evidence required')
        for observation in self.observations:
            if (type(observation.metadata_limitations) is not tuple
                    or type(observation.exclusion_reasons) is not tuple
                    or observation.disposition not in
                    ('SELECTED', 'NONSELECTED', 'ORPHAN', 'UNSUPPORTED', 'COMPETING')):
                raise IssuerQualificationError('Immutable observation disposition required')
        established = self.status is S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED
        if established:
            if (any(type(v) is not Decimal or not v.is_finite()
                    for v in (self.revenue, self.operating_income))
                    or not self.supporting_filings or not self.period_start or not self.period_end
                    or not self.selected_revenue_observation_ids
                    or not self.selected_operating_income_observation_ids):
                raise IssuerQualificationError('Complete established issuer pair required')
        elif (self.revenue is not None or self.operating_income is not None
                or self.supporting_filings or self.selected_revenue_observation_ids
                or self.selected_operating_income_observation_ids
                or any(o.disposition == 'SELECTED' for o in self.observations)):
            raise IssuerQualificationError('Non-established evidence cannot select facts')

    @property
    def semantic_id(self):
        return _identity(IDENTITY_VERSION + ':semantic', _jsonable({
            'contract': CONTRACT_VERSION, 'qualification': QUALIFICATION_VERSION,
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


def qualify_sec_current_annual_issuer_revenue_operating_income_v1(archive, receipt_id):
    """Qualify one exact LIVE capture; no acquisition or security admission."""
    if (type(archive) is not SecArchive or type(receipt_id) is not str
            or re.fullmatch(r'[0-9a-f]{64}', receipt_id) is None):
        raise IssuerQualificationError('Exact archive and lowercase receipt ID required')
    # Snapshot the location; do not retain caller-overridable instance methods.
    archive = SecArchive(archive.root)
    receipt = SecArchive.read_receipt(archive, receipt_id)
    raw = SecArchive.read_object(archive, receipt)
    if (receipt.receipt_id != receipt_id
            or receipt.acquisition_contract_version != LIVE_ACQUISITION_CONTRACT_VERSION
            or receipt.endpoint != endpoint_for(receipt.cik)
            or receipt.source_locator != receipt.endpoint):
        raise IssuerQualificationError('Canonical LIVE Companyfacts capture required')
    extraction = extract_revenue_operating_income(raw, receipt)
    if extraction.source_cik != receipt.cik:
        raise IssuerQualificationError('Receipt and extracted source CIK mismatch')
    result = _qualify_extraction(receipt, extraction)
    object.__setattr__(result, '_archive_replay_binding', _ArchiveReplayBinding(archive, receipt_id))
    return result


def _qualify_extraction(receipt, extraction):
    """Single source-derived adjudication pass; never consumes a research result."""
    receipt_id = receipt.receipt_id
    rows = extraction.observations
    reasons = set()
    notes = {o.observation_id: set() for o in rows}
    dispositions = {o.observation_id: 'NONSELECTED' for o in rows}
    dates = {o.observation_id: (_date(o.start), _date(o.end)) for o in rows}
    annual = []
    for o in rows:
        start, end = dates[o.observation_id]
        duration = (end - start).days + 1 if start and end else None
        fiscal_or_period_incomplete = (
            not start or not end or o.fp is None or o.fy is None
        )
        # Explicit FY and annual-length evidence have independent priority.
        # Quarterly metadata blocks inference solely from filing-vintage FY;
        # a supported annual form with incomplete context remains unresolved.
        unresolved_annual = (
            fiscal_or_period_incomplete
            and (o.form in ('10-K', '10-K/A')
                 or (o.fp not in ('Q1', 'Q2', 'Q3', 'Q4') and type(o.fy) is int))
        )
        apparent = (o.fp == 'FY' or (duration is not None and 364 <= duration <= 371)
                    or unresolved_annual)
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
        filings.append(IssuerAdjudicatedFiling(acc, forms, filed, years,
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
        elif status is S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED:
            dispositions[o.observation_id] = 'SELECTED'
        else:
            dispositions[o.observation_id] = 'COMPETING' if status is S.SOURCE_CONFLICT else 'NONSELECTED'
            notes[o.observation_id].update(r.value for r in ordered)
    for o in rows:
        if not notes[o.observation_id] and dispositions[o.observation_id] == 'NONSELECTED':
            notes[o.observation_id].add('OUTSIDE_SELECTED_ANNUAL_INTERVAL')
    refs = tuple(IssuerObservationReference(
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
    established = status is S.PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED
    selected = [tuple(sorted(group, key=lambda o: o.observation_id)) for group in paired]
    support = tuple(IssuerSupportingFiling(f.accession, f.forms[0], f.filed_dates[0],
        f.fiscal_years[0], f.revenue_observation_ids, f.operating_income_observation_ids)
        for f in filings) if established else ()
    return CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1(
        status=status, reasons=ordered, source_cik=receipt.cik,
        period_start=period_start, period_end=endpoint.isoformat() if endpoint else None,
        revenue=selected[0][0].value if established else None,
        operating_income=selected[1][0].value if established else None,
        capture_receipt_id=receipt_id, source_object_hash=receipt.content_sha256,
        captured_at=receipt.captured_at, source_locator=receipt.source_locator,
        acquisition_contract_version=receipt.acquisition_contract_version,
        observations=refs, adjudicated_filings=tuple(filings), supporting_filings=support,
        selected_revenue_observation_ids=tuple(o.observation_id for o in selected[0]) if established else (),
        selected_operating_income_observation_ids=tuple(o.observation_id for o in selected[1]) if established else (),
        source_byte_length=receipt.byte_length, extraction_inventory_id=inventory,
        extraction_issues=extraction.issues,
        conflict_values=tuple(v if len(v) > 1 else () for v in values),
    )


_CONTRACT_SURFACE = {
    'contract_version': CONTRACT_VERSION, 'qualification_version': QUALIFICATION_VERSION,
    'identity_version': IDENTITY_VERSION, 'extraction_version': EXTRACTION_VERSION,
    'evidence_kind': EVIDENCE_KIND, 'authority': AUTHORITY, 'limitations': LIMITATIONS,
    'source_kind': 'SEC_COMPANYFACTS_SNAPSHOT', 'namespace': 'us-gaap',
    'concepts': CONCEPTS, 'unit': 'USD', 'accounting_basis': 'US_GAAP',
    'temporal_mode': 'CURRENT_CAPTURE_BOUND_ONLY',
}


def _same_public_value(supplied, canonical):
    """Compare this closed source-replay surface without permissive == coercion."""
    if type(supplied) is not type(canonical):
        return False
    if type(canonical) is tuple:
        return len(supplied) == len(canonical) and all(
            _same_public_value(a, b) for a, b in zip(supplied, canonical))
    if type(canonical) is Decimal:
        return supplied.is_finite() and supplied.as_tuple() == canonical.as_tuple()
    if type(canonical) in (str, int, type(None)):
        return supplied == canonical
    if type(canonical) in (S, R):
        return supplied is canonical
    if type(canonical) in (CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1,
            IssuerObservationReference, IssuerAdjudicatedFiling, IssuerSupportingFiling):
        return all(_same_public_value(getattr(supplied, f.name), getattr(canonical, f.name))
                   for f in fields(canonical))
    return False


def _verified_issuer_snapshot(qualification):
    """Authenticate once and return only the independent source-derived snapshot.

    This is local archive integrity, not protection from arbitrary process code
    or replacement of all trust anchors. No caller callbacks participate.
    """
    if type(qualification) is not CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1:
        raise IssuerQualificationError('Exact native issuer qualification required')
    try:
        if any(not _same_public_value(getattr(qualification, key), expected)
               for key, expected in _CONTRACT_SURFACE.items()):
            raise IssuerQualificationError('Incompatible issuer qualification contract')
        binding = qualification._archive_replay_binding
        if (type(binding) is not _ArchiveReplayBinding or type(binding.archive) is not SecArchive
                or type(binding.receipt_id) is not str
                or type(qualification.capture_receipt_id) is not str
                or binding.receipt_id != qualification.capture_receipt_id):
            raise IssuerQualificationError('Missing or stale native archive binding')
        # One verified object read/extraction/adjudication, never a cached boolean.
        replay = qualify_sec_current_annual_issuer_revenue_operating_income_v1(
            binding.archive, binding.receipt_id)
        if not _same_public_value(qualification, replay):
            raise IssuerQualificationError('Issuer qualification differs from source replay')
        if (qualification.semantic_id != replay.semantic_id
                or qualification.evidence_id != replay.evidence_id):
            raise IssuerQualificationError('Issuer qualification identity mismatch')
        return replay
    except (AttributeError, TypeError, ValueError, ArithmeticError, RecursionError):
        raise IssuerQualificationError('Native issuer qualification replay failed') from None
