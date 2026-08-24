from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable


DEFAULT_PROJECT_WARN_BYTES = 2 * 1024**3
DEFAULT_CACHE_WARN_BYTES = 1024**3
DEFAULT_RESEARCH_WARN_BYTES = 1024**3
DEFAULT_RAW_LOG_WARN_BYTES = 512 * 1024**2
DEFAULT_STRUCTURED_HISTORY_WARN_BYTES = 1024**3
DEFAULT_FREE_WARN_BYTES = 2 * 1024**3
DEFAULT_FREE_CRITICAL_BYTES = 1024**3
DEFAULT_FREE_WARN_PERCENT = 10.0
DEFAULT_FREE_CRITICAL_PERCENT = 5.0
PRODUCTION_RAW_LOG_TARGET = 100


def build_storage_health_rows(
    project_root: str | Path,
    *,
    raw_log_dir: str | Path | None = None,
    disk_usage_provider: Callable[[str | Path], Any] = shutil.disk_usage,
    thresholds: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    root = Path(project_root)
    raw_logs = Path(raw_log_dir) if raw_log_dir is not None else Path(
        os.environ.get("INVESTMENT_AUTOMATION_LOG_DIR") or Path.home() / "investment_automation_run_logs"
    )
    threshold = {
        "project": DEFAULT_PROJECT_WARN_BYTES,
        "cache": DEFAULT_CACHE_WARN_BYTES,
        "research": DEFAULT_RESEARCH_WARN_BYTES,
        "raw_logs": DEFAULT_RAW_LOG_WARN_BYTES,
        "structured_history": DEFAULT_STRUCTURED_HISTORY_WARN_BYTES,
        "free_warn": DEFAULT_FREE_WARN_BYTES,
        "free_critical": DEFAULT_FREE_CRITICAL_BYTES,
        "free_warn_percent": DEFAULT_FREE_WARN_PERCENT,
        "free_critical_percent": DEFAULT_FREE_CRITICAL_PERCENT,
        **(thresholds or {}),
    }

    cache_dir = root / "data" / "cached_market_data"
    research_dir = root / "data" / "research_reports"
    structured_paths = [
        root / "data" / "run_log_history.csv",
        root / "data" / "account_performance_history.csv",
        root / "data" / "anomaly_history.csv",
        root / "data" / "portfolio_change_history.csv",
        root / "data" / "portfolio_inferred_transactions.csv",
        root / "data" / "proxy_calibration_history.csv",
        root / "data" / "source_health_history.csv",
        root / "data" / "ticker_memory.csv",
        root / "reports" / "history",
        root / "reports" / "universe_snapshots",
        root / "reports" / "decision_manifests",
        root / "reports" / "failed_run_audits",
    ]
    project_size, project_count = _tree_stats(root, excluded_names={".git", ".venv", "__pycache__"})
    cache_size, cache_count = _tree_stats(cache_dir)
    research_size, research_count = _tree_stats(research_dir)
    log_size, log_count = _tree_stats(raw_logs, glob_pattern="analysis_*.log")
    structured_size, structured_count = _paths_stats(structured_paths)

    rows = [
        _size_row("storage:project", project_size, project_count, threshold["project"], "Relevant project usage"),
        _size_row("storage:cache", cache_size, cache_count, threshold["cache"], "Market/cache usage"),
        _size_row("storage:research", research_size, research_count, threshold["research"], "Research-report usage"),
        _size_row("storage:raw_logs", log_size, log_count, threshold["raw_logs"], "Production raw-log usage"),
        _size_row(
            "storage:structured_history",
            structured_size,
            structured_count,
            threshold["structured_history"],
            "Structured validation/history usage",
        ),
    ]
    rows.append(_raw_log_count_row(log_count))
    rows.append(_free_space_row(root, disk_usage_provider, threshold))
    return rows


def _tree_stats(
    path: Path,
    *,
    excluded_names: set[str] | None = None,
    glob_pattern: str | None = None,
) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    excluded_names = excluded_names or set()
    iterator = path.glob(glob_pattern) if glob_pattern else path.rglob("*")
    total = 0
    count = 0
    for item in iterator:
        if not item.is_file() or item.is_symlink() or any(part in excluded_names for part in item.parts):
            continue
        try:
            total += item.stat().st_size
            count += 1
        except OSError:
            continue
    return total, count


def _paths_stats(paths: list[Path]) -> tuple[int, int]:
    seen: set[Path] = set()
    total = 0
    count = 0
    for path in paths:
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            candidates = [item for item in path.rglob("*") if item.is_file()]
        else:
            candidates = []
        for item in candidates:
            resolved = item.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                total += item.stat().st_size
                count += 1
            except OSError:
                continue
    return total, count


def _size_row(check: str, size: int, count: int, warning_threshold: float, label: str) -> dict[str, Any]:
    warned = size >= warning_threshold
    return {
        "check": check,
        "status": "WARN" if warned else "PASS",
        "severity": "MEDIUM" if warned else "LOW",
        "details": f"{label}: {_human_bytes(size)} across {count} file(s); warning threshold {_human_bytes(int(warning_threshold))}.",
        "suggested_action": "Review conservative cache/log cleanup; preserve structured evidence." if warned else "No action.",
    }


def _raw_log_count_row(count: int) -> dict[str, Any]:
    status = "WARN" if count > PRODUCTION_RAW_LOG_TARGET + 20 else "PASS"
    return {
        "check": "storage:raw_log_count",
        "status": status,
        "severity": "LOW",
        "details": f"{count} production analysis raw log(s); bounded target is approximately {PRODUCTION_RAW_LOG_TARGET}.",
        "suggested_action": "Verify bounded retention." if status == "WARN" else "No action.",
    }


def _free_space_row(root: Path, provider: Callable[[str | Path], Any], threshold: dict[str, float]) -> dict[str, Any]:
    try:
        usage = provider(root)
        total = int(usage.total)
        free = int(usage.free)
    except Exception as exc:  # noqa: BLE001
        return {
            "check": "storage:free_space",
            "status": "WARN",
            "severity": "LOW",
            "details": f"Free disk space unavailable: {exc}",
            "suggested_action": "Check disk capacity manually.",
        }
    free_percent = (free / total * 100.0) if total > 0 else 0.0
    if free <= threshold["free_critical"] or free_percent <= threshold["free_critical_percent"]:
        status, severity = "WARN", "HIGH"
    elif free <= threshold["free_warn"] or free_percent <= threshold["free_warn_percent"]:
        status, severity = "WARN", "MEDIUM"
    else:
        status, severity = "PASS", "LOW"
    return {
        "check": "storage:free_space",
        "status": status,
        "severity": severity,
        "details": f"Free disk: {_human_bytes(free)} of {_human_bytes(total)} ({free_percent:.1f}%).",
        "suggested_action": "Review disk usage conservatively; do not delete structured Baseline evidence." if status == "WARN" else "No action.",
    }


def _human_bytes(value: int) -> str:
    amount = float(max(0, value))
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024.0 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024.0
    return f"{amount:.1f} TiB"
