"""Offline VFV CURRENT evidence extraction and deterministic qualification.

This is intentionally one Vanguard Canada / product-9563 route.  It does not
calculate Expected Return, provide historical/PIT authority, or define a generic
benchmark abstraction.
"""
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum, StrEnum
from html.parser import HTMLParser
import hashlib
from io import BytesIO
import json
import re

from pypdf import PdfReader

from .source_authority import (
    AvailabilitySemantics,
    PublicationSemantics,
    UseStatus,
    VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1,
    VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1,
    get_source_route,
)
from .vanguard_vfv_archive import (
    VANGUARD_VFV_ACQUISITION_VERSION,
    VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION,
    VanguardVFVArchive,
    VanguardVFVArchiveError,
    VanguardVFVArtifactFamily,
    VanguardVFVArtifactReceipt,
)


VFV_CURRENT_EVIDENCE_CONTRACT_VERSION = (
    "2026-09-30-vfv-current-evidence-foundation-v1"
)
VFV_CURRENT_EXTRACTION_VERSION = (
    "2026-09-30-vfv-current-evidence-extraction-v1"
)
VFV_CURRENT_QUALIFICATION_VERSION = (
    "2026-09-30-vfv-current-evidence-qualification-v1"
)
_HASH = re.compile(r"[0-9a-f]{64}")


class VFVCurrentEvidenceError(ValueError):
    """Programming-contract or archive-integrity failure."""


class VFVCurrentEvidenceStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"


class VFVCurrentEvidenceReason(StrEnum):
    MISSING_REQUIRED_PRIMARY_ARTIFACT = "MISSING_REQUIRED_PRIMARY_ARTIFACT"
    MUTABLE_PAGE_NOT_CAPTURED = "MUTABLE_PAGE_NOT_CAPTURED"
    REPLAY_IDENTITY_MISMATCH = "REPLAY_IDENTITY_MISMATCH"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    TRACKED_INDEX_DISAGREEMENT = "TRACKED_INDEX_DISAGREEMENT"
    PRICE_UNAVAILABLE = "PRICE_UNAVAILABLE"
    REQUIRED_FIELD_UNAVAILABLE = "REQUIRED_FIELD_UNAVAILABLE"
    EXPENSE_PERIOD_AMBIGUOUS = "EXPENSE_PERIOD_AMBIGUOUS"
    SAME_METRIC_SAME_DATE_CONFLICT = "SAME_METRIC_SAME_DATE_CONFLICT"
    FIELD_CHRONOLOGY_INVALID = "FIELD_CHRONOLOGY_INVALID"
    SOURCE_STRUCTURE_UNSUPPORTED = "SOURCE_STRUCTURE_UNSUPPORTED"
    REQUIRED_FIELD_UNSUPPORTED_BY_REVIEWED_FREE_SOURCE = (
        "REQUIRED_FIELD_UNSUPPORTED_BY_REVIEWED_FREE_SOURCE"
    )


class VFVFactRole(StrEnum):
    FUND_NAME = "FUND_NAME"
    SECURITY_UNIT_TYPE = "SECURITY_UNIT_TYPE"
    PRIMARY_LISTING_EXCHANGE = "PRIMARY_LISTING_EXCHANGE"
    TICKER = "TICKER"
    ISIN = "ISIN"
    LISTED_CURRENCY = "LISTED_CURRENCY"
    BASE_CURRENCY = "BASE_CURRENCY"
    TRACKED_ECONOMIC_INDEX = "TRACKED_ECONOMIC_INDEX"
    PERFORMANCE_SERIES_LABEL = "PERFORMANCE_SERIES_LABEL"
    UNDERLYING_VEHICLE_NAME = "UNDERLYING_VEHICLE_NAME"
    UNDERLYING_VEHICLE_DOMICILE = "UNDERLYING_VEHICLE_DOMICILE"
    MARKET_PRICE = "MARKET_PRICE"
    NAV = "NAV"
    MANAGEMENT_FEE = "MANAGEMENT_FEE"
    MER = "MER"
    TER = "TER"
    DISTRIBUTION_FREQUENCY = "DISTRIBUTION_FREQUENCY"
    LATEST_DISTRIBUTION_TYPE = "LATEST_DISTRIBUTION_TYPE"
    LATEST_CASH_DISTRIBUTION = "LATEST_CASH_DISTRIBUTION"
    LATEST_REINVESTMENT_DISTRIBUTION = "LATEST_REINVESTMENT_DISTRIBUTION"
    LATEST_TOTAL_DISTRIBUTION = "LATEST_TOTAL_DISTRIBUTION"
    LATEST_DISTRIBUTION_CURRENCY = "LATEST_DISTRIBUTION_CURRENCY"
    LATEST_DISTRIBUTION_EX_DATE = "LATEST_DISTRIBUTION_EX_DATE"
    LATEST_DISTRIBUTION_RECORD_DATE = "LATEST_DISTRIBUTION_RECORD_DATE"
    LATEST_DISTRIBUTION_PAYMENT_DATE = "LATEST_DISTRIBUTION_PAYMENT_DATE"
    TRAILING_DISTRIBUTION_YIELD = "TRAILING_DISTRIBUTION_YIELD"
    WEIGHTED_PE = "WEIGHTED_PE"


class VFVObservationType(StrEnum):
    ISSUER_DAILY_MARKET_PRICE = "ISSUER_DAILY_MARKET_PRICE"
    ISSUER_DAILY_NAV = "ISSUER_DAILY_NAV"


class VFVFactUnit(StrEnum):
    CAD_PER_ETF_UNIT = "CAD_PER_ETF_UNIT"
    PERCENT = "PERCENT"


class VFVExpensePeriodSemantics(StrEnum):
    ANNUALIZED_PERCENTAGE_AS_OF_DATE = "ANNUALIZED_PERCENTAGE_AS_OF_DATE"
    ANNUAL_RATE_AS_OF_DATE = "ANNUAL_RATE_AS_OF_DATE"


class VFVTrailingYieldSemantics(StrEnum):
    ISSUER_TRAILING_12_MONTH_DISTRIBUTION_YIELD = (
        "ISSUER_TRAILING_12_MONTH_DISTRIBUTION_YIELD"
    )


class VFVValuationMetricSubject(StrEnum):
    FUND_PORTFOLIO = "FUND_PORTFOLIO"


class VFVValuationMetricSemantics(StrEnum):
    PROVIDER_TRAILING_WEIGHTED_P_E = "PROVIDER_TRAILING_WEIGHTED_P_E"


class VFVFactualAuthorityScope(StrEnum):
    CURRENT_ONLY = "CURRENT_ONLY"


