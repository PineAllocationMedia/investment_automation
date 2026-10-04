"""Bounded Stage-C diagnostic for five-period diluted-EPS direction.

The module consumes one exact, canonical ordinary-compounder profile
qualification.  It is deterministic and read-only: it performs no acquisition,
normalization, forecasting, scoring, ranking, or portfolio action.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum, StrEnum
import hashlib
import json

import economic_facts.sec_ordinary_compounder_profile as upstream


FIVE_PERIOD_EPS_CONSISTENCY_CONTRACT_VERSION = (
    "2026-10-04-five-period-diluted-eps-consistency-v1"
)
FIVE_PERIOD_EPS_CONSISTENCY_METHODOLOGY_VERSION = (
    "2026-10-04-exact-decimal-directional-consistency-v1"
)


class FivePeriodEPSConsistencyError(ValueError):
    """Wrong input type or a contradictory canonical upstream object."""


class FivePeriodEPSConsistencyAnalysisKind(StrEnum):
    FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY = (
        "FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY"
    )


class FivePeriodEPSConsistencyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class FivePeriodEPSDirection(StrEnum):
    INCREASED = "INCREASED"
    UNCHANGED = "UNCHANGED"
    DECREASED = "DECREASED"


class FivePeriodEPSConsistencyAuthority(StrEnum):
    QUALITY_EPS_CONSISTENCY_DIAGNOSTIC_ONLY = (
        "QUALITY_EPS_CONSISTENCY_DIAGNOSTIC_ONLY"
    )


class FivePeriodEPSConsistencyLimitation(StrEnum):
    NO_COMPOSITE_QUALITY_SCORE = "NO_COMPOSITE_QUALITY_SCORE"
    NO_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_SECTOR_COMPARABILITY"
    NO_PROFIT_MARGIN_OR_ROIC_CLAIM = "NO_PROFIT_MARGIN_OR_ROIC_CLAIM"
    NO_CASH_CONVERSION_OR_BALANCE_SHEET_CLAIM = (
        "NO_CASH_CONVERSION_OR_BALANCE_SHEET_CLAIM"
    )
    NO_CAPITAL_ALLOCATION_DILUTION_OR_MOAT_CLAIM = (
        "NO_CAPITAL_ALLOCATION_DILUTION_OR_MOAT_CLAIM"
    )
    NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM = (
        "NO_DURABILITY_OR_FORWARD_PERSISTENCE_CLAIM"
    )
    NO_EXPECTED_RETURN_ADJUSTMENT = "NO_EXPECTED_RETURN_ADJUSTMENT"
    NO_CONFIDENCE_SUBSTITUTION = "NO_CONFIDENCE_SUBSTITUTION"
    NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING = (
        "NO_RECOMMENDATION_RANKING_ALLOCATION_OR_SIZING"
    )
    NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY = (
        "NO_EXECUTION_PRODUCTION_OR_V2_PROMOTION_AUTHORITY"
    )
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_ANALYSIS_KIND = (
    FivePeriodEPSConsistencyAnalysisKind.
    FIVE_PERIOD_DILUTED_EPS_DIRECTIONAL_CONSISTENCY
)
_AUTHORITY = (
    FivePeriodEPSConsistencyAuthority.
    QUALITY_EPS_CONSISTENCY_DIAGNOSTIC_ONLY
)
_LIMITATIONS = tuple(FivePeriodEPSConsistencyLimitation)
_HASH_LENGTH = 64
_COMPARABILITY_CONTRACT_VERSION = (
    "2026-09-28-sec-current-eps-comparability-v1"
)
_COMPARABILITY_QUALIFIER_VERSION = (
    "2026-09-28-positive-five-period-presentation-v1"
)
_COMPARABILITY_QUALIFICATION_MODE = (
    "CURRENT_SEC_SINGLE_PRESENTATION_HISTORICAL_COMPARABILITY"
)


@dataclass(frozen=True, slots=True)
class FivePeriodEPSInterval:
    prior_period_end: str
    current_period_end: str
    prior_diluted_eps: Decimal
    current_diluted_eps: Decimal
    delta_diluted_eps: Decimal
    direction: FivePeriodEPSDirection


@dataclass(frozen=True, slots=True)
class FivePeriodEPSConsistencyResult:
    contract_version: str
    methodology_version: str
    analysis_kind: FivePeriodEPSConsistencyAnalysisKind
    status: FivePeriodEPSConsistencyStatus
    upstream_profile_status: upstream.OrdinaryCompounderProfileStatus
    upstream_profile_reasons: tuple[upstream.ProfileReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    upstream_profile_semantic_id: str
    upstream_profile_evidence_id: str
    upstream_comparability_semantic_id: str
    upstream_comparability_evidence_id: str
    intervals: tuple[FivePeriodEPSInterval, ...]
    increase_count: int | None
    unchanged_count: int | None
    decrease_count: int | None
    authority: FivePeriodEPSConsistencyAuthority
    limitations: tuple[FivePeriodEPSConsistencyLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("five-period-eps-consistency-semantics", {
            "contract_version": self.contract_version,
            "methodology_version": self.methodology_version,
            "analysis_kind": self.analysis_kind,
            "status": self.status,
            "upstream_profile_status": self.upstream_profile_status,
            "upstream_profile_reasons": self.upstream_profile_reasons,
            "route_local_issuer_key": self.route_local_issuer_key,
            "route_local_security_key": self.route_local_security_key,
            "upstream_profile_semantic_id": self.upstream_profile_semantic_id,
            "upstream_comparability_semantic_id":
                self.upstream_comparability_semantic_id,
            "intervals": self.intervals,
            "increase_count": self.increase_count,
            "unchanged_count": self.unchanged_count,
            "decrease_count": self.decrease_count,
            "authority": self.authority,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("five-period-eps-consistency-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_profile_evidence_id": self.upstream_profile_evidence_id,
            "upstream_comparability_evidence_id":
                self.upstream_comparability_evidence_id,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"five_period_eps_consistency": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
    if type(value) is Decimal:
        parts = value.as_tuple()
        return {
            "sign": parts.sign,
            "digits": list(parts.digits),
            "exponent": parts.exponent,
        }
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
    raise FivePeriodEPSConsistencyError(
        "Unsupported EPS-consistency identity value"
    )


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"),
        ensure_ascii=True, allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _is_hash(value) -> bool:
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_profile_shape(
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
) -> upstream.RealEPSComparabilityQualification:
    if (profile.contract_version != upstream.CONTRACT_VERSION
            or profile.qualifier_version != upstream.QUALIFIER_VERSION
            or profile.limitations != upstream.LIMITATIONS):
        raise FivePeriodEPSConsistencyError(
            "Canonical ordinary-compounder profile contract required"
        )
    if type(profile.status) is not upstream.OrdinaryCompounderProfileStatus:
        raise FivePeriodEPSConsistencyError(
            "Unknown ordinary-compounder profile status"
        )
    if (type(profile.reasons) is not tuple
            or any(type(reason) is not upstream.ProfileReason
                   for reason in profile.reasons)):
        raise FivePeriodEPSConsistencyError(
            "Canonical native profile reasons required"
        )
    if (type(profile.decisions) is not tuple
            or any(type(item) is not upstream.MethodProfileDecision
                   for item in profile.decisions)):
        raise FivePeriodEPSConsistencyError(
            "Canonical profile decisions required"
        )
    comparability = profile.upstream_comparability
    if type(comparability) is not upstream.RealEPSComparabilityQualification:
        raise FivePeriodEPSConsistencyError(
            "Canonical embedded comparability qualification required"
        )
    if (comparability.contract_version != _COMPARABILITY_CONTRACT_VERSION
            or comparability.qualifier_version
            != _COMPARABILITY_QUALIFIER_VERSION
            or comparability.qualification_mode
            != _COMPARABILITY_QUALIFICATION_MODE
            or type(comparability.outcome) is not upstream.ComparabilityOutcome
            or type(comparability.reasons) is not tuple):
        raise FivePeriodEPSConsistencyError(
            "Canonical comparability contract required"
        )

    identity_values = (
        profile.semantic_id,
        profile.evidence_id,
        comparability.semantic_id,
        comparability.evidence_id,
    )
    if any(not _is_hash(value) for value in identity_values):
        raise FivePeriodEPSConsistencyError(
            "Canonical upstream identities required"
        )

    issuer_key = comparability.route_local_issuer_key
    security_key = comparability.route_local_security_key
    if any(value is not None and not _is_hash(value)
           for value in (issuer_key, security_key)):
        raise FivePeriodEPSConsistencyError(
            "Malformed route-local identity"
        )
    security = comparability.upstream_security_eps
    if (issuer_key != security.route_local_issuer_key
            or security_key != security.route_local_security_key):
        raise FivePeriodEPSConsistencyError(
            "Profile/comparability route identity mismatch"
        )
    subject = comparability.upstream_reporting_subject_source
    if profile.source_cik != subject.source_cik:
        raise FivePeriodEPSConsistencyError(
            "Profile/comparability issuer linkage mismatch"
        )
    return comparability


def _validate_established_profile(
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
    comparability: upstream.RealEPSComparabilityQualification,
) -> tuple:
    if (profile.profile != upstream.PROFILE
            or profile.reasons != ()
            or type(profile.source_cik) is not str
            or not profile.source_cik
            or type(profile.sic) is not int
            or isinstance(profile.sic, bool)
            or not 100 <= profile.sic <= 9999
            or type(profile.sic_description) is not str
            or not profile.sic_description
            or not _is_hash(profile.metadata_semantic_id)
            or not _is_hash(profile.metadata_evidence_id)):
        raise FivePeriodEPSConsistencyError(
            "Contradictory established ordinary-compounder profile"
        )
    if (len(profile.decisions) != len(upstream.UnsupportedStructure)
            or tuple(item.profile for item in profile.decisions)
            != tuple(upstream.UnsupportedStructure)
            or any(type(item.profile) is not upstream.UnsupportedStructure
                   or type(item.decision) is not upstream.ProfileDecisionValue
                   or item.decision is not upstream.ProfileDecisionValue.EXCLUDED
                   for item in profile.decisions)):
        raise FivePeriodEPSConsistencyError(
            "Established profile must exclude every unsupported structure"
        )
    if (comparability.outcome is not
            upstream.ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
            or comparability.reasons != ()
            or not _is_hash(comparability.route_local_issuer_key)
            or not _is_hash(comparability.route_local_security_key)):
        raise FivePeriodEPSConsistencyError(
            "Established profile requires established comparable EPS"
        )

    periods = comparability.period_decisions
    if (type(periods) is not tuple
            or len(periods) != 5
            or any(not is_dataclass(period) for period in periods)):
        raise FivePeriodEPSConsistencyError(
            "Exactly five canonical period decisions required"
        )
    endpoints = tuple(period.period_end for period in periods)
    if (any(type(endpoint) is not str or not endpoint for endpoint in endpoints)
            or len(set(endpoints)) != 5
            or endpoints != tuple(sorted(endpoints))):
        raise FivePeriodEPSConsistencyError(
            "Period endpoints must be strictly ordered and distinct"
        )
    for period in periods:
        if (not isinstance(period.outcome, Enum)
                or period.outcome.value != "EXACT_MATCH"
                or period.reasons != ()):
            raise FivePeriodEPSConsistencyError(
                "Every period must be an exact comparable match"
            )
        if (type(period.c3_value) is not Decimal
                or not period.c3_value.is_finite()
                or period.c3_value <= 0
                or type(period.presented_value) is not Decimal
                or period.presented_value != period.c3_value):
            raise FivePeriodEPSConsistencyError(
                "Every period requires exact finite canonical diluted EPS"
            )
    return periods


def _capability_status(
    status: upstream.OrdinaryCompounderProfileStatus,
) -> FivePeriodEPSConsistencyStatus:
    mapping = {
        upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED:
            FivePeriodEPSConsistencyStatus.AVAILABLE,
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE:
            FivePeriodEPSConsistencyStatus.UNAVAILABLE,
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED:
            FivePeriodEPSConsistencyStatus.UNSUPPORTED,
        upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
            FivePeriodEPSConsistencyStatus.SOURCE_CONFLICT,
    }
    try:
        return mapping[status]
    except KeyError as exc:
        raise FivePeriodEPSConsistencyError(
            "Unknown ordinary-compounder profile status"
        ) from exc


def analyze_five_period_eps_consistency(
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
) -> FivePeriodEPSConsistencyResult:
    """Describe four exact diluted-EPS transitions for one qualified profile."""
    if type(profile) is not upstream.OrdinaryCompounderMethodProfileQualification:
        raise FivePeriodEPSConsistencyError(
            "Exact OrdinaryCompounderMethodProfileQualification required"
        )
    comparability = _validate_profile_shape(profile)
    status = _capability_status(profile.status)

    intervals = ()
    increase_count = None
    unchanged_count = None
    decrease_count = None
    if status is FivePeriodEPSConsistencyStatus.AVAILABLE:
        periods = _validate_established_profile(profile, comparability)
        built = []
        for prior, current in zip(periods, periods[1:]):
            delta = current.c3_value - prior.c3_value
            if delta > 0:
                direction = FivePeriodEPSDirection.INCREASED
            elif delta == 0:
                direction = FivePeriodEPSDirection.UNCHANGED
            else:
                direction = FivePeriodEPSDirection.DECREASED
            built.append(FivePeriodEPSInterval(
                prior.period_end,
                current.period_end,
                prior.c3_value,
                current.c3_value,
                delta,
                direction,
            ))
        intervals = tuple(built)
        increase_count = sum(
            item.direction is FivePeriodEPSDirection.INCREASED
            for item in intervals
        )
        unchanged_count = sum(
            item.direction is FivePeriodEPSDirection.UNCHANGED
            for item in intervals
        )
        decrease_count = sum(
            item.direction is FivePeriodEPSDirection.DECREASED
            for item in intervals
        )
        if (len(intervals) != 4
                or increase_count + unchanged_count + decrease_count != 4):
            raise FivePeriodEPSConsistencyError(
                "Available result requires exactly four classified intervals"
            )

    return FivePeriodEPSConsistencyResult(
        FIVE_PERIOD_EPS_CONSISTENCY_CONTRACT_VERSION,
        FIVE_PERIOD_EPS_CONSISTENCY_METHODOLOGY_VERSION,
        _ANALYSIS_KIND,
        status,
        profile.status,
        profile.reasons,
        comparability.route_local_issuer_key,
        comparability.route_local_security_key,
        profile.semantic_id,
        profile.evidence_id,
        comparability.semantic_id,
        comparability.evidence_id,
        intervals,
        increase_count,
        unchanged_count,
        decrease_count,
        _AUTHORITY,
        _LIMITATIONS,
    )
