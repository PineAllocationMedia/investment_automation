"""D1 same-filing comparative issuer evidence, CURRENT capture bound only.

EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT: REUSE PAM SecArchive,
2026-10-07 extraction, canonical exact Decimal JSON and native replay carrier;
ADAPT annual surveillance for the approved comparative contract. The Work Order
reports the external reuse gate completed: no dependency adoption or new costs.
No external code, license, API or data rights are introduced. Memory is linear in
source/inventory size; existing Python CPU runtime only, no GPU/downloads. Mac
validation does not establish Chromebook capacity or deployment compatibility.

Technical observation reasons: CLEARLY_NONANNUAL is proven short quarterly or
non-apparent annual context; OLDER_COMPARATIVE_HISTORY requires an identified
newer predecessor in that filing; OUTSIDE_COMPARATIVE_INTERVAL is other source
history; NO_COMPLETE_COMPARATIVE_SUPPORT is an admissible unselected/orphan row.
Economic reasons are separate from the two closed NONSELECTED exclusions.
"""
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import json
import re
from typing import ClassVar

from .sec_archive import ArchiveError, SecArchive, LIVE_ACQUISITION_CONTRACT_VERSION, endpoint_for
from .sec_revenue_operating_income import (
    extract_revenue_operating_income, RevenueOperatingIncomeObservation,
    _identity, CONCEPTS, EXTRACTION_VERSION,
)
from .sec_current_annual_issuer_revenue_operating_income import (
    _date, _jsonable, _ReplayCarrier, _ArchiveReplayBinding, _ACCESSION, _ROW_KEYS,
)

CONTRACT_VERSION = '2026-10-12-current-annual-issuer-two-period-revenue-operating-income-qualification-v1'
QUALIFICATION_VERSION = '2026-10-12-issuer-same-filing-adjacent-annual-pair-v1'
IDENTITY_VERSION = '2026-10-12-d1-comparative-evidence-identities-v1'
EVIDENCE_KIND = 'CURRENT_ANNUAL_ISSUER_TWO_PERIOD_REVENUE_OPERATING_INCOME_QUALIFICATION_V1'
AUTHORITY = 'CURRENT_ISSUER_TWO_PERIOD_REPORTED_OPERATING_FACTS_EVIDENCE_ONLY'
LIMITATIONS = (
    'LATEST_APPARENT_ANNUAL_ENDPOINT_WITHIN_ONE_VERIFIED_CAPTURE_ONLY',
    'NO_ABSOLUTELY_NEWEST_ISSUER_PERIOD_OR_COMPLETE_COVERAGE_CLAIM',
    'NO_INTER_FILING_ECONOMIC_COMPARABILITY_OR_OPERATIONAL_PERIMETER_CONTINUITY',
    'NO_LEGAL_ENTITY_OR_ACCOUNTING_REPORTING_SUBJECT_CONTINUITY',
    'NO_NORMALIZATION_EBIT_EBITDA_OR_ROIC',
    'NO_CYCLE_RESILIENCE_MOAT_OR_FUTURE_PERSISTENCE',
    'NO_COMPOSITE_DURABILITY_OR_OVERALL_QUALITY',
    'NO_ORDINARY_COMPOUNDER_PR5C_OR_INVESTMENT_ADMISSION',
    'NO_QUALITY_CONFIDENCE_OR_EXPECTED_RETURN_CHANGE',
    'NO_PIT_HISTORICAL_AS_OF_OR_PUBLICATION_TIME_AUTHORITY',
    'NO_RECOMMENDATION_RANKING_ALLOCATION_SIZING_OR_EXECUTION',
    'NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION',
    'NO_SOURCE_DATA_REDISTRIBUTION_RIGHTS',
    'LIVE_PROVENANCE_NOT_REMOTE_CRYPTOGRAPHIC_SEC_ATTESTATION',
    'UNAVAILABLE_IS_NOT_A_NEGATIVE_ISSUER_JUDGMENT',
)


class ComparativeQualificationError(ArchiveError):
    """Invalid native input/contract/integrity; never economic unavailability."""


class ComparativeQualificationStatus(str, Enum):
    COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED = 'COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED'
    EVIDENCE_UNAVAILABLE = 'EVIDENCE_UNAVAILABLE'
    EVIDENCE_UNSUPPORTED = 'EVIDENCE_UNSUPPORTED'
    SOURCE_CONFLICT = 'SOURCE_CONFLICT'


