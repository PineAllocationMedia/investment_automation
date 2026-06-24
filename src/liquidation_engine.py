from __future__ import annotations

from typing import Any

from .benchmark_relevance_engine import benchmark_relevance_level
from .manual_inputs import CATASTROPHIC_COLUMNS
from .utils import safe_float


def compute_liquidation_status(
    manual: dict[str, Any],
    score: dict[str, Any],
    thesis_status: str,
    market: dict[str, Any],
    benchmark: dict[str, Any],
    reliability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reliability = reliability or {}
    extreme_reasons = [field for field in CATASTROPHIC_COLUMNS if manual.get(field) is True]
    if len(extreme_reasons) >= 3:
        urgent = manual.get("catastrophic_fraud") is True and (
            manual.get("catastrophic_dangerous_debt") is True
            or manual.get("catastrophic_destructive_management") is True
            or manual.get("catastrophic_growth_broken") is True
        )
        mechanical_signal = "LIQUIDATE_PROGRESSIVELY"
        recommended_action = "LIQUIDATE_URGENT_REVIEW" if urgent else "REVIEW_LIQUIDATE_PROGRESSIVELY"
        return {
            "liquidation_status": "RED",
            "sell_status": "RED",
            "fundamental_sell_status": "RED",
            "monitoring_status": "CRITICAL",
            "monitoring_decision": "URGENT_REVIEW",
            "monitoring_reasons": [],
            "liquidation_decision": recommended_action,
            "recommended_action": recommended_action,
            "sell_decision": recommended_action,
            "mechanical_sell_signal": mechanical_signal,
            "sell_review_required": True,
            "liquidation_reasons": [f"Condition extrême: {field}" for field in extreme_reasons],
            "signals_detected": [f"Condition extrême: {field}" for field in extreme_reasons],
            "confirmed_fundamental_sell_signals": [f"Condition extrême: {field}" for field in extreme_reasons],
            "weak_or_unconfirmed_sell_signals": [],
            "technical_or_valuation_signals": [],
            "sell_signal_strength": "CRITICAL_CONFIRMED",
            "sell_signal_source_summary": f"{len(extreme_reasons)} signal(aux) extrême(s) confirmé(s).",
            "sell_discipline": "Catastrophic confirmed signals.",
        }

    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    peg = safe_float(score.get("peg"))
    price_above_sma = market.get("price_above_sma_200")
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    benchmark_5y = safe_float(benchmark.get("benchmark_5y_cagr"))
    stock_return_1y = safe_float(market.get("stock_return_1y"))
    benchmark_return_1y = safe_float(benchmark.get("benchmark_return_1y"))
    underperformance = (
        stock_return_1y - benchmark_return_1y
        if stock_return_1y is not None and benchmark_return_1y is not None
        else None
    )

    confirmed_fundamental = _confirmed_fundamental_sell_signals(manual, score)
    unconfirmed_fundamental = _unconfirmed_fundamental_sell_signals(manual, score)
    technical_or_valuation = _technical_or_valuation_signals(
        score=score,
        thesis_status=thesis_status,
        market=market,
        benchmark=benchmark,
        benchmark_5y=benchmark_5y,
        underperformance=underperformance,
    )
    monitoring_signals = _dedupe(technical_or_valuation + unconfirmed_fundamental)
    monitoring = _monitoring_fields(monitoring_signals)
    signal_meta = _sell_signal_metadata(
        confirmed_fundamental,
        unconfirmed_fundamental,
        technical_or_valuation,
        "NONE",
        "GREEN" if thesis_status == "INTACT" and not confirmed_fundamental else "",
    )

    if thesis_status == "INTACT" and not confirmed_fundamental:
        return {
            "liquidation_status": "GREEN",
            "sell_status": "GREEN",
            "fundamental_sell_status": "GREEN",
            **monitoring,
            **signal_meta,
            "liquidation_decision": "HOLD",
            "recommended_action": "HOLD",
            "sell_decision": "HOLD",
            "mechanical_sell_signal": "NONE",
            "sell_review_required": False,
            "liquidation_reasons": ["Aucun signal de vente fondamental détecté."],
            "signals_detected": [],
            "confirmed_fundamental_sell_signals": [],
            "weak_or_unconfirmed_sell_signals": unconfirmed_fundamental,
            "technical_or_valuation_signals": technical_or_valuation,
            "sell_discipline": "Technical or valuation alerts are monitored separately and do not become sell signals by themselves.",
        }

    if _sell_data_is_confirmed(reliability) and len(confirmed_fundamental) >= 3:
        return _orange_result("REVIEW_TRIM_50", "TRIM_50", confirmed_fundamental, unconfirmed_fundamental, technical_or_valuation)
    if _sell_data_is_confirmed(reliability) and len(confirmed_fundamental) >= 2:
        return _orange_result("REVIEW_TRIM_25", "TRIM_25", confirmed_fundamental, unconfirmed_fundamental, technical_or_valuation)

    yellow_reasons = list(confirmed_fundamental)
    if thesis_status == "WEAKENING" and "Thèse en affaiblissement." not in yellow_reasons:
        yellow_reasons.append("Thèse en affaiblissement.")
    if thesis_status == "UNCERTAIN":
        yellow_reasons.append("Thèse incertaine.")
    if thesis_status != "INTACT":
        yellow_reasons.extend(unconfirmed_fundamental)
    if confirmed_fundamental and not _sell_data_is_confirmed(reliability):
        yellow_reasons.append("Validation manuelle requise avant toute vente: signaux fondamentaux surtout automatiques ou fiabilité insuffisante.")

    yellow_reasons = _dedupe(yellow_reasons)
    if yellow_reasons:
        return {
            "liquidation_status": "YELLOW",
            "sell_status": "YELLOW",
            "fundamental_sell_status": "YELLOW",
            **monitoring,
            **_sell_signal_metadata(confirmed_fundamental, unconfirmed_fundamental, technical_or_valuation, "NONE", "YELLOW"),
            "liquidation_decision": "WATCH",
            "recommended_action": "WATCH",
            "sell_decision": "WATCH",
            "mechanical_sell_signal": "NONE",
            "sell_review_required": False,
            "liquidation_reasons": yellow_reasons,
            "signals_detected": yellow_reasons,
            "confirmed_fundamental_sell_signals": confirmed_fundamental,
            "weak_or_unconfirmed_sell_signals": unconfirmed_fundamental,
            "technical_or_valuation_signals": technical_or_valuation,
            "sell_discipline": "Technical or unconfirmed signals can block additions, but cannot trigger trimming.",
        }

    final_status = "GREEN" if thesis_status == "INTACT" else "YELLOW"
    final_action = "HOLD" if final_status == "GREEN" else "DO_NOT_ADD"
    return {
        "liquidation_status": final_status,
        "sell_status": final_status,
        "fundamental_sell_status": final_status,
        **monitoring,
        **_sell_signal_metadata([], unconfirmed_fundamental, technical_or_valuation, "NONE", final_status),
        "liquidation_decision": final_action,
        "recommended_action": final_action,
        "sell_decision": final_action,
        "mechanical_sell_signal": "NONE",
        "sell_review_required": False,
        "liquidation_reasons": ["Aucun signal de vente automatique détecté."],
        "signals_detected": [] if final_status == "GREEN" else ["Thèse non intacte."],
        "confirmed_fundamental_sell_signals": [],
        "weak_or_unconfirmed_sell_signals": unconfirmed_fundamental,
        "technical_or_valuation_signals": technical_or_valuation,
        "sell_discipline": "Fallback status.",
    }


def apply_history_sell_discipline(analyses: dict[str, dict[str, Any]]) -> None:
    for analysis in analyses.values():
        if analysis.get("liquidation_status") in {"RED", "ORANGE"}:
            continue
        confirmed = analysis.get("confirmed_fundamental_sell_signals")
        if not isinstance(confirmed, list) or len(confirmed) != 1:
            continue
        if analysis.get("trend_status") != "DETERIORATING" or (safe_float(analysis.get("trend_severity")) or 0.0) < 2:
            continue
        if not _analysis_sell_data_is_confirmed(analysis):
            _append_signal(
                analysis,
                "Validation manuelle requise: 1 signal fondamental confirmé et tendance historique négative, mais fiabilité insuffisante pour recommander un trim.",
            )
            analysis["liquidation_status"] = "YELLOW"
            analysis["sell_status"] = "YELLOW"
            analysis["fundamental_sell_status"] = "YELLOW"
            analysis["recommended_action"] = "WATCH"
            analysis["sell_decision"] = "WATCH"
            analysis["liquidation_decision"] = "WATCH"
            analysis["mechanical_sell_signal"] = "NONE"
            analysis["sell_review_required"] = False
            analysis["sell_signal_strength"] = "UNCONFIRMED_WATCH"
            analysis["sell_signal_source_summary"] = "1 fondamental confirmé, mais données insuffisantes pour escalade mécanique."
            continue
        history_signal = "Détérioration répétée dans l’historique."
        reasons = list(confirmed)
        reasons.append(history_signal)
        analysis["liquidation_status"] = "ORANGE"
        analysis["sell_status"] = "ORANGE"
        analysis["fundamental_sell_status"] = "ORANGE"
        analysis["liquidation_decision"] = "REVIEW_TRIM_25"
        analysis["recommended_action"] = "REVIEW_TRIM_25"
        analysis["sell_decision"] = "REVIEW_TRIM_25"
        analysis["mechanical_sell_signal"] = "TRIM_25"
        analysis["sell_review_required"] = True
        analysis["sell_signal_strength"] = "CONFIRMED_TRIM_REVIEW"
        analysis["sell_signal_source_summary"] = "1 fondamental confirmé + détérioration historique répétée."
        analysis["liquidation_reasons"] = reasons
        analysis["signals_detected"] = reasons + list(analysis.get("technical_or_valuation_signals") or [])
        analysis["sell_discipline"] = "1 confirmed fundamental signal plus repeated historical deterioration."


def _confirmed_fundamental_sell_signals(manual: dict[str, Any], score: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    serious_growth_floor = safe_float(score.get("profile_serious_growth_floor")) or 5.0

    if eps_est is not None and eps_est < serious_growth_floor and _field_confirmed(manual, "eps_growth_estimated_3_5y"):
        signals.append(f"Fondamental confirmé: EPS estimé 3-5 ans sous le seuil sérieux du profil ({serious_growth_floor:.0f} %).")
    if manual.get("margin_or_profitability_under_pressure") is True and _field_confirmed(manual, "margin_or_profitability_under_pressure"):
        signals.append("Fondamental confirmé: marge ou rentabilité sous forte pression.")
    if manual.get("moat_clear") is False and _field_confirmed(manual, "moat_clear"):
        signals.append("Fondamental confirmé: moat affaibli ou absent.")
    if manual.get("balance_sheet_strong") is False and _field_confirmed(manual, "balance_sheet_strong"):
        signals.append("Fondamental confirmé: bilan financier affaibli.")
    if manual.get("forward_pe_growth_acceptable") is False and _field_confirmed(manual, "forward_pe_growth_acceptable"):
        signals.append("Fondamental confirmé: Forward P/E non acceptable selon la croissance.")
    if sector_cagr is not None and sector_cagr < 0 and _field_confirmed(manual, "sector_cagr_estimated"):
        signals.append("Fondamental confirmé: secteur en déclin structurel.")
    return signals


def _unconfirmed_fundamental_sell_signals(manual: dict[str, Any], score: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    serious_growth_floor = safe_float(score.get("profile_serious_growth_floor")) or 5.0

    if eps_est is not None and eps_est < serious_growth_floor and not _field_confirmed(manual, "eps_growth_estimated_3_5y"):
        signals.append(f"Validation manuelle requise: EPS estimé sous le seuil sérieux du profil ({serious_growth_floor:.0f} %), mais donnée non confirmée.")
    if manual.get("margin_or_profitability_under_pressure") is True and not _field_confirmed(manual, "margin_or_profitability_under_pressure"):
        signals.append("Validation manuelle requise: pression sur marge détectée, mais donnée non confirmée.")
    if manual.get("moat_clear") is False and not _field_confirmed(manual, "moat_clear"):
        signals.append("Validation manuelle requise: moat affaibli détecté, mais donnée non confirmée.")
    if manual.get("balance_sheet_strong") is False and not _field_confirmed(manual, "balance_sheet_strong"):
        signals.append("Validation manuelle requise: bilan affaibli détecté, mais donnée non confirmée.")
    if manual.get("forward_pe_growth_acceptable") is False and not _field_confirmed(manual, "forward_pe_growth_acceptable"):
        signals.append("Validation manuelle requise: Forward P/E possiblement non acceptable, mais donnée non confirmée.")
    if sector_cagr is not None and sector_cagr < 0 and not _field_confirmed(manual, "sector_cagr_estimated"):
        signals.append("Validation manuelle requise: secteur possiblement en déclin, mais donnée non confirmée.")
    return signals


def _technical_or_valuation_signals(
    score: dict[str, Any],
    thesis_status: str,
    market: dict[str, Any],
    benchmark: dict[str, Any],
    benchmark_5y: float | None,
    underperformance: float | None,
) -> list[str]:
    signals: list[str] = []
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    peg = safe_float(score.get("peg"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    relevance = benchmark_relevance_level(benchmark)
    weak_growth_threshold = safe_float(score.get("profile_weak_growth_threshold")) or 10.0
    sector_threshold = safe_float(score.get("profile_sector_cagr_threshold")) or 8.0
    peg_limit = safe_float(score.get("profile_peg_limit")) or 2.0

    if eps_est is not None and 0 < eps_est < weak_growth_threshold:
        signals.append(f"Alerte: EPS estimé positif mais sous le seuil du profil ({weak_growth_threshold:.0f} %).")
    if peg is not None and peg > peg_limit + 1.0:
        signals.append(f"Alerte valorisation: PEG > limite profil + 1.0 ({peg_limit + 1.0:.1f}).")
    elif peg is not None and peg > peg_limit + 0.5:
        signals.append(f"Alerte valorisation: PEG > limite profil + 0.5 ({peg_limit + 0.5:.1f}).")
    if market.get("price_above_sma_200") is False:
        signals.append("Alerte technique: prix sous SMA 200.")
    if underperformance is not None:
        if relevance == "LOW":
            if underperformance <= -0.35 and market.get("price_above_sma_200") is False:
                signals.append("Alerte marché large: forte sous-performance malgré benchmark de faible pertinence.")
        elif underperformance <= -0.25:
            signals.append(f"Alerte marché: sous-performance importante vs ETF sur 1 an (pertinence {relevance}).")
    if sector_cagr is not None and 0 <= sector_cagr < sector_threshold:
        signals.append(f"Alerte: secteur sous le seuil du profil ({sector_threshold:.0f} %).")
    if benchmark_5y is not None and benchmark_5y < 0 and relevance != "LOW":
        signals.append(f"Alerte: ETF de comparaison négatif sur 5 ans (pertinence {relevance}).")
    if thesis_status == "WEAKENING":
        signals.append("Thèse en affaiblissement.")
    if int(score.get("score_missing_data_count") or 0) >= 3:
        signals.append("Données importantes incertaines.")
    return _dedupe(signals)


def _orange_result(
    action: str,
    mechanical_signal: str,
    confirmed_fundamental: list[str],
    weak_or_unconfirmed: list[str],
    technical_or_valuation: list[str],
) -> dict[str, Any]:
    return {
        "liquidation_status": "ORANGE",
        "sell_status": "ORANGE",
        "fundamental_sell_status": "ORANGE",
        **_monitoring_fields(technical_or_valuation),
        **_sell_signal_metadata(confirmed_fundamental, weak_or_unconfirmed, technical_or_valuation, mechanical_signal, "ORANGE"),
        "liquidation_decision": action,
        "recommended_action": action,
        "sell_decision": action,
        "mechanical_sell_signal": mechanical_signal,
        "sell_review_required": True,
        "liquidation_reasons": confirmed_fundamental,
        "signals_detected": confirmed_fundamental + technical_or_valuation,
        "confirmed_fundamental_sell_signals": confirmed_fundamental,
        "weak_or_unconfirmed_sell_signals": weak_or_unconfirmed,
        "technical_or_valuation_signals": technical_or_valuation,
        "sell_discipline": "Trim requires confirmed fundamental deterioration, not technical weakness alone.",
    }


def _sell_signal_metadata(
    confirmed_fundamental: list[str],
    weak_or_unconfirmed: list[str],
    technical_or_valuation: list[str],
    mechanical_signal: str,
    status: str,
) -> dict[str, Any]:
    if mechanical_signal in {"TRIM_25", "TRIM_50"}:
        strength = "CONFIRMED_TRIM_REVIEW"
    elif status == "RED":
        strength = "CRITICAL_CONFIRMED"
    elif confirmed_fundamental:
        strength = "CONFIRMED_WATCH_ONLY"
    elif weak_or_unconfirmed:
        strength = "UNCONFIRMED_WATCH"
    elif technical_or_valuation:
        strength = "TECHNICAL_VALUATION_WATCH"
    else:
        strength = "NO_SELL_SIGNAL"
    return {
        "sell_signal_strength": strength,
        "sell_signal_source_summary": (
            f"{len(confirmed_fundamental)} fondamental confirmé; "
            f"{len(weak_or_unconfirmed)} faible/non confirmé; "
            f"{len(technical_or_valuation)} technique/valorisation."
        ),
    }


def _monitoring_fields(signals: list[str]) -> dict[str, Any]:
    if not signals:
        return {
            "monitoring_status": "NORMAL",
            "monitoring_decision": "NONE",
            "monitoring_reasons": [],
        }
    if any("Validation manuelle requise" in signal or "Données importantes incertaines" in signal for signal in signals):
        return {
            "monitoring_status": "MANUAL_REVIEW",
            "monitoring_decision": "MANUAL_REVIEW_BEFORE_ADD",
            "monitoring_reasons": signals,
        }
    return {
        "monitoring_status": "WATCH",
        "monitoring_decision": "WATCH_POSITION",
        "monitoring_reasons": signals,
    }


def _field_confirmed(manual: dict[str, Any], field: str) -> bool:
    manual_fields = _field_set(manual.get("manual_override_fields"))
    research_fields = _field_set(manual.get("research_report_fields"))
    auto_fields = _field_set(manual.get("auto_estimated_fields"))
    if field in manual_fields:
        return True
    if field in research_fields:
        return _research_field_confidence(manual, field) != "LOW"
    return field not in auto_fields


def _research_field_confidence(manual: dict[str, Any], field: str) -> str:
    values = manual.get("research_report_field_confidence") or {}
    if isinstance(values, dict):
        confidence = str(values.get(field) or "").strip().upper()
        return confidence or "MEDIUM"
    text = str(values or "")
    for part in text.replace(",", ";").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key.strip() == field:
            return str(value).strip().upper() or "MEDIUM"
    return "MEDIUM"


def _sell_data_is_confirmed(reliability: dict[str, Any]) -> bool:
    if not reliability:
        return True
    level = str(reliability.get("data_reliability_level") or "").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "").upper()
    return level == "HIGH" and dependency != "HIGH"


def _analysis_sell_data_is_confirmed(analysis: dict[str, Any]) -> bool:
    level = str(analysis.get("data_reliability_level") or "").upper()
    dependency = str(analysis.get("auto_estimate_dependency") or "").upper()
    if not level:
        return True
    return level == "HIGH" and dependency != "HIGH"


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}


def _append_signal(analysis: dict[str, Any], signal: str) -> None:
    signals = analysis.get("signals_detected")
    if not isinstance(signals, list):
        signals = []
    if signal not in signals:
        signals.append(signal)
    analysis["signals_detected"] = signals
    reasons = analysis.get("liquidation_reasons")
    if not isinstance(reasons, list):
        reasons = []
    if signal not in reasons:
        reasons.append(signal)
    analysis["liquidation_reasons"] = reasons


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result
