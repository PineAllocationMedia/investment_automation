from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import read_csv_records, safe_float, today_iso, write_csv_records


ANOMALY_COLUMNS = [
    "date",
    "mode",
    "scope",
    "ticker",
    "anomaly_type",
    "severity",
    "metric",
    "current_value",
    "baseline_value",
    "change",
    "reason",
    "suggested_action",
    "requires_improvement_audit",
]

ANOMALY_HISTORY_COLUMNS = ANOMALY_COLUMNS

THESIS_RANK = {"BROKEN": 0, "WEAKENING": 1, "UNCERTAIN": 1, "INTACT": 3}
LIQUIDATION_RANK = {"RED": 0, "ORANGE": 1, "YELLOW": 2, "GREEN": 3}
QUALITY_RANK = {"UNCERTAIN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}
RELIABILITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "BENCHMARK": 3}
SEVERITY_RANK = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


def detect_analysis_anomalies(
    *,
    mode: str,
    analyses: dict[str, dict[str, Any]],
    watchlist_analyses: dict[str, dict[str, Any]] | None = None,
    market_analyses: dict[str, dict[str, Any]] | None = None,
    discovery_analyses: dict[str, dict[str, Any]] | None = None,
    allocation_result: dict[str, Any] | None = None,
    allocation_change_rows: list[dict[str, Any]] | None = None,
    portfolio_risk: dict[str, Any] | None = None,
    validation_priority_rows: list[dict[str, Any]] | None = None,
    date: str | None = None,
) -> list[dict[str, Any]]:
    """Flag unusual post-analysis movements without changing scores or allocations."""

    date = date or today_iso()
    allocation_result = allocation_result or {}
    allocation_change_rows = allocation_change_rows or []
    portfolio_risk = portfolio_risk or {}
    validation_priority_rows = validation_priority_rows or []
    groups = {
        "CORE_PORTFOLIO": analyses,
        "WATCHLIST": watchlist_analyses or {},
        "MARKET_SCANNER": market_analyses or {},
        "DISCOVERY_IDEAS": discovery_analyses or {},
    }
    allocation_map = _allocation_map(allocation_result)
    allocated_tickers = {ticker for ticker, row in allocation_map.items() if (safe_float(row.get("amount")) or 0.0) > 0}

    rows: list[dict[str, Any]] = []
    for universe, group in groups.items():
        for analysis in group.values():
            ticker = _ticker(analysis)
            if not ticker:
                continue
            is_allocated = ticker in allocated_tickers
            is_core = universe == "CORE_PORTFOLIO"
            is_actionable_external = str(analysis.get("promotion_status") or "") == "PROMOTE_TO_CORE_REVIEW"
            if not (is_core or is_allocated or is_actionable_external):
                continue
            rows.extend(_ticker_anomalies(date, mode, universe, ticker, analysis, is_allocated))

    rows.extend(_allocation_anomalies(date, mode, allocation_change_rows, allocation_map))
    rows.extend(_portfolio_risk_anomalies(date, mode, portfolio_risk))
    rows.extend(_validation_anomalies(date, mode, validation_priority_rows, allocated_tickers))
    rows.extend(_source_fallback_cluster_anomalies(date, mode, groups, allocated_tickers))
    rows = _dedupe_rows(rows)
    rows = _maybe_add_improvement_audit_row(date, mode, rows)
    if not rows:
        rows = [
            _row(
                date,
                mode,
                "GLOBAL",
                "",
                "NO_MAJOR_ANOMALY",
                "INFO",
                "global",
                "",
                "",
                "",
                "Aucune anomalie post-analyse majeure detectee pour ce mode.",
                "Continuer le workflow normal. Aucune action speciale n'est requise.",
                False,
            )
        ]
    return sorted(rows, key=_sort_key)


def update_anomaly_history(
    path: str | Path,
    rows: list[dict[str, Any]],
    *,
    mode: str,
    date: str | None = None,
    max_rows: int = 1200,
) -> list[dict[str, Any]]:
    path = Path(path)
    date = date or today_iso()
    stamped_rows = [{**row, "date": row.get("date") or date, "mode": row.get("mode") or mode} for row in rows]
    existing = read_csv_records(path)
    cleaned = [row for row in existing if not (row.get("date") == date and row.get("mode") == mode)]
    combined = [*cleaned, *stamped_rows][-max_rows:]
    write_csv_records(path, combined, ANOMALY_HISTORY_COLUMNS)
    return combined