class VFVCurrentEvidenceLimitation(StrEnum):
    NO_HISTORICAL_AS_OF_AUTHORITY = "NO_HISTORICAL_AS_OF_AUTHORITY"
    NO_PIT_AUTHORITY = "NO_PIT_AUTHORITY"
    NO_FIRST_PUBLICATION_AUTHORITY = "NO_FIRST_PUBLICATION_AUTHORITY"
    CAPTURE_BOUND_AVAILABILITY = "CAPTURE_BOUND_AVAILABILITY"
    NO_EXECUTABLE_QUOTE_AUTHORITY = "NO_EXECUTABLE_QUOTE_AUTHORITY"
    NO_FORWARD_ESTIMATE_AUTHORITY = "NO_FORWARD_ESTIMATE_AUTHORITY"
    NO_EXPECTED_RETURN_ANALYTICAL_AUTHORITY = (
        "NO_EXPECTED_RETURN_ANALYTICAL_AUTHORITY"
    )
    NO_RECOMMENDATION_OR_ALLOCATION = "NO_RECOMMENDATION_OR_ALLOCATION"
    NO_EXECUTION_OR_PRODUCTION_AUTHORITY = "NO_EXECUTION_OR_PRODUCTION_AUTHORITY"
    VFV_FIRST_ROUTE_ONLY = "VFV_FIRST_ROUTE_ONLY"
    NO_GENERIC_BENCHMARK_AUTHORITY = "NO_GENERIC_BENCHMARK_AUTHORITY"
    PUBLIC_AVAILABILITY_DOES_NOT_ESTABLISH_COMMERCIAL_AUTHORITY = (
        "PUBLIC_AVAILABILITY_DOES_NOT_ESTABLISH_COMMERCIAL_AUTHORITY"
    )
    NO_COMMERCIAL_INGESTION_OR_REDISTRIBUTION_AUTHORITY = (
        "NO_COMMERCIAL_INGESTION_OR_REDISTRIBUTION_AUTHORITY"
    )
    CURRENT_PRIVATE_INTERNAL_RESEARCH_ONLY = "CURRENT_PRIVATE_INTERNAL_RESEARCH_ONLY"
    S_AND_P_REUSE_AUTHORITY_NOT_ESTABLISHED = (
        "S_AND_P_REUSE_AUTHORITY_NOT_ESTABLISHED"
    )
    TMX_NOT_PRIMARY_CORE_SOURCE = "TMX_NOT_PRIMARY_CORE_SOURCE"
    CUSIP_NOT_EXPOSED_BY_THIS_CONTRACT = "CUSIP_NOT_EXPOSED_BY_THIS_CONTRACT"
    NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY = (
        "NO_UNDERLYING_EXPOSURE_CURRENCY_AUTHORITY"
    )
    NO_CURRENCY_HEDGE_STATUS_AUTHORITY = "NO_CURRENCY_HEDGE_STATUS_AUTHORITY"
    NO_FX_COMPARABILITY_AUTHORITY = "NO_FX_COMPARABILITY_AUTHORITY"


_LIMITATIONS = tuple(VFVCurrentEvidenceLimitation)


@dataclass(frozen=True, slots=True)
class VFVFundIdentity:
    fund_name: str
    security_unit_type: str
    primary_listing_exchange: str
    ticker: str
    isin: str
    listed_currency: str
    base_currency: str
    tracked_economic_index: str
    underlying_vehicle_name: str
    underlying_vehicle_domicile: str


@dataclass(frozen=True, slots=True)
class VFVMarketObservation:
    market_price: Decimal
    observation_type: VFVObservationType
    currency: str
    unit: VFVFactUnit
    field_effective_as_of: str
    nav: Decimal | None
    nav_observation_type: VFVObservationType | None
    nav_effective_as_of: str | None


@dataclass(frozen=True, slots=True)
class VFVExpenseFacts:
    management_fee: Decimal
    management_fee_unit: VFVFactUnit
    mer: Decimal
    mer_effective_as_of: str
    mer_period_semantics: VFVExpensePeriodSemantics
    mer_annualized: bool
    mer_unit: VFVFactUnit
    ter: Decimal
    ter_effective_as_of: str
    ter_period_semantics: VFVExpensePeriodSemantics
    ter_annualized: bool
    ter_unit: VFVFactUnit


@dataclass(frozen=True, slots=True)
class VFVDistributionEvent:
    type: str
    cash_distribution_per_unit: Decimal
    reinvestment_distribution_per_unit: Decimal
    total_distribution_per_unit: Decimal
    currency: str
    unit: VFVFactUnit
    ex_date: str
    record_date: str
    payment_date: str


@dataclass(frozen=True, slots=True)
class VFVDistributionFacts:
    distribution_frequency: str
    latest_event: VFVDistributionEvent
    trailing_distribution_yield: Decimal
    trailing_yield_effective_as_of: str
    trailing_yield_semantics: VFVTrailingYieldSemantics
    trailing_yield_unit: VFVFactUnit


@dataclass(frozen=True, slots=True)
class VFVTrailingValuation:
    weighted_pe: Decimal
    metric_subject: VFVValuationMetricSubject
    metric_semantics: VFVValuationMetricSemantics
    field_effective_as_of: str


@dataclass(frozen=True, slots=True)
class VFVFactEvidence:
    role: VFVFactRole
    artifact_receipt_id: str
    artifact_family: VanguardVFVArtifactFamily
    source_url: str
    content_sha256: str
    source_locator: str
    artifact_date: str | None
    field_effective_as_of: str | None
    publication_timestamp: None
    publication_semantics: PublicationSemantics
    availability_timestamp: str
    availability_semantics: AvailabilitySemantics
    retrieved_at: str
    extraction_version: str


@dataclass(frozen=True, slots=True)
class VFVCurrentEvidenceRequest:
    product_page_receipt_id: str
    expected_product_semantic_id: str
    expected_product_evidence_id: str
    etf_facts_receipt_id: str
    expected_etf_facts_semantic_id: str
    expected_etf_facts_evidence_id: str
    factsheet_receipt_id: str
    expected_factsheet_semantic_id: str
    expected_factsheet_evidence_id: str

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not str or _HASH.fullmatch(value) is None:
                raise VFVCurrentEvidenceError("Exact receipt/evidence identity required")


@dataclass(frozen=True, slots=True)
class _ExpenseObservation:
    value: Decimal
    effective_as_of: str | None
    period_semantics: VFVExpensePeriodSemantics | None
    annualized: bool | None
    artifact_family: VanguardVFVArtifactFamily
    role: VFVFactRole


