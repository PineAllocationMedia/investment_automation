from __future__ import annotations

import time
from pathlib import Path

from .mode_artifacts import mode_artifact_path


FULL_AUDIT_STALE_DAYS = 60
MODEL_AUDIT_STALE_DAYS = 21
FULL_AUDIT_COMMAND = "python3 main.py full-audit --period all --mode {mode} --refresh-market-data"
MODEL_AUDIT_COMMAND = "python3 main.py model-audit --period 12m --mode {mode}"


def compute_full_audit_signal(reports_dir: str | Path, mode: str) -> dict[str, str]:
    """Return a compact health signal for the latest full-audit artifact of the active mode."""
    command = FULL_AUDIT_COMMAND.format(mode=mode)
    try:
        reports_path = Path(reports_dir)
        summary_path = _first_existing_path(reports_path, "latest_full_audit_summary.csv", mode)
        if summary_path is None or not summary_path.exists() or summary_path.stat().st_size <= 0:
            return _signal(
                "FULL_AUDIT_ABSENT",
                "⚠️ FULL_AUDIT_ABSENT — Aucun audit maître disponible pour ce mode. "
                f"Le critère 7 et la performance réelle ne sont pas suivis. Lancer : {command}",
                command,
            )

        age_days = int((time.time() - summary_path.stat().st_mtime) // 86400)
        if age_days > FULL_AUDIT_STALE_DAYS:
            first_row = _read_first_csv_row(summary_path)
            criterion7_status = str(first_row.get("status") or "").strip()
            criterion7_value = str(first_row.get("value") or "").strip()
            verdict = f" Dernier résultat connu : critère 7 {criterion7_status} ({criterion7_value})." if criterion7_status else ""
            return _signal(
                "FULL_AUDIT_STALE",
                f"⚠️ FULL_AUDIT_STALE — Dernier audit il y a {age_days} jours "
                f"(seuil : {FULL_AUDIT_STALE_DAYS}j).{verdict} Relancer : {command}",
                command,
            )
        first_row = _read_first_csv_row(summary_path)
        criterion7_status = str(first_row.get("status") or "").strip()
        criterion7_value = str(first_row.get("value") or "").strip()
        verdict = f" Dernier résultat : critère 7 {criterion7_status} ({criterion7_value})." if criterion7_status else ""
        return _signal(
            "FULL_AUDIT_HEALTHY",
            f"✅ FULL_AUDIT_HEALTHY — Audit maître récent ({age_days}j).{verdict} "
            f"Prochain audit dans ~{FULL_AUDIT_STALE_DAYS - age_days}j.",
            "",
        )
    except Exception:
        return _absent_unreadable(command, "FULL_AUDIT")


def compute_model_audit_signal(reports_dir: str | Path, mode: str) -> dict[str, str]:
    """Return a compact health signal for the latest model-audit artifact of the active mode."""
    command = MODEL_AUDIT_COMMAND.format(mode=mode)
    try:
        reports_path = Path(reports_dir)
        audit_path = _first_existing_path(reports_path, "latest_model_audit.csv", mode)
        if audit_path is None or not audit_path.exists() or audit_path.stat().st_size <= 0:
            return _signal(
                "MODEL_AUDIT_ABSENT",
                "⚠️ MODEL_AUDIT_ABSENT — Aucun audit de stabilité disponible pour ce mode. "
                f"La cohérence du modèle n'est pas suivie. Lancer : {command}",
                command,
            )

        age_days = int((time.time() - audit_path.stat().st_mtime) // 86400)
        if age_days > MODEL_AUDIT_STALE_DAYS:
            first_row = _read_first_csv_row(audit_path)
            health_status = str(first_row.get("status") or "").strip()
            health_value = str(first_row.get("value") or "").strip()
            verdict = f" Dernier résultat connu : {health_status} ({health_value})." if health_status else ""
            return _signal(
                "MODEL_AUDIT_STALE",
                f"⚠️ MODEL_AUDIT_STALE — Dernier audit de stabilité il y a {age_days} jours "
                f"(seuil : {MODEL_AUDIT_STALE_DAYS}j).{verdict} Relancer : {command}",
                command,
            )
        first_row = _read_first_csv_row(audit_path)
        health_status = str(first_row.get("status") or "").strip()
        health_value = str(first_row.get("value") or "").strip()
        verdict = f" Dernier résultat : {health_status} ({health_value})." if health_status else ""
        return _signal(
            "MODEL_AUDIT_HEALTHY",
            f"✅ MODEL_AUDIT_HEALTHY — Audit de stabilité récent ({age_days}j).{verdict} "
            f"Prochain audit dans ~{MODEL_AUDIT_STALE_DAYS - age_days}j.",
            "",
        )
    except Exception:
        return _absent_unreadable(command, "MODEL_AUDIT")


def _signal(status: str, message: str, command: str) -> dict[str, str]:
    return {"status": status, "message": message, "command": command}


def _absent_unreadable(command: str, prefix: str) -> dict[str, str]:
    if prefix == "MODEL_AUDIT":
        return _signal(
            "MODEL_AUDIT_ABSENT",
            "⚠️ MODEL_AUDIT_ABSENT — Aucun audit de stabilité disponible pour ce mode (fichier illisible). "
            f"Lancer : {command}",
            command,
        )
    return _signal(
        "FULL_AUDIT_ABSENT",
        "⚠️ FULL_AUDIT_ABSENT — Aucun audit maître disponible pour ce mode (fichier illisible). "
        f"Lancer : {command}",
        command,
    )


def _first_existing_path(reports_dir: Path, filename: str, mode: str) -> Path | None:
    candidates = [
        mode_artifact_path(reports_dir / filename, mode),
        reports_dir / f"{Path(filename).stem}_{mode}{Path(filename).suffix}",
        reports_dir / filename,
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _read_first_csv_row(path: Path) -> dict[str, str]:
    """Lire la première ligne de données d'un CSV sentinelle."""
    try:
        import csv

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            return next(iter(reader), {})
    except Exception:
        return {}
