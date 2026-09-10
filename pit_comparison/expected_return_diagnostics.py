"""Post-decision diagnostic sidecar. Only frozen V2 imports PR4B1/PR4A.

No decision-model object, bundle, provider, path, or acquisition API is accepted.
Transport tickers are locators; QualifiedFacts retains the economic identity.
"""
from dataclasses import asdict, is_dataclass
from enum import Enum

from . import (AUTHORITY, PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION,
    PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION, PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION)
from .bundle import _require, canonical, fingerprint
from .expected_return_transport import (FACTS_VERSION, ASSUMPTION_POLICY_VERSION, TERMINAL_POLICY_VERSION,
    POLICY_TYPES, SHAPES, closed, shape, validate_inputs)

VERSION_KEYS = {"constructor", "facts", "methodology", "calculator_schema", "assumption_policy", "terminal_policy"}
V2_VERSIONS = {"constructor": "2026-09-09-qualified-history-constructor-v1", "facts": FACTS_VERSION,
    "methodology": "2026-09-08-normalized-eps-cashflow-irr-v1", "calculator_schema": "2026-09-08-expected-return-diagnostic-v1",
    "assumption_policy": ASSUMPTION_POLICY_VERSION, "terminal_policy": TERMINAL_POLICY_VERSION}
ENTRY_KEYS = {"ticker", "input_status", "status", "security_id", "share_class", "unavailable_reasons", "policy_hashes",
    "lineage_hash", "confidence", "overall_confidence", "scenarios"}
SCENARIO_FIELDS = {"annualized_return", "starting_eps_per_share", "growth_rates", "dividends_per_share",
    "terminal_eps_per_share", "terminal_pe", "terminal_price"}
CONFIDENCE_FIELDS = {"component", "root_ids", "source_authority", "freshness", "completeness", "consistency", "assumption_dependence", "category"}
COMPONENTS = ("fundamental", "growth", "distributions", "terminal_valuation")


def json_value(value):
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: json_value(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_value(v) for v in value]
    return value


def decode(value, kind, assumptions, policies):
    """Closed descriptors select exact frozen dataclasses; never arbitrary names."""
    if value is None:
        return None
    if kind == "root":
        kind = value["root_type"]
        value = {k: v for k, v in value.items() if k != "root_type"}
    fields = SHAPES[kind]
    closed(value, fields)
    decoded = {}
    enums = {("Provenance", "source_kind"): assumptions.SourceKind,
        ("Provenance", "extractor_id"): assumptions.AdapterIdentity,
        ("ProfileQualification", "profile"): assumptions.Profile,
        ("DistributionPolicy", "rule"): policies.DistributionRule}
    for key, spec in fields.items():
        child = value[key]
        if (kind, key) in enums:
            child = enums[kind, key](child)
        elif key == "excluded_structures":
            child = tuple(assumptions.Profile(p) for p in child)
        elif key == "roots":
            child = tuple(decode(r, "root", assumptions, policies) for r in child)
        elif isinstance(spec, str) and spec in SHAPES:
            child = decode(child, spec, assumptions, policies)
        decoded[key] = child
    module = policies if kind in {*POLICY_TYPES.values(), "Applicability", "ScenarioValues"} else assumptions
    return getattr(module, kind)(**decoded)