class ComparativeQualificationReason(str, Enum):
    NO_APPARENT_ANNUAL_PERIOD = 'NO_APPARENT_ANNUAL_PERIOD'
    ANNUAL_ENDPOINT_UNLOCATABLE = 'ANNUAL_ENDPOINT_UNLOCATABLE'
    CURRENT_ANNUAL_INTERVAL_UNSUPPORTED = 'CURRENT_ANNUAL_INTERVAL_UNSUPPORTED'
    CURRENT_ANNUAL_INTERVAL_AMBIGUOUS = 'CURRENT_ANNUAL_INTERVAL_AMBIGUOUS'
    CURRENT_REVENUE_UNAVAILABLE = 'CURRENT_REVENUE_UNAVAILABLE'
    CURRENT_OPERATING_INCOME_UNAVAILABLE = 'CURRENT_OPERATING_INCOME_UNAVAILABLE'
    NO_COMMON_CURRENT_ACCESSION = 'NO_COMMON_CURRENT_ACCESSION'
    FINITE_VALUE_UNAVAILABLE = 'FINITE_VALUE_UNAVAILABLE'
    ADJACENT_PRIOR_PERIOD_NOT_OBSERVED = 'ADJACENT_PRIOR_PERIOD_NOT_OBSERVED'
    PRIOR_REVENUE_UNAVAILABLE = 'PRIOR_REVENUE_UNAVAILABLE'
    PRIOR_OPERATING_INCOME_UNAVAILABLE = 'PRIOR_OPERATING_INCOME_UNAVAILABLE'
    NO_COMMON_FOUR_CELL_ACCESSION = 'NO_COMMON_FOUR_CELL_ACCESSION'
    PRIOR_ANNUAL_INTERVAL_UNSUPPORTED = 'PRIOR_ANNUAL_INTERVAL_UNSUPPORTED'
    PRIOR_ANNUAL_INTERVAL_AMBIGUOUS = 'PRIOR_ANNUAL_INTERVAL_AMBIGUOUS'
    PERIODS_NOT_IMMEDIATELY_ADJACENT = 'PERIODS_NOT_IMMEDIATELY_ADJACENT'
    PERIODS_OVERLAP = 'PERIODS_OVERLAP'
    UNSUPPORTED_FILING_CONTEXT = 'UNSUPPORTED_FILING_CONTEXT'
    UNSUPPORTED_UNIT_OR_ROW_CONTEXT = 'UNSUPPORTED_UNIT_OR_ROW_CONTEXT'
    COMPARATIVE_CONTEXT_UNRESOLVED = 'COMPARATIVE_CONTEXT_UNRESOLVED'
    INVALID_FILING_CHRONOLOGY = 'INVALID_FILING_CHRONOLOGY'
    COMMON_FILING_METADATA_CONFLICT = 'COMMON_FILING_METADATA_CONFLICT'
    COMPETING_CURRENT_REVENUE_VALUES = 'COMPETING_CURRENT_REVENUE_VALUES'
    COMPETING_CURRENT_OPERATING_INCOME_VALUES = 'COMPETING_CURRENT_OPERATING_INCOME_VALUES'
    COMPETING_PRIOR_REVENUE_VALUES = 'COMPETING_PRIOR_REVENUE_VALUES'
    COMPETING_PRIOR_OPERATING_INCOME_VALUES = 'COMPETING_PRIOR_OPERATING_INCOME_VALUES'


class ObservationDisposition(str, Enum):
    SELECTED = 'SELECTED'
    NONSELECTED = 'NONSELECTED'
    ORPHAN = 'ORPHAN'
    UNSUPPORTED = 'UNSUPPORTED'
    COMPETING = 'COMPETING'


class ObservationExclusionReason(str, Enum):
    EXCLUDED_CONSISTENT_PARTIAL_CURRENT = 'EXCLUDED_CONSISTENT_PARTIAL_CURRENT'
    EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY = 'EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY'


R = ComparativeQualificationReason
S = ComparativeQualificationStatus
D = ObservationDisposition
X = ObservationExclusionReason
_UNAVAILABLE = frozenset((R.NO_APPARENT_ANNUAL_PERIOD, R.CURRENT_REVENUE_UNAVAILABLE,
    R.CURRENT_OPERATING_INCOME_UNAVAILABLE, R.NO_COMMON_CURRENT_ACCESSION,
    R.FINITE_VALUE_UNAVAILABLE, R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED,
    R.PRIOR_REVENUE_UNAVAILABLE, R.PRIOR_OPERATING_INCOME_UNAVAILABLE,
    R.NO_COMMON_FOUR_CELL_ACCESSION))
