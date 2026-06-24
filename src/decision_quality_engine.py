from __future__ import annotations

from typing import Any

from .add_eligibility_engine import ADD_ALLOWED_STATUSES
from .allocation_sensitivity_engine import sensitivity_penalty
from .utils import clamp, safe_float


DECISION_QUALITY_COLUMNS = [
    "decision_quality_level",
    "decision_quality_score",
    "summary",
    "main_reasons",
    "watchpoints",
    "why_not_high",
    "profile_calibration",
    "vfv_total_percent",
    "vfv_mandatory_percent",
    "vfv_redirection_percent",
    "core_allocation_percent",
    "allocated_core_count",
    "eligible_core_count",
    "data_quality_status",
    "risk_status",
    "stability_status",
    "sensitivity_status",
]


def compute_decision_quality(
    analyses: dict[str, dict[str, Any]],
    allocation_result: dict[str, Any],
    portfolio_risk: dict[str, Any],
    validation_warnings: list[str] | None = None,
    mode: str = "rational-aggressive",
    allocation_sensitivity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate how robust the final allocation recommendation is.

    This is deliberately an explanation layer. It does not change the allocation;
    it tells the user how much confidence to place in the recommendation.
    """

    validation_warnings = validation_warnings or []
    calibration = _profile_calibration(mode)
    allocations = allocation_result.get("allocations") or []
    total_capital = sum(safe_float(row.get("montant", row.get("amount"))) or 0.0 for row in allocations)
    mandatory_vfv_pct = safe_float(allocation_result.get("mandatory_vfv_percent")) or 0.0
    vfv_amount = sum(
        safe_float(row.get("montant", row.get("amount"))) or 0.0
        for row in allocations
        if str(row.get("destination", row.get("ticker"))) == "VFV.TO"
    )
    mandatory_vfv_amount = total_capital * mandatory_vfv_pct if total_capital > 0 else 0.0
    redirection_vfv_amount = max(0.0, vfv_amount - mandatory_vfv_amount)
    vfv_total_pct = vfv_amount / total_capital if total_capital > 0 else 0.0
    vfv_redirection_pct = redirection_vfv_amount / total_capital if total_capital > 0 else 0.0
    core_allocation_pct = max(0.0, 1.0 - vfv_total_pct) if total_capital > 0 else 0.0

    allocated_core: list[dict[str, Any]] = []
    for allocation_row in allocations:
        ticker = str(allocation_row.get("destination", allocation_row.get("ticker")))
        if ticker == "VFV.TO":
            continue
        analysis = analyses.get(ticker)
        if not analysis:
            continue
        amount = safe_float(allocation_row.get("montant", allocation_row.get("amount"))) or 0.0
        enriched = dict(analysis)
        enriched["_allocated_amount"] = amount
        enriched["_allocated_percent"] = amount / total_capital if total_capital > 0 else 0.0
        allocated_core.append(enriched)
    eligible_core = [row for row in analyses.values() if _is_core_candidate(row) and _looks_addable(row)]

    score = 100.0
    reasons: list[str] = []
    watchpoints: list[str] = []
    manual_review_required = False

    if total_capital <= 0:
        return _result(
            score=100.0,
            level="HIGH",
            summary="Aucune nouvelle cotisation à allouer; le rapport sert surtout à surveiller le portefeuille.",
            reasons=["Capital analysé à 0 $, donc aucune décision d’allocation active n’est requise."],
            watchpoints=[],
            why_not_high=[],
            profile_calibration=calibration["profile_calibration"],
            vfv_total_pct=0.0,
            mandatory_vfv_pct=mandatory_vfv_pct,
            vfv_redirection_pct=0.0,
            core_allocation_pct=0.0,
            allocated_core_count=0,
            eligible_core_count=len(eligible_core),
            data_status="NOT_APPLICABLE",
            risk_status=_risk_status(portfolio_risk),
            stability_status="NOT_APPLICABLE",
            sensitivity_status="NOT_APPLICABLE",
        )

    if validation_warnings:
        penalty = min(18.0, len(validation_warnings) * 4.0)
        score -= penalty
        watchpoints.append(f"{len(validation_warnings)} avertissement(s) de validation à lire dans le rapport.")

    if allocated_core:
        reasons.append("La cotisation est investie dans au moins une position core admissible, pas seulement dans VFV.")
    else:
        score -= 30.0
        watchpoints.append("Aucune action core n’a reçu de capital; VFV sert de destination de secours.")

    if eligible_core:
        reasons.append(f"{len(eligible_core)} position(s) core passent les principaux garde-fous d’ajout.")
    else:
        score -= 12.0
        watchpoints.append("Aucune position core ne passe clairement les filtres d’ajout.")

    data_penalty, data_status, data_reasons, data_manual = _data_quality_penalty(allocated_core)
    score -= data_penalty
    manual_review_required = manual_review_required or data_manual
    reasons.extend(data_reasons[:2])
    if data_reasons[2:]:
        watchpoints.extend(data_reasons[2:])

    confidence_penalty, confidence_reasons = _confidence_range_penalty(allocated_core)
    score -= confidence_penalty
    if confidence_penalty:
        watchpoints.extend(confidence_reasons)
    else:
        reasons.extend(confidence_reasons)

    cap_reasons = _reliability_cap_notes(allocated_core)
    if cap_reasons:
        reasons.extend(cap_reasons[:1])
        watchpoints.extend(cap_reasons[1:])

    double_counting_notes = _double_counting_notes(allocated_core)
    if double_counting_notes:
        reasons.extend(double_counting_notes[:1])
        watchpoints.extend(double_counting_notes[1:])

    hidden_cluster_notes = _hidden_cluster_notes(allocated_core)
    if hidden_cluster_notes:
        reasons.extend(hidden_cluster_notes[:1])
        watchpoints.extend(hidden_cluster_notes[1:])

    vfv_penalty, vfv_reasons = _vfv_penalty(vfv_total_pct, vfv_redirection_pct, allocated_core, calibration)
    score -= vfv_penalty
    if vfv_penalty:
        watchpoints.extend(vfv_reasons)
    else:
        reasons.extend(vfv_reasons)

    risk_penalty, risk_status, risk_reasons = _portfolio_risk_penalty(portfolio_risk, allocated_core, calibration)
    score -= risk_penalty
    if risk_penalty >= 10:
        watchpoints.extend(risk_reasons)
    else:
        reasons.extend(risk_reasons)

    clarity_penalty, clarity_reasons = _candidate_clarity_penalty(eligible_core, allocated_core, calibration)
    score -= clarity_penalty
    if clarity_penalty:
        watchpoints.extend(clarity_reasons)
    else:
        reasons.extend(clarity_reasons)

    stability_penalty, stability_status, stability_reasons = _stability_penalty(allocated_core, calibration)
    score -= stability_penalty
    if stability_penalty:
        watchpoints.extend(stability_reasons)
    else:
        reasons.extend(stability_reasons)

    sensitivity_score_penalty, sensitivity_status, sensitivity_reasons = sensitivity_penalty(allocation_sensitivity)
    score -= sensitivity_score_penalty
    if sensitivity_score_penalty:
        watchpoints.extend(sensitivity_reasons)
    else:
        reasons.extend(sensitivity_reasons)

    score = round(clamp(score, 0, 100), 2)
    level = _level(score, manual_review_required)
    summary = _summary(level, allocated_core, vfv_total_pct, vfv_redirection_pct)
    why_not_high = _why_not_high(
        score=score,
        level=level,
        data_status=data_status,
        risk_status=risk_status,
        stability_status=stability_status,
        vfv_redirection_pct=vfv_redirection_pct,
        allocated_core=allocated_core,
        watchpoints=_dedupe(watchpoints),
    )
    return _result(
        score=score,
        level=level,
        summary=summary,
        reasons=_dedupe(reasons)[:6],
        watchpoints=_dedupe(watchpoints)[:8],
        why_not_high=why_not_high,
        profile_calibration=calibration["profile_calibration"],
        vfv_total_pct=vfv_total_pct,
        mandatory_vfv_pct=mandatory_vfv_pct,
        vfv_redirection_pct=vfv_redirection_pct,
        core_allocation_pct=core_allocation_pct,
        allocated_core_count=len(allocated_core),
        eligible_core_count=len(eligible_core),
        data_status=data_status,
        risk_status=risk_status,
        stability_status=stability_status,
        sensitivity_status=sensitivity_status,
    )


def annotate_allocations_with_decision_quality(allocation_result: dict[str, Any]) -> None:
    quality = allocation_result.get("decision_quality") or {}
    for row in allocation_result.get("allocations", []):
        row["decision_quality"] = quality.get("decision_quality_level", "")
        row["decision_quality_score"] = quality.get("decision_quality_score", "")
        row["decision_quality_reason"] = quality.get("summary", "")


def decision_quality_rows_for_csv(decision_quality: dict[str, Any]) -> list[dict[str, Any]]:
    if not decision_quality:
        return [
            {
                "decision_quality_level": "",
                "decision_quality_score": "",
                "summary": "Aucune évaluation de qualité de décision disponible.",
            }
        ]
    return [
        {
            "decision_quality_level": decision_quality.get("decision_quality_level"),
            "decision_quality_score": decision_quality.get("decision_quality_score"),
            "summary": decision_quality.get("summary"),
            "main_reasons": "; ".join(decision_quality.get("main_reasons") or []),
            "watchpoints": "; ".join(decision_quality.get("watchpoints") or []),
            "why_not_high": "; ".join(decision_quality.get("why_not_high") or []),
            "profile_calibration": decision_quality.get("profile_calibration"),
            "vfv_total_percent": decision_quality.get("vfv_total_percent"),
            "vfv_mandatory_percent": decision_quality.get("vfv_mandatory_percent"),
            "vfv_redirection_percent": decision_quality.get("vfv_redirection_percent"),
            "core_allocation_percent": decision_quality.get("core_allocation_percent"),
            "allocated_core_count": decision_quality.get("allocated_core_count"),
            "eligible_core_count": decision_quality.get("eligible_core_count"),
            "data_quality_status": decision_quality.get("data_quality_status"),
            "risk_status": decision_quality.get("risk_status"),
            "stability_status": decision_quality.get("stability_status"),
            "sensitivity_status": decision_quality.get("sensitivity_status"),
        }
    ]


def _is_core_candidate(row: dict[str, Any]) -> bool:
    return row.get("ticker") != "VFV.TO" and row.get("benchmark_role") is not True and row.get("universe", "CORE_PORTFOLIO") == "CORE_PORTFOLIO"


def _looks_addable(row: dict[str, Any]) -> bool:
    if not _is_core_candidate(row):
        return False
    if row.get("ticker_validation_status") in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
        return False
    if row.get("thesis_status") != "INTACT":
        return False
    if row.get("add_eligibility_status") not in ADD_ALLOWED_STATUSES:
        return False
    if row.get("opportunity_cost_status") == "WORSE_THAN_VFV":
        return False
    if row.get("data_reliability_level") == "LOW":
        return False
    return (safe_float(row.get("capital_allocation_score")) or 0.0) >= 40


def _data_quality_penalty(rows: list[dict[str, Any]]) -> tuple[float, str, list[str], bool]:
    if not rows:
        return 8.0, "NO_CORE_ALLOCATION", ["La qualité des données des actions n’est pas testée, car aucune action ne reçoit de capital."], False

    penalty = 0.0
    reasons: list[str] = []
    manual_review = False
    weak_names: list[str] = []
    medium_names: list[str] = []
    proxy_names: list[str] = []
    coverage_names: list[str] = []
    proof_names: list[str] = []

    for row in rows:
        ticker = str(row.get("ticker"))
        validation = str(row.get("ticker_validation_status") or "")
        coverage = str(row.get("ticker_coverage_status") or "")
        reliability = str(row.get("data_reliability_level") or "MEDIUM")
        dependency = str(row.get("auto_estimate_dependency") or "")
        proof_level = str(row.get("score_evidence_level") or "")
        confidence = str(row.get("confidence_level") or row.get("manual_confidence_level") or "MEDIUM")
        if validation in {"NO_MARKET_DATA", "POSSIBLE_WRONG_TICKER"}:
            penalty += 40
            manual_review = True
            weak_names.append(ticker)
        elif coverage in {"LOW_FREE_DATA_COVERAGE", "NEEDS_BNCD_OR_MANUAL_CONFIRMATION"}:
            penalty += 8
            coverage_names.append(ticker)
        if reliability == "LOW":
            penalty += 25
            manual_review = True
            weak_names.append(ticker)
        elif reliability == "MEDIUM":
            penalty += 7
            medium_names.append(ticker)
        if dependency == "HIGH":
            penalty += 7
            proxy_names.append(ticker)
        if proof_level in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
            penalty += 6 if proof_level == "ESTIMATE_HEAVY" else 10
            proof_names.append(ticker)
        if confidence == "LOW":
            penalty += 8
            medium_names.append(ticker)

    penalty = min(45.0, penalty)
    if weak_names:
        reasons.append("Données faibles ou ticker à valider sur: " + ", ".join(_dedupe(weak_names)))
    if coverage_names:
        reasons.append("Certaines allocations reposent sur des titres valides mais mal couverts gratuitement: " + ", ".join(_dedupe(coverage_names)))
    if proxy_names:
        reasons.append("Dépendance élevée aux proxys automatiques sur: " + ", ".join(_dedupe(proxy_names)))
    if proof_names:
        reasons.append("Score élevé mais encore trop dépendant d’estimations sur: " + ", ".join(_dedupe(proof_names)))
    if medium_names:
        reasons.append("Fiabilité ou confiance moyenne sur: " + ", ".join(_dedupe(medium_names)))
    if not reasons:
        reasons.append("Les titres recommandés ont des données suffisamment fiables pour une décision mécanique.")

    if penalty >= 25:
        status = "WEAK"
    elif penalty >= 8:
        status = "WATCH"
    else:
        status = "ROBUST"
    return penalty, status, reasons, manual_review


def _confidence_range_penalty(rows: list[dict[str, Any]]) -> tuple[float, list[str]]:
    if not rows:
        return 0.0, []
    wide_names = []
    very_wide_names = []
    for row in rows:
        ticker = str(row.get("ticker"))
        labels = {
            str(row.get("score_confidence_label") or ""),
            str(row.get("conviction_confidence_label") or ""),
            str(row.get("capital_allocation_confidence_label") or ""),
        }
        if "VERY_WIDE" in labels:
            very_wide_names.append(ticker)
        elif "WIDE" in labels:
            wide_names.append(ticker)

    penalty = min(6.0, len(wide_names) * 1.5 + len(very_wide_names) * 3.0)
    if very_wide_names:
        return penalty, ["Fourchette de confiance très large sur: " + ", ".join(_dedupe(very_wide_names))]
    if wide_names:
        return penalty, ["Fourchette de confiance large sur: " + ", ".join(_dedupe(wide_names))]
    return 0.0, ["Les fourchettes de confiance des titres recommandés restent raisonnables."]


def _reliability_cap_notes(rows: list[dict[str, Any]]) -> list[str]:
    capped = [str(row.get("ticker")) for row in rows if row.get("reliability_cap_applied") is True]
    if capped:
        return [
            "Cap de fiabilité appliqué sur: "
            + ", ".join(_dedupe(capped))
            + ". Le titre reste admissible, mais le modèle évite une trop grosse allocation avec preuves incomplètes."
        ]
    statuses = [str(row.get("ticker")) for row in rows if str(row.get("reliability_cap_status") or "NONE") != "NONE"]
    if statuses:
        return [
            "Certaines positions ont une surveillance de fiabilité, mais le cap n’a pas réduit l’allocation finale: "
            + ", ".join(_dedupe(statuses))
            + "."
        ]
    return []


def _double_counting_notes(rows: list[dict[str, Any]]) -> list[str]:
    active = [
        f"{row.get('ticker')} ({row.get('double_counting_risk_level')})"
        for row in rows
        if str(row.get("double_counting_risk_level") or "LOW") in {"HIGH", "EXTREME"}
        or (safe_float(row.get("double_counting_adjustment")) or 0.0) <= -2
    ]
    if not active:
        return []
    return [
        "Amortisseur double-counting actif sur: "
        + ", ".join(_dedupe(active))
        + ". Il modère le sizing quand plusieurs signaux répètent le même narratif, sans bloquer l’achat."
    ]


def _hidden_cluster_notes(rows: list[dict[str, Any]]) -> list[str]:
    active = [
        f"{row.get('ticker')} ({row.get('hidden_cluster_risk_level')})"
        for row in rows
        if str(row.get("hidden_cluster_risk_level") or "LOW") in {"HIGH", "EXTREME"}
        or (safe_float(row.get("hidden_cluster_adjustment")) or 0.0) <= -2
    ]
    if not active:
        return []
    return [
        "Garde-fou cluster caché actif sur: "
        + ", ".join(_dedupe(active))
        + ". Il réduit légèrement le sizing quand la cotisation renforcerait un pari sous-jacent déjà chargé."
    ]


def _vfv_penalty(
    vfv_total_pct: float,
    vfv_redirection_pct: float,
    allocated_core: list[dict[str, Any]],
    calibration: dict[str, Any],
) -> tuple[float, list[str]]:
    if vfv_redirection_pct >= 0.35:
        penalty = 25.0
        if calibration["high_cagr_profile"] and allocated_core:
            penalty = 21.0
        return penalty, ["VFV reçoit une forte redirection: plusieurs actions n’ont pas pu absorber le capital sans violer les garde-fous."]
    if vfv_total_pct >= 0.50:
        return 22.0, ["VFV représente au moins la moitié de la cotisation; décision prudente mais moins offensive pour un profil high-CAGR."]
    if vfv_redirection_pct >= 0.20:
        return (12.0 if calibration["high_cagr_profile"] else 16.0), [
            "Une part importante de VFV vient d’une redirection, pas seulement de l’allocation obligatoire."
        ]
    if vfv_redirection_pct >= 0.10:
        return (5.0 if calibration["high_cagr_profile"] else 8.0), [
            "VFV reçoit une redirection modérée parce que certains titres sont limités par les garde-fous."
        ]
    if allocated_core:
        return 0.0, ["La part VFV reste principalement un filet de sécurité, pas un défaut majeur de candidats."]
    return 10.0, ["VFV reçoit la cotisation par défaut faute de candidat core assez robuste."]


def _portfolio_risk_penalty(
    portfolio_risk: dict[str, Any],
    allocated_core: list[dict[str, Any]],
    calibration: dict[str, Any],
) -> tuple[float, str, list[str]]:
    alerts = portfolio_risk.get("alerts") or []
    penalty = 0.0
    reasons: list[str] = []
    high_cagr = calibration["high_cagr_profile"]
    for alert in alerts:
        text = str(alert.get("alert") or "").lower()
        if "extrême" in text or "extreme" in text:
            penalty += 6 if high_cagr else 8
        elif "élev" in text or "forte" in text or "très concentré" in text:
            penalty += 2.5 if high_cagr else 4
        else:
            penalty += 0.5 if high_cagr else 1
    for row in allocated_core:
        cycle = str(row.get("cycle_bubble_risk_level") or "")
        monitoring = str(row.get("monitoring_status") or "NORMAL")
        if cycle == "EXTREME":
            penalty += 14
            reasons.append(f"{row.get('ticker')} reçoit du capital malgré un risque cycle/bulle EXTREME.")
        elif cycle == "HIGH":
            penalty += 5 if high_cagr else 7
            reasons.append(f"{row.get('ticker')} reçoit du capital avec un risque cycle/bulle HIGH, acceptable seulement avec sizing limité.")
        if monitoring not in {"", "NORMAL", "BENCHMARK"}:
            allocated_pct = safe_float(row.get("_allocated_percent")) or 0.0
            penalty += (1.5 if high_cagr else 3.0) + allocated_pct * (4.0 if high_cagr else 8.0)
            reasons.append(
                f"{row.get('ticker')} reçoit {allocated_pct:.0%} de la cotisation avec une surveillance active; "
                "le score tient compte du sizing réel."
            )

    penalty = min(35.0, penalty)
    if alerts:
        reasons.append(f"{len(alerts)} alerte(s) de concentration ou facteur commun existent dans le portefeuille.")
    if not reasons:
        reasons.append("Aucun risque de portefeuille majeur ne fragilise directement la décision.")
    if penalty >= 20:
        status = "ELEVATED"
    elif penalty >= 8:
        status = "WATCH"
    else:
        status = "ACCEPTABLE"
    return penalty, status, reasons


def _candidate_clarity_penalty(
    eligible_core: list[dict[str, Any]],
    allocated_core: list[dict[str, Any]],
    calibration: dict[str, Any],
) -> tuple[float, list[str]]:
    scores = sorted((safe_float(row.get("capital_allocation_score")) or 0.0, str(row.get("ticker"))) for row in eligible_core)
    scores.reverse()
    if not scores:
        return 10.0, ["Aucun candidat core admissible ne se détache clairement."]
    if len(scores) == 1:
        return 0.0, [f"{scores[0][1]} est le seul candidat core admissible; la décision est claire mais concentrée."]
    gap = scores[0][0] - scores[1][0]
    if gap < 3 and len(allocated_core) <= 1:
        return (4.0 if calibration["high_cagr_profile"] else 6.0), [
            "Les meilleurs candidats sont très proches; la sélection peut bouger avec de petites variations."
        ]
    if gap < 6:
        return (1.0 if calibration["high_cagr_profile"] else 3.0), [
            "Les meilleurs candidats sont proches; la décision est correcte mais sensible aux scores."
        ]
    return 0.0, [f"{scores[0][1]} se détache clairement du candidat suivant selon le capital_allocation_score."]


def _stability_penalty(rows: list[dict[str, Any]], calibration: dict[str, Any]) -> tuple[float, str, list[str]]:
    if not rows:
        return 4.0, "NO_CORE_ALLOCATION", ["Aucune allocation core: stabilité non observable sur les titres recommandés."]
    deteriorating = [str(row.get("ticker")) for row in rows if row.get("trend_status") == "DETERIORATING"]
    no_history = [str(row.get("ticker")) for row in rows if row.get("allocation_stability_status") == "NEUTRAL_NO_HISTORY"]
    changed = [str(row.get("ticker")) for row in rows if row.get("allocation_stability_status") in {"ALLOW_NEW_LEADER", "LET_IMPROVEMENT_LEAD"}]
    if deteriorating:
        return 14.0, "WEAKENING", ["Une allocation touche un titre en détérioration historique: " + ", ".join(deteriorating)]
    if changed:
        penalty = 0.0 if calibration["high_cagr_profile"] else 3.0
        return penalty, "RESPONSIVE", ["Le modèle accepte un nouveau leader ou une amélioration claire: " + ", ".join(changed)]
    if len(no_history) == len(rows):
        return (2.0 if calibration["high_cagr_profile"] else 4.0), "LIMITED_HISTORY", [
            "Les titres recommandés manquent encore d’historique local comparable."
        ]
    return 0.0, "STABLE", ["La recommandation ne semble pas provenir d’un changement historique non expliqué."]


def _risk_status(portfolio_risk: dict[str, Any]) -> str:
    alerts = portfolio_risk.get("alerts") or []
    if not alerts:
        return "ACCEPTABLE"
    if any("extrême" in str(row.get("alert") or "").lower() for row in alerts):
        return "ELEVATED"
    return "WATCH"


def _level(score: float, manual_review_required: bool) -> str:
    if manual_review_required:
        return "MANUAL_REVIEW_REQUIRED"
    if score >= 82:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    if score >= 35:
        return "LOW"
    return "MANUAL_REVIEW_REQUIRED"


def _profile_calibration(mode: str) -> dict[str, Any]:
    high_cagr = str(mode or "").lower() == "high-cagr"
    return {
        "high_cagr_profile": high_cagr,
        "profile_calibration": "HIGH_CAGR_LONG_TERM" if high_cagr else "STANDARD_RISK_ADJUSTED",
    }


def _why_not_high(
    score: float,
    level: str,
    data_status: str,
    risk_status: str,
    stability_status: str,
    vfv_redirection_pct: float,
    allocated_core: list[dict[str, Any]],
    watchpoints: list[str],
) -> list[str]:
    if level == "HIGH":
        return ["Rien de majeur: la recommandation atteint le niveau HIGH."]

    blockers: list[str] = []
    gap = max(0.0, 82.0 - score)
    blockers.append(f"Il manque environ {gap:.0f} point(s) pour atteindre HIGH.")
    if data_status not in {"ROBUST", "NOT_APPLICABLE"}:
        blockers.append("La qualité ou la couverture des données n’est pas parfaitement robuste.")
    if vfv_redirection_pct >= 0.10:
        blockers.append(f"VFV reçoit {vfv_redirection_pct:.0%} de redirection, signe que certains titres sont limités par les garde-fous.")
    if risk_status != "ACCEPTABLE":
        blockers.append("Le portefeuille contient encore des risques de concentration, devise ou facteur commun à surveiller.")
    active_monitoring = [str(row.get("ticker")) for row in allocated_core if str(row.get("monitoring_status") or "NORMAL") not in {"", "NORMAL", "BENCHMARK"}]
    if active_monitoring:
        blockers.append("Allocation vers des titres sous surveillance: " + ", ".join(active_monitoring) + ".")
    hot_cycle = [str(row.get("ticker")) for row in allocated_core if str(row.get("cycle_bubble_risk_level") or "") in {"HIGH", "EXTREME"}]
    if hot_cycle:
        blockers.append("Risque cycle/bulle/tendance sur: " + ", ".join(hot_cycle) + ".")
    if stability_status == "WEAKENING":
        blockers.append("Une détérioration historique affaiblit la robustesse.")
    elif stability_status in {"RESPONSIVE", "LIMITED_HISTORY"}:
        blockers.append("La recommandation bouge avec les nouvelles données ou manque encore d’historique local.")
    if len(blockers) < 4:
        blockers.extend(watchpoints[: 4 - len(blockers)])
    return _dedupe(blockers)[:6]


def _summary(level: str, allocated_core: list[dict[str, Any]], vfv_total_pct: float, vfv_redirection_pct: float) -> str:
    names = ", ".join(str(row.get("ticker")) for row in allocated_core) if allocated_core else "aucune action core"
    if level == "HIGH":
        return f"Recommandation robuste: {names}; VFV reste contrôlé et les garde-fous sont cohérents."
    if level == "MEDIUM":
        return f"Recommandation utilisable mais à surveiller: {names}; certains risques ou données réduisent la robustesse."
    if level == "LOW":
        return f"Recommandation mécanique prudente: {names}; VFV total={vfv_total_pct:.0%}, redirection={vfv_redirection_pct:.0%}."
    return "Validation manuelle recommandée avant de suivre mécaniquement cette allocation."


def _result(
    score: float,
    level: str,
    summary: str,
    reasons: list[str],
    watchpoints: list[str],
    why_not_high: list[str],
    profile_calibration: str,
    vfv_total_pct: float,
    mandatory_vfv_pct: float,
    vfv_redirection_pct: float,
    core_allocation_pct: float,
    allocated_core_count: int,
    eligible_core_count: int,
    data_status: str,
    risk_status: str,
    stability_status: str,
    sensitivity_status: str,
) -> dict[str, Any]:
    return {
        "decision_quality_level": level,
        "decision_quality_score": round(score, 2),
        "summary": summary,
        "main_reasons": _dedupe(reasons) or ["Aucune raison principale détectée."],
        "watchpoints": _dedupe(watchpoints) or ["Aucun point de fragilité majeur détecté."],
        "why_not_high": _dedupe(why_not_high) or ["Rien de majeur."],
        "profile_calibration": profile_calibration,
        "vfv_total_percent": round(vfv_total_pct, 4),
        "vfv_mandatory_percent": round(mandatory_vfv_pct, 4),
        "vfv_redirection_percent": round(vfv_redirection_pct, 4),
        "core_allocation_percent": round(core_allocation_pct, 4),
        "allocated_core_count": allocated_core_count,
        "eligible_core_count": eligible_core_count,
        "data_quality_status": data_status,
        "risk_status": risk_status,
        "stability_status": stability_status,
        "sensitivity_status": sensitivity_status,
    }


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