def anomaly_summary(rows: list[dict[str, Any]]) -> str:
    actionable = [row for row in rows if row.get("anomaly_type") != "NO_MAJOR_ANOMALY"]
    if not actionable:
        return "Aucune anomalie majeure detectee."
    high = [row for row in actionable if row.get("severity") == "HIGH"]
    medium = [row for row in actionable if row.get("severity") == "MEDIUM"]
    audit_rows = [row for row in actionable if str(row.get("requires_improvement_audit")).lower() == "true"]
    audit_needed = len(high) >= 2 or len(audit_rows) >= 2
    base = f"{len(actionable)} signal(aux): {len(high)} HIGH, {len(medium)} MEDIUM."
    if audit_needed:
        return base + " Improvement-audit recommande si le signal persiste ou concerne l'allocation principale."
    return base + " A lire comme garde-fou, sans modifier automatiquement l'allocation."


def anomaly_rows_for_report(rows: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    selected = sorted(rows, key=_sort_key)
    if not selected:
        return []
    return [
        {
            "scope": row.get("scope"),
            "ticker": row.get("ticker"),
            "niveau": row.get("severity"),
            "signal": row.get("anomaly_type"),
            "metrique": row.get("metric"),
            "variation": row.get("change"),
            "lecture": row.get("reason"),
            "action": row.get("suggested_action"),
        }
        for row in selected[:limit]
    ]


def _ticker_anomalies(
    date: str,
    mode: str,
    universe: str,
    ticker: str,
    analysis: dict[str, Any],
    is_allocated: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    score_delta = safe_float(analysis.get("score_total_change"))
    conviction_delta = safe_float(analysis.get("conviction_score_change"))
    capital_delta = safe_float(analysis.get("capital_allocation_score_change"))
    prefix = "Titre recommande" if is_allocated else "Titre core/externe surveille"
    score_threshold = -1.0 if is_allocated else -1.5
    conviction_threshold = -12.0 if is_allocated else -18.0
    capital_threshold = -14.0 if is_allocated else -20.0

    if score_delta is not None and score_delta <= score_threshold:
        severity = "HIGH" if score_delta <= -2.0 and is_allocated else "MEDIUM"
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "SCORE_DROP",
                severity,
                "score_total",
                analysis.get("score_total"),
                analysis.get("previous_score_total"),
                score_delta,
                f"{prefix}: baisse inhabituelle du score fondamental vs historique du meme mode.",
                _audit_action(mode, "Verifier si la baisse vient des donnees, d'un rapport ajoute ou d'une vraie degradation."),
                severity == "HIGH",
            )
        )
    if conviction_delta is not None and conviction_delta <= conviction_threshold:
        severity = "HIGH" if conviction_delta <= -22.0 and is_allocated else "MEDIUM"
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "CONVICTION_DROP",
                severity,
                "conviction_score",
                analysis.get("conviction_score"),
                analysis.get("previous_conviction_score"),
                conviction_delta,
                f"{prefix}: chute de conviction plus forte que la fluctuation normale attendue.",
                _audit_action(mode, "Lire les raisons de score et les donnees a valider avant d'executer une grosse allocation."),
                severity == "HIGH",
            )
        )
    if capital_delta is not None and capital_delta <= capital_threshold:
        severity = "HIGH" if capital_delta <= -28.0 and is_allocated else "MEDIUM"
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "ALLOCATION_SCORE_DROP",
                severity,
                "capital_allocation_score",
                analysis.get("capital_allocation_score"),
                analysis.get("previous_capital_allocation_score"),
                capital_delta,
                f"{prefix}: le score d'allocation marginale a baisse fortement.",
                "Verifier les garde-fous recents: valuation, donnees, concentration, regime de marche et clusters.",
                severity == "HIGH",
            )
        )

    rows.extend(_status_anomalies(date, mode, universe, ticker, analysis, is_allocated))
    rows.extend(_data_quality_anomalies(date, mode, universe, ticker, analysis, is_allocated))
    rows.extend(_market_data_fallback_anomalies(date, mode, universe, ticker, analysis, is_allocated))
    return rows


def _status_anomalies(
    date: str,
    mode: str,
    universe: str,
    ticker: str,
    analysis: dict[str, Any],
    is_allocated: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric, rank, previous_key, current_key in [
        ("thesis_status", THESIS_RANK, "previous_thesis_status", "thesis_status"),
        ("liquidation_status", LIQUIDATION_RANK, "previous_liquidation_status", "liquidation_status"),
        ("expected_cagr_quality", QUALITY_RANK, "previous_expected_cagr_quality", "expected_cagr_quality"),
    ]:
        previous = str(analysis.get(previous_key) or "")
        current = str(analysis.get(current_key) or "")
        if not _rank_drop(previous, current, rank):
            continue
        severity = "HIGH" if is_allocated or current in {"BROKEN", "RED", "ORANGE"} else "MEDIUM"
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "STATUS_DEGRADATION",
                severity,
                metric,
                current,
                previous,
                "",
                f"Statut degrade de {previous or 'N/D'} a {current or 'N/D'}.",
                _audit_action(mode, "Verifier si c'est une vraie degradation fondamentale ou seulement un changement de source/donnee."),
                severity == "HIGH",
            )
        )
    return rows