_CONFLICT = frozenset((R.INVALID_FILING_CHRONOLOGY, R.COMMON_FILING_METADATA_CONFLICT,
    R.COMPETING_CURRENT_REVENUE_VALUES, R.COMPETING_CURRENT_OPERATING_INCOME_VALUES,
    R.COMPETING_PRIOR_REVENUE_VALUES, R.COMPETING_PRIOR_OPERATING_INCOME_VALUES))


def _status(reasons):
    if set(reasons) & _CONFLICT:
        return S.SOURCE_CONFLICT
    if set(reasons) - _UNAVAILABLE:
        return S.EVIDENCE_UNSUPPORTED
    return S.EVIDENCE_UNAVAILABLE if reasons else S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED


@dataclass(frozen=True, slots=True)
class ComparativeObservationReference:
    observation: RevenueOperatingIncomeObservation
    disposition: ObservationDisposition
    reasons: tuple[str, ...]
    exclusion_reasons: tuple[ObservationExclusionReason, ...]


@dataclass(frozen=True, slots=True)
class ComparativeFiling:
    accession: str
    population: str  # F, Q (subset of F), H, or UNLINKED
    observation_ids: tuple[str, ...]
    forms: tuple[str, ...]
    filed_dates: tuple[str, ...]
    fiscal_years: tuple[int, ...]
    prior_candidates: tuple[tuple[str | None, str], ...]
    # Four partitions: PRIOR Revenue, PRIOR OI, CURRENT Revenue, CURRENT OI.
    cell_observation_ids: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1(_ReplayCarrier):
    status: ComparativeQualificationStatus
    reasons: tuple[ComparativeQualificationReason, ...]
    source_cik: str
    prior_period_start: str | None
    prior_period_end: str | None
    current_period_start: str | None
    current_period_end: str | None
    prior_revenue: Decimal | None
    prior_operating_income: Decimal | None
    current_revenue: Decimal | None
    current_operating_income: Decimal | None
    capture_receipt_id: str
    source_object_hash: str
    source_byte_length: int
    captured_at: str
    endpoint: str
    source_locator: str
    acquisition_contract_version: str
    observations: tuple[ComparativeObservationReference, ...]
    adjudicated_filings: tuple[ComparativeFiling, ...]
    supporting_filings: tuple[ComparativeFiling, ...]
    selected_observation_ids: tuple[tuple[str, ...], ...]
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
            raise ComparativeQualificationError('Canonical comparative state/reasons required')
        for collection, record in ((self.observations, ComparativeObservationReference),
                (self.adjudicated_filings, ComparativeFiling), (self.supporting_filings, ComparativeFiling)):
            if type(collection) is not tuple or any(type(v) is not record for v in collection):
                raise ComparativeQualificationError('Immutable native comparative inventory required')
        for ref in self.observations:
            if (type(ref.observation) is not RevenueOperatingIncomeObservation
                    or type(ref.disposition) is not D or type(ref.reasons) is not tuple
                    or type(ref.exclusion_reasons) is not tuple
                    or any(type(x) is not X for x in ref.exclusion_reasons)
                    or ref.exclusion_reasons != tuple(sorted(set(ref.exclusion_reasons), key=lambda x: x.value))
                    or ref.exclusion_reasons and ref.disposition is not D.NONSELECTED):
                raise ComparativeQualificationError('Closed observation surface required')
        if (type(self.selected_observation_ids) is not tuple or len(self.selected_observation_ids) != 4
                or any(type(g) is not tuple for g in self.selected_observation_ids)
                or type(self.conflict_values) is not tuple or len(self.conflict_values) != 4
                or any(type(g) is not tuple for g in self.conflict_values)
                or type(self.extraction_issues) is not tuple):
            raise ComparativeQualificationError('Four immutable cell groups required')
        values = (self.prior_revenue, self.prior_operating_income,
                  self.current_revenue, self.current_operating_income)
        if self.status is S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED:
            if (any(type(v) is not Decimal or not v.is_finite() for v in values)
                    or not all(self.selected_observation_ids) or not self.supporting_filings
                    or not all((self.prior_period_start, self.prior_period_end,
                                self.current_period_start, self.current_period_end))):
                raise ComparativeQualificationError('Complete established four-cell presentation required')
        elif (any(v is not None for v in values) or any(self.selected_observation_ids)
                or self.supporting_filings or any(o.disposition is D.SELECTED for o in self.observations)):
            raise ComparativeQualificationError('Negative state cannot expose established facts')

    @property
    def semantic_id(self):
        return _identity(IDENTITY_VERSION + ':semantic', _jsonable({
            **_CONTRACT_SURFACE, 'status': self.status, 'reasons': self.reasons,
            'cik': self.source_cik,
            'periods': (self.prior_period_start, self.prior_period_end,
                        self.current_period_start, self.current_period_end),
            'values': (self.prior_revenue, self.prior_operating_income,
                       self.current_revenue, self.current_operating_income),
            'conflict_values': self.conflict_values,
        }))

    @property
    def evidence_id(self):
        return _identity(IDENTITY_VERSION + ':evidence', _jsonable({
            'semantic_id': self.semantic_id, 'result': asdict(self),
        }))


