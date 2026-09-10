"""Parent orchestration: no imports from src, no live data collection."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import AUTHORITY, CONTAINMENT_LEVEL, PIT_ADAPTER_VERSION, PIT_COMPARISON_SCHEMA_VERSION
from .boundary import clean_environment
from .bundle import BundleError, FAMILIES, canonical, digest, fingerprint, inventory, loads, verify_bundle
from .expected_return_diagnostics import validate_diagnostic, diagnostic_fingerprint, diagnostic_differences
from .source_export import V1_SHA, V2_SHA, export_revision, verify_export, git


class ComparisonError(RuntimeError):
    pass


def overlap(a, b):
    a, b = Path(a).resolve(), Path(b).resolve()
    return a.is_relative_to(b) or b.is_relative_to(a)


def validate_store(store, repo, bundle, extra_forbidden=()):
    store, repo, bundle = Path(store).absolute(), Path(repo).resolve(), Path(bundle).absolute()
    for path in (store, *store.parents):
        if path.is_symlink():
            raise BundleError("Symlink comparison store")
    home = Path.home()
    # Git administrative metadata identifies sibling production/development
    # checkouts without opening any operational input from those checkouts.
    checkout_roots = [Path(line[9:]) for line in git(repo, "worktree", "list", "--porcelain").decode().splitlines()
                      if line.startswith("worktree ")]
    denied = [*checkout_roots, *[repo / p for p in ("data", "reports", "backups", ".git", ".venv")]]
    denied += [home / "Library/CloudStorage", home / ".config/investment_automation",
               home / ".local/state/investment_automation", home / ".local/state/investment_automation_v2",
               home / "investment_automation_run_logs", *map(Path, extra_forbidden)]
    if any(overlap(store, p) for p in denied) or overlap(store, bundle):
        raise BundleError("Comparison store overlaps input/operational state")
    if overlap(store, repo) or store == home or any(part in {"reports", "history", "backups"} for part in store.parts):
        raise BundleError("Dedicated comparison output directory required")
    if any(overlap(bundle, p) for p in denied):
        raise BundleError("Operational state is not an authorized bundle root")
    return store.resolve(), [str(p.resolve()) for p in denied]


def isolated_python_setup():
    """With -S -s and a sanitized environment, explicitly load the pinned environment without .pth/sitecustomize."""
    environment = {"prefix": sys.prefix, "exec_prefix": sys.exec_prefix,
                   "packages": sorted({sysconfig.get_path("purelib"), sysconfig.get_path("platlib")})}
    return "import sys,json; sys.path=[p for p in sys.path if p]; e=json.loads(sys.argv.pop(1)); sys.prefix=e['prefix']; sys.exec_prefix=e['exec_prefix']; sys.path.extend(e['packages']); ", canonical(environment).decode()


def snapshot_harness(destination):
    package = Path(__file__).resolve().parent
    destination.mkdir()
    target = destination / "pit_comparison"
    target.mkdir()
    records = []
    for path in sorted(package.glob("*.py")):
        if path.is_symlink() or path.stat().st_nlink != 1:
            raise BundleError("Linked harness source")
        raw = path.read_bytes()
        (target / path.name).write_bytes(raw)
        records.append({"path": "pit_comparison/" + path.name, "sha256": digest(raw)})
    return fingerprint(records)


def validate_result(result, request):
    if result.get("status") != "SUCCEEDED":
        raise ComparisonError(f"{request['source_provenance']['model_lineage']} worker failed: {result.get('status')}: {result.get('error')}; {result.get('containment')}")
    expected_keys = {*AUTHORITY, "schema_version", "status", "comparison_id", "execution_id", "bundle_hash", "input_identity",
        "effective_pit_at", "investment_mode", "capital_context", "artifact_created_at", "runtime_diagnostics", "model_provenance",
        "containment", "consumed_logical_inputs", "completeness_status", "semantic_result", "semantic_fingerprint",
        "diagnostic_result", "diagnostic_fingerprint"}
    if set(result) != expected_keys:
        raise ComparisonError("Result closed schema mismatch")
    for key, value in AUTHORITY.items():
        if result.get(key) != value or type(result.get(key)) is not type(value):
            raise ComparisonError("Retrospective authority mismatch")
    for key in ("comparison_id", "execution_id"):
        if result.get(key) != request[key]:
            raise ComparisonError("Execution linkage mismatch")
    if result.get("bundle_hash") != request["expected_bundle_hash"] or result.get("input_identity") != request["input_identity"]:
        raise ComparisonError("Bundle attestation mismatch")
    if result.get("schema_version") != PIT_COMPARISON_SCHEMA_VERSION:
        raise ComparisonError("Result schema mismatch")
    if "decision_context" in request and any(result.get(k) != v for k, v in request["decision_context"].items()):
        raise ComparisonError("Decision context mismatch")
    p = result.get("model_provenance", {})
    if any(p.get(k) != v for k, v in request["source_provenance"].items()):
        raise ComparisonError("Model revision/export mismatch")
    if p.get("harness_hash") != request["harness_hash"] or p.get("adapter_version") != PIT_ADAPTER_VERSION:
        raise ComparisonError("Harness/adapter provenance mismatch")
    if p.get("dependencies", {}).get("dependency_status") != "MATCH":
        raise ComparisonError("Dependency attestation mismatch")
    if result.get("containment") != {**result.get("containment", {}), "status": "PASSED", "containment_level": CONTAINMENT_LEVEL, "violations": []}:
        raise ComparisonError("Containment attestation failed")
    if result.get("consumed_logical_inputs") != sorted(FAMILIES) or result.get("completeness_status") != "COMPLETE_PIT":
        raise ComparisonError("Input-consumption/completeness mismatch")
    semantic = result.get("semantic_result")
    if not isinstance(semantic, dict) or set(semantic) != {"investment_mode", "capital", "analyses", "allocation", "rankings", "concentration", "tax", "portfolio"}:
        raise ComparisonError("Malformed semantic result")
    if semantic["investment_mode"] != result["investment_mode"] or semantic["capital"] != result["capital_context"]["amount"]:
        raise ComparisonError("Semantic decision context mismatch")
    if fingerprint(semantic) != result.get("semantic_fingerprint"):
        raise ComparisonError("Semantic fingerprint mismatch")

    try:
        validate_diagnostic(result["diagnostic_result"], request)
        if diagnostic_fingerprint(result["diagnostic_result"]) != result["diagnostic_fingerprint"]:
            raise BundleError("Diagnostic fingerprint mismatch")
    except (BundleError, KeyError, TypeError, AttributeError) as exc:
        raise ComparisonError("Invalid diagnostic result: " + str(exc)) from exc


CORRESPONDING_FIELDS = ("score_total", "conviction_score", "capital_allocation_score", "expected_cagr_quality",
    "expected_cagr", "opportunity_cost_status", "add_eligibility_status", "liquidation_status", "final_position_action")


def differences(first, second):
    rows = []
    for universe in sorted(set(first["analyses"]) | set(second["analyses"])):
        left, right = first["analyses"].get(universe, {}), second["analyses"].get(universe, {})
        for ticker in sorted(set(left) | set(right)):
            a, b = left.get(ticker, {}), right.get(ticker, {})
            fields = {}
            metrics = set(CORRESPONDING_FIELDS) | {k for k in set(a) | set(b) if any(term in k for term in ("score", "cagr", "expected_return"))}
            for name in sorted(metrics):
                if name not in CORRESPONDING_FIELDS or name not in a or name not in b:
                    fields[name] = {"status": "NOT_COMPARABLE", "v1": a.get(name), "v2": b.get(name)}
                elif a[name] != b[name]:
                    fields[name] = {"status": "DIFFERENT", "v1": a[name], "v2": b[name]}
            rows.append({"universe": universe, "ticker": ticker, "membership": "BOTH" if ticker in left and ticker in right else "V1_ONLY" if ticker in left else "V2_ONLY", "fields": fields})
    return {"analyses": rows, **{key: {"status": "EQUAL" if first[key] == second[key] else "DIFFERENT",
            "v1": first[key], "v2": second[key]} for key in ("allocation", "rankings", "concentration")}}


def run_comparison(*, repo, bundle_root, expected_bundle_hash, store, v2_revision=V2_SHA,
                   hash_seed="0", execution_order=("V1", "V2"), source_preparer=export_revision):
    """source_preparer is a code-only offline fixture seam, never a CLI option."""
    if tuple(sorted(execution_order)) != ("V1", "V2"):
        raise BundleError("Exactly one execution of each model required")
    store, denied = validate_store(store, repo, bundle_root)
    bundle = verify_bundle(Path(bundle_root), expected_bundle_hash, require_complete=True)
    comparison_id = "cmp-" + uuid.uuid4().hex
    store.mkdir(parents=True, exist_ok=True)
    # Exclusive reservation; concurrent callers can never share staging/IDs.
    stage = store / (".staging-" + comparison_id)
    stage.mkdir()
    try:
        with tempfile.TemporaryDirectory(prefix="pit-comparison-") as temporary:
            temp = Path(temporary).resolve()
            harness_root = temp / "harness"
            harness_hash = snapshot_harness(harness_root)
            results, requests = {}, {}
            for lineage, revision in (("V1", V1_SHA), ("V2", v2_revision)):
                source = temp / (lineage + "-source")
                provenance = source_preparer(Path(repo), revision, source, lineage=lineage)
                verify_export(source, provenance)
                if provenance["model_lineage"] != lineage:
                    raise ComparisonError("Selected model lineage mismatch")
                worker = temp / (lineage + "-worker")
                worker.mkdir()
                materialized = worker / "runtime" / "bundle"
                bundle.materialize(materialized)
                request = {"comparison_id": comparison_id, "execution_id": "exec-" + uuid.uuid4().hex,
                    "worker_root": str(worker), "source_root": str(source), "bundle_root": str(materialized),
                    "expected_bundle_hash": expected_bundle_hash, "input_identity": bundle.manifest["input_identity"],
                    "decision_context": {k: bundle.manifest[k] for k in ("effective_pit_at", "investment_mode", "capital_context")},
                    "source_provenance": provenance, "harness_root": str(harness_root), "harness_hash": harness_hash,
                    "forbidden_roots": [*denied, str(Path(repo).resolve()), str(temp / (("V2" if lineage == "V1" else "V1") + "-worker")), str(store)]}
                requests[lineage] = request
            for lineage in execution_order:
                request = requests[lineage]
                worker = Path(request["worker_root"])
                request_file = worker / "request.json"
                request_file.write_bytes(canonical(request))
                env = clean_environment(worker, hash_seed=hash_seed)
                # Sanitized environment, no site startup, and no cwd on sys.path.
                # PYTHONHASHSEED is deliberately honored for perturbation tests.
                setup, environment = isolated_python_setup()
                bootstrap = setup + "sys.path.insert(0, sys.argv.pop(1)); from pit_comparison.worker import main; raise SystemExit(main())"
                completed = subprocess.run([sys.executable, "-s", "-S", "-B", "-c", bootstrap, environment, str(harness_root), str(request_file)],
                    cwd=worker, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=120, close_fds=True)
                output = worker / "runtime" / "result.json"
                if not output.is_file():
                    raise ComparisonError(f"{lineage} worker exited {completed.returncode}: {completed.stderr.decode(errors='replace')[-3000:]}")
                raw = output.read_bytes()
                result = loads(raw)
                validate_result(result, request)
                if completed.returncode:
                    raise ComparisonError("Worker exited unsuccessfully despite result")
                results[lineage] = (result, raw)
            spec = {"decision_context": {k: bundle.manifest[k] for k in ("effective_pit_at", "investment_mode", "capital_context")}, "bundle_hash": expected_bundle_hash, "input_identity": bundle.manifest["input_identity"],
                    "models": {k: r["source_provenance"] for k, r in requests.items()},
                    "adapter_version": PIT_ADAPTER_VERSION, "harness_hash": harness_hash,
                    "effective_config_hash": fingerprint(bundle.data["config"]), "comparison_mode": "RETROSPECTIVE_PIT"}
            manifest = {**AUTHORITY, "schema_version": PIT_COMPARISON_SCHEMA_VERSION,
                "comparison_id": comparison_id, "comparison_spec_hash": fingerprint(spec), "specification": spec,
                "bundle_id": bundle.manifest["bundle_id"], "bundle_hash": expected_bundle_hash,
                "input_identity": bundle.manifest["input_identity"], "effective_pit_at": bundle.manifest["effective_pit_at"],
                "artifact_created_at": datetime.now(timezone.utc).isoformat(), "status": "SUCCEEDED",
                "containment_level": CONTAINMENT_LEVEL, "executions": {}}
            for lineage, (result, raw) in results.items():
                target = stage / "executions" / result["execution_id"]
                target.mkdir(parents=True)
                (target / "result.json").write_bytes(raw)
                manifest["executions"][lineage] = {"execution_id": result["execution_id"],
                    "path": f"executions/{result['execution_id']}/result.json", "artifact_sha256": digest(raw),
                    "semantic_fingerprint": result["semantic_fingerprint"],
                    "diagnostic_fingerprint": result["diagnostic_fingerprint"]}
            delta = canonical(differences(results["V1"][0]["semantic_result"], results["V2"][0]["semantic_result"]))
            (stage / "differences.json").write_bytes(delta)
            manifest["differences_sha256"] = digest(delta)
            diagnostic_delta = canonical(diagnostic_differences(results["V1"][0]["diagnostic_result"], results["V2"][0]["diagnostic_result"]))
            (stage / "diagnostic_differences.json").write_bytes(diagnostic_delta)
            manifest["diagnostic_differences"] = {"path": "diagnostic_differences.json", "sha256": digest(diagnostic_delta)}
            (stage / "comparison_manifest.json").write_bytes(canonical(manifest))
            verify_pair(stage)
            verify_bundle(Path(bundle_root), expected_bundle_hash, require_complete=True)
            final_root = store / "comparisons"
            final_root.mkdir(exist_ok=True)
            final = final_root / comparison_id
            if final.exists():
                raise ComparisonError("Comparison ID already published")
            os.rename(stage, final)
            return final
    except Exception as exc:
        failure_root = store / "failures" / comparison_id
        failure_root.mkdir(parents=True, exist_ok=False)
        (failure_root / "failure.json").write_bytes(canonical({**AUTHORITY, "comparison_id": comparison_id,
            "status": "FAILED", "containment_level": CONTAINMENT_LEVEL, "error": str(exc)}))
        shutil.rmtree(stage)
        raise


def verify_pair(root):
    files = inventory(Path(root))
    manifest = loads(files["comparison_manifest.json"])
    expected = {"comparison_manifest.json", "differences.json", "diagnostic_differences.json"}
    diagnostics = {}
    if manifest.get("executions", {}).keys() != {"V1", "V2"}:
        raise ComparisonError("Incomplete pair")
    spec = manifest["specification"]
    if (manifest.get("status") != "SUCCEEDED" or manifest.get("containment_level") != CONTAINMENT_LEVEL
            or manifest.get("schema_version") != PIT_COMPARISON_SCHEMA_VERSION
            or manifest.get("bundle_id") != "sha256:" + manifest["bundle_hash"]
            or any(manifest[k] != spec[k] for k in ("bundle_hash", "input_identity"))
            or manifest["effective_pit_at"] != spec["decision_context"]["effective_pit_at"]):
        raise ComparisonError("Parent specification linkage mismatch")
    execution_ids = set()
    for lineage, link in manifest["executions"].items():
        if spec["models"][lineage]["model_lineage"] != lineage:
            raise ComparisonError("Parent model lineage mismatch")
        path = link["path"]
        if path != f"executions/{link['execution_id']}/result.json" or link["execution_id"] in execution_ids:
            raise ComparisonError("Execution identity mismatch")
        execution_ids.add(link["execution_id"])
        expected.add(path)
        raw = files.get(path, b"")
        if digest(raw) != link["artifact_sha256"]:
            raise ComparisonError("Result artifact hash mismatch")
        result = loads(raw)
        spec = manifest["specification"]
        validate_result(result, {"comparison_id": manifest["comparison_id"], "execution_id": link["execution_id"],
            "expected_bundle_hash": manifest["bundle_hash"], "input_identity": manifest["input_identity"],
            "decision_context": spec["decision_context"], "source_provenance": spec["models"][lineage], "harness_hash": spec["harness_hash"]})
        diagnostics[lineage] = result["diagnostic_result"]
        if result["diagnostic_fingerprint"] != link.get("diagnostic_fingerprint"):
            raise ComparisonError("Diagnostic link mismatch")
        if result["semantic_fingerprint"] != link["semantic_fingerprint"]:
            raise ComparisonError("Semantic link mismatch")
    if set(files) != expected or digest(files["differences.json"]) != manifest["differences_sha256"]:
        raise ComparisonError("Pair inventory/difference hash mismatch")
    diagnostic_raw = files.get("diagnostic_differences.json", b"")
    if (manifest.get("diagnostic_differences") != {"path": "diagnostic_differences.json", "sha256": digest(diagnostic_raw)}
            or diagnostic_raw != canonical(diagnostic_differences(diagnostics["V1"], diagnostics["V2"]))):
        raise ComparisonError("Diagnostic differences hash/content/linkage mismatch")
    if fingerprint(manifest["specification"]) != manifest["comparison_spec_hash"] or any(manifest.get(k) != v or type(manifest.get(k)) is not type(v) for k, v in AUTHORITY.items()):
        raise ComparisonError("Comparison specification/authority mismatch")
    return manifest