def _data_quality_anomalies(
    date: str,
    mode: str,
    universe: str,
    ticker: str,
    analysis: dict[str, Any],
    is_allocated: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous = str(analysis.get("previous_data_reliability_level") or "")
    current = str(analysis.get("data_reliability_level") or "")
    if _rank_drop(previous, current, RELIABILITY_RANK):
        severity = "MEDIUM" if is_allocated else "LOW"
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "DATA_RELIABILITY_DROP",
                severity,
                "data_reliability_level",
                current,
                previous,
                "",
                "La fiabilite des donnees a baisse par rapport a l'historique.",
                "Valider les champs prioritaires avant d'augmenter fortement cette position.",
                False,
            )
        )
    if (
        analysis.get("requires_manual_validation_for_large_allocation") is True
        and is_allocated
        and str(analysis.get("ticker") or "") != "VFV.TO"
        and (
            str(analysis.get("data_reliability_level") or "") == "LOW"
            or str(analysis.get("auto_estimate_dependency") or "") == "HIGH"
            or str(analysis.get("score_evidence_level") or "") in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}
        )
    ):
        rows.append(
            _row(
                date,
                mode,
                universe,
                ticker,
                "ALLOCATED_WITH_MANUAL_VALIDATION_NEED",
                "MEDIUM",
                "requires_manual_validation_for_large_allocation",
                True,
                "",
                "",
                "Le titre recoit du capital, mais le modele demande une validation manuelle avant grosse allocation.",
                "Lire latest_validation_priority.csv ou chercher un rapport BNCD/Morningstar si le titre reste recommande.",
                False,
            )
        )
    return rows


def _market_data_fallback_anomalies(
    date: str,
    mode: str,
    universe: str,
    ticker: str,
    analysis: dict[str, Any],
    is_allocated: bool,
) -> list[dict[str, Any]]:
    status = str(analysis.get("market_data_fetch_status") or "")
    fallback_level = str(analysis.get("market_data_fallback_level") or "")
    freshness = str(analysis.get("market_data_freshness_level") or "")
    if not (status.startswith("FALLBACK") or fallback_level in {"STALE_CACHE", "LAST_KNOWN_GOOD"}):
        return []
    if _normalize_ticker(ticker) == "VFV.TO":
        return []
    if not is_allocated and freshness not in {"STALE", "VERY_STALE", "UNAVAILABLE"}:
        return []
    severity = "MEDIUM" if is_allocated or freshness in {"STALE", "VERY_STALE", "UNAVAILABLE"} else "LOW"
    return [
        _row(
            date,
            mode,
            universe,
            ticker,
            "MARKET_DATA_FALLBACK_USED",
            severity,
            "market_data_fetch_status",
            status,
            "LIVE_SUCCESS",
            "",
            "L'analyse a utilise un filet de secours de donnees de marche au lieu d'une source live.",
            "Relancer avec --refresh-market-data avant une grosse decision si ce signal reste present.",
            False,
        )
    ]


