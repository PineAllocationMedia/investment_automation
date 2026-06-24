from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


CRITERION_FIELDS = {
    "C1": ["roic_5y_avg"],
    "C2": ["net_margin_stable_or_expanding"],
    "C3": ["eps_growth_5y"],
    "C4": ["moat_clear"],
    "C5": ["eps_growth_estimated_3_5y"],
    "C6": ["sector_cagr_estimated"],
    "C9": ["valuation_vs_5y_avg_ok"],
    "C10": ["fair_value"],
}


def compute_proof_score(
    manual: dict[str, Any],
    market: dict[str, Any],
    benchmark: dict[str, Any],
    score: dict[str, Any],
    reliability: dict[str, Any],
) -> dict[str, Any]:
    """Split the score between confirmed evidence and automatic estimates.

    The full score still powers the model. This layer says how much of that
    score is supported by manual/research/free-market evidence versus proxies.
    """

    criteria = score.get("criteria") or {}
    manual_fields = _field_set(manual.get("manual_override_fields")) | _field_set(manual.get("research_report_fields"))
    auto_fields = _field_set(manual.get("auto_estimated_fields"))
    official_fields = _field_set(manual.get("official_supported_manual_fields")) | _field_set(
        manual.get("official_confirmed_manual_fields")
    )

    confirmed_points = 0.0
    estimate_supported_points = 0.0
    estimated_criteria: list[str] = []
    confirmed_criteria: list[str] = []

    for code, criterion in criteria.items():
        points = safe_float(criterion.get("points"))
        if points is None or points <= 0:
            continue
        confirmed_fraction = _confirmed_fraction(code, manual, market, benchmark, manual_fields, auto_fields, official_fields)
        if confirmed_fraction >= 1.0:
            confirmed_points += points
            confirmed_criteria.append(code)
        elif confirmed_fraction > 0:
            confirmed_part = points * confirmed_fraction
            confirmed_points += confirmed_part
            estimate_supported_points += points - confirmed_part
            confirmed_criteria.append(f"{code} partiel")
            estimated_criteria.append(f"{code} partiel")
        else:
            estimate_supported_points += points
            estimated_criteria.append(code)

    score_with_estimates = safe_float(score.get("score_total")) or 0.0
    score_confirmed_only = round(clamp(confirmed_points, 0, 10), 2)
    estimate_gap = round(max(0.0, score_with_estimates - score_confirmed_only), 2)
    evidence_level, penalty, reason = _evidence_level(
        score_with_estimates=score_with_estimates,
        score_confirmed_only=score_confirmed_only,
        estimate_gap=estimate_gap,
        estimated_criteria=estimated_criteria,
        reliability=reliability,
    )
    confidence_range = _score_confidence_range(
        score_with_estimates=score_with_estimates,
        score_confirmed_only=score_confirmed_only,
        estimate_gap=estimate_gap,
        evidence_level=evidence_level,
        reliability=reliability,
    )

    return {
        "score_with_estimates": round(score_with_estimates, 2),
        "score_confirmed_only": score_confirmed_only,
        "score_estimate_gap": estimate_gap,
        "score_estimated_points": round(estimate_supported_points, 2),
        "score_confirmed_criteria": confirmed_criteria,
        "score_estimated_criteria": estimated_criteria,
        "score_evidence_level": evidence_level,
        "score_evidence_penalty": penalty,
        "score_evidence_reason": reason,
        **confidence_range,
    }


def _confirmed_fraction(
    code: str,
    manual: dict[str, Any],
    market: dict[str, Any],
    benchmark: dict[str, Any],
    manual_fields: set[str],
    auto_fields: set[str],
    official_fields: set[str],
) -> float:
    if code == "C7":
        if benchmark.get("benchmark_usable_cagr") is not None and benchmark.get("benchmark_above_sma_200") is not None:
            return 1.0
        if benchmark.get("benchmark_usable_cagr") is not None or benchmark.get("benchmark_above_sma_200") is not None:
            return 0.5
        return 0.0

    if code == "C8":
        confirmed = 0
        if (
            _field_is_confirmed("forward_pe_manual", manual, manual_fields, auto_fields, official_fields)
            or market.get("forward_pe") is not None
        ):
            confirmed += 1
        if _field_is_confirmed("peg_manual", manual, manual_fields, auto_fields, official_fields) or market.get("peg") is not None:
            confirmed += 1
        return confirmed / 2

    required_fields = CRITERION_FIELDS.get(code, [])
    if not required_fields:
        return 0.0
    confirmed = sum(
        1 for field in required_fields if _field_is_confirmed(field, manual, manual_fields, auto_fields, official_fields)
    )
    return confirmed / len(required_fields)


def _field_is_confirmed(
    field: str,
    manual: dict[str, Any],
    manual_fields: set[str],
    auto_fields: set[str],
    official_fields: set[str],
) -> bool:
    if manual.get(field) is None:
        return False
    if field in manual_fields:
        return True
    if field in official_fields:
        return True
    if field in auto_fields:
        return False
    input_mode = str(manual.get("input_data_mode") or "").upper()
    return not input_mode.startswith("AUTO")


