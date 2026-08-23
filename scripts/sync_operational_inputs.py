#!/usr/bin/env python3
"""Synchroniser les intrants humains depuis un dossier partagé, de façon atomique."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Mapping, NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = Path.home() / ".config" / "investment_automation" / "input_sync.env"
DEFAULT_BACKUP_ROOT = Path.home() / ".local" / "state" / "investment_automation" / "input_backups"
SOURCE_ENV_NAME = "INVESTMENT_AUTOMATION_INPUT_SOURCE"
REQUIRED_CSV_PATHS = (
    Path("data/portfolio.csv"),
    Path("data/proxy_calibration.csv"),
)
REPORT_DIRECTORY = Path("data/research_reports/bncd_morningstar")


class InputSyncError(RuntimeError):
    """Erreur contrôlée de synchronisation des intrants."""


class SyncResult(NamedTuple):
    copied: tuple[Path, ...]
    unchanged: tuple[Path, ...]
    backup_directory: Path | None
    proxy_calibration_changed: bool


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def configured_source(
    *,
    explicit_source: Path | None,
    config_path: Path,
    environ: Mapping[str, str] = os.environ,
) -> Path | None:
    if explicit_source is not None:
        return explicit_source.expanduser()
    environment_value = str(environ.get(SOURCE_ENV_NAME) or "").strip()
    if environment_value:
        return Path(environment_value).expanduser()
    config_value = _read_env_file(config_path).get(SOURCE_ENV_NAME, "").strip()
    return Path(config_value).expanduser() if config_value else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_regular_file(path: Path, *, pdf: bool = False) -> None:
    if path.is_symlink():
        raise InputSyncError(f"lien symbolique refusé: {path}")
    if not path.is_file():
        raise InputSyncError(f"fichier source requis absent: {path}")
    if pdf:
        with path.open("rb") as handle:
            if handle.read(5) != b"%PDF-":
                raise InputSyncError(f"fichier .pdf invalide: {path}")


def _source_files(source_root: Path, *, skip_portfolio: bool = False) -> list[tuple[Path, Path]]:
    if not source_root.is_dir():
        raise InputSyncError(f"dossier source introuvable: {source_root}")

    files: list[tuple[Path, Path]] = []
    for relative_path in REQUIRED_CSV_PATHS:
        if skip_portfolio and relative_path == Path("data/portfolio.csv"):
            continue
        source = source_root / relative_path
        _validate_regular_file(source)
        files.append((source, relative_path))

    report_source = source_root / REPORT_DIRECTORY
    if report_source.is_symlink():
        raise InputSyncError(f"lien symbolique refusé: {report_source}")
    if not report_source.is_dir():
        raise InputSyncError(f"dossier de rapports absent: {report_source}")
    for source in sorted(report_source.iterdir(), key=lambda item: item.name.casefold()):
        if source.suffix.lower() != ".pdf":
            continue
        _validate_regular_file(source, pdf=True)
        files.append((source, REPORT_DIRECTORY / source.name))
    return files


def _atomic_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
        shutil.copystat(source, temporary_path)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def sync_inputs(
    *,
    source_root: Path,
    project_root: Path,
    backup_root: Path,
    dry_run: bool = False,
    skip_portfolio: bool = False,
    now: datetime | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[object]] = subprocess.run,
) -> SyncResult:
    pairs = _source_files(source_root, skip_portfolio=skip_portfolio)
    changed: list[tuple[Path, Path, Path]] = []
    unchanged: list[Path] = []
    for source, relative_path in pairs:
        destination = project_root / relative_path
        if destination.is_symlink():
            raise InputSyncError(f"destination symbolique refusée: {destination}")
        if destination.is_file() and _sha256(source) == _sha256(destination):
            unchanged.append(relative_path)
        else:
            changed.append((source, destination, relative_path))

    backup_directory: Path | None = None
    overwritten = any(destination.exists() for _, destination, _ in changed)
    if changed and not dry_run:
        stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S_%f")
        if overwritten:
            backup_directory = backup_root / stamp
        for _, destination, relative_path in changed:
            if destination.exists():
                assert backup_directory is not None
                backup_destination = backup_directory / relative_path
                backup_destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup_destination)
        for source, destination, _ in changed:
            _atomic_copy(source, destination)

    relative_changed = tuple(item[2] for item in changed)
    proxy_changed = Path("data/proxy_calibration.csv") in relative_changed
    if proxy_changed and not dry_run:
        python = project_root / ".venv" / "bin" / "python"
        if not python.is_file():
            raise InputSyncError(f"environnement Python introuvable: {python}")
        result = command_runner(
            [str(python), "main.py", "sync-manual-inputs"],
            cwd=project_root,
            check=False,
        )
        if int(result.returncode) != 0:
            raise InputSyncError(
                f"sync-manual-inputs a échoué avec le statut {result.returncode}; sauvegarde: {backup_directory}"
            )

    return SyncResult(
        copied=relative_changed,
        unchanged=tuple(unchanged),
        backup_directory=backup_directory,
        proxy_calibration_changed=proxy_changed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Synchroniser les intrants Investment Automation")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--backup-root", type=Path, default=DEFAULT_BACKUP_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--skip-portfolio",
        action="store_true",
        help="Synchronise les autres intrants sans lire ni copier data/portfolio.csv.",
    )
    args = parser.parse_args(argv)

    source = configured_source(explicit_source=args.source, config_path=args.config)
    if source is None:
        print(f"Synchronisation des intrants désactivée: aucune source configurée dans {args.config}.")
        return 0

    try:
        result = sync_inputs(
            source_root=source.resolve(),
            project_root=args.project_root.resolve(),
            backup_root=args.backup_root.expanduser().resolve(),
            dry_run=args.dry_run,
            skip_portfolio=args.skip_portfolio,
        )
    except (InputSyncError, OSError) as exc:
        print(f"ÉCHEC synchronisation des intrants: {exc}", file=sys.stderr)
        return 1

    action = "À copier" if args.dry_run else "Copiés"
    print(f"Source des intrants: {source}")
    print(f"{action}: {len(result.copied)} | Inchangés: {len(result.unchanged)}")
    for relative_path in result.copied:
        print(f"- {relative_path}")
    if result.backup_directory is not None:
        print(f"Sauvegarde avant écrasement: {result.backup_directory}")
    if result.proxy_calibration_changed and not args.dry_run:
        print("Calibration modifiée: sync-manual-inputs exécuté.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
