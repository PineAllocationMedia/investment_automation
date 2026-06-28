from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .market_scanner import MARKET_UNIVERSE_COLUMNS
from .portfolio_loader import ACCOUNT_LOCATION_COLUMNS, PORTFOLIO_COLUMNS
from .portfolio_transactions import PORTFOLIO_TRANSACTION_COLUMNS
from .proxy_calibration import PROXY_CALIBRATION_COLUMNS, PROXY_CALIBRATION_HISTORY_COLUMNS
from .proxy_correction_engine import PROXY_CORRECTION_HISTORY_COLUMNS
from .research_reports import RESEARCH_INDEX_COLUMNS
from .utils import read_csv_records, write_csv_records
from .watchlist_engine import WATCHLIST_COLUMNS

try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover - exercised when dependency is absent locally.
    BaseModel = None  # type: ignore


SCHEMA_REPAIR_COLUMNS = [
    "file",
    "status",
    "severity",
    "details",
    "backup_path",
    "action_taken",
]


@dataclass(frozen=True)
class CSVSchemaSpec:
    path: Path
    columns: list[str]
    optional: bool = False
    allow_extra_columns: bool = True


if BaseModel is not None:

    class _FlexibleRow(BaseModel):
        class Config:
            extra = "allow"

    class PortfolioSchema(_FlexibleRow):
        ticker: str | None = ""
        shares: str | None = ""
        average_cost: str | None = ""
        average_cost_currency: str | None = ""
        account_type: str | None = ""

    class MarketUniverseSchema(_FlexibleRow):
        ticker: str | None = ""
        company_name: str | None = ""

    class WatchlistSchema(_FlexibleRow):
        ticker: str | None = ""
        notes: str | None = ""
        manual_priority: str | None = ""

    class ResearchIndexSchema(_FlexibleRow):
        ticker: str | None = ""
        provider: str | None = ""
        report_date: str | None = ""
        file_name: str | None = ""
        notes: str | None = ""

else:
    PortfolioSchema = MarketUniverseSchema = WatchlistSchema = ResearchIndexSchema = None  # type: ignore


def csv_schema_specs(project_root: str | Path) -> list[CSVSchemaSpec]:
    root = Path(project_root)
    data_dir = root / "data"
    research_dir = data_dir / "research_reports"
    specs = [
        CSVSchemaSpec(data_dir / "portfolio.csv", PORTFOLIO_COLUMNS),
        CSVSchemaSpec(data_dir / "portfolio_transactions.csv", PORTFOLIO_TRANSACTION_COLUMNS, optional=True),
        CSVSchemaSpec(data_dir / "watchlist.csv", WATCHLIST_COLUMNS, optional=True),
        CSVSchemaSpec(data_dir / "market_universe.csv", MARKET_UNIVERSE_COLUMNS, optional=True),
        CSVSchemaSpec(research_dir / "research_index.csv", RESEARCH_INDEX_COLUMNS, optional=True),
        CSVSchemaSpec(data_dir / "proxy_calibration.csv", PROXY_CALIBRATION_COLUMNS, optional=True),
        CSVSchemaSpec(data_dir / "proxy_calibration_history.csv", PROXY_CALIBRATION_HISTORY_COLUMNS, optional=True),
        CSVSchemaSpec(data_dir / "proxy_correction_history.csv", PROXY_CORRECTION_HISTORY_COLUMNS, optional=True),
    ]
    if (data_dir / "account_locations.csv").exists():
        specs.append(CSVSchemaSpec(data_dir / "account_locations.csv", ACCOUNT_LOCATION_COLUMNS, optional=True))
    return specs


