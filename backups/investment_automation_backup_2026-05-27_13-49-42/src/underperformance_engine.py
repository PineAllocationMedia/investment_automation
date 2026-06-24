from __future__ import annotations

from typing import Any

from .utils import money, pct, safe_float


UNDERPERFORMANCE_COLUMNS = [
    "metric",
    "status",
    "value",
    "interpretation",
    "impact",
]


MODE_PROCESS_TARGETS = {
    "high-cagr": {
        "vfv_high": 0.25,
        "core_low": 0.70,
        "turnover_high": 0.45,
        "max_single_high": 0.55,
        "cycle_high": 0.55,
        "low_data_high": 0.15,
        "decision_quality_low": 60,
    },
    "rational-aggressive": {
        "vfv_high": 0.35,
        "core_low": 0.60,
        "turnover_high": 0.40,
        "max_single_high": 0.45,
        "cycle_high": 0.45,
        "low_data_high": 0.12,
        "decision_quality_low": 62,
    },
    "family-office": {
        "vfv_high": 0.45,
        "core_low": 0.45,
        "turnover_high": 0.35,
        "max_single_high": 0.35,
        "cycle_high": 0.35,
        "low_data_high": 0.10,
        "decision_quality_low": 65,
    },
    "balanced": {
        "vfv_high": 0.65,
        "core_low": 0.25,
        "turnover_high": 0.25,
        "max_single_high": 0.20,
        "cycle_high": 0.15,
        "low_data_high": 0.08,
        "decision_quality_low": 68,
    },
}


def build_underperformance_attribution(
    *,
    model_metrics: dict[str, Any],
    account_performance_rows: list[dict[str, Any]] | None = None,
    backtest_summaries: list[dict[str, Any]] | None = None,
    mode: str = "high-cagr",
) -> dict[str, Any]:
    targets = MODE_PROCESS_TARGETS.get(str(mode or "high-cagr"), MODE_PROCESS_TARGETS["high-cagr"])
    account = _account_performance_snapshot(account_performance_rows or [])
    backtest = _backtest_snapshot(backtest_summaries or [])
    process = _process_snapshot(model_metrics, targets)

    excess = safe_float(account.get("preferred_excess_vs_sp500"))
    realized_status = str(account.get("status") or "UNAVAILABLE")
    span_days = int(safe_float(model_metrics.get("span_days")) or 0)
    sample_count = int(safe_float(model_metrics.get("allocation_sample_count")) or 0)
    underperformance_level = _underperformance_level(excess, realized_status)
    evidence_horizon = _evidence_horizon(span_days, sample_count)
    status = _attribution_status(
        underperformance_level=underperformance_level,
        process_issue_count=process["issue_count"],
        severe_process_issue_count=process["severe_issue_count"],
        evidence_horizon=evidence_horizon,
        backtest_status=backtest["status"],
    )
    governor = _correction_governor(status, process["issue_count"], evidence_horizon)

    return {
        "status": status,
        "correction_governor": governor["correction_governor"],
        "can_auto_apply_safe_tuning": governor["can_auto_apply_safe_tuning"],
        "max_safe_changes_allowed": governor["max_safe_changes_allowed"],
        "underperformance_level": underperformance_level,
        "evidence_horizon": evidence_horizon,
        "preferred_excess_vs_sp500": excess,
        "realized_performance_status": realized_status,
        "backtest_status": backtest["status"],
        "backtest_negative_period_count": backtest["negative_period_count"],
        "process_issue_count": process["issue_count"],
        "severe_process_issue_count": process["severe_issue_count"],
        "process_issue_list": process["issues"],
        "interpretation": _status_interpretation(status),
        "recommended_posture": governor["recommended_posture"],
        "guardrail": governor["guardrail"],
        "account_snapshot": account,
        "backtest_snapshot": backtest,
        "process_snapshot": process,
        "rows": build_underperformance_rows(
            {
                "status": status,
                "correction_governor": governor["correction_governor"],
                "underperformance_level": underperformance_level,
                "evidence_horizon": evidence_horizon,
                "preferred_excess_vs_sp500": excess,
                "realized_performance_status": realized_status,
                "backtest_status": backtest["status"],
                "process_issue_count": process["issue_count"],
                "severe_process_issue_count": process["severe_issue_count"],
                "process_issue_list": process["issues"],
                "interpretation": _status_interpretation(status),
                "recommended_posture": governor["recommended_posture"],
                "guardrail": governor["guardrail"],
            }
        ),
    }


