from __future__ import annotations

from typing import Any

from .utils import safe_float


SELL_VALIDATION_CHECKLIST_COLUMNS = [
    "ticker",
    "ticker_display",
    "sell_status",
    "sell_decision",
    "validation_level",
    "fundamental_evidence",
    "technical_or_valuation_context",
    "winner_protection_check",
    "historical_trend_check",
    "news_or_research_check",
    "data_quality_check",
    "tax_check",
    "manual_action_required",
    "checklist_summary",
]


ACTIVE_WINNER_STATUSES = {
    "WATCH_WINNER_PULLBACK",
    "PROTECT_WINNER_REVIEW",
    "TRIM_25_REVIEW",
    "TRIM_50_REVIEW",
    "LIQUIDATE_WINNER_REVIEW",
}


def sell_validation_checklist_rows(
    analyses: dict[str, dict[str, Any]],
    tax_report: list[dict[str, Any]] | None = None,
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    tax_warnings = _tax_warnings_by_ticker(tax_report or [])
    rows: list[dict[str, Any]] = []
    for row in sorted(analyses.values(), key=lambda item: str(item.get("ticker") or "")):
        if row.get("benchmark_role") is True or row.get("ticker") == "VFV.TO":
            continue
        if active_only and not _needs_validation_row(row):
            continue
        rows.append(_checklist_row(row, tax_warnings.get(str(row.get("ticker") or ""), [])))
    return rows


def _checklist_row(row: dict[str, Any], tax_warnings: list[str]) -> dict[str, Any]:
    confirmed = _as_list(row.get("confirmed_fundamental_sell_signals"))
    technical = _as_list(row.get("technical_or_valuation_signals"))
    monitoring = _as_list(row.get("monitoring_reasons"))
    sell_status = str(row.get("sell_status") or row.get("liquidation_status") or "GREEN")
    sell_decision = str(row.get("sell_decision") or row.get("recommended_action") or "HOLD")
    winner_status = str(row.get("winner_protection_status") or "NONE")
    winner_action = str(row.get("winner_protection_action") or "NONE")
    trend = str(row.get("trend_status") or "STABLE")
    news_status = str(row.get("news_context_status") or "")
    research_sources = _as_list(row.get("research_report_sources"))
    reliability = safe_float(row.get("data_reliability_score"))
    missing_count = safe_float(row.get("score_missing_data_count")) or 0.0

    validation_level = _validation_level(row, confirmed, technical)
    manual_required = _manual_required(validation_level, row, tax_warnings)

    return {
        "ticker": row.get("ticker"),
        "ticker_display": row.get("ticker_display", row.get("ticker")),
        "sell_status": sell_status,
        "sell_decision": sell_decision,
        "validation_level": validation_level,
        "fundamental_evidence": _fundamental_evidence_text(confirmed, sell_status),
        "technical_or_valuation_context": _technical_context_text(technical, monitoring, confirmed),
        "winner_protection_check": _winner_text(winner_status, winner_action, row.get("winner_protection_reason")),
        "historical_trend_check": _trend_text(trend, row),
        "news_or_research_check": _news_research_text(news_status, research_sources, row),
        "data_quality_check": _data_text(reliability, missing_count, row),
        "tax_check": _tax_text(tax_warnings),
        "manual_action_required": "YES" if manual_required else "NO",
        "checklist_summary": _summary_text(validation_level, sell_status, sell_decision),
    }


def _needs_validation_row(row: dict[str, Any]) -> bool:
    sell_status = str(row.get("sell_status") or row.get("liquidation_status") or "GREEN")
    winner_status = str(row.get("winner_protection_status") or "")
    sell_decision = str(row.get("sell_decision") or row.get("recommended_action") or "")
    if sell_status in {"YELLOW", "ORANGE", "RED"}:
        return True
    if winner_status in ACTIVE_WINNER_STATUSES:
        return True
    if sell_decision in {"REVIEW_TRIM_25", "REVIEW_TRIM_50", "REVIEW_LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW"}:
        return True
    return False


def _validation_level(row: dict[str, Any], confirmed: list[str], technical: list[str]) -> str:
    sell_status = str(row.get("sell_status") or row.get("liquidation_status") or "GREEN")
    mechanical = str(row.get("mechanical_sell_signal") or "NONE")
    thesis = str(row.get("thesis_status") or "")
    winner_status = str(row.get("winner_protection_status") or "")
    monitoring = str(row.get("monitoring_status") or "NORMAL")

    if sell_status == "RED" and (len(confirmed) >= 3 or thesis == "BROKEN"):
        return "CONFIRMED_SELL_REVIEW"
    if sell_status == "ORANGE" and len(confirmed) >= 2:
        return "CONFIRMED_TRIM_REVIEW"
    if mechanical in {"TRIM_25", "TRIM_50", "LIQUIDATE_PROGRESSIVELY"}:
        return "MANUAL_CONFIRMATION_REQUIRED"
    if sell_status in {"ORANGE", "RED"}:
        return "MANUAL_CONFIRMATION_REQUIRED"
    if sell_status == "YELLOW" or winner_status in ACTIVE_WINNER_STATUSES or technical or monitoring not in {"", "NORMAL", "BENCHMARK"}:
        return "WATCH_ONLY_NO_SELL"
    return "NO_SELL_SIGNAL"


def _manual_required(validation_level: str, row: dict[str, Any], tax_warnings: list[str]) -> bool:
    if validation_level in {"CONFIRMED_SELL_REVIEW", "CONFIRMED_TRIM_REVIEW", "MANUAL_CONFIRMATION_REQUIRED"}:
        return True
    if row.get("sell_review_required") is True:
        return True
    return bool(tax_warnings) and validation_level != "NO_SELL_SIGNAL"


def _fundamental_evidence_text(confirmed: list[str], sell_status: str) -> str:
    if confirmed:
        return f"Confirmée ({len(confirmed)}): {_short_list(confirmed)}"
    if sell_status in {"ORANGE", "RED"}:
        return "Non confirmée directement: revue manuelle obligatoire avant vente."
    return "Aucune preuve fondamentale de vente confirmée."


def _technical_context_text(technical: list[str], monitoring: list[str], confirmed: list[str]) -> str:
    signals = technical or monitoring
    if not signals:
        return "Aucun signal technique/valorisation majeur."
    prefix = "Contexte seulement" if not confirmed else "Contexte additionnel"
    return f"{prefix}: {_short_list(signals)}"


def _winner_text(status: str, action: str, reason: Any) -> str:
    if status in {"", "NONE", "NO_POSITION", "NOT_A_WINNER", "HOLD_RUN_WINNER"}:
        return "Aucune vente winner active."
    return f"{status}/{action}: {str(reason or 'validation requise')}"


def _trend_text(trend: str, row: dict[str, Any]) -> str:
    severity = safe_float(row.get("trend_severity")) or 0.0
    if trend == "DETERIORATING":
        return f"Détérioration historique détectée (sévérité {severity:.0f})."
    if trend in {"SOLIDIFYING", "DEVELOPING"}:
        return f"Tendance historique plutôt favorable: {trend}."
    return "Aucune détérioration historique majeure."


def _news_research_text(news_status: str, research_sources: list[str], row: dict[str, Any]) -> str:
    parts: list[str] = []
    if research_sources:
        parts.append("rapport local disponible")
    has_headlines = bool(row.get("news_context_headlines"))
    if has_headlines or news_status not in {"", "NOT_TRIGGERED", "NONE"}:
        label = "titres disponibles" if news_status in {"", "NOT_TRIGGERED", "NONE"} else news_status
        parts.append(f"nouvelles vérifiées ({label})")
    if parts:
        return "; ".join(parts)
    return "Aucun rapport/nouvelle dédié ne confirme une vente pour l’instant."


def _data_text(reliability: float | None, missing_count: float, row: dict[str, Any]) -> str:
    dependency = str(row.get("auto_estimate_dependency") or "")
    if reliability is not None and reliability < 60:
        return f"Fiabilité limitée ({reliability:.0f}/100): valider avant vente."
    if missing_count >= 3 or dependency == "HIGH":
        return "Données incomplètes ou très automatiques: valider avant vente."
    return "Données suffisantes pour l’analyse mécanique, mais décision finale manuelle."


def _tax_text(tax_warnings: list[str]) -> str:
    if not tax_warnings:
        return "Aucune alerte fiscale majeure détectée."
    return _short_list(tax_warnings)


def _summary_text(validation_level: str, sell_status: str, sell_decision: str) -> str:
    if validation_level == "CONFIRMED_SELL_REVIEW":
        return "Signal sérieux: vente/liquidation à valider avec preuves récentes avant exécution."
    if validation_level == "CONFIRMED_TRIM_REVIEW":
        return "Signal sérieux: réduction partielle à valider, pas une vente émotionnelle."
    if validation_level == "MANUAL_CONFIRMATION_REQUIRED":
        return "Signal mécanique présent, mais confirmation manuelle requise avant de vendre."
    if validation_level == "WATCH_ONLY_NO_SELL":
        return "Surveiller et ne pas renforcer; pas de vente automatique."
    if sell_status == "GREEN" and sell_decision == "HOLD":
        return "Aucun signal de vente."
    return "Aucun signal de vente confirmé."


def _tax_warnings_by_ticker(tax_report: list[dict[str, Any]]) -> dict[str, list[str]]:
    warnings: dict[str, list[str]] = {}
    for row in tax_report:
        ticker = str(row.get("ticker") or "")
        warning = str(row.get("warning") or "").strip()
        if ticker and warning and warning.lower() not in {"none", "aucun", "nan"}:
            warnings.setdefault(ticker, []).append(warning)
    return warnings


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text == "Aucun":
        return []
    separator = ";" if ";" in text else ","
    return [part.strip() for part in text.split(separator) if part.strip()]


def _short_list(values: list[str], limit: int = 2) -> str:
    selected = values[:limit]
    suffix = f" (+{len(values) - limit})" if len(values) > limit else ""
    return "; ".join(selected) + suffix
