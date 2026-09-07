from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .model_tuning import TUNABLE_PARAMETER_LIMITS
from .proxy_correction_engine import PROXY_CORRECTION_PARAMETER_PREFIX
from .utils import pct, safe_float
from .model_identity import MODEL_LINEAGE, matches_current_cohort, production_audit_scope
from .validation_evidence import (
    AUTO_TUNING_POLICY,
    EvidenceClass,
    evidence_maturity,
    walk_forward_period_has_strategy_validation_authority,
    walk_forward_period_is_legacy_diagnostic,
)


ANTI_OVERFITTING_FIELDS = [
    "tuning_policy",
    "evidence_class",
    "evidence_maturity",
    "model_version_scope",
    "genuine_oos_periods",
    "overfit_gate_status",
    "overfit_gate_score",
    "overfit_gate_reason",
    "in_sample_out_of_sample_status",
    "regime_consistency_status",
    "do_no_harm_status",
    "risk_adjusted_status",
    "walk_forward_status",
    "cooldown_status",
]

PASSING_GATE_STATUSES = {"PASS", "PASS_WITH_LIMITS"}


def build_anti_overfitting_context(
    *,
    model_metrics: dict[str, Any],
    backtest_summary_rows: list[dict[str, Any]] | None = None,
    backtest_monthly_rows: list[dict[str, Any]] | None = None,
    walk_forward_summary_rows: list[dict[str, Any]] | None = None,
    walk_forward_period_rows: list[dict[str, Any]] | None = None,
    tuning_history_rows: list[dict[str, Any]] | None = None,
    mode: str = "high-cagr",
    settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings = settings or {}
    sample_count = int(safe_float(model_metrics.get("allocation_sample_count")) or 0)
    span_days = int(safe_float(model_metrics.get("span_days")) or 0)
    min_samples = int(safe_float(settings.get("min_distinct_allocation_dates")) or 4)
    cooldown_days = int(safe_float(settings.get("min_days_between_same_parameter_tuning")) or 45)
    summaries = backtest_summary_rows or []
    monthly = backtest_monthly_rows or []
    walk_forward_summary = _first_row(walk_forward_summary_rows or [])
    walk_forward_periods = walk_forward_period_rows or []
    current_model_version = str(model_metrics.get("current_model_rules_version") or "")
    current_lineage = str(model_metrics.get("current_model_lineage") or MODEL_LINEAGE)
    simulated_walk_forward_periods = [
        row
        for row in walk_forward_periods
        if str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    current_version_total_walk_forward_periods = [
        row for row in walk_forward_periods
        if current_model_version
        and matches_current_cohort(row, lineage=current_lineage, rules_version=current_model_version)
        and str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    current_walk_forward_periods = [
        row
        for row in current_version_total_walk_forward_periods
        if walk_forward_period_has_strategy_validation_authority(row)
    ]
    current_version_legacy_walk_forward_periods = [
        row
        for row in current_version_total_walk_forward_periods
        if walk_forward_period_is_legacy_diagnostic(row)
    ]
    scoped_walk_forward_summary = _scoped_walk_forward_summary(current_walk_forward_periods)
    walk_forward_status = _walk_forward_status(scoped_walk_forward_summary, current_walk_forward_periods)
    genuine_oos_periods = int(safe_float(scoped_walk_forward_summary.get("simulated_periods")) or 0)
    current_version_decision_observations = int(
        safe_float(
            model_metrics.get(
                "current_version_decision_observation_count",
                model_metrics.get("current_version_observation_count"),
            )
        )
        or 0
    )
    if not production_audit_scope(model_metrics):
        current_version_decision_observations = 0
        sample_count = 0
        span_days = 0
    return {
        "mode": mode,
        "sample_count": sample_count,
        "span_days": span_days,
        "minimum_sample_count": min_samples,
        "cooldown_days": cooldown_days,
        "backtest_period_status": _backtest_period_status(summaries),
        "in_sample_out_of_sample_status": _split_sample_status(monthly),
        "regime_consistency_status": _regime_consistency_status(summaries),
        "do_no_harm_status": _do_no_harm_status(summaries),
        "risk_adjusted_status": _risk_adjusted_status(summaries),
        "walk_forward_status": walk_forward_status,
        "tuning_policy": AUTO_TUNING_POLICY,
        "evidence_class": (
            EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value
            if current_walk_forward_periods
            else EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value
            if current_version_legacy_walk_forward_periods
            else EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value
        ),
        "evidence_maturity": evidence_maturity(genuine_oos_periods),
        "model_version_scope": "CURRENT_VERSION_AUDIT",
        "current_version_observations": current_version_decision_observations,
        "current_version_decision_observations": current_version_decision_observations,
        "cross_version_observations": int(safe_float(model_metrics.get("cross_version_observation_count")) or 0),
        "genuine_oos_periods": genuine_oos_periods,
        "walk_forward_simulated_periods": int(safe_float(walk_forward_summary.get("simulated_periods")) or 0),
        "walk_forward_usable_periods": int(safe_float(walk_forward_summary.get("usable_walk_forward_periods")) or 0),
        "walk_forward_current_version_total_simulated_period_count": len(current_version_total_walk_forward_periods),
        "walk_forward_current_version_legacy_period_count": len(current_version_legacy_walk_forward_periods),
        "walk_forward_current_version_non_authoritative_period_count": max(
            0,
            len(current_version_total_walk_forward_periods) - len(current_walk_forward_periods),
        ),
        "walk_forward_excess_return": safe_float(scoped_walk_forward_summary.get("compounded_excess_return_vs_vfv")),
        "walk_forward_win_rate": safe_float(scoped_walk_forward_summary.get("win_rate_vs_vfv")),
        "walk_forward_regime_coverage_status": str(scoped_walk_forward_summary.get("regime_coverage_status") or "NO_REGIME_EVIDENCE"),
        "walk_forward_regime_count": int(safe_float(scoped_walk_forward_summary.get("regime_count")) or 0),
        "walk_forward_weak_regimes": str(scoped_walk_forward_summary.get("weak_regimes") or ""),
        "tuning_history_rows": tuning_history_rows or [],
        "backtest_summary_count": len(summaries),
        "monthly_backtest_count": len(monthly),
        "walk_forward_period_count": len(walk_forward_periods),
        "walk_forward_current_version_period_count": len(current_walk_forward_periods),
        "walk_forward_cross_version_period_count": max(
            0,
            len(simulated_walk_forward_periods) - len(current_version_total_walk_forward_periods),
        ),
    }


def apply_anti_overfitting_gate_to_suggestions(
    suggestions: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    gated: list[dict[str, Any]] = []
    for suggestion in suggestions:
        row = dict(suggestion)
        gate = evaluate_anti_overfitting_gate(row, context)
        row.update(gate)
        if (
            row.get("can_auto_apply") is True
            and str(row.get("status") or "") == "PENDING_SAFE_APPLY"
            and str(gate.get("overfit_gate_status") or "") not in PASSING_GATE_STATUSES
        ):
            row["can_auto_apply"] = False
            row["status"] = "REVIEW_ONLY"
        gated.append(row)
    return gated


def evaluate_anti_overfitting_gate(suggestion: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    parameter = str(suggestion.get("parameter") or "")
    safety = str(suggestion.get("safety_level") or "").upper()
    delta = safe_float(suggestion.get("suggested_delta")) or 0.0
    if not _is_auto_adjustable_parameter(parameter) or safety != "SAFE":
        return _gate_result(
            "NOT_APPLICABLE",
            100,
            "Suggestion informative ou non ajustable automatiquement.",
            context,
            "NOT_APPLICABLE",
        )

    if str(context.get("tuning_policy") or AUTO_TUNING_POLICY) == "PROPOSAL_ONLY":
        return _gate_result(
            "REVIEW_ONLY",
            40,
            (
                "Politique PROPOSAL_ONLY: aucune modification comportementale automatique. "
                "Le backtest mécanique ne possède aucune autorité positive et les preuves OOS restent auditables séparément."
            ),
            context,
            "NOT_EVALUATED_PROPOSAL_ONLY",
        )

    sample_count = int(safe_float(context.get("sample_count")) or 0)
    minimum = int(safe_float(context.get("minimum_sample_count")) or 4)
    if sample_count < minimum:
        return _gate_result(
            "REVIEW_ONLY",
            45,
            f"Historique insuffisant: {sample_count} date(s) avec allocation, minimum {minimum}.",
            context,
            "INSUFFICIENT_HISTORY",
        )

    cooldown_status = _cooldown_status(
        context.get("tuning_history_rows") or [],
        mode=str(context.get("mode") or ""),
        parameter=parameter,
        cooldown_days=int(safe_float(context.get("cooldown_days")) or 45),
    )
    posture = _suggestion_posture(parameter, delta)
    regime = str(context.get("regime_consistency_status") or "LIMITED")
    split = str(context.get("in_sample_out_of_sample_status") or "LIMITED")
    harm = str(context.get("do_no_harm_status") or "LIMITED")
    risk_adjusted = str(context.get("risk_adjusted_status") or "LIMITED")
    walk_forward = str(context.get("walk_forward_status") or "LIMITED")

    if cooldown_status == "COOLDOWN_ACTIVE":
        return _gate_result(
            "REVIEW_ONLY",
            55,
            "Même paramètre ajusté récemment; attendre plus de recul avant un nouvel auto-ajustement.",
            context,
            cooldown_status,
        )

    if posture in {"MORE_AGGRESSIVE", "MORE_REACTIVE", "DRAWNDOWN_OPPORTUNITY"}:
        if walk_forward == "FAIL":
            return _gate_result(
                "REVIEW_ONLY",
                54,
                "Le walk-forward hors-échantillon disponible échoue le test do-no-harm vs VFV; application automatique refusée.",
                context,
                cooldown_status,
            )
        if walk_forward == "WATCH":
            return _gate_result(
                "PASS_WITH_LIMITS",
                70,
                "Le walk-forward disponible est mitigé; seuls de petits ajustements SAFE restent acceptables.",
                context,
                cooldown_status,
            )
        if regime == "RECENT_ONLY":
            return _gate_result(
                "REVIEW_ONLY",
                58,
                "Le signal semble surtout favorable à la période récente; application automatique refusée pour éviter le surapprentissage.",
                context,
                cooldown_status,
            )
        if harm == "FAIL":
            return _gate_result(
                "REVIEW_ONLY",
                52,
                "Le test do-no-harm vs VFV/S&P 500 est faible; la suggestion reste en revue manuelle.",
                context,
                cooldown_status,
            )
        if risk_adjusted == "FAIL":
            return _gate_result(
                "REVIEW_ONLY",
                55,
                "Le rendement ajusté au drawdown n’est pas assez robuste pour appliquer automatiquement une hausse de risque.",
                context,
                cooldown_status,
            )

    if split == "WEAK" and posture in {"MORE_AGGRESSIVE", "MORE_REACTIVE"}:
        return _gate_result(
            "REVIEW_ONLY",
            58,
            "La séparation ancien/récent ne soutient pas assez la suggestion pour l’appliquer automatiquement.",
            context,
            cooldown_status,
        )

    if "LIMITED" in {regime, split, harm, risk_adjusted} or regime == "MIXED" or harm == "WATCH":
        return _gate_result(
            "PASS_WITH_LIMITS",
            72,
            "Preuve utile mais incomplète; l’ajustement peut rester SAFE parce qu’il est petit et plafonné.",
            context,
            cooldown_status,
        )

    return _gate_result(
        "PASS",
        86,
        "La suggestion ne montre pas de risque évident de surapprentissage selon les preuves disponibles.",
        context,
        cooldown_status,
    )


def anti_overfitting_summary(suggestions: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    statuses = [str(row.get("overfit_gate_status") or "") for row in suggestions]
    pass_count = sum(1 for status in statuses if status in PASSING_GATE_STATUSES)
    review_count = sum(1 for status in statuses if status == "REVIEW_ONLY")
    blocked_count = sum(1 for status in statuses if status == "BLOCKED")
    applicable_count = sum(1 for status in statuses if status not in {"", "NOT_APPLICABLE"})
    if applicable_count == 0:
        status = "NO_AUTOMATIC_TUNING_NEEDED"
    elif review_count or blocked_count:
        status = "PASS_WITH_MANUAL_REVIEWS" if pass_count else "OBSERVE_OR_REVIEW"
    elif any(status == "PASS_WITH_LIMITS" for status in statuses):
        status = "PASS_WITH_LIMITS"
    else:
        status = "PASS"
    return {
        "overfit_gate_status": status,
        "overfit_gate_pass_count": pass_count,
        "overfit_gate_review_count": review_count + blocked_count,
        "overfit_gate_interpretation": _summary_read(status, context),
        "tuning_policy": context.get("tuning_policy", AUTO_TUNING_POLICY),
        "evidence_class": context.get("evidence_class", EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value),
        "evidence_maturity": context.get("evidence_maturity", "INSUFFICIENT"),
        "model_version_scope": context.get("model_version_scope", "CURRENT_VERSION_AUDIT"),
        "genuine_oos_periods": context.get("genuine_oos_periods", 0),
    }


def anti_overfitting_context_rows(context: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _context_row(
            "Backtests multi-périodes",
            context.get("regime_consistency_status", "LIMITED"),
            f"{context.get('backtest_summary_count', 0)} résumé(s)",
            "Vérifie que le modèle ne dépend pas seulement d’une fenêtre récente.",
        ),
        _context_row(
            "Ancien vs récent",
            context.get("in_sample_out_of_sample_status", "LIMITED"),
            f"{context.get('monthly_backtest_count', 0)} mois simulé(s)",
            "Compare la robustesse des périodes anciennes et récentes quand les données existent.",
        ),
        _context_row(
            "Do-no-harm vs VFV",
            context.get("do_no_harm_status", "LIMITED"),
            "",
            "Refuse les auto-ajustements agressifs si le modèle détériore nettement le benchmark.",
        ),
        _context_row(
            "Rendement ajusté au risque",
            context.get("risk_adjusted_status", "LIMITED"),
            "",
            "Évite de favoriser une hausse de rendement théorique obtenue avec trop de drawdown.",
        ),
        _context_row(
            "Walk-forward hors-échantillon",
            context.get("walk_forward_status", "LIMITED"),
            f"{context.get('walk_forward_simulated_periods', 0)} période(s); régimes: {context.get('walk_forward_regime_coverage_status', 'NO_REGIME_EVIDENCE')}",
            "Vérifie les recommandations historiques réellement produites; reste neutre quand l’historique est trop court.",
        ),
        _context_row(
            "Cooldown tuning",
            f"{context.get('cooldown_days', 45)} jours",
            "",
            "Empêche de modifier trop souvent le même paramètre.",
        ),
    ]


def _backtest_period_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "LIMITED"
    excess_values = [safe_float(row.get("excess_value_vs_vfv")) for row in rows]
    values = [value for value in excess_values if value is not None]
    if not values:
        return "LIMITED"
    if all(value >= 0 for value in values):
        return "SUPPORTIVE"
    if all(value < 0 for value in values):
        return "WEAK"
    return "MIXED"


def _regime_consistency_status(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 2:
        return "LIMITED"
    values = [safe_float(row.get("excess_value_vs_vfv")) for row in rows]
    values = [value for value in values if value is not None]
    if len(values) < 2:
        return "LIMITED"
    positives = sum(1 for value in values if value >= 0)
    if positives == len(values):
        return "PASS"
    if positives == 0:
        return "WEAK"
    periods = [int(safe_float(row.get("period_years")) or 0) for row in rows]
    shortest = min((period for period in periods if period > 0), default=0)
    recent_row = next((row for row in rows if int(safe_float(row.get("period_years")) or 0) == shortest), rows[0])
    if (safe_float(recent_row.get("excess_value_vs_vfv")) or 0.0) > 0 and positives < len(values):
        return "RECENT_ONLY"
    return "MIXED"


def _do_no_harm_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "LIMITED"
    values = [safe_float(row.get("excess_value_vs_vfv")) for row in rows]
    values = [value for value in values if value is not None]
    if not values:
        return "LIMITED"
    negative_count = sum(1 for value in values if value < 0)
    avg_excess = sum(values) / len(values)
    if negative_count == len(values) and avg_excess < 0:
        return "FAIL"
    if negative_count:
        return "WATCH"
    return "PASS"


def _risk_adjusted_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "LIMITED"
    failures = 0
    watch = 0
    usable = 0
    for row in rows:
        drawdown = safe_float(row.get("max_drawdown_on_capital_multiple"))
        excess = safe_float(row.get("excess_value_vs_vfv"))
        if drawdown is None and excess is None:
            continue
        usable += 1
        if drawdown is not None and drawdown <= -0.50 and (excess is None or excess < 0):
            failures += 1
        elif drawdown is not None and drawdown <= -0.40:
            watch += 1
    if usable == 0:
        return "LIMITED"
    if failures:
        return "FAIL"
    if watch:
        return "WATCH"
    return "PASS"


def _split_sample_status(rows: list[dict[str, Any]]) -> str:
    by_period: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        period = str(row.get("period_years") or "")
        by_period.setdefault(period, []).append(row)
    statuses = [_split_status_for_rows(period_rows) for period_rows in by_period.values()]
    statuses = [status for status in statuses if status != "LIMITED"]
    if not statuses:
        return "LIMITED"
    if "RECENT_ONLY" in statuses:
        return "RECENT_ONLY"
    if "WEAK" in statuses:
        return "WEAK"
    if "MIXED" in statuses:
        return "MIXED"
    return "PASS"


def _split_status_for_rows(rows: list[dict[str, Any]]) -> str:
    ordered = sorted(rows, key=lambda row: str(row.get("date") or ""))
    if len(ordered) < 24:
        return "LIMITED"
    split_index = max(12, int(len(ordered) * 0.70))
    old = ordered[:split_index]
    recent = ordered[split_index:]
    if len(recent) < 6:
        return "LIMITED"
    old_excess = _segment_excess(old)
    recent_excess = _segment_excess(recent)
    if old_excess is None or recent_excess is None:
        return "LIMITED"
    if old_excess >= -0.02 and recent_excess >= -0.02:
        return "PASS"
    if old_excess < -0.02 and recent_excess > 0.02:
        return "RECENT_ONLY"
    if old_excess < -0.02 and recent_excess < -0.02:
        return "WEAK"
    return "MIXED"


def _segment_excess(rows: list[dict[str, Any]]) -> float | None:
    if len(rows) < 2:
        return None
    first = rows[0]
    last = rows[-1]
    portfolio_start = safe_float(first.get("capital_multiple"))
    portfolio_end = safe_float(last.get("capital_multiple"))
    vfv_start = safe_float(first.get("vfv_capital_multiple"))
    vfv_end = safe_float(last.get("vfv_capital_multiple"))
    if None in {portfolio_start, portfolio_end, vfv_start, vfv_end}:
        return None
    return (portfolio_end - portfolio_start) - (vfv_end - vfv_start)


def _walk_forward_status(summary: dict[str, Any], period_rows: list[dict[str, Any]]) -> str:
    status = str(summary.get("status") or "").upper()
    simulated = int(safe_float(summary.get("simulated_periods")) or 0)
    if status in {"", "NO_USABLE_PERIODS", "NO_SIMULATED_PERIODS"} or simulated <= 0:
        return "LIMITED"
    if status == "EARLY_SIGNAL_ONLY":
        return "LIMITED"
    excess = safe_float(summary.get("compounded_excess_return_vs_vfv"))
    avg_excess = safe_float(summary.get("avg_excess_return_vs_vfv"))
    win_rate = safe_float(summary.get("win_rate_vs_vfv"))
    regime_coverage = str(summary.get("regime_coverage_status") or "")
    simulated_rows = [
        row for row in period_rows
        if str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    negative_rows = sum(1 for row in simulated_rows if (safe_float(row.get("excess_return_vs_vfv")) or 0.0) < 0)

    # This gate is deliberately slow to fail. It should prevent obvious
    # overfitting, not make the strategy conservative because of a few young
    # observations.
    enough_observations = simulated >= 4 or status == "READY_FOR_WALK_FORWARD_REVIEW"
    if not enough_observations:
        if excess is not None and excess < -0.08 and win_rate is not None and win_rate <= 0.25:
            return "WATCH"
        return "LIMITED"
    if excess is not None and excess < -0.08 and win_rate is not None and win_rate <= 0.35:
        return "FAIL"
    if regime_coverage == "HAS_WEAK_REGIME":
        return "WATCH"
    if negative_rows >= max(2, int(len(simulated_rows) * 0.6)) and (avg_excess is not None and avg_excess < -0.02):
        return "WATCH"
    if excess is not None and excess >= -0.02:
        return "PASS"
    return "WATCH"


def _scoped_walk_forward_summary(period_rows: list[dict[str, Any]]) -> dict[str, Any]:
    simulated = [
        row for row in period_rows
        if str(row.get("evaluation_status") or "") in {"SIMULATED", "SIMULATED_WITH_PARTIAL_PRICE_DATA"}
    ]
    strategy_returns = [safe_float(row.get("strategy_period_return")) or 0.0 for row in simulated]
    vfv_returns = [safe_float(row.get("vfv_period_return")) or 0.0 for row in simulated]
    excess_returns = [safe_float(row.get("excess_return_vs_vfv")) or 0.0 for row in simulated]
    compounded_strategy = _compound(strategy_returns)
    compounded_vfv = _compound(vfv_returns)
    compounded_excess = None
    if compounded_vfv > -1.0:
        compounded_excess = (1.0 + compounded_strategy) / (1.0 + compounded_vfv) - 1.0
    return {
        "status": "READY_FOR_WALK_FORWARD_REVIEW" if len(simulated) >= 6 else ("EARLY_SIGNAL_ONLY" if simulated else "NO_SIMULATED_PERIODS"),
        "simulated_periods": len(simulated),
        "compounded_excess_return_vs_vfv": compounded_excess,
        "avg_excess_return_vs_vfv": sum(excess_returns) / len(excess_returns) if excess_returns else None,
        "win_rate_vs_vfv": sum(1 for value in excess_returns if value > 0) / len(excess_returns) if excess_returns else None,
        "regime_coverage_status": "CURRENT_VERSION_SCOPED",
        "regime_count": len({str(row.get("market_regime") or "UNKNOWN") for row in simulated}),
        "weak_regimes": "",
    }


def _compound(values: list[float]) -> float:
    total = 1.0
    for value in values:
        total *= 1.0 + value
    return total - 1.0


def _first_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return rows[0] if rows else {}


def _cooldown_status(rows: list[dict[str, Any]], *, mode: str, parameter: str, cooldown_days: int) -> str:
    if cooldown_days <= 0:
        return "PASS"
    latest: date | None = None
    for row in rows:
        if str(row.get("mode") or "") != mode or str(row.get("parameter") or "") != parameter:
            continue
        parsed = _parse_date(row.get("applied_at"))
        if parsed and (latest is None or parsed > latest):
            latest = parsed
    if latest is None:
        return "PASS"
    days = (date.today() - latest).days
    if days < cooldown_days:
        return "COOLDOWN_ACTIVE"
    return "PASS"


def _suggestion_posture(parameter: str, delta: float) -> str:
    if parameter.startswith(PROXY_CORRECTION_PARAMETER_PREFIX):
        return "DATA_QUALITY"
    if parameter in {"vfv_adjustment", "defensive_reserve_adjustment"}:
        return "MORE_AGGRESSIVE" if delta < 0 else "MORE_DEFENSIVE"
    if parameter == "min_capital_score_adjustment":
        return "MORE_AGGRESSIVE" if delta < 0 else "QUALITY_FILTER"
    if parameter in {"cycle_budget_adjustment", "cycle_individual_cap_adjustment", "single_stock_cap_adjustment"}:
        return "MORE_AGGRESSIVE" if delta > 0 else "RISK_DAMPENER"
    if parameter == "quality_drawdown_score_adjustment":
        return "DRAWNDOWN_OPPORTUNITY" if delta > 0 else "RISK_DAMPENER"
    if parameter == "stability_strength_adjustment":
        return "STABILITY" if delta > 0 else "MORE_REACTIVE"
    return "NEUTRAL"


def _is_auto_adjustable_parameter(parameter: str) -> bool:
    return parameter in TUNABLE_PARAMETER_LIMITS or parameter.startswith(PROXY_CORRECTION_PARAMETER_PREFIX)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text[:19]).date()
    except ValueError:
        try:
            return datetime.fromisoformat(text[:10]).date()
        except ValueError:
            return None


def _gate_result(
    status: str,
    score: float,
    reason: str,
    context: dict[str, Any],
    cooldown_status: str,
) -> dict[str, Any]:
    return {
        "overfit_gate_status": status,
        "overfit_gate_score": round(score, 1),
        "overfit_gate_reason": reason,
        "in_sample_out_of_sample_status": context.get("in_sample_out_of_sample_status", "LIMITED"),
        "regime_consistency_status": context.get("regime_consistency_status", "LIMITED"),
        "do_no_harm_status": context.get("do_no_harm_status", "LIMITED"),
        "risk_adjusted_status": context.get("risk_adjusted_status", "LIMITED"),
        "walk_forward_status": context.get("walk_forward_status", "LIMITED"),
        "cooldown_status": cooldown_status,
        "tuning_policy": context.get("tuning_policy", AUTO_TUNING_POLICY),
        "evidence_class": context.get("evidence_class", EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value),
        "evidence_maturity": context.get("evidence_maturity", "INSUFFICIENT"),
        "model_version_scope": context.get("model_version_scope", "CURRENT_VERSION_AUDIT"),
        "genuine_oos_periods": context.get("genuine_oos_periods", 0),
    }


def _summary_read(status: str, context: dict[str, Any]) -> str:
    if status == "PASS":
        return "Les suggestions automatiques disponibles passent les garde-fous anti-overfitting."
    if status == "PASS_WITH_LIMITS":
        return "Les suggestions peuvent être appliquées, mais avec preuve encore incomplète et petits ajustements seulement."
    if status == "PASS_WITH_MANUAL_REVIEWS":
        return "Certaines suggestions passent, d’autres restent en revue manuelle pour éviter de réagir au dernier cycle."
    if status == "OBSERVE_OR_REVIEW":
        return "Aucune suggestion automatique assez robuste; observer ou valider manuellement."
    return (
        "Aucun tuning automatique nécessaire. "
        f"Backtest: {context.get('regime_consistency_status', 'LIMITED')}; "
        f"do-no-harm: {context.get('do_no_harm_status', 'LIMITED')}; "
        f"walk-forward: {context.get('walk_forward_status', 'LIMITED')}."
    )


def _context_row(check: str, status: Any, value: Any, interpretation: str) -> dict[str, Any]:
    return {
        "check": check,
        "status": str(status or ""),
        "value": "" if value is None else str(value),
        "interpretation": interpretation,
    }
