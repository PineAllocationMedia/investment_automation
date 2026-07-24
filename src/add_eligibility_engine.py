from __future__ import annotations

from typing import Any

from .asset_type_engine import is_etf_asset_analysis
from .utils import safe_float


ADD_ALLOWED_STATUSES = {"ADD_ALLOWED", "ADD_ALLOWED_SMALL"}


def compute_add_eligibility_status(analysis: dict[str, Any]) -> dict[str, Any]:
    ticker = analysis.get("ticker")
    if ticker == "VFV.TO" or analysis.get("benchmark_role") is True:
        return {
            "add_eligibility_status": "BENCHMARK_FALLBACK",
            "add_eligibility_reason": "VFV.TO est le filet de sécurité et benchmark, pas une action à scorer.",
            "add_eligibility_size": "FALLBACK",
        }
    if is_etf_asset_analysis(analysis):
        return {
            "add_eligibility_status": "ETF_HOLD_ONLY",
            "add_eligibility_reason": "FNB/ETF: pas d’allocation automatique comme une action individuelle.",
            "add_eligibility_size": "NONE",
        }

    thesis_status = str(analysis.get("thesis_status") or "")
    liquidation_status = str(analysis.get("liquidation_status") or "")
    reliability_level = str(analysis.get("data_reliability_level") or "MEDIUM").upper()
    confirmed_fundamental = _as_list(analysis.get("confirmed_fundamental_sell_signals"))
    technical_or_valuation = _as_list(analysis.get("technical_or_valuation_signals"))
    original_monitoring_status = str(analysis.get("monitoring_status") or "NORMAL")
    monitoring_status = original_monitoring_status
    if monitoring_status == "NORMAL" and liquidation_status == "YELLOW" and technical_or_valuation and not confirmed_fundamental:
        monitoring_status = "MANUAL_REVIEW" if _has_unconfirmed_fundamental_warning(technical_or_valuation) else "WATCH"

    def status_result(status: str, reason: str, size: str) -> dict[str, Any]:
        result = _status(status, reason, size)
        if monitoring_status != original_monitoring_status:
            result["resolved_monitoring_status"] = monitoring_status
            result["monitoring_status"] = monitoring_status
        return result

    expected_quality = str(analysis.get("expected_cagr_quality") or "")
    conviction = safe_float(analysis.get("conviction_score")) or 0.0
    trend_status = str(analysis.get("trend_status") or "")
    trend_severity = safe_float(analysis.get("trend_severity")) or 0.0
    quality_drawdown_status = str(analysis.get("quality_drawdown_status") or "")
    quality_drawdown_score = safe_float(analysis.get("quality_drawdown_score")) or 0.0

    if thesis_status != "INTACT":
        return status_result("DO_NOT_ADD", "Thèse non intacte.", "NONE")
    if liquidation_status in {"ORANGE", "RED"}:
        return status_result("DO_NOT_ADD", f"Signal de vente {liquidation_status}.", "NONE")
    if confirmed_fundamental:
        return status_result("DO_NOT_ADD", "Signal fondamental confirmé; ne pas renforcer.", "NONE")
    if reliability_level == "LOW":
        return status_result("DO_NOT_ADD", "Fiabilité des données trop faible.", "NONE")
    if trend_status == "DETERIORATING" and trend_severity >= 2:
        return status_result("DO_NOT_ADD", "Détérioration répétée dans l’historique.", "NONE")

    if monitoring_status == "MANUAL_REVIEW":
        monitoring_reasons = _as_list(analysis.get("monitoring_reasons"))
        if monitoring_reasons:
            monitoring_reason_text = " | ".join(monitoring_reasons)
            add_reason = f"Alerte de surveillance à valider manuellement avant ajout : {monitoring_reason_text}"
        else:
            add_reason = "Alerte de surveillance à valider manuellement avant ajout."
        return status_result("RESEARCH_REPORT_REQUIRED_BEFORE_ADD", add_reason, "NONE")
    if monitoring_status == "WATCH":
        if _has_unconfirmed_fundamental_warning(technical_or_valuation):
            return status_result("RESEARCH_REPORT_REQUIRED_BEFORE_ADD", "Alerte fondamentale non confirmée; validation manuelle avant ajout.", "NONE")
        if (
            quality_drawdown_status == "QUALITY_DRAWDOWN_OPPORTUNITY"
            and quality_drawdown_score >= 75
            and conviction >= 80
            and expected_quality in {"MEDIUM", "HIGH", "VERY_HIGH"}
        ):
            return status_result(
                "ADD_ALLOWED_SMALL",
                "Quality drawdown: la baisse est traitée comme opportunité potentielle car la thèse et la qualité restent solides; achat limité seulement.",
                "LIMITED",
            )
        if expected_quality in {"HIGH", "VERY_HIGH"} and conviction >= 75:
            return status_result(
                "ADD_ALLOWED_SMALL",
                "Surveillance technique/valorisation seulement: petite allocation permise si le sizing et VFV restent favorables.",
                "LIMITED",
            )
        return status_result("DO_NOT_ADD", "Surveillance active sans qualité CAGR/conviction suffisante pour renforcer.", "NONE")

    if liquidation_status == "GREEN":
        return status_result("ADD_ALLOWED", "Thèse intacte, aucun signal de vente et garde-fous respectés.", "NORMAL")

    if liquidation_status == "YELLOW":
        return status_result("DO_NOT_ADD", "Signal de vente fondamental à surveiller; ne pas renforcer.", "NONE")

    return status_result("DO_NOT_ADD", "Statut d’achat non admissible par prudence.", "NONE")


def is_add_allowed(analysis: dict[str, Any]) -> bool:
    return str(analysis.get("add_eligibility_status") or "") in ADD_ALLOWED_STATUSES


def _status(status: str, reason: str, size: str) -> dict[str, Any]:
    return {
        "add_eligibility_status": status,
        "add_eligibility_reason": reason,
        "add_eligibility_size": size,
    }


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace(";", ",").split(",") if part.strip() and part.strip() != "Aucun"]
    return [str(part).strip() for part in value if str(part).strip()]


def _has_unconfirmed_fundamental_warning(signals: list[str]) -> bool:
    return any("Validation manuelle requise" in signal for signal in signals)