def _apparent_annual(o):
    start, end = _date(o.start), _date(o.end)
    duration = (end - start).days + 1 if start and end else None
    incomplete = not start or not end or o.fp is None or o.fy is None
    return (o.fp == 'FY' or duration is not None and 364 <= duration <= 371
            or incomplete and (o.form in ('10-K', '10-K/A')
                or o.fp not in ('Q1', 'Q2', 'Q3', 'Q4') and type(o.fy) is int))


def _short_quarter(o):
    start, end = _date(o.start), _date(o.end)
    return bool(start and end and 0 < (end - start).days + 1 < 364
                and o.fp in ('Q1', 'Q2', 'Q3', 'Q4'))


def _row_reasons(o, capture_day):
    reasons = set()
    row = json.loads(o.row_json, parse_float=Decimal)
    if set(row) - _ROW_KEYS or o.unit != 'USD':
        reasons.add(R.UNSUPPORTED_UNIT_OR_ROW_CONTEXT)
    if o.form not in ('10-K', '10-K/A') or o.fp != 'FY':
        reasons.add(R.UNSUPPORTED_FILING_CONTEXT)
    start, end, filed = _date(o.start), _date(o.end), _date(o.filed)
    if (type(o.fy) is not int or not filed or not start or not end
            or type(o.accession) is not str or _ACCESSION.fullmatch(o.accession) is None
            or any(n not in ('MISSING_VALUE', 'INVALID_VALUE', 'NONFINITE_VALUE',
                             'UNIT_NOT_REVIEWED_USD') for n in o.metadata_limitations)):
        reasons.add(R.COMPARATIVE_CONTEXT_UNRESOLVED)
    if filed and end and not end <= filed <= capture_day:
        reasons.add(R.INVALID_FILING_CHRONOLOGY)
    if o.value is None:
        reasons.add(R.FINITE_VALUE_UNAVAILABLE)
    return reasons


def _metadata_conflict(rows):
    return (len({o.form for o in rows if o.form is not None}) > 1
            or len({o.filed for o in rows if _date(o.filed)}) > 1
            or len({o.fy for o in rows if type(o.fy) is int}) > 1)


def qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(archive, receipt_id):
    """Read one authentic local LIVE receipt and all its source bytes; no writes."""
    if (type(archive) is not SecArchive or type(receipt_id) is not str
            or re.fullmatch(r'[0-9a-f]{64}', receipt_id) is None):
        raise ComparativeQualificationError('Exact archive and lowercase receipt ID required')
    archive = SecArchive(archive.root)
    receipt = SecArchive.read_receipt(archive, receipt_id)
    raw = SecArchive.read_object(archive, receipt)
    if (receipt.receipt_id != receipt_id
            or receipt.acquisition_contract_version != LIVE_ACQUISITION_CONTRACT_VERSION
            or receipt.endpoint != receipt.source_locator
            or receipt.endpoint != endpoint_for(receipt.cik)):
        raise ComparativeQualificationError('Exact LIVE Companyfacts source binding required')
    extraction = extract_revenue_operating_income(raw, receipt)
    if extraction.source_cik != receipt.cik:
        raise ComparativeQualificationError('Receipt and source CIK mismatch')
    result = _qualify_extraction(receipt, extraction)
    object.__setattr__(result, '_archive_replay_binding', _ArchiveReplayBinding(archive, receipt_id))
    return result


