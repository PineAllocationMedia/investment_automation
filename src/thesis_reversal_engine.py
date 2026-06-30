from __future__ import annotations

from typing import Any

from .utils import normalize_ticker, safe_float


THESIS_REVERSAL_COLUMNS = [
    "ticker",
    "ticker_display",
    "universe",
    "previous_thesis_status",
    "current_thesis_status",
    "thesis_reversal_status",
    "thesis_reversal_severity",
    "manual_review_priority",
    "conclusion_basis",
    "data_quality_driven",
    "score_contradiction_flag",
    "suggested_human_action",
    "allocation_impact",
    "reason_fr",
    "score_total_change",
    "conviction_score_change",
    "capital_allocation_score_change",
    "proof_score_status",
    "sell_validation_level",
    "data_reliability_level",
    "score_evidence_level",
    "source_conflict_profile",
    "history_reference_count",
    "history_reference_dates",
]

THESIS_RANK = {"BROKEN": 0, "WEAKENING": 1, "UNCERTAIN": 1, "INTACT": 3}
CORE_UNIVERSE_ORDER = {"CORE_PORTFOLIO": 0, "WATCHLIST": 1, "MARKET_SCANNER": 2, "DISCOVERY_IDEAS": 3}
CONFIRMED_SELL_VALIDATION_LEVELS = {"CONFIRMED_SELL_REVIEW", "CONFIRMED_TRIM_REVIEW"}
DATA_QUALITY_THESIS_REASONS = (
    "données",
    "donnees",
    "missing",
    "manquent",
    "incertain",
    "non confirm",
    "proxy",
    "fiabilité",
    "fraîcheur",
)
FUNDAMENTAL_REASON_TERMS = (
    "croissance",
    "eps",
    "moat",
    "marge",
    "rentabilité",
    "bilan",
    "dette",
    "déclin",
    "secteur",
    "fraude",
    "obsolète",
    "management",
    "cash",
    "dilution",
)