def build_underperformance_rows(attribution: dict[str, Any]) -> list[dict[str, Any]]:
    excess = safe_float(attribution.get("preferred_excess_vs_sp500"))
    issues = attribution.get("process_issue_list") or []
    issue_text = "; ".join(str(item) for item in issues[:5]) if issues else "Aucun problème mécanique majeur détecté."
    return [
        _row(
            "Sous-performance observée",
            attribution.get("underperformance_level", "N/D"),
            "N/D" if excess is None else pct(excess),
            _underperformance_read(attribution),
            "Évite de confondre une mauvaise année normale avec une erreur de modèle.",
        ),
        _row(
            "Horizon de preuve",
            attribution.get("evidence_horizon", "N/D"),
            "",
            _horizon_read(str(attribution.get("evidence_horizon") or "")),
            "Plus l’horizon réel est long, plus une sous-performance devient significative.",
        ),
        _row(
            "Problèmes de processus",
            _issue_status(int(safe_float(attribution.get("process_issue_count")) or 0)),
            str(int(safe_float(attribution.get("process_issue_count")) or 0)),
            issue_text,
            "Indique si la sous-performance semble venir d’une mécanique perfectible plutôt que du marché.",
        ),
        _row(
            "Diagnostic d’attribution",
            attribution.get("status", "N/D"),
            "",
            attribution.get("interpretation", ""),
            "Classe la sous-performance avant de laisser le modèle s’auto-ajuster.",
        ),
        _row(
            "Gouverneur de correction",
            attribution.get("correction_governor", "N/D"),
            "",
            attribution.get("recommended_posture", ""),
            attribution.get("guardrail", ""),
        ),
    ]


def correction_governor_allows_auto_apply(attribution: dict[str, Any] | None) -> bool:
    if not attribution:
        return True
    return bool(attribution.get("can_auto_apply_safe_tuning"))


def correction_governor_max_changes(attribution: dict[str, Any] | None, default: int) -> int:
    if not attribution:
        return max(1, default)
    allowed = int(safe_float(attribution.get("max_safe_changes_allowed")) or 0)
    if allowed <= 0:
        return 0
    return max(1, min(default, allowed))


def _account_performance_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "UNAVAILABLE", "preferred_excess_vs_sp500": None, "basis": "NONE"}
    row = next((item for item in rows if str(item.get("account_type") or "") == "ALL_ACCOUNTS"), rows[0])
    twr_excess = safe_float(row.get("twr_excess_vs_sp500"))
    xirr_excess = safe_float(row.get("xirr_excess_vs_sp500"))
    simple_excess = safe_float(row.get("excess_return_vs_sp500"))
    if twr_excess is not None:
        excess = twr_excess
        basis = "TWR"
        status = str(row.get("twr_status") or row.get("comparison_status") or "AVAILABLE")
    elif xirr_excess is not None:
        excess = xirr_excess
        basis = "XIRR"
        status = str(row.get("xirr_status") or row.get("comparison_status") or "AVAILABLE")
    else:
        excess = simple_excess
        basis = "SIMPLE"
        status = str(row.get("comparison_status") or "AVAILABLE")
    return {
        "status": status or "AVAILABLE",
        "preferred_excess_vs_sp500": excess,
        "basis": basis,
        "value_added_vs_sp500_cad": safe_float(row.get("value_added_vs_sp500_cad")),
    }


