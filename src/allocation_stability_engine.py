from __future__ import annotations

from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .model_tuning import tuning_value
from .utils import safe_float


POSITIVE_ALLOCATION_ACTIONS = {"BUY / ADD", "ADD_WITH_MONITORING"}
ELIGIBLE_ACTIONS = {"BUY / ADD", "ADD_WITH_MONITORING", "ELIGIBLE_BUT_NOT_SELECTED"}
CONTINUITY_CLOSE_SCORE_GAP = 6.0
CLEAR_NEW_LEADER_EDGE = 7.0
CHURN_PENALTY = -2.5
CONTINUITY_SUPPORT = 5.5


def apply_allocation_stability(analyses: dict[str, dict[str, Any]], mode: str = "rational-aggressive") -> None:
    base_results: dict[str, dict[str, Any]] = {}
    for analysis in analyses.values():
        if analysis.get("ticker") == "VFV.TO" or analysis.get("benchmark_role") is True:
            continue
        result = compute_allocation_stability(analysis, mode=mode)
        analysis.update(result)
        base_results[str(analysis.get("ticker") or "")] = result
    _apply_group_switching_discipline(analyses, base_results, mode=mode)


def compute_allocation_stability(analysis: dict[str, Any], mode: str = "rational-aggressive") -> dict[str, Any]:
    current_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
    previous_score = safe_float(analysis.get("previous_capital_allocation_score"))
    previous_allocation = str(analysis.get("previous_allocation_decision") or "")
    previous_final_action = str(analysis.get("previous_final_position_action") or "")
    trend_status = str(analysis.get("trend_status") or "")
    trend_severity = safe_float(analysis.get("trend_severity")) or 0.0

    current_addable = _currently_addable(analysis)
    if not current_addable:
        return _result(
            "RESET_IF_NOT_ADDABLE",
            -4.0 if previous_allocation in POSITIVE_ALLOCATION_ACTIONS else 0.0,
            "Aucune ancre de stabilité: le titre n’est plus admissible à une cotisation.",
            current_score,
            previous_score,
        )

    if trend_status == "DETERIORATING":
        adjustment = -8.0 if trend_severity >= 2 else -4.0
        return _result(
            "REDUCE_ON_DETERIORATION",
            adjustment,
            "Stabilité volontairement réduite: détérioration détectée par rapport aux analyses précédentes.",
            current_score,
            previous_score,
        )

    if previous_allocation in POSITIVE_ALLOCATION_ACTIONS or previous_final_action in POSITIVE_ALLOCATION_ACTIONS:
        if previous_score is None:
            return _result(
                "SUPPORT_CONTINUITY",
                2.0 + _stability_tuning(mode),
                "Le titre recevait déjà une allocation et reste admissible; léger bonus de continuité.",
                current_score,
                previous_score,
            )
        score_delta = current_score - previous_score
        if score_delta >= 8:
            return _result(
                "LET_IMPROVEMENT_LEAD",
                1.0,
                "Le titre reste admissible et s’améliore; continuité conservée sans ancrage excessif.",
                current_score,
                previous_score,
            )
        if score_delta <= -10:
            return _result(
                "REDUCE_AFTER_SCORE_DROP",
                -3.0,
                "Le titre recevait une allocation, mais son score d’allocation a reculé nettement.",
                current_score,
                previous_score,
            )
        return _result(
            "SUPPORT_CONTINUITY",
            3.0 + _stability_tuning(mode),
            "Le titre recevait déjà une allocation et reste comparable; léger bonus anti-bruit.",
            current_score,
            previous_score,
        )

    if previous_allocation == "ELIGIBLE_BUT_NOT_SELECTED" or previous_final_action == "WATCH":
        if previous_score is not None and current_score >= previous_score + 8:
            return _result(
                "ALLOW_NEW_LEADER",
                1.0,
                "Le titre n’était pas sélectionné avant, mais l’amélioration est suffisante pour être considérée.",
                current_score,
                previous_score,
            )
        return _result(
            "NEUTRAL_WATCHED_NAME",
            0.5,
            "Titre déjà surveillé et encore admissible; mini bonus sans forcer l’allocation.",
            current_score,
            previous_score,
        )

    if previous_allocation in {"NO_NEW_ALLOCATION", "DO_NOT_ADD"}:
        if previous_score is not None and current_score >= previous_score + 10:
            return _result(
                "ALLOW_NEW_LEADER",
                1.0,
                "Le titre était exclu avant, mais l’amélioration actuelle est assez nette pour être détectée.",
                current_score,
                previous_score,
            )
        return _result(
            "NEUTRAL_PREVIOUSLY_EXCLUDED",
            0.0,
            "Ancienne exclusion: aucune stabilité artificielle appliquée.",
            current_score,
            previous_score,
        )

    return _result(
        "NEUTRAL_NO_HISTORY",
        0.0,
        "Aucune allocation historique exploitable: décision basée sur les règles actuelles.",
        current_score,
        previous_score,
    )


def _currently_addable(analysis: dict[str, Any]) -> bool:
    if analysis.get("thesis_status") != "INTACT":
        return False
    add_status = analysis.get("add_eligibility_status")
    liquidation_status = analysis.get("liquidation_status")
    if add_status:
        if add_status not in ADD_ALLOWED_STATUSES:
            return False
    elif liquidation_status != "GREEN":
        return False
    if analysis.get("opportunity_cost_status") == "WORSE_THAN_VFV":
        return False
    return True


