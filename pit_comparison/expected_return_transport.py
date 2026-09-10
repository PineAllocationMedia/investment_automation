"""Closed synthetic JSON envelope, independent of model imports and economics.

Descriptors describe wire shapes only. The frozen V2 constructor owns semantic
qualification, policy applicability, and every economic calculation.
"""
from datetime import date
import math

from . import PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION
from .bundle import BundleError, HEX, _require, canonical, timestamp

FACTS_VERSION = "2026-09-09-synthetic-qualified-facts-v1"
ASSUMPTION_POLICY_VERSION = "2026-09-09-assumption-policy-v1"
TERMINAL_POLICY_VERSION = "2026-09-09-terminal-policy-v1"
PROFILES = frozenset("ORDINARY_COMPOUNDER BANK INSURER REIT ASSET_MANAGER RESOURCES_MINING ENERGY_CYCLICAL PIPELINE UTILITY_ACCOUNTING INVESTMENT_HOLDING MIXED_CONGLOMERATE TURNAROUND LOSS_MAKING UNKNOWN".split())
ROOT_ADAPTERS = {
    "ObservedPrice": "SYNTHETIC_OBSERVED_PRICE_V1",
    "ReportedDilutedEPS": "SYNTHETIC_REPORTED_DILUTED_EPS_V1",
    "OrdinaryAnnualDividend": "SYNTHETIC_ORDINARY_ANNUAL_DIVIDEND_V1",
    "VerifiedNonpayer": "SYNTHETIC_VERIFIED_NONPAYER_V1",
    "ProfileQualification": "SYNTHETIC_PROFILE_QUALIFICATION_V1",
}
SHAPES = {
    "Provenance": dict.fromkeys(("source_reference", "source_version", "source_locator"), "text") | {
        "source_kind": ("SYNTHETIC_OFFICIAL", "SYNTHETIC_MANUAL"), "source_document_hash": "hash",
        "published_at": "timestamp", "available_at": "timestamp", "captured_at": "timestamp",
        "extractor_id": tuple(ROOT_ADAPTERS.values()), "extractor_version": ("1",)},
    "Identity": {"observation_id": "text", "security_id": "text", "share_class": "text", "provenance": "Provenance"},
    "ShareBasis": {"currency": "text", "share_basis": "text"},
    "AnnualPeriod": {"start": "date", "end": "date"},
    "ObservedPrice": {"identity": "Identity", "value": "number", "basis": "ShareBasis", "observed_on": "date"},
    "ReportedDilutedEPS": {"identity": "Identity", "value": "number", "basis": "ShareBasis", "period": "AnnualPeriod", "accounting_basis": "text"},
    "OrdinaryAnnualDividend": {"identity": "Identity", "value": "number", "basis": "ShareBasis", "period": "AnnualPeriod", "special_dividends_excluded": "bool"},
    "VerifiedNonpayer": {"identity": "Identity", "period": "AnnualPeriod"},
    "ProfileQualification": {"identity": "Identity", "profile": tuple(sorted(PROFILES)), "excluded_structures": [tuple(sorted(PROFILES))], "rationale": "text"},
    "QualifiedFacts": {"contract_version": (FACTS_VERSION,), "as_of": "timestamp", "security_id": "text", "share_class": "text", "basis": "ShareBasis", "accounting_basis": "text", "latest_required_fiscal_end": "date", "roots": ["root"]},
    "Applicability": {"profile": "text", "currency": "text", "accounting_basis": "text", "valid_from": "date", "valid_through": "date"},
    "ScenarioValues": dict.fromkeys(("bear", "base", "bull"), "number"),
}
for name, field, spec in (
    ("MatureGrowthPolicy", "log_growth", "ScenarioValues"),
    ("TerminalValuationPolicy", "terminal_pe", "ScenarioValues"),
    ("DistributionPolicy", "rule", ("CONSTANT_MATCHED_ORDINARY_PAYOUT", "CONTINUED_VERIFIED_NONPAYER")),
):
    SHAPES[name] = {"policy_id": "text", "schema_version": (TERMINAL_POLICY_VERSION if name == "TerminalValuationPolicy" else ASSUMPTION_POLICY_VERSION,),
        "applicability": "Applicability", field: spec, "rationale": "text", "assumption_id": "text"}