@dataclass(frozen=True, slots=True)
class VFVCurrentArtifactExtraction:
    extraction_version: str
    receipt: VanguardVFVArtifactReceipt
    structure_supported: bool
    artifact_recognized: bool
    document_date: str | None
    fund_name: str | None = None
    security_unit_type: str | None = None
    primary_listing_exchange: str | None = None
    ticker: str | None = None
    isin: str | None = None
    listed_currency: str | None = None
    base_currency: str | None = None
    tracked_economic_index: str | None = None
    performance_series_label: str | None = None
    underlying_vehicle_name: str | None = None
    underlying_vehicle_domicile: str | None = None
    market_price: Decimal | None = None
    market_price_date: str | None = None
    nav: Decimal | None = None
    nav_date: str | None = None
    management_fee: Decimal | None = None
    mer: Decimal | None = None
    mer_effective_as_of: str | None = None
    mer_period_semantics: VFVExpensePeriodSemantics | None = None
    mer_annualized: bool | None = None
    ter: Decimal | None = None
    ter_effective_as_of: str | None = None
    ter_period_semantics: VFVExpensePeriodSemantics | None = None
    ter_annualized: bool | None = None
    distribution_frequency: str | None = None
    latest_distribution_type: str | None = None
    latest_cash_distribution: Decimal | None = None
    latest_reinvestment_distribution: Decimal | None = None
    latest_total_distribution: Decimal | None = None
    latest_distribution_currency: str | None = None
    latest_ex_date: str | None = None
    latest_record_date: str | None = None
    latest_payment_date: str | None = None
    trailing_distribution_yield: Decimal | None = None
    trailing_yield_date: str | None = None
    weighted_pe: Decimal | None = None
    weighted_pe_date: str | None = None
    locators: tuple[tuple[VFVFactRole, str], ...] = ()

    @property
    def semantic_id(self):
        values = {field.name: getattr(self, field.name) for field in fields(self)
                  if field.name not in {"receipt", "locators"}}
        values["artifact_family"] = self.receipt.artifact_family
        values["locators"] = self.locators
        return _identity("vfv-artifact-extraction-semantics", values)

    @property
    def evidence_id(self):
        return _identity("vfv-artifact-extraction-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_id": self.receipt.receipt_id,
            "content_sha256": self.receipt.content_sha256,
            "retrieved_at": self.receipt.retrieved_at,
            "source_url": self.receipt.source_url,
        })

    def locator_for(self, role):
        matches = [locator for candidate, locator in self.locators if candidate is role]
        if len(matches) != 1:
            raise VFVCurrentEvidenceError("Exactly one source locator required")
        return matches[0]


@dataclass(frozen=True, slots=True)
class VFVCurrentEvidenceQualification:
    contract_version: str
    qualification_version: str
    status: VFVCurrentEvidenceStatus
    reasons: tuple[VFVCurrentEvidenceReason, ...]
    factual_authority_scope: VFVFactualAuthorityScope
    identity: VFVFundIdentity | None
    performance_series_label: str | None
    market_observation: VFVMarketObservation | None
    expenses: VFVExpenseFacts | None
    distributions: VFVDistributionFacts | None
    trailing_valuation: VFVTrailingValuation | None
    fact_evidence: tuple[VFVFactEvidence, ...]
    limitations: tuple[VFVCurrentEvidenceLimitation, ...]
    license_status: UseStatus
    use_status: UseStatus
    product_route_factual_hash: str
    document_route_factual_hash: str
    product_route_profile_hash: str
    document_route_profile_hash: str
    product_extraction: VFVCurrentArtifactExtraction
    etf_facts_extraction: VFVCurrentArtifactExtraction
    factsheet_extraction: VFVCurrentArtifactExtraction

    @property
    def latest_capture_at(self):
        values = tuple(item.receipt.retrieved_at for item in (
            self.product_extraction, self.etf_facts_extraction,
            self.factsheet_extraction))
        return max(values, key=lambda value: datetime.fromisoformat(
            value.replace("Z", "+00:00")))

    @property
    def semantic_id(self):
        return _identity("vfv-current-qualification-semantics", {
            "contract_version": self.contract_version,
            "qualification_version": self.qualification_version,
            "status": self.status,
            "reasons": self.reasons,
            "factual_authority_scope": self.factual_authority_scope,
            "identity": self.identity,
            "performance_series_label": self.performance_series_label,
            "market_observation": self.market_observation,
            "expenses": self.expenses,
            "distributions": self.distributions,
            "trailing_valuation": self.trailing_valuation,
            "limitations": self.limitations,
            "product_route_factual_hash": self.product_route_factual_hash,
            "document_route_factual_hash": self.document_route_factual_hash,
            "extraction_semantic_ids": (
                self.product_extraction.semantic_id,
                self.etf_facts_extraction.semantic_id,
                self.factsheet_extraction.semantic_id,
            ),
        })

    @property
    def evidence_id(self):
        return _identity("vfv-current-qualification-evidence", {
            "semantic_id": self.semantic_id,
            "receipt_ids": tuple(item.receipt.receipt_id for item in (
                self.product_extraction,
                self.etf_facts_extraction,
                self.factsheet_extraction,
            )),
            "content_sha256": tuple(item.receipt.content_sha256 for item in (
                self.product_extraction,
                self.etf_facts_extraction,
                self.factsheet_extraction,
            )),
            "retrieved_at": tuple(item.receipt.retrieved_at for item in (
                self.product_extraction,
                self.etf_facts_extraction,
                self.factsheet_extraction,
            )),
            "source_urls": tuple(item.receipt.source_url for item in (
                self.product_extraction,
                self.etf_facts_extraction,
                self.factsheet_extraction,
            )),
            "source_locators": tuple((item.role, item.source_locator)
                                     for item in self.fact_evidence),
            "route_profile_hashes": (
                self.product_route_profile_hash,
                self.document_route_profile_hash,
            ),
            "extraction_evidence_ids": (
                self.product_extraction.evidence_id,
                self.etf_facts_extraction.evidence_id,
                self.factsheet_extraction.evidence_id,
            ),
        })


def _project(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _project(getattr(value, field.name)) for field in fields(value)}
    if type(value) is Decimal:
        if not value.is_finite():
            raise VFVCurrentEvidenceError("Nonfinite Decimal")
        sign, digits, exponent = value.as_tuple()
        digits = list(digits)
        while len(digits) > 1 and digits[-1] == 0:
            digits.pop()
            exponent += 1
        if not any(digits):
            sign, digits, exponent = 0, [0], 0
        return {"decimal_tuple": [sign, list(digits), exponent]}
    if type(value) in (tuple, list):
        return [_project(item) for item in value]
    if type(value) is dict:
        return {key: _project(item) for key, item in value.items()}
    if value is None or type(value) in (str, int, bool):
        return value
    raise VFVCurrentEvidenceError("Unsupported deterministic identity value")