def _apply_group_switching_discipline(
    analyses: dict[str, dict[str, Any]],
    base_results: dict[str, dict[str, Any]],
    mode: str = "rational-aggressive",
) -> None:
    addable = [
        analysis
        for analysis in analyses.values()
        if analysis.get("ticker") != "VFV.TO"
        and analysis.get("benchmark_role") is not True
        and _currently_addable(analysis)
    ]
    if len(addable) < 2:
        return

    previous_picks = [analysis for analysis in addable if _was_previous_pick(analysis)]
    if not previous_picks:
        return

    best_previous_score = max(safe_float(row.get("capital_allocation_score")) or 0.0 for row in previous_picks)
    best_current_score = max(safe_float(row.get("capital_allocation_score")) or 0.0 for row in addable)

    for analysis in addable:
        ticker = str(analysis.get("ticker") or "")
        current_score = safe_float(analysis.get("capital_allocation_score")) or 0.0
        trend_status = str(analysis.get("trend_status") or "")
        trend_severity = safe_float(analysis.get("trend_severity")) or 0.0
        if trend_status == "DETERIORATING" and trend_severity >= 1:
            continue

        if _was_previous_pick(analysis):
            if best_current_score - current_score <= CONTINUITY_CLOSE_SCORE_GAP:
                _raise_adjustment(
                    analysis,
                    base_results.get(ticker, {}),
                    "CONTINUITY_IF_CLOSE",
                    CONTINUITY_SUPPORT + _stability_tuning(mode),
                    (
                        "Le titre était déjà retenu et reste très proche du meilleur candidat; "
                        "l’amortisseur évite un changement causé par un écart trop mince."
                    ),
                )
            continue

        score_edge = current_score - best_previous_score
        if score_edge >= CLEAR_NEW_LEADER_EDGE or trend_status in {"SOLIDIFYING", "DEVELOPING"} and score_edge >= 3:
            _append_reason(
                analysis,
                "CLEAR_NEW_LEADER_ALLOWED",
                (
                    "Le nouveau candidat a un avantage assez net pour passer malgré l’amortisseur de stabilité."
                ),
            )
            continue

        _add_adjustment(
            analysis,
            "CHALLENGER_NEEDS_CLEAR_EDGE",
            CHURN_PENALTY - max(0.0, _stability_tuning(mode) * 0.35),
            (
                "Nouveau candidat proche de l’ancien choix: petite pénalité anti-bruit jusqu’à ce que "
                "son avantage devienne plus clair."
            ),
        )


def _was_previous_pick(analysis: dict[str, Any]) -> bool:
    return (
        str(analysis.get("previous_allocation_decision") or "") in POSITIVE_ALLOCATION_ACTIONS
        or str(analysis.get("previous_final_position_action") or "") in POSITIVE_ALLOCATION_ACTIONS
    )


def _stability_tuning(mode: str) -> float:
    return tuning_value(mode, "stability_strength_adjustment", 0.0)


def _raise_adjustment(
    analysis: dict[str, Any],
    base_result: dict[str, Any],
    status: str,
    minimum_adjustment: float,
    reason: str,
) -> None:
    current_adjustment = safe_float(analysis.get("allocation_stability_adjustment")) or 0.0
    if current_adjustment >= minimum_adjustment:
        return
    analysis["allocation_stability_adjustment"] = minimum_adjustment
    analysis["allocation_stability_status"] = status
    previous_reason = str(base_result.get("allocation_stability_reason") or analysis.get("allocation_stability_reason") or "")
    analysis["allocation_stability_reason"] = _join_reasons(previous_reason, reason)


def _add_adjustment(analysis: dict[str, Any], status: str, delta: float, reason: str) -> None:
    current_adjustment = safe_float(analysis.get("allocation_stability_adjustment")) or 0.0
    analysis["allocation_stability_adjustment"] = round(current_adjustment + delta, 4)
    analysis["allocation_stability_status"] = status
    previous_reason = str(analysis.get("allocation_stability_reason") or "")
    analysis["allocation_stability_reason"] = _join_reasons(previous_reason, reason)


def _append_reason(analysis: dict[str, Any], status: str, reason: str) -> None:
    if str(analysis.get("allocation_stability_status") or "").startswith("CLEAR"):
        return
    analysis["allocation_stability_status"] = status
    previous_reason = str(analysis.get("allocation_stability_reason") or "")
    analysis["allocation_stability_reason"] = _join_reasons(previous_reason, reason)


def _join_reasons(first: str, second: str) -> str:
    first = first.strip()
    second = second.strip()
    if not first:
        return second
    if not second or second in first:
        return first
    return f"{first} {second}"


def _result(status: str, adjustment: float, reason: str, current_score: float, previous_score: float | None) -> dict[str, Any]:
    result = {
        "allocation_stability_status": status,
        "allocation_stability_adjustment": adjustment,
        "allocation_stability_reason": reason,
        "previous_capital_allocation_score": previous_score,
    }
    if previous_score is not None:
        result["capital_allocation_score_change"] = round(current_score - previous_score, 4)
    return result
