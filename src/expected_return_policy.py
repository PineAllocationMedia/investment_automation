"""Immutable explicit policy contracts. No production economic policy values."""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import date
from enum import Enum
import hashlib
import json
import math

EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION = "2026-09-09-assumption-policy-v1"
EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION = "2026-09-09-terminal-policy-v1"
FADE_TRANSFORMATION_ID = "LOG_GROWTH_FADE_7Y_V1"
# Methodology weights specified by PR4B1; these are not economic forecasts.
HISTORICAL_FADE_WEIGHTS = (1.0, 1.0, .75, .50, .25, 0.0, 0.0)


class ConstructorContractError(ValueError):
    """Malformed, contradictory or unsupported input contract (never unavailable)."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ConstructorContractError(message)


def text(value, label: str) -> None:
    require(type(value) is str and bool(value.strip()) and value == value.strip(), label + ": trimmed nonempty text required")


def number(value, label: str) -> None:
    require(type(value) in (float, int), label + ": finite number required")
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    require(valid, label + ": finite binary64 number required")


def iso_date(value: str) -> date:
    text(value, "date")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ConstructorContractError("Invalid ISO date") from exc
    require(result.isoformat() == value, "Canonical ISO date required")
    return result


def canonical_hash(value) -> str:
    """Internal JSON projection: maps sorted, integers/floats normalized equally."""
    def canonical(item):
        if is_dataclass(item):
            return canonical(asdict(item))
        if isinstance(item, Enum):
            return item.value
        if type(item) is dict:
            return {key: canonical(child) for key, child in sorted(item.items())}
        if type(item) in (tuple, list):
            return [canonical(child) for child in item]
        if type(item) in (float, int):
            number(item, "hash value")
            return 0.0 if item == 0 else float(item)
        return item
    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True, allow_nan=False).encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True)
class Applicability:
    profile: str
    currency: str
    accounting_basis: str
    valid_from: str
    valid_through: str


@dataclass(frozen=True, slots=True)
class ScenarioValues:
    bear: float
    base: float
    bull: float


class DistributionRule(Enum):
    CONSTANT_MATCHED_ORDINARY_PAYOUT = "CONSTANT_MATCHED_ORDINARY_PAYOUT"
    CONTINUED_VERIFIED_NONPAYER = "CONTINUED_VERIFIED_NONPAYER"


@dataclass(frozen=True, slots=True)
class MatureGrowthPolicy:
    policy_id: str
    schema_version: str
    applicability: Applicability
    log_growth: ScenarioValues
    rationale: str
    assumption_id: str

    @property
    def policy_hash(self) -> str:
        validate_policy(self)
        return canonical_hash((type(self).__name__, self, FADE_TRANSFORMATION_ID, HISTORICAL_FADE_WEIGHTS))


@dataclass(frozen=True, slots=True)
class TerminalValuationPolicy:
    policy_id: str
    schema_version: str
    applicability: Applicability
    terminal_pe: ScenarioValues
    rationale: str
    assumption_id: str

    @property
    def policy_hash(self) -> str:
        validate_policy(self)
        return canonical_hash((type(self).__name__, self))


@dataclass(frozen=True, slots=True)
class DistributionPolicy:
    policy_id: str
    schema_version: str
    applicability: Applicability
    rule: DistributionRule
    rationale: str
    assumption_id: str

    @property
    def policy_hash(self) -> str:
        validate_policy(self)
        return canonical_hash((type(self).__name__, self))


def validate_policy(policy) -> None:
    require(type(policy) in (MatureGrowthPolicy, TerminalValuationPolicy, DistributionPolicy), "Unsupported policy type")
    expected = (EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION if type(policy) is TerminalValuationPolicy
                else EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION)
    require(policy.schema_version == expected, "Unsupported policy schema")
    for field in ("policy_id", "rationale", "assumption_id"):
        text(getattr(policy, field), field)
    app = policy.applicability
    require(type(app) is Applicability, "Typed Applicability required")
    require(app.profile == "ORDINARY_COMPOUNDER", "Unsupported policy profile")
    require(type(app.currency) is str and len(app.currency) == 3 and app.currency.isascii()
            and app.currency.isalpha() and app.currency.isupper(), "Invalid policy currency")
    require(app.accounting_basis in ("IFRS", "US_GAAP"), "Unsupported policy accounting basis")
    require(iso_date(app.valid_from) <= iso_date(app.valid_through), "Reversed policy validity")
    if type(policy) is DistributionPolicy:
        require(type(policy.rule) is DistributionRule, "Unsupported payout transformation")
    else:
        values = policy.log_growth if type(policy) is MatureGrowthPolicy else policy.terminal_pe
        require(type(values) is ScenarioValues, "Typed ScenarioValues required")
        for value in (values.bear, values.base, values.bull):
            number(value, "policy scenario")
            if type(policy) is TerminalValuationPolicy:
                require(value > 0, "Terminal P/E must be positive")
        require(values.bear <= values.base <= values.bull, "Policy scenarios cross; sorting is forbidden")


def applicable(policy, *, currency: str, accounting_basis: str, as_of: date) -> bool:
    validate_policy(policy)
    app = policy.applicability
    return (app.currency == currency and app.accounting_basis == accounting_basis
            and iso_date(app.valid_from) <= as_of <= iso_date(app.valid_through))
