"""Bounded Stage-C diagnostic for one annual diluted-EPS denominator effect.

The module consumes one exact canonical denominator-share qualification and
reports only the exact incremental diluted denominator ratio.  It performs no
acquisition, historical reconstruction, scoring, forecasting, or portfolio
action.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, StrEnum
from math import gcd
import hashlib
import json
import re
import sys


CONTRACT_VERSION = (
    "2026-10-04-current-annual-eps-denominator-dilution-diagnostic-v1"
)
METHODOLOGY_VERSION = (
    "2026-10-04-exact-rational-incremental-denominator-ratio-v1"
)


class CurrentAnnualEPSDenominatorDilutionError(ValueError):
    """Wrong public input type or contradictory canonical upstream object."""


class CurrentAnnualEPSDenominatorDilutionAnalysisKind(StrEnum):
    CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION = (
        "CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION"
    )


class CurrentAnnualEPSDenominatorDilutionStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualEPSDenominatorDilutionAuthority(StrEnum):
    QUALITY_DILUTION_EPS_DENOMINATOR_DIAGNOSTIC_ONLY = (
        "QUALITY_DILUTION_EPS_DENOMINATOR_DIAGNOSTIC_ONLY"
    )


class CurrentAnnualEPSDenominatorDilutionLimitation(StrEnum):
    NO_ACTUAL_SHAREHOLDER_DILUTION_CLAIM = (
        "NO_ACTUAL_SHAREHOLDER_DILUTION_CLAIM"
    )
    NO_SHARES_OUTSTANDING_CHANGE_CLAIM = (
        "NO_SHARES_OUTSTANDING_CHANGE_CLAIM"
    )
    NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM = (
        "NO_PERIOD_END_SHARES_OUTSTANDING_CLAIM"
    )
    NO_SBC_CAUSAL_ATTRIBUTION = "NO_SBC_CAUSAL_ATTRIBUTION"
    NO_OPTION_OR_CONVERTIBLE_CAUSAL_ATTRIBUTION = (
        "NO_OPTION_OR_CONVERTIBLE_CAUSAL_ATTRIBUTION"
    )
    NO_ISSUANCE_CAUSAL_ATTRIBUTION = "NO_ISSUANCE_CAUSAL_ATTRIBUTION"
    NO_REPURCHASE_EFFECTIVENESS_CONCLUSION = (
        "NO_REPURCHASE_EFFECTIVENESS_CONCLUSION"
    )
    NO_CAPITAL_ALLOCATION_QUALITY_CONCLUSION = (
        "NO_CAPITAL_ALLOCATION_QUALITY_CONCLUSION"
    )
    NO_TOTAL_DILUTED_EPS_IMPACT_CLAIM = (
        "NO_TOTAL_DILUTED_EPS_IMPACT_CLAIM"
    )
    NO_HISTORICAL_DILUTION_TREND = "NO_HISTORICAL_DILUTION_TREND"
    NO_CROSS_SECTOR_QUALITY_COMPARABILITY = (
        "NO_CROSS_SECTOR_QUALITY_COMPARABILITY"
    )
    NO_DILUTION_THRESHOLD_GRADE_OR_SCORE = (
        "NO_DILUTION_THRESHOLD_GRADE_OR_SCORE"
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
    CurrentAnnualEPSDenominatorDilutionAnalysisKind.
    CURRENT_ANNUAL_EPS_DENOMINATOR_DILUTION
)
_AUTHORITY = (
    CurrentAnnualEPSDenominatorDilutionAuthority.
    QUALITY_DILUTION_EPS_DENOMINATOR_DIAGNOSTIC_ONLY
)
_LIMITATIONS = tuple(CurrentAnnualEPSDenominatorDilutionLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_UPSTREAM_MODULE_NAME = (
    "economic_facts.sec_current_annual_eps_denominator_shares"
)


@dataclass(frozen=True, slots=True)
class EPSDenominatorDilutionRatio:
    """Canonical reduced nonnegative rational ratio."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if (type(self.numerator) is not int
                or type(self.denominator) is not int
                or self.numerator < 0
                or self.denominator <= 0):
            raise CurrentAnnualEPSDenominatorDilutionError(
                "Canonical nonnegative reduced ratio required"
            )
        divisor = gcd(self.numerator, self.denominator)
        object.__setattr__(self, "numerator", self.numerator // divisor)
        object.__setattr__(self, "denominator", self.denominator // divisor)


@dataclass(frozen=True, slots=True)
class CurrentAnnualEPSDenominatorDilutionResult:
    contract_version: str
    methodology_version: str
    analysis_kind: CurrentAnnualEPSDenominatorDilutionAnalysisKind
    status: CurrentAnnualEPSDenominatorDilutionStatus
    upstream_status: Enum
    upstream_reasons: tuple[Enum, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    upstream_denominator_qualification_semantic_id: str
    upstream_denominator_qualification_evidence_id: str
    incremental_denominator_ratio: EPSDenominatorDilutionRatio | None
    authority: CurrentAnnualEPSDenominatorDilutionAuthority
    limitations: tuple[CurrentAnnualEPSDenominatorDilutionLimitation, ...]

    @property
    def semantic_id(self) -> str:
        return _identity("current-annual-eps-denominator-dilution-semantics", {
            "contract_version": self.contract_version,
            "methodology_version": self.methodology_version,
            "analysis_kind": self.analysis_kind,
            "status": self.status,
            "upstream_status": self.upstream_status,
            "upstream_reasons": self.upstream_reasons,
            "route_local_issuer_key": self.route_local_issuer_key,
            "route_local_security_key": self.route_local_security_key,
            "source_cik": self.source_cik,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "upstream_denominator_qualification_semantic_id":
                self.upstream_denominator_qualification_semantic_id,
            "incremental_denominator_ratio":
                self.incremental_denominator_ratio,
            "authority": self.authority,
            "limitations": self.limitations,
        })

    @property
    def evidence_id(self) -> str:
        return _identity("current-annual-eps-denominator-dilution-evidence", {
            "semantic_id": self.semantic_id,
            "upstream_denominator_qualification_evidence_id":
                self.upstream_denominator_qualification_evidence_id,
        })

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_eps_denominator_dilution": payload}


def _canonical(value):
    if isinstance(value, Enum):
        return value.value
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
    raise CurrentAnnualEPSDenominatorDilutionError(
        "Unsupported dilution-diagnostic identity value"
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


def _valid_optional_hash(value) -> bool:
    return value is None or _is_hash(value)


def _valid_optional_nonempty_string(value) -> bool:
    return value is None or (
        type(value) is str and bool(value) and value == value.strip()
    )


def _valid_optional_timestamp(value) -> bool:
    if value is None:
        return True
    if not _valid_optional_nonempty_string(value):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_period(start, end) -> bool:
    if start is None or end is None:
        return start is None and end is None
    if type(start) is not str or type(end) is not str:
        return False
    try:
        return date.fromisoformat(start) <= date.fromisoformat(end)
    except ValueError:
        return False


def _canonical_upstream_module(qualification):
    qualification_type = type(qualification)
    module = sys.modules.get(qualification_type.__module__)
    if (qualification_type.__module__ != _UPSTREAM_MODULE_NAME
            or module is None
            or getattr(
                module,
                "CurrentAnnualEPSDenominatorSharesQualification",
                None,
            ) is not qualification_type):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Exact CurrentAnnualEPSDenominatorSharesQualification required"
        )
    return module


def _validate_supporting_filing(
    filing,
    upstream,
) -> None:
    if (type(filing) is not upstream.EPSDenominatorSupportingFiling
            or type(filing.accession) is not str
            or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
            or type(filing.forms) is not tuple
            or len(filing.forms) != 1
            or any(type(item) is not str or item not in ("10-K", "10-K/A")
                   for item in filing.forms)
            or filing.forms != tuple(sorted(set(filing.forms)))
            or type(filing.filed_dates) is not tuple
            or len(filing.filed_dates) != 1
            or filing.filed_dates != tuple(sorted(set(filing.filed_dates)))
            or any(not _valid_period(item, item)
                   for item in filing.filed_dates)
            or type(filing.basic_observation_ids) is not tuple
            or not filing.basic_observation_ids
            or filing.basic_observation_ids
            != tuple(sorted(set(filing.basic_observation_ids)))
            or any(not _is_hash(item)
                   for item in filing.basic_observation_ids)
            or type(filing.diluted_observation_ids) is not tuple
            or not filing.diluted_observation_ids
            or filing.diluted_observation_ids
            != tuple(sorted(set(filing.diluted_observation_ids)))
            or any(not _is_hash(item)
                   for item in filing.diluted_observation_ids)):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical established supporting filing required"
        )


def _validate_profile_state_reasons(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    status = qualification.upstream_profile_status
    reasons = qualification.upstream_profile_reasons
    reason = profile_upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical native profile reasons required"
        )
    unavailable_reasons = frozenset({
        reason.PR5C_NOT_ESTABLISHED,
        reason.SIC_MISSING_OR_INVALID,
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID,
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
    })
    decision_derived_reasons = frozenset({
        reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED,
        reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED,
        reason.MIXED_STRUCTURE_UNRESOLVED,
        reason.UNSUPPORTED_SIC_PROFILE,
    })
    if status is (
            profile_upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED):
        coherent = reasons == ()
    elif status is (
            profile_upstream.OrdinaryCompounderProfileStatus.
            PROFILE_UNAVAILABLE):
        coherent = bool(reasons) and set(reasons) <= unavailable_reasons
    elif status is (
            profile_upstream.OrdinaryCompounderProfileStatus.
            PROFILE_UNSUPPORTED):
        coherent = (
            reason.UNSUPPORTED_SIC_PROFILE in reasons
            and reason.REPLAY_IDENTITY_MISMATCH not in reasons
        )
    elif status is profile_upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
        coherent = (
            reason.REPLAY_IDENTITY_MISMATCH in reasons
            and reason.UNSUPPORTED_SIC_PROFILE not in reasons
        )
    else:
        coherent = False
    if (reason.SIC_DESCRIPTION_MISSING_OR_INVALID in reasons
            and set(reasons) & decision_derived_reasons):
        coherent = False
    if (status is
            profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
            and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons):
        coherent = False
    if not coherent:
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical native profile status/reasons required"
        )


def _validate_shape(
    qualification,
    upstream,
) -> None:
    profile_upstream = upstream.upstream
    if (qualification.contract_version != upstream.CONTRACT_VERSION
            or qualification.qualifier_version != upstream.QUALIFIER_VERSION
            or qualification.evidence_kind != upstream.EVIDENCE_KIND
            or qualification.accounting_namespace != upstream.NAMESPACE
            or qualification.accounting_basis != upstream.ACCOUNTING_BASIS
            or qualification.basic_concept != upstream.BASIC_CONCEPT
            or qualification.diluted_concept != upstream.DILUTED_CONCEPT
            or qualification.unit != upstream.REVIEWED_UNIT
            or qualification.authority != upstream.AUTHORITY
            or qualification.limitations != tuple(
                upstream.CurrentAnnualEPSDenominatorSharesLimitation
            )):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical denominator-share qualification contract required"
        )
    if type(qualification.status) is not (
            upstream.CurrentAnnualEPSDenominatorSharesStatus):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Unknown denominator-share qualification status"
        )
    if (type(qualification.reasons) is not tuple
            or any(type(reason) is not
                   upstream.CurrentAnnualEPSDenominatorSharesReason
                   for reason in qualification.reasons)
            or qualification.reasons != tuple(sorted(
                set(qualification.reasons), key=lambda item: item.value
            ))):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical native denominator-share reasons required"
        )
    if (type(qualification.upstream_profile_status) is not
            profile_upstream.OrdinaryCompounderProfileStatus
            or type(qualification.upstream_profile_reasons) is not tuple
            or any(type(reason) is not profile_upstream.ProfileReason
                   for reason in qualification.upstream_profile_reasons)):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical native profile state required"
        )
    _validate_profile_state_reasons(qualification, upstream)
    if (any(not _valid_optional_hash(value) for value in (
            qualification.route_local_issuer_key,
            qualification.route_local_security_key,
            qualification.capture_receipt_id,
            qualification.source_object_hash,
    )) or any(not _is_hash(value) for value in (
            qualification.upstream_profile_semantic_id,
            qualification.upstream_comparability_semantic_id,
            qualification.upstream_profile_evidence_id,
            qualification.upstream_comparability_evidence_id,
    )) or (qualification.source_cik is not None and (
            type(qualification.source_cik) is not str
            or re.fullmatch(r"[0-9]{10}", qualification.source_cik) is None
    )) or not _valid_period(
            qualification.period_start, qualification.period_end
    ) or not _valid_optional_timestamp(
            qualification.captured_at
    ) or not _valid_optional_nonempty_string(
            qualification.capture_source_locator
    )):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical denominator-share identity and route context required"
        )


