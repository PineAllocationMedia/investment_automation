from __future__ import annotations

import csv
import time
from pathlib import Path

from .mode_artifacts import mode_artifact_path


SIMULATED_STATUSES = {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
WALK_FORWARD_COMMAND = "python3 main.py walk-forward-backtest --mode {mode}"


def compute_walk_forward_signal(reports_dir: str | Path, mode: str) -> dict[str, str]:
    """Return a compact health signal for the latest walk-forward artifact of the active mode."""
    command = WALK_FORWARD_COMMAND.format(mode=mode)
    try:
        reports_path = Path(reports_dir)
        inventory_path = _first_existing_path(reports_path, "latest_walk_forward_inventory.csv", mode)
        if inventory_path is None or not inventory_path.exists() or inventory_path.stat().st_size <= 0:
            return _signal(
                "WALK_FORWARD_ABSENT",
                f"⚠️ WALK_FORWARD_ABSENT — Le gate anti-overfitting est aveugle pour ce mode. Lancer : {command}",
                command,
            )

        age_days = int((time.time() - inventory_path.stat().st_mtime) // 86400)
        if age_days > 21:
            return _signal(
                "WALK_FORWARD_STALE",
                "⚠️ WALK_FORWARD_STALE — "
                f"Dernière exécution il y a {age_days} jours. Le gate anti-overfitting utilise des données périmées. "
                f"Relancer : {command}",
                command,
            )

        inventory_rows = _read_csv_rows(inventory_path)
        if not inventory_rows:
            return _absent_unreadable(command)

        simulated_count, regime_count = _simulation_counts(reports_path, mode, inventory_rows)
        if simulated_count < 4:
            return _signal(
                "WALK_FORWARD_DORMANT",
                "⚠️ WALK_FORWARD_DORMANT — "
                f"Seulement {simulated_count} période(s) simulée(s). Gate anti-overfitting partiellement aveugle. "
                f"Relancer régulièrement : {command}",
                command,
            )
        if simulated_count <= 7 and regime_count < 2:
            return _signal(
                "WALK_FORWARD_EARLY",
                "ℹ️ WALK_FORWARD_EARLY — "
                f"{simulated_count} périodes simulées, régime de marché limité. "
                f"Continuer à relancer après chaque nouvelle cotisation. Relancer : {command}",
                command,
            )
        return _signal(
            "WALK_FORWARD_HEALTHY",
            f"✅ WALK_FORWARD_HEALTHY — {simulated_count} périodes simulées. "
            "Gate anti-overfitting actif. Prochaine exécution dans ~21 jours.",
            "",
        )
    except Exception:
        return _absent_unreadable(command)


def _signal(status: str, message: str, command: str) -> dict[str, str]:
    return {"status": status, "message": message, "command": command}


def _absent_unreadable(command: str) -> dict[str, str]:
    return _signal(
        "WALK_FORWARD_ABSENT",
        "⚠️ WALK_FORWARD_ABSENT — Le gate anti-overfitting est aveugle pour ce mode (fichier illisible). "
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


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    except Exception:
        return []


def _simulation_counts(reports_dir: Path, mode: str, inventory_rows: list[dict[str, str]]) -> tuple[int, int]:
    period_rows = _read_csv_rows(_first_existing_path(reports_dir, "latest_walk_forward_periods.csv", mode) or Path())
    simulated_periods = [
        row for row in period_rows if str(row.get("evaluation_status") or "").strip().upper() in SIMULATED_STATUSES
    ]
    if simulated_periods:
        return len(simulated_periods), _distinct_regime_count(simulated_periods)

    summary_rows = _read_csv_rows(_first_existing_path(reports_dir, "latest_walk_forward_summary.csv", mode) or Path())
    if summary_rows:
        summary = summary_rows[0]
        simulated_count = _safe_int(summary.get("simulated_periods"))
        regime_count = _safe_int(summary.get("regime_count"))
        return simulated_count, regime_count

    usable_inventory_rows = [row for row in inventory_rows if _truthy(row.get("usable_for_walk_forward"))]
    return len(usable_inventory_rows), _distinct_regime_count(usable_inventory_rows)


def _distinct_regime_count(rows: list[dict[str, str]]) -> int:
    regimes = {
        str(row.get("market_regime") or row.get("regime") or row.get("market_regime_status") or "").strip()
        for row in rows
    }
    return len({regime for regime in regimes if regime})


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "oui"}


def _safe_int(value: object) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return 0
