"""CURRENT qualification for exact annual opening and closing Assets.

The public boundary is one exact ``SecArchive`` plus one exact canonical
ordinary-compounder profile. The embedded route selects the issuer, annual
period, Companyfacts receipt, and immutable source object.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, timedelta
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
    _periods as _rebuild_comparable_periods,
    RealEPSComparabilityQualification,
)
from .sec_current_evidence import assess_sec_current_evidence
from .current_authority import CurrentAuthorityError
from .sec_eps_series import ResolutionStatus
from .sec_assets_liabilities import (
    NAMESPACE,
    ASSETS_CONCEPT,
    REVIEWED_UNIT,
    AssetsLiabilitiesObservation,
    extract_assets_liabilities,
)
from . import sec_ordinary_compounder_profile as upstream


CONTRACT_VERSION = (
    "2026-10-10-current-annual-opening-closing-assets-qualification-v1"
)
QUALIFIER_VERSION = (
    "2026-10-10-adjacent-common-filing-exact-decimal-usd-assets-instants-qualification-v1"
)
EVIDENCE_KIND = (
    "CURRENT_ANNUAL_OPENING_CLOSING_ASSETS_QUALIFICATION"
)
ACCOUNTING_BASIS = "US_GAAP"
AUTHORITY = "QUALITY_OPENING_CLOSING_ASSETS_EVIDENCE_ONLY"


class CurrentAnnualOpeningClosingAssetsError(ValueError):
    """Wrong public type or contradictory canonical upstream object."""


class CurrentAnnualOpeningClosingAssetsStatus(StrEnum):
    OPENING_CLOSING_ASSETS_ESTABLISHED = (
        "OPENING_CLOSING_ASSETS_ESTABLISHED"
    )
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class CurrentAnnualOpeningClosingAssetsReason(StrEnum):
    UPSTREAM_PROFILE_UNAVAILABLE = "UPSTREAM_PROFILE_UNAVAILABLE"
    UPSTREAM_PROFILE_UNSUPPORTED = "UPSTREAM_PROFILE_UNSUPPORTED"
    UPSTREAM_SOURCE_CONFLICT = "UPSTREAM_SOURCE_CONFLICT"
    CANONICAL_ROUTE_IDENTITY_CONFLICT = "CANONICAL_ROUTE_IDENTITY_CONFLICT"
    CAPTURE_REPLAY_CONFLICT = "CAPTURE_REPLAY_CONFLICT"
    SOURCE_CIK_CONFLICT = "SOURCE_CIK_CONFLICT"
    CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE = "CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE"
    CLOSING_ASSETS_UNAVAILABLE = "CLOSING_ASSETS_UNAVAILABLE"
    OPENING_ASSETS_UNAVAILABLE = "OPENING_ASSETS_UNAVAILABLE"
    EXACT_USD_UNIT_UNAVAILABLE = "EXACT_USD_UNIT_UNAVAILABLE"
    FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE = (
        "FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE"
    )
    FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE = (
        "FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE"
    )
    EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE = (
        "EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE"
    )
    NO_COMMON_ANNUAL_FILING_ACCESSION = "NO_COMMON_ANNUAL_FILING_ACCESSION"
    COMPETING_CLOSING_ASSETS_VALUES = (
        "COMPETING_CLOSING_ASSETS_VALUES"
    )
    COMPETING_OPENING_ASSETS_VALUES = "COMPETING_OPENING_ASSETS_VALUES"
    COMMON_FILING_METADATA_CONFLICT = "COMMON_FILING_METADATA_CONFLICT"


class CurrentAnnualOpeningClosingAssetsLimitation(StrEnum):
    ONLY_US_GAAP_ASSETS = "ONLY_US_GAAP_ASSETS"
    NO_TAXONOMY_SUBSTITUTION = "NO_TAXONOMY_SUBSTITUTION"
    NO_AVERAGE_ASSETS = "NO_AVERAGE_ASSETS"
    NO_ROA = "NO_ROA"
    NO_ROE = "NO_ROE"
    NO_ROIC = "NO_ROIC"
    NO_INVESTED_CAPITAL_INTERPRETATION = "NO_INVESTED_CAPITAL_INTERPRETATION"
    NO_TANGIBLE_BOOK_VALUE = "NO_TANGIBLE_BOOK_VALUE"
    NO_LIQUIDATION_VALUE = "NO_LIQUIDATION_VALUE"
    NO_ASSET_QUALITY_JUDGMENT = "NO_ASSET_QUALITY_JUDGMENT"
    NO_CAPITAL_EFFICIENCY_JUDGMENT = "NO_CAPITAL_EFFICIENCY_JUDGMENT"
    NO_ASSET_GROWTH_QUALITY_OR_HISTORICAL_TREND = "NO_ASSET_GROWTH_QUALITY_OR_HISTORICAL_TREND"
    NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION = "NO_LEVERAGE_LIQUIDITY_OR_SOLVENCY_CONCLUSION"
    NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY = "NO_CROSS_COMPANY_OR_CROSS_SECTOR_COMPARABILITY"
    NO_QUALITY_SCORE_GRADE_RANKING_AGGREGATION_OR_WEIGHTING = "NO_QUALITY_SCORE_GRADE_RANKING_AGGREGATION_OR_WEIGHTING"
    NO_DURABILITY_CONCLUSION = "NO_DURABILITY_CONCLUSION"
    NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT = "NO_EXPECTED_RETURN_OR_CONFIDENCE_EFFECT"
    NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION = "NO_RECOMMENDATION_ALLOCATION_SIZING_OR_EXECUTION"
    NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION = "NO_PRODUCTION_DEPLOYMENT_OR_V2_PROMOTION"
    NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY = "NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY"


_LIMITATIONS = tuple(CurrentAnnualOpeningClosingAssetsLimitation)
_HASH_LENGTH = 64
_ACCESSION_PATTERN = re.compile(r"[0-9]{10}-[0-9]{2}-[0-9]{6}")
_COMPARABILITY_CONTRACT_VERSION = (
    "2026-09-28-sec-current-eps-comparability-v1"
)
_COMPARABILITY_QUALIFIER_VERSION = (
    "2026-09-28-positive-five-period-presentation-v1"
)
_COMPARABILITY_MODE = "CURRENT_SEC_SINGLE_PRESENTATION_HISTORICAL_COMPARABILITY"


@dataclass(frozen=True, slots=True)
class OpeningClosingAssetsSupportingFiling:
    accession: str
    forms: tuple[str, ...]
    filed_dates: tuple[str, ...]
    fiscal_years: tuple[int, ...]
    closing_assets_observation_ids: tuple[str, ...]
    opening_assets_observation_ids: tuple[str, ...]


class _RouteContextState(StrEnum):
    ROUTE_CONTEXT_PRESENT = "ROUTE_CONTEXT_PRESENT"
    ROUTE_CONTEXT_ABSENT = "ROUTE_CONTEXT_ABSENT"


@dataclass(frozen=True, slots=True)
class CurrentAnnualOpeningClosingAssetsQualification:
    contract_version: str
    qualifier_version: str
    evidence_kind: str
    status: CurrentAnnualOpeningClosingAssetsStatus
    reasons: tuple[CurrentAnnualOpeningClosingAssetsReason, ...]
    upstream_profile_status: upstream.OrdinaryCompounderProfileStatus
    upstream_profile_reasons: tuple[upstream.ProfileReason, ...]
    route_local_issuer_key: str | None
    route_local_security_key: str | None
    source_cik: str | None
    period_start: str | None
    period_end: str | None
    opening_balance_date: str | None
    closing_balance_date: str | None
    accounting_namespace: str
    accounting_basis: str
    concept: str
    unit: str
    closing_assets: Decimal | None
    opening_assets: Decimal | None
    upstream_profile_semantic_id: str
    upstream_comparability_semantic_id: str
    upstream_profile_evidence_id: str
    upstream_comparability_evidence_id: str
    capture_receipt_id: str | None
    source_object_hash: str | None
    captured_at: str | None
    capture_source_locator: str | None
    selected_closing_assets_observation_ids: tuple[str, ...]
    selected_opening_assets_observation_ids: tuple[str, ...]
    supporting_accessions: tuple[str, ...]
    supporting_filings: tuple[OpeningClosingAssetsSupportingFiling, ...]
    selected_opening_observations: tuple[AssetsLiabilitiesObservation, ...]
    selected_closing_observations: tuple[AssetsLiabilitiesObservation, ...]
    authority: str
    limitations: tuple[CurrentAnnualOpeningClosingAssetsLimitation, ...]

    @property
    def semantic_id(self):
        return _identity(
            "current-annual-opening-closing-assets-semantics",
            {
                "contract_version": self.contract_version,
                "qualifier_version": self.qualifier_version,
                "evidence_kind": self.evidence_kind,
                "status": self.status,
                "reasons": self.reasons,
                "upstream_profile_status": self.upstream_profile_status,
                "upstream_profile_reasons": self.upstream_profile_reasons,
                "route_context_state": _route_context_state(self),
                "source_cik": self.source_cik,
                "period_start": self.period_start,
                "period_end": self.period_end,
                "opening_balance_date": self.opening_balance_date,
                "closing_balance_date": self.closing_balance_date,
                "accounting_namespace": self.accounting_namespace,
                "accounting_basis": self.accounting_basis,
                "concept": self.concept,
                "unit": self.unit,
                "closing_assets": self.closing_assets,
                "opening_assets": self.opening_assets,
                "authority": self.authority,
                "limitations": self.limitations,
            },
        )

    @property
    def evidence_id(self):
        return _identity(
            "current-annual-opening-closing-assets-evidence",
            {
                "semantic_id": self.semantic_id,
                "upstream_profile_semantic_id": self.upstream_profile_semantic_id,
                "upstream_comparability_semantic_id": (
                    self.upstream_comparability_semantic_id
                ),
                "upstream_profile_evidence_id": self.upstream_profile_evidence_id,
                "upstream_comparability_evidence_id": (
                    self.upstream_comparability_evidence_id
                ),
                "capture_receipt_id": self.capture_receipt_id,
                "source_object_hash": self.source_object_hash,
                "captured_at": self.captured_at,
                "capture_source_locator": self.capture_source_locator,
                "route_local_issuer_key": self.route_local_issuer_key,
                "route_local_security_key": self.route_local_security_key,
                "selected_closing_assets_observation_ids": (
                    self.selected_closing_assets_observation_ids
                ),
                "selected_opening_assets_observation_ids": (
                    self.selected_opening_assets_observation_ids
                ),
                "supporting_accessions": self.supporting_accessions,
                "supporting_filings": self.supporting_filings,
                "selected_opening_observations": self.selected_opening_observations,
                "selected_closing_observations": self.selected_closing_observations,
            },
        )

    def to_dict(self):
        payload = _canonical(self)
        payload["semantic_id"] = self.semantic_id
        payload["evidence_id"] = self.evidence_id
        return {"current_annual_opening_closing_assets": payload}


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
    raise CurrentAnnualOpeningClosingAssetsError(
        "Unsupported opening-closing-assets-evidence identity value"
    )


def _canonical_decimal(value):
    """Project equal finite base-ten values identically without rounding."""
    if not value.is_finite():
        raise CurrentAnnualOpeningClosingAssetsError(
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


def _route_context_state(qualification):
    values = (
        qualification.route_local_issuer_key,
        qualification.route_local_security_key,
    )
    if all(value is None for value in values):
        return _RouteContextState.ROUTE_CONTEXT_ABSENT
    if all(_is_hash(value) for value in values):
        return _RouteContextState.ROUTE_CONTEXT_PRESENT
    raise CurrentAnnualOpeningClosingAssetsError(
        "Canonical paired route context required"
    )


def _ordered_reasons(reasons):
    return tuple(sorted(set(reasons), key=lambda item: item.value))


def _valid_date(value):
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _validate_profile_state_reasons(profile):
    reasons = profile.reasons
    reason = upstream.ProfileReason
    if reasons != tuple(sorted(set(reasons), key=lambda item: item.value)):
        raise CurrentAnnualOpeningClosingAssetsError(
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
    if profile.status is (
        upstream.OrdinaryCompounderProfileStatus.
        ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
    ):
        coherent = reasons == ()
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE:
        coherent = bool(reasons) and set(reasons) <= unavailable_reasons
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED:
        coherent = (
            reason.UNSUPPORTED_SIC_PROFILE in reasons
            and reason.REPLAY_IDENTITY_MISMATCH not in reasons
        )
    elif profile.status is upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT:
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
        profile.status is upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
        and reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED in reasons
    ):
        coherent = False
    if not coherent:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical native profile status/reasons required"
        )


def _factory_reachable_profile(profile, comparability):
    """Rebuild the exact upstream projection consumed by this qualifier."""
    reason = upstream.ProfileReason
    reasons = set()
    if comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED:
        reasons.add(reason.PR5C_NOT_ESTABLISHED)
    replay_mismatch = (
        profile.expected_comparability_semantic_id != comparability.semantic_id
        or profile.expected_comparability_evidence_id != comparability.evidence_id
    )
    if replay_mismatch:
        reasons.add(reason.REPLAY_IDENTITY_MISMATCH)

    sic, description, metadata_semantic_id, metadata_evidence_id = (
        upstream._sic_metadata(comparability)
    )
    if sic is None or not 100 <= sic <= 9999:
        reasons.add(reason.SIC_MISSING_OR_INVALID)
    if description is None:
        reasons.add(reason.SIC_DESCRIPTION_MISSING_OR_INVALID)

    decisions = []
    if sic is not None and description is not None:
        support_semantics = tuple(value for value in (
            metadata_semantic_id,
            comparability.historical_reporting_subject.qualified_subject_identity,
            comparability.semantic_id,
        ) if value is not None)
        support_evidence = tuple(value for value in (
            metadata_evidence_id,
            comparability.evidence_id,
        ) if value is not None)
        flags = upstream._structural_flags(sic, description)
        mixed_signal = any(
            claim.kind is upstream.ReportingSubjectClaimKind.
            COMBINED_FINANCIAL_STATEMENTS_REFERENCE
            for claim in comparability.upstream_reporting_subject_source.explicit_claims
        )
        for structure in tuple(upstream.UnsupportedStructure)[:10]:
            detected = flags[structure]
            unresolved_mixed = (
                structure is upstream.UnsupportedStructure.MIXED_CONGLOMERATE
                and mixed_signal
                and not detected
            )
            decisions.append(upstream.MethodProfileDecision(
                structure,
                (
                    upstream.ProfileDecisionValue.NOT_EXCLUDED
                    if detected
                    else upstream.ProfileDecisionValue.UNRESOLVED
                    if unresolved_mixed
                    else upstream.ProfileDecisionValue.EXCLUDED
                ),
                (
                    f"SEC_SIC_PROFILE_MATCH:{sic}:{description}"
                    if detected
                    else "COMBINED_FINANCIAL_STATEMENTS_REQUIRE_MIXED_STRUCTURE_RESOLUTION"
                    if unresolved_mixed
                    else f"SEC_SIC_PROFILE_EXCLUDED:{sic}:{description}"
                ),
                support_semantics,
                support_evidence,
            ))
        positive = (
            len(comparability.period_decisions) == 5
            and all(item.c3_value > 0 for item in comparability.period_decisions)
        )
        subject_stable = (
            comparability.historical_reporting_subject.qualified_subject_identity
            is not None
        )
        decisions.extend((
            upstream.MethodProfileDecision(
                upstream.UnsupportedStructure.TURNAROUND,
                (
                    upstream.ProfileDecisionValue.EXCLUDED
                    if positive and subject_stable
                    else upstream.ProfileDecisionValue.UNRESOLVED
                ),
                (
                    "STABLE_POSITIVE_FIVE_PERIOD_REPORTING_SUBJECT_ROUTE"
                    if positive and subject_stable
                    else "TURNAROUND_EXCLUSION_NOT_ESTABLISHED"
                ),
                support_semantics,
                support_evidence,
            ),
            upstream.MethodProfileDecision(
                upstream.UnsupportedStructure.LOSS_MAKING,
                (
                    upstream.ProfileDecisionValue.EXCLUDED
                    if positive
                    else upstream.ProfileDecisionValue.NOT_EXCLUDED
                ),
                (
                    "ALL_FIVE_QUALIFIED_DILUTED_EPS_PERIODS_STRICTLY_POSITIVE"
                    if positive
                    else "POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED"
                ),
                support_semantics,
                support_evidence,
            ),
        ))
        if not positive:
            reasons.add(reason.POSITIVE_FIVE_PERIOD_ROUTE_NOT_ESTABLISHED)
        if not subject_stable:
            reasons.add(reason.REPORTING_SUBJECT_STABILITY_NOT_ESTABLISHED)
        if any(
            item.profile is upstream.UnsupportedStructure.MIXED_CONGLOMERATE
            and item.decision is upstream.ProfileDecisionValue.UNRESOLVED
            for item in decisions
        ):
            reasons.add(reason.MIXED_STRUCTURE_UNRESOLVED)

    if reason.REPLAY_IDENTITY_MISMATCH in reasons:
        status = upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT
    elif decisions and any(
        item.decision is upstream.ProfileDecisionValue.NOT_EXCLUDED
        for item in decisions
    ):
        reasons.add(reason.UNSUPPORTED_SIC_PROFILE)
        status = upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED
    elif (
        reasons
        or len(decisions) != len(upstream.UnsupportedStructure)
        or any(
            item.decision is not upstream.ProfileDecisionValue.EXCLUDED
            for item in decisions
        )
    ):
        status = upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE
    else:
        status = (
            upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        )

    return upstream.OrdinaryCompounderMethodProfileQualification(
        upstream.CONTRACT_VERSION,
        upstream.QUALIFIER_VERSION,
        status,
        upstream.PROFILE if status is (
            upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        ) else None,
        comparability.upstream_reporting_subject_source.source_cik,
        sic,
        description,
        tuple(decisions),
        tuple(sorted(reasons, key=lambda item: item.value)),
        upstream.LIMITATIONS,
        comparability,
        metadata_semantic_id,
        metadata_evidence_id,
        profile.expected_comparability_semantic_id,
        profile.expected_comparability_evidence_id,
    )


def _validate_profile_shape(profile):
    if (
        profile.contract_version != upstream.CONTRACT_VERSION
        or profile.qualifier_version != upstream.QUALIFIER_VERSION
        or profile.limitations != upstream.LIMITATIONS
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical ordinary-compounder profile contract required"
        )
    if type(profile.status) is not upstream.OrdinaryCompounderProfileStatus:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Unknown ordinary-compounder profile state"
        )
    if (
        type(profile.reasons) is not tuple
        or any(type(reason) is not upstream.ProfileReason for reason in profile.reasons)
        or type(profile.decisions) is not tuple
        or any(type(item) is not upstream.MethodProfileDecision
               for item in profile.decisions)
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical ordinary-compounder profile details required"
        )
    if profile.sic is not None and type(profile.sic) is not int:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical ordinary-compounder SIC value required"
        )
    _validate_profile_state_reasons(profile)
    comparability = profile.upstream_comparability
    if type(comparability) is not RealEPSComparabilityQualification:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical embedded comparability required"
        )
    if (
        comparability.contract_version != _COMPARABILITY_CONTRACT_VERSION
        or comparability.qualifier_version != _COMPARABILITY_QUALIFIER_VERSION
        or comparability.qualification_mode != _COMPARABILITY_MODE
        or type(comparability.outcome) is not ComparabilityOutcome
        or type(comparability.reasons) is not tuple
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical comparability contract required"
        )
    if any(not _is_hash(value) for value in (
        profile.semantic_id,
        profile.evidence_id,
        profile.expected_comparability_semantic_id,
        profile.expected_comparability_evidence_id,
        comparability.semantic_id,
        comparability.evidence_id,
    )):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical upstream identities required"
        )
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    if (
        type(profile.source_cik) is not str
        or re.fullmatch(r"[0-9]{10}", profile.source_cik) is None
        or profile.source_cik != subject_cik
        or (profile.profile is not None and profile.profile != upstream.PROFILE)
        or (
            profile.status is upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        ) != (profile.profile == upstream.PROFILE)
        or (profile.sic_description is not None and (
            type(profile.sic_description) is not str
            or not profile.sic_description
            or profile.sic_description != profile.sic_description.strip()
        ))
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical ordinary-compounder profile context required"
        )
    metadata_present = profile.sic is not None and profile.sic_description is not None
    if metadata_present:
        if not _is_hash(profile.metadata_semantic_id) or not _is_hash(
            profile.metadata_evidence_id
        ):
            raise CurrentAnnualOpeningClosingAssetsError(
                "Canonical ordinary-compounder metadata identities required"
            )
    elif (
        profile.metadata_semantic_id is not None
        or profile.metadata_evidence_id is not None
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Impossible ordinary-compounder metadata identity surface"
        )
    expected_profiles = tuple(upstream.UnsupportedStructure)
    if metadata_present:
        if len(profile.decisions) != len(expected_profiles):
            raise CurrentAnnualOpeningClosingAssetsError(
                "Canonical method-profile decision inventory required"
            )
        for item, expected in zip(profile.decisions, expected_profiles, strict=True):
            if (
                type(item.profile) is not upstream.UnsupportedStructure
                or item.profile is not expected
                or type(item.decision) is not upstream.ProfileDecisionValue
                or type(item.reason) is not str
                or not item.reason
                or item.reason != item.reason.strip()
                or type(item.supporting_semantic_ids) is not tuple
                or any(not _is_hash(value) for value in item.supporting_semantic_ids)
                or type(item.supporting_evidence_ids) is not tuple
                or any(not _is_hash(value) for value in item.supporting_evidence_ids)
            ):
                raise CurrentAnnualOpeningClosingAssetsError(
                    "Canonical method-profile decisions required"
                )
    elif profile.decisions != ():
        raise CurrentAnnualOpeningClosingAssetsError(
            "Profile decisions require canonical SIC metadata"
        )
    if profile != _factory_reachable_profile(profile, comparability):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Factory-impossible ordinary-compounder profile projection"
        )
    return comparability


def _validate_established_profile(profile, comparability):
    security = comparability.upstream_security_eps
    if (
        profile.profile != upstream.PROFILE
        or profile.reasons != ()
        or type(profile.sic) is not int
        or not 100 <= profile.sic <= 9999
        or type(profile.sic_description) is not str
        or any(
            item.decision is not upstream.ProfileDecisionValue.EXCLUDED
            for item in profile.decisions
        )
        or comparability.outcome is not ComparabilityOutcome.COMPARABLE_REAL_EPS_ESTABLISHED
        or comparability.reasons != ()
        or not _is_hash(comparability.route_local_issuer_key)
        or not _is_hash(comparability.route_local_security_key)
        or comparability.route_local_issuer_key != security.route_local_issuer_key
        or comparability.route_local_security_key != security.route_local_security_key
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Contradictory established ordinary-compounder profile"
        )


def _target_period(comparability, *, require_established):
    periods = comparability.period_decisions
    if (
        type(periods) is not tuple
        or any(type(item) is not ComparableEPSPeriodDecision for item in periods)
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical comparable periods required"
        )
    series = (comparability.upstream_security_eps.upstream_registered_listing_bridge
              .temporal_boundary.current_evidence.resolution.series)
    if periods != _rebuild_comparable_periods(series, comparability.presentation):
        raise CurrentAnnualOpeningClosingAssetsError("Fabricated comparable annual chain")
    if not periods:
        if require_established:
            raise CurrentAnnualOpeningClosingAssetsError(
                "Established profile requires comparable annual periods"
            )
        return (None, None, None, None)
    try:
        period_dates = tuple(
            (date.fromisoformat(item.period_start), date.fromisoformat(item.period_end))
            for item in periods
        )
    except (TypeError, ValueError) as exc:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical annual period dates required"
        ) from exc
    if any(not _valid_date(value) for item in periods
           for value in (item.period_start, item.period_end)):
        raise CurrentAnnualOpeningClosingAssetsError("Exact ISO annual dates required")
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
        raise CurrentAnnualOpeningClosingAssetsError(
            "Contradictory established comparability"
        )
    latest = ordered[-1]
    start, end = period_dates[-1]
    if start > end:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical annual period order required"
        )
    if any(start > end for start, end in period_dates):
        raise CurrentAnnualOpeningClosingAssetsError("Canonical annual period order required")
    opening = None if len(ordered) < 2 else ordered[-2].period_end
    opening = _adjacent_opening_date(latest.period_start, opening)
    return latest.period_start, latest.period_end, opening, latest.period_end


def _adjacent_opening_date(period_start, preceding_end):
    """Exact calendar adjacency; never substitute a guessed annual interval."""
    if preceding_end is None:
        return None
    if date.fromisoformat(preceding_end) != date.fromisoformat(period_start) - timedelta(days=1):
        return None
    return preceding_end


def _route_context(profile, comparability):
    security = comparability.upstream_security_eps
    issuer_key = comparability.route_local_issuer_key
    security_key = comparability.route_local_security_key
    subject_cik = comparability.upstream_reporting_subject_source.source_cik
    conflict = (
        issuer_key != security.route_local_issuer_key
        or security_key != security.route_local_security_key
        or any(value is not None and not _is_hash(value)
               for value in (issuer_key, security_key))
        or profile.source_cik != subject_cik
    )
    try:
        current = (
            security.upstream_registered_listing_bridge.temporal_boundary
            .current_evidence
        )
        receipt = current.receipt
    except AttributeError:
        return issuer_key, security_key, subject_cik, None, True
    if receipt is not None and type(receipt) is not CaptureReceipt:
        return issuer_key, security_key, subject_cik, None, True
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
    dates,
    source_cik,
    receipt=None,
    closing_assets=None,
    opening_assets=None,
    closing_assets_ids=(),
    opening_assets_ids=(),
    accessions=(),
    filings=(),
    opening_observations=(),
    closing_observations=(),
):
    if status is not (
        CurrentAnnualOpeningClosingAssetsStatus.
        OPENING_CLOSING_ASSETS_ESTABLISHED
    ):
        closing_assets = None
        opening_assets = None
        closing_assets_ids = ()
        opening_assets_ids = ()
        accessions = ()
        filings = ()
        opening_observations = ()
        closing_observations = ()
    return CurrentAnnualOpeningClosingAssetsQualification(
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
        *dates,
        NAMESPACE,
        ACCOUNTING_BASIS,
        ASSETS_CONCEPT,
        REVIEWED_UNIT,
        closing_assets,
        opening_assets,
        profile.semantic_id,
        comparability.semantic_id,
        profile.evidence_id,
        comparability.evidence_id,
        None if receipt is None else receipt.receipt_id,
        None if receipt is None else receipt.content_sha256,
        None if receipt is None else receipt.captured_at,
        None if receipt is None else receipt.source_locator,
        tuple(closing_assets_ids),
        tuple(opening_assets_ids),
        tuple(accessions),
        tuple(filings),
        tuple(opening_observations),
        tuple(closing_observations),
        AUTHORITY,
        _LIMITATIONS,
    )


def _upstream_status(profile):
    mapping = {
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNAVAILABLE: (
            CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNAVAILABLE,
            CurrentAnnualOpeningClosingAssetsReason.UPSTREAM_PROFILE_UNAVAILABLE,
        ),
        upstream.OrdinaryCompounderProfileStatus.PROFILE_UNSUPPORTED: (
            CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNSUPPORTED,
            CurrentAnnualOpeningClosingAssetsReason.UPSTREAM_PROFILE_UNSUPPORTED,
        ),
        upstream.OrdinaryCompounderProfileStatus.SOURCE_CONFLICT: (
            CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            CurrentAnnualOpeningClosingAssetsReason.UPSTREAM_SOURCE_CONFLICT,
        ),
    }
    return mapping.get(profile.status)


def _eligible(observation, *, concept, cik, period_end):
    return (
        type(observation) is AssetsLiabilitiesObservation
        and observation.source_cik == cik
        and observation.namespace == NAMESPACE
        and observation.concept == concept
        and observation.accounting_basis == ACCOUNTING_BASIS
        and observation.unit == REVIEWED_UNIT
        and type(observation.value) is Decimal
        and observation.value.is_finite()
        and observation.start is None
        and observation.end == period_end
        and type(observation.fy) is int
        and observation.fp == "FY"
        and observation.form in ("10-K", "10-K/A")
        and _valid_date(observation.filed)
        and type(observation.accession) is str
        and _ACCESSION_PATTERN.fullmatch(observation.accession) is not None
        and observation.metadata_limitations == ()
    )


def _instant_rows(all_assets, issues, cik, target_date, other_date, *, missing, nonfinite):
    """Keep each instant's unit/value failures separate from the other instant."""
    reason = CurrentAnnualOpeningClosingAssetsReason
    if not all_assets:
        return (), (reason.EXACT_USD_UNIT_UNAVAILABLE
                    if "ASSETS_EXACT_USD_UNIT_UNAVAILABLE" in issues else missing)
    instant = tuple(row for row in all_assets if row.end == target_date)
    if not instant:
        # Only the other required instant is present: the boundary is missing.
        # Rows at a different/malformed instant cannot substitute for this one.
        return (), (reason.EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE
                    if any(row.end != other_date for row in all_assets) else missing)
    usd = tuple(row for row in instant if row.unit == REVIEWED_UNIT)
    if not usd:
        return (), reason.EXACT_USD_UNIT_UNAVAILABLE
    finite = tuple(row for row in usd
                   if type(row.value) is Decimal and row.value.is_finite())
    if not finite:
        return (), nonfinite
    eligible = tuple(row for row in finite
                     if _eligible(row, concept=ASSETS_CONCEPT, cik=cik, period_end=target_date))
    return eligible, (None if eligible else
                      reason.EXACT_OPENING_CLOSING_INSTANT_PRESENTATION_UNAVAILABLE)


