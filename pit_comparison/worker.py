"""One model, one fresh process, diagnostic outputs only."""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import AUTHORITY, PIT_ADAPTER_VERSION, PIT_COMPARISON_SCHEMA_VERSION
from .boundary import Boundary, dependency_roots, platform_roots
from .bundle import BundleError, canonical, digest, fingerprint, inventory, loads, verify_bundle
from .source_export import RULES, literal_assignment, verify_export


def prepare_inputs(bundle, runtime):
    config_dir = runtime / "effective_config"
    config_dir.mkdir()
    for name, value in bundle.get("config").items():
        # JSON is a YAML subset; existing model configuration parsers remain in use.
        (config_dir / name).write_bytes(canonical(value))
    prior = runtime / "prior" / "history"
    prior.mkdir(parents=True)
    state = bundle.get("prior_state")
    for kind in ("analysis", "allocation"):
        for index, row in enumerate(state[kind]):
            payload = {k: v for k, v in row.items() if k != "rows"}
            payload["analyses" if kind == "analysis" else "allocations"] = row["rows"]
            if row["storage_role"] == "LATEST":
                if row["analysis_mode"] not in {"balanced", "rational-aggressive", "family-office", "high-cagr"}:
                    raise BundleError("Unsupported latest prior mode")
                target = prior.parent / f"latest_{kind}_snapshot_{row['analysis_mode']}.json"
            else:
                target = prior / f"{kind}_{index:06d}.json"
            target.write_bytes(canonical(payload))
    return (config_dir, runtime / "prior")


def install_http_sentinels(boundary):
    # requests/urllib3 probe IPv6 by constructing sockets during import. The
    # decision adapter needs no HTTP implementation, so expose fatal interfaces
    # before model modules import requests, instead of importing that stack.
    import types
    module = types.ModuleType("requests")
    module.__path__ = []
    for name in ("request", "get", "post", "put", "delete", "head", "options", "patch", "Session", "session"):
        setattr(module, name, boundary.sentinel("requests." + name))
    exceptions = types.ModuleType("requests.exceptions")
    for name in ("RequestException", "HTTPError", "ConnectionError", "Timeout"):
        setattr(exceptions, name, type(name, (RuntimeError,), {}))
        setattr(module, name, getattr(exceptions, name))
    module.exceptions = exceptions
    sessions = types.ModuleType("requests.sessions")
    sessions.Session = module.Session
    module.sessions = sessions
    sys.modules.update({"requests": module, "requests.exceptions": exceptions, "requests.sessions": sessions})


