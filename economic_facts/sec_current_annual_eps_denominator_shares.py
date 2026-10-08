"""CURRENT evidence qualification for paired annual EPS denominator shares.

The public boundary is one exact ``SecArchive`` plus one exact canonical
ordinary-compounder profile.  The embedded route selects the issuer, annual
period, Companyfacts receipt, and immutable source object.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json
import re

from .sec_archive import ArchiveError, CaptureReceipt, SecArchive
from .sec_current_eps_comparability_qualification import (
    ComparableEPSPeriodDecision,
    ComparabilityOutcome,
    PeriodOutcome,
    RealEPSComparabilityQualification,
)
from .sec_eps_denominator_shares import (
    BASIC_CONCEPT,
    CONCEPTS,
    DILUTED_CONCEPT,
    EPSDenominatorSharesObservation,
    NAMESPACE,
    REVIEWED_UNIT,
    extract_eps_denominator_shares,
)
from .sec_eps_series import ResolutionStatus
from . import sec_ordinary_compounder_profile as upstream


CONTRACT_VERSION = (
    "2026-10-04-current-annual-eps-denominator-shares-qualification-v1"
)
QUALIFIER_VERSION = (
    "2026-10-04-paired-common-filing-exact-decimal-qualification-v1"
)
EVIDENCE_KIND = "CURRENT_ANNUAL_EPS_DENOMINATOR_SHARES_QUALIFICATION"
ACCOUNTING_BASIS = "US_GAAP"
AUTHORITY = "QUALITY_DILUTION_EPS_DENOMINATOR_EVIDENCE_ONLY"


class CurrentAnnualEPSDenominatorSharesError(ValueError):
    """Wrong public type or contradictory canonical upstream object."""


class CurrentAnnualEPSDenominatorSharesStatus(StrEnum):
    PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED = (
        "PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED"
    )
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualEPSDenominatorSharesReason(StrEnum):
    UPSTREAM_PROFILE_UNAVAILABLE = "UPSTREAM_PROFILE_UNAVAILABLE"
    UPSTREAM_PROFILE_UNSUPPORTED = "UPSTREAM_PROFILE_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    CANONICAL_ROUTE_IDENTITY_CONFLICT = "CANONICAL_ROUTE_IDENTITY_CONFLICT"
    CAPTURE_REPLAY_CONFLICT = "CAPTURE_REPLAY_CONFLICT"
    SOURCE_CIK_CONFLICT = "SOURCE_CIK_CONFLICT"
    BASIC_DENOMINATOR_SHARES_UNAVAILABLE = "BASIC_DENOMINATOR_SHARES_UNAVAILABLE"
    DILUTED_DENOMINATOR_SHARES_UNAVAILABLE = (
        "DILUTED_DENOMINATOR_SHARES_UNAVAILABLE"
    )
    EXACT_SHARES_UNIT_UNAVAILABLE = "EXACT_SHARES_UNIT_UNAVAILABLE"
    FINITE_POSITIVE_BASIC_VALUE_UNAVAILABLE = (
        "FINITE_POSITIVE_BASIC_VALUE_UNAVAILABLE"
    )
    FINITE_POSITIVE_DILUTED_VALUE_UNAVAILABLE = (
        "FINITE_POSITIVE_DILUTED_VALUE_UNAVAILABLE"
    )
    EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE = (
        "EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE"
    )
    NO_COMMON_ANNUAL_FILING_ACCESSION = "NO_COMMON_ANNUAL_FILING_ACCESSION"
    COMPETING_BASIC_DENOMINATOR_VALUES = "COMPETING_BASIC_DENOMINATOR_VALUES"
    COMPETING_DILUTED_DENOMINATOR_VALUES = (
        "COMPETING_DILUTED_DENOMINATOR_VALUES"
    )
    COMMON_FILING_METADATA_CONFLICT = "COMMON_FILING_METADATA_CONFLICT"
    DILUTED_SHARES_BELOW_BASIC_SHARES = "DILUTED_SHARES_BELOW_BASIC_SHARES"


class CurrentAnnualEPSDenominatorSharesLimitation(StrEnum):
    ONLY_US_GAAP_WEIGHTED_AVERAGE_NUMBER_OF_SHARES_OUTSTANDING_BASIC = (
        "ONLY_US_GAAP_WEIGHTED_AVERAGE_NUMBER_OF_SHARES_OUTSTANDING_BASIC"
    )
    ONLY_US_GAAP_WEIGHTED_AVERAGE_NUMBER_OF_DILUTED_SHARES_OUTSTANDING = (
        "ONLY_US_GAAP_WEIGHTED_AVERAGE_NUMBER_OF_DILUTED_SHARES_OUTSTANDING"
    )
    NO_DILUTION_QUALITY_CONCLUSION = "NO_DILUTION_QUALITY_CONCLUSION"
    NO_HISTORICAL_DILUTION_TREND = "NO_HISTORICAL_DILUTION_TREND"
    NO_SBC_CAUSAL_ATTRIBUTION = "NO_SBC_CAUSAL_ATTRIBUTION"
    NO_ISSUANCE_CAUSAL_ATTRIBUTION = "NO_ISSUANCE_CAUSAL_ATTRIBUTION"
    NO_REPURCHASE_EFFECTIVENESS_CONCLUSION = (
        "NO_REPURCHASE_EFFECTIVENESS_CONCLUSION"
    )
    NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM = (
        "NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM"
    )
    NO_CLASS_SPECIFIC_SHARES_OUTSTANDING_CLAIM = (
        "NO_CLASS_SPECIFIC_SHARES_OUTSTANDING_CLAIM"
    )
    NO_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_SECTOR_COMPARABILITY"
    NO_EXPECTED_RETURN_EFFECT = "NO_EXPECTED_RETURN_EFFECT"
    NO_DURABILITY_CONCLUSION = "NO_DURABILITY_CONCLUSION"
    NO_CONFIDENCE_CONCLUSION = "NO_CONFIDENCE_CONCLUSION"
    NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING = (
        "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING"
    )
    NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY = (
        "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_LIMITATIONS = tuple(CurrentAnnualEPSDenominatorSharesLimitation)
_HASH_LENGTH = 64
_COMPARABILITY_CONTRACT_VERSION = (
    "2026-09-28-sec-current-eps-comparability-v1"
)
_COMPARABILITY_QUALIFIER_VERSION = (
    "2026-09-28-positive-five-period-presentation-v1"
)
_COMPARABILITY_MODE = "CURRENT_SEC_SINGLE_PRESENTATION_HISTORICAL_COMPARABILITY"


@dataclass(frozen=True, slots=True)
class EPSDenominatorSupportingFiling:
    accession: str
    forms: tuple[str, ...]
    filed_dates: tuple[str, ...]
    basic_observation_ids: tuple[str, ...]
    diluted_observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurrentAnnualEPSDenominatorSharesQualification:
    contract_version: str
    qualifier_version: str
    evidence_kind: str
    status: CurrentAnnualEPSDenominatorSharesStatus
    reasons: tuple[CurrentAnnualEPSDenominatorSharesReason, ...]
    upstream_profile_status: upstream.OrdinaryCompounderProfileStatus
    upstream_profile_reasons: tuple[upstream.ProfileReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    accounting_namespace: str
    accounting_basis: str
    basic_concept: str
    diluted_concept: str
    unit: str
    basic_weighted_average_shares: Decimal | None
    diluted_weighted_average_shares: Decimal | None
    upstream_profile_semantic_id: str
    upstream_comparability_semantic_id: str
    upstream_profile_evidence_id: str
    upstream_comparability_evidence_id: str
    capture_receipt_id: str | None
    source_object_hash: str | None
    captured_at: str | None
    capture_source_locator: str | None
    selected_basic_observation_ids: tuple[str, ...]
    selected_diluted_observation_ids: tuple[str, ...]
    supporting_accessions: tuple[str, ...]
    supporting_filings: tuple[EPSDenominatorSupportingFiling, ...]
    authority: str
    limitations: tuple[CurrentAnnualEPSDenominatorSharesLimitation, ...]

    @property
    def semantic_id(self):
        return _identity("current-annual-eps-denominator-shares-semantics", {
            "contract_version": self.contract_version,
            "qualifier_version": self.qualifier_version,
            "evidence_kind": self.evidence_kind,
            "status": self.status,
            "reasons": self.reasons,
            "upstream_profile_status": self.upstream_profile_status,
            "upstream_profile_reasons": self.upstream_profile_reasons,
            "route_local_issuer_key": self.route_local_issuer_key,
            "route_local_security_key": self.route_local_security_key,
            "source_cik": self.source_cik,
            "upstream_profile_semantic_id": self.upstream_profile_semantic_id,
            "upstream_comparability_semantic_id":
                self.upstream_comparability_semantic_id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "accounting_namespace": self.accounting_namespace,
            "accounting_basis": self.accounting_basis,
            "basic_concept": self.basic_concept,
            "diluted_concept": self.diluted_concept,
            "unit": self.unit,
            "basic_weighted_average_shares":
                self.basic_weighted_average_shares,
            "diluted_weighted_average_shares":
                self.diluted_weighted_average_shares,
            "authority": self.authority,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self):
        return _identity("current-annual-eps-denominator-shares-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_profile_evidence_id": self.upstream_profile_evidence_id,
            "upstream_comparability_evidence_id":
                self.upstream_comparability_evidence_id,
            "capture_receipt_id": self.capture_receipt_id,
            "source_object_hash": self.source_object_hash,
            "captured_at": self.captured_at,
            "capture_source_locator": self.capture_source_locator,
            "selected_basic_observation_ids":
                self.selected_basic_observation_ids,
            "selected_diluted_observation_ids":
                self.selected_diluted_observation_ids,
            "supporting_accessions": self.supporting_accessions,
            "supporting_filings": self.supporting_filings,
        })

    def to_dict(self):
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_eps_denominator_shares": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        return _canonical_decimal(value)
    if is_dataclass(value):
        return {
            field.name: _canonical(getattr(value, field.name))
            for field in fields(value)
        }
    if type(value) in (tuple, list):
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {key: _canonical(value[key]) for key in sorted(value)}
    if value is None or type(value) in (str, int, bool):
        return value
    raise CurrentAnnualEPSDenominatorSharesError(
        "Unsupported denominator-share identity value"
    )


def _canonical_decimal(value):
    """Project equal finite base-ten values identically without rounding."""
    if not value.is_finite():
        raise CurrentAnnualEPSDenominatorSharesError(
            "Finite Decimal identity value required"
        )
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    if not any(digits):
        return {"sign": 0, "digits": [0], "exponent": 0}
    if exponent > 0:
        digits.extend([0] * exponent)
        exponent = 0
    while exponent < 0 and digits[-1] == 0:
        digits.pop()
        exponent += 1
    return {"sign": sign, "digits": digits, "exponent": exponent}


def _identity(domain, value):
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _is_hash(value):
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _ordered_reasons(reasons):
    return tuple(sorted(set(reasons), key=lambda item: item.value))


def _validate_profile_shape(profile):
    if (
        profile.contract_version != upstream.CONTRACT_VERSION
        or profile.qualifier_version != upstream.QUALIFIER_VERSION
        or profile.limitations != upstream.LIMITATIONS
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical ordinary-compounder profile contract required"
        )
    if type(profile.status) is not upstream.OrdinaryCompounderProfileStatus:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Unknown ordinary-compounder profile state"
        )
    if (
        type(profile.reasons) is not tuple
        or any(type(reason) is not upstream.ProfileReason for reason in profile.reasons)
        or type(profile.decisions) is not tuple
        or any(type(item) is not upstream.MethodProfileDecision
               for item in profile.decisions)
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical ordinary-compounder profile details required"
        )
    comparability = profile.upstream_comparability
    if type(comparability) is not RealEPSComparabilityQualification:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical embedded comparability required"
        )
    if (
        comparability.contract_version != _COMPARABILITY_CONTRACT_VERSION
        or comparability.qualifier_version != _COMPARABILITY_QUALIFIER_VERSION
        or comparability.qualification_mode != _COMPARABILITY_MODE
        or type(comparability.outcome) is not ComparabilityOutcome
        or type(comparability.reasons) is not tuple
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical comparability contract required"
        )
    if (
        not _is_hash(profile.expected_comparability_semantic_id)
        or not _is_hash(profile.expected_comparability_evidence_id)
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical expected comparability replay identities required"
        )
    replay_mismatch = (
        profile.expected_comparability_semantic_id != comparability.semantic_id
        or profile.expected_comparability_evidence_id != comparability.evidence_id
    )
    replay_reason_present = (
        upstream.ProfileReason.REPLAY_IDENTITY_MISMATCH in profile.reasons
    )
    if replay_mismatch != replay_reason_present:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Authenticated comparability replay mismatch required"
        )
    if any(not _is_hash(value) for value in (
        profile.semantic_id,
        profile.evidence_id,
        comparability.semantic_id,
        comparability.evidence_id,
    )):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical upstream identities required"
        )
    return comparability


def _validate_established_profile(profile, comparability):
    security = comparability.upstream_security_eps
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    if (
        profile.profile != upstream.PROFILE
        or profile.reasons != ()
        or type(profile.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", profile.source_cik) is None
        or profile.source_cik != subject_cik
        or type(profile.sic) is not int
        or not 100 <= profile.sic <= 9999
        or type(profile.sic_description) is not str
        or not profile.sic_description
        or profile.sic_description != profile.sic_description.strip()
        or not _is_hash(profile.metadata_semantic_id)
        or not _is_hash(profile.metadata_evidence_id)
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Contradictory established ordinary-compounder profile"
        )
    if (
        len(profile.decisions) != len(upstream.UnsupportedStructure)
        or any(
            type(item) is not upstream.MethodProfileDecision
            or type(item.profile) is not upstream.UnsupportedStructure
            or item.profile is not expected
            or type(item.decision) is not upstream.ProfileDecisionValue
            or item.decision is not upstream.ProfileDecisionValue.EXCLUDED
            for item, expected in zip(
                profile.decisions, tuple(upstream.UnsupportedStructure), strict=True
            )
        )
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Established profile requires the canonical excluded decision inventory"
        )
    if (
        comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
        or comparability.reasons != ()
        or not _is_hash(comparability.route_local_issuer_key)
        or not _is_hash(comparability.route_local_security_key)
        or comparability.route_local_issuer_key != security.route_local_issuer_key
        or comparability.route_local_security_key != security.route_local_security_key
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Established profile requires canonical established comparability"
        )


def _target_period(comparability, *, require_established):
    periods = comparability.period_decisions
    if (
        type(periods) is not tuple
        or any(type(item) is not ComparableEPSPeriodDecision for item in periods)
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical comparable periods required"
        )
    if not periods:
        if require_established:
            raise CurrentAnnualEPSDenominatorSharesError(
                "Established profile requires comparable annual periods"
            )
        return None, None
    try:
        period_dates = tuple(
            (date.fromisoformat(item.period_start), date.fromisoformat(item.period_end))
            for item in periods
        )
    except (TypeError, ValueError) as exc:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical annual period dates required"
        ) from exc
    ordered = tuple(sorted(periods, key=lambda item: item.period_end))
    if require_established and (
        comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
        or comparability.reasons != ()
        or len(ordered) != 5
        or ordered != periods
        or len({item.period_end for item in periods}) != 5
        or any(
            prior_start >= current_start or prior_end >= current_end
            for (prior_start, prior_end), (current_start, current_end)
            in zip(period_dates, period_dates[1:])
        )
        or any(
            item.outcome is not PeriodOutcome.EXACT_MATCH
            or item.reasons != ()
            or type(item.c3_value) is not Decimal
            or not item.c3_value.is_finite()
            or item.c3_value <= 0
            or type(item.presented_value) is not Decimal
            or item.presented_value != item.c3_value
            for item in ordered
        )
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Contradictory established comparability"
        )
    latest = ordered[-1]
    start, end = period_dates[-1]
    if start > end:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Canonical annual period order required"
        )
    return start.isoformat(), end.isoformat()


def _route_context(profile, comparability):
    security = comparability.upstream_security_eps
    issuer_key = comparability.route_local_issuer_key
    security_key = comparability.route_local_security_key
    conflict = False
    if (
        issuer_key != security.route_local_issuer_key
        or security_key != security.route_local_security_key
        or any(value is not None and not _is_hash(value)
               for value in (issuer_key, security_key))
    ):
        conflict = True
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    if profile.source_cik != subject_cik:
        conflict = True
    try:
        current = (
            security.upstream_registered_listing_bridge.temporal_boundary
            .current_evidence
        )
        receipt = current.receipt
    except AttributeError:
        return issuer_key, security_key, subject_cik, None, True
    if receipt is not None and type(receipt) is not CaptureReceipt:
        conflict = True
        receipt = None
    if receipt is not None:
        series = current.resolution.series
        if (
            subject_cik != receipt.cik
            or current.request.cik != receipt.cik
            or current.request.receipt_id != receipt.receipt_id
            or current.resolution.status is not ResolutionStatus.RESOLVED_ISSUER_EVIDENCE
            or series is None
            or series.cik != receipt.cik
            or series.receipt_ids != (receipt.receipt_id,)
            or series.object_hashes != (receipt.content_sha256,)
        ):
            conflict = True
    return issuer_key, security_key, subject_cik, receipt, conflict


def _result(
    profile,
    comparability,
    *,
    status,
    reasons,
    period_start,
    period_end,
    source_cik,
    receipt=None,
    basic=None,
    diluted=None,
    basic_ids=(),
    diluted_ids=(),
    accessions=(),
    filings=(),
):
    if status is not (
        CurrentAnnualEPSDenominatorSharesStatus.
        PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED
    ):
        basic = None
        diluted = None
        basic_ids = ()
        diluted_ids = ()
        accessions = ()
        filings = ()
    return CurrentAnnualEPSDenominatorSharesQualification(
        CONTRACT_VERSION,
        QUALIFIER_VERSION,
        EVIDENCE_KIND,
        status,
        _ordered_reasons(reasons),
        profile.status,
        profile.reasons,
        comparability.route_local_issuer_key,
        comparability.route_local_security_key,
        source_cik,
        period_start,
        period_end,
        NAMESPACE,
        ACCOUNTING_BASIS,
        BASIC_CONCEPT,
        DILUTED_CONCEPT,
        REVIEWED_UNIT,
        basic,
        diluted,
        profile.semantic_id,
        comparability.semantic_id,
        profile.evidence_id,
        comparability.evidence_id,
        None if receipt is None else receipt.receipt_id,
        None if receipt is None else receipt.content_sha256,
        None if receipt is None else receipt.captured_at,
        None if receipt is None else receipt.source_locator,
        tuple(basic_ids),
        tuple(diluted_ids),
        tuple(accessions),
        tuple(filings),
        AUTHORITY,
        _LIMITATIONS,
    )


def _upstream_status(profile):
    mapping = {
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE: (
            CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE,
            CurrentAnnualEPSDenominatorSharesReason.UPSTREAM_PROFILE_UNAVAILABLE,
        ),
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
            CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNSUPPORTED,
            CurrentAnnualEPSDenominatorSharesReason.UPSTREAM_PROFILE_UNSUPPORTED,
        ),
        upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
            CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            CurrentAnnualEPSDenominatorSharesReason.UPSTREAM_SOURCE_CONFLICT,
        ),
    }
    return mapping.get(profile.status)


def _eligible(observation, *, concept, cik, period_start, period_end):
    return (
        type(observation) is EPSDenominatorSharesObservation
        and observation.source_cik == cik
        and observation.namespace == NAMESPACE
        and observation.concept == concept
        and observation.unit == REVIEWED_UNIT
        and type(observation.value) is Decimal
        and observation.value.is_finite()
        and observation.value > 0
        and observation.start == period_start
        and observation.end == period_end
        and type(observation.fy) is int
        and observation.fp == "FY"
        and observation.form in ("10-K", "10-K/A")
        and type(observation.filed) is str
        and bool(observation.filed)
        and type(observation.accession) is str
        and bool(observation.accession)
        and observation.metadata_limitations == ()
    )


def _supporting_filings(basic_rows, diluted_rows, accessions):
    result = []
    for accession in accessions:
        basic = tuple(row for row in basic_rows if row.accession == accession)
        diluted = tuple(row for row in diluted_rows if row.accession == accession)
        rows = basic + diluted
        result.append(EPSDenominatorSupportingFiling(
            accession,
            tuple(sorted({row.form for row in rows})),
            tuple(sorted({row.filed for row in rows})),
            tuple(sorted(row.observation_id for row in basic)),
            tuple(sorted(row.observation_id for row in diluted)),
        ))
    return tuple(result)


def qualify_sec_current_annual_eps_denominator_shares(
    archive: SecArchive,
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
) -> CurrentAnnualEPSDenominatorSharesQualification:
    """Qualify one exact annual basic/diluted denominator-share pair."""
    if (
        type(archive) is not SecArchive
        or type(profile) is not upstream.OrdinaryCompounderMethodProfileQualification
    ):
        raise CurrentAnnualEPSDenominatorSharesError(
            "Exact SecArchive and OrdinaryCompounderMethodProfileQualification required"
        )
    comparability = _validate_profile_shape(profile)
    established = (
        profile.status is upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    )
    if established:
        _validate_established_profile(profile, comparability)
    period_start, period_end = _target_period(
        comparability, require_established=established
    )
    issuer_key, security_key, source_cik, receipt, route_conflict = _route_context(
        profile, comparability
    )

    mapped = _upstream_status(profile)
    if mapped is not None:
        status, reason = mapped
        return _result(
            profile,
            comparability,
            status=status,
            reasons=(reason,),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )
    if not established:
        raise CurrentAnnualEPSDenominatorSharesError(
            "Unknown ordinary-compounder profile state"
        )
    if route_conflict or receipt is None or issuer_key is None or security_key is None:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualEPSDenominatorSharesReason.
                CANONICAL_ROUTE_IDENTITY_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    try:
        stored = archive.read_receipt(receipt.receipt_id)
        if stored != receipt:
            raise ArchiveError("Embedded receipt differs from archive receipt")
        raw = archive.read_object(stored)
        extraction = extract_eps_denominator_shares(raw, stored)
    except (ArchiveError, OSError):
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualEPSDenominatorSharesReason.CAPTURE_REPLAY_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )
    if extraction.source_cik != source_cik:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=(CurrentAnnualEPSDenominatorSharesReason.SOURCE_CIK_CONFLICT,),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    all_basic = tuple(
        row for row in extraction.observations if row.concept == BASIC_CONCEPT
    )
    all_diluted = tuple(
        row for row in extraction.observations if row.concept == DILUTED_CONCEPT
    )
    basic_rows = tuple(
        row for row in all_basic
        if _eligible(
            row,
            concept=BASIC_CONCEPT,
            cik=source_cik,
            period_start=period_start,
            period_end=period_end,
        )
    )
    diluted_rows = tuple(
        row for row in all_diluted
        if _eligible(
            row,
            concept=DILUTED_CONCEPT,
            cik=source_cik,
            period_start=period_start,
            period_end=period_end,
        )
    )

    unavailable = []
    if not all_basic:
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.
            BASIC_DENOMINATOR_SHARES_UNAVAILABLE
        )
    if not all_diluted:
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.
            DILUTED_DENOMINATOR_SHARES_UNAVAILABLE
        )
    if (all_basic or all_diluted) and not any(
        row.unit == REVIEWED_UNIT for row in all_basic + all_diluted
    ):
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.EXACT_SHARES_UNIT_UNAVAILABLE
        )
    if all_basic and not any(
        type(row.value) is Decimal and row.value.is_finite() and row.value > 0
        for row in all_basic
    ):
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.
            FINITE_POSITIVE_BASIC_VALUE_UNAVAILABLE
        )
    if all_diluted and not any(
        type(row.value) is Decimal and row.value.is_finite() and row.value > 0
        for row in all_diluted
    ):
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.
            FINITE_POSITIVE_DILUTED_VALUE_UNAVAILABLE
        )
    if (all_basic and not basic_rows) or (all_diluted and not diluted_rows):
        unavailable.append(
            CurrentAnnualEPSDenominatorSharesReason.
            EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE
        )
    if unavailable:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE,
            reasons=unavailable,
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    common = tuple(sorted(
        {row.accession for row in basic_rows}
        & {row.accession for row in diluted_rows}
    ))
    if not common:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE,
            reasons=(
                CurrentAnnualEPSDenominatorSharesReason.
                NO_COMMON_ANNUAL_FILING_ACCESSION,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    paired_basic_rows = tuple(
        row for row in basic_rows if row.accession in common
    )
    paired_diluted_rows = tuple(
        row for row in diluted_rows if row.accession in common
    )
    metadata_conflict = any(
        len({getattr(row, field) for row in paired_basic_rows + paired_diluted_rows
             if row.accession == accession}) != 1
        for accession in common
        for field in ("form", "filed", "fy")
    )
    if metadata_conflict:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualEPSDenominatorSharesReason.
                COMMON_FILING_METADATA_CONFLICT,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    conflicts = []
    basic_values = {row.value for row in paired_basic_rows}
    diluted_values = {row.value for row in paired_diluted_rows}
    if len(basic_values) > 1:
        conflicts.append(
            CurrentAnnualEPSDenominatorSharesReason.
            COMPETING_BASIC_DENOMINATOR_VALUES
        )
    if len(diluted_values) > 1:
        conflicts.append(
            CurrentAnnualEPSDenominatorSharesReason.
            COMPETING_DILUTED_DENOMINATOR_VALUES
        )
    if conflicts:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=conflicts,
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    basic = next(iter(basic_values))
    diluted = next(iter(diluted_values))
    if diluted < basic:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualEPSDenominatorSharesReason.
                DILUTED_SHARES_BELOW_BASIC_SHARES,
            ),
            period_start=period_start,
            period_end=period_end,
            source_cik=source_cik,
            receipt=receipt,
        )

    selected_basic = tuple(
        row for row in paired_basic_rows if row.value == basic
    )
    selected_diluted = tuple(
        row for row in paired_diluted_rows if row.value == diluted
    )
    filings = _supporting_filings(selected_basic, selected_diluted, common)
    return _result(
        profile,
        comparability,
        status=(
            CurrentAnnualEPSDenominatorSharesStatus.
            PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED
        ),
        reasons=(),
        period_start=period_start,
        period_end=period_end,
        source_cik=source_cik,
        receipt=receipt,
        basic=basic,
        diluted=diluted,
        basic_ids=tuple(sorted(row.observation_id for row in selected_basic)),
        diluted_ids=tuple(sorted(row.observation_id for row in selected_diluted)),
        accessions=common,
        filings=filings,
    )
