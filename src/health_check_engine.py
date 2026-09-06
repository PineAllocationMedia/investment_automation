from __future__ import annotations

from .runtime_context import state_root

import importlib.util
import tempfile
from pathlib import Path
from typing import Any

from .cache_management_engine import cache_health_summary, run_cache_maintenance
from .baseline_identity import VALIDATION_BASELINE_ID, load_baseline_identity
from .csv_schema_engine import repair_safe_csv_schemas, validate_csv_schemas
from .critical_input_engine import critical_config_fingerprint
from .dependency_reproducibility import dependency_environment
from .model_version import MODEL_RULES_VERSION
from .research_reports import research_status_rows
from .source_health_engine import check_canadian_source_health
from .storage_observability_engine import build_storage_health_rows
from .utils import read_csv_records, safe_float
from .validation_evidence import AUTO_TUNING_POLICY, VALIDATION_SCHEMA_VERSION
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
    rows.extend(_dependency_reproducibility_rows(project_root))
    rows.extend(_baseline_rows(project_root))
    rows.extend(_file_rows(project_root))
    schema_rows = schema_rows if schema_rows is not None else (
        repair_safe_csv_schemas(project_root) if repair_safe else validate_csv_schemas(project_root)
    )
    rows.extend(_schema_rows(schema_rows, repair_safe=repair_safe))
    rows.extend(_validation_rows(project_root))
    rows.extend(_research_report_rows(project_root, known_tickers or []))
    rows.extend(walk_forward_health_rows(project_root))
    cache_rows = cache_rows if cache_rows is not None else run_cache_maintenance(
        state_root(project_root) / "data" / "cached_market_data",
        repair_safe=repair_safe,
    )
    rows.extend(_cache_rows(cache_rows))
    rows.extend(_canadian_source_rows(check_canadian_source_health(state_root(project_root) / "data" / "cached_market_data")))
    rows.extend(build_storage_health_rows(project_root))
    rows.extend(_writeability_rows(project_root))
    return rows


def _dependency_reproducibility_rows(project_root: Path) -> list[dict[str, Any]]:
    environment = dependency_environment(project_root / "requirements.lock")
    status = str(environment.get("dependency_status") or "DRIFT")
    if status == "MATCH":
        return [
            _row(
                "dependency_reproducibility",
                "PASS",
                "LOW",
                f"Python {environment.get('python_version')}; lock and installed dependency versions match; fingerprint={environment.get('dependency_fingerprint')}.",
                "Aucune action.",
            )
        ]
    return [
        _row(
            "dependency_reproducibility",
            "WARN",
            "MEDIUM",
            f"status={status}; Python={environment.get('python_version')}; missing={environment.get('missing_packages')}; drift={environment.get('version_drift')}; fingerprint={environment.get('dependency_fingerprint')}.",
            "Recréer .venv avec Python 3.12 et requirements.lock avant un run Baseline de décision.",
        )
    ]


def _baseline_rows(project_root: Path) -> list[dict[str, Any]]:
    identity = load_baseline_identity(project_root / "config" / "baseline.yaml")
    approved_config = str(identity.get("approved_config_fingerprint") or "")
    actual_config = critical_config_fingerprint(project_root) if approved_config else ""
    checks = [
        identity.get("baseline_id") == VALIDATION_BASELINE_ID,
        identity.get("model_rules_version") == MODEL_RULES_VERSION,
        identity.get("validation_schema_version") == VALIDATION_SCHEMA_VERSION,
        AUTO_TUNING_POLICY == "PROPOSAL_ONLY",
        not approved_config or approved_config == actual_config,
    ]
    if not all(checks):
        return [
            _row(
                "baseline_identity",
                "FAIL",
                "HIGH",
                f"Baseline identity/config mismatch: {identity}; actual_config_fingerprint={actual_config}; tuning={AUTO_TUNING_POLICY}.",
                "Stopper les runs de décision et restaurer l’identité Baseline V1 approuvée.",
            )
        ]
    start_note = identity.get("baseline_started_at") or "pending approved deployment"
    return [
        _row(
            "baseline_identity",
            "PASS",
            "LOW",
            f"{VALIDATION_BASELINE_ID}; model={MODEL_RULES_VERSION}; schema={VALIDATION_SCHEMA_VERSION}; start={start_note}; config={actual_config or 'UNPINNED'}; tuning=PROPOSAL_ONLY.",
            "Renseigner baseline_started_at seulement lors du déploiement Baseline approuvé." if not identity.get("baseline_started_at") else "Aucune action.",
        )
    ]


def _writeability_rows(project_root: Path) -> list[dict[str, Any]]:
    rows = []
    for check, directory in (
        ("manifest_writeability", state_root(project_root) / "reports"),
        ("operational_history_writeability", state_root(project_root) / "data"),
    ):
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(prefix=".baseline-health-", dir=directory, delete=True):
                pass
        except OSError as exc:
            rows.append(_row(check, "FAIL", "HIGH", f"Write test failed: {exc}", "Repair filesystem permissions before production analysis."))
        else:
            rows.append(_row(check, "PASS", "LOW", "Atomic temporary write succeeded.", "Aucune action."))
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
        state_root(project_root) / "data" / "portfolio.csv",
        state_root(project_root) / "data" / "market_universe.csv",
        state_root(project_root) / "data" / "manual_inputs_friendly.txt",
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


