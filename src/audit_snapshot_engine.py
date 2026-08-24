from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .model_version import MODEL_RULES_VERSION
from .utils import read_csv_records, safe_float, save_json, today_iso
from .validation_evidence import RunPurpose, VALIDATION_SCHEMA_VERSION, normalize_run_purpose


SNAPSHOT_BLOCK_KEYS = [
    "meta",
    "allocation",
    "anomalies",
    "validation",
    "walk_forward",
    "source_health",
    "proxy_calibration",
    "model_audit",
    "run_log_summary",
]


def save_audit_snapshot(
    *,
    reports_dir: str | Path,
    analysis_mode: str | None,
    allocation_result: dict,
    anomaly_rows: list[dict],
    validation_priority_rows: list[dict],
    run_log_rows: list[dict],
) -> None:
    reports_path = Path(reports_dir)
    current = _build_current_run_snapshot(
        reports_dir=reports_path,
        analysis_mode=analysis_mode,
        allocation_result=allocation_result,
        anomaly_rows=anomaly_rows,
        validation_priority_rows=validation_priority_rows,
        run_log_rows=run_log_rows,
    )
    mode_slug = _mode_slug(analysis_mode)
    history_dir = reports_path / "history"
    previous_runs = _load_previous_run_snapshots(
        history_dir=history_dir,
        mode_slug=mode_slug,
        current_run_date=str(current.get("meta", {}).get("run_date") or ""),
    )
    runs_history = [current, *previous_runs[:4]]
    payload = {
        **current,
        "delta_analysis": _build_delta_analysis(runs_history),
        "runs_history": runs_history[:5],
    }

    created_at = str(current.get("meta", {}).get("created_at") or datetime.now().replace(microsecond=0).isoformat())
    timestamp = _timestamp_for_filename(created_at)
    save_json(reports_path / f"latest_audit_snapshot_{mode_slug}.json", payload)
    save_json(history_dir / f"audit_{mode_slug}_{timestamp}.json", payload)


def _build_current_run_snapshot(
    *,
    reports_dir: Path,
    analysis_mode: str | None,
    allocation_result: dict,
    anomaly_rows: list[dict],
    validation_priority_rows: list[dict],
    run_log_rows: list[dict],
) -> dict:
    now = datetime.now().replace(microsecond=0)
    mode = str(analysis_mode or "unknown")
    run_purpose = next(
        (normalize_run_purpose(row.get("run_purpose")) for row in run_log_rows if row.get("run_purpose")),
        RunPurpose.UNKNOWN_LEGACY.value,
    )
    baseline = allocation_result.get("baseline_identity") or {}
    manifest = allocation_result.get("decision_manifest") or {}
    return {
        "meta": {
            "run_date": today_iso(),
            "created_at": now.isoformat(),
            "analysis_mode": mode,
            "model_rules_version": MODEL_RULES_VERSION,
            "validation_schema_version": VALIDATION_SCHEMA_VERSION,
            "run_purpose": run_purpose,
            "baseline_id": baseline.get("baseline_id", ""),
            "baseline_started_at": baseline.get("baseline_started_at", ""),
            "baseline_evidence_status": baseline.get("baseline_evidence_status", ""),
            "baseline_forward_eligible": baseline.get("baseline_forward_eligible", False),
            "git_commit_sha": manifest.get("git_commit_sha", ""),
            "manifest_reference": manifest.get("manifest_reference", ""),
            "manifest_fingerprint": manifest.get("manifest_fingerprint", ""),
            "decision_output_fingerprint": manifest.get("decision_output_fingerprint", ""),
            "capital": _number(allocation_result.get("monthly_contribution"), _allocation_total(allocation_result)),
            "portfolio_total_value": _number(allocation_result.get("portfolio_total_value_cad"), 0.0),
        },
        "allocation": _allocation_block(allocation_result),
        "anomalies": _anomaly_block(anomaly_rows),
        "validation": _validation_block(validation_priority_rows),
        "walk_forward": _walk_forward_block(reports_dir, mode),
        "source_health": _source_health_block(reports_dir),
        "proxy_calibration": _proxy_calibration_block(reports_dir),
        "model_audit": _model_audit_block(reports_dir, mode),
        "run_log_summary": _run_log_summary_block(run_log_rows),
    }


