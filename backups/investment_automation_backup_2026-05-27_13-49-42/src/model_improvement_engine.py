from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .backup_engine import create_project_backup
from .model_audit_engine import build_model_audit
from .model_tuning import (
    TUNABLE_PARAMETER_LIMITS,
    apply_tuning_suggestion,
    can_auto_apply_value,
    create_model_tuning_template,
    load_model_tuning,
    tuning_value,
)
from .underperformance_engine import (
    UNDERPERFORMANCE_COLUMNS,
    build_underperformance_attribution,
    correction_governor_allows_auto_apply,
    correction_governor_max_changes,
)
from .utils import DISCLAIMER, markdown_to_html, pct, read_csv_records, safe_float, write_csv_records, write_text


IMPROVEMENT_COLUMNS = [
    "suggestion_id",
    "mode",
    "parameter",
    "current_value",
    "suggested_delta",
    "suggested_value",
    "safety_level",
    "can_auto_apply",
    "status",
    "evidence",
    "reason",
    "expected_effect",
    "risk",
    "guardrail",
    "correction_governor",
]

IMPROVEMENT_SUMMARY_COLUMNS = [
    "date",
    "mode",
    "period",
    "status",
    "suggestion_count",
    "safe_auto_applicable_count",
    "moderate_count",
    "risky_count",
    "history_status",
    "underperformance_status",
    "correction_governor",
    "max_safe_changes_allowed",
    "interpretation",
]

PROFILE_TARGETS = {
    "high-cagr": {
        "vfv_low": 0.03,
        "vfv_high": 0.25,
        "core_min": 0.70,
        "turnover_high": 0.45,
        "max_single_high": 0.55,
        "cycle_high": 0.55,
        "low_data_high": 0.15,
    },
    "rational-aggressive": {
        "vfv_low": 0.08,
        "vfv_high": 0.35,
        "core_min": 0.60,
        "turnover_high": 0.40,
        "max_single_high": 0.45,
        "cycle_high": 0.45,
        "low_data_high": 0.12,
    },
    "family-office": {
        "vfv_low": 0.12,
        "vfv_high": 0.45,
        "core_min": 0.45,
        "turnover_high": 0.35,
        "max_single_high": 0.35,
        "cycle_high": 0.35,
        "low_data_high": 0.10,
    },
    "balanced": {
        "vfv_low": 0.20,
        "vfv_high": 0.65,
        "core_min": 0.25,
        "turnover_high": 0.25,
        "max_single_high": 0.20,
        "cycle_high": 0.15,
        "low_data_high": 0.08,
    },
}