def _evidence_level(
    score_with_estimates: float,
    score_confirmed_only: float,
    estimate_gap: float,
    estimated_criteria: list[str],
    reliability: dict[str, Any],
) -> tuple[str, float, str]:
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()
    automation_evidence = str(reliability.get("automation_evidence_level") or "WEAK").upper()
    estimated_count = len(estimated_criteria)

    if estimate_gap <= 0.75 and score_confirmed_only >= 7.5:
        return (
            "CONFIRMED",
            0.0,
            "Le score est largement confirmé par des données manuelles, rapports locaux, sources officielles ou données gratuites directes.",
        )

    if automation_evidence == "STRONG" and reliability_level == "HIGH" and dependency != "HIGH":
        penalty = 1.5 if estimate_gap >= 2.0 else 0.5
        return (
            "AUTOMATED_STRONG",
            penalty,
            "Le score repose beaucoup sur des estimations, mais les preuves automatiques et officielles disponibles sont assez complètes et cohérentes.",
        )

    if score_with_estimates >= 8.5 and score_confirmed_only < 6.5:
        return (
            "INSUFFICIENT_CONFIRMED",
            10.0,
            "Le score complet est élevé, mais trop peu de points sont confirmés pour justifier une grosse allocation sans validation.",
        )

    if estimate_gap >= 2.0 or dependency == "HIGH" or estimated_count >= 6:
        return (
            "ESTIMATE_HEAVY",
            7.0,
            "Une part importante du score dépend de proxys automatiques; allocation possible mais prudente.",
        )

    if estimate_gap >= 1.0 or reliability_level == "MEDIUM":
        return (
            "MIXED",
            2.5,
            "Le score combine des preuves confirmées et des estimations automatiques; la conclusion reste utilisable.",
        )

    return "MOSTLY_CONFIRMED", 0.0, "Le score est suffisamment appuyé par les preuves disponibles."


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.replace(";", ",").split(",") if part.strip()}
    return {str(item).strip() for item in value if str(item).strip()}


def _score_confidence_range(
    score_with_estimates: float,
    score_confirmed_only: float,
    estimate_gap: float,
    evidence_level: str,
    reliability: dict[str, Any],
) -> dict[str, Any]:
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()

    if evidence_level == "CONFIRMED":
        downside = 0.25
        upside = 0.25
    elif evidence_level == "MOSTLY_CONFIRMED":
        downside = 0.45
        upside = 0.25
    elif evidence_level == "AUTOMATED_STRONG":
        downside = max(0.65, min(1.15, estimate_gap * 0.45))
        upside = 0.35
    elif evidence_level == "MIXED":
        downside = max(0.90, min(1.65, estimate_gap * 0.70))
        upside = 0.35
    else:
        downside = max(1.35, min(2.60, estimate_gap))
        upside = 0.40

    if reliability_level == "LOW":
        downside += 0.70
    elif reliability_level == "MEDIUM":
        downside += 0.25
    if dependency == "HIGH":
        downside += 0.35

    low = score_with_estimates - downside
    if evidence_level in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
        low = min(low, score_confirmed_only + 0.75)
    high = score_with_estimates + upside

    low = round(clamp(low, 0, 10), 2)
    high = round(clamp(high, 0, 10), 2)
    width = round(max(0.0, high - low), 2)
    label = _range_label(width, scale=10)

    return {
        "score_confidence_low": low,
        "score_confidence_high": high,
        "score_confidence_range": f"{low:.2f}-{high:.2f}",
        "score_confidence_label": label,
        "score_confidence_reason": _score_confidence_reason(label, evidence_level, reliability_level, dependency),
    }


def _range_label(width: float, scale: int) -> str:
    if scale == 10:
        if width <= 0.75:
            return "TIGHT"
        if width <= 1.50:
            return "NORMAL"
        if width <= 2.50:
            return "WIDE"
        return "VERY_WIDE"
    if width <= 6:
        return "TIGHT"
    if width <= 11:
        return "NORMAL"
    if width <= 18:
        return "WIDE"
    return "VERY_WIDE"


def _score_confidence_reason(label: str, evidence_level: str, reliability_level: str, dependency: str) -> str:
    if label == "TIGHT":
        return "Fourchette serrée: le score est bien appuyé par des données confirmées ou très cohérentes."
    if label == "NORMAL":
        return "Fourchette normale: le score reste utilisable, avec une part raisonnable d’estimations."
    if label == "WIDE":
        return (
            "Fourchette large: le score central est utile, mais dépend davantage de proxys, de données incomplètes "
            f"ou d’une preuve {evidence_level}."
        )
    return (
        "Fourchette très large: interpréter le score comme une zone approximative avant validation, surtout avec "
        f"fiabilité {reliability_level} et dépendance aux estimations {dependency}."
    )