def _allocation_block(allocation_result: dict) -> dict:
    rows = []
    for row in allocation_result.get("allocations", []) or []:
        amount = _number(row.get("amount", row.get("montant")), 0.0)
        percentage = _number(row.get("percentage", row.get("pourcentage")), 0.0)
        if 0 < percentage <= 1:
            percentage = round(percentage * 100.0, 4)
        rows.append(
            {
                "ticker": row.get("ticker") or row.get("destination") or row.get("symbol"),
                "amount": amount,
                "percentage": percentage,
                "confidence": row.get("confidence") or row.get("niveau de confiance"),
                "allocation_decision": row.get("allocation_decision") or row.get("decision") or row.get("règle appliquée"),
            }
        )
    decision_quality = allocation_result.get("decision_quality") or {}
    return {
        "allocation": rows,
        "decision_quality_score": _number(
            allocation_result.get("decision_quality_score", decision_quality.get("decision_quality_score")),
            None,
        ),
        "decision_quality_label": allocation_result.get("decision_quality_label")
        or decision_quality.get("decision_quality_level"),
        "robustness_score": _number(allocation_result.get("robustness_score"), None),
        "robustness_label": allocation_result.get("robustness_label"),
    }


def _anomaly_block(anomaly_rows: list[dict]) -> dict:
    rows = anomaly_rows or []
    levels = [str(row.get("niveau") or row.get("severity") or "").upper() for row in rows]
    high_count = sum(1 for level in levels if level == "HIGH")
    medium_count = sum(1 for level in levels if level == "MEDIUM")
    if high_count:
        max_level = "HIGH"
    elif medium_count:
        max_level = "MEDIUM"
    elif rows:
        max_level = "LOW"
    else:
        max_level = "NONE"
    return {
        "anomaly_count": len(rows),
        "anomaly_max_level": max_level,
        "anomaly_high_count": high_count,
        "anomaly_medium_count": medium_count,
        "anomalies": [
            {
                "scope": row.get("scope"),
                "ticker": row.get("ticker"),
                "niveau": row.get("niveau") or row.get("severity"),
                "signal": row.get("signal") or row.get("anomaly_type"),
                "metrique": row.get("metrique") or row.get("metric"),
                "variation": row.get("variation") or row.get("change"),
            }
            for row in rows
        ],
    }


def _validation_block(validation_priority_rows: list[dict]) -> dict:
    priority_values = {"TRES_HAUTE", "TRÈS_HAUTE", "HAUTE", "CRITICAL", "HIGH"}
    selected = [
        row
        for row in validation_priority_rows or []
        if str(row.get("importance") or row.get("priority") or "").upper() in priority_values
    ]
    return {
        "validation_high_critical_count": len(selected),
        "validation_top_items": [
            {
                "ticker": row.get("ticker"),
                "donnee": row.get("donnee") or row.get("donnée") or row.get("field_label") or row.get("field"),
                "importance": row.get("importance") or row.get("priority"),
            }
            for row in selected[:5]
        ],
    }


def _walk_forward_block(reports_dir: Path, mode: str) -> dict | None:
    path = reports_dir / f"latest_walk_forward_inventory_{_mode_slug(mode)}.csv"
    if not path.exists():
        return None
    rows = _safe_read_csv(path)
    if not rows:
        return None
    usable_count = sum(1 for row in rows if _truthy(row.get("usable") or row.get("usable_for_walk_forward")))
    if usable_count >= 12:
        status = "SUFFICIENT"
    elif usable_count >= 6:
        status = "PARTIAL"
    else:
        status = "INSUFFICIENT"
    summary_row = next((row for row in rows if _truthy(row.get("summary") or row.get("is_summary"))), {})
    return {
        "periods_available": len(rows),
        "periods_usable": usable_count,
        "status": status,
        "vs_vfv_status": summary_row.get("vs_vfv_status") or None,
        "vs_vfv_excess_return": _number(summary_row.get("excess_return_vs_vfv"), None),
        "insufficient_reason": None if status == "SUFFICIENT" else f"{usable_count} période(s) utilisable(s) sur 12 recommandées.",
    }


def _source_health_block(reports_dir: Path) -> dict | None:
    rows = _safe_read_csv(reports_dir / "latest_source_health.csv")
    if not rows:
        return None
    counts = {"OK": 0, "WATCH": 0, "DEGRADED": 0, "FAIL": 0}
    worst_row = None
    worst_rank = -1
    for row in rows:
        status = str(row.get("status") or row.get("statut") or "").upper()
        if status in counts:
            counts[status] += 1
        rank = {"OK": 0, "WATCH": 1, "DEGRADED": 2, "FAIL": 3}.get(status, -1)
        if rank > worst_rank:
            worst_rank = rank
            worst_row = row
    return {
        "sources_ok": counts["OK"],
        "sources_watch": counts["WATCH"],
        "sources_degraded": counts["DEGRADED"],
        "worst_source": (worst_row or {}).get("source"),
        "worst_status": (worst_row or {}).get("status") or (worst_row or {}).get("statut"),
    }