def _supporting_filings(closing_assets_rows, opening_assets_rows, accessions):
    filings = []
    for accession in accessions:
        closing_assets = tuple(row for row in closing_assets_rows if row.accession == accession)
        opening_assets = tuple(row for row in opening_assets_rows if row.accession == accession)
        rows = closing_assets + opening_assets
        filings.append(OpeningClosingAssetsSupportingFiling(
            accession,
            tuple(sorted({row.form for row in rows})),
            tuple(sorted({row.filed for row in rows})),
            tuple(sorted({row.fy for row in rows})),
            tuple(sorted(row.observation_id for row in closing_assets)),
            tuple(sorted(row.observation_id for row in opening_assets)),
        ))
    return tuple(filings)


def _validate_supporting_provenance(
    closing_assets_rows,
    opening_assets_rows,
    accessions,
    filings,
):
    closing_assets_ids = tuple(sorted(row.observation_id for row in closing_assets_rows))
    opening_assets_ids = tuple(sorted(row.observation_id for row in opening_assets_rows))
    if (
        accessions != tuple(sorted(set(accessions)))
        or not accessions
        or len(filings) != len(accessions)
        or tuple(item.accession for item in filings) != accessions
        or closing_assets_ids != tuple(sorted(set(closing_assets_ids)))
        or opening_assets_ids != tuple(sorted(set(opening_assets_ids)))
        or set(closing_assets_ids) & set(opening_assets_ids)
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Canonical selected observation partition required"
        )
    flattened_closing_assets = []
    flattened_opening_assets = []
    for filing in filings:
        if (
            type(filing) is not OpeningClosingAssetsSupportingFiling
            or _ACCESSION_PATTERN.fullmatch(filing.accession) is None
            or len(filing.forms) != 1
            or filing.forms[0] not in ("10-K", "10-K/A")
            or len(filing.filed_dates) != 1
            or not _valid_date(filing.filed_dates[0])
            or len(filing.fiscal_years) != 1
            or type(filing.fiscal_years[0]) is not int
            or not filing.closing_assets_observation_ids
            or filing.closing_assets_observation_ids
            != tuple(sorted(set(filing.closing_assets_observation_ids)))
            or not filing.opening_assets_observation_ids
            or filing.opening_assets_observation_ids
            != tuple(sorted(set(filing.opening_assets_observation_ids)))
            or set(filing.closing_assets_observation_ids)
            & set(filing.opening_assets_observation_ids)
            or any(not _is_hash(value) for value in (
                filing.closing_assets_observation_ids
                + filing.opening_assets_observation_ids
            ))
        ):
            raise CurrentAnnualOpeningClosingAssetsError(
                "Canonical supporting filing provenance required"
            )
        expected_closing_assets = tuple(sorted(
            row.observation_id
            for row in closing_assets_rows
            if row.accession == filing.accession
        ))
        expected_opening_assets = tuple(sorted(
            row.observation_id
            for row in opening_assets_rows
            if row.accession == filing.accession
        ))
        if (
            filing.closing_assets_observation_ids != expected_closing_assets
            or filing.opening_assets_observation_ids != expected_opening_assets
        ):
            raise CurrentAnnualOpeningClosingAssetsError(
                "Supporting filing observation partition mismatch"
            )
        flattened_closing_assets.extend(filing.closing_assets_observation_ids)
        flattened_opening_assets.extend(filing.opening_assets_observation_ids)
    if (
        tuple(sorted(flattened_closing_assets)) != closing_assets_ids
        or tuple(sorted(flattened_opening_assets)) != opening_assets_ids
        or len(flattened_closing_assets) != len(set(flattened_closing_assets))
        or len(flattened_opening_assets) != len(set(flattened_opening_assets))
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Exact selected observation partition required"
        )