def _allocation_anomalies(
    date: str,
    mode: str,
    allocation_change_rows: list[dict[str, Any]],
    allocation_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    active_changes = [
        row
        for row in allocation_change_rows
        if row.get("change_status") not in {"STABLE", "NO_HISTORY", "NO_ALLOCATION_TO_COMPARE"}
    ]
    comparable = [
        row
        for row in allocation_change_rows
        if row.get("change_status") not in {"NO_HISTORY", "NO_ALLOCATION_TO_COMPARE"}
    ]
    if comparable and len(active_changes) >= max(3, int(len(comparable) * 0.55)):
        rows.append(
            _row(
                date,
                mode,
                "ALLOCATION",
                "",
                "ALLOCATION_CHURN",
                "MEDIUM",
                "changed_allocations",
                len(active_changes),
                len(comparable),
                "",
                "Plusieurs lignes d'allocation ont change par rapport aux dates distinctes precedentes du meme mode.",
                _audit_action(mode, "Verifier si le changement est explique par de nouvelles donnees ou par une instabilite du modele."),
                True,
            )
        )
    vfv_change = next((row for row in allocation_change_rows if str(row.get("ticker") or "") == "VFV.TO"), None)
    if vfv_change:
        delta = safe_float(vfv_change.get("change_amount"))
        current_pct = safe_float(vfv_change.get("current_percentage"))
        previous_pct = safe_float(vfv_change.get("previous_percentage"))
        if current_pct is not None and previous_pct is not None and abs(current_pct - previous_pct) >= 0.15:
            rows.append(
                _row(
                    date,
                    mode,
                    "ALLOCATION",
                    "VFV.TO",
                    "VFV_ALLOCATION_SWING",
                    "MEDIUM",
                    "vfv_percentage",
                    current_pct,
                    previous_pct,
                    round(current_pct - previous_pct, 4),
                    "La part VFV a bouge fortement vs l'historique du meme mode.",
                    "Verifier si la variation vient du score moyen, de redirections, de donnees manquantes ou de nouveaux garde-fous.",
                    False,
                )
            )
        elif delta is not None and abs(delta) >= max(75.0, _total_allocated(allocation_map) * 0.20):
            rows.append(
                _row(
                    date,
                    mode,
                    "ALLOCATION",
                    "VFV.TO",
                    "VFV_AMOUNT_SWING",
                    "LOW",
                    "vfv_amount",
                    vfv_change.get("current_amount"),
                    vfv_change.get("previous_amount"),
                    delta,
                    "Le montant VFV a bouge notablement, sans depasser le seuil de pourcentage critique.",
                    "Lire l'explication de changement d'allocation; aucune correction automatique.",
                    False,
                )
            )
    return rows


def _portfolio_risk_anomalies(date: str, mode: str, portfolio_risk: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    top3 = safe_float(portfolio_risk.get("top3_weight")) or 0.0
    tech = safe_float(portfolio_risk.get("tech_ai_semi_weight")) or 0.0
    usd = safe_float(portfolio_risk.get("usd_weight")) or 0.0
    if top3 >= 0.75:
        rows.append(_risk_row(date, mode, "TOP3_EXTREME", "top3_weight", top3, "Top 3 positions tres concentrees."))
    elif top3 >= 0.65:
        rows.append(_risk_row(date, mode, "TOP3_HIGH", "top3_weight", top3, "Top 3 positions concentrees."))
    if tech >= 0.60:
        rows.append(_risk_row(date, mode, "TECH_AI_SEMI_CLUSTER", "tech_ai_semi_weight", tech, "Cluster tech/IA/semi-conducteurs eleve."))
    if usd >= 0.90:
        rows.append(_risk_row(date, mode, "USD_EXTREME", "usd_weight", usd, "Exposition USD extreme."))
    return rows


def _validation_anomalies(
    date: str,
    mode: str,
    validation_priority_rows: list[dict[str, Any]],
    allocated_tickers: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    high_rows = [row for row in validation_priority_rows if str(row.get("priority") or "") in {"TRES_HAUTE", "HAUTE"}]
    allocated_high = [row for row in high_rows if _normalize_ticker(row.get("ticker")) in allocated_tickers]
    if len(allocated_high) >= 2:
        tickers = sorted({_normalize_ticker(row.get("ticker")) for row in allocated_high if _normalize_ticker(row.get("ticker"))})
        rows.append(
            _row(
                date,
                mode,
                "VALIDATION",
                ", ".join(tickers[:5]),
                "ALLOCATED_TICKERS_NEED_VALIDATION",
                "MEDIUM",
                "validation_priority_count",
                len(allocated_high),
                "",
                "",
                "Des titres recommandes ont plusieurs donnees prioritaires a valider.",
                "Lire latest_validation_priority.csv avant de transformer cette allocation en achat important.",
                False,
            )
        )
    elif len(high_rows) >= 8:
        rows.append(
            _row(
                date,
                mode,
                "VALIDATION",
                "",
                "HIGH_VALIDATION_LOAD",
                "LOW",
                "validation_priority_count",
                len(high_rows),
                "",
                "",
                "Beaucoup de validations prioritaires existent dans les univers suivis.",
                "Prioriser les titres core ou recommandes; ne pas chercher tous les rapports d'un coup.",
                False,
            )
        )
    return rows


def _source_fallback_cluster_anomalies(
    date: str,
    mode: str,
    groups: dict[str, dict[str, dict[str, Any]]],
    allocated_tickers: set[str],
) -> list[dict[str, Any]]:
    core_rows = list(groups.get("CORE_PORTFOLIO", {}).values())
    if not core_rows:
        return []
    fallback_rows = [
        row
        for row in core_rows
        if str(row.get("market_data_fetch_status") or "").startswith("FALLBACK")
        or str(row.get("market_data_fallback_level") or "") in {"STALE_CACHE", "LAST_KNOWN_GOOD"}
    ]
    allocated_fallback = [row for row in fallback_rows if _ticker(row) in allocated_tickers]
    fallback_rate = len(fallback_rows) / len(core_rows)
    if fallback_rate >= 0.35 or allocated_fallback:
        severity = "MEDIUM" if allocated_fallback else "LOW"
        return [
            _row(
                date,
                mode,
                "DATA",
                ", ".join(_ticker(row) for row in allocated_fallback[:5]) if allocated_fallback else "",
                "MARKET_DATA_FALLBACK_CLUSTER",
                severity,
                "fallback_rate_core",
                round(fallback_rate, 4),
                "",
                "",
                "Une part importante du core utilise un fallback de donnees de marche.",
                "Relancer avec --refresh-market-data plus tard; si le signal persiste, verifier la sante des sources.",
                False,
            )
        ]
    return []


def _maybe_add_improvement_audit_row(date: str, mode: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return rows
    high_count = sum(1 for row in rows if row.get("severity") == "HIGH")
    audit_rows = [row for row in rows if str(row.get("requires_improvement_audit")).lower() == "true"]
    if high_count >= 2 or len(audit_rows) >= 2:
        rows.append(
            _row(
                date,
                mode,
                "GLOBAL",
                "",
                "IMPROVEMENT_AUDIT_SUGGESTED",
                "MEDIUM",
                "anomaly_count",
                len(rows),
                "",
                "",
                "Plusieurs anomalies importantes apparaissent dans la meme analyse.",
                f"Si elles ne sont pas dues a une source temporairement indisponible, lancer: python3 main.py improvement-audit --period 12m --mode {mode}",
                True,
            )
        )
    return rows


def _risk_row(date: str, mode: str, anomaly_type: str, metric: str, current: float, reason: str) -> dict[str, Any]:
    return _row(
        date,
        mode,
        "PORTFOLIO_RISK",
        "",
        anomaly_type,
        "MEDIUM",
        metric,
        round(current, 4),
        "",
        "",
        reason,
        "Verifier que l'allocation ajoutee ne renforce pas inutilement ce risque cache.",
        False,
    )


def _row(
    date: str,
    mode: str,
    scope: str,
    ticker: str,
    anomaly_type: str,
    severity: str,
    metric: str,
    current_value: Any,
    baseline_value: Any,
    change: Any,
    reason: str,
    suggested_action: str,
    requires_improvement_audit: bool,
) -> dict[str, Any]:
    return {
        "date": date,
        "mode": mode,
        "scope": scope,
        "ticker": ticker,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "metric": metric,
        "current_value": current_value,
        "baseline_value": baseline_value,
        "change": change,
        "reason": reason,
        "suggested_action": suggested_action,
        "requires_improvement_audit": requires_improvement_audit,
    }


def _allocation_map(allocation_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in allocation_result.get("allocations") or []:
        ticker = _normalize_ticker(row.get("destination") or row.get("ticker"))
        if not ticker:
            continue
        output[ticker] = {
            "amount": safe_float(row.get("montant", row.get("amount"))) or 0.0,
            "percentage": safe_float(row.get("pourcentage", row.get("percentage"))) or 0.0,
        }
    return output


def _total_allocated(allocation_map: dict[str, dict[str, Any]]) -> float:
    return sum(safe_float(row.get("amount")) or 0.0 for row in allocation_map.values())


def _rank_drop(previous: str, current: str, ranks: dict[str, int]) -> bool:
    previous_key = str(previous or "").upper()
    current_key = str(current or "").upper()
    return previous_key in ranks and current_key in ranks and ranks[current_key] < ranks[previous_key]


def _audit_action(mode: str, first_step: str) -> str:
    return f"{first_step} Si le signal persiste: python3 main.py improvement-audit --period 12m --mode {mode}."


def _ticker(analysis: dict[str, Any]) -> str:
    return _normalize_ticker(analysis.get("ticker") or analysis.get("ticker_display"))


def _normalize_ticker(value: Any) -> str:
    return str(value or "").strip().upper()


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        key = (
            str(row.get("scope") or ""),
            str(row.get("ticker") or ""),
            str(row.get("anomaly_type") or ""),
            str(row.get("metric") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def _sort_key(row: dict[str, Any]) -> tuple[int, str, str]:
    return (-SEVERITY_RANK.get(str(row.get("severity") or "INFO"), 0), str(row.get("scope") or ""), str(row.get("ticker") or ""))