POLICY_TYPES = {"mature_growth": "MatureGrowthPolicy", "terminal_valuation": "TerminalValuationPolicy", "distributions": "DistributionPolicy"}


def closed(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "Expected Return closed object keys mismatch")


def shape(value, spec):
    if type(spec) is tuple:
        _require(type(value) is str and value in spec, "Unknown Expected Return enum/version")
    elif type(spec) is list:
        _require(type(value) is list, "Expected Return array required")
        for item in value:
            shape(item, spec[0])
    elif spec == "root":
        _require(type(value) is dict and type(value.get("root_type")) is str and value["root_type"] in ROOT_ADAPTERS,
                 "Unsupported Expected Return root type")
        shape({k: v for k, v in value.items() if k != "root_type"}, value["root_type"])
        _require(value["identity"]["provenance"]["extractor_id"] == ROOT_ADAPTERS[value["root_type"]], "Root/adapter mismatch")
    elif spec in SHAPES:
        fields = SHAPES[spec]
        closed(value, fields)
        for key, child in fields.items():
            shape(value[key], child)
    elif spec == "number":
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
        _require(valid, "Expected Return finite binary64 number required")
    elif spec == "bool":
        _require(type(value) is bool, "Expected Return boolean required")
    else:
        _require(type(value) is str and bool(value.strip()) and value == value.strip(), "Expected Return trimmed text required")
        if spec == "hash":
            _require(HEX.fullmatch(value), "Expected Return SHA-256 required")
        elif spec == "timestamp":
            timestamp(value)
        elif spec == "date":
            try:
                _require(date.fromisoformat(value).isoformat() == value, "Canonical Expected Return date required")
            except ValueError as exc:
                raise BundleError("Invalid Expected Return date") from exc


def validate_inputs(value, effective_pit_at):
    canonical(value)
    closed(value, {"contract_version", "entries"})
    shape(value["contract_version"], (PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION,))
    _require(type(value["entries"]) is list, "Expected Return entries required")
    pit, tickers = timestamp(effective_pit_at), set()
    for entry in value["entries"]:
        closed(entry, {"ticker", "status", "facts", "policies", "unavailable_reasons"})
        shape(entry["ticker"], "text")
        _require(entry["ticker"] not in tickers, "Duplicate Expected Return ticker")
        tickers.add(entry["ticker"])
        shape(entry["status"], ("QUALIFIED_SYNTHETIC", "EXPLICITLY_UNAVAILABLE"))
        shape(entry["unavailable_reasons"], ["text"])
        _require(len(set(entry["unavailable_reasons"])) == len(entry["unavailable_reasons"]), "Duplicate absence reasons")
        if entry["status"] == "EXPLICITLY_UNAVAILABLE":
            _require(entry["facts"] is None and entry["policies"] is None and entry["unavailable_reasons"], "Explicit absence requires reasons and null facts/policies")
            continue
        _require(not entry["unavailable_reasons"], "Qualified entry cannot declare absence")
        facts = entry["facts"]
        shape(facts, "QualifiedFacts")
        # No archival exception: evaluate at exactly the bundle's semantic time.
        _require(timestamp(facts["as_of"]) == pit, "Expected Return as_of must equal effective PIT")
        _require(date.fromisoformat(facts["latest_required_fiscal_end"]) <= pit.date(), "Future Expected Return fiscal end")
        for root in facts["roots"]:
            p = root["identity"]["provenance"]
            published, available, captured = (timestamp(p[k]) for k in ("published_at", "available_at", "captured_at"))
            _require(published <= available <= captured <= pit, "Expected Return publication/availability/capture chronology")
            if "period" in root:
                _require(root["period"]["start"] <= root["period"]["end"] <= published.date().isoformat(), "Expected Return fiscal chronology")
            if "observed_on" in root:
                _require(root["observed_on"] <= published.date().isoformat(), "Expected Return observation chronology")
        closed(entry["policies"], POLICY_TYPES)
        for key, kind in POLICY_TYPES.items():
            # Explicit null is economic insufficiency; omitted keys are malformed.
            if entry["policies"][key] is not None:
                shape(entry["policies"][key], kind)