def _research_report_rows(project_root: Path, known_tickers: list[str]) -> list[dict[str, Any]]:
    research_dir = state_root(project_root) / "data" / "research_reports"
    rows = research_status_rows(
        research_dir / "bncd_morningstar",
        research_dir / "research_index.csv",
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


def _canadian_source_rows(health: dict[str, Any]) -> list[dict[str, Any]]:
    status = str(health.get("canadian_source_health_status") or "DEAD").upper()
    fallback_available = bool(health.get("canadian_fallback_available"))
    sources = health.get("sources") if isinstance(health.get("sources"), dict) else {}
    source_parts = []
    for source in ("stockanalysis", "tmx", "sedarplus"):
        row = sources.get(source, {}) if isinstance(sources.get(source), dict) else {}
        source_parts.append(
            f"{source}: {row.get('available_files', 0)}/{row.get('attempted_files', 0)} "
            f"({row.get('success_rate_percent', 0)}%), dernier succès={row.get('latest_success_age_hours', 'N/D')}h"
        )
    summary = "; ".join(source_parts)
    if status == "HEALTHY":
        return [
            _row(
                "canadian_sources",
                "PASS",
                "LOW",
                f"status=HEALTHY | canadian_fallback_available={fallback_available} | {summary}",
                "Aucune action.",
            )
        ]
    if status == "DEGRADED":
        return [
            _row(
                "canadian_sources",
                "WARN",
                "MEDIUM",
                f"status=DEGRADED | canadian_fallback_available={fallback_available} | {summary}",
                "Surveiller les titres .TO; relancer avec --refresh-market-data si une recommandation dépend fortement de données canadiennes.",
            )
        ]
    return [
        _row(
            "canadian_sources",
            "WARN",
            "HIGH",
            "status=DEAD | canadian_fallback_available=False | AVERTISSEMENT: Toutes les sources canadiennes de fallback sont inopérantes. "
            "Les titres .TO sont scorés sur yfinance seul sans filet de sécurité fondamental.",
            "Vérifier la connexion réseau ou ajouter/valider des rapports BNCD/Morningstar pour les titres canadiens importants.",
        )
    ]


def walk_forward_health_rows(project_root: str | Path) -> list[dict[str, Any]]:
    project_root = Path(project_root)
    reports_dir = state_root(project_root) / "reports"
    expected = [
        "latest_walk_forward_summary.csv",
        "latest_walk_forward_coverage.csv",
        "latest_walk_forward_periods.csv",
        "latest_walk_forward_report.md",
    ]
    existing = [name for name in expected if (reports_dir / name).exists()]
    if not existing:
        return [
            _row(
                "walk_forward",
                "INFO",
                "LOW",
                "Aucun backtest walk-forward local généré pour l’instant.",
                "Optionnel: lancer python3 main.py walk-forward-backtest --mode high-cagr après quelques analyses espacées.",
            )
        ]

    missing = [name for name in expected if not (reports_dir / name).exists()]
    if missing:
        return [
            _row(
                "walk_forward",
                "WARN",
                "MEDIUM",
                f"Sorties walk-forward partielles; fichier(s) manquant(s): {', '.join(missing)}.",
                "Relancer python3 main.py walk-forward-backtest --mode high-cagr.",
            )
        ]

    summary_rows = read_csv_records(reports_dir / "latest_walk_forward_summary.csv")
    coverage_rows = read_csv_records(reports_dir / "latest_walk_forward_coverage.csv")
    summary = summary_rows[0] if summary_rows else {}
    coverage = coverage_rows[0] if coverage_rows else {}
    status = str(summary.get("status") or "").upper()
    usable = int(safe_float(summary.get("usable_walk_forward_periods") or coverage.get("usable_walk_forward_periods")) or 0)
    simulated = int(safe_float(summary.get("simulated_periods")) or 0)
    regime_status = str(summary.get("regime_coverage_status") or "NO_REGIME_EVIDENCE")
    weak_regimes = str(summary.get("weak_regimes") or "").strip()
    price_basis = str(summary.get("price_return_basis") or "")

    if status in {"NO_USABLE_PERIODS", "INSUFFICIENT_HISTORY", ""}:
        return [
            _row(
                "walk_forward",
                "INFO",
                "LOW",
                f"Walk-forward trop jeune: {usable} période(s) utilisable(s), {simulated} simulée(s).",
                "Aucune action; continuer à utiliser le modèle et relancer après des analyses espacées.",
            )
        ]
    if status in {"NO_SIMULATED_PERIODS", "SIMULATION_ERROR"} or price_basis == "PRICE_FETCH_FAILED":
        return [
            _row(
                "walk_forward",
                "WARN",
                "MEDIUM",
                f"Walk-forward présent mais non simulable proprement: status={status}, base prix={price_basis}.",
                "Relancer avec --refresh-market-data ou vérifier les prix historiques si le problème persiste.",
            )
        ]
    if weak_regimes:
        return [
            _row(
                "walk_forward",
                "WARN",
                "LOW",
                f"Walk-forward simulé: {simulated} période(s); régime(s) faible(s): {weak_regimes}; couverture={regime_status}.",
                "Lire latest_walk_forward_regime_summary.csv; ne pas modifier automatiquement les règles sur ce seul signal.",
            )
        ]
    return [
        _row(
            "walk_forward",
            "PASS",
            "LOW",
            f"Walk-forward disponible: {simulated} période(s) simulée(s); couverture régimes={regime_status}.",
            "Aucune action.",
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