def evaluate_diagnostics(inputs, lineage, effective_pit_at):
    validate_inputs(inputs, effective_pit_at)
    _require(lineage in {"V1", "V2"}, "Unknown diagnostic model lineage")
    versions = dict.fromkeys(sorted(VERSION_KEYS))
    if lineage == "V2":
        from src import expected_return_assumptions as a
        from src import expected_return_policy as p
        from src import expected_return_engine as e
        versions = {"constructor": a.EXPECTED_RETURN_CONSTRUCTOR_VERSION, "facts": a.EXPECTED_RETURN_FACTS_CONTRACT_VERSION,
            "methodology": e.EXPECTED_RETURN_METHODOLOGY_VERSION, "calculator_schema": e.EXPECTED_RETURN_SCHEMA_VERSION,
            "assumption_policy": p.EXPECTED_RETURN_ASSUMPTION_POLICY_SCHEMA_VERSION,
            "terminal_policy": p.EXPECTED_RETURN_TERMINAL_POLICY_SCHEMA_VERSION}
        _require(versions == V2_VERSIONS, "Unsupported frozen Expected Return contracts")
    entries = []
    for entry in sorted(inputs["entries"], key=lambda row: row["ticker"]):
        row = {"ticker": entry["ticker"], "input_status": entry["status"],
            "status": "NOT_AVAILABLE_IN_MODEL" if lineage == "V1" else "UNAVAILABLE",
            "security_id": None, "share_class": None, "unavailable_reasons": [], "policy_hashes": {},
            "lineage_hash": None, "confidence": [], "overall_confidence": None, "scenarios": {}}
        if lineage == "V1":
            row["unavailable_reasons"] = ["NOT_AVAILABLE_IN_MODEL"]
        elif entry["status"] == "EXPLICITLY_UNAVAILABLE":
            row["unavailable_reasons"] = sorted(entry["unavailable_reasons"])
        else:
            facts = decode(entry["facts"], "QualifiedFacts", a, p)
            policies = {key: decode(entry["policies"][key], kind, a, p) for key, kind in POLICY_TYPES.items()}
            # Contract errors propagate; valid economic insufficiency is a result.
            built = a.construct_expected_return(facts, mature_policy=policies["mature_growth"],
                terminal_policy=policies["terminal_valuation"], distribution_policy=policies["distributions"])
            row.update(status=built.status, security_id=facts.security_id, share_class=facts.share_class,
                unavailable_reasons=list(built.reasons), policy_hashes=dict(built.policy_hashes),
                lineage_hash=built.lineage_hash, confidence=json_value(built.confidence))
            if built.diagnostic is not None:
                row["overall_confidence"] = built.diagnostic.overall_confidence
                row["scenarios"] = {scenario.name: {key: json_value(getattr(scenario, key)) for key in sorted(SCENARIO_FIELDS)}
                                    for scenario in built.diagnostic.scenarios}
        entries.append(row)
    result = {**AUTHORITY, "schema_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION,
        "adapter_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION,
        "input_contract_version": PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION, "model_lineage": lineage,
        "status": "NOT_AVAILABLE_IN_MODEL" if lineage == "V1" else "COMPLETED",
        "comparison_status": "NOT_COMPARABLE", "coverage": "DECLARED_INPUTS_ONLY", "versions": versions,
        "counts": {"declared": len(entries), "built": sum(r["status"] == "BUILT" for r in entries),
            "unavailable": sum(r["status"] == "UNAVAILABLE" for r in entries),
            "not_available_in_model": sum(r["status"] == "NOT_AVAILABLE_IN_MODEL" for r in entries)}, "entries": entries}
    canonical(result)
    return result


def diagnostic_linkage(request):
    return {"comparison_id": request["comparison_id"], "execution_id": request["execution_id"],
        "bundle_hash": request["expected_bundle_hash"], "input_identity": request["input_identity"],
        "source_export_hash": request["source_provenance"]["source_export_hash"]}


def diagnostic_fingerprint(result):
    # Execution bindings are separately checked and covered by artifact hashes.
    return fingerprint({k: v for k, v in result.items() if k != "linkage"})