def _backtest_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"status": "NO_BACKTEST", "negative_period_count": 0, "avg_excess_value": None}
    excess_values = [safe_float(row.get("excess_value_vs_vfv")) for row in rows]
    excess_values = [value for value in excess_values if value is not None]
    negative_count = sum(1 for value in excess_values if value < 0)
    avg_excess = sum(excess_values) / len(excess_values) if excess_values else None
    if not excess_values:
        status = "NO_BACKTEST"
    elif negative_count == 0:
        status = "BACKTEST_SUPPORTIVE"
    elif negative_count == len(excess_values):
        status = "BACKTEST_WEAK"
    else:
        status = "BACKTEST_MIXED"
    return {
        "status": status,
        "negative_period_count": negative_count,
        "avg_excess_value": avg_excess,
    }


def _process_snapshot(model_metrics: dict[str, Any], targets: dict[str, float]) -> dict[str, Any]:
    issues: list[str] = []
    severe = 0

    def add(condition: bool, message: str, severe_condition: bool = False) -> None:
        nonlocal severe
        if condition:
            issues.append(message)
            if severe_condition:
                severe += 1

    avg_vfv = safe_float(model_metrics.get("avg_vfv")) or 0.0
    avg_core = safe_float(model_metrics.get("avg_core")) or 0.0
    avg_turnover = safe_float(model_metrics.get("avg_allocation_turnover")) or 0.0
    primary_change = safe_float(model_metrics.get("primary_change_rate")) or 0.0
    avg_single = safe_float(model_metrics.get("avg_max_single")) or 0.0
    high_cycle = safe_float(model_metrics.get("high_cycle_day_rate")) or 0.0
    extreme_cycle = safe_float(model_metrics.get("extreme_cycle_day_rate")) or 0.0
    low_data = safe_float(model_metrics.get("low_data_day_rate")) or 0.0
    decision_quality = safe_float(model_metrics.get("avg_decision_quality"))
    health_status = str(model_metrics.get("health_status") or "")

    add(
        avg_vfv > targets["vfv_high"] and avg_core < targets["core_low"],
        f"VFV moyen élevé ({pct(avg_vfv)}) et exposition core faible ({pct(avg_core)}).",
        avg_vfv > targets["vfv_high"] + 0.15,
    )
    add(
        avg_turnover > targets["turnover_high"] or primary_change > targets["turnover_high"],
        f"Rotation ou changement du titre principal élevé ({pct(avg_turnover)} / {pct(primary_change)}).",
        avg_turnover > targets["turnover_high"] + 0.20,
    )
    add(
        avg_single > targets["max_single_high"],
        f"Plus gros bloc moyen élevé ({pct(avg_single)}).",
        avg_single > targets["max_single_high"] + 0.15,
    )
    add(
        high_cycle > targets["cycle_high"] or extreme_cycle > max(0.10, targets["cycle_high"] * 0.55),
        f"Exposition répétée à des thèmes cycliques/bulles ({pct(high_cycle)} élevé, {pct(extreme_cycle)} extrême).",
        extreme_cycle > max(0.20, targets["cycle_high"] * 0.80),
    )
    add(
        low_data > targets["low_data_high"],
        f"Trop de titres financés avec données faibles ({pct(low_data)}).",
        low_data > targets["low_data_high"] + 0.15,
    )
    if decision_quality is not None:
        add(
            decision_quality < targets["decision_quality_low"],
            f"Qualité moyenne des décisions faible ({decision_quality:.1f}/100).",
            decision_quality < targets["decision_quality_low"] - 10,
        )
    add(
        health_status in {"TOO_DEFENSIVE", "TOO_VOLATILE", "TOO_CONCENTRATED", "NEEDS_REVIEW"},
        f"Santé du modèle à surveiller ({health_status}).",
        health_status == "NEEDS_REVIEW",
    )
    return {
        "issues": issues,
        "issue_count": len(issues),
        "severe_issue_count": severe,
    }


def _underperformance_level(excess: float | None, status: str) -> str:
    status_text = str(status or "").upper()
    if excess is None and "UNDERPERFORM" not in status_text and "BEHIND" not in status_text:
        return "UNKNOWN"
    if excess is None:
        return "MATERIAL"
    if excess >= 0:
        return "NONE"
    if excess <= -0.10:
        return "SEVERE"
    if excess <= -0.05:
        return "MATERIAL"
    if excess <= -0.02:
        return "MILD"
    return "NOISE"


