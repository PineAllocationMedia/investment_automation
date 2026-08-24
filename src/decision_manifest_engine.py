from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .baseline_identity import baseline_observation_metadata
from .dependency_reproducibility import dependency_environment
from .model_version import MODEL_RULES_VERSION
from .utils import load_json, save_json
from .validation_evidence import VALIDATION_SCHEMA_VERSION, normalize_run_purpose


MANIFEST_SCHEMA_VERSION = "2026-08-24-decision-run-manifest-v1"
TRANSIENT_PATH_KEYS = {
    "path",
    "file_path",
    "source_path",
    "cache_path",
    "project_root",
    "report_path",
    "temp_path",
    "temporary_path",
}
DECISION_OUTPUT_FIELDS = [
    "ticker",
    "universe",
    "score_total",
    "business_quality_score",
    "conviction_score",
    "capital_allocation_score",
    "expected_cagr_quality",
    "opportunity_cost_status",
    "add_eligibility_status",
    "thesis_status",
    "liquidation_status",
    "allocation_decision",
    "final_position_action",
    "sell_decision",
    "data_reliability_level",
    "current_value_cad",
    "position_weight",
    "applicable_hard_room",
    "limiting_room_reason",
]
ALLOCATION_OUTPUT_FIELDS = [
    "destination",
    "ticker",
    "montant",
    "amount",
    "pourcentage",
    "percentage",
    "bloc",
    "allocation_type",
    "raison",
    "reason",
]


