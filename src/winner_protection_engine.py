from __future__ import annotations

from typing import Any

from .utils import safe_float


WINNER_PROTECTION_COLUMNS = [
    "ticker",
    "shares",
    "average_cost",
    "average_cost_currency",
    "average_cost_cad",
    "acquisition_value",
    "acquisition_value_currency",
    "acquisition_value_cad",
    "current_value",
    "current_value_currency",
    "quote_currency",
    "quote_to_cad_rate",
    "current_price_cad",
    "unrealized_gain_amount",
    "unrealized_gain_percent",
    "personal_high_price",
    "drawdown_from_personal_high",
    "winner_protection_status",
    "winner_protection_action",
    "winner_protection_reason",
]


SELL_ACTIONS = {
    "REVIEW_TRIM_25",
    "REVIEW_TRIM_50",
    "REVIEW_LIQUIDATE_PROGRESSIVELY",
    "LIQUIDATE_URGENT_REVIEW",
}


def apply_winner_protection(
    analyses: dict[str, dict[str, Any]],
    previous_snapshot: dict[str, dict[str, Any]] | None = None,
) -> None:
    previous_snapshot = previous_snapshot or {}
    for ticker, analysis in analyses.items():
        if ticker == "VFV.TO" or analysis.get("benchmark_role") is True:
            continue
        result = compute_winner_protection(analysis, previous_snapshot.get(ticker))
        analysis.update(result)
        _apply_sell_overlay(analysis)


def compute_winner_protection(analysis: dict[str, Any], previous: dict[str, Any] | None = None) -> dict[str, Any]:
    current_price = safe_float(analysis.get("current_price"))
    current_price_cad = safe_float(analysis.get("current_price_cad"))
    quote_to_cad_rate = safe_float(analysis.get("quote_to_cad_rate"))
    if current_price_cad is None and current_price is not None:
        if str(analysis.get("quote_currency") or "").upper() == "CAD":
            current_price_cad = current_price
        elif quote_to_cad_rate is not None:
            current_price_cad = current_price * quote_to_cad_rate
    current_value = safe_float(analysis.get("current_value")) or 0.0
    shares = safe_float(analysis.get("shares")) or 0.0
    average_cost = safe_float(analysis.get("average_cost"))
    acquisition_value = safe_float(analysis.get("acquisition_value"))
    average_cost_cad = safe_float(analysis.get("average_cost_cad"))
    acquisition_value_cad = safe_float(analysis.get("acquisition_value_cad"))
    cost_currency = str(analysis.get("average_cost_currency") or analysis.get("acquisition_value_currency") or "CAD").upper()
    if average_cost_cad is None and average_cost is not None and cost_currency == "CAD":
        average_cost_cad = average_cost
    if acquisition_value_cad is None and acquisition_value is not None and cost_currency == "CAD":
        acquisition_value_cad = acquisition_value

    if acquisition_value is None and shares > 0 and average_cost is not None:
        acquisition_value = shares * average_cost
    if average_cost is None and shares > 0 and acquisition_value is not None:
        average_cost = acquisition_value / shares
    if acquisition_value_cad is None and shares > 0 and average_cost_cad is not None:
        acquisition_value_cad = shares * average_cost_cad
    if average_cost_cad is None and shares > 0 and acquisition_value_cad is not None:
        average_cost_cad = acquisition_value_cad / shares

    held_position = current_value > 0 or shares > 0
    previous_high = safe_float((previous or {}).get("personal_high_price"))
    personal_high = _max_present(previous_high, current_price) if held_position else None
    drawdown_from_high = current_price / personal_high - 1 if current_price is not None and personal_high else None
    gain_amount = current_value - acquisition_value_cad if acquisition_value_cad is not None and current_value > 0 else None
    gain_percent = _gain_percent(
        current_price_cad=current_price_cad,
        average_cost=average_cost_cad,
        current_value=current_value,
        acquisition_value=acquisition_value_cad,
    )

    base = {
        "shares": shares,
        "average_cost": average_cost,
        "average_cost_currency": analysis.get("average_cost_currency"),
        "average_cost_cad": average_cost_cad,
        "acquisition_value": acquisition_value,
        "acquisition_value_currency": analysis.get("acquisition_value_currency"),
        "acquisition_value_cad": acquisition_value_cad,
        "current_value_currency": analysis.get("current_value_currency"),
        "quote_currency": analysis.get("quote_currency"),
        "quote_to_cad_rate": quote_to_cad_rate,
        "current_price_cad": current_price_cad,
        "unrealized_gain_amount": round(gain_amount, 2) if gain_amount is not None else None,
        "unrealized_gain_percent": gain_percent,
        "personal_high_price": personal_high,
        "drawdown_from_personal_high": drawdown_from_high,
    }

    if not held_position:
        return {
            **base,
            **_result("NO_POSITION", "NONE", "Aucune position détenue; protection des winners non applicable.", []),
        }
    if gain_percent is None:
        return {
            **base,
            **_result(
                "NO_COST_DATA",
                "HOLD",
                "Coût d’acquisition absent; remplir average_cost et average_cost_currency pour activer la protection.",
                [],
            ),
        }

    winner_tier = _winner_tier(gain_percent)
    if winner_tier == "NOT_WINNER":
        return {
            **base,
            "winner_tier": winner_tier,
            **_result("NOT_A_WINNER", "HOLD", "La position n’est pas encore un winner important selon le coût fourni.", []),
        }

    deterioration = _deterioration_profile(analysis)
    signals = deterioration["signals"]
    status = "HOLD_RUN_WINNER"
    action = "HOLD_RUN_WINNER"
    reason = "Winner à laisser courir: gain accumulé et aucune détérioration suffisante pour vendre."

    if winner_tier == "MULTIBAGGER":
        watch_threshold = -0.35
        protect_threshold = -0.40
        trim25_threshold = -0.50
        trim50_threshold = -0.60
    elif winner_tier == "BIG_WINNER":
        watch_threshold = -0.30
        protect_threshold = -0.35
        trim25_threshold = -0.40
        trim50_threshold = -0.50
    else:
        watch_threshold = -0.25
        protect_threshold = -0.30
        trim25_threshold = -0.35
        trim50_threshold = -0.45

    if analysis.get("thesis_status") == "BROKEN" or analysis.get("liquidation_status") == "RED":
        status = "LIQUIDATE_WINNER_REVIEW"
        action = "LIQUIDATE_URGENT_REVIEW" if analysis.get("mechanical_sell_signal") == "LIQUIDATE_PROGRESSIVELY" else "REVIEW_LIQUIDATE_PROGRESSIVELY"
        reason = "Ancien winner avec thèse brisée ou signal rouge; revue de liquidation nécessaire."
    elif _le(drawdown_from_high, trim50_threshold) and deterioration["trim_allowed"] and deterioration["score"] >= 4:
        status = "TRIM_50_REVIEW"
        action = "REVIEW_TRIM_50"
        reason = f"Winner en drawdown sévère ({trim50_threshold:.0%}) avec détérioration confirmée; réduction de 50 % à valider manuellement."
    elif _le(drawdown_from_high, trim25_threshold) and deterioration["trim_allowed"] and deterioration["score"] >= 3:
        status = "TRIM_25_REVIEW"
        action = "REVIEW_TRIM_25"
        reason = f"Winner en drawdown important ({trim25_threshold:.0%}) avec détérioration confirmée; réduction de 25 % à valider manuellement."
    elif _le(drawdown_from_high, protect_threshold) and deterioration["score"] >= 2:
        status = "PROTECT_WINNER_REVIEW"
        action = "WATCH"
        reason = f"Winner en drawdown important ({protect_threshold:.0%}) avec signaux de détérioration, mais preuve insuffisante pour recommander un trim."
    elif _le(drawdown_from_high, watch_threshold):
        status = "WATCH_WINNER_PULLBACK"
        action = "WATCH"
        reason = f"Winner en correction importante ({watch_threshold:.0%}); surveiller, mais ne pas vendre sans détérioration fondamentale."

    return {
        **base,
        "winner_tier": winner_tier,
        "winner_protection_deterioration_score": deterioration["score"],
        "winner_protection_trim_allowed": deterioration["trim_allowed"],
        **_result(status, action, reason, signals),
    }