def _evidence_horizon(span_days: int, sample_count: int) -> str:
    if sample_count < 4 or span_days < 120:
        return "TOO_SHORT"
    if span_days < 450:
        return "AROUND_1_YEAR"
    if span_days < 1275:
        return "TWO_TO_THREE_YEARS"
    if span_days < 1825:
        return "FOUR_YEARS"
    return "FIVE_YEARS_PLUS"


def _attribution_status(
    *,
    underperformance_level: str,
    process_issue_count: int,
    severe_process_issue_count: int,
    evidence_horizon: str,
    backtest_status: str,
) -> str:
    if underperformance_level in {"NONE", "NOISE"}:
        return "NO_UNDERPERFORMANCE"
    if underperformance_level == "UNKNOWN":
        return "INSUFFICIENT_PERFORMANCE_DATA"
    if evidence_horizon == "TOO_SHORT":
        return "INSUFFICIENT_EVIDENCE"

    process_warning = process_issue_count >= 2 or severe_process_issue_count >= 1
    backtest_weak = backtest_status == "BACKTEST_WEAK"

    if evidence_horizon == "AROUND_1_YEAR":
        if process_warning:
            return "PROCESS_WARNING"
        return "TEMPORARY_REGIME_LAG"

    if evidence_horizon in {"TWO_TO_THREE_YEARS", "FOUR_YEARS"}:
        if process_warning or backtest_weak:
            return "CORRECTION_LIKELY_NEEDED"
        return "JUSTIFIED_OR_ACCEPTABLE_LAG"

    if underperformance_level in {"MATERIAL", "SEVERE"} and (process_warning or backtest_weak):
        return "MANUAL_STRATEGIC_REVIEW_NEEDED"
    if underperformance_level == "SEVERE":
        return "CORRECTION_LIKELY_NEEDED"
    return "JUSTIFIED_OR_ACCEPTABLE_LAG"


def _correction_governor(status: str, process_issue_count: int, evidence_horizon: str) -> dict[str, Any]:
    if status == "INSUFFICIENT_PERFORMANCE_DATA":
        return {
            "correction_governor": "PROCESS_ONLY_TUNING",
            "can_auto_apply_safe_tuning": True,
            "max_safe_changes_allowed": 2,
            "recommended_posture": "La performance vs S&P 500 n’est pas encore attribuable; autoriser seulement les corrections mécaniques déjà prouvées par l’audit.",
            "guardrail": "N’autorise pas une correction basée sur la performance, seulement sur des dérives de processus.",
        }
    if status == "INSUFFICIENT_EVIDENCE":
        return {
            "correction_governor": "OBSERVE_ONLY",
            "can_auto_apply_safe_tuning": False,
            "max_safe_changes_allowed": 0,
            "recommended_posture": "Observer, accumuler plus d’historique et éviter toute correction automatique.",
            "guardrail": "Protège contre l’optimisation sur trop peu de données.",
        }
    if status in {"TEMPORARY_REGIME_LAG", "JUSTIFIED_OR_ACCEPTABLE_LAG"}:
        return {
            "correction_governor": "THROTTLE_SAFE_TUNING",
            "can_auto_apply_safe_tuning": process_issue_count >= 1,
            "max_safe_changes_allowed": 1 if process_issue_count >= 1 else 0,
            "recommended_posture": "Ne pas courir après le S&P 500; corriger seulement un petit signal mécanique clairement observé.",
            "guardrail": "Réduit le risque d’over-correction après une période défavorable mais acceptable.",
        }
    if status == "PROCESS_WARNING":
        return {
            "correction_governor": "THROTTLE_SAFE_TUNING",
            "can_auto_apply_safe_tuning": True,
            "max_safe_changes_allowed": 1,
            "recommended_posture": "Autoriser au maximum un micro-ajustement SAFE; la sous-performance n’est pas encore assez longue.",
            "guardrail": "Évite une réaction excessive après environ un an.",
        }
    if status == "CORRECTION_LIKELY_NEEDED":
        return {
            "correction_governor": "ALLOW_SAFE_TUNING",
            "can_auto_apply_safe_tuning": True,
            "max_safe_changes_allowed": 2 if evidence_horizon in {"TWO_TO_THREE_YEARS", "FOUR_YEARS"} else 1,
            "recommended_posture": "Permettre des ajustements SAFE graduels, sans toucher aux règles vitales.",
            "guardrail": "Corrige progressivement sans réécrire la stratégie.",
        }
    if status == "MANUAL_STRATEGIC_REVIEW_NEEDED":
        return {
            "correction_governor": "MANUAL_REVIEW_ONLY",
            "can_auto_apply_safe_tuning": False,
            "max_safe_changes_allowed": 0,
            "recommended_posture": "Ne pas laisser l’agent se réparer seul; demander une revue stratégique humaine.",
            "guardrail": "Évite une auto-réécriture dangereuse après plusieurs années difficiles.",
        }
    return {
        "correction_governor": "NORMAL_SAFE_TUNING",
        "can_auto_apply_safe_tuning": True,
        "max_safe_changes_allowed": 3,
        "recommended_posture": "Aucune sous-performance significative; conserver les règles normales d’amélioration.",
        "guardrail": "Les corrections restent limitées aux paramètres secondaires.",
    }


