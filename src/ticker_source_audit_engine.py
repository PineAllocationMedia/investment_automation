from __future__ import annotations

from typing import Any

from .utils import safe_float


TICKER_SOURCE_AUDIT_COLUMNS = [
    "check",
    "status",
    "value",
    "interpretation",
    "impact",
]

REVIEW_TICKER_STATUSES = {"NEEDS_TICKER_REVIEW", "CLASSIFICATION_CHANGED_REVIEW"}
WATCH_TICKER_STATUSES = {"LOW_FREE_COVERAGE", "FALLBACK_AVAILABLE"}
REVIEW_ISSUE_STATUSES = {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}
WATCH_ISSUE_STATUSES = {"NEEDS_BNCD_OR_MANUAL_CONFIRMATION", "LOW_FREE_DATA_COVERAGE"}
REVIEW_CONFLICT_SEVERITIES = {"HIGH_REVIEW"}
WATCH_CONFLICT_SEVERITIES = {"REVIEW", "WATCH"}


def build_ticker_source_audit_context(
    ticker_memory_rows: list[dict[str, Any]] | None = None,
    source_conflict_rows: list[dict[str, Any]] | None = None,
    ticker_issue_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ticker_memory_rows = ticker_memory_rows or []
    source_conflict_rows = source_conflict_rows or []
    ticker_issue_rows = ticker_issue_rows or []

    memory_review = [row for row in ticker_memory_rows if _is_priority_memory_review(row)]
    memory_watch = [row for row in ticker_memory_rows if _is_priority_memory_watch(row)]
    issue_review = [row for row in ticker_issue_rows if _is_priority_ticker_issue(row)]
    issue_watch = [row for row in ticker_issue_rows if _is_watch_ticker_issue(row)]
    conflict_review = [row for row in source_conflict_rows if _is_priority_conflict(row)]
    conflict_watch = [row for row in source_conflict_rows if _is_watch_conflict(row)]

    review_count = len(memory_review) + len(issue_review) + len(conflict_review)
    watch_count = len(memory_watch) + len(issue_watch) + len(conflict_watch)
    score = _score(review_count, watch_count, ticker_memory_rows, source_conflict_rows, ticker_issue_rows)
    status = _status(review_count, watch_count, score)

    return {
        "ticker_source_quality_status": status,
        "ticker_source_quality_score": score,
        "ticker_memory_review_count": len(memory_review),
        "ticker_memory_watch_count": len(memory_watch),
        "ticker_issue_review_count": len(issue_review),
        "ticker_issue_watch_count": len(issue_watch),
        "source_conflict_review_count": len(conflict_review),
        "source_conflict_watch_count": len(conflict_watch),
        "ticker_review_tickers": _ticker_list(memory_review + issue_review),
        "source_conflict_review_tickers": _ticker_list(conflict_review),
        "source_conflict_watch_tickers": _ticker_list(conflict_watch),
        "ticker_source_review_tickers": _ticker_list(memory_review + issue_review + conflict_review),
        "ticker_source_watch_tickers": _ticker_list(memory_watch + issue_watch + conflict_watch),
        "ticker_source_interpretation": _interpretation(status, memory_review, issue_review, conflict_review, watch_count),
        "ticker_source_guardrail": _guardrail(status),
    }


def ticker_source_audit_rows(context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or build_ticker_source_audit_context()
    return [
        {
            "check": "Statut global",
            "status": context.get("ticker_source_quality_status", "UNKNOWN"),
            "value": f"{safe_float(context.get('ticker_source_quality_score')) or 0:.1f}/100",
            "interpretation": context.get("ticker_source_interpretation", "N/D"),
            "impact": context.get("ticker_source_guardrail", "N/D"),
        },
        {
            "check": "Tickers à revoir",
            "status": _count_status(context.get("ticker_memory_review_count"), context.get("ticker_issue_review_count")),
            "value": (
                f"mémoire={context.get('ticker_memory_review_count', 0)}; "
                f"issues={context.get('ticker_issue_review_count', 0)}"
            ),
            "interpretation": _list_or_none(context.get("ticker_review_tickers")),
            "impact": "À valider avant grosse décision si le ticker est dans le portefeuille ou dans la recommandation.",
        },
        {
            "check": "Contradictions prioritaires",
            "status": _count_status(context.get("source_conflict_review_count"), 0),
            "value": (
                f"review={context.get('source_conflict_review_count', 0)}; "
                f"watch={context.get('source_conflict_watch_count', 0)}"
            ),
            "interpretation": _list_or_none(context.get("source_conflict_review_tickers")),
            "impact": "Alerte de validation seulement; ne bloque pas automatiquement une allocation.",
        },
    ]


def _is_priority_memory_review(row: dict[str, Any]) -> bool:
    status = str(row.get("ticker_memory_status") or "").upper()
    source = str(row.get("source") or "").upper()
    return status in REVIEW_TICKER_STATUSES and source == "CORE_PORTFOLIO"


def _is_priority_memory_watch(row: dict[str, Any]) -> bool:
    status = str(row.get("ticker_memory_status") or "").upper()
    source = str(row.get("source") or "").upper()
    return status in WATCH_TICKER_STATUSES and source == "CORE_PORTFOLIO"


def _is_priority_ticker_issue(row: dict[str, Any]) -> bool:
    validation = str(row.get("ticker_validation_status") or "").upper()
    coverage = str(row.get("ticker_coverage_status") or "").upper()
    return validation in REVIEW_ISSUE_STATUSES or coverage in REVIEW_ISSUE_STATUSES


def _is_watch_ticker_issue(row: dict[str, Any]) -> bool:
    validation = str(row.get("ticker_validation_status") or "").upper()
    coverage = str(row.get("ticker_coverage_status") or "").upper()
    coverage_class = str(row.get("free_data_coverage_class") or "").upper()
    return (
        validation not in REVIEW_ISSUE_STATUSES
        and coverage not in REVIEW_ISSUE_STATUSES
        and (coverage in WATCH_ISSUE_STATUSES or coverage_class == "VALID_TICKER_POOR_FREE_COVERAGE")
    )


def _is_priority_conflict(row: dict[str, Any]) -> bool:
    universe = str(row.get("universe") or "").upper()
    severity = str(row.get("severity") or "").upper()
    count = safe_float(row.get("conflict_count")) or 0.0
    return universe == "CORE_PORTFOLIO" and severity in REVIEW_CONFLICT_SEVERITIES and count >= 3


def _is_watch_conflict(row: dict[str, Any]) -> bool:
    universe = str(row.get("universe") or "").upper()
    severity = str(row.get("severity") or "").upper()
    return universe == "CORE_PORTFOLIO" and severity in WATCH_CONFLICT_SEVERITIES


def _score(
    review_count: int,
    watch_count: int,
    ticker_memory_rows: list[dict[str, Any]],
    source_conflict_rows: list[dict[str, Any]],
    ticker_issue_rows: list[dict[str, Any]],
) -> float:
    if not ticker_memory_rows and not source_conflict_rows and not ticker_issue_rows:
        return 72.0
    penalty = min(35.0, review_count * 6.0 + watch_count * 1.5)
    return round(max(0.0, min(100.0, 92.0 - penalty)), 1)


def _status(review_count: int, watch_count: int, score: float) -> str:
    if review_count >= 3 or score < 65:
        return "REVIEW"
    if review_count > 0 or watch_count > 0 or score < 82:
        return "WATCH"
    return "OK"


def _interpretation(
    status: str,
    memory_review: list[dict[str, Any]],
    issue_review: list[dict[str, Any]],
    conflict_review: list[dict[str, Any]],
    watch_count: int,
) -> str:
    if status == "REVIEW":
        tickers = _ticker_list(memory_review + issue_review + conflict_review)
        return f"Validation prioritaire recommandée sur {tickers or 'certains titres'} avant une grosse décision."
    if status == "WATCH":
        return f"{watch_count} alerte(s) ticker/source à surveiller; aucune ne devrait déclencher une correction automatique seule."
    if status == "OK":
        return "Aucun problème prioritaire de ticker ou contradiction de source détecté."
    return "Données insuffisantes pour juger."


def _guardrail(status: str) -> str:
    if status == "REVIEW":
        return "Réduit très légèrement la qualité de preuve de l’audit; ne bloque pas l’allocation ni le tuning SAFE."
    if status == "WATCH":
        return "Informe l’audit sans modifier la recommandation."
    return "Aucun impact."


def _count_status(value_a: Any, value_b: Any) -> str:
    total = int(safe_float(value_a) or 0) + int(safe_float(value_b) or 0)
    if total >= 3:
        return "REVIEW"
    if total > 0:
        return "WATCH"
    return "OK"


def _ticker_list(rows: list[dict[str, Any]], limit: int = 8) -> str:
    tickers: list[str] = []
    for row in rows:
        ticker = str(row.get("ticker") or row.get("ticker_display") or row.get("resolved_ticker") or "").strip()
        if ticker and ticker not in tickers:
            tickers.append(ticker)
    return ", ".join(tickers[:limit])


def _list_or_none(value: Any) -> str:
    text = str(value or "").strip()
    return text or "Aucun titre prioritaire."