def _qualify_extraction(receipt, extraction):
    rows = extraction.observations
    reasons = set()
    notes = {o.observation_id: set() for o in rows}
    exclusions = {o.observation_id: set() for o in rows}
    dispositions = {o.observation_id: D.NONSELECTED for o in rows}
    capture_day = datetime.fromisoformat(receipt.captured_at.replace('Z', '+00:00')).date()
    annual = [o for o in rows if _apparent_annual(o) and not _short_quarter(o)]
    annual_ids = {o.observation_id for o in annual}
    for o in rows:
        if o.observation_id not in annual_ids:
            notes[o.observation_id].add('CLEARLY_NONANNUAL')
    if not annual:
        reasons.add(R.NO_APPARENT_ANNUAL_PERIOD)
    if any(_date(o.end) is None for o in annual):
        reasons.add(R.ANNUAL_ENDPOINT_UNLOCATABLE)
    ends = [_date(o.end) for o in annual if _date(o.end)]
    endpoint = max(ends) if ends else None
    target = [o for o in annual if endpoint and _date(o.end) == endpoint]
    target_ids = {o.observation_id for o in target}
    intervals = set()
    valid = {}

    def inspect(o):
        local = _row_reasons(o, capture_day)
        reasons.update(local)
        notes[o.observation_id].update(r.value for r in local)
        valid[o.observation_id] = not local
        if local:
            dispositions[o.observation_id] = D.UNSUPPORTED
        return not local

    for o in target:
        start = _date(o.start)
        if start and (endpoint - start).days + 1 in (365, 366):
            intervals.add((o.start, o.end))
        else:
            reasons.add(R.CURRENT_ANNUAL_INTERVAL_UNSUPPORTED)
            notes[o.observation_id].add(R.CURRENT_ANNUAL_INTERVAL_UNSUPPORTED.value)
            dispositions[o.observation_id] = D.UNSUPPORTED
        inspect(o)
    if len(intervals) > 1:
        reasons.add(R.CURRENT_ANNUAL_INTERVAL_AMBIGUOUS)
    current = next(iter(intervals)) if len(intervals) == 1 else None
    if reasons & {R.ANNUAL_ENDPOINT_UNLOCATABLE, R.CURRENT_ANNUAL_INTERVAL_UNSUPPORTED,
                  R.CURRENT_ANNUAL_INTERVAL_AMBIGUOUS}:
        current = None
    f_accessions = {o.accession for o in target if o.accession is not None}
    current_groups = [[], []]
    coherent_current = set()
    candidates = {}
    complete = {}
    prior = None
    conflicts = [(), (), (), ()]
    cell_groups = [[], [], [], []]
    relevant_ids = {o.observation_id for o in target}

    for acc in f_accessions:
        if _metadata_conflict([o for o in target if o.accession == acc]):
            reasons.add(R.COMMON_FILING_METADATA_CONFLICT)
            for o in target:
                if o.accession == acc:
                    notes[o.observation_id].add(R.COMMON_FILING_METADATA_CONFLICT.value)

    if current:
        current_groups = [[o for o in target if o.concept == c and valid[o.observation_id]]
                          for c in CONCEPTS]
        for group, reason in zip(current_groups, (R.CURRENT_REVENUE_UNAVAILABLE,
                                                  R.CURRENT_OPERATING_INCOME_UNAVAILABLE)):
            if not group:
                reasons.add(reason)
        accession_sets = [{o.accession for o in g} for g in current_groups]
        common = accession_sets[0] & accession_sets[1]
        if all(accession_sets) and not common:
            reasons.add(R.NO_COMMON_CURRENT_ACCESSION)
        coherent_current = {acc for acc in common if not _metadata_conflict(
            [o for o in target if o.accession == acc])
            and all(len({o.value for o in group if o.accession == acc}) == 1
                    for group in current_groups)}
        for index, group in enumerate(current_groups, 2):
            values = tuple(sorted({o.value for o in group}))
            if len(values) > 1:
                conflicts[index] = values
                reasons.add((R.COMPETING_CURRENT_REVENUE_VALUES,
                             R.COMPETING_CURRENT_OPERATING_INCOME_VALUES)[index - 2])
                for o in group:
                    dispositions[o.observation_id] = D.COMPETING
                    notes[o.observation_id].add((R.COMPETING_CURRENT_REVENUE_VALUES,
                        R.COMPETING_CURRENT_OPERATING_INCOME_VALUES)[index - 2].value)
        if coherent_current:
            required_end = (_date(current[0]) - timedelta(days=1)).isoformat()
            for acc in sorted(coherent_current):
                previous = [o for o in annual if o.accession == acc
                            and _date(o.end) and _date(o.end) < endpoint]
                latest = max((_date(o.end) for o in previous), default=None)
                immediate = [o for o in previous if _date(o.end) == latest]
                candidates[acc] = tuple(sorted({(o.start, o.end) for o in immediate},
                                               key=lambda p: (p[1], p[0] or '')))
                for o in previous:
                    if _date(o.end) != latest:
                        notes[o.observation_id].add('OLDER_COMPARATIVE_HISTORY')
                for o in immediate:
                    relevant_ids.add(o.observation_id)
                    inspect(o)
                    start, end = _date(o.start), _date(o.end)
                    if not start or (end - start).days + 1 not in (365, 366):
                        reasons.add(R.PRIOR_ANNUAL_INTERVAL_UNSUPPORTED)
                        notes[o.observation_id].add(R.PRIOR_ANNUAL_INTERVAL_UNSUPPORTED.value)
                        dispositions[o.observation_id] = D.UNSUPPORTED
                    if start and start < _date(current[0]) <= end:
                        reasons.add(R.PERIODS_OVERLAP)
                        notes[o.observation_id].add(R.PERIODS_OVERLAP.value)
                    elif o.end != required_end:
                        reasons.add(R.PERIODS_NOT_IMMEDIATELY_ADJACENT)
                        notes[o.observation_id].add(R.PERIODS_NOT_IMMEDIATELY_ADJACENT.value)
                together = [o for o in target + immediate if o.accession == acc]
                if _metadata_conflict(together):
                    reasons.add(R.COMMON_FILING_METADATA_CONFLICT)
                    continue
                for interval in candidates[acc]:
                    start, end = map(_date, interval)
                    if not start or end.isoformat() != required_end or (end-start).days+1 not in (365, 366):
                        continue
                    groups = [[o for o in immediate if (o.start, o.end) == interval
                               and o.concept == c and valid[o.observation_id]] for c in CONCEPTS]
                    four_groups = groups + [
                        [o for o in g if o.accession == acc] for g in current_groups]
                    if all(len({o.value for o in group}) == 1 for group in four_groups):
                        complete[(acc, interval)] = four_groups
            prior_intervals = {interval for acc, interval in complete}
            if len(prior_intervals) > 1:
                reasons.add(R.PRIOR_ANNUAL_INTERVAL_AMBIGUOUS)
            elif len(prior_intervals) == 1:
                prior = next(iter(prior_intervals))
            else:
                # Determine a provisional adjacent interval from relevant F only;
                # H never determines PRIOR or supplies an established cell.
                adjacent = {p for ps in candidates.values() for p in ps if p[1] == required_end
                            and _date(p[0]) and (_date(p[1]) - _date(p[0])).days + 1 in (365, 366)}
                if len(adjacent) == 1:
                    prior = next(iter(adjacent))
                elif len(adjacent) > 1:
                    reasons.add(R.COMPARATIVE_CONTEXT_UNRESOLVED)
            if not any(candidates.values()):
                global_prior = [[o for o in annual if o.concept == c and o.end == required_end
                                 and _date(o.start) and (_date(o.end)-_date(o.start)).days+1 in (365,366)
                                 and not _row_reasons(o, capture_day)] for c in CONCEPTS]
                reasons.add(R.NO_COMMON_FOUR_CELL_ACCESSION if all(global_prior)
                            else R.ADJACENT_PRIOR_PERIOD_NOT_OBSERVED)
            if not complete and any(candidates.values()):
                global_prior = [[o for o in annual if o.concept == c and o.end == required_end
                                 and _date(o.start) and (_date(o.end)-_date(o.start)).days+1 in (365,366)
                                 and not _row_reasons(o, capture_day)] for c in CONCEPTS]
                if all(global_prior):
                    reasons.add(R.NO_COMMON_FOUR_CELL_ACCESSION)
            for o in annual:
                if o.accession in f_accessions - coherent_current and _date(o.end) != endpoint:
                    if (prior and _date(o.start) and _date(o.end)
                            and (_date(o.end)-_date(o.start)).days+1 in (365,366)
                            and _date(o.end) < _date(prior[1]) and not _row_reasons(o, capture_day)):
                        continue
                    relevant_ids.add(o.observation_id)
                    inspect(o)
                    if not prior and (o.end != required_end or not _date(o.start)
                            or (_date(o.end)-_date(o.start)).days+1 not in (365,366)):
                        reasons.add(R.COMPARATIVE_CONTEXT_UNRESOLVED)
            if prior:
                # Every exact PRIOR row in F, including partial filings, is
                # surveyed. Alternative contexts in partial F cannot vanish.
                for o in annual:
                    if o.accession not in f_accessions or _date(o.end) == endpoint:
                        continue
                    if (o.start, o.end) == prior:
                        relevant_ids.add(o.observation_id)
                        inspect(o)
                    elif (o.accession not in coherent_current
                          or (o.start, o.end) in candidates[o.accession]):
                        # Immediate alternatives remain material even when
                        # their accession has a coherent CURRENT pair. Older
                        # same-filing history was excluded during selection.
                        start, end = _date(o.start), _date(o.end)
                        if (start and end and (end-start).days+1 in (365,366)
                                and end < _date(prior[1]) and not _row_reasons(o, capture_day)):
                            # An explicit older interval cannot replace the
                            # already demonstrated adjacent predecessor.
                            notes[o.observation_id].add('OUTSIDE_COMPARATIVE_INTERVAL')
                        else:
                            relevant_ids.add(o.observation_id)
                            inspect(o)
                            reasons.add(R.COMPARATIVE_CONTEXT_UNRESOLVED)
                prior_groups = [[o for o in annual if o.accession in f_accessions
                                 and (o.start, o.end) == prior and o.concept == c
                                 and valid.get(o.observation_id, False)] for c in CONCEPTS]
                for group, reason in zip(prior_groups, (R.PRIOR_REVENUE_UNAVAILABLE,
                                                        R.PRIOR_OPERATING_INCOME_UNAVAILABLE)):
                    if not group:
                        reasons.add(reason)
                if all(prior_groups) and not complete:
                    reasons.add(R.NO_COMMON_FOUR_CELL_ACCESSION)
                cell_groups = prior_groups + current_groups
                for index, group in enumerate(prior_groups):
                    values = tuple(sorted({o.value for o in group}))
                    if len(values) > 1:
                        conflicts[index] = values
                        reasons.add((R.COMPETING_PRIOR_REVENUE_VALUES,
                                     R.COMPETING_PRIOR_OPERATING_INCOME_VALUES)[index])
                        for o in group:
                            dispositions[o.observation_id] = D.COMPETING
                            notes[o.observation_id].add((R.COMPETING_PRIOR_REVENUE_VALUES,
                                R.COMPETING_PRIOR_OPERATING_INCOME_VALUES)[index].value)
            # Any CURRENT-linked accession must have coherent metadata across
            # every relevant cell, even when it is not a complete presentation.
            for acc in f_accessions:
                if _metadata_conflict([o for o in annual if o.accession == acc
                                       and o.observation_id in relevant_ids]):
                    reasons.add(R.COMMON_FILING_METADATA_CONFLICT)

    # No pair means no PRIOR-dependent reasons or fields. Source/current checks
    # above are independent and retain their precedence.
    if not coherent_current:
        cell_groups[2:] = current_groups
    ordered = tuple(sorted(reasons, key=lambda r: r.value))
    status = _status(ordered)
    established = status is S.COMPARATIVE_ISSUER_REPORTED_FACTS_ESTABLISHED
    support_accessions = {acc for acc, interval in complete if interval == prior}
    support_ids = {o.observation_id for (acc, interval), groups in complete.items()
                   if interval == prior for group in groups for o in group}
    fiscal_vintages = {o.fy for o in target if o.fy is not None}
    historical_accessions = set()
    if current:
        for acc in {o.accession for o in annual if o.accession is not None} - f_accessions:
            history = [o for o in annual if o.accession == acc]
            if all(_date(o.end) and _date(o.end) < endpoint
                   and o.fy is not None and o.fy not in fiscal_vintages for o in history):
                historical_accessions.add(acc)
    for o in rows:
        oid = o.observation_id
        if established and oid in support_ids:
            dispositions[oid] = D.SELECTED
        elif o.accession in historical_accessions and oid in annual_ids:
            dispositions[oid] = D.NONSELECTED
            exclusions[oid].add(X.EXCLUDED_DIFFERENT_FILING_VINTAGE_PRIOR_ONLY)
        elif (complete and oid in target_ids and valid.get(oid) and oid not in support_ids
              and len({v.value for g in complete.values() for v in g[2 + CONCEPTS.index(o.concept)]}) == 1
              and o.value == next(iter(complete.values()))[2 + CONCEPTS.index(o.concept)][0].value
              and not _metadata_conflict([v for v in annual if v.accession == o.accession
                                         and v.observation_id in relevant_ids])):
            dispositions[oid] = D.NONSELECTED
            exclusions[oid].add(X.EXCLUDED_CONSISTENT_PARTIAL_CURRENT)
        elif (oid in relevant_ids and valid.get(oid) and oid not in support_ids
              and dispositions[oid] is D.NONSELECTED):
            dispositions[oid] = D.ORPHAN
        if not notes[oid] and not exclusions[oid] and dispositions[oid] is not D.SELECTED:
            notes[oid].add('NO_COMPLETE_COMPARATIVE_SUPPORT' if oid in relevant_ids
                           else 'OUTSIDE_COMPARATIVE_INTERVAL')
    refs = tuple(ComparativeObservationReference(o, dispositions[o.observation_id],
        tuple(sorted(notes[o.observation_id])),
        tuple(sorted(exclusions[o.observation_id], key=lambda x: x.value)))
        for o in sorted(rows, key=lambda o: o.observation_id))
    filings = []
    for acc in sorted({o.accession for o in rows if o.accession is not None}):
        obs = [o for o in rows if o.accession == acc]
        groups = next((groups for (a, p), groups in complete.items() if a == acc and p == prior), None)
        raw_current = [any(o.concept == c and o.observation_id in target_ids for o in obs) for c in CONCEPTS]
        raw_prior = [any(o.concept == c and o.observation_id in annual_ids
                         and _date(o.end) and _date(o.end) < endpoint for o in obs) for c in CONCEPTS] if endpoint else [False, False]
        population = ('Q' if all(raw_current + raw_prior) else 'F') if acc in f_accessions else (
            'H' if acc in historical_accessions else 'UNLINKED')
        filings.append(ComparativeFiling(acc, population,
            tuple(sorted(o.observation_id for o in obs)),
            tuple(sorted({o.form for o in obs if o.form is not None})),
            tuple(sorted({o.filed for o in obs if o.filed is not None})),
            tuple(sorted({o.fy for o in obs if o.fy is not None})),
            candidates.get(acc, ()), tuple(tuple(sorted(o.observation_id for o in g))
                                          for g in groups) if groups else ((), (), (), ())))
    inventory = _identity(IDENTITY_VERSION + ':extraction-inventory', _jsonable({
        'version': extraction.extraction_version, 'receipt': receipt.receipt_id,
        'object': receipt.content_sha256, 'issues': extraction.issues,
        'observations': tuple(asdict(o) for o in sorted(rows, key=lambda o: o.observation_id)),
    }))
    selected = tuple(tuple(sorted(o.observation_id for o in group if o.observation_id in support_ids))
                     for group in cell_groups) if established else ((), (), (), ())
    values = tuple(group[0].value for group in cell_groups) if established else (None,) * 4
    return CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1(
        status, ordered, receipt.cik, prior[0] if prior else None, prior[1] if prior else None,
        current[0] if current else None, endpoint.isoformat() if endpoint else None,
        *values, receipt.receipt_id, receipt.content_sha256, receipt.byte_length,
        receipt.captured_at, receipt.endpoint, receipt.source_locator, receipt.acquisition_contract_version,
        refs, tuple(filings), tuple(f for f in filings if f.accession in support_accessions) if established else (),
        selected, inventory, extraction.issues, tuple(conflicts),
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
    if type(supplied) is not type(canonical):
        return False
    if type(canonical) is tuple:
        return len(supplied) == len(canonical) and all(
            _same_public_value(a, b) for a, b in zip(supplied, canonical))
    if type(canonical) is Decimal:
        return supplied.is_finite() and supplied.as_tuple() == canonical.as_tuple()
    if type(canonical) in (str, int, type(None)):
        return supplied == canonical
    if type(canonical) in (S, R, D, X):
        return supplied is canonical
    if type(canonical) in (CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1,
            ComparativeObservationReference, ComparativeFiling, RevenueOperatingIncomeObservation):
        return all(_same_public_value(getattr(supplied, f.name), getattr(canonical, f.name))
                   for f in fields(canonical))
    return False


def _verified_comparative_snapshot(qualification):
    """Reconstruct all four cells and surveillance from the original bound bytes."""
    if type(qualification) is not CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1:
        raise ComparativeQualificationError('Exact native comparative qualification required')
    try:
        if any(not _same_public_value(getattr(qualification, key), expected)
               for key, expected in _CONTRACT_SURFACE.items()):
            raise ComparativeQualificationError('Incompatible comparative contract')
        binding = qualification._archive_replay_binding
        if (type(binding) is not _ArchiveReplayBinding or type(binding.archive) is not SecArchive
                or type(binding.receipt_id) is not str
                or binding.receipt_id != qualification.capture_receipt_id):
            raise ComparativeQualificationError('Missing or stale native archive binding')
        replay = qualify_sec_current_annual_issuer_two_period_revenue_operating_income_v1(
            binding.archive, binding.receipt_id)
        if (not _same_public_value(qualification, replay)
                or qualification.semantic_id != replay.semantic_id
                or qualification.evidence_id != replay.evidence_id):
            raise ComparativeQualificationError('Comparative qualification differs from source replay')
        return replay
    except (AttributeError, TypeError, ValueError, ArithmeticError, RecursionError):
        raise ComparativeQualificationError('Native comparative source replay failed') from None