def build_thesis_reversal_audit_rows(
    analysis_groups: dict[str, dict[str, dict[str, Any]]],
    sell_validation_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build an audit-only thesis reversal table from already-computed pipeline data.

    This engine does not fetch external data and never changes allocation, sizing or
    sell decisions. It only classifies whether a change in thesis looks fundamental,
    data-quality-driven, mixed, or too young to interpret.
    """

    sell_validation_by_ticker = _sell_validation_by_ticker(sell_validation_rows or [])
    rows: list[dict[str, Any]] = []
    for universe, analyses in analysis_groups.items():
        for ticker, analysis in sorted(analyses.items()):
            row = _reversal_row(universe, ticker, analysis, sell_validation_by_ticker.get(normalize_ticker(ticker)))
            rows.append(row)
    return sorted(
        rows,
        key=lambda row: (
            -int(safe_float(row.get("thesis_reversal_severity")) or 0),
            CORE_UNIVERSE_ORDER.get(str(row.get("universe") or ""), 9),
            str(row.get("ticker") or ""),
        ),
    )


def compact_thesis_reversal_summary(rows: list[dict[str, Any]], limit: int = 5) -> str:
    """Return the one-line compact-report summary for thesis reversal alerts."""

    alerts = [
        row
        for row in rows
        if str(row.get("thesis_reversal_status") or "") in {"WATCH", "REVIEW", "BROKEN"}
    ]
    if not alerts:
        return "Thesis reversal: aucun renversement majeur détecté."
    shown = alerts[:limit]
    items = ", ".join(f"{row.get('ticker')}={row.get('thesis_reversal_status')}" for row in shown)
    suffix = f" (+{len(alerts) - limit})" if len(alerts) > limit else ""
    return (
        f"Thesis reversal: {items}{suffix}. Audit-only: aucune vente automatique; "
        "revue manuelle avant nouvel ajout si REVIEW/HIGH."
    )


def _reversal_row(
    universe: str,
    ticker: str,
    analysis: dict[str, Any],
    sell_validation: dict[str, Any] | None,
) -> dict[str, Any]:
    ticker = normalize_ticker(ticker or analysis.get("ticker"))
    current = str(analysis.get("thesis_status") or "").upper()
    previous = str(analysis.get("previous_thesis_status") or "").upper()
    history_count = int(safe_float(analysis.get("history_reference_count")) or 0)
    history_dates = _date_text(analysis.get("history_reference_dates"))
    data_quality_driven = _is_data_quality_driven(analysis, previous, current)
    fundamental_evidence = _has_confirmed_fundamental_evidence(analysis, sell_validation)
    score_contradiction = _score_contradiction(analysis, current)
    status, severity = _status_and_severity(previous, current, history_count, data_quality_driven, fundamental_evidence)
    conclusion_basis = _conclusion_basis(history_count, data_quality_driven, fundamental_evidence)
    priority = _manual_review_priority(status, severity, data_quality_driven, score_contradiction)
    reason = _reason_fr(
        analysis=analysis,
        previous=previous,
        current=current,
        status=status,
        severity=severity,
        history_count=history_count,
        data_quality_driven=data_quality_driven,
        fundamental_evidence=fundamental_evidence,
        score_contradiction=score_contradiction,
        sell_validation=sell_validation,
    )
    return {
        "ticker": ticker,
        "ticker_display": analysis.get("ticker_display") or ticker,
        "universe": universe,
        "previous_thesis_status": previous,
        "current_thesis_status": current,
        "thesis_reversal_status": status,
        "thesis_reversal_severity": severity,
        "manual_review_priority": priority,
        "conclusion_basis": conclusion_basis,
        "data_quality_driven": data_quality_driven,
        "score_contradiction_flag": score_contradiction,
        "suggested_human_action": _suggested_action(status, priority, data_quality_driven),
        "allocation_impact": "NONE_AUDIT_ONLY",
        "reason_fr": reason,
        "score_total_change": analysis.get("score_total_change"),
        "conviction_score_change": analysis.get("conviction_score_change"),
        "capital_allocation_score_change": analysis.get("capital_allocation_score_change"),
        "proof_score_status": analysis.get("score_evidence_level"),
        "sell_validation_level": (sell_validation or {}).get("validation_level", ""),
        "data_reliability_level": analysis.get("data_reliability_level"),
        "score_evidence_level": analysis.get("score_evidence_level"),
        "source_conflict_profile": analysis.get("official_conflict_profile"),
        "history_reference_count": history_count,
        "history_reference_dates": history_dates,
    }


def _status_and_severity(
    previous: str,
    current: str,
    history_count: int,
    data_quality_driven: bool,
    fundamental_evidence: bool,
) -> tuple[str, int]:
    if history_count <= 0 or not previous:
        return "NONE", 0
    if previous == current:
        return "NONE", 0
    if previous == "INTACT" and current == "INTACT":
        return "NONE", 0
    if previous == "WEAKENING" and current == "INTACT":
        return "NONE", 0
    if previous == "INTACT" and current == "UNCERTAIN":
        return "WATCH", 1
    if previous == "INTACT" and current == "WEAKENING":
        return ("WATCH", 1) if data_quality_driven and not fundamental_evidence else ("REVIEW", 2)
    if previous == "INTACT" and current == "BROKEN":
        return "BROKEN", 3
    if previous == "WEAKENING" and current == "BROKEN":
        return ("BROKEN", 3) if fundamental_evidence and not data_quality_driven else ("REVIEW", 2)
    if _deteriorated(previous, current):
        return ("WATCH", 1) if data_quality_driven and not fundamental_evidence else ("REVIEW", 2)
    return "NONE", 0


def _is_data_quality_driven(analysis: dict[str, Any], previous: str, current: str) -> bool:
    reliability = str(analysis.get("data_reliability_level") or "").upper()
    data_quality = str(analysis.get("data_quality") or "").upper()
    evidence = str(analysis.get("score_evidence_level") or "").upper()
    dependency = str(analysis.get("auto_estimate_dependency") or "").upper()
    missing_count = safe_float(analysis.get("score_missing_data_count")) or 0.0
    missing_delta = safe_float(analysis.get("score_missing_data_count_change"))
    if missing_delta is None:
        previous_missing = safe_float(analysis.get("previous_score_missing_data_count"))
        if previous_missing is not None:
            missing_delta = missing_count - previous_missing
    conflict_weight = safe_float(analysis.get("official_weighted_conflict_score")) or 0.0
    directional_conflicts = int(safe_float(analysis.get("official_directional_conflict_count")) or 0)
    thesis_reasons = " ".join(_as_text_list(analysis.get("thesis_reasons"))).lower()

    if current == "UNCERTAIN":
        return True
    if reliability == "LOW" or data_quality == "LOW":
        return True
    if evidence in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"} or dependency == "HIGH":
        return True
    if missing_count >= 4 or (missing_delta is not None and missing_delta >= 2):
        return True
    if directional_conflicts > 0 or conflict_weight >= 1.5:
        return True
    if any(term in thesis_reasons for term in DATA_QUALITY_THESIS_REASONS):
        return True
    return previous == "INTACT" and current in {"WEAKENING", "BROKEN"} and not _has_strong_direct_evidence(analysis)


def _has_confirmed_fundamental_evidence(
    analysis: dict[str, Any],
    sell_validation: dict[str, Any] | None,
) -> bool:
    confirmed = _as_text_list(analysis.get("confirmed_fundamental_sell_signals"))
    if confirmed:
        return True
    validation_level = str((sell_validation or {}).get("validation_level") or "").upper()
    if validation_level in CONFIRMED_SELL_VALIDATION_LEVELS:
        return True
    thesis_reasons = " ".join(_as_text_list(analysis.get("fundamental_thesis_reasons") or analysis.get("thesis_reasons"))).lower()
    if any(term in thesis_reasons for term in FUNDAMENTAL_REASON_TERMS) and not any(
        term in thesis_reasons for term in DATA_QUALITY_THESIS_REASONS
    ):
        return True
    if str(analysis.get("cash_flow_quality_status") or "") in {"WEAK_CASH_CONVERSION", "CASH_FLOW_STRESS"}:
        return True
    if str(analysis.get("shareholder_discipline_status") or "") in {"HIGH_DILUTION_RISK"}:
        return True
    if analysis.get("moat_clear") is False or analysis.get("balance_sheet_strong") is False:
        return True
    return False


def _has_strong_direct_evidence(analysis: dict[str, Any]) -> bool:
    if _has_confirmed_fundamental_evidence(analysis, None):
        return True
    confirmed_fields = _as_text_list(analysis.get("confirmed_critical_fields"))
    research_fields = _as_text_list(analysis.get("research_report_fields"))
    official_fields = _as_text_list(analysis.get("official_confirmed_fields"))
    return len(set(confirmed_fields + research_fields + official_fields)) >= 4


def _score_contradiction(analysis: dict[str, Any], current: str) -> bool:
    if current not in {"WEAKENING", "BROKEN", "UNCERTAIN"}:
        return False
    score = safe_float(analysis.get("score_total")) or 0.0
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    allocation_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    return score >= 8.0 or conviction >= 75.0 or allocation_score >= 70.0


def _conclusion_basis(history_count: int, data_quality_driven: bool, fundamental_evidence: bool) -> str:
    if history_count <= 0:
        return "INSUFFICIENT_HISTORY"
    if data_quality_driven and fundamental_evidence:
        return "MIXED"
    if data_quality_driven:
        return "DATA_QUALITY_DRIVEN"
    if fundamental_evidence:
        return "FUNDAMENTAL"
    return "FUNDAMENTAL"


def _manual_review_priority(status: str, severity: int, data_quality_driven: bool, score_contradiction: bool) -> str:
    if status == "BROKEN" and severity >= 3:
        return "HIGH" if data_quality_driven else "CRITICAL"
    if status == "REVIEW":
        return "HIGH"
    if status == "WATCH":
        return "HIGH" if score_contradiction else "MEDIUM"
    return "LOW"


def _suggested_action(status: str, priority: str, data_quality_driven: bool) -> str:
    if status == "BROKEN":
        if data_quality_driven:
            return "Valider les données/sources avant de conclure; ne pas exécuter une vente automatique."
        return "Revue fondamentale prioritaire avant tout nouvel ajout ou décision de vente."
    if status == "REVIEW":
        return "Lire les preuves fondamentales et la check-list de vente; revue manuelle avant nouvel ajout."
    if status == "WATCH":
        return "Surveiller la prochaine analyse et combler les données si la position reçoit du capital."
    if priority != "LOW":
        return "Revue manuelle utile."
    return "Aucune action spécifique; conserver la discipline normale."


def _reason_fr(
    *,
    analysis: dict[str, Any],
    previous: str,
    current: str,
    status: str,
    severity: int,
    history_count: int,
    data_quality_driven: bool,
    fundamental_evidence: bool,
    score_contradiction: bool,
    sell_validation: dict[str, Any] | None,
) -> str:
    if history_count <= 0:
        return "Historique insuffisant: le moteur observe la thèse actuelle, mais ne conclut pas à un renversement."
    if status == "NONE":
        if previous == "WEAKENING" and current == "INTACT":
            return "La thèse semble s'améliorer par rapport à l'historique; audit-only, aucune action automatique."
        return "Aucun renversement majeur de thèse détecté par rapport à la référence historique."

    parts = [f"Thèse passée de {previous or 'N/D'} à {current or 'N/D'}; sévérité {severity}."]
    score_delta = safe_float(analysis.get("score_total_change"))
    conviction_delta = safe_float(analysis.get("conviction_score_change"))
    capital_delta = safe_float(analysis.get("capital_allocation_score_change"))
    changes = []
    if score_delta is not None:
        changes.append(f"score {score_delta:+.2f}")
    if conviction_delta is not None:
        changes.append(f"conviction {conviction_delta:+.1f}")
    if capital_delta is not None:
        changes.append(f"allocation_score {capital_delta:+.1f}")
    if changes:
        parts.append("Changements observés: " + ", ".join(changes) + ".")
    if fundamental_evidence:
        parts.append("Des preuves fondamentales ou de vente confirmée existent dans les signaux déjà calculés.")
    if data_quality_driven:
        parts.append("La conclusion semble surtout liée à la qualité, fraîcheur ou contradiction des données; validation manuelle avant conclusion forte.")
    if score_contradiction:
        parts.append("Contradiction: certains scores restent élevés malgré une thèse détériorée.")
    validation = str((sell_validation or {}).get("validation_level") or "")
    if validation:
        parts.append(f"Check-list vente: {validation}.")
    return " ".join(parts)


def _sell_validation_by_ticker(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = normalize_ticker(row.get("ticker"))
        if ticker:
            output[ticker] = row
    return output


def _deteriorated(previous: str, current: str) -> bool:
    return previous in THESIS_RANK and current in THESIS_RANK and THESIS_RANK[current] < THESIS_RANK[previous]


def _as_text_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text == "Aucun":
        return []
    separator = ";" if ";" in text else ","
    return [part.strip() for part in text.split(separator) if part.strip()]


def _date_text(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
