from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_csv_records, write_csv_records, write_text


MODE_SLUGS = {
    "balanced": "balanced",
    "family-office": "family_office",
    "rational-aggressive": "rational_aggressive",
    "high-cagr": "high_cagr",
}


def mode_slug(mode: str | None) -> str:
    normalized = str(mode or "").strip()
    return MODE_SLUGS.get(normalized, normalized.replace("-", "_"))


def mode_artifact_path(path: str | Path, mode: str | None) -> Path:
    path = Path(path)
    slug = mode_slug(mode)
    if not slug:
        return path
    return path.with_name(f"{path.stem}_{slug}{path.suffix}")


def mode_artifact_exists(reports_dir: str | Path, filename: str, mode: str | None) -> bool:
    return mode_artifact_path(Path(reports_dir) / filename, mode).exists()


def require_mode_artifact(
    reports_dir: str | Path,
    filename: str,
    mode: str,
    *,
    command_hint: str = "analyze",
) -> Path:
    path = mode_artifact_path(Path(reports_dir) / filename, mode)
    if not path.exists():
        raise RuntimeError(
            f"Missing mode-specific {Path(filename).stem.replace('latest_', '').replace('_', ' ')} "
            f"for {mode}. Run `python3 main.py {command_hint} --mode {mode}` first."
        )
    return path


def read_mode_csv_if_exists(reports_dir: str | Path, filename: str, mode: str | None) -> list[dict[str, Any]]:
    path = mode_artifact_path(Path(reports_dir) / filename, mode)
    if not path.exists():
        return []
    return read_csv_records(path)


def write_csv_records_mode_pair(
    reports_dir: str | Path,
    filename: str,
    mode: str | None,
    rows: list[dict[str, Any]],
    columns: list[str],
) -> None:
    base = Path(reports_dir) / filename
    write_csv_records(base, rows, columns)
    write_csv_records(mode_artifact_path(base, mode), rows, columns)


def write_text_mode_pair(reports_dir: str | Path, filename: str, mode: str | None, content: str) -> None:
    base = Path(reports_dir) / filename
    write_text(base, content)
    write_text(mode_artifact_path(base, mode), content)
