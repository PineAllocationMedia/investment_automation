#!/usr/bin/env python3
"""Process one stable, previously unprocessed portfolio.csv source version."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, NamedTuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from src.portfolio_change_tracker import PORTFOLIO_CHANGE_COLUMNS, PORTFOLIO_STATE_COLUMNS  # noqa: E402
from src.validators import validate_portfolio_file  # noqa: E402
from sync_operational_inputs import DEFAULT_CONFIG_PATH, configured_source  # noqa: E402


DEFAULT_STATE_FILE = Path.home() / ".local" / "state" / "investment_automation" / "portfolio_sync_state.json"
DEFAULT_SETTLE_DELAY_SECONDS = 1.0
MARKER_SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class AutomaticPortfolioSyncError(RuntimeError):
    """Controlled failure that must not advance the processed marker."""


class ProcessResult(NamedTuple):
    processed: bool
    source_sha256: str
    source_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_source_file(source_root: Path) -> Path:
    resolved_root = source_root.expanduser().resolve()
    source = resolved_root / "data" / "portfolio.csv"
    if source.is_symlink():
        raise AutomaticPortfolioSyncError(f"source portfolio symbolique refusée: {source}")
    if not source.is_file():
        raise AutomaticPortfolioSyncError(f"source portfolio introuvable: {source}")
    return source.resolve()


def _parse_utc_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AutomaticPortfolioSyncError("marqueur invalide: processed_at doit être une date UTC ISO")
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError as exc:
        raise AutomaticPortfolioSyncError("marqueur invalide: processed_at doit être une date UTC ISO") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise AutomaticPortfolioSyncError("marqueur invalide: processed_at doit être en UTC")
    return text


def _load_marker(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        raise AutomaticPortfolioSyncError(f"marqueur symbolique refusé: {path}")
    if not path.exists():
        return None
    if not path.is_file():
        raise AutomaticPortfolioSyncError(f"marqueur invalide: fichier régulier attendu: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AutomaticPortfolioSyncError(f"marqueur illisible ou JSON invalide: {path}") from exc
    if not isinstance(payload, dict):
        raise AutomaticPortfolioSyncError("marqueur invalide: objet JSON attendu")
    version = payload.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int) or version != MARKER_SCHEMA_VERSION:
        raise AutomaticPortfolioSyncError(f"marqueur invalide: schema_version attendu={MARKER_SCHEMA_VERSION}")
    source_hash = payload.get("processed_source_sha256")
    if not isinstance(source_hash, str) or SHA256_PATTERN.fullmatch(source_hash) is None:
        raise AutomaticPortfolioSyncError("marqueur invalide: processed_source_sha256")
    _parse_utc_timestamp(payload.get("processed_at"))
    source_path = payload.get("source_path")
    if not isinstance(source_path, str) or not source_path or not Path(source_path).is_absolute():
        raise AutomaticPortfolioSyncError("marqueur invalide: source_path absolu requis")
    return payload


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_marker(path: Path, payload: dict[str, Any]) -> None:
    path = path.expanduser()
    if path.is_symlink():
        raise AutomaticPortfolioSyncError(f"marqueur symbolique refusé: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
        try:
            _fsync_directory(path.parent)
        except OSError as exc:
            raise AutomaticPortfolioSyncError(
                f"marqueur remplacé, mais confirmation de durabilité du dossier impossible: {path.parent}"
            ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def _strict_csv_rows(path: Path, required_columns: list[str] | None = None) -> tuple[list[str], int]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            if header is None or not header or not any(str(value).strip() for value in header):
                raise AutomaticPortfolioSyncError(f"CSV sans en-tête: {path}")
            actual_header = [str(value) for value in header]
            normalized_header = [value.strip() for value in actual_header]
            if any("\x00" in value for value in normalized_header):
                raise AutomaticPortfolioSyncError(f"CSV avec caractère NUL dans l'en-tête: {path}")
            if any(not value for value in normalized_header):
                raise AutomaticPortfolioSyncError(f"CSV avec colonne sans nom: {path}")
            if len(set(normalized_header)) != len(normalized_header):
                raise AutomaticPortfolioSyncError(f"CSV avec colonnes dupliquées: {path}")
            if required_columns:
                missing = [column for column in required_columns if column not in actual_header]
                if missing:
                    raise AutomaticPortfolioSyncError(
                        f"CSV avec schéma incomplet ({', '.join(missing)}): {path}"
                    )
            row_count = 0
            for line_number, row in enumerate(reader, start=2):
                if any("\x00" in str(value) for value in row):
                    raise AutomaticPortfolioSyncError(f"CSV avec caractère NUL à la ligne {line_number}: {path}")
                if not any(str(value).strip() for value in row):
                    continue
                if len(row) != len(actual_header):
                    raise AutomaticPortfolioSyncError(
                        f"CSV avec largeur de ligne invalide à la ligne {line_number}: {path}"
                    )
                row_count += 1
            return actual_header, row_count
    except AutomaticPortfolioSyncError:
        raise
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise AutomaticPortfolioSyncError(f"CSV illisible ou malformé: {path}: {exc}") from exc


def _validate_staged_portfolio(path: Path) -> None:
    _strict_csv_rows(path)
    try:
        errors = validate_portfolio_file(path)
    except Exception as exc:
        raise AutomaticPortfolioSyncError(f"validation portfolio impossible: {exc}") from exc
    if errors:
        raise AutomaticPortfolioSyncError("portfolio invalide: " + " | ".join(errors))


def _validate_tracking_integrity(data_dir: Path) -> None:
    snapshot = data_dir / "portfolio_state_snapshot.csv"
    history = data_dir / "portfolio_change_history.csv"
    if snapshot.is_symlink() or history.is_symlink():
        raise AutomaticPortfolioSyncError("état de suivi incohérent: liens symboliques refusés")
    snapshot_exists = snapshot.exists()
    history_exists = history.exists()

    if not snapshot_exists and not history_exists:
        return
    if snapshot_exists != history_exists:
        raise AutomaticPortfolioSyncError(
            "état de suivi incohérent: snapshot et historique doivent être tous deux présents ou absents"
        )

    _, snapshot_count = _strict_csv_rows(snapshot, PORTFOLIO_STATE_COLUMNS)
    _, history_count = _strict_csv_rows(history, PORTFOLIO_CHANGE_COLUMNS)
    if snapshot_count > 0 and history_count == 0:
        raise AutomaticPortfolioSyncError(
            "état de suivi incohérent: snapshot avec positions mais historique sans enregistrements"
        )


def _preflight_command_environment(project_root: Path) -> Path:
    python = project_root / ".venv" / "bin" / "python"
    main_file = project_root / "main.py"
    if not python.is_file() or not os.access(python, os.X_OK):
        raise AutomaticPortfolioSyncError(f"interpréteur Python absent ou inutilisable: {python}")
    if not main_file.is_file():
        raise AutomaticPortfolioSyncError(f"commande principale absente: {main_file}")
    return python


def _stage_source(source: Path, destination_directory: Path) -> Path:
    destination_directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".portfolio.csv.stage.", suffix=".tmp", dir=destination_directory
    )
    staged = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_file:
            shutil.copyfileobj(input_file, output)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return staged


def process_portfolio_sync(
    *,
    explicit_source: Path | None,
    config_path: Path,
    project_root: Path,
    state_file: Path,
    settle_delay_seconds: float = DEFAULT_SETTLE_DELAY_SECONDS,
    environ: Mapping[str, str] = os.environ,
    sleeper: Callable[[float], None] = time.sleep,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    marker_writer: Callable[[Path, dict[str, Any]], None] = _write_marker,
    now_utc: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> ProcessResult:
    marker_path = state_file.expanduser()
    marker = _load_marker(marker_path)
    source_root = configured_source(explicit_source=explicit_source, config_path=config_path, environ=environ)
    if source_root is None:
        raise AutomaticPortfolioSyncError("source portfolio non configurée")
    source = _canonical_source_file(source_root)
    source_hash = _sha256(source)
    canonical_source_text = str(source)

    project_root = project_root.expanduser().resolve()
    data_dir = project_root / "data"
    destination = data_dir / "portfolio.csv"
    if destination.is_symlink():
        raise AutomaticPortfolioSyncError(f"destination portfolio symbolique refusée: {destination}")

    if marker is not None and (
        source_hash == marker["processed_source_sha256"] and canonical_source_text == marker["source_path"]
    ):
        if destination.is_file() and _sha256(destination) == marker["processed_source_sha256"]:
            return ProcessResult(False, source_hash, source)

    python = _preflight_command_environment(project_root)

    if settle_delay_seconds < 0:
        raise AutomaticPortfolioSyncError("le délai de stabilisation ne peut pas être négatif")
    if settle_delay_seconds:
        sleeper(settle_delay_seconds)

    staged: Path | None = None
    try:
        staged = _stage_source(source, data_dir)
        staged_hash = _sha256(staged)
        final_source_hash = _sha256(source)
        if not (source_hash == staged_hash == final_source_hash):
            raise AutomaticPortfolioSyncError("source portfolio modifiée pendant la mise en scène")

        _validate_staged_portfolio(staged)
        _validate_tracking_integrity(data_dir)

        os.replace(staged, destination)
        staged = None
        _fsync_directory(data_dir)

        result = command_runner(
            [str(python), "main.py", "sync-portfolio"],
            cwd=project_root,
            check=False,
        )
        if int(result.returncode) != 0:
            raise AutomaticPortfolioSyncError(f"sync-portfolio a échoué avec le statut {result.returncode}")

        timestamp = now_utc().astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        marker_writer(
            marker_path,
            {
                "schema_version": MARKER_SCHEMA_VERSION,
                "processed_source_sha256": staged_hash,
                "processed_at": timestamp,
                "source_path": canonical_source_text,
            },
        )
        return ProcessResult(True, staged_hash, source)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Réconcilier manuellement une nouvelle version source de portfolio.csv")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_FILE)
    parser.add_argument("--settle-delay", type=float, default=DEFAULT_SETTLE_DELAY_SECONDS)
    args = parser.parse_args(argv)

    try:
        result = process_portfolio_sync(
            explicit_source=args.source,
            config_path=args.config,
            project_root=args.project_root,
            state_file=args.state_file,
            settle_delay_seconds=args.settle_delay,
        )
    except (AutomaticPortfolioSyncError, OSError) as exc:
        print(f"ÉCHEC synchronisation automatique du portefeuille: {exc}", file=sys.stderr)
        return 1

    if result.processed:
        print(f"Portfolio source traité avec succès: {result.source_path}")
        print(f"SHA-256 traité: {result.source_sha256}")
    else:
        print(f"Aucune nouvelle version source à traiter: {result.source_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
