"""Pure seven-year equity cash-flow calculations, with no investment authority.

Inputs are already-qualified economic assumptions, never V1 scores or proxies.
Per-share growth incorporates net share-count effects: NEVER add buyback yield
or subtract dilution again. Dividends enter once, as explicit cash flows.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date, datetime, timezone
import math
import re


EXPECTED_RETURN_METHODOLOGY_VERSION = "2026-09-08-normalized-eps-cashflow-irr-v1"
EXPECTED_RETURN_SCHEMA_VERSION = "2026-09-08-expected-return-diagnostic-v1"
HORIZON_YEARS = 7
SUPPORTED_PROFILE = "ORDINARY_COMPOUNDER"
SUPPORTED_METRIC = "NORMALIZED_DILUTED_EPS"
SCENARIOS = ("bear", "base", "bull")
COMPONENTS = ("fundamental", "growth", "distributions", "terminal_valuation")
CONFIDENCE_ORDER = ("NONE", "LOW", "MEDIUM", "HIGH")
SOURCE_KINDS = frozenset({"OFFICIAL_CURRENT_DATA", "MARKET_PROVIDER", "RESEARCH_REPORT", "HUMAN_MANUAL", "DERIVED"})
# Known repository field names, not a ban on raw operating facts or all CAGR
# measures (share_count_cagr_5y, for example, is legitimate operating evidence).
# Enforced only on material provenance, regardless of source kind or confidence.
PROHIBITED_EXPECTED_RETURN_EVIDENCE_FIELDS = frozenset({
    # data_fetcher.py: price-history returns and its actual adjusted aliases.
    "stock_cagr_3y", "stock_cagr_5y", "stock_cagr_10y", "cagr_5y", "cagr_10y",
    "adjusted_stock_cagr_3y", "adjusted_stock_cagr_5y", "adjusted_stock_cagr_10y",
    "adjusted_cagr_5y", "adjusted_cagr_10y", "stock_return_1y", "adjusted_stock_return_1y",
    # benchmark_metrics_for and the sector proxy used by V1 scoring/sizing.
    "sector_cagr_estimated", "benchmark_3y_cagr", "benchmark_5y_cagr",
    "benchmark_10y_cagr", "benchmark_usable_cagr", "benchmark_1y_return", "benchmark_return_1y",
    # V1 classifications, scores and their numeric sizing components.
    "expected_cagr_quality", "expected_cagr_quality_raw", "expected_cagr_quality_score",
    "score_total", "score_total_normalized", "conviction_score",
    "opportunity_cost_status", "opportunity_cost_score", "long_term_durability_score",
    "business_quality_score", "high_cagr_potential_score", "quality_cagr_intersection",
    # Existing heuristic valuation judgments, not underlying earnings observations.
    "peg", "peg_manual", "fair_value", "price_to_fair_value", "valuation_severity",
    "valuation_score", "quality_but_too_expensive",
    # sizing_engine/allocation_engine outputs and the allocation-weight projection.
    "capital_allocation_score", "capital_allocation_score_low", "capital_allocation_score_high",
    "capital_allocation_components", "capital_allocation_confidence_range",
    "capital_allocation_confidence_label", "allocations", "allocation_weight",
    "montant", "pourcentage", "post_purchase_position_weight",
    "reliability_allocation_cap_percent", "reliability_allocation_cap_amount",
})
_MAX_ITERATIONS = 256
_ROOT_TOLERANCE = 1e-14
_RESIDUAL_TOLERANCE = 1e-10


class ExpectedReturnError(ValueError):
    """Malformed contract or inconsistent economic assumptions."""


class ExpectedReturnNumericalError(ExpectedReturnError):
    """The valid-shaped request cannot be solved faithfully in binary64."""


@dataclass(frozen=True, slots=True)
class References:
    evidence_ids: tuple[str, ...] = ()
    assumption_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    field: str
    value: float | str | tuple[float, ...]
    unit: str
    source_kind: str
    source_reference: str
    source_version: str
    published_at: str
    available_at: str
    captured_at: str
    freshness_status: str
    reliability_status: str
    currency: str | None = None
    share_basis: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    accounting_basis: str | None = None
    parent_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Assumption:
    id: str
    component: str
    scenario: str
    rationale: str
    policy_version: str
    supporting_evidence_ids: tuple[str, ...] = ()
    value: float | tuple[float, ...] | None = None
    rule: str | None = None


@dataclass(frozen=True, slots=True)
class ConfidenceComponents:
    fundamental: str
    growth: str
    distributions: str
    terminal_valuation: str


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    starting_eps_per_share: float | None
    growth_rates: tuple[float, ...] | None
    dividends_per_share: tuple[float, ...] | None
    terminal_pe: float | None
    currency: str
    share_basis: str
    fundamental_refs: References
    growth_refs: References
    distribution_refs: References
    terminal_refs: References


@dataclass(frozen=True, slots=True)
class ExpectedReturnRequest:
    schema_version: str
    methodology_version: str
    as_of: str
    profile: str
    metric: str
    currency: str
    share_basis: str
    horizon_years: int
    current_price: float | None
    current_price_evidence_id: str | None
    scenarios: tuple[Scenario, ...]
    confidence: ConfidenceComponents
    evidence: tuple[Evidence, ...]
    assumptions: tuple[Assumption, ...]


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: str
    annualized_return: float | None
    starting_eps_per_share: float | None
    growth_rates: tuple[float, ...] | None
    dividends_per_share: tuple[float, ...] | None
    terminal_eps_per_share: float | None
    terminal_pe: float | None
    terminal_price: float | None
    fundamental_refs: References
    growth_refs: References
    distribution_refs: References
    terminal_refs: References


@dataclass(frozen=True, slots=True)
class ExpectedReturnDiagnostic:
    schema_version: str
    methodology_version: str
    status: str
    authority: str
    as_of: str
    horizon_years: int
    profile: str
    metric: str
    currency: str
    share_basis: str
    current_price: float | None
    current_price_evidence_id: str | None
    return_basis: str
    fx_basis: str
    confidence: ConfidenceComponents
    overall_confidence: str
    scenarios: tuple[ScenarioResult, ...]
    evidence: tuple[Evidence, ...]
    assumptions: tuple[Assumption, ...]
    warnings: tuple[str, ...]
    unavailable_reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        """Fresh JSON-compatible projection; never expose mutable internal state."""
        def lists(value):
            if isinstance(value, dict):
                return {key: lists(child) for key, child in value.items()}
            if isinstance(value, (tuple, list)):
                return [lists(child) for child in value]
            return value
        payload = lists(asdict(self))
        payload["scenarios"] = {row.pop("name"): row for row in payload["scenarios"]}
        return {"expected_return_diagnostic": payload}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ExpectedReturnError(message)


def _text(value, label: str) -> None:
    _require(type(value) is str and bool(value.strip()) and value == value.strip(), f"{label}: nonempty trimmed string required")


def _number(value, label: str) -> None:
    _require(type(value) in (int, float), f"{label}: finite number required (booleans are not numbers)")
    try:
        finite = math.isfinite(value)
    except OverflowError as exc:
        raise ExpectedReturnError(f"{label}: number exceeds binary64 range") from exc
    _require(finite, f"{label}: finite number required")


def _tuple(value, label: str, member_type=None) -> None:
    _require(type(value) is tuple, f"{label}: immutable tuple required")
    if member_type is not None:
        _require(all(type(item) is member_type for item in value), f"{label}: invalid record type")


def _ids(value, label: str) -> None:
    _tuple(value, label)
    for item in value:
        _text(item, label)
    _require(len(set(value)) == len(value), f"{label}: duplicate references")


def _currency(value, label: str) -> None:
    _require(type(value) is str and re.fullmatch(r"[A-Z]{3}", value) is not None, f"{label}: three-letter uppercase currency required")


def _timestamp(value, label: str) -> datetime:
    _text(value, label)
    _require(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value) is not None,
             f"{label}: explicit offset ISO timestamp required")
    if not value.endswith("Z"):
        _require(int(value[-5:-3]) < 24 and int(value[-2:]) < 60, f"{label}: invalid UTC offset")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ExpectedReturnError(f"{label}: invalid timestamp") from exc


def _date(value, label: str) -> date:
    _require(type(value) is str and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None, f"{label}: ISO date required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ExpectedReturnError(f"{label}: invalid date") from exc


def _value(value, label: str, *, text_allowed=False) -> None:
    if text_allowed and type(value) is str:
        _text(value, label)
    elif type(value) is tuple:
        _require(bool(value), f"{label}: empty value vector")
        for item in value:
            _number(item, label)
    else:
        _number(value, label)


def _validate_request(request: ExpectedReturnRequest):
    _require(type(request) is ExpectedReturnRequest, "ExpectedReturnRequest required; mappings and extra keys are not accepted")
    _require(request.schema_version == EXPECTED_RETURN_SCHEMA_VERSION, "Unsupported schema version")
    _require(request.methodology_version == EXPECTED_RETURN_METHODOLOGY_VERSION, "Unsupported methodology version")
    as_of = _timestamp(request.as_of, "as_of")
    for label in ("profile", "metric"):
        value = getattr(request, label)
        _require(type(value) is str and re.fullmatch(r"[A-Z][A-Z0-9_]*", value) is not None, f"{label}: malformed identifier")
    _currency(request.currency, "currency")
    _text(request.share_basis, "share_basis")
    _require(type(request.horizon_years) is int and request.horizon_years == HORIZON_YEARS, "horizon_years must be exactly seven")
    if request.current_price is not None:
        _number(request.current_price, "current_price")
        _require(request.current_price > 0, "current_price must be positive")
    if request.current_price_evidence_id is not None:
        _text(request.current_price_evidence_id, "current_price_evidence_id")
    _require(type(request.confidence) is ConfidenceComponents, "ConfidenceComponents required")
    for component in COMPONENTS:
        _require(type(getattr(request.confidence, component)) is str and getattr(request.confidence, component) in CONFIDENCE_ORDER, f"{component}: invalid confidence")
    _tuple(request.evidence, "evidence", Evidence)
    _tuple(request.assumptions, "assumptions", Assumption)
    _tuple(request.scenarios, "scenarios", Scenario)
    for scenario in request.scenarios:
        _require(type(scenario.name) is str and scenario.name in SCENARIOS, "Invalid scenario name")
    _require(len(request.scenarios) == 3 and {s.name for s in request.scenarios} == set(SCENARIOS), "Exactly bear, base and bull required")
    all_ids = []
    for record in (*request.evidence, *request.assumptions):
        _text(record.id, "record id")
        all_ids.append(record.id)
    _require(len(all_ids) == len(set(all_ids)), "Duplicate evidence/assumption IDs")
    evidence = {record.id: record for record in request.evidence}
    assumptions = {record.id: record for record in request.assumptions}
    for record in request.evidence:
        for field in ("field", "unit", "source_reference", "source_version"):
            _text(getattr(record, field), f"evidence {record.id}.{field}")
        _value(record.value, record.id, text_allowed=True)
        _require(type(record.source_kind) is str and record.source_kind in SOURCE_KINDS, f"{record.id}: invalid evidence source kind")
        _require(type(record.freshness_status) is str and record.freshness_status in ("CURRENT", "STALE", "UNKNOWN"), f"{record.id}: invalid freshness")
        _require(type(record.reliability_status) is str and record.reliability_status in CONFIDENCE_ORDER, f"{record.id}: invalid reliability")
        published = _timestamp(record.published_at, record.id + ".published_at")
        available = _timestamp(record.available_at, record.id + ".available_at")
        captured = _timestamp(record.captured_at, record.id + ".captured_at")
        _require(published <= available <= as_of and available <= captured <= as_of, f"{record.id}: publication/availability/capture must be ordered and no later than as_of")
        if record.currency is not None:
            _currency(record.currency, record.id + ".currency")
        for field in ("share_basis", "accounting_basis"):
            if getattr(record, field) is not None:
                _text(getattr(record, field), record.id + "." + field)
        start = _date(record.period_start, record.id + ".period_start") if record.period_start is not None else None
        end = _date(record.period_end, record.id + ".period_end") if record.period_end is not None else None
        _require(not (start and end) or start <= end, f"{record.id}: reversed target/fiscal period")
        _ids(record.parent_evidence_ids, record.id + ".parents")
        _require(all(parent in evidence for parent in record.parent_evidence_ids), f"{record.id}: dangling parent evidence")
    # A derived fact cannot cite itself, or acquire information before its parents.
    visited, active = set(), set()
    def visit(identifier):
        _require(identifier not in active, "Cyclic evidence provenance")
        if identifier in visited:
            return
        active.add(identifier)
        child = evidence[identifier]
        for parent in child.parent_evidence_ids:
            _require(_timestamp(evidence[parent].available_at, parent) <= _timestamp(child.available_at, identifier), "Derived evidence predates its parent")
            visit(parent)
        active.remove(identifier)
        visited.add(identifier)
    for identifier in sorted(evidence):
        visit(identifier)
    for record in request.assumptions:
        _require(type(record.component) is str and record.component in COMPONENTS, f"{record.id}: invalid component")
        _require(type(record.scenario) is str and record.scenario in SCENARIOS, f"{record.id}: invalid scenario")
        _text(record.rationale, record.id + ".rationale")
        _text(record.policy_version, record.id + ".policy_version")
        _require(record.value is not None or record.rule is not None, f"{record.id}: assumption value or rule required")
        if record.value is not None:
            _value(record.value, record.id)
        if record.rule is not None:
            _text(record.rule, record.id + ".rule")
        _ids(record.supporting_evidence_ids, record.id + ".support")
        _require(all(key in evidence for key in record.supporting_evidence_ids), f"{record.id}: dangling supporting evidence")
    if request.current_price_evidence_id is not None:
        _require(request.current_price_evidence_id in evidence, "Dangling current price evidence")
        record = evidence[request.current_price_evidence_id]
        _require(record.field == "current_price" and record.unit == "CURRENCY_PER_SHARE", "Price evidence must be an observed share price")
        _require(record.currency == request.currency and record.share_basis == request.share_basis, "Price currency/share basis mismatch")
        _require(record.source_kind in {"MARKET_PROVIDER", "OFFICIAL_CURRENT_DATA", "HUMAN_MANUAL"}, "Observed price evidence required")
        _require(record.period_end is None or _date(record.period_end, "price period") <= as_of.date(), "Observed price cannot have a future target period")
        if request.current_price is not None:
            _require(type(record.value) in (int, float) and record.value == request.current_price, "Price contradicts linked evidence")
    for scenario in request.scenarios:
        _currency(scenario.currency, "scenario currency")
        _text(scenario.share_basis, "scenario share_basis")
        _require(scenario.currency == request.currency and scenario.share_basis == request.share_basis, "Scenario currency/share basis mismatch")
        for field in ("starting_eps_per_share", "terminal_pe"):
            value = getattr(scenario, field)
            if value is not None:
                _number(value, field)
                _require(value > 0, f"{field} must be positive")
        for field in ("growth_rates", "dividends_per_share"):
            values = getattr(scenario, field)
            if values is not None:
                _tuple(values, field)
                _require(len(values) == HORIZON_YEARS, f"{field}: exactly seven values required")
                for value in values:
                    _number(value, field)
                    _require(value > -1 if field == "growth_rates" else value >= 0, f"{field}: invalid economic value")
        for component, value, refs, field, unit in _components(scenario):
            _require(type(refs) is References, f"{component}: References required")
            _ids(refs.evidence_ids, component + ".evidence_ids")
            _ids(refs.assumption_ids, component + ".assumption_ids")
            _require(all(key in evidence for key in refs.evidence_ids), f"{component}: dangling evidence reference")
            _require(all(key in assumptions for key in refs.assumption_ids), f"{component}: dangling assumption reference")
            for key in refs.evidence_ids:
                record = evidence[key]
                _require(record.field == field and record.unit == unit, f"{key}: wrong field/unit for {component}")
                if component in {"fundamental", "distributions"}:
                    _require(record.currency == request.currency and record.share_basis == request.share_basis, f"{key}: currency/share basis mismatch")
                if component == "fundamental":
                    _require(record.accounting_basis == SUPPORTED_METRIC, f"{key}: explicitly normalized diluted EPS evidence required")
                if value is not None:
                    _require(record.value == value, f"{key}: scenario value contradicts direct evidence; use an explicit transformation assumption")
            for key in refs.assumption_ids:
                record = assumptions[key]
                _require(record.component == component and record.scenario == scenario.name, f"{key}: wrong assumption component/scenario")
                if value is not None and record.value is not None:
                    _require(record.value == value, f"{key}: scenario contradicts assumption value")
    return as_of, evidence, assumptions


def _components(scenario):
    return (
        ("fundamental", scenario.starting_eps_per_share, scenario.fundamental_refs, "normalized_diluted_eps", "CURRENCY_PER_SHARE"),
        ("growth", scenario.growth_rates, scenario.growth_refs, "per_share_eps_growth", "DECIMAL_FRACTION"),
        ("distributions", scenario.dividends_per_share, scenario.distribution_refs, "dividends_per_share", "CURRENCY_PER_SHARE"),
        ("terminal_valuation", scenario.terminal_pe, scenario.terminal_refs, "terminal_pe", "MULTIPLE"),
    )


def _canonical_refs(refs):
    return References(tuple(sorted(refs.evidence_ids)), tuple(sorted(refs.assumption_ids)))


def _solve_return(price: float, dividends: tuple[float, ...], terminal: float) -> float:
    # Solve in log gross-return space. Log-sum-exp avoids overflowing discounted
    # cash flows near -100%, and never needs a speculative financial upper bound.
    cash = [(year, math.log(value)) for year, value in enumerate(dividends, 1) if value > 0]
    cash.append((HORIZON_YEARS, math.log(terminal)))
    log_price = math.log(price)
    def residual(log_gross):
        terms = [log_cash - year * log_gross for year, log_cash in cash]
        peak = max(terms)
        return peak + math.log(math.fsum(math.exp(term - peak) for term in terms)) - log_price
    lower = math.log1p(math.nextafter(-1.0, 0.0))
    upper = math.log(float.fromhex("0x1.fffffffffffffp+1023"))
    if residual(lower) < 0 or residual(upper) > 0:
        raise ExpectedReturnNumericalError("Root is outside representable annual-return range")
    for _ in range(_MAX_ITERATIONS):
        midpoint = lower + (upper - lower) / 2
        error = residual(midpoint)
        if error > 0:
            lower = midpoint
        else:
            upper = midpoint
        if upper - lower <= _ROOT_TOLERANCE * max(1.0, abs(midpoint)):
            try:
                result = math.expm1(midpoint)
            except OverflowError as exc:
                raise ExpectedReturnNumericalError("Unrepresentable annualized return") from exc
            if not math.isfinite(result) or result <= -1 or abs(residual(math.log1p(result))) > _RESIDUAL_TOLERANCE:
                raise ExpectedReturnNumericalError("Returned root fails representability/NPV residual check")
            return result
    raise ExpectedReturnNumericalError("IRR bisection did not converge")


def calculate_expected_return(request: ExpectedReturnRequest) -> ExpectedReturnDiagnostic:
    """Validate the entire immutable contract, then calculate or report absence.

    Missing economics are UNAVAILABLE. Invalid values, provenance, structures,
    crossed returns and numerical failures raise; programmer errors are not hidden.
    """
    as_of, evidence, assumptions = _validate_request(request)
    reasons, warnings = set(), set()
    levels = {component: getattr(request.confidence, component) for component in COMPONENTS}
    if request.profile != SUPPORTED_PROFILE:
        reasons.add("UNSUPPORTED_PROFILE:" + request.profile)
    if request.metric != SUPPORTED_METRIC:
        reasons.add("UNSUPPORTED_METRIC:" + request.metric)
    if request.current_price is None:
        reasons.add("MISSING_CURRENT_PRICE")
    if request.current_price_evidence_id is None:
        reasons.add("MISSING_CURRENT_PRICE_EVIDENCE")

    def inspect_evidence(keys, component):
        pending, seen = sorted(keys, reverse=True), set()
        while pending:
            key = pending.pop()
            if key in seen:
                continue
            seen.add(key)
            record = evidence[key]
            _require(record.field.casefold() not in PROHIBITED_EXPECTED_RETURN_EVIDENCE_FIELDS,
                     f"{key}: prohibited material Expected Return evidence field {record.field!r} for {component}")
            pending.extend(sorted(record.parent_evidence_ids, reverse=True))
            if record.reliability_status == "NONE" or record.freshness_status == "UNKNOWN":
                reasons.add("UNUSABLE_EVIDENCE:" + key)
                levels[component] = "NONE"
            else:
                levels[component] = min((levels[component], record.reliability_status), key=CONFIDENCE_ORDER.index)
                if record.freshness_status == "STALE":
                    warnings.add("STALE_EVIDENCE:" + key)
                    levels[component] = min((levels[component], "LOW"), key=CONFIDENCE_ORDER.index)
        return seen

    if request.current_price_evidence_id is not None:
        inspect_evidence((request.current_price_evidence_id,), "fundamental")
    ordered = sorted(request.scenarios, key=lambda scenario: SCENARIOS.index(scenario.name))
    for scenario in ordered:
        for component, value, refs, _, _ in _components(scenario):
            if value is None:
                reasons.add(f"MISSING_INPUT:{scenario.name}:{component}")
            if not refs.evidence_ids and not refs.assumption_ids:
                reasons.add(f"MISSING_PROVENANCE:{scenario.name}:{component}")
            if component in {"growth", "terminal_valuation"} and not refs.assumption_ids:
                reasons.add(f"MISSING_ASSUMPTION:{scenario.name}:{component}")
            support = set(refs.evidence_ids)
            for key in refs.assumption_ids:
                support.update(assumptions[key].supporting_evidence_ids)
            inspect_evidence(support, component)
            if component == "fundamental" and not support:
                reasons.add(f"MISSING_FUNDAMENTAL_EVIDENCE:{scenario.name}")
    for component, level in levels.items():
        if level == "NONE":
            reasons.add("ESSENTIAL_CONFIDENCE_NONE:" + component)
    overall = min(levels.values(), key=CONFIDENCE_ORDER.index)
    if reasons:
        overall = "NONE"
    outputs = []
    for scenario in ordered:
        terminal_eps = terminal_price = annualized_return = None
        if not reasons:
            terminal_eps = float(scenario.starting_eps_per_share)
            for growth in scenario.growth_rates:
                terminal_eps *= 1 + float(growth)
                if not math.isfinite(terminal_eps) or terminal_eps <= 0:
                    raise ExpectedReturnNumericalError("EPS path overflows or underflows binary64")
            terminal_price = terminal_eps * float(scenario.terminal_pe)
            if not math.isfinite(terminal_price) or terminal_price <= 0:
                raise ExpectedReturnNumericalError("Terminal price overflows or underflows binary64")
            annualized_return = _solve_return(request.current_price, scenario.dividends_per_share, terminal_price)
        outputs.append(ScenarioResult(scenario.name, annualized_return, scenario.starting_eps_per_share,
            scenario.growth_rates, scenario.dividends_per_share, terminal_eps, scenario.terminal_pe,
            terminal_price, *(_canonical_refs(refs) for refs in (scenario.fundamental_refs,
                scenario.growth_refs, scenario.distribution_refs, scenario.terminal_refs))))
    if not reasons:
        _require(outputs[0].annualized_return <= outputs[1].annualized_return <= outputs[2].annualized_return,
                 "Scenario returns cross: require bear <= base <= bull; labels are never sorted/swapped")
    canonical_evidence = tuple(replace(record,
        published_at=_timestamp(record.published_at, record.id).isoformat(),
        available_at=_timestamp(record.available_at, record.id).isoformat(),
        captured_at=_timestamp(record.captured_at, record.id).isoformat(),
        parent_evidence_ids=tuple(sorted(record.parent_evidence_ids))) for record in sorted(request.evidence, key=lambda row: row.id))
    canonical_assumptions = tuple(replace(record, supporting_evidence_ids=tuple(sorted(record.supporting_evidence_ids)))
                                  for record in sorted(request.assumptions, key=lambda row: row.id))
    return ExpectedReturnDiagnostic(
        EXPECTED_RETURN_SCHEMA_VERSION, EXPECTED_RETURN_METHODOLOGY_VERSION,
        "UNAVAILABLE" if reasons else "AVAILABLE" if overall == "HIGH" else "DEGRADED",
        "DIAGNOSTIC_ONLY", as_of.isoformat(), HORIZON_YEARS, request.profile, request.metric,
        request.currency, request.share_basis, request.current_price, request.current_price_evidence_id,
        "NOMINAL_PRETAX_EQUITY_CASHFLOW_IRR", "CONSTANT_FX", ConfidenceComponents(**levels),
        overall, tuple(outputs), canonical_evidence, canonical_assumptions,
        tuple(sorted(warnings)), tuple(sorted(reasons)))
