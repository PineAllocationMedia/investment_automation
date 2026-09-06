from __future__ import annotations

from .runtime_context import state_root

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .utils import PROJECT_ROOT


BACKUP_PREFIX = "investment_automation_backup_"

EXCLUDED_NAMES = {
    ".DS_Store",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "backups",
}

EXCLUDED_RELATIVE_PATHS = {
    "data/cached_market_data",
}


def create_project_backup(
    project_root: str | Path = PROJECT_ROOT,
    backups_dir: str | Path | None = None,
    *,
    include_cache: bool = False,
) -> dict[str, Any]:
    project_root = state_root(project_root).resolve()
    backups_dir = Path(backups_dir).resolve() if backups_dir else project_root / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destination = _unique_backup_path(backups_dir / f"{BACKUP_PREFIX}{created_at}")
    shutil.copytree(
        project_root,
        destination,
        ignore=_ignore_factory(project_root, include_cache=include_cache),
        copy_function=shutil.copy2,
    )

    file_count, total_bytes = _directory_stats(destination)
    manifest = {
        "created_at": created_at,
        "source_project": str(project_root),
        "backup_path": str(destination),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "total_size": format_bytes(total_bytes),
        "include_cache": include_cache,
        "excluded_names": sorted(EXCLUDED_NAMES),
        "excluded_relative_paths": [] if include_cache else sorted(EXCLUDED_RELATIVE_PATHS),
        "restore_note": "Restauration automatique non activee: copier manuellement cette sauvegarde si necessaire.",
    }
    (destination / "_backup_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    file_count, total_bytes = _directory_stats(destination)
    manifest["file_count"] = file_count
    manifest["total_bytes"] = total_bytes
    manifest["total_size"] = format_bytes(total_bytes)
    (destination / "_backup_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def list_project_backups(backups_dir: str | Path | None = None) -> list[dict[str, Any]]:
    backups_dir = Path(backups_dir).resolve() if backups_dir else state_root(PROJECT_ROOT) / "backups"
    if not backups_dir.exists():
        return []

    rows = []
    for path in backups_dir.iterdir():
        if not path.is_dir() or not path.name.startswith(BACKUP_PREFIX):
            continue
        manifest = _load_manifest(path)
        file_count, total_bytes = _directory_stats(path)
        rows.append(
            {
                "name": path.name,
                "path": str(path),
                "created_at": manifest.get("created_at") or path.name.replace(BACKUP_PREFIX, ""),
                "file_count": manifest.get("file_count") or file_count,
                "total_bytes": manifest.get("total_bytes") or total_bytes,
                "total_size": manifest.get("total_size") or format_bytes(total_bytes),
                "source_project": manifest.get("source_project", ""),
            }
        )
    return sorted(rows, key=lambda row: (str(row.get("created_at", "")), str(row.get("name", ""))), reverse=True)


def format_bytes(value: int | float | None) -> str:
    size = float(value or 0)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def _unique_backup_path(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = Path(f"{path}_{counter}")
        if not candidate.exists():
            return candidate
        counter += 1


def _ignore_factory(project_root: Path, *, include_cache: bool) -> Callable[[str, list[str]], set[str]]:
    def ignore(current_dir: str, names: list[str]) -> set[str]:
        current_path = Path(current_dir).resolve()
        ignored = {name for name in names if name in EXCLUDED_NAMES}
        if not include_cache:
            for name in names:
                candidate = current_path / name
                relative = _relative_key(candidate, project_root)
                if relative in EXCLUDED_RELATIVE_PATHS:
                    ignored.add(name)
        return ignored

    return ignore


def _relative_key(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root).as_posix()
    except ValueError:
        return path.name


def _directory_stats(path: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            total_bytes += item.stat().st_size
            file_count += 1
        except OSError:
            continue
    return file_count, total_bytes


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest_path = path / "_backup_manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}