def validate_diagnostic(result, request):
    lineage = request["source_provenance"]["model_lineage"]
    closed(result, {*AUTHORITY, "schema_version", "adapter_version", "input_contract_version", "model_lineage", "status",
        "comparison_status", "coverage", "versions", "counts", "entries", "linkage"})
    expected = {**AUTHORITY, "schema_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION,
        "adapter_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION,
        "input_contract_version": PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION, "model_lineage": lineage,
        "status": "NOT_AVAILABLE_IN_MODEL" if lineage == "V1" else "COMPLETED",
        "comparison_status": "NOT_COMPARABLE", "coverage": "DECLARED_INPUTS_ONLY",
        "versions": dict.fromkeys(sorted(VERSION_KEYS)) if lineage == "V1" else V2_VERSIONS,
        "linkage": diagnostic_linkage(request)}
    _require(all(result[k] == v and type(result[k]) is type(v) for k, v in expected.items()), "Diagnostic authority/version/lineage/linkage mismatch")
    _require(type(result["entries"]) is list, "Diagnostic entries required")
    tickers = []
    for row in result["entries"]:
        closed(row, ENTRY_KEYS)
        shape(row["ticker"], "text")
        tickers.append(row["ticker"])
        shape(row["input_status"], ("QUALIFIED_SYNTHETIC", "EXPLICITLY_UNAVAILABLE"))
        shape(row["status"], ("NOT_AVAILABLE_IN_MODEL",) if lineage == "V1" else ("BUILT", "UNAVAILABLE"))
        shape(row["unavailable_reasons"], ["text"])
        _require(row["unavailable_reasons"] == sorted(set(row["unavailable_reasons"])), "Noncanonical diagnostic reasons")
        _require(type(row["policy_hashes"]) is dict and set(row["policy_hashes"]) <= set(POLICY_TYPES), "Diagnostic policy hashes malformed")
        for value in row["policy_hashes"].values():
            shape(value, "hash")
        if lineage == "V1" or row["input_status"] == "EXPLICITLY_UNAVAILABLE":
            _require(row["status"] != "BUILT" and row["security_id"] is None and row["share_class"] is None
                and row["lineage_hash"] is None and row["policy_hashes"] == {} and row["confidence"] == []
                and row["overall_confidence"] is None and row["scenarios"] == {} and bool(row["unavailable_reasons"]), "Fabricated absent diagnostic")
            if lineage == "V1":
                _require(row["unavailable_reasons"] == ["NOT_AVAILABLE_IN_MODEL"], "V1 diagnostic state mismatch")
            continue
        for key in ("security_id", "share_class"):
            shape(row[key], "text")
        shape(row["lineage_hash"], "hash")
        _require(type(row["confidence"]) is list, "Malformed confidence")
        for assessment in row["confidence"]:
            closed(assessment, CONFIDENCE_FIELDS)
            shape(assessment["component"], COMPONENTS)
            shape(assessment["root_ids"], ["text"])
            for key in CONFIDENCE_FIELDS - {"component", "root_ids"}:
                shape(assessment[key], ("NONE", "LOW", "MEDIUM", "HIGH"))
        if row["status"] == "UNAVAILABLE":
            _require(bool(row["unavailable_reasons"]) and row["scenarios"] == {} and row["overall_confidence"] is None, "Malformed unavailable diagnostic")
        else:
            _require(not row["unavailable_reasons"] and set(row["policy_hashes"]) == set(POLICY_TYPES), "Malformed built diagnostic")
            _require([r["component"] for r in row["confidence"]] == list(COMPONENTS), "Missing built confidence components")
            shape(row["overall_confidence"], ("NONE", "LOW", "MEDIUM", "HIGH"))
            closed(row["scenarios"], {"bear", "base", "bull"})
            for scenario in row["scenarios"].values():
                closed(scenario, SCENARIO_FIELDS)
                for key, value in scenario.items():
                    shape(value, ["number"] if key in {"growth_rates", "dividends_per_share"} else "number")
                    if isinstance(value, list):
                        _require(len(value) == 7, "Diagnostic horizon mismatch")
    _require(tickers == sorted(set(tickers)), "Noncanonical/duplicate diagnostic tickers")
    counts = {"declared": len(tickers), **{key: sum(r["status"] == status for r in result["entries"])
        for key, status in (("built", "BUILT"), ("unavailable", "UNAVAILABLE"), ("not_available_in_model", "NOT_AVAILABLE_IN_MODEL"))}}
    _require(result["counts"] == counts and all(type(v) is int for v in result["counts"].values()), "Diagnostic coverage mismatch")
    canonical(result)


def diagnostic_differences(first, second):
    return {**AUTHORITY, "schema_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION,
        "adapter_version": PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION, "comparison_status": "NOT_COMPARABLE",
        "reason": "V1_HAS_NO_COMPATIBLE_NUMERIC_EXPECTED_RETURN", "models": {
            lineage: {"linkage": result["linkage"], "diagnostic_fingerprint": diagnostic_fingerprint(result),
                "status": result["status"], "coverage": result["coverage"], "counts": result["counts"],
                "entries": [{k: row[k] for k in ("ticker", "status", "unavailable_reasons")} for row in result["entries"]]}
            for lineage, result in (("V1", first), ("V2", second))}}
