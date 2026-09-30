"""Pure qualified-fact constructor; no acquisition or decisions.

Only exact closed root classes are admitted. Derived nodes are constructor output,
never an input capability. Adapter identities attest semantics, not authenticity
of external documents. The original synthetic contract remains closed; PR5E owns
the only currently supported real-fact construction path.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from enum import Enum
import math
import re
from statistics import median

from . import expected_return_engine as er
from .expected_return_policy import (
    ConstructorContractError, DistributionPolicy, DistributionRule,
    FADE_TRANSFORMATION_ID, HISTORICAL_FADE_WEIGHTS, MatureGrowthPolicy,
    TerminalValuationPolicy, applicable, canonical_hash, iso_date, number,
    require, text, validate_policy,
)

EXPECTED_RETURN_FACTS_CONTRACT_VERSION = "2026-09-09-synthetic-qualified-facts-v1"
EXPECTED_RETURN_REAL_FACTS_CONTRACT_VERSION = "2026-09-30-pr5e-real-qualified-facts-v1"
EXPECTED_RETURN_CONSTRUCTOR_VERSION = "2026-09-09-qualified-history-constructor-v1"


class Profile(Enum):
    ORDINARY_COMPOUNDER = "ORDINARY_COMPOUNDER"
    BANK = "BANK"
    INSURER = "INSURER"
    REIT = "REIT"
    ASSET_MANAGER = "ASSET_MANAGER"
    RESOURCES_MINING = "RESOURCES_MINING"
    ENERGY_CYCLICAL = "ENERGY_CYCLICAL"
    PIPELINE = "PIPELINE"
    UTILITY_ACCOUNTING = "UTILITY_ACCOUNTING"
    INVESTMENT_HOLDING = "INVESTMENT_HOLDING"
    MIXED_CONGLOMERATE = "MIXED_CONGLOMERATE"
    TURNAROUND = "TURNAROUND"
    LOSS_MAKING = "LOSS_MAKING"
    UNKNOWN = "UNKNOWN"


UNSUPPORTED_STRUCTURES = tuple(p for p in Profile if p not in (Profile.ORDINARY_COMPOUNDER, Profile.UNKNOWN))


class AdapterIdentity(Enum):
    SYNTHETIC_OBSERVED_PRICE_V1 = "SYNTHETIC_OBSERVED_PRICE_V1"
    SYNTHETIC_REPORTED_DILUTED_EPS_V1 = "SYNTHETIC_REPORTED_DILUTED_EPS_V1"
    SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1 = "SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1"
    SYNTHETIC_VERIFIED_NONPAYER_V1 = "SYNTHETIC_VERIFIED_NONPAYER_V1"
    SYNTHETIC_PROFILE_QUALIFICATION_V1 = "SYNTHETIC_PROFILE_QUALIFICATION_V1"
    PR5E_REAL_OBSERVED_PRICE_V1 = "PR5E_REAL_OBSERVED_PRICE_V1"
    PR5E_REAL_REPORTED_DILUTED_EPS_V1 = "PR5E_REAL_REPORTED_DILUTED_EPS_V1"
    PR5E_REAL_VERIFIED_NONPAYER_V1 = "PR5E_REAL_VERIFIED_NONPAYER_V1"
    PR5E_REAL_PROFILE_QUALIFICATION_V1 = "PR5E_REAL_PROFILE_QUALIFICATION_V1"


class SourceKind(Enum):
    SYNTHETIC_OFFICIAL = "SYNTHETIC_OFFICIAL"
    SYNTHETIC_MANUAL = "SYNTHETIC_MANUAL"
    SEC_CURRENT = "SEC_CURRENT"
    YAHOO_MARKET_PROVIDER = "YAHOO_MARKET_PROVIDER"


class PublicationSemantics(Enum):
    EXACT = "EXACT"
    UNKNOWN = "UNKNOWN"


class AvailabilitySemantics(Enum):
    EXACT = "EXACT"
    CAPTURE_BOUND = "CAPTURE_BOUND"


@dataclass(frozen=True, slots=True)
class Provenance:
    source_kind: SourceKind
    source_reference: str
    source_version: str
    source_document_hash: str
    source_locator: str
    published_at: str
    available_at: str
    captured_at: str
    extractor_id: AdapterIdentity
    extractor_version: str


@dataclass(frozen=True, slots=True)
class RealProvenance:
    source_kind: SourceKind
    source_reference: str
    source_version: str
    source_document_hash: str
    source_locator: str
    published_at: None
    available_at: str
    captured_at: str
    extractor_id: AdapterIdentity
    extractor_version: str
    publication_semantics: PublicationSemantics
    availability_semantics: AvailabilitySemantics


@dataclass(frozen=True, slots=True)
class Identity:
    observation_id: str
    security_id: str
    share_class: str
    provenance: Provenance | RealProvenance


@dataclass(frozen=True, slots=True)
class ShareBasis:
    currency: str
    share_basis: str


@dataclass(frozen=True, slots=True)
class AnnualPeriod:
    start: str
    end: str


@dataclass(frozen=True, slots=True)
class ObservedPrice:
    identity: Identity
    value: float
    basis: ShareBasis
    observed_on: str


@dataclass(frozen=True, slots=True)
class ReportedDilutedEPS:
    identity: Identity
    value: float
    basis: ShareBasis
    period: AnnualPeriod
    accounting_basis: str


@dataclass(frozen=True, slots=True)
class OrdinaryAnnualDividend:
    """Verified annual ordinary amount, with special distributions explicitly excluded."""
    identity: Identity
    value: float
    basis: ShareBasis
    period: AnnualPeriod
    special_dividends_excluded: bool


@dataclass(frozen=True, slots=True)
class VerifiedNonpayer:
    identity: Identity
    period: AnnualPeriod


@dataclass(frozen=True, slots=True)
class ProfileQualification:
    identity: Identity
    profile: Profile
    excluded_structures: tuple[Profile, ...]
    rationale: str


RootFact = ObservedPrice | ReportedDilutedEPS | OrdinaryAnnualDividend | VerifiedNonpayer | ProfileQualification
ROOT_ADAPTERS = {
    ObservedPrice: frozenset((AdapterIdentity.SYNTHETIC_OBSERVED_PRICE_V1,
                              AdapterIdentity.PR5E_REAL_OBSERVED_PRICE_V1)),
    ReportedDilutedEPS: frozenset((AdapterIdentity.SYNTHETIC_REPORTED_DILUTED_EPS_V1,
                                   AdapterIdentity.PR5E_REAL_REPORTED_DILUTED_EPS_V1)),
    OrdinaryAnnualDividend: frozenset((AdapterIdentity.SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1,)),
    VerifiedNonpayer: frozenset((AdapterIdentity.SYNTHETIC_VERIFIED_NONPAYER_V1,
                                 AdapterIdentity.PR5E_REAL_VERIFIED_NONPAYER_V1)),
    ProfileQualification: frozenset((AdapterIdentity.SYNTHETIC_PROFILE_QUALIFICATION_V1,
                                     AdapterIdentity.PR5E_REAL_PROFILE_QUALIFICATION_V1)),
}
SYNTHETIC_ADAPTERS = frozenset(adapter for adapters in ROOT_ADAPTERS.values()
                               for adapter in adapters if adapter.value.startswith("SYNTHETIC_"))
REAL_ADAPTERS = frozenset(adapter for adapters in ROOT_ADAPTERS.values()
                          for adapter in adapters if adapter.value.startswith("PR5E_REAL_"))
ADAPTER_SOURCE_KINDS = {
    AdapterIdentity.SYNTHETIC_OBSERVED_PRICE_V1: frozenset((SourceKind.SYNTHETIC_OFFICIAL, SourceKind.SYNTHETIC_MANUAL)),
    AdapterIdentity.SYNTHETIC_REPORTED_DILUTED_EPS_V1: frozenset((SourceKind.SYNTHETIC_OFFICIAL, SourceKind.SYNTHETIC_MANUAL)),
    AdapterIdentity.SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1: frozenset((SourceKind.SYNTHETIC_OFFICIAL, SourceKind.SYNTHETIC_MANUAL)),
    AdapterIdentity.SYNTHETIC_VERIFIED_NONPAYER_V1: frozenset((SourceKind.SYNTHETIC_OFFICIAL, SourceKind.SYNTHETIC_MANUAL)),
    AdapterIdentity.SYNTHETIC_PROFILE_QUALIFICATION_V1: frozenset((SourceKind.SYNTHETIC_OFFICIAL, SourceKind.SYNTHETIC_MANUAL)),
    AdapterIdentity.PR5E_REAL_OBSERVED_PRICE_V1: frozenset((SourceKind.YAHOO_MARKET_PROVIDER,)),
    AdapterIdentity.PR5E_REAL_REPORTED_DILUTED_EPS_V1: frozenset((SourceKind.SEC_CURRENT,)),
    AdapterIdentity.PR5E_REAL_VERIFIED_NONPAYER_V1: frozenset((SourceKind.SEC_CURRENT,)),
    AdapterIdentity.PR5E_REAL_PROFILE_QUALIFICATION_V1: frozenset((SourceKind.SEC_CURRENT,)),
}


@dataclass(frozen=True, slots=True)
class QualifiedFacts:
    contract_version: str
    as_of: str
    security_id: str
    share_class: str
    basis: ShareBasis
    accounting_basis: str
    latest_required_fiscal_end: str
    roots: tuple[RootFact, ...]


@dataclass(frozen=True, slots=True)
class LineageNode:
    id: str
    transformation_id: str
    parents: tuple[str, ...]
    root_ids: tuple[str, ...]
    policy_hashes: tuple[str, ...]
    value: float | str | tuple[float, ...]
    available_at: str
    captured_at: str


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    component: str
    root_ids: tuple[str, ...]
    source_authority: str
    freshness: str
    completeness: str
    consistency: str
    assumption_dependence: str
    category: str


@dataclass(frozen=True, slots=True)
class ConstructionResult:
    status: str
    reasons: tuple[str, ...]
    constructor_version: str
    facts_contract_version: str
    policy_hashes: tuple[tuple[str, str], ...]
    input_roots: tuple[RootFact, ...]
    lineage_hash: str
    lineage: tuple[LineageNode, ...]
    component_root_ids: tuple[tuple[str, tuple[str, ...]], ...]
    shared_evidence_roots: tuple[str, ...]
    confidence: tuple[ConfidenceAssessment, ...]
    request: er.ExpectedReturnRequest | None
    diagnostic: er.ExpectedReturnDiagnostic | None


def _timestamp(value: str) -> datetime:
    text(value, "timestamp")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value) is not None,
            "Explicit offset timestamp required")
    if not value.endswith("Z"):
        require(int(value[-5:-3]) < 24 and int(value[-2:]) < 60, "Invalid UTC offset")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ConstructorContractError("Invalid timestamp") from exc


def _basis(value) -> None:
    require(type(value) is ShareBasis, "Typed ShareBasis required")
    require(type(value.currency) is str and re.fullmatch(r"[A-Z]{3}", value.currency) is not None, "Invalid currency")
    text(value.share_basis, "share basis")


def _period(value) -> None:
    require(type(value) is AnnualPeriod, "Typed AnnualPeriod required")
    start, end = iso_date(value.start), iso_date(value.end)
    require((end - start).days in (364, 365), "Only explicit 365/366-day annual periods supported")


def _validate(facts: QualifiedFacts) -> tuple[RootFact, ...]:
    require(type(facts) is QualifiedFacts, "Closed QualifiedFacts input required; no mappings or derived inputs")
    require(facts.contract_version in (EXPECTED_RETURN_FACTS_CONTRACT_VERSION,
                                       EXPECTED_RETURN_REAL_FACTS_CONTRACT_VERSION),
            "Unsupported facts contract")
    real_contract = facts.contract_version == EXPECTED_RETURN_REAL_FACTS_CONTRACT_VERSION
    as_of = _timestamp(facts.as_of)
    for key in ("security_id", "share_class"):
        text(getattr(facts, key), key)
    _basis(facts.basis)
    require(facts.accounting_basis in ("IFRS", "US_GAAP"), "Unsupported accounting basis")
    require(iso_date(facts.latest_required_fiscal_end) <= as_of.date(), "Future required fiscal period")
    require(type(facts.roots) is tuple, "Immutable root tuple required")
    ids, economic_roots, periods = set(), set(), set()
    for root in facts.roots:
        require(type(root) in ROOT_ADAPTERS, "Unsupported root type or caller-supplied transformation")
        identity = root.identity
        require(type(identity) is Identity, "Typed identity required")
        for key in ("observation_id", "security_id", "share_class"):
            text(getattr(identity, key), key)
        require(identity.observation_id not in ids, "Duplicate observation ID")
        ids.add(identity.observation_id)
        require((identity.security_id, identity.share_class) == (facts.security_id, facts.share_class), "Security/share class mismatch")
        provenance = identity.provenance
        require(type(provenance) is (RealProvenance if real_contract else Provenance),
                "Facts contract requires its exact typed provenance")
        require(type(provenance.source_kind) is SourceKind, "Unsupported semantic source kind")
        require(type(provenance.extractor_id) is AdapterIdentity
                and provenance.extractor_id in ROOT_ADAPTERS[type(root)],
                "Root type/semantic source adapter mismatch")
        require(provenance.extractor_id in (REAL_ADAPTERS if real_contract else SYNTHETIC_ADAPTERS),
                "Facts contract/source adapter authority mismatch")
        require(provenance.source_kind in ADAPTER_SOURCE_KINDS[provenance.extractor_id],
                "Source kind/source adapter mismatch")
        require(provenance.extractor_version == "1", "Unsupported source adapter version")
        for key in ("source_reference", "source_version", "source_locator"):
            text(getattr(provenance, key), key)
        require(type(provenance.source_document_hash) is str
                and re.fullmatch(r"[0-9a-f]{64}", provenance.source_document_hash) is not None, "SHA-256 document hash required")
        available, captured = (_timestamp(getattr(provenance, key))
                               for key in ("available_at", "captured_at"))
        if type(provenance) is Provenance:
            published = _timestamp(provenance.published_at)
            require(published <= available, "Publication cannot follow availability")
        else:
            require(type(provenance.publication_semantics) is PublicationSemantics
                    and provenance.publication_semantics is PublicationSemantics.UNKNOWN,
                    "Real provenance requires UNKNOWN publication semantics")
            require(type(provenance.availability_semantics) is AvailabilitySemantics
                    and provenance.availability_semantics is AvailabilitySemantics.CAPTURE_BOUND,
                    "Real provenance requires CAPTURE_BOUND availability semantics")
            require(provenance.published_at is None, "Unknown publication requires published_at=None")
            published = None
            require(available == captured,
                    "Capture-bound availability must equal the exact capture timestamp")
        require(available <= captured <= as_of, "Invalid availability/capture chronology")
        economic_key = (identity.security_id, identity.share_class, provenance.source_document_hash,
                        provenance.source_locator, provenance.extractor_id)
        require(economic_key not in economic_roots, "Duplicate economic root under another wrapper")
        economic_roots.add(economic_key)
        if type(root) in (ObservedPrice, ReportedDilutedEPS, OrdinaryAnnualDividend):
            _basis(root.basis)
            require(root.basis == facts.basis, "Inconsistent currency/split/share basis")
            number(root.value, "root value")
        if type(root) is ObservedPrice:
            require(root.value > 0, "Observed price must be positive")
            require(iso_date(root.observed_on) <= (published or available).date(),
                    "Price observation after evidence boundary")
        elif type(root) in (ReportedDilutedEPS, OrdinaryAnnualDividend, VerifiedNonpayer):
            _period(root.period)
            require(iso_date(root.period.end) <= (published or available).date(),
                    "Reported fiscal period after evidence boundary")
            period_key = (type(root), root.period.end)
            require(period_key not in periods, "Duplicate fiscal period / unresolved revision")
            periods.add(period_key)
            if type(root) is ReportedDilutedEPS:
                require(root.accounting_basis == facts.accounting_basis, "Inconsistent accounting basis")
                require(root.period.end <= facts.latest_required_fiscal_end, "EPS later than declared latest required period")
            if type(root) is OrdinaryAnnualDividend:
                require(root.value >= 0, "Negative annual dividend")
                require(root.special_dividends_excluded is True, "Ordinary dividend must explicitly exclude specials")
        else:
            require(type(root.profile) is Profile, "Typed profile required")
            require(type(root.excluded_structures) is tuple and all(type(p) is Profile for p in root.excluded_structures), "Typed exclusion tuple required")
            require(len(set(root.excluded_structures)) == len(root.excluded_structures), "Duplicate profile exclusions")
            require(root.profile not in root.excluded_structures, "Profile contradicts exclusions")
            text(root.rationale, "profile qualification rationale")
    for root_type in (ObservedPrice, ProfileQualification, OrdinaryAnnualDividend, VerifiedNonpayer):
        require(sum(type(r) is root_type for r in facts.roots) <= 1, "Ambiguous or conflicting " + root_type.__name__)
    if real_contract:
        require(not any(type(r) is OrdinaryAnnualDividend for r in facts.roots),
                "PR5E real facts do not support the payer route")
    require(not (any(type(r) is OrdinaryAnnualDividend for r in facts.roots)
                 and any(type(r) is VerifiedNonpayer for r in facts.roots)), "Contradictory payer/nonpayer facts")
    canonical = []
    for root in facts.roots:
        provenance = root.identity.provenance
        fields_to_replace = {
            "available_at": _timestamp(provenance.available_at).isoformat(),
            "captured_at": _timestamp(provenance.captured_at).isoformat(),
        }
        if type(provenance) is Provenance:
            fields_to_replace["published_at"] = _timestamp(provenance.published_at).isoformat()
        provenance = replace(provenance, **fields_to_replace)
        root = replace(root, identity=replace(root.identity, provenance=provenance))
        if type(root) is ProfileQualification:
            root = replace(root, excluded_structures=tuple(sorted(root.excluded_structures, key=lambda p: p.value)))
        elif type(root) in (ObservedPrice, ReportedDilutedEPS, OrdinaryAnnualDividend):
            root = replace(root, value=float(root.value))
        canonical.append(root)
    return tuple(sorted(canonical, key=lambda root: root.identity.observation_id))


def _floor(*levels: str) -> str:
    return min(levels, key=er.CONFIDENCE_ORDER.index)


def construct_expected_return(facts: QualifiedFacts, *, mature_policy: MatureGrowthPolicy | None = None,
                              terminal_policy: TerminalValuationPolicy | None = None,
                              distribution_policy: DistributionPolicy | None = None) -> ConstructionResult:
    """Build PR4A request/diagnostic, or explicit unavailability; malformed input raises.

    No caller-derived DAG is accepted. Revisions require upstream resolution in a
    future contract; all duplicate annual periods currently raise contract errors.
    """
    roots = _validate(facts)
    as_of = _timestamp(facts.as_of)
    policies = (("mature_growth", mature_policy, MatureGrowthPolicy),
                ("terminal_valuation", terminal_policy, TerminalValuationPolicy),
                ("distributions", distribution_policy, DistributionPolicy))
    for name, policy, expected_type in policies:
        if policy is not None:
            require(type(policy) is expected_type, name + ": wrong policy type")
            validate_policy(policy)
    present = tuple(p for _, p, _ in policies if p is not None)
    require(len({p.policy_id for p in present}) == len(present), "Duplicate policy IDs")
    require(len({p.assumption_id for p in present}) == len(present), "Duplicate policy assumption IDs")
    hashes = tuple(sorted((name, p.policy_hash) for name, p, _ in policies if p is not None))
    root_by_id = {r.identity.observation_id: r for r in roots}
    nodes: dict[str, LineageNode] = {}
    # Every supplied observation is retained, including older unused history.
    root_hashes = tuple((r.identity.observation_id, canonical_hash((type(r).__name__, r))) for r in roots)
    component_roots: dict[str, tuple[str, ...]] = {}
    assessments: list[ConfidenceAssessment] = []

    def finish(reasons=(), request=None, diagnostic=None):
        components = tuple(sorted(component_roots.items()))
        shared = tuple(sorted(key for key in root_by_id if sum(key in ids for _, ids in components) > 1))
        lineage = tuple(sorted(nodes.values(), key=lambda node: node.id))
        digest = canonical_hash((EXPECTED_RETURN_CONSTRUCTOR_VERSION, facts.contract_version, as_of.isoformat(),
                                 facts.security_id, facts.share_class, facts.basis, facts.accounting_basis,
                                 facts.latest_required_fiscal_end, root_hashes, hashes, lineage, components,
                                 tuple(assessments), tuple(sorted(reasons))))
        return ConstructionResult("UNAVAILABLE" if reasons else "BUILT", tuple(sorted(reasons)),
            EXPECTED_RETURN_CONSTRUCTOR_VERSION, facts.contract_version, hashes, roots, digest, lineage,
            components, shared, tuple(assessments), request, diagnostic)

    def node(transform, parents, value, policy_hashes=()):
        parents = tuple(sorted(set(parents)))
        transitive = set()
        available, captured = [], []
        for parent in parents:
            if parent in root_by_id:
                transitive.add(parent)
                p = root_by_id[parent].identity.provenance
            else:
                require(parent in nodes, "Internal dangling transformation parent")
                p = nodes[parent]
                transitive.update(p.root_ids)
            available.append(_timestamp(p.available_at))
            captured.append(_timestamp(p.captured_at))
        require(bool(parents), "Transformation requires qualified roots")
        # Content identity binds transitive root metadata, not merely labels.
        root_ids = tuple(sorted(transitive))
        semantic = (EXPECTED_RETURN_CONSTRUCTOR_VERSION, transform, parents, value,
                    tuple(sorted(policy_hashes)), tuple((key, dict(root_hashes)[key]) for key in root_ids))
        identifier = "derived:" + canonical_hash(semantic)
        require(identifier not in root_by_id, "Root collides with derived ID")
        result = LineageNode(identifier, transform, parents, root_ids, tuple(sorted(policy_hashes)), value,
                             max(available).isoformat(), max(captured).isoformat())
        nodes[identifier] = result
        return result

    profiles = [r for r in roots if type(r) is ProfileQualification]
    if not profiles or profiles[0].profile is not Profile.ORDINARY_COMPOUNDER:
        return finish(("UNSUPPORTED_OR_MISSING_PROFILE",))
    profile = profiles[0]
    if set(profile.excluded_structures) != set(UNSUPPORTED_STRUCTURES):
        return finish(("AMBIGUOUS_PROFILE",))
    prices = [r for r in roots if type(r) is ObservedPrice]
    if not prices:
        return finish(("MISSING_CURRENT_PRICE",))
    price = prices[0]
    eps = sorted((r for r in roots if type(r) is ReportedDilutedEPS), key=lambda r: r.period.end)
    history = eps[-5:]
    if len(history) != 5 or history[-1].period.end != facts.latest_required_fiscal_end:
        return finish(("MISSING_EPS_SEQUENCE",))
    for previous, current in zip(history, history[1:]):
        if iso_date(current.period.start) != iso_date(previous.period.end) + timedelta(days=1):
            return finish(("MISSING_CONSECUTIVE_EPS_PERIOD",))
    if any(r.value <= 0 for r in history):
        return finish(("NONPOSITIVE_REQUIRED_EPS",))
    missing = []
    for name, policy, _ in policies:
        if policy is None or not applicable(policy, currency=facts.basis.currency,
                                           accounting_basis=facts.accounting_basis, as_of=as_of.date()):
            missing.append({"mature_growth": "MISSING_MATURE_GROWTH_POLICY",
                            "terminal_valuation": "MISSING_TERMINAL_VALUATION_POLICY",
                            "distributions": "MISSING_DISTRIBUTION_POLICY"}[name])
    dividends = [r for r in roots if type(r) is OrdinaryAnnualDividend]
    nonpayers = [r for r in roots if type(r) is VerifiedNonpayer]
    if not dividends and not nonpayers:
        missing.append("MISSING_DIVIDEND_STATUS")
    if missing:
        return finish(missing)
    status_root = (dividends or nonpayers)[0]
    # The first route supports the latest matched annual period only. No stale
    # nonpayer attestation or older convenient payout denominator is substituted.
    if status_root.period != history[-1].period:
        return finish(("DIVIDEND_EPS_PERIOD_MISMATCH",))
    expected_rule = (DistributionRule.CONSTANT_MATCHED_ORDINARY_PAYOUT if dividends
                     else DistributionRule.CONTINUED_VERIFIED_NONPAYER)
    if distribution_policy.rule is not expected_rule:
        return finish(("INAPPLICABLE_DISTRIBUTION_POLICY",))
    if dividends and dividends[0].value == 0:
        return finish(("MISSING_DIVIDEND_STATUS",))
    starting = float(median(r.value for r in history[-3:]))
    normalization = node("MEDIAN_LATEST_THREE_DILUTED_EPS_V1", [r.identity.observation_id for r in history[-3:]], starting)
    intervals = []
    for previous, current in zip(history, history[1:]):
        # log difference avoids intermediate E_i/E_(i-1) overflow; same formula.
        value = math.log(current.value) - math.log(previous.value)
        intervals.append(node("ANNUAL_DILUTED_EPS_LOG_RATIO_V1",
                              (previous.identity.observation_id, current.identity.observation_id), value))
    historical = (min(n.value for n in intervals), median(n.value for n in intervals), max(n.value for n in intervals))
    anchors = []
    for scenario, value in zip(er.SCENARIOS, historical):
        # All four intervals participate in each order statistic, including the
        # decision that an interval is not min/max. This retains exact support.
        anchors.append(node("HISTORICAL_LOG_" + scenario.upper() + "_V1", [n.id for n in intervals], float(value)))
    payout_parents = [status_root.identity.observation_id]
    payout = 0.0
    if dividends:
        payout = dividends[0].value / history[-1].value
        payout_parents.append(history[-1].identity.observation_id)
    if not math.isfinite(payout) or (dividends and payout <= 0):
        return finish(("UNREPRESENTABLE_PAYOUT",))
    # This initial route cannot establish sustained distributions above earnings.
    if dividends and payout > 1.0:
        return finish(("PAYOUT_EXCEEDS_EARNINGS",))
    payout_node = node(expected_rule.value + "_V1", payout_parents, payout, (distribution_policy.policy_hash,))
    growth_nodes, dividend_nodes, terminal_nodes = [], [], []
    try:
        for scenario, anchor in zip(er.SCENARIOS, anchors):
            mature = getattr(mature_policy.log_growth, scenario)
            logs = tuple(w * anchor.value + (1 - w) * mature for w in HISTORICAL_FADE_WEIGHTS)
            rates = tuple(math.expm1(g) for g in logs)
            if any(not math.isfinite(g) or g <= -1 for g in rates):
                return finish(("UNREPRESENTABLE_GROWTH_PATH",))
            faded = node(FADE_TRANSFORMATION_ID + ":" + scenario, (anchor.id, profile.identity.observation_id), logs,
                         (mature_policy.policy_hash,))
            growth_node = node("LOG_TO_DECIMAL_GROWTH_V1:" + scenario, (faded.id,), rates)
            growth_nodes.append(growth_node)
            # EPS projection is needed to construct dividend cash flows; the
            # terminal value and IRR remain exclusively PR4A's responsibility.
            projected = starting
            distributions = []
            for rate in rates:
                projected *= 1 + rate
                if not math.isfinite(projected) or projected <= 0:
                    return finish(("UNREPRESENTABLE_EPS_PATH",))
                distributions.append(payout * projected)
            if any(not math.isfinite(d) or (dividends and d <= 0) for d in distributions):
                return finish(("UNREPRESENTABLE_DIVIDEND_PATH",))
            dividend_parents = ((payout_node.id, normalization.id, growth_node.id, profile.identity.observation_id)
                                if dividends else (payout_node.id, profile.identity.observation_id))
            dividend_nodes.append(node("DIVIDEND_SCHEDULE_V1:" + scenario, dividend_parents, tuple(distributions),
                                       (distribution_policy.policy_hash,)))
            terminal_nodes.append(node("INDEPENDENT_TERMINAL_PE_V1:" + scenario, (profile.identity.observation_id,),
                                       float(getattr(terminal_policy.terminal_pe, scenario)), (terminal_policy.policy_hash,)))
    except OverflowError:
        return finish(("UNREPRESENTABLE_GROWTH_PATH",))
    for year in range(er.HORIZON_YEARS):
        if not growth_nodes[0].value[year] <= growth_nodes[1].value[year] <= growth_nodes[2].value[year]:
            return finish(("CROSSING_GROWTH_PATHS",))
    component_roots.update({
        "fundamental": tuple(sorted(set(normalization.root_ids) | {price.identity.observation_id})),
        "growth": tuple(sorted({key for n in growth_nodes for key in n.root_ids})),
        "distributions": tuple(sorted({key for n in dividend_nodes for key in n.root_ids})),
        "terminal_valuation": tuple(sorted({key for n in terminal_nodes for key in n.root_ids})),
    })

    def freshness(root):
        provenance = root.identity.provenance
        if type(provenance) is RealProvenance:
            # Capture proves an upper availability bound, not publication or
            # current freshness. Keep it usable but conservatively LOW.
            return "LOW"
        # Historical years are evaluated against the explicit latest-series
        # endpoint, not penalized merely for being required old observations.
        if type(root) is ObservedPrice:
            age, limits = (as_of.date() - iso_date(root.observed_on)).days, (7, 30)
        elif type(root) is ProfileQualification:
            age, limits = (as_of - _timestamp(root.identity.provenance.published_at)).days, (365, 730)
        else:
            age, limits = (as_of.date() - iso_date(facts.latest_required_fiscal_end)).days, (550, 730)
        return "HIGH" if age <= limits[0] else "MEDIUM" if age <= limits[1] else "LOW"

    for component in er.COMPONENTS:
        ids = component_roots[component]
        authority = _floor(*(
            "HIGH" if root_by_id[key].identity.provenance.source_kind is SourceKind.SYNTHETIC_OFFICIAL
            else "LOW" for key in ids))
        fresh = _floor(*(freshness(root_by_id[key]) for key in ids))
        ceiling = "HIGH" if component == "fundamental" else "LOW"
        category = _floor(authority, fresh, "HIGH", "HIGH", ceiling)
        assessments.append(ConfidenceAssessment(component, ids, authority, fresh, "HIGH", "HIGH", ceiling, category))
        confidence_parents = {
            "fundamental": (normalization.id, price.identity.observation_id),
            "growth": tuple(n.id for n in growth_nodes),
            "distributions": tuple(n.id for n in dividend_nodes),
            "terminal_valuation": tuple(n.id for n in terminal_nodes),
        }[component]
        node("CONFIDENCE_MIN_V1:" + component, confidence_parents, category)
    confidence = er.ConfidenceComponents(**{row.component: row.category for row in assessments})
    evidence = []
    for root in roots:
        identity, p = root.identity, root.identity.provenance
        period = getattr(root, "period", None)
        if type(root) is ObservedPrice:
            field, value, unit = "current_price", float(root.value), "CURRENCY_PER_SHARE"
        elif type(root) is ReportedDilutedEPS:
            field, value, unit = "reported_diluted_eps", float(root.value), "CURRENCY_PER_SHARE"
        elif type(root) is OrdinaryAnnualDividend:
            field, value, unit = "ordinary_annual_dividend", float(root.value), "CURRENCY_PER_SHARE"
        elif type(root) is VerifiedNonpayer:
            field, value, unit = "verified_nonpayer", "VERIFIED", "QUALIFICATION"
        else:
            field, value, unit = "qualified_company_profile", root.profile.value, "QUALIFICATION"
        basis = getattr(root, "basis", None)
        evidence_type = er.RealEvidence if type(p) is RealProvenance else er.Evidence
        evidence_args = (identity.observation_id, field, value, unit,
            ("MARKET_PROVIDER" if p.source_kind is SourceKind.YAHOO_MARKET_PROVIDER
             else "OFFICIAL_CURRENT_DATA" if p.source_kind in (SourceKind.SYNTHETIC_OFFICIAL,
                                                                 SourceKind.SEC_CURRENT)
             else "HUMAN_MANUAL"),
            p.source_reference, p.source_version,
            None if type(p) is RealProvenance else _timestamp(p.published_at).isoformat(),
            _timestamp(p.available_at).isoformat(), _timestamp(p.captured_at).isoformat(),
            ("CAPTURE_BOUND" if type(p) is RealProvenance
             else "STALE" if freshness(root) == "LOW" else "CURRENT"),
            ("HIGH" if p.source_kind is SourceKind.SYNTHETIC_OFFICIAL else "LOW"),
            basis.currency if basis else None, basis.share_basis if basis else None,
            period.start if period else root.observed_on if type(root) is ObservedPrice else None,
            period.end if period else root.observed_on if type(root) is ObservedPrice else None,
            getattr(root, "accounting_basis", None), ())
        if type(p) is RealProvenance:
            evidence_args += (p.publication_semantics.value, p.availability_semantics.value)
        evidence.append(evidence_type(*evidence_args))
    scenarios, assumptions = [], []
    for index, scenario in enumerate(er.SCENARIOS):
        outputs = (normalization, growth_nodes[index], dividend_nodes[index], terminal_nodes[index])
        refs = []
        for component, output in zip(er.COMPONENTS, outputs):
            policy = {"fundamental": None, "growth": mature_policy, "distributions": distribution_policy,
                      "terminal_valuation": terminal_policy}[component]
            identifier = "assumption:" + canonical_hash((scenario, component, output.id))
            require(identifier not in root_by_id, "Root collides with assumption ID")
            assumptions.append(er.Assumption(identifier, component, scenario,
                "Latest-three annual median normalization" if policy is None else policy.rationale,
                EXPECTED_RETURN_CONSTRUCTOR_VERSION if policy is None else policy.schema_version,
                output.root_ids, output.value, output.transformation_id + "; lineage=" + output.id))
            refs.append(er.References(assumption_ids=(identifier,)))
        scenarios.append(er.Scenario(scenario, starting, growth_nodes[index].value, dividend_nodes[index].value,
            terminal_nodes[index].value, facts.basis.currency, facts.basis.share_basis, *refs))
    schema_version = (er.EXPECTED_RETURN_REAL_SCHEMA_VERSION
                      if facts.contract_version == EXPECTED_RETURN_REAL_FACTS_CONTRACT_VERSION
                      else er.EXPECTED_RETURN_SCHEMA_VERSION)
    request = er.ExpectedReturnRequest(schema_version, er.EXPECTED_RETURN_METHODOLOGY_VERSION,
        as_of.isoformat(), er.SUPPORTED_PROFILE, er.SUPPORTED_METRIC, facts.basis.currency, facts.basis.share_basis,
        er.HORIZON_YEARS, float(price.value), price.identity.observation_id, tuple(scenarios), confidence,
        tuple(evidence), tuple(sorted(assumptions, key=lambda a: a.id)))
    # Only the calculator's explicit numerical-domain failure is translated.
    # Programming/contract bugs propagate instead of being disguised as missing data.
    try:
        diagnostic = er.calculate_expected_return(request)
    except er.ExpectedReturnNumericalError:
        return finish(("UNREPRESENTABLE_PR4A_CALCULATION",))
    return finish(request=request, diagnostic=diagnostic)
