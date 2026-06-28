from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import read_csv_records, safe_float, today_iso, write_csv_records


RUN_LOG_COLUMNS = [
    "timestamp",
    "date",
    "run_id",
    "command",
    "mode",
    "level",
    "component",
    "event",
    "ticker",
    "message",
    "suggested_action",
    "details",
]

LEVEL_RANK = {"ERROR": 4, "WARN": 3, "INFO": 2, "DEBUG": 1}
SOURCE_WARN_STATUSES = {"WATCH", "DEGRADED", "CRITICAL", "WARN", "FAIL"}
TICKER_MEMORY_WARN_STATUSES = {"LOW_FREE_COVERAGE", "NEEDS_TICKER_REVIEW", "CLASSIFICATION_CHANGED_REVIEW"}


def make_run_id(command: str, mode: str | None = None, now: datetime | None = None) -> str:
    now = now or datetime.now()
    suffix = f"{command}-{mode or 'global'}".replace("_", "-").replace(" ", "-").lower()
    return f"{now.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def build_analysis_run_log(
    *,
    run_id: str,
    mode: str,
    capital: float,
    refresh_market_data: bool,
    universe_counts: dict[str, int] | None = None,
    validation_warnings: list[str] | None = None,
    allocation_warnings: list[str] | None = None,
    cache_health_rows: list[dict[str, Any]] | None = None,
    data_gaps: list[dict[str, Any]] | None = None,
    validation_priority_rows: list[dict[str, Any]] | None = None,
    anomaly_rows: list[dict[str, Any]] | None = None,
    allocation_result: dict[str, Any] | None = None,
    portfolio_risk: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    universe_counts = universe_counts or {}
    validation_warnings = validation_warnings or []
    allocation_warnings = allocation_warnings or []
    cache_health_rows = cache_health_rows or []
    data_gaps = data_gaps or []
    validation_priority_rows = validation_priority_rows or []
    anomaly_rows = anomaly_rows or []
    allocation_result = allocation_result or {}
    portfolio_risk = portfolio_risk or {}

    _add(
        rows,
        run_id,
        "analyze",
        mode,
        "INFO",
        "RUN",
        "RUN_STARTED",
        f"Analyse lancée avec {capital:.2f} $ de capital.",
        details=f"refresh_market_data={bool(refresh_market_data)}; univers={universe_counts}",
    )
    if universe_counts:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "INFO",
            "UNIVERSE",
            "UNIVERSE_COUNTS",
            _universe_message(universe_counts),
            details=str(universe_counts),
        )

    if validation_warnings:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN",
            "INPUTS",
            "INPUT_VALIDATION_WARNINGS",
            f"{len(validation_warnings)} avertissement(s) de validation détecté(s).",
            "Lire la section Données à vérifier avant une grosse décision.",
            details=" | ".join(str(item) for item in validation_warnings[:8]),
        )

    cache_summary = _summary_row(cache_health_rows)
    if cache_summary:
        cache_status = str(cache_summary.get("status") or "INFO").upper()
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN" if cache_status == "WARN" else "INFO",
            "CACHE",
            "CACHE_HEALTH",
            str(cache_summary.get("details") or "Cache vérifié."),
            "Lire reports/latest_cache_health.csv." if cache_status == "WARN" else "Aucune action.",
            details=f"cleaned_count={cache_summary.get('cleaned_count', 0)}",
        )

    high_gaps = [row for row in data_gaps if str(row.get("importance") or "").upper() == "HIGH"]
    if high_gaps:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN",
            "DATA",
            "HIGH_IMPORTANCE_DATA_GAPS",
            f"{len(high_gaps)} donnée(s) importante(s) manquante(s) ou fragile(s).",
            "Lire reports/latest_data_gaps.csv et reports/latest_validation_priority.csv.",
            details=_ticker_field_details(high_gaps),
        )

    priority_rows = [row for row in validation_priority_rows if str(row.get("priority") or "").upper() == "HIGH"]
    if priority_rows:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN",
            "VALIDATION",
            "HIGH_PRIORITY_VALIDATION",
            f"{len(priority_rows)} validation(s) manuelle(s) haute priorité.",
            "Chercher un rapport fiable ou valider la donnée avant une grosse allocation.",
            details=_ticker_field_details(priority_rows),
        )

    if allocation_warnings:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN",
            "ALLOCATION",
            "ALLOCATION_RULE_WARNINGS",
            f"{len(allocation_warnings)} avertissement(s) de règles d'allocation.",
            "Lire le rapport avant d'exécuter.",
            details=" | ".join(str(item) for item in allocation_warnings[:8]),
        )

    allocations = allocation_result.get("allocations") or []
    allocation_text = _allocation_message(allocations)
    _add(
        rows,
        run_id,
        "analyze",
        mode,
        "INFO",
        "ALLOCATION",
        "ALLOCATION_OUTPUT",
        allocation_text,
        "Suivre le workflow habituel: lire le rapport compact avant d'acheter.",
        details=f"allocation_count={len(allocations)}; mandatory_vfv_percent={allocation_result.get('mandatory_vfv_percent')}",
    )

    risk_alerts = portfolio_risk.get("alerts") or []
    if risk_alerts:
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN",
            "RISK",
            "PORTFOLIO_RISK_ALERTS",
            f"{len(risk_alerts)} alerte(s) de concentration ou corrélation.",
            "Lire la section Portfolio risk; ne pas vendre automatiquement.",
            details=_risk_details(risk_alerts),
        )

    actionable_anomalies = [row for row in anomaly_rows if row.get("anomaly_type") != "NO_MAJOR_ANOMALY"]
    if actionable_anomalies:
        worst = _worst_level(actionable_anomalies, "severity")
        _add(
            rows,
            run_id,
            "analyze",
            mode,
            "WARN" if worst != "INFO" else "INFO",
            "ANOMALY",
            "POST_ANALYSIS_ANOMALIES",
            f"{len(actionable_anomalies)} anomalie(s) post-analyse détectée(s); niveau max {worst}.",
            "Lire reports/latest_anomaly_report.csv; lancer improvement-audit seulement si le signal persiste.",
            details=_anomaly_details(actionable_anomalies),
        )

    _add(
        rows,
        run_id,
        "analyze",
        mode,
        "INFO",
        "RUN",
        "RUN_COMPLETED",
        "Analyse terminée et rapports générés.",
        "Aucune action technique.",
    )
    return rows