def _identity(domain, value):
    raw = json.dumps(
        _project((VFV_CURRENT_QUALIFICATION_VERSION, domain, value)),
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


class _HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = []
        self.rows = []
        self._row = None
        self._cell = None

    @staticmethod
    def _clean(value):
        return " ".join(value.replace("\xa0", " ").split())

    def handle_starttag(self, tag, _attrs):
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []

    def handle_data(self, data):
        clean = self._clean(data)
        if clean:
            self.lines.append(clean)
            if self._cell is not None:
                self._cell.append(clean)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("td", "th") and self._cell is not None:
            self._row.append(self._clean(" ".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(tuple(self._row))
            self._row = None


def _pdf_text(raw):
    try:
        reader = PdfReader(BytesIO(raw), strict=True)
        if not reader.pages:
            return None
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:  # pypdf normalizes many malformed-input exception classes.
        return None
    return text if text.strip() else None


def _lines(text):
    return tuple(" ".join(line.replace("\xa0", " ").split())
                 for line in text.splitlines() if line.strip())


def _date_value(value):
    if type(value) is not str:
        return None
    cleaned = " ".join(value.replace(",", " ").split())
    for pattern in ("%Y-%m-%d", "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def _decimal(value, *, percent=False, multiple=False, dash_zero=False):
    if type(value) is not str:
        return None
    cleaned = value.strip().replace(",", "").replace("$", "")
    if dash_zero and cleaned in ("-", "—", "–"):
        return Decimal(0)
    if percent:
        cleaned = cleaned.removesuffix("%").strip()
    if multiple:
        cleaned = cleaned.removesuffix("x").strip()
    if re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", cleaned) is None:
        return None
    try:
        result = Decimal(cleaned)
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _search(text, pattern, flags=re.IGNORECASE):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else None


def _money_and_date(text, label):
    pattern = (re.escape(label)
               + r"\s*\(?CAD\)?\s*\$?([0-9][0-9,]*(?:\.[0-9]+)?)"
                 r"(?:(?!\bAs at\b).){0,160}\bAs at\s+([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})")
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None, None
    return _decimal(match.group(1)), _date_value(match.group(2))


def _percent_and_date(text, label):
    pattern = (re.escape(label) + r"\s*([0-9]+(?:\.[0-9]+)?)%"
               r"(?:(?!\bAs at\b).){0,100}\bAs at\s+"
               r"([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})")
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None, None
    return _decimal(match.group(1)), _date_value(match.group(2))


def _locator(role, family):
    prefix = "/html/text" if family is VanguardVFVArtifactFamily.PRODUCT_PAGE else "/pdf/text"
    return prefix + "/" + role.value


def _extract_values(receipt, text, rows=()):
    flat = "\n".join(_lines(text))
    family = receipt.artifact_family
    recognized = "Vanguard S&P 500 Index ETF" in flat and "VFV" in flat
    values = {}
    roles = set()

    def put(name, value, role):
        values[name] = value
        if value is not None:
            roles.add(role)

    put("fund_name", ("Vanguard S&P 500 Index ETF" if
                      "Vanguard S&P 500 Index ETF" in flat else None),
        VFVFactRole.FUND_NAME)
    ticker = _search(
        flat,
        r"\b(?:Ticker[ \t]+symbol|Ticker(?![ \t]+symbol))"
        r"[ \t]*:?[ \t]+([A-Z][A-Z0-9.-]{0,14})\b",
    )
    if ticker is None and re.search(r"\(VFV\)\s+Vanguard S&P 500 Index ETF", flat):
        ticker = "VFV"
    put("ticker", ticker, VFVFactRole.TICKER)
    isin = _search(flat, r"\bISIN\s*:?\s+([A-Z]{2}[A-Z0-9]{9}[0-9])\b")
    put("isin", isin, VFVFactRole.ISIN)
    exchange = _search(flat, r"\b(?:Exchanges?|Primary listing exchange)[ \t]*:?[ \t]+"
                              r"(Toronto\s+Stock\s+Exchange|TSX)\b")
    if exchange is None:
        exchange = _search(
            flat,
            r"\b(?:Exchanges?|Primary listing exchange)[ \t]*:?[ \t]+([^\n]+)",
        )
    if exchange == "TSX":
        exchange = "Toronto Stock Exchange"
    elif exchange is not None and re.fullmatch(
            r"Toronto\s+Stock\s+Exchange", exchange, re.IGNORECASE):
        exchange = "Toronto Stock Exchange"
    put("primary_listing_exchange", exchange, VFVFactRole.PRIMARY_LISTING_EXCHANGE)
    listed = _search(
        flat,
        r"\b(?:Listed currencies|Listed currency|Currency)[ \t]*:?[ \t]+(CAD|USD)\b",
    )
    put("listed_currency", listed, VFVFactRole.LISTED_CURRENCY)
    base = _search(flat, r"\bBase currency\s*:?\s+(CAD|USD)\b")
    put("base_currency", base, VFVFactRole.BASE_CURRENCY)
    unit = None
    if re.search(r"\bETF Units\b|\bunits of the ETF\b", flat, re.IGNORECASE):
        unit = "ETF Units"
    put("security_unit_type", unit, VFVFactRole.SECURITY_UNIT_TYPE)
    tracked = _search(
        flat,
        r"\btrack(?:s|ed|ing)?\b[^.\n]{0,120}?\b"
        r"([A-Z][A-Za-z0-9&/ .-]{1,80} Index)\b",
    )
    if tracked is None:
        tracked = _search(flat, r"\bBenchmark\s*:?\s+([^\n]{1,100}? Index)\b")
    if tracked is not None and tracked.casefold().startswith("the "):
        tracked = tracked[4:]
    put("tracked_economic_index", tracked, VFVFactRole.TRACKED_ECONOMIC_INDEX)
    performance = _search(
        flat,
        r"\bPerformance series label\s*:?\s+([^\n]+)",
    )
    if performance is None:
        performance = _search(flat, r"\bBenchmark\s*:?\s+(S&P 500 \(CAD NY Rate\) NTR 15%)")
    put("performance_series_label", performance,
        VFVFactRole.PERFORMANCE_SERIES_LABEL)
    underlying = None
    domicile = None
    if re.search(r"\bU\.S\.-domiciled Vanguard S&P 500 ETF\b", flat, re.IGNORECASE):
        underlying = "Vanguard S&P 500 ETF"
        domicile = "United States"
    put("underlying_vehicle_name", underlying, VFVFactRole.UNDERLYING_VEHICLE_NAME)
    put("underlying_vehicle_domicile", domicile,
        VFVFactRole.UNDERLYING_VEHICLE_DOMICILE)

    document_date = None
    if family is VanguardVFVArtifactFamily.FACTSHEET:
        raw_date = _search(flat, r"\bFactsheet\s*\|\s*([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})")
        document_date = _date_value(raw_date)
    elif family is VanguardVFVArtifactFamily.ETF_FACTS:
        raw_date = _search(
            flat,
            r"Vanguard S&P 500 Index ETF\s+([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
        )
        document_date = _date_value(raw_date)

    market_price, market_date = _money_and_date(flat, "Market price")
    nav, nav_date = _money_and_date(flat, "Nav Price")
    if nav is None:
        nav, nav_date = _money_and_date(flat, "NAV price")
    put("market_price", market_price, VFVFactRole.MARKET_PRICE)
    values["market_price_date"] = market_date
    put("nav", nav, VFVFactRole.NAV)
    values["nav_date"] = nav_date

    management = _search(flat, r"\bManagement fee\*?\s*:?\s+([0-9]+(?:\.[0-9]+)?%)")
    put("management_fee", _decimal(management, percent=True), VFVFactRole.MANAGEMENT_FEE)
    mer = _search(flat, r"\b(?:Management Expense Ratio \(MER\)|MER(?:\u2020)?)\s*:?\s+"
                        r"([0-9]+(?:\.[0-9]+)?%)")
    ter = _search(flat, r"\b(?:Trading Expense Ratio \(TER\)|TER)\s*:?\s+"
                        r"([0-9]+(?:\.[0-9]+)?%)")
    mer_period = _date_value(_search(flat, r"\bMER period end\s*:?\s+([^\n]+)"))
    ter_period = _date_value(_search(flat, r"\bTER period end\s*:?\s+([^\n]+)"))
    mer_period_semantics = None
    mer_annualized = None
    ter_period_semantics = None
    ter_annualized = None
    factsheet_mer_period = _date_value(_search(
        flat,
        r"MER\)?[ \t]+is the MER as of "
        r"([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})",
    ))
    if (factsheet_mer_period is not None
            and re.search(r"expressed as an annualized percentage", flat,
                          re.IGNORECASE)):
        mer_period = factsheet_mer_period
        mer_period_semantics = (
            VFVExpensePeriodSemantics.ANNUALIZED_PERCENTAGE_AS_OF_DATE
        )
        mer_annualized = True
    expense_period = _date_value(_search(
        flat, r"\bAs of ([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}), the ETF's expenses"))
    annual_rate = re.search(
        r"\bAnnual rate\s*\(as a % of the ETF[’']s value\)", flat,
        re.IGNORECASE,
    )
    if expense_period is not None and annual_rate:
        if mer_period is None:
            mer_period = expense_period
        if ter_period is None:
            ter_period = expense_period
        mer_period_semantics = VFVExpensePeriodSemantics.ANNUAL_RATE_AS_OF_DATE
        mer_annualized = True
        ter_period_semantics = VFVExpensePeriodSemantics.ANNUAL_RATE_AS_OF_DATE
        ter_annualized = True
    put("mer", _decimal(mer, percent=True), VFVFactRole.MER)
    values["mer_effective_as_of"] = mer_period
    values["mer_period_semantics"] = mer_period_semantics
    values["mer_annualized"] = mer_annualized
    put("ter", _decimal(ter, percent=True), VFVFactRole.TER)
    values["ter_effective_as_of"] = ter_period
    values["ter_period_semantics"] = ter_period_semantics
    values["ter_annualized"] = ter_annualized

    frequency = _search(flat, r"\bDistribution (?:frequency|schedule)\s*:?\s+([A-Za-z]+)")
    put("distribution_frequency", frequency, VFVFactRole.DISTRIBUTION_FREQUENCY)
    trailing, trailing_date = _percent_and_date(flat, "12 month trailing yield")
    if trailing is None:
        match = re.search(
            r"12 month trailing yield\s*([0-9]+(?:\.[0-9]+)?)%\s*\(?"
            r"([A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4})\)?",
            flat, re.IGNORECASE | re.DOTALL)
        if match:
            trailing = _decimal(match.group(1))
            trailing_date = _date_value(match.group(2))
    put("trailing_distribution_yield", trailing,
        VFVFactRole.TRAILING_DISTRIBUTION_YIELD)
    values["trailing_yield_date"] = trailing_date

    event = None
    for row in rows:
        if len(row) == 7 and _date_value(row[1]) and _date_value(row[2]) and _date_value(row[3]):
            event = row
            break
    if event is None:
        labels = (
            "Latest distribution type", "Latest ex-date", "Latest record date",
            "Latest payment date", "Latest cash distribution per unit",
            "Latest reinvestment distribution per unit", "Latest total distribution per unit",
        )
        captured = [_search(flat, rf"\b{re.escape(label)}\s*:?\s+([^\n]+)")
                    for label in labels]
        if all(value is not None for value in captured):
            event = (captured[0], captured[1], captured[2], captured[3],
                     captured[4], captured[5], captured[6])
    if event is not None:
        event_type, ex_date, record_date, payment_date, cash, reinvestment, total = event
        put("latest_distribution_type", event_type,
            VFVFactRole.LATEST_DISTRIBUTION_TYPE)
        put("latest_cash_distribution", _decimal(cash, dash_zero=True),
            VFVFactRole.LATEST_CASH_DISTRIBUTION)
        put("latest_reinvestment_distribution", _decimal(reinvestment, dash_zero=True),
            VFVFactRole.LATEST_REINVESTMENT_DISTRIBUTION)
        put("latest_total_distribution", _decimal(total, dash_zero=True),
            VFVFactRole.LATEST_TOTAL_DISTRIBUTION)
        values["latest_distribution_currency"] = "CAD"
        roles.add(VFVFactRole.LATEST_DISTRIBUTION_CURRENCY)
        put("latest_ex_date", _date_value(ex_date),
            VFVFactRole.LATEST_DISTRIBUTION_EX_DATE)
        put("latest_record_date", _date_value(record_date),
            VFVFactRole.LATEST_DISTRIBUTION_RECORD_DATE)
        put("latest_payment_date", _date_value(payment_date),
            VFVFactRole.LATEST_DISTRIBUTION_PAYMENT_DATE)

    pe = _search(flat, r"\b(?:Weighted P/E|Price/earnings ratio)\s*:?\s+"
                       r"([0-9]+(?:\.[0-9]+)?x)")
    put("weighted_pe", _decimal(pe, multiple=True), VFVFactRole.WEIGHTED_PE)
    values["weighted_pe_date"] = document_date

    locators = tuple(sorted(
        ((role, _locator(role, family)) for role in roles),
        key=lambda item: item[0].value,
    ))
    return VFVCurrentArtifactExtraction(
        VFV_CURRENT_EXTRACTION_VERSION,
        receipt,
        True,
        recognized,
        document_date,
        **values,
        locators=locators,
    )


def extract_vfv_current_artifact(
    archive: VanguardVFVArchive, receipt_id: str,
) -> VFVCurrentArtifactExtraction:
    """Replay one exact receipt; never scan the archive or select latest."""
    if type(archive) is not VanguardVFVArchive:
        raise VFVCurrentEvidenceError("Exact VanguardVFVArchive required")
    try:
        receipt = archive.read_receipt(receipt_id)
        raw = archive.read_object(receipt)
    except VanguardVFVArchiveError as exc:
        raise VFVCurrentEvidenceError("VFV archive integrity failure") from exc
    if receipt.artifact_family is VanguardVFVArtifactFamily.PRODUCT_PAGE:
        try:
            parser = _HTMLText()
            parser.feed(raw.decode("utf-8", "strict"))
            parser.close()
            text = "\n".join(parser.lines)
            return _extract_values(receipt, text, parser.rows)
        except (UnicodeError, ValueError):
            pass
    else:
        text = _pdf_text(raw)
        if text is not None:
            return _extract_values(receipt, text)
    return VFVCurrentArtifactExtraction(
        VFV_CURRENT_EXTRACTION_VERSION,
        receipt,
        False,
        False,
        None,
    )


def _route_profiles():
    product = get_source_route(VANGUARD_CANADA_VFV_PRODUCT_CURRENT_V1)
    document = get_source_route(VANGUARD_CANADA_VFV_DOCUMENT_CURRENT_V1)
    for profile in (product, document):
        if (profile.required_acquisition_contract != VANGUARD_VFV_ACQUISITION_VERSION
                or profile.required_capture_contract
                != VANGUARD_VFV_ARTIFACT_RECEIPT_VERSION
                or profile.required_extraction_contract != VFV_CURRENT_EXTRACTION_VERSION
                or profile.required_resolution_contract != VFV_CURRENT_QUALIFICATION_VERSION
                or profile.required_resolver_version
                != VFV_CURRENT_EVIDENCE_CONTRACT_VERSION):
            raise VFVCurrentEvidenceError("VFV source-route contract pin mismatch")
    return product, document


def _agreement(values):
    present = {value for value in values if value is not None}
    return None if not present else (next(iter(present)) if len(present) == 1 else False)


def _as_date(value):
    try:
        return date.fromisoformat(value) if value is not None else None
    except ValueError:
        return None


def _retrieval_date(extraction):
    try:
        return datetime.fromisoformat(
            extraction.receipt.retrieved_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _select_expense(observations):
    dated = [item for item in observations if item.value is not None
             and item.effective_as_of is not None
             and item.period_semantics is not None
             and item.annualized is not None]
    if not dated:
        return None
    return max(dated, key=lambda item: item.effective_as_of)


def _fact_evidence(extraction, role, field_date):
    receipt = extraction.receipt
    return VFVFactEvidence(
        role,
        receipt.receipt_id,
        receipt.artifact_family,
        receipt.source_url,
        receipt.content_sha256,
        extraction.locator_for(role),
        receipt.artifact_date,
        field_date,
        None,
        PublicationSemantics.UNKNOWN,
        receipt.retrieved_at,
        AvailabilitySemantics.CAPTURE_BOUND,
        receipt.retrieved_at,
        extraction.extraction_version,
    )


def _blank_result(product, etf, factsheet, status, reasons, routes):
    product_route, document_route = routes
    return VFVCurrentEvidenceQualification(
        VFV_CURRENT_EVIDENCE_CONTRACT_VERSION,
        VFV_CURRENT_QUALIFICATION_VERSION,
        status,
        tuple(sorted(reasons, key=lambda item: item.value)),
        VFVFactualAuthorityScope.CURRENT_ONLY,
        None, None, None, None, None, None,
        (),
        _LIMITATIONS,
        product_route.license_status,
        product_route.use_status,
        product_route.factual_hash,
        document_route.factual_hash,
        product_route.profile_hash,
        document_route.profile_hash,
        product, etf, factsheet,
    )


def qualify_vfv_current_evidence(
    archive: VanguardVFVArchive,
    request: VFVCurrentEvidenceRequest,
) -> VFVCurrentEvidenceQualification:
    """Freshly replay all three exact artifacts and qualify CURRENT facts only."""
    if (type(archive) is not VanguardVFVArchive
            or type(request) is not VFVCurrentEvidenceRequest):
        raise VFVCurrentEvidenceError("Exact archive and typed request required")
    product = extract_vfv_current_artifact(archive, request.product_page_receipt_id)
    etf = extract_vfv_current_artifact(archive, request.etf_facts_receipt_id)
    factsheet = extract_vfv_current_artifact(archive, request.factsheet_receipt_id)
    routes = _route_profiles()

    conflicts = set()
    unsupported = set()
    unavailable = set()
    expected = (
        (product, request.expected_product_semantic_id,
         request.expected_product_evidence_id),
        (etf, request.expected_etf_facts_semantic_id,
         request.expected_etf_facts_evidence_id),
        (factsheet, request.expected_factsheet_semantic_id,
         request.expected_factsheet_evidence_id),
    )
    if any(item.semantic_id != semantic or item.evidence_id != evidence
           for item, semantic, evidence in expected):
        conflicts.add(VFVCurrentEvidenceReason.REPLAY_IDENTITY_MISMATCH)
    if (product.receipt.artifact_family is not VanguardVFVArtifactFamily.PRODUCT_PAGE
            or etf.receipt.artifact_family is not VanguardVFVArtifactFamily.ETF_FACTS
            or factsheet.receipt.artifact_family is not VanguardVFVArtifactFamily.FACTSHEET):
        unavailable.add(VFVCurrentEvidenceReason.MISSING_REQUIRED_PRIMARY_ARTIFACT)
        unavailable.add(VFVCurrentEvidenceReason.MUTABLE_PAGE_NOT_CAPTURED)
    if (etf.receipt.parent_product_receipt_id != product.receipt.receipt_id
            or factsheet.receipt.parent_product_receipt_id != product.receipt.receipt_id):
        conflicts.add(VFVCurrentEvidenceReason.REPLAY_IDENTITY_MISMATCH)
    if not all(item.structure_supported for item in (product, etf, factsheet)):
        unsupported.add(VFVCurrentEvidenceReason.SOURCE_STRUCTURE_UNSUPPORTED)
    if not all(item.artifact_recognized for item in (product, etf, factsheet)):
        unavailable.add(VFVCurrentEvidenceReason.MISSING_REQUIRED_PRIMARY_ARTIFACT)

    etf_primary_identity = (
        ("fund_name", VFVFactRole.FUND_NAME),
        ("security_unit_type", VFVFactRole.SECURITY_UNIT_TYPE),
        ("primary_listing_exchange", VFVFactRole.PRIMARY_LISTING_EXCHANGE),
        ("ticker", VFVFactRole.TICKER),
        ("listed_currency", VFVFactRole.LISTED_CURRENCY),
        ("tracked_economic_index", VFVFactRole.TRACKED_ECONOMIC_INDEX),
    )
    etf_locator_roles = {role for role, _locator_value in etf.locators}
    if any(getattr(etf, name) is None or role not in etf_locator_roles
           for name, role in etf_primary_identity):
        unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)

    identity_specs = (
        ("fund_name", "Vanguard S&P 500 Index ETF"),
        ("security_unit_type", "ETF Units"),
        ("primary_listing_exchange", "Toronto Stock Exchange"),
        ("ticker", "VFV"),
        ("isin", "CA92205Y1051"),
        ("listed_currency", "CAD"),
        ("base_currency", "CAD"),
        ("underlying_vehicle_name", "Vanguard S&P 500 ETF"),
        ("underlying_vehicle_domicile", "United States"),
    )
    identity_values = {}
    for name, reviewed in identity_specs:
        values = [getattr(item, name) for item in (etf, product, factsheet)
                  if getattr(item, name) is not None]
        agreed = _agreement(values)
        if agreed is False or (agreed is not None and agreed != reviewed):
            conflicts.add(VFVCurrentEvidenceReason.IDENTITY_MISMATCH)
        if agreed is None:
            unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)
        identity_values[name] = agreed if isinstance(agreed, str) else None

    indexes = [item.tracked_economic_index for item in (etf, product, factsheet)
               if item.tracked_economic_index is not None]
    tracked = _agreement(indexes)
    if tracked is False or (tracked is not None and tracked != "S&P 500 Index"):
        conflicts.add(VFVCurrentEvidenceReason.TRACKED_INDEX_DISAGREEMENT)
    if tracked is None:
        unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)
    identity_values["tracked_economic_index"] = tracked if isinstance(tracked, str) else None

    if product.market_price is None or product.market_price_date is None:
        unavailable.add(VFVCurrentEvidenceReason.PRICE_UNAVAILABLE)

    mer_observations = tuple(
        _ExpenseObservation(item.mer, item.mer_effective_as_of,
                            item.mer_period_semantics, item.mer_annualized,
                            item.receipt.artifact_family, VFVFactRole.MER)
        for item in (product, etf, factsheet) if item.mer is not None
    )
    ter_observations = tuple(
        _ExpenseObservation(item.ter, item.ter_effective_as_of,
                            item.ter_period_semantics, item.ter_annualized,
                            item.receipt.artifact_family, VFVFactRole.TER)
        for item in (product, etf, factsheet) if item.ter is not None
    )
    for observations in (mer_observations, ter_observations):
        by_semantic_period = {}
        for item in observations:
            if item.effective_as_of is not None and item.period_semantics is not None:
                key = (item.effective_as_of, item.period_semantics, item.annualized)
                by_semantic_period.setdefault(key, set()).add(item.value)
        if any(len(values) > 1 for values in by_semantic_period.values()):
            conflicts.add(VFVCurrentEvidenceReason.SAME_METRIC_SAME_DATE_CONFLICT)
    mer_choice = _select_expense(mer_observations)
    ter_choice = _select_expense(ter_observations)
    if mer_observations and mer_choice is None or ter_observations and ter_choice is None:
        unavailable.add(VFVCurrentEvidenceReason.EXPENSE_PERIOD_AMBIGUOUS)
    if (factsheet.management_fee is None and product.management_fee is None
            and etf.management_fee is None) or mer_choice is None or ter_choice is None:
        unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)

    required_product = (
        product.distribution_frequency,
        product.latest_distribution_type,
        product.latest_cash_distribution,
        product.latest_reinvestment_distribution,
        product.latest_total_distribution,
        product.latest_distribution_currency,
        product.latest_ex_date,
        product.latest_record_date,
        product.latest_payment_date,
        product.trailing_distribution_yield,
        product.trailing_yield_date,
    )
    if any(value is None for value in required_product):
        unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)
    if factsheet.weighted_pe is None or factsheet.weighted_pe_date is None:
        unavailable.add(VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE)

    chronology = False
    dated_fields = (
        (product.market_price_date, product),
        (product.nav_date, product),
        (product.trailing_yield_date, product),
        (etf.document_date, etf),
        (factsheet.document_date, factsheet),
        (factsheet.weighted_pe_date, factsheet),
        (mer_choice.effective_as_of if mer_choice else None,
         {item.receipt.artifact_family: item for item in (product, etf, factsheet)}.get(
             mer_choice.artifact_family) if mer_choice else product),
        (ter_choice.effective_as_of if ter_choice else None,
         {item.receipt.artifact_family: item for item in (product, etf, factsheet)}.get(
             ter_choice.artifact_family) if ter_choice else product),
    )
    for field_date, item in dated_fields:
        parsed = _as_date(field_date)
        retrieved = _retrieval_date(item)
        if field_date is not None and (parsed is None or retrieved is None or parsed > retrieved):
            chronology = True
    event_dates = tuple(_as_date(value) for value in (
        product.latest_ex_date, product.latest_record_date, product.latest_payment_date))
    if all(event_dates):
        product_retrieved = _retrieval_date(product)
        payment_explicit = (
            VFVFactRole.LATEST_DISTRIBUTION_PAYMENT_DATE
            in {role for role, _locator_value in product.locators}
        )
        if (not (event_dates[0] <= event_dates[1] <= event_dates[2])
                or product_retrieved is None
                or event_dates[0] > product_retrieved
                or event_dates[1] > product_retrieved
                or (event_dates[2] > product_retrieved and not payment_explicit)):
            chronology = True
    if chronology:
        conflicts.add(VFVCurrentEvidenceReason.FIELD_CHRONOLOGY_INVALID)

    if conflicts:
        return _blank_result(product, etf, factsheet,
                             VFVCurrentEvidenceStatus.SOURCE_CONFLICT,
                             conflicts, routes)
    if unsupported:
        return _blank_result(product, etf, factsheet,
                             VFVCurrentEvidenceStatus.UNSUPPORTED,
                             unsupported, routes)
    if unavailable:
        return _blank_result(product, etf, factsheet,
                             VFVCurrentEvidenceStatus.UNAVAILABLE,
                             unavailable, routes)

    identity = VFVFundIdentity(**identity_values)
    management_source = next(item for item in (factsheet, product, etf)
                             if item.management_fee is not None)
    family_map = {item.receipt.artifact_family: item for item in (product, etf, factsheet)}
    mer_source = family_map[mer_choice.artifact_family]
    ter_source = family_map[ter_choice.artifact_family]
    market = VFVMarketObservation(
        product.market_price,
        VFVObservationType.ISSUER_DAILY_MARKET_PRICE,
        "CAD",
        VFVFactUnit.CAD_PER_ETF_UNIT,
        product.market_price_date,
        product.nav,
        (VFVObservationType.ISSUER_DAILY_NAV if product.nav is not None else None),
        product.nav_date,
    )
    expenses = VFVExpenseFacts(
        management_source.management_fee,
        VFVFactUnit.PERCENT,
        mer_choice.value,
        mer_choice.effective_as_of,
        mer_choice.period_semantics,
        mer_choice.annualized,
        VFVFactUnit.PERCENT,
        ter_choice.value,
        ter_choice.effective_as_of,
        ter_choice.period_semantics,
        ter_choice.annualized,
        VFVFactUnit.PERCENT,
    )
    event = VFVDistributionEvent(
        product.latest_distribution_type,
        product.latest_cash_distribution,
        product.latest_reinvestment_distribution,
        product.latest_total_distribution,
        product.latest_distribution_currency,
        VFVFactUnit.CAD_PER_ETF_UNIT,
        product.latest_ex_date,
        product.latest_record_date,
        product.latest_payment_date,
    )
    distributions = VFVDistributionFacts(
        product.distribution_frequency,
        event,
        product.trailing_distribution_yield,
        product.trailing_yield_date,
        VFVTrailingYieldSemantics.ISSUER_TRAILING_12_MONTH_DISTRIBUTION_YIELD,
        VFVFactUnit.PERCENT,
    )
    valuation = VFVTrailingValuation(
        factsheet.weighted_pe,
        VFVValuationMetricSubject.FUND_PORTFOLIO,
        VFVValuationMetricSemantics.PROVIDER_TRAILING_WEIGHTED_P_E,
        factsheet.weighted_pe_date,
    )
    evidence_sources = {
        VFVFactRole.FUND_NAME: (etf, etf.document_date),
        VFVFactRole.SECURITY_UNIT_TYPE: (etf, etf.document_date),
        VFVFactRole.PRIMARY_LISTING_EXCHANGE: (etf, etf.document_date),
        VFVFactRole.TICKER: (etf, etf.document_date),
        VFVFactRole.ISIN: (factsheet if factsheet.isin else product,
                           factsheet.document_date if factsheet.isin else None),
        VFVFactRole.LISTED_CURRENCY: (etf, etf.document_date),
        VFVFactRole.BASE_CURRENCY: (product, None),
        VFVFactRole.TRACKED_ECONOMIC_INDEX: (etf, etf.document_date),
        VFVFactRole.UNDERLYING_VEHICLE_NAME: (product, None),
        VFVFactRole.UNDERLYING_VEHICLE_DOMICILE: (product, None),
        VFVFactRole.MARKET_PRICE: (product, product.market_price_date),
        VFVFactRole.MANAGEMENT_FEE: (management_source,
                                     management_source.document_date),
        VFVFactRole.MER: (mer_source, mer_choice.effective_as_of),
        VFVFactRole.TER: (ter_source, ter_choice.effective_as_of),
        VFVFactRole.DISTRIBUTION_FREQUENCY: (product, None),
        VFVFactRole.LATEST_DISTRIBUTION_TYPE: (product, product.latest_ex_date),
        VFVFactRole.LATEST_CASH_DISTRIBUTION: (product, product.latest_ex_date),
        VFVFactRole.LATEST_REINVESTMENT_DISTRIBUTION: (product, product.latest_ex_date),
        VFVFactRole.LATEST_TOTAL_DISTRIBUTION: (product, product.latest_ex_date),
        VFVFactRole.LATEST_DISTRIBUTION_CURRENCY: (product, product.latest_ex_date),
        VFVFactRole.LATEST_DISTRIBUTION_EX_DATE: (product, product.latest_ex_date),
        VFVFactRole.LATEST_DISTRIBUTION_RECORD_DATE: (product, product.latest_record_date),
        VFVFactRole.LATEST_DISTRIBUTION_PAYMENT_DATE: (product, product.latest_payment_date),
        VFVFactRole.TRAILING_DISTRIBUTION_YIELD: (product, product.trailing_yield_date),
        VFVFactRole.WEIGHTED_PE: (factsheet, factsheet.weighted_pe_date),
    }
    if product.nav is not None:
        evidence_sources[VFVFactRole.NAV] = (product, product.nav_date)
    if product.performance_series_label is not None:
        evidence_sources[VFVFactRole.PERFORMANCE_SERIES_LABEL] = (product, None)
    fact_evidence = tuple(
        _fact_evidence(source, role, field_date)
        for role, (source, field_date) in sorted(
            evidence_sources.items(), key=lambda item: item[0].value)
    )
    required_roles = set(evidence_sources)
    if len(fact_evidence) != len(required_roles):
        raise VFVCurrentEvidenceError("Exactly one evidence record per fact role required")

    product_route, document_route = routes
    return VFVCurrentEvidenceQualification(
        VFV_CURRENT_EVIDENCE_CONTRACT_VERSION,
        VFV_CURRENT_QUALIFICATION_VERSION,
        VFVCurrentEvidenceStatus.AVAILABLE,
        (),
        VFVFactualAuthorityScope.CURRENT_ONLY,
        identity,
        product.performance_series_label,
        market,
        expenses,
        distributions,
        valuation,
        fact_evidence,
        _LIMITATIONS,
        product_route.license_status,
        product_route.use_status,
        product_route.factual_hash,
        document_route.factual_hash,
        product_route.profile_hash,
        document_route.profile_hash,
        product, etf, factsheet,
    )
