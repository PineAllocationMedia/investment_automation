"""Bounded Stage-C diagnostic for liabilities relative to positive assets.

The module consumes one exact canonical paired liabilities/assets qualification and
reports only the exact signed liabilities / assets relationship when assets is
strictly positive.  It performs no acquisition, requalification, scoring,
forecasting, or downstream action.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from math import gcd
import hashlib
import json
import re
import sys


CONTRACT_VERSION = (
    "2026-10-09-current-annual-liabilities-to-positive-assets-diagnostic-v1"
)
METHODOLOGY_VERSION = (
    "2026-10-09-exact-rational-liabilities-per-positive-assets-v1"
)


class CurrentAnnualLiabilitiesToPositiveAssetsError(ValueError):
    """Wrong public input type or contradictory canonical upstream object."""


class CurrentAnnualLiabilitiesToPositiveAssetsAnalysisKind(StrEnum):
    CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS = (
        "CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS"
    )


class CurrentAnnualLiabilitiesToPositiveAssetsStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualLiabilitiesToPositiveAssetsReason(StrEnum):
    UPSTREAM_EVIDENCE_UNAVAILABLE = "UPSTREAM_EVIDENCE_UNAVAILABLE"
    UPSTREAM_EVIDENCE_UNSUPPORTED = "UPSTREAM_EVIDENCE_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    ASSETS_ZERO_DENOMINATOR = "ASSETS_ZERO_DENOMINATOR"
    ASSETS_NEGATIVE_NOT_POSITIVE_DENOMINATOR = (
        "ASSETS_NEGATIVE_NOT_POSITIVE_DENOMINATOR"
    )


class CurrentAnnualLiabilitiesToPositiveAssetsAuthority(StrEnum):
    QUALITY_CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS_DIAGNOSTIC_ONLY = (
        "QUALITY_CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS_DIAGNOSTIC_ONLY"
    )


class CurrentAnnualLiabilitiesToPositiveAssetsLimitation(StrEnum):
    ONLY_QUALIFIED_REPORTED_ASSETS_CONCEPT = (
        "ONLY_QUALIFIED_REPORTED_ASSETS_CONCEPT"
    )
    ONLY_QUALIFIED_REPORTED_LIABILITIES_CONCEPT = (
        "ONLY_QUALIFIED_REPORTED_LIABILITIES_CONCEPT"
    )
    ONLY_POSITIVE_ASSETS_DENOMINATOR = "ONLY_POSITIVE_ASSETS_DENOMINATOR"
    PRESERVES_SIGNED_REPORTED_LIABILITIES_WITHOUT_JUDGMENT = (
        "PRESERVES_SIGNED_REPORTED_LIABILITIES_WITHOUT_JUDGMENT"
    )
    NO_LIABILITIES_AS_INTEREST_BEARING_DEBT = (
        "NO_LIABILITIES_AS_INTEREST_BEARING_DEBT"
    )
    NO_ASSETS_AS_INVESTED_CAPITAL = "NO_ASSETS_AS_INVESTED_CAPITAL"
    NO_DEBT_ASSETS = "NO_DEBT_ASSETS"
    NO_DEBT_EQUITY = "NO_DEBT_EQUITY"
    NO_NET_DEBT = "NO_NET_DEBT"
    NO_LEVERAGE_CONCLUSION = "NO_LEVERAGE_CONCLUSION"
    NO_LIQUIDITY_CONCLUSION = "NO_LIQUIDITY_CONCLUSION"
    NO_SOLVENCY_CONCLUSION = "NO_SOLVENCY_CONCLUSION"
    NO_BALANCE_SHEET_STRENGTH = "NO_BALANCE_SHEET_STRENGTH"
    NO_CAPITAL_ALLOCATION_CONCLUSION = "NO_CAPITAL_ALLOCATION_CONCLUSION"
    NO_HISTORICAL_TREND = "NO_HISTORICAL_TREND"
    NO_DURABILITY_OR_PERSISTENCE = "NO_DURABILITY_OR_PERSISTENCE"
    NO_ROIC = "NO_ROIC"
    NO_ROE = "NO_ROE"
    NO_ROA = "NO_ROA"
    NO_CROSS_ISSUER_COMPARABILITY = "NO_CROSS_ISSUER_COMPARABILITY"
    NO_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_SECTOR_COMPARABILITY"
    NO_AGGREGATE_QUALITY_SCORE = "NO_AGGREGATE_QUALITY_SCORE"
    NO_QUALITY_GRADE = "NO_QUALITY_GRADE"
    NO_WEIGHTING = "NO_WEIGHTING"
    NO_RANKING = "NO_RANKING"
    NO_EXPECTED_RETURN_CHANGE = "NO_EXPECTED_RETURN_CHANGE"
    NO_CONFIDENCE_CHANGE = "NO_CONFIDENCE_CHANGE"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"
    NO_ALLOCATION = "NO_ALLOCATION"
    NO_SIZING = "NO_SIZING"
    NO_EXECUTION = "NO_EXECUTION"
    NO_PRODUCTION = "NO_PRODUCTION"
    NO_DEPLOYMENT = "NO_DEPLOYMENT"
    NO_V2_PROMOTION = "NO_V2_PROMOTION"
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = (
        "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"
    )


_ANALYSIS_KIND = (
    CurrentAnnualLiabilitiesToPositiveAssetsAnalysisKind.
    CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS
)
_AUTHORITY = (
    CurrentAnnualLiabilitiesToPositiveAssetsAuthority.
    QUALITY_CURRENT_ANNUAL_LIABILITIES_TO_POSITIVE_ASSETS_DIAGNOSTIC_ONLY
)
_LIMITATIONS = tuple(CurrentAnnualLiabilitiesToPositiveAssetsLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_UPSTREAM_MODULE_NAME = (
    "economic_facts.sec_current_annual_assets_liabilities"
)


@dataclass(frozen=True, slots=True)
class LiabilitiesToAssetsRatio:
    """Canonical reduced signed rational liabilities-to-assets relationship."""

    numerator: int
    denominator: int

    def __post_init__(self) -> None:
        if type(self.numerator) is not int or type(self.denominator) is not int:
            raise CurrentAnnualLiabilitiesToPositiveAssetsError(
                "Canonical integer ratio required"
            )
        if self.denominator == 0:
            raise CurrentAnnualLiabilitiesToPositiveAssetsError(
                "Canonical nonzero ratio denominator required"
            )
        numerator = self.numerator
        denominator = self.denominator
        if denominator < 0:
            numerator = -numerator
            denominator = -denominator
        divisor = gcd(numerator, denominator)
        object.__setattr__(self, "numerator", numerator // divisor)
        object.__setattr__(self, "denominator", denominator // divisor)


class _StableAnalyticalInputCarrier:
    __slots__ = ("_analytical_input_semantic_fingerprint",)


class _RouteContextState(StrEnum):
    ROUTE_CONTEXT_PRESENT = "ROUTE_CONTEXT_PRESENT"
    ROUTE_CONTEXT_ABSENT = "ROUTE_CONTEXT_ABSENT"


@dataclass(frozen=True, slots=True)
class CurrentAnnualLiabilitiesToPositiveAssetsResult(
    _StableAnalyticalInputCarrier
):
    contract_version: str
    methodology_version: str
    analysis_kind: CurrentAnnualLiabilitiesToPositiveAssetsAnalysisKind
    status: CurrentAnnualLiabilitiesToPositiveAssetsStatus
    reasons: tuple[CurrentAnnualLiabilitiesToPositiveAssetsReason, ...]
    upstream_status: Enum
    upstream_reasons: tuple[Enum, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_end: str | None
    upstream_qualification_semantic_id: str
    upstream_qualification_evidence_id: str
    liabilities_to_assets_ratio: (
        LiabilitiesToAssetsRatio | None
    )
    authority: CurrentAnnualLiabilitiesToPositiveAssetsAuthority
    limitations: tuple[CurrentAnnualLiabilitiesToPositiveAssetsLimitation, ...]

    @property
    def semantic_id(self) -> str:
        try:
            analytical_input_semantic_fingerprint = (
                self._analytical_input_semantic_fingerprint
            )
        except AttributeError as exc:
            raise CurrentAnnualLiabilitiesToPositiveAssetsError(
                "Stable analytical-input semantics required"
            ) from exc
        if not _is_hash(analytical_input_semantic_fingerprint):
            raise CurrentAnnualLiabilitiesToPositiveAssetsError(
                "Canonical analytical-input semantic fingerprint required"
            )
        return _identity(
            "current-annual-liabilities-to-positive-assets-semantics",
            {
                "contract_version": self.contract_version,
                "methodology_version": self.methodology_version,
                "analysis_kind": self.analysis_kind,
                "status": self.status,
                "reasons": self.reasons,
                "upstream_status": self.upstream_status,
                "upstream_reasons": self.upstream_reasons,
                "source_cik": self.source_cik,
                "period_end": self.period_end,
                "analytical_input_semantic_fingerprint": (
                    analytical_input_semantic_fingerprint
                ),
                "liabilities_to_assets_ratio": (
                    self.liabilities_to_assets_ratio
                ),
                "authority": self.authority,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self) -> str:
        return _identity(
            "current-annual-liabilities-to-positive-assets-evidence",
            {
                "semantic_id": self.semantic_id,
                "upstream_qualification_evidence_id": (
                    self.upstream_qualification_evidence_id
                ),
            },
        )

    def to_dict(self) -> dict:
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_liabilities_to_positive_assets": payload}


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
    raise CurrentAnnualLiabilitiesToPositiveAssetsError(
        "Unsupported liabilities-to-assets diagnostic identity value"
    )


def _identity(domain: str, value) -> str:
    payload = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return hashlib.sha256((domain + "\0" + payload).encode("utf-8")).hexdigest()


def _exact_decimal_semantics(value: Decimal | None):
    if value is None:
        return None
    if type(value) is not Decimal or not value.is_finite():
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Exact finite analytical Decimal required"
        )
    numerator, denominator = value.as_integer_ratio()
    return {"numerator": numerator, "denominator": denominator}


def _route_context_state(qualification) -> _RouteContextState:
    route_values = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    if all(value is None for value in route_values):
        return _RouteContextState.ROUTE_CONTEXT_ABSENT
    if all(_is_hash(value) for value in route_values):
        return _RouteContextState.ROUTE_CONTEXT_PRESENT
    raise CurrentAnnualLiabilitiesToPositiveAssetsError(
        "Canonical paired route context required"
    )


def _analytical_input_semantic_fingerprint(
    qualification,
    *,
    status,
    reasons,
) -> str:
    return _identity(
        "current-annual-liabilities-to-positive-assets-input-semantics",
        {
            "contract_version": CONTRACT_VERSION,
            "methodology_version": METHODOLOGY_VERSION,
            "analysis_kind": _ANALYSIS_KIND,
            "status": status,
            "reasons": reasons,
            "upstream_contract_version": qualification.contract_version,
            "upstream_qualifier_version": qualification.qualifier_version,
            "upstream_evidence_kind": qualification.evidence_kind,
            "upstream_status": qualification.status,
            "upstream_reasons": qualification.reasons,
            "upstream_profile_status": qualification.upstream_profile_status,
            "upstream_profile_reasons": qualification.upstream_profile_reasons,
            "route_context_state": _route_context_state(qualification),
            "source_cik": qualification.source_cik,
            "period_end": qualification.period_end,
            "accounting_namespace": qualification.accounting_namespace,
            "accounting_basis": qualification.accounting_basis,
            "assets_concept": (
                qualification.assets_concept
            ),
            "liabilities_concept": qualification.liabilities_concept,
            "unit": qualification.unit,
            "assets": _exact_decimal_semantics(
                qualification.assets
            ),
            "liabilities": _exact_decimal_semantics(
                qualification.liabilities
            ),
            "upstream_authority": qualification.authority,
            "upstream_limitations": qualification.limitations,
        },
    )


def _is_hash(value) -> bool:
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _valid_optional_nonempty_string(value) -> bool:
    return value is None or (
        type(value) is str and bool(value) and value == value.strip()
    )


def _valid_optional_timestamp(value) -> bool:
    if value is None:
        return True
    if (
        not _valid_optional_nonempty_string(value)
        or not value.endswith("Z")
    ):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        canonical = (
            parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        )
    except (ValueError, OverflowError):
        return False
    return parsed.tzinfo is not None and canonical == value


def _valid_date(value) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _valid_optional_date(value) -> bool:
    return value is None or _valid_date(value)


def _canonical_upstream_module(qualification):
    qualification_type = type(qualification)
    module = sys.modules.get(qualification_type.__module__)
    if (
        qualification_type.__module__ != _UPSTREAM_MODULE_NAME
        or module is None
        or getattr(
            module,
            "CurrentAnnualAssetsLiabilitiesQualification",
            None,
        ) is not qualification_type
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Exact CurrentAnnualAssetsLiabilitiesQualification required"
        )
    return module


def _validate_supporting_filing(filing, upstream) -> None:
    if (
        type(filing) is not upstream.AssetsLiabilitiesSupportingFiling
        or type(filing.accession) is not str
        or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
        or type(filing.forms) is not tuple
        or len(filing.forms) != 1
        or filing.forms != tuple(sorted(set(filing.forms)))
        or any(
            type(item) is not str or item not in ("10-K", "10-K/A")
            for item in filing.forms
        )
        or type(filing.filed_dates) is not tuple
        or len(filing.filed_dates) != 1
        or filing.filed_dates != tuple(sorted(set(filing.filed_dates)))
        or any(not _valid_date(item) for item in filing.filed_dates)
        or type(filing.fiscal_years) is not tuple
        or len(filing.fiscal_years) != 1
        or filing.fiscal_years != tuple(sorted(set(filing.fiscal_years)))
        or any(type(item) is not int for item in filing.fiscal_years)
        or type(filing.assets_observation_ids) is not tuple
        or not filing.assets_observation_ids
        or filing.assets_observation_ids
        != tuple(sorted(set(filing.assets_observation_ids)))
        or any(
            not _is_hash(item)
            for item in filing.assets_observation_ids
        )
        or type(filing.liabilities_observation_ids) is not tuple
        or not filing.liabilities_observation_ids
        or filing.liabilities_observation_ids
        != tuple(sorted(set(filing.liabilities_observation_ids)))
        or any(not _is_hash(item) for item in filing.liabilities_observation_ids)
        or set(filing.assets_observation_ids)
        & set(filing.liabilities_observation_ids)
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical established supporting filing required"
        )


def _validate_profile_state_reasons(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    status = qualification.upstream_profile_status
    reasons = qualification.upstream_profile_reasons
    reason = profile_upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
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
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    ):
        coherent = reasons == ()
    elif status is (
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
    ):
        coherent = bool(reasons) and set(reasons) <= unavailable_reasons
    elif status is (
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED
    ):
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
    if (
        reason.SIC_DESCRIPTION_MISSING_OR_INVALID in reasons
        and set(reasons) & decision_derived_reasons
    ):
        coherent = False
    if (
        status is
        profile_upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons
    ):
        coherent = False
    if not coherent:
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical native profile status/reasons required"
        )


def _validate_shape(qualification, upstream) -> None:
    profile_upstream = upstream.upstream
    if (
        qualification.contract_version != upstream.CONTRACT_VERSION
        or qualification.qualifier_version != upstream.QUALIFIER_VERSION
        or qualification.evidence_kind != upstream.EVIDENCE_KIND
        or qualification.accounting_namespace != upstream.NAMESPACE
        or qualification.accounting_basis != upstream.ACCOUNTING_BASIS
        or qualification.assets_concept
        != upstream.ASSETS_CONCEPT
        or qualification.liabilities_concept != upstream.LIABILITIES_CONCEPT
        or qualification.unit != upstream.REVIEWED_UNIT
        or qualification.authority != upstream.AUTHORITY
        or qualification.limitations != tuple(
            upstream.CurrentAnnualAssetsLiabilitiesLimitation
        )
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical liabilities/assets qualification contract required"
        )
    if type(qualification.status) is not (
        upstream.CurrentAnnualAssetsLiabilitiesStatus
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Unknown liabilities/assets qualification status"
        )
    if (
        type(qualification.reasons) is not tuple
        or any(
            type(reason) is not
            upstream.CurrentAnnualAssetsLiabilitiesReason
            for reason in qualification.reasons
        )
        or qualification.reasons != tuple(
            sorted(set(qualification.reasons), key=lambda item: item.value)
        )
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical native liabilities/assets reasons required"
        )
    if (
        type(qualification.upstream_profile_status) is not
        profile_upstream.OrdinaryCompounderProfileStatus
        or type(qualification.upstream_profile_reasons) is not tuple
        or any(
            type(reason) is not profile_upstream.ProfileReason
            for reason in qualification.upstream_profile_reasons
        )
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical native profile state required"
        )
    _validate_profile_state_reasons(qualification, upstream)
    route_values = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    route_absent = all(value is None for value in route_values)
    route_present = all(_is_hash(value) for value in route_values)
    receipt_values = (
        qualification.capture_receipt_id,
        qualification.source_object_hash,
        qualification.captured_at,
        qualification.capture_source_locator,
    )
    receipt_absent = all(value is None for value in receipt_values)
    receipt_present = (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and _valid_optional_timestamp(qualification.captured_at)
        and qualification.captured_at is not None
        and _valid_optional_nonempty_string(
            qualification.capture_source_locator
        )
        and qualification.capture_source_locator is not None
    )
    if (
        not (route_absent or route_present)
        or not (receipt_absent or receipt_present)
        or any(
            not _is_hash(value)
            for value in (
                qualification.upstream_profile_semantic_id,
                qualification.upstream_comparability_semantic_id,
                qualification.upstream_profile_evidence_id,
                qualification.upstream_comparability_evidence_id,
            )
        )
        or type(qualification.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", qualification.source_cik) is None
        or not _valid_optional_date(qualification.period_end)
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical liabilities/assets identity and route context required"
        )


def _has_route_context(qualification) -> bool:
    return (
        _is_hash(qualification.route_local_issuer_key)
        and _is_hash(qualification.route_local_security_key)
        and qualification.period_end is not None
    )


def _has_receipt_context(qualification) -> bool:
    return (
        _is_hash(qualification.capture_receipt_id)
        and _is_hash(qualification.source_object_hash)
        and qualification.captured_at is not None
        and qualification.capture_source_locator is not None
    )


def _preliminary_unavailable_reason_families(reason) -> frozenset[tuple]:
    assets_paths = (
        None,
        reason.ASSETS_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_ASSETS_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_TARGET_PERIOD_END_PRESENTATION_UNAVAILABLE,
    )
    liabilities_paths = (
        None,
        reason.LIABILITIES_UNAVAILABLE,
        reason.EXACT_USD_UNIT_UNAVAILABLE,
        reason.FINITE_LIABILITIES_VALUE_UNAVAILABLE,
        reason.EXACT_ANNUAL_TARGET_PERIOD_END_PRESENTATION_UNAVAILABLE,
    )
    return frozenset(
        tuple(sorted(
            {
                item
                for item in (assets_reason, liabilities_reason)
                if item is not None
            },
            key=lambda item: item.value,
        ))
        for assets_reason in assets_paths
        for liabilities_reason in liabilities_paths
        if assets_reason is not None or liabilities_reason is not None
    )


def _local_conflict_reason_families(reason) -> frozenset[tuple]:
    competing_both = tuple(sorted(
        (
            reason.COMPETING_ASSETS_VALUES,
            reason.COMPETING_LIABILITIES_VALUES,
        ),
        key=lambda item: item.value,
    ))
    return frozenset({
        (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,),
        (reason.CAPTURE_REPLAY_CONFLICT,),
        (reason.SOURCE_CIK_CONFLICT,),
        (reason.COMMON_FILING_METADATA_CONFLICT,),
        (reason.COMPETING_ASSETS_VALUES,),
        (reason.COMPETING_LIABILITIES_VALUES,),
        competing_both,
    })


def _upstream_identities(qualification) -> tuple[str, str]:
    try:
        semantic_id = qualification.semantic_id
        evidence_id = qualification.evidence_id
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical upstream liabilities/assets identities required"
        ) from exc
    if not _is_hash(semantic_id) or not _is_hash(evidence_id):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical upstream liabilities/assets identities required"
        )
    return semantic_id, evidence_id


def _validate_established(
    qualification,
    upstream,
) -> tuple[Decimal, Decimal]:
    profile_upstream = upstream.upstream
    assets = qualification.assets
    liabilities = qualification.liabilities
    if (
        qualification.reasons != ()
        or qualification.upstream_profile_status is not
        profile_upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        or qualification.upstream_profile_reasons != ()
        or not _is_hash(qualification.route_local_issuer_key)
        or not _is_hash(qualification.route_local_security_key)
        or qualification.source_cik is None
        or qualification.period_end is None
        or type(assets) is not Decimal
        or not assets.is_finite()
        or type(liabilities) is not Decimal
        or not liabilities.is_finite()
        or not _is_hash(qualification.capture_receipt_id)
        or not _is_hash(qualification.source_object_hash)
        or not qualification.captured_at
        or not qualification.capture_source_locator
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Contradictory established liabilities/assets qualification"
        )

    assets_ids = qualification.selected_assets_observation_ids
    liabilities_ids = qualification.selected_liabilities_observation_ids
    accessions = qualification.supporting_accessions
    filings = qualification.supporting_filings
    if (
        type(assets_ids) is not tuple
        or not assets_ids
        or assets_ids != tuple(sorted(set(assets_ids)))
        or any(not _is_hash(item) for item in assets_ids)
        or type(liabilities_ids) is not tuple
        or not liabilities_ids
        or liabilities_ids != tuple(sorted(set(liabilities_ids)))
        or any(not _is_hash(item) for item in liabilities_ids)
        or type(accessions) is not tuple
        or not accessions
        or accessions != tuple(sorted(set(accessions)))
        or any(
            type(item) is not str
            or _ACCESSION_PATTERN.fullmatch(item) is None
            for item in accessions
        )
        or type(filings) is not tuple
        or len(filings) != len(accessions)
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical established liabilities/assets evidence surfaces required"
        )
    for filing in filings:
        _validate_supporting_filing(filing, upstream)
    flattened_assets_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.assets_observation_ids
    )
    flattened_liabilities_ids = tuple(
        observation_id
        for filing in filings
        for observation_id in filing.liabilities_observation_ids
    )
    if (
        tuple(item.accession for item in filings) != accessions
        or set(assets_ids) & set(liabilities_ids)
        or len(flattened_assets_ids) != len(set(flattened_assets_ids))
        or len(flattened_liabilities_ids) != len(set(flattened_liabilities_ids))
        or tuple(sorted(flattened_assets_ids)) != assets_ids
        or tuple(sorted(flattened_liabilities_ids)) != liabilities_ids
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Coherent established liabilities/assets provenance required"
        )
    return assets, liabilities


def _validate_non_established(qualification, upstream) -> None:
    if (
        not qualification.reasons
        or qualification.assets is not None
        or qualification.liabilities is not None
        or qualification.selected_assets_observation_ids != ()
        or qualification.selected_liabilities_observation_ids != ()
        or qualification.supporting_accessions != ()
        or qualification.supporting_filings != ()
    ):
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical non-established liabilities/assets qualification required"
        )
    status = qualification.status
    reasons = qualification.reasons
    reason = upstream.CurrentAnnualAssetsLiabilitiesReason
    upstream_status = upstream.CurrentAnnualAssetsLiabilitiesStatus
    profile_status = upstream.upstream.OrdinaryCompounderProfileStatus
    preliminary_unavailable = _preliminary_unavailable_reason_families(reason)
    local_unavailable = preliminary_unavailable | frozenset({
        (reason.NO_COMMON_ANNUAL_FILING_ACCESSION,),
    })
    local_conflicts = _local_conflict_reason_families(reason)
    route_context = _has_route_context(qualification)
    receipt_context = _has_receipt_context(qualification)
    if status is upstream_status.EVIDENCE_UNAVAILABLE:
        if reasons == (reason.UPSTREAM_PROFILE_UNAVAILABLE,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.PROFILE_UNAVAILABLE
            )
        else:
            coherent = (
                reasons in local_unavailable
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and receipt_context
            )
    elif status is upstream_status.EVIDENCE_UNSUPPORTED:
        coherent = (
            reasons == (reason.UPSTREAM_PROFILE_UNSUPPORTED,)
            and qualification.upstream_profile_status is
            profile_status.PROFILE_UNSUPPORTED
        )
    elif status is upstream_status.SOURCE_CONFLICT:
        if reasons == (reason.UPSTREAM_SOURCE_CONFLICT,):
            coherent = (
                qualification.upstream_profile_status is
                profile_status.SOURCE_CONFLICT
            )
        else:
            coherent = (
                reasons in local_conflicts
                and qualification.upstream_profile_status is
                profile_status.ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
                and qualification.upstream_profile_reasons == ()
                and route_context
                and (
                    receipt_context
                    or reasons == (reason.CANONICAL_ROUTE_IDENTITY_CONFLICT,)
                )
            )
    else:
        coherent = False
    if not coherent:
        raise CurrentAnnualLiabilitiesToPositiveAssetsError(
            "Canonical non-established status/reason/profile path required"
        )


def _ratio_from_decimals(
    liabilities: Decimal,
    assets: Decimal,
) -> LiabilitiesToAssetsRatio:
    liabilities_numerator, liabilities_denominator = (
        liabilities.as_integer_ratio()
    )
    assets_numerator, assets_denominator = assets.as_integer_ratio()
    numerator = liabilities_numerator * assets_denominator
    denominator = liabilities_denominator * assets_numerator
    divisor = gcd(numerator, denominator)
    return LiabilitiesToAssetsRatio(
        numerator // divisor,
        denominator // divisor,
    )


def analyze_current_annual_liabilities_to_positive_assets(
    qualification,
) -> CurrentAnnualLiabilitiesToPositiveAssetsResult:
    """Report exact liabilities per positive assets dollar for qualified evidence."""
    upstream = _canonical_upstream_module(qualification)
    _validate_shape(qualification, upstream)
    upstream_status = qualification.status
    upstream_status_type = upstream.CurrentAnnualAssetsLiabilitiesStatus

    ratio = None
    if upstream_status is (
        upstream_status_type.PAIRED_ASSETS_LIABILITIES_ESTABLISHED
    ):
        assets, liabilities = _validate_established(
            qualification, upstream
        )
        if assets > 0:
            status = CurrentAnnualLiabilitiesToPositiveAssetsStatus.AVAILABLE
            reasons = ()
            ratio = _ratio_from_decimals(liabilities, assets)
        elif assets == 0:
            status = CurrentAnnualLiabilitiesToPositiveAssetsStatus.NOT_APPLICABLE
            reasons = (
                CurrentAnnualLiabilitiesToPositiveAssetsReason.
                ASSETS_ZERO_DENOMINATOR,
            )
        else:
            status = CurrentAnnualLiabilitiesToPositiveAssetsStatus.NOT_APPLICABLE
            reasons = (
                CurrentAnnualLiabilitiesToPositiveAssetsReason.
                ASSETS_NEGATIVE_NOT_POSITIVE_DENOMINATOR,
            )
    else:
        _validate_non_established(qualification, upstream)
        mapping = {
            upstream_status_type.EVIDENCE_UNAVAILABLE: (
                CurrentAnnualLiabilitiesToPositiveAssetsStatus.UNAVAILABLE,
                CurrentAnnualLiabilitiesToPositiveAssetsReason.
                UPSTREAM_EVIDENCE_UNAVAILABLE,
            ),
            upstream_status_type.EVIDENCE_UNSUPPORTED: (
                CurrentAnnualLiabilitiesToPositiveAssetsStatus.UNSUPPORTED,
                CurrentAnnualLiabilitiesToPositiveAssetsReason.
                UPSTREAM_EVIDENCE_UNSUPPORTED,
            ),
            upstream_status_type.SOURCE_CONFLICT: (
                CurrentAnnualLiabilitiesToPositiveAssetsStatus.SOURCE_CONFLICT,
                CurrentAnnualLiabilitiesToPositiveAssetsReason.
                UPSTREAM_SOURCE_CONFLICT,
            ),
        }
        try:
            status, reason = mapping[upstream_status]
        except KeyError as exc:
            raise CurrentAnnualLiabilitiesToPositiveAssetsError(
                "Unknown liabilities/assets qualification status"
            ) from exc
        reasons = (reason,)

    upstream_semantic_id, upstream_evidence_id = _upstream_identities(
        qualification
    )
    analytical_input_semantic_fingerprint = (
        _analytical_input_semantic_fingerprint(
            qualification,
            status=status,
            reasons=reasons,
        )
    )
    result = CurrentAnnualLiabilitiesToPositiveAssetsResult(
        CONTRACT_VERSION,
        METHODOLOGY_VERSION,
        _ANALYSIS_KIND,
        status,
        reasons,
        qualification.status,
        qualification.reasons,
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
        qualification.source_cik,
        qualification.period_end,
        upstream_semantic_id,
        upstream_evidence_id,
        ratio,
        _AUTHORITY,
        _LIMITATIONS,
    )
    object.__setattr__(
        result,
        "_analytical_input_semantic_fingerprint",
        analytical_input_semantic_fingerprint,
    )
    return result