def _proxy_calibration_block(reports_dir: Path) -> dict | None:
    rows = _safe_read_csv(reports_dir / "latest_proxy_calibration.csv")
    if rows and not any("reliability_status" in row for row in rows):
        summary_rows = _safe_read_csv(reports_dir / "latest_proxy_calibration_summary.csv")
        if summary_rows:
            rows = summary_rows
    if not rows:
        return None
    recalibration = [row.get("field") for row in rows if row.get("reliability_status") == "RECALIBRATION_CANDIDATE" and row.get("field")]
    monitor = [row for row in rows if row.get("reliability_status") == "MONITOR_MORE_EXAMPLES"]
    return {
        "recalibration_candidates": recalibration,
        "monitor_count": len(monitor),
        "recalibration_count": len(recalibration),
    }


def _model_audit_block(reports_dir: Path, mode: str) -> dict | None:
    mode_slug = _mode_slug(mode)
    rows = _read_first_csv(
        [
            reports_dir / "latest_model_audit.csv",
            reports_dir / f"latest_model_audit_{mode_slug}.csv",
            reports_dir / "latest_full_audit.csv",
            reports_dir / "latest_full_audit_summary.csv",
            reports_dir / f"latest_full_audit_summary_{mode_slug}.csv",
        ]
    )
    if not rows:
        return None
    statuses = [str(row.get("status") or row.get("statut") or row.get("audit_status") or "").upper() for row in rows]
    if any(status in {"FAIL", "CRITICAL"} for status in statuses):
        audit_status = "FAIL"
    elif any(status == "WARN" or "WATCH" in status or "REVIEW" in status for status in statuses):
        audit_status = "WARN"
    else:
        audit_status = "PASS"
    flagged = [
        row
        for row, status in zip(rows, statuses)
        if status in {"FAIL", "CRITICAL", "WARN"} or "WATCH" in status or "REVIEW" in status
    ]
    first_with_weakest = next((row for row in rows if row.get("weakest_core_ticker") or row.get("weakest_core_status")), {})
    first_with_overfit = next((row for row in rows if row.get("anti_overfitting_status")), {})
    return {
        "audit_status": audit_status,
        "audit_flags": [_audit_message(row) for row in flagged[:5]],
        "weakest_core_ticker": first_with_weakest.get("weakest_core_ticker") or None,
        "weakest_core_status": first_with_weakest.get("weakest_core_status") or None,
        "anti_overfitting_status": first_with_overfit.get("anti_overfitting_status") or None,
    }


def _run_log_summary_block(run_log_rows: list[dict]) -> dict:
    warnings = []
    errors = []
    components = set()
    for row in run_log_rows or []:
        level = str(row.get("niveau") or row.get("level") or "").upper()
        if level == "WARN":
            warnings.append(row)
            component = row.get("composant") or row.get("component")
            if component:
                components.add(str(component))
        elif level == "ERROR":
            errors.append(row)
    return {
        "warn_count": len(warnings),
        "error_count": len(errors),
        "warn_components": sorted(components),
    }


def _build_delta_analysis(runs_history: list[dict]) -> dict:
    if len(runs_history) < 2:
        return {"status": "INSUFFICIENT_HISTORY"}
    latest = runs_history[0]
    previous = runs_history[1]
    latest_tickers = _allocated_tickers(latest)
    previous_tickers = _allocated_tickers(previous)
    added = sorted(latest_tickers - previous_tickers)
    removed = sorted(previous_tickers - latest_tickers)
    allocation_churn = {
        "status": "STABLE" if not added and not removed else "CHANGED",
        "details": "Allocation identique sur 2 runs consécutifs." if not added and not removed else f"Ajoutés: {added or []}; retirés: {removed or []}.",
        "added": added,
        "removed": removed,
    }
    latest_anomalies = int(_nested_number(latest, ["anomalies", "anomaly_count"], 0) or 0)
    previous_anomalies = int(_nested_number(previous, ["anomalies", "anomaly_count"], 0) or 0)
    latest_quality = _nested_number(latest, ["allocation", "decision_quality_score"], None)
    previous_quality = _nested_number(previous, ["allocation", "decision_quality_score"], None)
    latest_usable = _nested_number(latest, ["walk_forward", "periods_usable"], None)
    previous_usable = _nested_number(previous, ["walk_forward", "periods_usable"], None)
    latest_calibration = set(_nested_list(latest, ["proxy_calibration", "recalibration_candidates"]))
    older_calibration = set()
    for run in runs_history[1:]:
        older_calibration.update(_nested_list(run, ["proxy_calibration", "recalibration_candidates"]))
    latest_degraded = int(_nested_number(latest, ["source_health", "sources_degraded"], 0) or 0)
    previous_degraded = int(_nested_number(previous, ["source_health", "sources_degraded"], 0) or 0)
    return {
        "status": "OK",
        "runs_compared": len(runs_history),
        "allocation_churn": allocation_churn,
        "anomaly_trend": {
            "direction": _problem_direction(latest_anomalies, previous_anomalies),
            "latest_count": latest_anomalies,
            "previous_count": previous_anomalies,
        },
        "decision_quality_trend": {
            "direction": _score_direction(latest_quality, previous_quality),
            "latest_score": latest_quality,
            "previous_score": previous_quality,
        },
        "walk_forward_trend": {
            "direction": _positive_direction(latest_usable, previous_usable),
            "latest_usable": latest_usable,
            "previous_usable": previous_usable,
        },
        "calibration_trend": {
            "recalibration_candidates_stable": sorted(latest_calibration & older_calibration),
            "recalibration_candidates_new": sorted(latest_calibration - older_calibration),
            "recalibration_candidates_resolved": sorted(older_calibration - latest_calibration),
        },
        "source_health_trend": {
            "direction": _problem_direction(latest_degraded, previous_degraded),
            "latest_degraded": latest_degraded,
            "previous_degraded": previous_degraded,
        },
    }