def _upstream_identities(
    qualification,
) -> tuple[str, str]:
    try:
        semantic_id = qualification.semantic_id
        evidence_id = qualification.evidence_id
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical upstream denominator identities required"
        ) from exc
    if not _is_hash(semantic_id) or not _is_hash(evidence_id):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical upstream denominator identities required"
        )
    return semantic_id, evidence_id


def _validate_established(
    qualification,
    upstream,
) -> tuple[Decimal, Decimal]:
    profile_upstream = upstream.upstream
    basic = qualification.basic_weighted_average_shares
    diluted = qualification.diluted_weighted_average_shares
    if (qualification.reasons != ()
            or qualification.upstream_profile_status is not
            profile_upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
            or qualification.upstream_profile_reasons != ()
            or not _is_hash(qualification.route_local_issuer_key)
            or not _is_hash(qualification.route_local_security_key)
            or qualification.source_cik is None
            or qualification.period_start is None
            or qualification.period_end is None
            or type(basic) is not Decimal
            or not basic.is_finite()
            or basic <= 0
            or type(diluted) is not Decimal
            or not diluted.is_finite()
            or diluted <= 0
            or diluted < basic
            or not _is_hash(qualification.capture_receipt_id)
            or not _is_hash(qualification.source_object_hash)
            or not qualification.captured_at
            or not qualification.capture_source_locator):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Contradictory established denominator-share qualification"
        )

    basic_ids = qualification.selected_basic_observation_ids
    diluted_ids = qualification.selected_diluted_observation_ids
    accessions = qualification.supporting_accessions
    filings = qualification.supporting_filings
    if (type(basic_ids) is not tuple
            or not basic_ids
            or basic_ids != tuple(sorted(set(basic_ids)))
            or any(not _is_hash(item) for item in basic_ids)
            or type(diluted_ids) is not tuple
            or not diluted_ids
            or diluted_ids != tuple(sorted(set(diluted_ids)))
            or any(not _is_hash(item) for item in diluted_ids)
            or type(accessions) is not tuple
            or not accessions
            or accessions != tuple(sorted(set(accessions)))
            or any(type(item) is not str
                   or _ACCESSION_PATTERN.fullmatch(item) is None
                   for item in accessions)
            or type(filings) is not tuple
            or len(filings) != len(accessions)):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical established denominator evidence surfaces required"
        )
    for filing in filings:
        _validate_supporting_filing(filing, upstream)
    flattened_basic_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.basic_observation_ids
    )
    flattened_diluted_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.diluted_observation_ids
    )
    if (tuple(item.accession for item in filings) != accessions
            or set(basic_ids) & set(diluted_ids)
            or len(flattened_basic_ids) != len(set(flattened_basic_ids))
            or len(flattened_diluted_ids) != len(set(flattened_diluted_ids))
            or tuple(sorted(flattened_basic_ids)) != basic_ids
            or tuple(sorted(flattened_diluted_ids)) != diluted_ids):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Coherent established denominator provenance required"
        )
    return basic, diluted