def semantic_json(value):
    """Lossless JSON representation of model containers; no numeric rounding."""
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise BundleError("Non-string semantic object key")
        return {k: semantic_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [semantic_json(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((semantic_json(v) for v in value), key=canonical)
    return value


def execute(request, *, evaluator=None):
    """evaluator is a code-only synthetic reference seam; CLI never accepts one."""
    source, root = Path(request["source_root"]), Path(request["worker_root"])
    runtime = root / "runtime"
    result_path = runtime / "result.json"
    runtime.mkdir(exist_ok=True)
    boundary = None
    try:
        if "src" in sys.modules or "main" in sys.modules:
            raise BundleError("Worker must start without model imports")
        bundle = verify_bundle(Path(request["bundle_root"]), request["expected_bundle_hash"], require_complete=True)
        provenance = verify_export(source, request["source_provenance"])
        harness_files = inventory(Path(request["harness_root"]) / "pit_comparison")
        harness_hash = fingerprint([{"path": "pit_comparison/" + name, "sha256": digest(raw)}
            for name, raw in sorted(harness_files.items())])
        if harness_hash != request["harness_hash"] or bundle.manifest["input_identity"] != request["input_identity"]:
            raise BundleError("Harness/input request attestation mismatch")
        if set(p.name for p in runtime.iterdir()) != {"bundle"}:
            raise BundleError("Worker runtime must be fresh except for verified bundle")
        immutable = prepare_inputs(bundle, runtime)
        lineage = provenance["model_lineage"]
        sys.dont_write_bytecode = True
        if lineage == "V2":
            os.environ["INVESTMENT_AUTOMATION_RUNTIME_PROFILE"] = "v2-restricted"
            os.environ["INVESTMENT_AUTOMATION_RUNTIME_ROOT"] = str(runtime)
            os.environ["INVESTMENT_AUTOMATION_FORBIDDEN_ROOTS"] = os.pathsep.join(request["forbidden_roots"])
        tempfile.tempdir = os.environ["TMPDIR"]
        reads = [source, root, Path(request["harness_root"]), *dependency_roots(), *platform_roots()]
        boundary = Boundary(read_roots=reads, writable_root=root,
            immutable_roots=[source, Path(request["bundle_root"]), *immutable],
            forbidden_roots=request["forbidden_roots"])
        boundary.install()
        install_http_sentinels(boundary)
        sys.path.insert(0, str(source))
        from .adapter import bind_inputs, evaluate
        # All harness modules (and the test oracle, when present) are loaded.
        # Remove the bootstrap search path before PR1 activation so subsequent
        # model/dependency imports never probe an external harness directory.
        sys.path = [p for p in sys.path if p != request["harness_root"]]
        import src
        if lineage == "V2":
            from src.runtime_context import RUNTIME, RuntimeIsolationError
            native_error_init = RuntimeIsolationError.__init__
            def record_native_error(error, *args):
                boundary.violations.append("Native PR1 containment: " + str(args))
                native_error_init(error, *args)
            # Retain every native check, including check_analysis. Observation of
            # its exception construction makes caught native denials irreversible.
            RuntimeIsolationError.__init__ = record_native_error
            from src.model_identity import current_model_identity
            if not RUNTIME.restricted or RUNTIME.root != runtime or current_model_identity()["model_lineage"] != "V2" or current_model_identity()["validation_authority"] != "NONE":
                raise BundleError("V2 runtime/native identity mismatch")
        model = bind_inputs(bundle, source, runtime, boundary)
        from src.dependency_reproducibility import dependency_environment
        dependencies = dependency_environment(source / "requirements.lock")
        if dependencies["dependency_status"] != "MATCH":
            raise BundleError("Locked dependency environment mismatch: " + str(dependencies))
        semantic = semantic_json((evaluator or evaluate)(bundle, model))
        canonical(semantic)
        if boundary.violations:
            raise BundleError("Caught containment violation")
        if bundle.consumed != set(bundle.data):
            raise BundleError("Input-consumption contract incomplete")
        # Recheck immutable inputs and source after execution, before success.
        verify_bundle(Path(request["bundle_root"]), request["expected_bundle_hash"], require_complete=True)
        verify_export(source, provenance)
        from src.validation_evidence import VALIDATION_SCHEMA_VERSION
        result = {**AUTHORITY, "schema_version": PIT_COMPARISON_SCHEMA_VERSION,
            "status": "SUCCEEDED", "comparison_id": request["comparison_id"], "execution_id": request["execution_id"],
            "bundle_hash": bundle.manifest["bundle_hash"], "input_identity": bundle.manifest["input_identity"],
            "effective_pit_at": bundle.manifest["effective_pit_at"],
            "investment_mode": bundle.manifest["investment_mode"], "capital_context": bundle.manifest["capital_context"],
            "artifact_created_at": datetime.now(timezone.utc).isoformat(),
            "runtime_diagnostics": {"process_id": os.getpid(), "hash_seed_probe": hash("pit-comparison-seed-probe")},
            "model_provenance": {**provenance, "model_rules_version": model.MODEL_RULES_VERSION,
                "validation_schema_version": VALIDATION_SCHEMA_VERSION,
                "lineage_origin": "NATIVE" if lineage == "V2" else "EXTERNAL_COMPARISON_PROVENANCE",
                "effective_config_hash": fingerprint(bundle.data["config"]),
                "adapter_version": PIT_ADAPTER_VERSION, "harness_hash": request["harness_hash"],
                "dependencies": dependencies},
            "containment": boundary.status(), "consumed_logical_inputs": sorted(bundle.consumed),
            "completeness_status": "COMPLETE_PIT", "semantic_result": semantic,
            "semantic_fingerprint": fingerprint(semantic)}
    except Exception as exc:
        result = {**AUTHORITY, "schema_version": PIT_COMPARISON_SCHEMA_VERSION,
            "status": "CONTAINMENT_FAILED" if boundary and boundary.violations else "FAILED",
            "comparison_id": request.get("comparison_id"), "execution_id": request.get("execution_id"),
            "error_type": type(exc).__name__, "error": str(exc),
            "containment": boundary.status() if boundary else {"containment_level": "APPLICATION_GUARDED", "status": "NOT_STARTED"}}
    result_path.write_bytes(canonical(result))
    return 0 if result["status"] == "SUCCEEDED" else 2


def main():
    if len(sys.argv) != 2:
        raise SystemExit("worker requires one request file")
    request = loads(Path(sys.argv[1]).read_bytes())
    return execute(request)


if __name__ == "__main__":
    raise SystemExit(main())
