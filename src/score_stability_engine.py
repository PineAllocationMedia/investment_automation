from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import load_json, normalize_ticker, safe_float, today_iso


SCORE_STABILITY_COLUMNS = [
    "ticker",
    "stability_flag",
    "score_total_prev",
    "score_total_curr",
    "score_total_delta",
    "conviction_score_prev",
    "conviction_score_curr",
    "conviction_score_delta",
    "capital_allocation_score_prev",
    "capital_allocation_score_curr",
    "capital_allocation_score_delta",
    "data_reliability_score_prev",
    "data_reliability_score_curr",
    "data_reliability_score_delta",
    "run_date",
    "mode",
]

NUMERIC_FIELDS = [
    "score_total",
    "conviction_score",
    "capital_allocation_score",
]
AUDIT_NUMERIC_FIELDS = [
    *NUMERIC_FIELDS,
    "data_reliability_score",
]
WATCH_THRESHOLD = 1.5
UNSTABLE_THRESHOLD = 3.0
FLAG_ORDER = {"UNSTABLE": 0, "WATCH": 1, "STABLE": 2}


def compute_score_stability(
    reports_dir: str | Path,
    mode: str,
    current_analyses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Compare current scores to the earliest same-day snapshot for the active mode."""
    run_date = today_iso()
    try:
        previous_snapshot = _earliest_same_day_snapshot(Path(reports_dir), mode, run_date)
        if not previous_snapshot:
            return _baseline("ℹ️ SCORE_STABILITY_BASELINE — Premier run de la journée. Relancer analyze pour comparer les scores.")
        previous_rows = _rows_by_ticker(previous_snapshot.get("analyses"))
        if not previous_rows:
            return _baseline("ℹ️ SCORE_STABILITY_BASELINE — Premier run de la journée. Relancer analyze pour comparer les scores.")

        rows = _comparison_rows(previous_rows, current_analyses or {}, run_date, mode)
        if not rows:
            return _baseline(
                "ℹ️ SCORE_STABILITY_BASELINE — Aucun titre comparable entre les runs du jour (lecture possible, comparaison vide)."
            )

        unstable_count = sum(1 for row in rows if row["stability_flag"] == "UNSTABLE")
        watch_count = sum(1 for row in rows if row["stability_flag"] == "WATCH")
        stable_count = sum(1 for row in rows if row["stability_flag"] == "STABLE")

        if unstable_count:
            status = "UNSTABLE"
            message = (
                "⚠️ SCORE_STABILITY_UNSTABLE — "
                f"{unstable_count} ticker(s) avec variation de score ≥ 3 pts entre deux runs du même jour "
                "sans changement de données connu. Voir reports/latest_score_stability.csv pour identifier la source."
            )
        elif watch_count:
            status = "WATCH"
            message = (
                "ℹ️ SCORE_STABILITY_WATCH — "
                f"{watch_count} ticker(s) avec légère variation de score (< 3 pts). "
                "Voir reports/latest_score_stability.csv."
            )
        else:
            status = "STABLE"
            message = (
                "✅ SCORE_STABILITY_STABLE — Tous les scores sont identiques entre les deux runs du jour "
                f"({stable_count} tickers comparés)."
            )
        return {
            "status": status,
            "message": message,
            "unstable_count": unstable_count,
            "watch_count": watch_count,
            "stable_count": stable_count,
            "ticker_rows": rows,
        }
    except Exception:
        return _baseline(
            "ℹ️ SCORE_STABILITY_BASELINE — Premier run de la journée. Relancer analyze pour comparer les scores. "
            "(lecture impossible)"
        )


def _baseline(message: str) -> dict[str, Any]:
    return {
        "status": "SCORE_STABILITY_BASELINE",
        "message": message,
        "unstable_count": 0,
        "watch_count": 0,
        "stable_count": 0,
        "ticker_rows": [],
    }


def _earliest_same_day_snapshot(reports_dir: Path, mode: str, run_date: str) -> dict[str, Any]:
    history_dir = reports_dir / "history"
    if not history_dir.exists():
        return {}
    snapshots: list[tuple[str, str, Path, dict[str, Any]]] = []
    for path in history_dir.glob("analysis_*.json"):
        payload = load_json(path)
        if not isinstance(payload, dict):
            continue
        if str(payload.get("analysis_date") or "")[:10] != run_date:
            continue
        if _normalize_mode(payload.get("analysis_mode")) != _normalize_mode(mode):
            continue
        created_at = str(payload.get("created_at") or "")
        snapshots.append((created_at, path.name, path, payload))
    if len(snapshots) <= 1:
        return {}
    snapshots.sort(key=lambda item: (item[0], item[1]))
    return snapshots[0][3]


def _comparison_rows(
    previous_rows: dict[str, dict[str, Any]],
    current_analyses: dict[str, dict[str, Any]],
    run_date: str,
    mode: str,
) -> list[dict[str, Any]]:
    current_rows = _rows_by_ticker(current_analyses.values())
    rows: list[dict[str, Any]] = []
    for ticker in sorted(set(previous_rows) & set(current_rows)):
        previous = previous_rows[ticker]
        current = current_rows[ticker]
        if _is_ignored_ticker(ticker, previous, current):
            continue
        deltas = {
            field: _delta(previous.get(field), current.get(field))
            for field in AUDIT_NUMERIC_FIELDS
        }
        comparable_deltas = [abs(deltas[field]) for field in NUMERIC_FIELDS if deltas.get(field) is not None]
        if not comparable_deltas:
            continue
        max_delta = max(comparable_deltas)
        if max_delta >= UNSTABLE_THRESHOLD:
            flag = "UNSTABLE"
        elif max_delta >= WATCH_THRESHOLD:
            flag = "WATCH"
        else:
            flag = "STABLE"
        rows.append(_row(ticker, flag, previous, current, deltas, run_date, mode))
    rows.sort(key=lambda row: (FLAG_ORDER.get(str(row.get("stability_flag")), 9), -(safe_float(row.get("score_total_delta")) or 0.0), str(row.get("ticker"))))
    return rows


def _row(
    ticker: str,
    flag: str,
    previous: dict[str, Any],
    current: dict[str, Any],
    deltas: dict[str, float | None],
    run_date: str,
    mode: str,
) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "stability_flag": flag,
        "score_total_prev": _rounded(previous.get("score_total")),
        "score_total_curr": _rounded(current.get("score_total")),
        "score_total_delta": _rounded(deltas.get("score_total")),
        "conviction_score_prev": _rounded(previous.get("conviction_score")),
        "conviction_score_curr": _rounded(current.get("conviction_score")),
        "conviction_score_delta": _rounded(deltas.get("conviction_score")),
        "capital_allocation_score_prev": _rounded(previous.get("capital_allocation_score")),
        "capital_allocation_score_curr": _rounded(current.get("capital_allocation_score")),
        "capital_allocation_score_delta": _rounded(deltas.get("capital_allocation_score")),
        "data_reliability_score_prev": _rounded(previous.get("data_reliability_score")),
        "data_reliability_score_curr": _rounded(current.get("data_reliability_score")),
        "data_reliability_score_delta": _rounded(deltas.get("data_reliability_score")),
        "run_date": run_date,
        "mode": mode,
    }


def _rows_by_ticker(rows: Any) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if isinstance(rows, dict):
        iterable = rows.values()
    elif isinstance(rows, list) or isinstance(rows, tuple):
        iterable = rows
    elif hasattr(rows, "__iter__"):
        iterable = rows
    else:
        iterable = []
    for row in iterable:
        if not isinstance(row, dict):
            continue
        ticker = normalize_ticker(row.get("ticker"))
        if ticker:
            indexed[ticker] = row
    return indexed


def _delta(previous: Any, current: Any) -> float | None:
    prev_value = safe_float(previous)
    curr_value = safe_float(current)
    if prev_value is None or curr_value is None:
        return None
    return abs(curr_value - prev_value)


def _rounded(value: Any) -> float | None:
    number = safe_float(value)
    if number is None:
        return None
    return round(number, 4)


def _is_ignored_ticker(ticker: str, previous: dict[str, Any], current: dict[str, Any]) -> bool:
    if normalize_ticker(ticker) == "VFV.TO":
        return True
    return _is_etf_row(previous) or _is_etf_row(current)


def _is_etf_row(row: dict[str, Any]) -> bool:
    return str(row.get("asset_type") or row.get("instrument_type") or "").strip().upper() == "ETF"


def _normalize_mode(mode: Any) -> str:
    return str(mode or "").strip().lower().replace("_", "-")