def winner_protection_rows(analyses: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for analysis in sorted(analyses.values(), key=lambda row: str(row.get("ticker"))):
        if analysis.get("benchmark_role") is True:
            continue
        rows.append({column: analysis.get(column) for column in WINNER_PROTECTION_COLUMNS})
    return rows


def _apply_sell_overlay(analysis: dict[str, Any]) -> None:
    action = analysis.get("winner_protection_action")
    status = analysis.get("winner_protection_status")
    signals = list(analysis.get("winner_protection_signals") or [])
    if status in {"WATCH_WINNER_PULLBACK", "PROTECT_WINNER_REVIEW"} and analysis.get("liquidation_status") == "GREEN":
        analysis["monitoring_status"] = "WATCH"
        analysis["monitoring_decision"] = "WATCH_WINNER"
        analysis["mechanical_sell_signal"] = "NONE"
        analysis["sell_review_required"] = False
        reasons = analysis.get("monitoring_reasons")
        if not isinstance(reasons, list):
            reasons = []
        reason = analysis.get("winner_protection_reason")
        if reason and reason not in reasons:
            reasons.append(reason)
        analysis["monitoring_reasons"] = reasons
        _append_signal(analysis, analysis.get("winner_protection_reason"))
        return

    if action not in SELL_ACTIONS:
        return
    if action in {"REVIEW_LIQUIDATE_PROGRESSIVELY", "LIQUIDATE_URGENT_REVIEW"}:
        analysis["liquidation_status"] = "RED"
        analysis["sell_status"] = "RED"
        analysis["fundamental_sell_status"] = "RED"
        mechanical_signal = "LIQUIDATE_PROGRESSIVELY"
    else:
        analysis["liquidation_status"] = "ORANGE"
        analysis["sell_status"] = "ORANGE"
        analysis["fundamental_sell_status"] = "ORANGE"
        mechanical_signal = "TRIM_50" if action == "REVIEW_TRIM_50" else "TRIM_25"
    analysis["liquidation_decision"] = action
    analysis["recommended_action"] = action
    analysis["sell_decision"] = action
    analysis["mechanical_sell_signal"] = mechanical_signal
    analysis["sell_review_required"] = True
    analysis["sell_discipline"] = "Winner protection: drawdown from personal high plus fundamental deterioration."
    _append_signal(analysis, analysis.get("winner_protection_reason"))
    for signal in signals:
        _append_signal(analysis, signal)


def _deterioration_profile(analysis: dict[str, Any]) -> dict[str, Any]:
    signals: list[str] = []
    score = 0
    confirmed = analysis.get("confirmed_fundamental_sell_signals") or []
    if not isinstance(confirmed, list):
        confirmed = [str(confirmed)]
    trend_severity = safe_float(analysis.get("trend_severity")) or 0.0

    thesis = str(analysis.get("thesis_status") or "")
    liquidation = str(analysis.get("liquidation_status") or "")
    if thesis == "BROKEN":
        score += 5
        signals.append("Thèse brisée.")
    elif thesis == "WEAKENING":
        score += 2
        signals.append("Thèse en affaiblissement.")
    elif thesis == "UNCERTAIN":
        score += 1
        signals.append("Thèse incertaine.")
    if liquidation == "RED":
        score += 5
        signals.append("Signal de liquidation rouge.")
    elif liquidation == "ORANGE":
        score += 3
        signals.append("Signal de réduction orange.")
    elif liquidation == "YELLOW":
        score += 1
        signals.append("Signal de surveillance jaune.")
    if analysis.get("trend_status") == "DETERIORATING":
        score += max(1, min(int(trend_severity), 3))
        signals.append("Détérioration historique détectée.")
    if (safe_float(analysis.get("score_total_change")) or 0.0) <= -1.0:
        score += 1
        signals.append("Score fondamental en baisse.")
    if (safe_float(analysis.get("conviction_score_change")) or 0.0) <= -10.0:
        score += 1
        signals.append("Conviction en baisse.")
    if (safe_float(analysis.get("capital_allocation_score_change")) or 0.0) <= -10.0:
        score += 1
        signals.append("Score d’allocation en baisse.")
    if confirmed:
        score += 2 * len(confirmed)
        signals.extend(str(item) for item in confirmed)

    trim_allowed = _sell_data_is_confirmed(analysis) and (
        bool(confirmed)
        or liquidation in {"ORANGE", "RED"}
        or (thesis == "WEAKENING" and analysis.get("trend_status") == "DETERIORATING" and trend_severity >= 2)
    )
    return {"score": score, "signals": _dedupe(signals), "trim_allowed": trim_allowed}


def _sell_data_is_confirmed(analysis: dict[str, Any]) -> bool:
    level = str(analysis.get("data_reliability_level") or "").upper()
    dependency = str(analysis.get("auto_estimate_dependency") or "").upper()
    if not level:
        return True
    return level == "HIGH" and dependency != "HIGH"


def _gain_percent(
    current_price_cad: float | None,
    average_cost: float | None,
    current_value: float,
    acquisition_value: float | None,
) -> float | None:
    if acquisition_value is not None and acquisition_value > 0 and current_value > 0:
        return current_value / acquisition_value - 1
    if current_price_cad is not None and average_cost is not None and average_cost > 0:
        return current_price_cad / average_cost - 1
    return None


def _winner_tier(gain_percent: float) -> str:
    if gain_percent >= 2.0:
        return "MULTIBAGGER"
    if gain_percent >= 1.0:
        return "BIG_WINNER"
    if gain_percent >= 0.30:
        return "WINNER"
    return "NOT_WINNER"


def _result(status: str, action: str, reason: str, signals: list[str]) -> dict[str, Any]:
    return {
        "winner_protection_status": status,
        "winner_protection_action": action,
        "winner_protection_reason": reason,
        "winner_protection_signals": signals,
    }


def _max_present(*values: float | None) -> float | None:
    present = [value for value in values if value is not None and value > 0]
    return max(present) if present else None


def _le(value: float | None, threshold: float) -> bool:
    return value is not None and value <= threshold


def _append_signal(analysis: dict[str, Any], signal: Any) -> None:
    text = str(signal or "").strip()
    if not text:
        return
    for field in ["signals_detected", "liquidation_reasons"]:
        values = analysis.get(field)
        if not isinstance(values, list):
            values = []
        if text not in values:
            values.append(text)
        analysis[field] = values


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in result:
            result.append(text)
    return result
