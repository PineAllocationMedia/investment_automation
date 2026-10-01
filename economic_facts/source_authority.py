"""Closed source ROUTES, never provider-wide trust or caller-supplied profiles.

The registry describes permitted claims; it does not verify evidence. Only the
route's reviewed adapter may establish them from controlled stored captures.
Usage review is independent of factual authority. No legal permission is inferred.
"""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum
import hashlib
import json

SOURCE_AUTHORITY_VERSION = "2026-09-19-source-route-authority-v1"
SEC_COMPANYFACTS_LIVE_CURRENT_V1 = "SEC_COMPANYFACTS_LIVE_CURRENT_V1"
YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1 = "YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1"
YAHOO_FINANCE_CHART_SPLIT_HISTORY_V1 = "YAHOO_FINANCE_CHART_SPLIT_HISTORY_V1"
VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1 = "VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1"
VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1 = "VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1"


class AuthorityProperty(Enum):
    SOURCE_ACQUISITION_PROVENANCE = "SOURCE_ACQUISITION_PROVENANCE"
    CURRENT_OBSERVED_AVAILABILITY = "CURRENT_OBSERVED_AVAILABILITY"
    SECURITY_SHARE_CLASS_LISTING_IDENTITY = "SECURITY_SHARE_CLASS_LISTING_IDENTITY"
    SHARE_BASIS_COMPARABILITY = "SHARE_BASIS_COMPARABILITY"
    ECONOMIC_REPORTING_SUBJECT_COMPARABILITY = "ECONOMIC_REPORTING_SUBJECT_COMPARABILITY"
    CURRENT_SNAPSHOT_SCOPE = "CURRENT_SNAPSHOT_SCOPE"
    CURRENT_OBSERVED_MARKET_PRICE = "CURRENT_OBSERVED_MARKET_PRICE"
    QUOTE_CURRENCY_AND_UNIT = "QUOTE_CURRENCY_AND_UNIT"
    FINAL_ECONOMIC_ADMISSION = "FINAL_ECONOMIC_ADMISSION"


class ClaimAuthority(Enum):
    TRUSTED_LOCAL_PROCESS = "TRUSTED_LOCAL_PROCESS"


class ClaimRole(Enum):
    PRIMARY = "PRIMARY"


class PublicationSemantics(Enum):
    UNKNOWN = "UNKNOWN"


class AvailabilitySemantics(Enum):
    CAPTURE_BOUND = "CAPTURE_BOUND"


class PITCapability(Enum):
    UNSUPPORTED = "UNSUPPORTED"


class FailurePolicy(Enum):
    FAIL_CLOSED = "FAIL_CLOSED"


class UseStatus(Enum):
    UNKNOWN = "UNKNOWN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class SourceAuthorityReason(Enum):
    INVALID_CONTRACT = "INVALID_CONTRACT"
    UNKNOWN_ROUTE = "UNKNOWN_ROUTE"
    CLAIM_NOT_PERMITTED = "CLAIM_NOT_PERMITTED"


class SourceAuthorityError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason.value)