def qualify_sec_current_annual_opening_closing_assets(
    archive: SecArchive,
    profile: upstream.OrdinaryCompounderMethodProfileQualification,
) -> CurrentAnnualOpeningClosingAssetsQualification:
    """Qualify two adjacent annual Assets instants without analysis."""
    if (
        type(archive) is not SecArchive
        or type(profile) is not upstream.OrdinaryCompounderMethodProfileQualification
    ):
        raise CurrentAnnualOpeningClosingAssetsError(
            "Exact SecArchive and OrdinaryCompounderMethodProfileQualification required"
        )
    try:
        comparability = _validate_profile_shape(profile)
        established = (
            profile.status is upstream.OrdinaryCompounderProfileStatus.
            ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED
        )
        if established:
            _validate_established_profile(profile, comparability)
        dates = _target_period(
            comparability, require_established=established
        )
        period_start, period_end, opening_date, closing_date = dates
        issuer_key, security_key, source_cik, receipt, route_conflict = _route_context(
            profile, comparability
        )
    except (AttributeError, TypeError, IndexError, ValueError, ArithmeticError) as exc:
        if isinstance(exc, CurrentAnnualOpeningClosingAssetsError):
            raise
        raise CurrentAnnualOpeningClosingAssetsError("Malformed canonical evidence graph") from exc
    mapped = _upstream_status(profile)
    if mapped is not None:
        if route_conflict:
            raise CurrentAnnualOpeningClosingAssetsError(
                "Impossible reconstructed non-established profile route"
            )
        status, reason = mapped
        return _result(
            profile,
            comparability,
            status=status,
            reasons=(reason,),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )
    if not established:
        raise CurrentAnnualOpeningClosingAssetsError(
            "Unknown ordinary-compounder profile state"
        )
    if route_conflict or receipt is None or issuer_key is None or security_key is None:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOpeningClosingAssetsReason.
                CANONICAL_ROUTE_IDENTITY_CONFLICT,
            ),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    try:
        stored = archive.read_receipt(receipt.receipt_id)
        if stored != receipt:
            raise ArchiveError("Embedded receipt differs from archive receipt")
        raw = archive.read_object(stored)
        current = (comparability.upstream_security_eps.upstream_registered_listing_bridge
                   .temporal_boundary.current_evidence)
        replayed = assess_sec_current_evidence(archive, current.request)
        if replayed != current:
            raise CurrentAnnualOpeningClosingAssetsError(
                "Embedded CURRENT series differs from authentic immutable-object replay"
            )
        extraction = extract_assets_liabilities(raw, stored)
    except (ArchiveError, OSError, ArithmeticError, CurrentAuthorityError):
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOpeningClosingAssetsReason.CAPTURE_REPLAY_CONFLICT,
            ),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )
    if extraction.source_cik != source_cik:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            reasons=(CurrentAnnualOpeningClosingAssetsReason.SOURCE_CIK_CONFLICT,),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    if opening_date is None:
        return _result(
            profile, comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNAVAILABLE,
            reasons=(CurrentAnnualOpeningClosingAssetsReason.
                     CANONICAL_OPENING_BALANCE_DATE_UNAVAILABLE,),
            dates=dates, source_cik=source_cik, receipt=receipt,
        )

    all_assets = tuple(row for row in extraction.observations
                       if row.concept == ASSETS_CONCEPT)
    opening_assets_rows, opening_reason = _instant_rows(
        all_assets, extraction.issues, source_cik, opening_date, closing_date,
        missing=CurrentAnnualOpeningClosingAssetsReason.OPENING_ASSETS_UNAVAILABLE,
        nonfinite=CurrentAnnualOpeningClosingAssetsReason.FINITE_OPENING_ASSETS_VALUE_UNAVAILABLE,
    )
    closing_assets_rows, closing_reason = _instant_rows(
        all_assets, extraction.issues, source_cik, closing_date, opening_date,
        missing=CurrentAnnualOpeningClosingAssetsReason.CLOSING_ASSETS_UNAVAILABLE,
        nonfinite=CurrentAnnualOpeningClosingAssetsReason.FINITE_CLOSING_ASSETS_VALUE_UNAVAILABLE,
    )
    unavailable = tuple(reason for reason in (opening_reason, closing_reason)
                        if reason is not None)
    if unavailable:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNAVAILABLE,
            reasons=unavailable,
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    common = tuple(sorted(
        {row.accession for row in closing_assets_rows}
        & {row.accession for row in opening_assets_rows}
    ))
    if not common:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.EVIDENCE_UNAVAILABLE,
            reasons=(
                CurrentAnnualOpeningClosingAssetsReason.
                NO_COMMON_ANNUAL_FILING_ACCESSION,
            ),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    paired_closing_assets = tuple(
        row for row in closing_assets_rows if row.accession in common
    )
    paired_opening_assets = tuple(
        row for row in opening_assets_rows if row.accession in common
    )
    metadata_conflict = any(
        len({
            getattr(row, field)
            for row in paired_closing_assets + paired_opening_assets
            if row.accession == accession
        }) != 1
        for accession in common
        for field in ("form", "filed", "fy")
    )
    if metadata_conflict:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            reasons=(
                CurrentAnnualOpeningClosingAssetsReason.
                COMMON_FILING_METADATA_CONFLICT,
            ),
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    conflicts = []
    closing_assets_values = {row.value for row in paired_closing_assets}
    opening_assets_values = {row.value for row in paired_opening_assets}
    if len(closing_assets_values) > 1:
        conflicts.append(
            CurrentAnnualOpeningClosingAssetsReason.
            COMPETING_CLOSING_ASSETS_VALUES
        )
    if len(opening_assets_values) > 1:
        conflicts.append(
            CurrentAnnualOpeningClosingAssetsReason.
            COMPETING_OPENING_ASSETS_VALUES
        )
    if conflicts:
        return _result(
            profile,
            comparability,
            status=CurrentAnnualOpeningClosingAssetsStatus.SOURCE_CONFLICT,
            reasons=conflicts,
            dates=dates,
            source_cik=source_cik,
            receipt=receipt,
        )

    closing_assets = next(iter(closing_assets_values))
    opening_assets = next(iter(opening_assets_values))
    selected_closing_assets = tuple(
        row for row in paired_closing_assets if row.value == closing_assets
    )
    selected_opening_assets = tuple(
        row for row in paired_opening_assets if row.value == opening_assets
    )
    filings = _supporting_filings(selected_closing_assets, selected_opening_assets, common)
    _validate_supporting_provenance(
        selected_closing_assets, selected_opening_assets, common, filings
    )
    return _result(
        profile,
        comparability,
        status=(
            CurrentAnnualOpeningClosingAssetsStatus.
            OPENING_CLOSING_ASSETS_ESTABLISHED
        ),
        reasons=(),
        dates=dates,
        source_cik=source_cik,
        receipt=receipt,
        closing_assets=closing_assets,
        opening_assets=opening_assets,
        closing_assets_ids=tuple(
            sorted(row.observation_id for row in selected_closing_assets)
        ),
        opening_assets_ids=tuple(
            sorted(row.observation_id for row in selected_opening_assets)
        ),
        accessions=common,
        filings=filings,
        opening_observations=tuple(sorted(selected_opening_assets, key=lambda row: row.observation_id)),
        closing_observations=tuple(sorted(selected_closing_assets, key=lambda row: row.observation_id)),
    )