def _load_previous_run_snapshots(history_dir: Path, mode_slug: str, current_run_date: str) -> list[dict]:
    rows = []
    seen_dates = set()
    for path in sorted(history_dir.glob(f"audit_{mode_slug}_*.json"), key=lambda item: item.name, reverse=True):
        payload = _safe_load_json(path)
        snapshot = _snapshot_only(payload)
        meta = snapshot.get("meta") or {}
        run_date = str(meta.get("run_date") or "")
        if not run_date or run_date == current_run_date or run_date in seen_dates:
            continue
        seen_dates.add(run_date)
        rows.append(snapshot)
    return sorted(rows, key=lambda row: str(row.get("meta", {}).get("created_at") or ""), reverse=True)


def _snapshot_only(payload: dict) -> dict:
    return {key: payload.get(key) for key in SNAPSHOT_BLOCK_KEYS if key in payload}


def _safe_read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        return read_csv_records(path)
    except Exception:
        return []


def _read_first_csv(paths: list[Path]) -> list[dict[str, Any]]:
    for path in paths:
        rows = _safe_read_csv(path)
        if rows:
            return rows
    return []


def _safe_load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _mode_slug(mode: str | None) -> str:
    clean = str(mode or "unknown").strip().lower().replace(" ", "-")
    return clean or "unknown"


def _timestamp_for_filename(created_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(created_at)
    except ValueError:
        parsed = datetime.now()
    return parsed.strftime("%Y%m%d_%H%M%S")


def _number(value: Any, default: Any = 0.0) -> Any:
    number = safe_float(value)
    return default if number is None else round(number, 6)


def _allocation_total(allocation_result: dict) -> float:
    return round(sum(_number(row.get("amount", row.get("montant")), 0.0) or 0.0 for row in allocation_result.get("allocations", []) or []), 6)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "oui"}


def _audit_message(row: dict[str, Any]) -> str:
    for key in ("message", "interpretation", "impact", "reason", "metric", "section"):
        value = str(row.get(key) or "").strip()
        if value:
            return value
    return str(row)


def _allocated_tickers(run: dict) -> set[str]:
    return {
        str(row.get("ticker") or "")
        for row in (run.get("allocation") or {}).get("allocation", [])
        if str(row.get("ticker") or "") and (_number(row.get("amount"), 0.0) or 0.0) > 0
    }


def _nested_number(row: dict, keys: list[str], default: Any) -> Any:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return _number(value, default)


def _nested_list(row: dict, keys: list[str]) -> list[str]:
    value: Any = row
    for key in keys:
        if not isinstance(value, dict):
            return []
        value = value.get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


def _problem_direction(latest: int | float | None, previous: int | float | None) -> str:
    if latest is None or previous is None:
        return "UNKNOWN"
    if latest < previous:
        return "IMPROVING"
    if latest > previous:
        return "WORSENING"
    return "STABLE"


def _positive_direction(latest: int | float | None, previous: int | float | None) -> str:
    if latest is None or previous is None:
        return "UNKNOWN"
    if latest > previous:
        return "IMPROVING"
    if latest < previous:
        return "WORSENING"
    return "STABLE"


def _score_direction(latest: float | None, previous: float | None) -> str:
    if latest is None or previous is None:
        return "UNKNOWN"
    difference = latest - previous
    if difference > 1.0:
        return "IMPROVING"
    if difference < -1.0:
        return "WORSENING"
    return "STABLE"