def _validate_non_established(
    qualification,
    upstream,
) -> None:
    if (not qualification.reasons
            or qualification.basic_weighted_average_shares is not None
            or qualification.diluted_weighted_average_shares is not None
            or qualification.selected_basic_observation_ids != ()
            or qualification.selected_diluted_observation_ids != ()
            or qualification.supporting_accessions != ()
            or qualification.supporting_filings != ()):
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical non-established denominator qualification required"
        )
    status = qualification.status
    reasons = qualification.reasons
    reason = upstream.CurrentAnnualEPSDenominatorSharesReason
    upstream_status = upstream.CurrentAnnualEPSDenominatorSharesStatus
    profile_status = upstream.upstream.OrdinaryCompounderProfileStatus
    unavailable_reasons = frozenset({
        reason.UPSTREAM_PROFILE_UNAVAILABLE,
        reason.BASIC_DENOMINATOR_SHARES_UNAVAILABLE,
        reason.DILUTED_DENOMINATOR_SHARES_UNAVAILABLE,
        reason.EXACT_SHARES_UNIT_UNAVAILABLE,
        reason.FINITE_POSITIVE_BASIC_VALUE_UNAVAILABLE,
        reason.FINITE_POSITIVE_DILUTED_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_PERIOD_PRESENTATION_UNAVAILABLE,
        reason.NO_COMMON_ANNUAL_FILING_ACCESSION,
    })
    local_unavailable_reasons = unavailable_reasons - {
        reason.UPSTREAM_PROFILE_UNAVAILABLE
    }
    conflict_reasons = frozenset({
        reason.UPSTREAM_SOURCE_CONFLICT,
        reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,
        reason.CAPTURE_REPLAY_CONFLICT,
        reason.SOURCE_CIK_CONFLICT,
        reason.COMPETING_BASIC_DENOMINATOR_VALUES,
        reason.COMPETING_DILUTED_DENOMINATOR_VALUES,
        reason.COMMON_FILING_METADATA_CONFLICT,
        reason.DILUTED_SHARES_BELOW_BASIC_SHARES,
    })
    local_conflict_reasons = conflict_reasons - {
        reason.UPSTREAM_SOURCE_CONFLICT
    }
    reason_set = set(reasons)
    if status is upstream_status.EVIDENCE_UNAVAILABLE:
        if not reason_set <= unavailable_reasons:
            coherent = False
        elif reason.UPSTREAM_PROFILE_UNAVAILABLE in reason_set:
            coherent = (
                reasons == (reason.UPSTREAM_PROFILE_UNAVAILABLE,)
                and qualification.upstream_profile_status is
                profile_status.PROFILE_UNAVAILABLE
            )
        else:
            coherent = (
                reason_set <= local_unavailable_reasons
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
            )
    elif status is upstream_status.EVIDENCE_UNSUPPORTED:
        coherent = (
            reasons == (reason.UPSTREAM_PROFILE_UNSUPPORTED,)
            and qualification.upstream_profile_status is
            profile_status.PROFILE_UNSUPPORTED
        )
    elif status is upstream_status.SOURCE_CONFLICT:
        if not reason_set <= conflict_reasons:
            coherent = False
        elif reason.UPSTREAM_SOURCE_CONFLICT in reason_set:
            coherent = (
                reasons == (reason.UPSTREAM_SOURCE_CONFLICT,)
                and qualification.upstream_profile_status is
                profile_status.SOURCE_CONFLICT
            )
        else:
            coherent = (
                reason_set <= local_conflict_reasons
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
            )
    else:
        coherent = False
    if not coherent:
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Canonical non-established status/reason/profile path required"
        )