def _project(value):
    """Exact evidence encoding; no binary64 or Decimal context operations."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {f.name: _project(getattr(value, f.name)) for f in fields(value)}
    if type(value) is Decimal:
        if not value.is_finite():
            raise SourceAuthorityError(SourceAuthorityReason.INVALID_CONTRACT)
        sign, digits, exponent = value.as_tuple()
        return {"decimal_tuple": [sign, list(digits), exponent]}
    if type(value) in (tuple, list):
        return [_project(v) for v in value]
    if type(value) is dict:
        return {k: _project(v) for k, v in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise SourceAuthorityError(SourceAuthorityReason.INVALID_CONTRACT)


def _hash(domain, value):
    raw = json.dumps(_project((SOURCE_AUTHORITY_VERSION, domain, value)),
                     sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ClaimGrant:
    property: AuthorityProperty
    authority: ClaimAuthority
    role: ClaimRole


@dataclass(frozen=True, slots=True)
class SourceRouteProfile:
    route_id: str
    provider: str
    profile_version: str
    jurisdictions: tuple[str, ...]
    permitted_claims: tuple[ClaimGrant, ...]
    verifier_id: str
    required_acquisition_contract: str
    required_capture_contract: str
    required_extraction_contract: str
    required_resolution_contract: str
    required_resolver_version: str
    immutable_capture_required: bool
    publication_semantics: PublicationSemantics
    availability_semantics: AvailabilitySemantics
    pit_capability: PITCapability
    failure_policy: FailurePolicy
    license_status: UseStatus
    use_status: UseStatus

    @property
    def factual_hash(self):
        # Legal metadata cannot increase or otherwise change factual powers.
        factual = {f.name: getattr(self, f.name) for f in fields(self)
                   if f.name not in {"license_status", "use_status"}}
        factual["jurisdictions"] = tuple(sorted(self.jurisdictions))
        factual["permitted_claims"] = tuple(sorted(self.permitted_claims,
                                                   key=lambda c: c.property.value))
        return _hash("route-factual-profile", factual)

    @property
    def profile_hash(self):
        return _hash("route-full-profile", (self.factual_hash, self.license_status, self.use_status))


# Literal contract pins are checked against actual upstream identities by the
# adapter. No SEC objects or identifiers are mandatory fields in the core types.
_ROUTES = (SourceRouteProfile(
    SEC_COMPANYFACTS_LIVE_CURRENT_V1, "SEC", "2026-09-19-companyfacts-current-route-v1",
    ("US",), tuple(ClaimGrant(p, ClaimAuthority.TRUSTED_LOCAL_PROCESS, ClaimRole.PRIMARY)
                  for p in (AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                            AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY,
                            AuthorityProperty.CURRENT_SNAPSHOT_SCOPE)),
    "2026-09-19-sec-current-evidence-verifier-v1",
    "2026-09-11-sec-live-companyfacts-v1", "2026-09-10-sec-capture-receipt-v1",
    "2026-09-10-sec-diluted-eps-extraction-v1", "2026-09-11-sec-annual-diluted-eps-series-v1",
    "2026-09-11-sec-current-reported-consensus-v1", True,
    PublicationSemantics.UNKNOWN, AvailabilitySemantics.CAPTURE_BOUND,
    PITCapability.UNSUPPORTED, FailurePolicy.FAIL_CLOSED,
    UseStatus.UNKNOWN, UseStatus.REVIEW_REQUIRED,
), SourceRouteProfile(
    YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1,
    "YAHOO_FINANCE",
    "2026-09-28-yahoo-chart-current-quote-route-v1",
    ("US",),
    tuple(ClaimGrant(p, ClaimAuthority.TRUSTED_LOCAL_PROCESS, ClaimRole.PRIMARY)
          for p in (AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                    AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY,
                    AuthorityProperty.CURRENT_SNAPSHOT_SCOPE,
                    AuthorityProperty.CURRENT_OBSERVED_MARKET_PRICE,
                    AuthorityProperty.QUOTE_CURRENCY_AND_UNIT)),
    "2026-09-28-yahoo-current-quote-qualification-v1",
    "2026-09-28-yahoo-chart-current-quote-acquisition-v1",
    "2026-09-28-yahoo-quote-receipt-v1",
    "2026-09-28-yahoo-current-quote-extraction-v1",
    "2026-09-28-yahoo-current-quote-qualification-v1",
    "2026-09-28-yahoo-nms-nasdaqgs-usd-equity-v1",
    True,
    PublicationSemantics.UNKNOWN,
    AvailabilitySemantics.CAPTURE_BOUND,
    PITCapability.UNSUPPORTED,
    FailurePolicy.FAIL_CLOSED,
    UseStatus.UNKNOWN,
    UseStatus.REVIEW_REQUIRED,
), SourceRouteProfile(
    YAHOO_FINANCE_CHART_SPLIT_HISTORY_V1,
    "YAHOO_FINANCE",
    "2026-09-29-yahoo-chart-split-history-route-v1",
    ("US",),
    (ClaimGrant(AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                ClaimAuthority.TRUSTED_LOCAL_PROCESS, ClaimRole.PRIMARY),),
    "2026-09-29-yahoo-split-history-extraction-v1",
    "2026-09-29-yahoo-chart-split-history-acquisition-v1",
    "2026-09-29-yahoo-split-history-receipt-v1",
    "2026-09-29-yahoo-split-history-extraction-v1",
    "2026-09-29-free-bounded-share-basis-bridge-v1",
    "2026-09-29-exact-integral-split-events-v1",
    True,
    PublicationSemantics.UNKNOWN,
    AvailabilitySemantics.CAPTURE_BOUND,
    PITCapability.UNSUPPORTED,
    FailurePolicy.FAIL_CLOSED,
    UseStatus.UNKNOWN,
    UseStatus.REVIEW_REQUIRED,
), SourceRouteProfile(
    VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1,
    "VANGUARD_CANADA",
    "2026-09-30-vanguard-vfv-product-current-route-v1",
    ("CA",),
    tuple(ClaimGrant(p, ClaimAuthority.TRUSTED_LOCAL_PROCESS, ClaimRole.PRIMARY)
          for p in (AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                    AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY,
                    AuthorityProperty.CURRENT_SNAPSHOT_SCOPE,
                    AuthorityProperty.CURRENT_OBSERVED_MARKET_PRICE,
                    AuthorityProperty.QUOTE_CURRENCY_AND_UNIT)),
    "2026-09-30-vfv-current-evidence-qualification-v1",
    "2026-09-30-vanguard-vfv-current-acquisition-v1",
    "2026-09-30-vanguard-vfv-artifact-receipt-v1",
    "2026-09-30-vfv-current-evidence-extraction-v1",
    "2026-09-30-vfv-current-evidence-qualification-v1",
    "2026-09-30-vfv-current-evidence-foundation-v1",
    True,
    PublicationSemantics.UNKNOWN,
    AvailabilitySemantics.CAPTURE_BOUND,
    PITCapability.UNSUPPORTED,
    FailurePolicy.FAIL_CLOSED,
    UseStatus.UNKNOWN,
    UseStatus.REVIEW_REQUIRED,
), SourceRouteProfile(
    VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1,
    "VANGUARD_CANADA",
    "2026-09-30-vanguard-vfv-document-current-route-v1",
    ("CA",),
    tuple(ClaimGrant(p, ClaimAuthority.TRUSTED_LOCAL_PROCESS, ClaimRole.PRIMARY)
          for p in (AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                    AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY,
                    AuthorityProperty.CURRENT_SNAPSHOT_SCOPE)),
    "2026-09-30-vfv-current-evidence-qualification-v1",
    "2026-09-30-vanguard-vfv-current-acquisition-v1",
    "2026-09-30-vanguard-vfv-artifact-receipt-v1",
    "2026-09-30-vfv-current-evidence-extraction-v1",
    "2026-09-30-vfv-current-evidence-qualification-v1",
    "2026-09-30-vfv-current-evidence-foundation-v1",
    True,
    PublicationSemantics.UNKNOWN,
    AvailabilitySemantics.CAPTURE_BOUND,
    PITCapability.UNSUPPORTED,
    FailurePolicy.FAIL_CLOSED,
    UseStatus.UNKNOWN,
    UseStatus.REVIEW_REQUIRED,
))


def get_source_route(route_id: str) -> SourceRouteProfile:
    """Only a registered exact route ID; a provider name or profile is not input."""
    if type(route_id) is not str:
        raise SourceAuthorityError(SourceAuthorityReason.INVALID_CONTRACT)
    for profile in _ROUTES:
        if profile.route_id == route_id:
            return profile
    raise SourceAuthorityError(SourceAuthorityReason.UNKNOWN_ROUTE)


def permitted_claim(route_id: str, property: AuthorityProperty) -> ClaimGrant:
    """Look up a route's powers, not proof that any particular fact is true."""
    profile = get_source_route(route_id)
    if type(property) is not AuthorityProperty:
        raise SourceAuthorityError(SourceAuthorityReason.INVALID_CONTRACT)
    for grant in profile.permitted_claims:
        if grant.property is property:
            return grant
    raise SourceAuthorityError(SourceAuthorityReason.CLAIM_NOT_PERMITTED)