def validate_csv_schemas(project_root: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in csv_schema_specs(project_root):
        rows.append(_validate_schema(spec))
    return rows


def repair_safe_csv_schemas(project_root: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for spec in csv_schema_specs(project_root):
        rows.append(_repair_schema(spec))
    return rows


def _validate_schema(spec: CSVSchemaSpec) -> dict[str, Any]:
    if not spec.path.exists():
        return _row(spec.path, "WARN" if spec.optional else "FAIL", "MEDIUM", "Fichier absent.", "", "Aucune réparation appliquée.")
    header = _read_header(spec.path)
    missing = [column for column in spec.columns if column not in header]
    blank_rows = _blank_row_count(spec.path)
    model_warning = _pydantic_validate_sample(spec)
    if missing or blank_rows or model_warning:
        details = []
        if missing:
            details.append("Colonnes manquantes: " + ", ".join(missing))
        if blank_rows:
            details.append(f"{blank_rows} ligne(s) vide(s)")
        if model_warning:
            details.append(model_warning)
        return _row(spec.path, "WARN", "LOW", "; ".join(details), "", "Utiliser health-check --repair-safe.")
    return _row(spec.path, "PASS", "LOW", "Schéma CSV OK.", "", "Aucune action.")


def _repair_schema(spec: CSVSchemaSpec) -> dict[str, Any]:
    if not spec.path.exists():
        spec.path.parent.mkdir(parents=True, exist_ok=True)
        write_csv_records(spec.path, [], spec.columns)
        return _row(spec.path, "REPAIRED", "LOW", "Fichier absent recréé avec en-têtes.", "", "Fichier créé.")

    header = _read_header(spec.path)
    missing = [column for column in spec.columns if column not in header]
    rows, blank_count, unsafe_extra_count = _read_repairable_rows(spec.path)
    if unsafe_extra_count:
        return _row(
            spec.path,
            "SKIPPED",
            "MEDIUM",
            f"{unsafe_extra_count} ligne(s) ont trop de cellules non vides; réparation automatique ignorée.",
            "",
            "Corriger manuellement pour éviter une perte de données.",
        )
    if not missing and blank_count == 0:
        return _row(spec.path, "PASS", "LOW", "Aucune réparation nécessaire.", "", "Aucune action.")

    backup_path = _backup_file(spec.path)
    output_columns = _output_columns(spec, header)
    write_csv_records(spec.path, rows, output_columns)
    details = []
    if missing:
        details.append("Colonnes ajoutées: " + ", ".join(missing))
    if blank_count:
        details.append(f"{blank_count} ligne(s) vide(s) retirée(s)")
    return _row(spec.path, "REPAIRED", "LOW", "; ".join(details), str(backup_path), "Réparation safe appliquée.")


def _read_header(path: Path) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            return [str(value or "").strip() for value in next(reader, [])]
    except OSError:
        return []


def _read_repairable_rows(path: Path) -> tuple[list[dict[str, Any]], int, int]:
    repaired: list[dict[str, Any]] = []
    blank_count = 0
    unsafe_extra_count = 0
    for row in read_csv_records(path):
        extras = row.pop(None, None)  # type: ignore[arg-type]
        if extras and any(str(value or "").strip() for value in extras):
            unsafe_extra_count += 1
        if not any(str(value or "").strip() for value in row.values()):
            blank_count += 1
            continue
        repaired.append(row)
    return repaired, blank_count, unsafe_extra_count


def _blank_row_count(path: Path) -> int:
    return sum(1 for row in read_csv_records(path) if not any(str(value or "").strip() for value in row.values()))


def _output_columns(spec: CSVSchemaSpec, existing_header: list[str]) -> list[str]:
    extras = [column for column in existing_header if column and column not in spec.columns]
    return spec.columns + (extras if spec.allow_extra_columns else [])


def _backup_file(path: Path) -> Path:
    backup_dir = _data_root_for(path) / "repair_backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / path.name
    shutil.copy2(path, backup_path)
    return backup_path


def _data_root_for(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if parent.name == "data":
            return parent
    return path.parent


def _pydantic_validate_sample(spec: CSVSchemaSpec) -> str:
    if BaseModel is None:
        return ""
    model = _model_for_spec(spec)
    if model is None:
        return ""
    try:
        for row in read_csv_records(spec.path)[:25]:
            model(**{key: value for key, value in row.items() if key is not None})
    except Exception as exc:
        return f"Pydantic signale une ligne possiblement invalide: {exc}"
    return ""


def _model_for_spec(spec: CSVSchemaSpec) -> Any:
    name = spec.path.name
    if name == "portfolio.csv":
        return PortfolioSchema
    if name == "market_universe.csv":
        return MarketUniverseSchema
    if name == "watchlist.csv":
        return WatchlistSchema
    if name == "research_index.csv":
        return ResearchIndexSchema
    return None


def _row(path: Path, status: str, severity: str, details: str, backup_path: str, action: str) -> dict[str, str]:
    return {
        "file": str(path),
        "status": status,
        "severity": severity,
        "details": details,
        "backup_path": backup_path,
        "action_taken": action,
    }