def _status_interpretation(status: str) -> str:
    return {
        "NO_UNDERPERFORMANCE": "Aucune sous-performance significative détectée; les corrections doivent rester basées sur la mécanique, pas sur la performance.",
        "INSUFFICIENT_PERFORMANCE_DATA": "La performance réelle vs S&P 500 n’est pas assez exploitable pour attribuer un retard.",
        "INSUFFICIENT_EVIDENCE": "La sous-performance existe peut-être, mais l’historique est trop court pour corriger le modèle sans risque d’overfitting.",
        "TEMPORARY_REGIME_LAG": "La sous-performance ressemble davantage à un retard de régime qu’à une erreur de modèle démontrée.",
        "JUSTIFIED_OR_ACCEPTABLE_LAG": "Le retard peut être acceptable si le processus reste sain et discipliné.",
        "PROCESS_WARNING": "La sous-performance est encore jeune, mais certains signaux mécaniques méritent un micro-ajustement prudent.",
        "CORRECTION_LIKELY_NEEDED": "La sous-performance est accompagnée de signaux mécaniques; des ajustements SAFE graduels sont justifiés.",
        "MANUAL_STRATEGIC_REVIEW_NEEDED": "La sous-performance est persistante et sérieuse; il faut une revue humaine plutôt qu’une auto-correction libre.",
    }.get(status, "Diagnostic non reconnu.")


def _underperformance_read(attribution: dict[str, Any]) -> str:
    status = str(attribution.get("realized_performance_status") or "N/D")
    excess = safe_float(attribution.get("preferred_excess_vs_sp500"))
    if excess is None:
        return f"Statut réel: {status}; écart chiffré non disponible."
    return f"Statut réel: {status}; écart préféré vs S&P 500: {pct(excess)}."


def _horizon_read(status: str) -> str:
    return {
        "TOO_SHORT": "Historique trop court: une correction automatique serait fragile.",
        "AROUND_1_YEAR": "Environ un an: signal utile, mais encore insuffisant pour changer fortement le modèle.",
        "TWO_TO_THREE_YEARS": "Deux à trois ans: le signal devient plus sérieux si la mécanique montre aussi des faiblesses.",
        "FOUR_YEARS": "Quatre ans: la sous-performance commence à devenir très significative.",
        "FIVE_YEARS_PLUS": "Cinq ans ou plus: une sous-performance persistante exige une revue stratégique.",
    }.get(status, "Horizon non reconnu.")


def _issue_status(count: int) -> str:
    if count <= 0:
        return "CLEAN_PROCESS"
    if count == 1:
        return "MINOR_PROCESS_SIGNAL"
    if count <= 3:
        return "PROCESS_WARNING"
    return "PROCESS_WEAKNESS"


def _row(metric: str, status: Any, value: Any, interpretation: str, impact: str) -> dict[str, Any]:
    return {
        "metric": metric,
        "status": str(status or ""),
        "value": "" if value is None else str(value),
        "interpretation": interpretation,
        "impact": impact,
    }