def run_improvement_audit(
    reports_dir: str | Path,
    config_dir: str | Path,
    data_dir: str | Path,
    *,
    period: str = "12m",
    mode: str = "high-cagr",
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    config_dir = Path(config_dir)
    data_dir = Path(data_dir)
    create_model_tuning_template(config_dir / "model_tuning.yaml")
    model_audit = build_model_audit(reports_dir, period=period, mode=mode)
    tuning = load_model_tuning(config_dir / "model_tuning.yaml")
    proxy_summary_rows = read_csv_records(reports_dir / "latest_proxy_calibration_summary.csv")
    underperformance = build_underperformance_attribution(
        model_metrics=model_audit.get("metrics") or {},
        account_performance_rows=read_csv_records(reports_dir / "latest_account_performance_vs_sp500.csv"),
        backtest_summaries=read_csv_records(reports_dir / "latest_backtest_summary.csv"),
        mode=mode,
    )
    suggestions = build_improvement_suggestions(model_audit, tuning, proxy_summary_rows, mode, underperformance)
    summary = build_improvement_summary(model_audit, suggestions, period, mode, underperformance)
    markdown = build_improvement_markdown(model_audit, summary, suggestions, underperformance)
    write_improvement_outputs(reports_dir, summary, suggestions, markdown, underperformance)
    return {
        "model_audit": model_audit,
        "summary": summary,
        "suggestions": suggestions,
        "underperformance_attribution": underperformance,
        "markdown": markdown,
    }


def build_improvement_suggestions(
    model_audit: dict[str, Any],
    tuning: dict[str, Any],
    proxy_summary_rows: list[dict[str, Any]],
    mode: str,
    underperformance_attribution: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    metrics = model_audit.get("metrics") or {}
    targets = PROFILE_TARGETS.get(mode, PROFILE_TARGETS["high-cagr"])
    settings = tuning.get("safe_auto_apply") or {}
    auto_apply_enabled = can_auto_apply_value(settings.get("enabled", True))
    governor_allows_auto_apply = correction_governor_allows_auto_apply(underperformance_attribution)
    correction_governor = str((underperformance_attribution or {}).get("correction_governor") or "NORMAL_SAFE_TUNING")
    sample_count = int(safe_float(metrics.get("allocation_sample_count")) or 0)
    confidence = str(metrics.get("confidence") or "")
    enough_history = sample_count >= int(settings.get("min_distinct_allocation_dates") or 4)
    suggestions: list[dict[str, Any]] = []

    if underperformance_attribution:
        suggestions.append(
            _suggestion(
                mode=mode,
                parameter="correction_governor",
                current_value="",
                delta=0.0,
                safety_level="INFO",
                can_auto_apply=False,
                status=str(underperformance_attribution.get("status") or "N/D"),
                evidence=(
                    f"Écart vs S&P 500: {pct(safe_float(underperformance_attribution.get('preferred_excess_vs_sp500')))}; "
                    f"problèmes de processus: {underperformance_attribution.get('process_issue_count', 0)}."
                ),
                reason=str(underperformance_attribution.get("interpretation") or ""),
                expected_effect=str(underperformance_attribution.get("recommended_posture") or ""),
                risk="Ce gouverneur évite à la fois l’over-correction après une mauvaise période et l’under-correction après une vraie dérive.",
                correction_governor=correction_governor,
            )
        )

    if not enough_history:
        suggestions.append(
            _suggestion(
                mode=mode,
                parameter="none",
                current_value="",
                delta=0.0,
                safety_level="INFO",
                can_auto_apply=False,
                status="WAIT_FOR_MORE_HISTORY",
                evidence=f"{sample_count} date(s) avec allocation; confiance {confidence}.",
                reason="L’audit fonctionne, mais l’historique est trop court pour ajuster les paramètres sans risque de suradaptation.",
                expected_effect="Accumuler quelques analyses réelles avant de modifier le comportement du modèle.",
                risk="Changer trop tôt pourrait optimiser le modèle pour du bruit de marché.",
            )
        )

    avg_vfv = safe_float(metrics.get("avg_vfv")) or 0.0
    avg_core = safe_float(metrics.get("avg_core")) or 0.0
    avg_turnover = safe_float(metrics.get("avg_allocation_turnover")) or 0.0
    primary_change_rate = safe_float(metrics.get("primary_change_rate")) or 0.0
    avg_max_single = safe_float(metrics.get("avg_max_single")) or 0.0
    high_cycle_rate = safe_float(metrics.get("high_cycle_day_rate")) or 0.0
    extreme_cycle_rate = safe_float(metrics.get("extreme_cycle_day_rate")) or 0.0
    low_data_rate = safe_float(metrics.get("low_data_day_rate")) or 0.0
    decision_quality = safe_float(metrics.get("avg_decision_quality"))

    if avg_vfv > targets["vfv_high"] and avg_core < targets["core_min"]:
        suggestions.append(
            _bounded_adjustment(
                mode,
                "vfv_adjustment",
                -0.01,
                "SAFE" if enough_history and decision_quality_ok(decision_quality) else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history and decision_quality_ok(decision_quality),
                f"VFV moyen {pct(avg_vfv)}, core moyen {pct(avg_core)}.",
                "La cotisation semble peut-être trop souvent redirigée vers VFV pour ce profil.",
                "Réduire légèrement la part automatique VFV afin de laisser plus de place aux titres admissibles.",
                "Un filet de sécurité un peu plus petit peut augmenter la volatilité.",
            )
        )
    elif avg_vfv < targets["vfv_low"] and avg_max_single > targets["max_single_high"]:
        suggestions.append(
            _bounded_adjustment(
                mode,
                "vfv_adjustment",
                0.01,
                "SAFE" if enough_history else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history,
                f"VFV moyen {pct(avg_vfv)}, plus gros bloc moyen {pct(avg_max_single)}.",
                "Le modèle semble peut-être trop offensif pour ce mode si cette tendance persiste.",
                "Remonter très légèrement le filet VFV.",
                "Peut réduire un peu le potentiel CAGR si les titres financés sont excellents.",
            )
        )

    if avg_turnover > targets["turnover_high"] or primary_change_rate > targets["turnover_high"]:
        suggestions.append(
            _bounded_adjustment(
                mode,
                "stability_strength_adjustment",
                0.25,
                "SAFE" if enough_history else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history,
                f"rotation moyenne {pct(avg_turnover)}, changement du titre principal {pct(primary_change_rate)}.",
                "Les recommandations semblent peut-être trop sensibles aux variations récentes.",
                "Augmenter légèrement l’amortisseur anti-bruit sans empêcher un vrai changement de leader.",
                "Trop de stabilité pourrait retarder un changement justifié; la variation est donc limitée.",
            )
        )

    if avg_max_single > targets["max_single_high"]:
        suggestions.append(
            _bounded_adjustment(
                mode,
                "single_stock_cap_adjustment",
                -0.02,
                "SAFE" if enough_history else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history,
                f"plus gros bloc moyen {pct(avg_max_single)}.",
                "Le plus gros bloc revient peut-être trop souvent élevé pour ce mode.",
                "Réduire légèrement le plafond marginal par titre.",
                "Peut réduire la puissance des meilleurs winners si appliqué trop fortement.",
            )
        )

    if high_cycle_rate > targets["cycle_high"] or extreme_cycle_rate > max(0.10, targets["cycle_high"] * 0.55):
        suggestions.append(
            _bounded_adjustment(
                mode,
                "cycle_budget_adjustment",
                -0.02,
                "SAFE" if enough_history else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history,
                f"cycle élevé {pct(high_cycle_rate)}, cycle extrême {pct(extreme_cycle_rate)}.",
                "Le modèle finance peut-être trop souvent des thèmes chauds ou cycliques.",
                "Réduire légèrement le budget de cotisation disponible pour les zones cycle/bulle.",
                "Peut faire manquer un compounder cyclique de grande qualité si le signal est temporaire.",
            )
        )

    if low_data_rate > targets["low_data_high"]:
        suggestions.append(
            _bounded_adjustment(
                mode,
                "min_capital_score_adjustment",
                1.0,
                "SAFE" if enough_history else "MODERATE",
                auto_apply_enabled and governor_allows_auto_apply and enough_history,
                f"données faibles dans les titres financés {pct(low_data_rate)}.",
                "Trop de recommandations semblent reposer sur des données gratuites faibles.",
                "Exiger un score d’allocation légèrement plus élevé avant d’acheter.",
                "Peut augmenter VFV ou réduire les achats tant que les données manuelles ne sont pas meilleures.",
            )
        )

    proxy_suggestions = _proxy_suggestions(proxy_summary_rows, mode)
    suggestions.extend(proxy_suggestions)

    if not suggestions:
        suggestions.append(
            _suggestion(
                mode=mode,
                parameter="none",
                current_value="",
                delta=0.0,
                safety_level="INFO",
                can_auto_apply=False,
                status="NO_CHANGE_SUGGESTED",
                evidence="Aucun signal de dérive important dans l’historique disponible.",
                reason="Les réglages secondaires semblent cohérents avec le profil choisi.",
                expected_effect="Continuer à utiliser le modèle et réévaluer après de nouvelles analyses.",
                risk="Aucun changement proposé.",
            )
        )

    return suggestions


def apply_safe_tuning(
    reports_dir: str | Path,
    config_dir: str | Path,
    data_dir: str | Path,
    *,
    mode: str = "high-cagr",
) -> dict[str, Any]:
    reports_dir = Path(reports_dir)
    config_dir = Path(config_dir)
    data_dir = Path(data_dir)
    tuning = load_model_tuning(config_dir / "model_tuning.yaml")
    settings = tuning.get("safe_auto_apply") or {}
    if not can_auto_apply_value(settings.get("enabled", True)):
        return {"applied": [], "message": "Auto-application désactivée dans config/model_tuning.yaml."}

    summary_rows = read_csv_records(reports_dir / "latest_improvement_summary.csv")
    summary = summary_rows[0] if summary_rows else {}
    if not _summary_allows_apply(summary, mode):
        return {
            "applied": [],
            "message": (
                "Aucun ajustement appliqué: relance improvement-audit aujourd’hui et vérifie que le statut est "
                "READY_FOR_SAFE_TUNING pour le même mode."
            ),
        }

    suggestions = read_csv_records(reports_dir / "latest_improvement_suggestions.csv")
    applicable = [
        row
        for row in suggestions
        if str(row.get("mode") or "") == mode
        and str(row.get("safety_level") or "").upper() == "SAFE"
        and can_auto_apply_value(row.get("can_auto_apply"))
        and str(row.get("status") or "") == "PENDING_SAFE_APPLY"
        and str(row.get("parameter") or "") in TUNABLE_PARAMETER_LIMITS
    ]
    if not applicable:
        return {"applied": [], "message": "Aucune suggestion SAFE applicable. Lance improvement-audit ou attends plus d’historique."}

    backup = create_project_backup(Path(config_dir).parents[0])
    base_max_changes = int(safe_float(settings.get("max_safe_changes_per_run")) or 3)
    governor_max_changes = int(safe_float(summary.get("max_safe_changes_allowed")) or base_max_changes)
    max_changes = max(0, min(base_max_changes, governor_max_changes))
    if max_changes <= 0:
        return {
            "applied": [],
            "message": "Aucun ajustement appliqué: le gouverneur de sous-performance demande observation ou revue manuelle.",
        }
    applied = []
    for row in applicable[:max(1, max_changes)]:
        parameter = str(row.get("parameter"))
        delta = _capped_apply_delta(parameter, safe_float(row.get("suggested_delta")) or 0.0, settings)
        if delta == 0:
            continue
        applied.append(
            apply_tuning_suggestion(
                mode=mode,
                parameter=parameter,
                delta=delta,
                suggestion_id=str(row.get("suggestion_id") or ""),
                safety_level=str(row.get("safety_level") or "SAFE"),
                reason=str(row.get("reason") or ""),
                tuning_path=config_dir / "model_tuning.yaml",
                history_path=data_dir / "model_tuning_history.csv",
            )
        )
    return {
        "applied": applied,
        "backup_path": backup.get("backup_path"),
        "message": "Ajustements SAFE appliqués dans config/model_tuning.yaml.",
    }


def _summary_allows_apply(summary: dict[str, Any], mode: str) -> bool:
    if not summary:
        return False
    if str(summary.get("mode") or "") != mode:
        return False
    if str(summary.get("status") or "") != "READY_FOR_SAFE_TUNING":
        return False
    if str(summary.get("date") or "") != date.today().isoformat():
        return False
    return (safe_float(summary.get("safe_auto_applicable_count")) or 0.0) > 0


def _capped_apply_delta(parameter: str, delta: float, settings: dict[str, Any]) -> float:
    if parameter == "vfv_adjustment":
        cap = safe_float(settings.get("max_abs_vfv_adjustment_per_run")) or 0.01
    elif "score" in parameter:
        cap = safe_float(settings.get("max_abs_score_adjustment_per_run")) or 1.0
    else:
        cap = safe_float(settings.get("max_abs_pct_adjustment_per_run")) or 0.02
    cap = abs(cap)
    if cap <= 0:
        return 0.0
    return round(max(-cap, min(cap, delta)), 6)


def build_improvement_summary(
    model_audit: dict[str, Any],
    suggestions: list[dict[str, Any]],
    period: str,
    mode: str,
    underperformance_attribution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metrics = model_audit.get("metrics") or {}
    safe_count = sum(1 for row in suggestions if row.get("safety_level") == "SAFE" and row.get("can_auto_apply") is True)
    moderate_count = sum(1 for row in suggestions if row.get("safety_level") == "MODERATE")
    risky_count = sum(1 for row in suggestions if row.get("safety_level") == "RISKY")
    sample_count = int(safe_float(metrics.get("allocation_sample_count")) or 0)
    status = "READY_FOR_SAFE_TUNING" if safe_count else "OBSERVE_ONLY"
    if sample_count < 4:
        status = "INSUFFICIENT_HISTORY"
    if underperformance_attribution and not correction_governor_allows_auto_apply(underperformance_attribution):
        status = "OBSERVE_ONLY" if status == "READY_FOR_SAFE_TUNING" else status
    return {
        "date": date.today().isoformat(),
        "mode": mode,
        "period": period,
        "status": status,
        "suggestion_count": len(suggestions),
        "safe_auto_applicable_count": safe_count,
        "moderate_count": moderate_count,
        "risky_count": risky_count,
        "history_status": str(metrics.get("confidence") or ""),
        "underperformance_status": str((underperformance_attribution or {}).get("status") or "N/D"),
        "correction_governor": str((underperformance_attribution or {}).get("correction_governor") or "NORMAL_SAFE_TUNING"),
        "max_safe_changes_allowed": correction_governor_max_changes(
            underperformance_attribution,
            3,
        ),
        "interpretation": _summary_interpretation(status),
    }


def build_improvement_markdown(
    model_audit: dict[str, Any],
    summary: dict[str, Any],
    suggestions: list[dict[str, Any]],
    underperformance_attribution: dict[str, Any] | None = None,
) -> str:
    metrics = model_audit.get("metrics") or {}
    lines = [
        "# Audit d’amélioration du modèle",
        "",
        f"- Date: {summary.get('date')}",
        f"- Mode audité: {summary.get('mode')}",
        f"- Période: {summary.get('period')}",
        f"- Statut: **{summary.get('status')}**",
        f"- Historique: {metrics.get('allocation_sample_count', 0)} date(s) avec allocation; confiance {metrics.get('confidence', 'N/D')}",
        "",
        f"> {DISCLAIMER}",
        "",
        "## Résumé",
        "",
        f"- Suggestions totales: {summary.get('suggestion_count')}",
        f"- Suggestions SAFE applicables automatiquement: {summary.get('safe_auto_applicable_count')}",
        f"- Suggestions MODERATE: {summary.get('moderate_count')}",
        f"- Suggestions RISKY: {summary.get('risky_count')}",
        f"- Attribution de sous-performance: **{summary.get('underperformance_status')}**",
        f"- Gouverneur de correction: **{summary.get('correction_governor')}**",
        f"- Interprétation: {summary.get('interpretation')}",
        "",
        "## Attribution de sous-performance",
        "",
        "- Cette couche décide si une sous-performance mérite une correction ou si elle ressemble plutôt à un retard temporaire acceptable.",
        "- Elle protège contre deux erreurs opposées: corriger trop vite après une mauvaise année, ou refuser de corriger après une vraie dérive.",
        "",
        _markdown_table((underperformance_attribution or {}).get("rows") or [], UNDERPERFORMANCE_COLUMNS),
        "",
        "## Suggestions",
        "",
        _markdown_table(suggestions, IMPROVEMENT_COLUMNS),
        "",
        "## Ce que la commande peut appliquer",
        "",
        "- `apply-safe-tuning` applique seulement les lignes `SAFE` avec `can_auto_apply = True`.",
        "- Les suggestions `MODERATE`, `RISKY` ou `INFO` restent informatives.",
        "- Les règles vitales restent verrouillées: thèse cassée, vente orange/rouge, comparaison VFV et promotions externes ne sont pas modifiables par tuning.",
        "- Une sauvegarde est créée avant toute application via la commande CLI.",
        "",
        "## Commandes",
        "",
        "```bash",
        f"python3 main.py improvement-audit --period 12m --mode {summary.get('mode')}",
        f"python3 main.py apply-safe-tuning --mode {summary.get('mode')}",
        "```",
        "",
    ]
    return "\n".join(lines)


def write_improvement_outputs(
    reports_dir: str | Path,
    summary: dict[str, Any],
    suggestions: list[dict[str, Any]],
    markdown: str,
    underperformance_attribution: dict[str, Any] | None = None,
) -> None:
    reports_dir = Path(reports_dir)
    write_text(reports_dir / "latest_improvement_suggestions.md", markdown)
    write_text(reports_dir / "latest_improvement_suggestions.html", markdown_to_html(markdown))
    write_csv_records(reports_dir / "latest_improvement_suggestions.csv", suggestions, IMPROVEMENT_COLUMNS)
    write_csv_records(reports_dir / "latest_improvement_summary.csv", [summary], IMPROVEMENT_SUMMARY_COLUMNS)
    write_csv_records(
        reports_dir / "latest_underperformance_attribution.csv",
        (underperformance_attribution or {}).get("rows") or [],
        UNDERPERFORMANCE_COLUMNS,
    )


def decision_quality_ok(value: float | None) -> bool:
    return value is None or value >= 60


def _bounded_adjustment(
    mode: str,
    parameter: str,
    delta: float,
    safety_level: str,
    can_auto_apply: bool,
    evidence: str,
    reason: str,
    expected_effect: str,
    risk: str,
    correction_governor: str = "",
) -> dict[str, Any]:
    current = tuning_value(mode, parameter, 0.0)
    limits = TUNABLE_PARAMETER_LIMITS[parameter]
    suggested = max(safe_float(limits.get("min")) or 0.0, min((safe_float(limits.get("max")) or 0.0), current + delta))
    actual_delta = round(suggested - current, 6)
    status = "PENDING_SAFE_APPLY" if safety_level == "SAFE" and can_auto_apply and actual_delta != 0 else "REVIEW_ONLY"
    if actual_delta == 0:
        status = "ALREADY_AT_LIMIT"
        can_auto_apply = False
    return _suggestion(
        mode=mode,
        parameter=parameter,
        current_value=current,
        delta=actual_delta,
        safety_level=safety_level,
        can_auto_apply=can_auto_apply and safety_level == "SAFE",
        status=status,
        evidence=evidence,
        reason=reason,
        expected_effect=expected_effect,
        risk=risk,
        correction_governor=correction_governor,
    )


def _suggestion(
    *,
    mode: str,
    parameter: str,
    current_value: Any,
    delta: float,
    safety_level: str,
    can_auto_apply: bool,
    status: str,
    evidence: str,
    reason: str,
    expected_effect: str,
    risk: str,
    correction_governor: str = "",
) -> dict[str, Any]:
    suggestion_id = f"{mode}:{parameter}:{status}".replace(" ", "_")
    suggested_value = ""
    if parameter in TUNABLE_PARAMETER_LIMITS and current_value != "":
        suggested_value = round((safe_float(current_value) or 0.0) + delta, 6)
    return {
        "suggestion_id": suggestion_id,
        "mode": mode,
        "parameter": parameter,
        "current_value": current_value,
        "suggested_delta": round(delta, 6),
        "suggested_value": suggested_value,
        "safety_level": safety_level,
        "can_auto_apply": bool(can_auto_apply),
        "status": status,
        "evidence": evidence,
        "reason": reason,
        "expected_effect": expected_effect,
        "risk": risk,
        "guardrail": "Règles vitales verrouillées; ajustement limité aux paramètres secondaires.",
        "correction_governor": correction_governor,
    }


def _proxy_suggestions(rows: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    text = " ".join(" ".join(str(value) for value in row.values()) for row in rows).lower()
    if "recalibr" not in text and "surestim" not in text and "sous-estim" not in text:
        return []
    return [
        _suggestion(
            mode=mode,
            parameter="proxy_formulas",
            current_value="",
            delta=0.0,
            safety_level="MODERATE",
            can_auto_apply=False,
            status="MANUAL_RECALIBRATION_REVIEW",
            evidence="Le rapport de calibration des proxies contient des écarts ou indices de recalibration.",
            reason="Les formules de proxy peuvent nécessiter une revue, mais elles ne doivent pas être modifiées automatiquement.",
            expected_effect="Améliorer la justesse des estimations automatiques après validation sur plusieurs exemples.",
            risk="Recalibrer sur trop peu d’entreprises pourrait dégrader la qualité générale du modèle.",
        )
    ]


def _summary_interpretation(status: str) -> str:
    return {
        "READY_FOR_SAFE_TUNING": "Des micro-ajustements sécuritaires peuvent être appliqués localement, avec sauvegarde.",
        "OBSERVE_ONLY": "Aucun ajustement automatique prudent n’est justifié; continuer l’observation.",
        "INSUFFICIENT_HISTORY": "Historique trop court: l’audit informe, mais ne doit pas ajuster le modèle.",
    }.get(status, "Audit d’amélioration disponible.")


def _markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        rows = [{column: "" for column in columns}]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(_cell(row.get(column)) for column in columns) + " |")
    return "\n".join([header, separator, *body])


def _cell(value: Any) -> str:
    return str(value if value is not None else "").replace("\n", " ").replace("|", "/")