def extend_report_run_log(
    rows: list[dict[str, Any]] | None,
    *,
    source_health_rows: list[dict[str, Any]] | None = None,
    source_conflict_rows: list[dict[str, Any]] | None = None,
    ticker_memory_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    output = [dict(row) for row in (rows or [])]
    context = _first_context(output)
    run_id = context.get("run_id") or make_run_id("report")
    command = context.get("command") or "analyze"
    mode = context.get("mode") or ""
    completion_rows = [row for row in output if row.get("event") == "RUN_COMPLETED"]
    output = [row for row in output if row.get("event") != "RUN_COMPLETED"]

    source_health_rows = source_health_rows or []
    source_conflict_rows = source_conflict_rows or []
    ticker_memory_rows = ticker_memory_rows or []

    degraded_sources = [row for row in source_health_rows if str(row.get("status") or "").upper() in SOURCE_WARN_STATUSES]
    if degraded_sources:
        weakest = sorted(degraded_sources, key=lambda row: safe_float(row.get("health_score")) or 0.0)[0]
        _add(
            output,
            run_id,
            command,
            mode,
            "WARN",
            "SOURCES",
            "SOURCE_HEALTH_WARNINGS",
            f"{len(degraded_sources)} source(s) à surveiller; plus faible: {weakest.get('source')} ({weakest.get('status')}).",
            "Lire reports/latest_source_health.csv.",
            details=_source_details(degraded_sources),
        )

    important_conflicts = [row for row in source_conflict_rows if _is_priority_source_conflict(row)]
    if important_conflicts:
        _add(
            output,
            run_id,
            command,
            mode,
            "WARN",
            "SOURCES",
            "SOURCE_CONFLICTS",
            f"{len(important_conflicts)} contradiction(s) de source à vérifier.",
            "Lire reports/latest_source_conflicts.csv avant une grosse décision.",
            details=_ticker_field_details(important_conflicts),
        )

    ticker_reviews = [row for row in ticker_memory_rows if str(row.get("ticker_memory_status") or "").upper() in TICKER_MEMORY_WARN_STATUSES]
    if ticker_reviews:
        _add(
            output,
            run_id,
            command,
            mode,
            "WARN",
            "TICKER_MEMORY",
            "TICKER_MEMORY_REVIEW",
            f"{len(ticker_reviews)} ticker(s) à surveiller dans la mémoire locale.",
            "Lire reports/latest_ticker_memory.csv si un titre recommandé est touché.",
            details=_ticker_field_details(ticker_reviews),
        )

    if completion_rows:
        original = completion_rows[-1]
        _add(
            output,
            run_id,
            command,
            mode,
            str(original.get("level") or "INFO"),
            str(original.get("component") or "RUN"),
            "RUN_COMPLETED",
            str(original.get("message") or "Analyse terminée et rapports générés."),
            str(original.get("suggested_action") or "Aucune action technique."),
            details=str(original.get("details") or ""),
        )
    return output


def build_health_check_run_log(
    *,
    run_id: str,
    repair_safe: bool,
    health_rows: list[dict[str, Any]],
    cache_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    fail_count = sum(1 for row in health_rows if str(row.get("status") or "").upper() == "FAIL")
    warn_count = sum(1 for row in health_rows if str(row.get("status") or "").upper() == "WARN")
    _add(
        rows,
        run_id,
        "health-check",
        "",
        "INFO",
        "RUN",
        "RUN_STARTED",
        f"Health-check lancé; repair_safe={bool(repair_safe)}.",
        details=f"repair_safe={bool(repair_safe)}",
    )
    level = "ERROR" if fail_count else ("WARN" if warn_count else "INFO")
    _add(
        rows,
        run_id,
        "health-check",
        "",
        level,
        "HEALTH",
        "HEALTH_CHECK_SUMMARY",
        f"{fail_count} FAIL, {warn_count} WARN.",
        "Corriger les FAIL avant une grosse décision." if fail_count else ("Lire les WARN; ils ne bloquent pas forcément." if warn_count else "Aucune action."),
        details=_health_details(health_rows),
    )
    cache_summary = _summary_row(cache_rows or [])
    if cache_summary:
        status = str(cache_summary.get("status") or "INFO").upper()
        _add(
            rows,
            run_id,
            "health-check",
            "",
            "WARN" if status == "WARN" else "INFO",
            "CACHE",
            "CACHE_HEALTH",
            str(cache_summary.get("details") or "Cache vérifié."),
            "Lire reports/latest_cache_health.csv." if status == "WARN" else "Aucune action.",
            details=f"cleaned_count={cache_summary.get('cleaned_count', 0)}",
        )
    _add(rows, run_id, "health-check", "", "INFO", "RUN", "RUN_COMPLETED", "Health-check terminé.", "Aucune action technique.")
    return rows


def build_walk_forward_run_log(
    *,
    run_id: str,
    mode: str,
    refresh_market_data: bool,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    coverage = result.get("coverage") or {}
    summary = result.get("summary") or {}
    regime_rows = result.get("regime_rows") or []
    status = str(summary.get("status") or "UNKNOWN")
    simulated = int(safe_float(summary.get("simulated_periods")) or 0)
    usable = int(safe_float(summary.get("usable_walk_forward_periods") or coverage.get("usable_walk_forward_periods")) or 0)
    weak_regimes = str(summary.get("weak_regimes") or "").strip()
    price_basis = str(summary.get("price_return_basis") or "")

    _add(
        rows,
        run_id,
        "walk-forward-backtest",
        mode,
        "INFO",
        "RUN",
        "RUN_STARTED",
        f"Backtest walk-forward lancé en mode {mode}.",
        details=f"refresh_market_data={bool(refresh_market_data)}",
    )
    level = "INFO"
    action = "Aucune action; accumuler des analyses espacées."
    if status in {"NO_SIMULATED_PERIODS", "SIMULATION_ERROR"} or price_basis == "PRICE_FETCH_FAILED":
        level = "WARN"
        action = "Relancer avec --refresh-market-data ou vérifier les prix historiques si le problème persiste."
    elif weak_regimes:
        level = "WARN"
        action = "Lire latest_walk_forward_regime_summary.csv; ne pas ajuster automatiquement sur ce seul signal."

    _add(
        rows,
        run_id,
        "walk-forward-backtest",
        mode,
        level,
        "WALK_FORWARD",
        "WALK_FORWARD_SUMMARY",
        f"Status={status}; {usable} période(s) utilisable(s), {simulated} simulée(s).",
        action,
        details=(
            f"coverage_status={coverage.get('status')}; price_basis={price_basis}; "
            f"regime_coverage={summary.get('regime_coverage_status')}; weak_regimes={weak_regimes}"
        ),
    )
    if regime_rows:
        _add(
            rows,
            run_id,
            "walk-forward-backtest",
            mode,
            "WARN" if weak_regimes else "INFO",
            "WALK_FORWARD",
            "WALK_FORWARD_REGIME_CHECK",
            f"{len(regime_rows)} régime(s) de marché observé(s); faiblesse: {weak_regimes or 'aucune'}.",
            "Lire latest_walk_forward_regime_summary.csv." if weak_regimes else "Aucune action.",
            details=_walk_forward_regime_details(regime_rows),
        )
    _add(
        rows,
        run_id,
        "walk-forward-backtest",
        mode,
        "INFO",
        "RUN",
        "RUN_COMPLETED",
        "Backtest walk-forward terminé.",
        "Aucune action technique.",
    )
    return rows


def append_run_log_history(path: str | Path, rows: list[dict[str, Any]], max_rows: int = 3000) -> list[dict[str, Any]]:
    path = Path(path)
    if not rows:
        return read_csv_records(path)
    run_ids = {str(row.get("run_id") or "") for row in rows if row.get("run_id")}
    existing = read_csv_records(path)
    cleaned = [row for row in existing if str(row.get("run_id") or "") not in run_ids]
    combined = [*cleaned, *rows][-max_rows:]
    write_csv_records(path, combined, RUN_LOG_COLUMNS)
    return combined


def run_log_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Journal non disponible."
    errors = [row for row in rows if str(row.get("level") or "").upper() == "ERROR"]
    warnings = [row for row in rows if str(row.get("level") or "").upper() == "WARN"]
    if errors:
        return f"{len(errors)} erreur(s), {len(warnings)} avertissement(s). Lire latest_run_log.csv avant toute décision."
    if warnings:
        return f"{len(warnings)} avertissement(s) non bloquant(s). Lire latest_run_log.csv si la recommandation surprend."
    return "Aucun avertissement technique important."


def run_log_rows_for_report(rows: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    selected = sorted(rows, key=_report_sort_key)
    if not selected:
        return [
            {
                "niveau": "INFO",
                "composant": "RUN",
                "événement": "NO_LOG",
                "message": "Journal non disponible.",
                "action": "Aucune action.",
            }
        ]
    return [
        {
            "niveau": row.get("level"),
            "composant": row.get("component"),
            "événement": row.get("event"),
            "message": row.get("message"),
            "action": row.get("suggested_action"),
        }
        for row in selected[:limit]
    ]


def _add(
    rows: list[dict[str, Any]],
    run_id: str,
    command: str,
    mode: str,
    level: str,
    component: str,
    event: str,
    message: str,
    suggested_action: str = "Aucune action.",
    *,
    ticker: str = "",
    details: str = "",
) -> None:
    rows.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "date": today_iso(),
            "run_id": run_id,
            "command": command,
            "mode": mode,
            "level": level,
            "component": component,
            "event": event,
            "ticker": ticker,
            "message": message,
            "suggested_action": suggested_action,
            "details": details,
        }
    )


def _first_context(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if row.get("run_id"):
            return row
    return {}


def _summary_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return next((row for row in rows if str(row.get("category") or "") == "summary"), rows[0] if rows else None)


def _worst_level(rows: list[dict[str, Any]], key: str) -> str:
    levels = [str(row.get(key) or "INFO").upper() for row in rows]
    return sorted(levels, key=lambda item: LEVEL_RANK.get(item, 0), reverse=True)[0] if levels else "INFO"


def _allocation_message(allocations: list[dict[str, Any]]) -> str:
    if not allocations:
        return "Aucune allocation produite."
    parts = []
    for row in allocations[:6]:
        ticker = row.get("ticker") or row.get("destination") or ""
        amount = safe_float(row.get("amount") or row.get("montant")) or 0.0
        parts.append(f"{ticker} {amount:.2f} $")
    suffix = "..." if len(allocations) > 6 else ""
    return "Allocation produite: " + ", ".join(parts) + suffix


def _universe_message(counts: dict[str, int]) -> str:
    if not counts:
        return "Univers analysé non détaillé."
    return "Univers analysé: " + ", ".join(f"{key}={value}" for key, value in counts.items())


def _ticker_field_details(rows: list[dict[str, Any]], limit: int = 10) -> str:
    parts = []
    for row in rows[:limit]:
        ticker = row.get("ticker") or row.get("ticker_display") or row.get("affected_tickers") or ""
        field = row.get("data_field") or row.get("metric") or row.get("need_type") or row.get("event") or row.get("status") or ""
        parts.append(" ".join(str(item) for item in [ticker, field] if item))
    return " | ".join(parts)


def _risk_details(rows: list[dict[str, Any]], limit: int = 8) -> str:
    return " | ".join(
        f"{row.get('risk_type')}:{row.get('name')}={safe_float(row.get('weight')) or 0:.1%} {row.get('alert')}"
        for row in rows[:limit]
    )


def _anomaly_details(rows: list[dict[str, Any]], limit: int = 8) -> str:
    return " | ".join(
        f"{row.get('ticker') or row.get('scope')}:{row.get('anomaly_type')} {row.get('severity')}"
        for row in rows[:limit]
    )


def _source_details(rows: list[dict[str, Any]], limit: int = 8) -> str:
    return " | ".join(
        f"{row.get('source')}={row.get('status')} {row.get('health_score')}/100"
        for row in rows[:limit]
    )


def _walk_forward_regime_details(rows: list[dict[str, Any]], limit: int = 8) -> str:
    return " | ".join(
        f"{row.get('market_regime')}={row.get('regime_status')} n={row.get('period_count')} excess={row.get('compounded_excess_return_vs_vfv')}"
        for row in rows[:limit]
    )


def _is_priority_source_conflict(row: dict[str, Any]) -> bool:
    severity = str(row.get("severity") or "").upper()
    universe = str(row.get("universe") or "").upper()
    if severity in {"HIGH", "HIGH_REVIEW"}:
        return True
    return universe == "CORE_PORTFOLIO" and severity == "REVIEW"


def _health_details(rows: list[dict[str, Any]], limit: int = 8) -> str:
    return " | ".join(
        f"{row.get('status')}:{row.get('check')}"
        for row in rows
        if str(row.get("status") or "").upper() in {"WARN", "FAIL"}
    )[:limit * 80]


def _report_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    level = str(row.get("level") or "INFO").upper()
    event = str(row.get("event") or "")
    event_rank = 0 if level in {"ERROR", "WARN"} else (1 if event in {"RUN_COMPLETED", "ALLOCATION_OUTPUT"} else 2)
    return (-LEVEL_RANK.get(level, 0), event_rank, str(row.get("timestamp") or ""))