def canonical_fingerprint(payload: Any) -> str:
    encoded = json.dumps(
        _canonicalize(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def git_commit_sha(project_root: str | Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(project_root),
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:  # noqa: BLE001
        return "UNKNOWN"
    value = completed.stdout.strip().lower()
    return value if len(value) == 40 and all(character in "0123456789abcdef" for character in value) else "UNKNOWN"


def build_decision_manifest(
    *,
    project_root: str | Path,
    run_id: str,
    run_timestamp: str,
    run_purpose: Any,
    mode: str,
    capital: Any,
    analyses_by_universe: dict[str, dict[str, dict[str, Any]]],
    allocation_result: dict[str, Any],
    research_inputs: Any,
    market_data: Any,
    benchmark_data: Any,
    baseline_metadata: dict[str, Any] | None = None,
    input_audit: dict[str, Any] | None = None,
    git_sha: str | None = None,
    dependency_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    baseline = baseline_metadata or baseline_observation_metadata(
        run_timestamp=run_timestamp,
        run_purpose=run_purpose,
        capital=capital,
        config_path=root / "config" / "baseline.yaml",
    )
    dependencies = dependency_payload or dependency_environment(root / "requirements.lock")
    config_fingerprints = _directory_file_fingerprints(root, root / "config", suffixes={".yaml", ".yml"})
    portfolio_fingerprints = _selected_file_fingerprints(
        root,
        [
            root / "data" / "portfolio.csv",
            root / "data" / "portfolio_transactions.csv",
            root / "data" / "watchlist.csv",
            root / "data" / "market_universe.csv",
        ],
    )
    manual_proxy_fingerprints = _selected_file_fingerprints(
        root,
        [
            root / "data" / "manual_inputs_friendly.txt",
            root / "data" / "proxy_calibration.csv",
            root / "config" / "proxy_corrections.yaml",
        ],
    )
    decision_payload = recommendation_payload(
        mode=mode,
        capital=capital,
        analyses_by_universe=analyses_by_universe,
        allocation_result=allocation_result,
    )
    decision_output_fingerprint = canonical_fingerprint(decision_payload)
    semantic_identity = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "baseline_id": baseline.get("baseline_id"),
        "model_rules_version": MODEL_RULES_VERSION,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
        "git_commit_sha": git_sha or git_commit_sha(root),
        "run_purpose": normalize_run_purpose(run_purpose),
        "mode": mode,
        "capital": capital,
        "config_fingerprint": config_fingerprints["combined_fingerprint"],
        "portfolio_input_fingerprint": portfolio_fingerprints["combined_fingerprint"],
        "proxy_manual_input_fingerprint": manual_proxy_fingerprints["combined_fingerprint"],
        "research_input_fingerprint": canonical_fingerprint(_without_transient_paths(research_inputs)),
        "dependency_fingerprint": dependencies.get("dependency_fingerprint"),
        "dependency_lock_fingerprint": dependencies.get("dependency_lock_fingerprint"),
        "market_data_fingerprint": canonical_fingerprint(_without_transient_paths(market_data)),
        "benchmark_data_fingerprint": canonical_fingerprint(_without_transient_paths(benchmark_data)),
        "decision_output_fingerprint": decision_output_fingerprint,
    }
    manifest = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "timestamp": run_timestamp,
        "run_purpose": normalize_run_purpose(run_purpose),
        "baseline": baseline,
        "model_rules_version": MODEL_RULES_VERSION,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
        "git_commit_sha": semantic_identity["git_commit_sha"],
        "mode": mode,
        "capital": capital,
        "config_fingerprints": config_fingerprints,
        "portfolio_input_fingerprints": portfolio_fingerprints,
        "proxy_manual_input_fingerprints": manual_proxy_fingerprints,
        "research_input_fingerprint": semantic_identity["research_input_fingerprint"],
        "dependency_environment": dependencies,
        "market_data_identity": {
            "market_data_fingerprint": semantic_identity["market_data_fingerprint"],
            "benchmark_data_fingerprint": semantic_identity["benchmark_data_fingerprint"],
            "market_ticker_count": len(market_data) if isinstance(market_data, dict) else 0,
            "benchmark_ticker_count": len(benchmark_data) if isinstance(benchmark_data, dict) else 0,
            "observation_timestamps": _observation_timestamp_summary(market_data, benchmark_data),
        },
        "critical_input_audit": input_audit or {},
        "decision_output_fingerprint": decision_output_fingerprint,
        "manifest_fingerprint": canonical_fingerprint(semantic_identity),
    }
    return manifest


def recommendation_payload(
    *,
    mode: str,
    capital: Any,
    analyses_by_universe: dict[str, dict[str, dict[str, Any]]],
    allocation_result: dict[str, Any],
) -> dict[str, Any]:
    analyses: list[dict[str, Any]] = []
    for universe, rows in sorted((analyses_by_universe or {}).items()):
        for ticker, row in sorted((rows or {}).items()):
            selected = {field: row.get(field) for field in DECISION_OUTPUT_FIELDS if field in row}
            selected["ticker"] = row.get("ticker") or ticker
            selected["universe"] = row.get("universe") or universe
            analyses.append(selected)
    allocations = [
        {field: row.get(field) for field in ALLOCATION_OUTPUT_FIELDS if field in row}
        for row in (allocation_result.get("allocations") or [])
    ]
    allocations.sort(
        key=lambda row: (
            str(row.get("destination") or row.get("ticker") or ""),
            str(row.get("bloc") or row.get("allocation_type") or ""),
        )
    )
    return {
        "mode": mode,
        "capital": capital,
        "allocations": allocations,
        "analyses": analyses,
        "mandatory_vfv_percent": allocation_result.get("mandatory_vfv_percent"),
        "average_score_ex_vfv": allocation_result.get("average_score_ex_vfv"),
        "decision_quality": allocation_result.get("decision_quality") or {},
    }


def write_decision_manifest(
    reports_dir: str | Path,
    manifest: dict[str, Any],
) -> dict[str, str]:
    reports = Path(reports_dir)
    run_id = str(manifest.get("run_id") or "unknown-run")
    history_dir = reports / "decision_manifests"
    history_path = history_dir / f"{run_id}.json"
    latest_path = reports / "latest_decision_manifest.json"
    _write_immutable_run_artifact(history_path, manifest)
    save_json(latest_path, manifest)
    return {
        "manifest_reference": f"reports/decision_manifests/{run_id}.json",
        "latest_manifest_reference": "reports/latest_decision_manifest.json",
        "manifest_fingerprint": str(manifest.get("manifest_fingerprint") or ""),
        "decision_output_fingerprint": str(manifest.get("decision_output_fingerprint") or ""),
        "git_commit_sha": str(manifest.get("git_commit_sha") or "UNKNOWN"),
    }


def write_failed_run_audit(
    *,
    reports_dir: str | Path,
    project_root: str | Path,
    run_id: str,
    run_timestamp: str,
    run_purpose: Any,
    mode: str,
    capital: Any,
    input_audit: dict[str, Any],
) -> dict[str, Any]:
    baseline = baseline_observation_metadata(
        run_timestamp=run_timestamp,
        run_purpose=run_purpose,
        capital=capital,
        config_path=Path(project_root) / "config" / "baseline.yaml",
    )
    payload = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "timestamp": run_timestamp,
        "status": "FAILED_CRITICAL_INPUT",
        "run_purpose": normalize_run_purpose(run_purpose),
        "baseline": {**baseline, "baseline_forward_eligible": False},
        "model_rules_version": MODEL_RULES_VERSION,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
        "git_commit_sha": git_commit_sha(project_root),
        "mode": mode,
        "capital": capital,
        "critical_input_audit": input_audit,
        "allocations": [],
        "genuine_forward_evidence": False,
        "decision_output_fingerprint": "",
    }
    reports = Path(reports_dir)
    _write_immutable_run_artifact(reports / "failed_run_audits" / f"{run_id}.json", payload)
    save_json(reports / "latest_failed_run_audit.json", payload)
    return payload


def _write_immutable_run_artifact(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        if load_json(path) != payload:
            raise FileExistsError(f"Refusing to overwrite conflicting per-run audit artifact: {path}")
        return
    save_json(path, payload)


def _directory_file_fingerprints(root: Path, directory: Path, *, suffixes: set[str]) -> dict[str, Any]:
    paths = [path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in suffixes]
    return _selected_file_fingerprints(root, paths)


def _selected_file_fingerprints(root: Path, paths: Iterable[Path]) -> dict[str, Any]:
    files: dict[str, str] = {}
    for path in sorted({Path(path) for path in paths}, key=lambda item: str(item)):
        logical_name = _logical_name(root, path)
        if not path.exists() or not path.is_file():
            files[logical_name] = "MISSING"
            continue
        files[logical_name] = canonical_fingerprint(_semantic_file_payload(path))
    return {"files": files, "combined_fingerprint": canonical_fingerprint(files)}


def _semantic_file_payload(path: Path) -> Any:
    if path.suffix.lower() == ".csv":
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                rows = [dict(row) for row in csv.DictReader(handle)]
            return sorted((_canonicalize(row) for row in rows), key=_canonical_sort_key)
        except Exception:  # noqa: BLE001
            return path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            return yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return path.read_text(encoding="utf-8", errors="replace")
    return path.read_text(encoding="utf-8", errors="replace")


def _logical_name(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _observation_timestamp_summary(*payloads: Any) -> list[str]:
    keys = {"fetched_at", "market_data_fetched_at", "as_of", "timestamp", "last_updated", "observation_date"}
    values: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key) in keys and item not in {None, ""}:
                    values.add(str(item))
                elif isinstance(item, (dict, list, tuple)):
                    visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    for payload in payloads:
        visit(payload)
    return sorted(values)


def _without_transient_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(raw_key): _without_transient_paths(item)
            for raw_key, item in value.items()
            if str(raw_key).strip().lower() not in TRANSIENT_PATH_KEYS
        }
    if isinstance(value, list):
        return [_without_transient_paths(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_without_transient_paths(item) for item in value)
    if isinstance(value, Path):
        return value.name
    return value


def _canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, set):
        return sorted((_canonicalize(item) for item in value), key=_canonical_sort_key)
    if isinstance(value, Path):
        return value.name
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 12)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    return str(value)


def _canonical_sort_key(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
