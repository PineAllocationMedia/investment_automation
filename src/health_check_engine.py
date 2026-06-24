from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .cache_management_engine import cache_health_summary, run_cache_maintenance
from .csv_schema_engine import repair_safe_csv_schemas, validate_csv_schemas
from .research_reports import BNCD_MORNINGSTAR_DIR, RESEARCH_REPORTS_DIR, research_status_rows
from .utils import DATA_DIR
from .validators import validate_input_files


HEALTH_CHECK_COLUMNS = [
    "check",
    "status",
    "severity",
    "details",
    "suggested_action",
]


def run_health_check(
    project_root: str | Path,
    known_tickers: list[str] | None = None,
    repair_safe: bool = False,
    schema_rows: list[dict[str, Any]] | None = None,
    cache_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    project_root = Path(project_root)
    rows: list[dict[str, Any]] = []
    rows.extend(_dependency_rows())
    rows.extend(_file_rows(project_root))
    schema_rows = schema_rows if schema_rows is not None else (
        repair_safe_csv_schemas(project_root) if repair_safe else validate_csv_schemas(project_root)
    )
    rows.extend(_schema_rows(schema_rows, repair_safe=repair_safe))
    rows.extend(_validation_rows(project_root))
    rows.extend(_research_report_rows(known_tickers or []))
    cache_rows = cache_rows if cache_rows is not None else run_cache_maintenance(repair_safe=repair_safe)
    rows.extend(_cache_rows(cache_rows))
    return rows


def health_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    summary = {"PASS": 0, "WARN": 0, "FAIL": 0, "INFO": 0}
    for row in rows:
        status = str(row.get("status") or "INFO").upper()
        summary[status] = summary.get(status, 0) + 1
    return summary


def _dependency_rows() -> list[dict[str, Any]]:
    dependencies = [
        ("pandas", True),
        ("numpy", True),
        ("yfinance", True),
        ("yaml", True),
        ("pypdf", True),
        ("pydantic", False),
        ("fitz", False),
        ("pytesseract", False),
    ]
    rows = []
    for module_name, required in dependencies:
        installed = importlib.util.find_spec(module_name) is not None
        if installed:
            rows.append(_row(f"dependency:{module_name}", "PASS", "LOW", "Module disponible.", "Aucune action."))
        elif required:
            rows.append(
                _row(
                    f"dependency:{module_name}",
                    "FAIL",
                    "HIGH",
                    "Module requis non disponible.",
                    "Lancer pip install -r requirements.txt dans l’environnement virtuel.",
                )
            )
        else:
            action = "Installer avec pip install -r requirements.txt pour activer la validation CSV avancée." if module_name == "pydantic" else (
                "Optionnel. Utile seulement pour mieux lire certains PDF ou activer l’OCR."
            )
            details = "Module optionnel non disponible; validation CSV avancée désactivée." if module_name == "pydantic" else "Module optionnel non disponible."
            rows.append(
                _row(
                    f"dependency:{module_name}",
                    "WARN",
                    "LOW",
                    details,
                    action,
                )
            )
    return rows


def _file_rows(project_root: Path) -> list[dict[str, Any]]:
    required_files = [
        DATA_DIR / "portfolio.csv",
        DATA_DIR / "market_universe.csv",
        DATA_DIR / "manual_inputs_friendly.txt",
        project_root / "requirements.txt",
        project_root / "main.py",
    ]
    rows = []
    for path in required_files:
        exists = path.exists()
        rows.append(
            _row(
                f"file:{path.name}",
                "PASS" if exists else "FAIL",
                "HIGH" if not exists else "LOW",
                str(path),
                "Créer le fichier avec python3 main.py init ou export-template." if not exists else "Aucune action.",
            )
        )
    return rows


def _validation_rows(project_root: Path) -> list[dict[str, Any]]:
    errors = validate_input_files(project_root)
    if not errors:
        return [_row("csv_validation", "PASS", "LOW", "Fichiers CSV valides.", "Aucune action.")]
    return [
        _row(
            "csv_validation",
            "FAIL",
            "HIGH",
            "; ".join(errors[:8]),
            "Corriger les fichiers indiqués avant de lancer une analyse importante.",
        )
    ]


def _schema_rows(schema_rows: list[dict[str, Any]], repair_safe: bool) -> list[dict[str, Any]]:
    problematic = [
        row for row in schema_rows if str(row.get("status") or "").upper() not in {"PASS", "REPAIRED"}
    ]
    repaired = [row for row in schema_rows if str(row.get("status") or "").upper() == "REPAIRED"]
    if problematic:
        return [
            _row(
                "csv_schema",
                "WARN",
                "MEDIUM",
                f"{len(problematic)} fichier(s) CSV demandent une correction manuelle; {len(repaired)} réparation(s) safe appliquée(s).",
                "Lire reports/latest_schema_repair.csv.",
            )
        ]
    if repaired:
        return [
            _row(
                "csv_schema",
                "PASS",
                "LOW",
                f"{len(repaired)} réparation(s) safe appliquée(s).",
                "Aucune action. Une sauvegarde est indiquée dans latest_schema_repair.csv.",
            )
        ]
    return [
        _row(
            "csv_schema",
            "PASS",
            "LOW",
            "Schémas CSV OK." if not repair_safe else "Schémas CSV OK; aucune réparation nécessaire.",
            "Aucune action.",
        )
    ]


def _research_report_rows(known_tickers: list[str]) -> list[dict[str, Any]]:
    rows = research_status_rows(
        BNCD_MORNINGSTAR_DIR,
        RESEARCH_REPORTS_DIR / "research_index.csv",
        known_tickers=known_tickers,
    )
    if not rows:
        return [
            _row(
                "research_reports",
                "INFO",
                "LOW",
                "Aucun rapport BNCD/Morningstar local trouvé.",
                "Aucune action sauf si un titre manque de données.",
            )
        ]
    ready = sum(1 for row in rows if row.get("status") == "READY")
    ocr_needed = [row for row in rows if str(row.get("ocr_status") or "").upper() == "OCR_NEEDED"]
    low_quality = [row for row in rows if str(row.get("text_quality_status") or "").upper() in {"LOW_TEXT_QUALITY", "OCR_NEEDED"}]
    output = [
        _row(
            "research_reports:readiness",
            "PASS" if ready else "WARN",
            "MEDIUM" if not ready else "LOW",
            f"{ready}/{len(rows)} fichier(s) prêt(s).",
            "Vérifier latest_research_status.csv si plusieurs rapports ne sont pas READY.",
        )
    ]
    if low_quality:
        output.append(
            _row(
                "research_reports:text_quality",
                "WARN",
                "MEDIUM",
                f"{len(low_quality)} rapport(s) avec texte faible ou OCR requis; {len(ocr_needed)} OCR_NEEDED.",
                "Remplacer par un PDF texte, ou installer OCR seulement si nécessaire.",
            )
        )
    else:
        output.append(_row("research_reports:text_quality", "PASS", "LOW", "Qualité texte OK pour les rapports lisibles.", "Aucune action."))
    return output


def _cache_rows(cache_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not cache_rows:
        return [_row("market_cache", "INFO", "LOW", "Cache non vérifié.", "Relancer health-check.")]
    summary = next((row for row in cache_rows if row.get("category") == "summary"), cache_rows[0])
    status = str(summary.get("status") or "INFO")
    severity = str(summary.get("severity") or ("MEDIUM" if status == "WARN" else "LOW"))
    return [
        _row(
            "market_cache",
            status,
            severity,
            cache_health_summary(cache_rows),
            "Lire reports/latest_cache_health.csv." if status == "WARN" else "Aucune action.",
        )
    ]


def _row(check: str, status: str, severity: str, details: str, suggested_action: str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "severity": severity,
        "details": details,
        "suggested_action": suggested_action,
    }