def _capability_status(
    status,
    upstream,
) -> CurrentAnnualEPSDenominatorDilutionStatus:
    mapping = {
        upstream.CurrentAnnualEPSDenominatorSharesStatus.
        PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED:
            CurrentAnnualEPSDenominatorDilutionStatus.AVAILABLE,
        upstream.CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNAVAILABLE:
            CurrentAnnualEPSDenominatorDilutionStatus.UNAVAILABLE,
        upstream.CurrentAnnualEPSDenominatorSharesStatus.EVIDENCE_UNSUPPORTED:
            CurrentAnnualEPSDenominatorDilutionStatus.UNSUPPORTED,
        upstream.CurrentAnnualEPSDenominatorSharesStatus.SOURCE_CONFLICT:
            CurrentAnnualEPSDenominatorDilutionStatus.SOURCE_CONFLICT,
    }
    try:
        return mapping[status]
    except KeyError as exc:
        raise CurrentAnnualEPSDenominatorDilutionError(
            "Unknown denominator-share qualification status"
        ) from exc


def _ratio_from_decimals(
    basic: Decimal,
    diluted: Decimal,
) -> EPSDenominatorDilutionRatio:
    basic_numerator, basic_denominator = basic.as_integer_ratio()
    diluted_numerator, diluted_denominator = diluted.as_integer_ratio()
    numerator = (
        diluted_numerator * basic_denominator
        - basic_numerator * diluted_denominator
    )
    denominator = diluted_denominator * basic_numerator
    divisor = gcd(numerator, denominator)
    return EPSDenominatorDilutionRatio(
        numerator // divisor,
        denominator // divisor,
    )


def analyze_current_annual_eps_denominator_dilution(
    qualification,
) -> CurrentAnnualEPSDenominatorDilutionResult:
    """Report one exact incremental denominator ratio for qualified evidence."""
    upstream = _canonical_upstream_module(qualification)
    _validate_shape(qualification, upstream)
    status = _capability_status(qualification.status, upstream)

    ratio = None
    if status is CurrentAnnualEPSDenominatorDilutionStatus.AVAILABLE:
        basic, diluted = _validate_established(qualification, upstream)
        ratio = _ratio_from_decimals(basic, diluted)
    else:
        _validate_non_established(qualification, upstream)
    upstream_semantic_id, upstream_evidence_id = _upstream_identities(
        qualification
    )

    return CurrentAnnualEPSDenominatorDilutionResult(
        CONTRACT_VERSION,
        METHODOLOGY_VERSION,
        _ANALYSIS_KIND,
        status,
        qualification.status,
        qualification.reasons,
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
        qualification.source_cik,
        qualification.period_start,
        qualification.period_end,
        upstream_semantic_id,
        upstream_evidence_id,
        ratio,
        _AUTHORITY,
        _LIMITATIONS,
    )
