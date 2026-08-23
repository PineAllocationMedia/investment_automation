from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .evidence_provenance import research_field_confidence
from .source_conflict_engine import summarize_conflict_profile
from .utils import clamp


CORE_RELIABILITY_FIELDS = {
    "roic_5y_avg",
    "net_margin_stable_or_expanding",
    "eps_growth_5y",
    "moat_clear",
    "eps_growth_estimated_3_5y",
    "sector_cagr_estimated",
    "fair_value",
    "valuation_vs_5y_avg_ok",
    "forward_pe_growth_acceptable",
    "management_quality_good",
    "balance_sheet_strong",
    "margin_or_profitability_under_pressure",
}

QUALITY_GATE_FIELDS = {
    "roic_5y_avg",
    "eps_growth_5y",
    "eps_growth_estimated_3_5y",
    "moat_clear",
    "fair_value",
    "valuation_vs_5y_avg_ok",
    "management_quality_good",
    "balance_sheet_strong",
}

QUALITY_ORDER = {"UNCERTAIN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}
QUALITY_BY_RANK = {rank: quality for quality, rank in QUALITY_ORDER.items()}
CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
CONFIDENCE_BY_RANK = {rank: confidence for confidence, rank in CONFIDENCE_ORDER.items()}


def compute_data_reliability(manual: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    auto_fields = _field_set(manual.get("auto_estimated_fields"))
    calibration_applied_fields = _field_set(manual.get("calibration_applied_fields"))
    manual_fields = _field_set(manual.get("manual_override_fields"))
    research_fields = {
        field
        for field in _field_set(manual.get("research_report_fields"))
        if research_field_confidence(manual, field) != "LOW"
    }
    official_supported_fields = _field_set(manual.get("official_supported_manual_fields"))
    official_confirmed_fields = _field_set(manual.get("official_confirmed_manual_fields"))
    official_evidence_fields = official_supported_fields | official_confirmed_fields
    official_conflicts = _as_values(manual.get("official_data_conflicts"))
    official_conflict_profile = summarize_conflict_profile(official_conflicts)
    auto_quality = str(manual.get("auto_source_quality") or "").upper()
    input_mode = str(manual.get("input_data_mode") or "").upper()
    missing_count = int(score.get("score_missing_data_count") or 0)
    freshness = compute_research_report_freshness(manual)
    freshness_penalty = float(freshness.get("research_report_freshness_penalty") or 0.0)
    freshness_requires_validation = bool(freshness.get("research_report_requires_fresh_validation"))
    text_quality_penalty, text_quality_requires_validation, text_quality_reason = _research_text_quality_penalty(manual)

    if not auto_fields and not input_mode.startswith("AUTO"):
        reliability = round(clamp(100.0 - freshness_penalty - text_quality_penalty, 0, 100), 2)
        level = _reliability_level(reliability)
        reasons = ["Données traitées comme manuelles ou déjà confirmées."]
        if freshness_penalty:
            reasons.append(str(freshness.get("research_report_freshness_reason")))
        if text_quality_reason:
            reasons.append(text_quality_reason)
        confirmed_critical = sorted((manual_fields | research_fields | official_evidence_fields) & CORE_RELIABILITY_FIELDS)
        return {
            "data_reliability_score": reliability,
            "data_reliability_level": level,
            "auto_estimate_dependency": "LOW",
            "automation_evidence_level": "CONFIRMED",
            "auto_critical_fields": [],
            "confirmed_critical_fields": confirmed_critical,
            "official_supported_fields": sorted(official_supported_fields),
            "official_confirmed_fields": sorted(official_confirmed_fields),
            "official_data_conflict_count": len(official_conflicts),
            "official_technical_conflict_count": official_conflict_profile["technical_conflict_count"],
            "official_material_conflict_count": official_conflict_profile["material_conflict_count"],
            "official_directional_conflict_count": official_conflict_profile["directional_conflict_count"],
            "official_weighted_conflict_score": official_conflict_profile["weighted_conflict_score"],
            "official_conflict_profile": official_conflict_profile["conflict_profile"],
            "official_evidence_level": _official_evidence_level(
                official_supported_fields,
                official_confirmed_fields,
                official_conflicts,
            ),
            "data_reliability_reasons": reasons,
            "requires_manual_validation_for_large_allocation": level != "HIGH" or freshness_requires_validation or text_quality_requires_validation,
            **_data_quality_audit_metrics(
                confirmed_critical=confirmed_critical,
                official_evidence_fields=official_evidence_fields,
                auto_critical=[],
                auto_quality_gates=[],
                missing_count=missing_count,
                official_conflict_profile=official_conflict_profile,
            ),
            **_freshness_public_fields(freshness),
        }

    low_authority_fields = auto_fields | calibration_applied_fields
    raw_auto_critical = sorted((low_authority_fields & CORE_RELIABILITY_FIELDS) - manual_fields - research_fields)
    raw_auto_quality_gates = sorted((low_authority_fields & QUALITY_GATE_FIELDS) - manual_fields - research_fields)
    auto_critical = sorted(set(raw_auto_critical) - official_evidence_fields)
    confirmed_critical = sorted((manual_fields | research_fields | official_evidence_fields) & CORE_RELIABILITY_FIELDS)
    confirmed_quality_gates = sorted((manual_fields | research_fields | official_evidence_fields) & QUALITY_GATE_FIELDS)
    auto_quality_gates = sorted(set(raw_auto_quality_gates) - official_evidence_fields)
    official_quality_gates = sorted(official_evidence_fields & QUALITY_GATE_FIELDS)
    official_evidence_level = _official_evidence_level(official_supported_fields, official_confirmed_fields, official_conflicts)
    automation_evidence = _automation_evidence_level(auto_quality, missing_count, raw_auto_critical, raw_auto_quality_gates)

    reliability = 100.0
    reasons: list[str] = []

    if automation_evidence == "STRONG":
        reliability -= 5
        reasons.append("Preuve automatique forte: données gratuites nombreuses, cohérentes et complètes.")
        if official_quality_gates:
            reasons.append(
                "Sources complémentaires appuient des champs fondamentaux clés: "
                + ", ".join(official_quality_gates[:6])
                + "."
            )
        if not confirmed_quality_gates:
            reliability -= 3
            reasons.append("Validation BNCD/manuelle utile mais non obligatoire pour une allocation modérée.")
    else:
        if len(auto_critical) >= 9:
            reliability -= 20
            reasons.append("Beaucoup de champs fondamentaux viennent de proxys automatiques.")
        elif len(auto_critical) >= 6:
            reliability -= 16
            reasons.append("Plusieurs champs fondamentaux viennent de proxys automatiques.")
        elif len(auto_critical) >= 3:
            reliability -= 10
            reasons.append("Quelques champs fondamentaux viennent de proxys automatiques.")
        elif auto_critical:
            reliability -= 5
            reasons.append("Une partie des champs fondamentaux est estimée automatiquement.")

        if len(confirmed_quality_gates) == 0 and auto_quality_gates:
            reliability -= 10
            reasons.append("Aucun champ de qualité clé n’est confirmé par saisie manuelle ou rapport local.")
        elif len(confirmed_quality_gates) <= 2 and len(auto_quality_gates) >= 4:
            reliability -= 8
            reasons.append("Les champs de qualité clés reposent surtout sur des estimations.")

    if missing_count > 3:
        reliability -= 20
        reasons.append("Plusieurs données critiques restent manquantes.")
    elif missing_count > 0:
        reliability -= min(12, missing_count * 4)
        reasons.append("Certaines données critiques restent manquantes.")

    if auto_quality == "LOW":
        reliability -= 15
        reasons.append("Qualité de source automatique faible.")
    elif auto_quality == "MEDIUM":
        reliability -= 5
        reasons.append("Qualité de source automatique moyenne.")

    conflict_penalty = _official_conflict_penalty(official_conflicts, official_evidence_fields)
    if conflict_penalty:
        reliability -= conflict_penalty
        reasons.append(
            "Conflits entre sources détectés: pénalité calibrée selon le type d’écart. "
            "Les écarts techniques/périodes sont moins pénalisés qu’un conflit directionnel réel."
        )

    provenance_conflict = bool(manual.get("fundamental_evidence_conflict"))
    if provenance_conflict:
        reliability -= 5
        reasons.append(
            "Conflit entre calibration historique et preuve fondamentale actuelle: validation manuelle requise."
        )

    if input_mode == "AUTO_ESTIMATED" and not confirmed_critical and automation_evidence != "STRONG":
        reliability -= 5
        reasons.append("Aucune validation manuelle ou PDF n’a encore confirmé les estimations.")

    if freshness_penalty:
        reliability -= freshness_penalty
        reasons.append(str(freshness.get("research_report_freshness_reason")))
    if text_quality_penalty:
        reliability -= text_quality_penalty
        reasons.append(text_quality_reason)

    reliability = round(clamp(reliability, 0, 100), 2)
    level = _reliability_level(reliability)

    if automation_evidence == "STRONG":
        dependency = "LOW" if len(official_quality_gates) >= 3 and len(auto_critical) <= 5 else "MEDIUM"
    elif len(auto_critical) >= 7 and len(confirmed_quality_gates) <= 2:
        dependency = "HIGH"
    elif len(auto_critical) >= 3:
        dependency = "MEDIUM"
    else:
        dependency = "LOW"

    if not reasons:
        reasons.append("Les données automatiques sont appuyées par suffisamment de confirmations.")

    return {
        "data_reliability_score": reliability,
        "data_reliability_level": level,
        "auto_estimate_dependency": dependency,
        "automation_evidence_level": automation_evidence,
        "auto_critical_fields": auto_critical,
        "calibration_applied_fields": sorted(calibration_applied_fields),
        "confirmed_critical_fields": confirmed_critical,
        "official_supported_fields": sorted(official_supported_fields),
        "official_confirmed_fields": sorted(official_confirmed_fields),
        "official_data_conflict_count": len(official_conflicts),
        "official_technical_conflict_count": official_conflict_profile["technical_conflict_count"],
        "official_material_conflict_count": official_conflict_profile["material_conflict_count"],
        "official_directional_conflict_count": official_conflict_profile["directional_conflict_count"],
        "official_weighted_conflict_score": official_conflict_profile["weighted_conflict_score"],
        "official_conflict_profile": official_conflict_profile["conflict_profile"],
        "official_evidence_level": official_evidence_level,
        "data_reliability_reasons": reasons,
        "requires_manual_validation_for_large_allocation": (
            level != "HIGH"
            or dependency == "HIGH"
            or freshness_requires_validation
            or text_quality_requires_validation
            or provenance_conflict
        ),
        **_data_quality_audit_metrics(
            confirmed_critical=confirmed_critical,
            official_evidence_fields=official_evidence_fields,
            auto_critical=auto_critical,
            auto_quality_gates=auto_quality_gates,
            missing_count=missing_count,
            official_conflict_profile=official_conflict_profile,
        ),
        **_freshness_public_fields(freshness),
    }


def apply_reliability_confidence_cap(manual: dict[str, Any], reliability: dict[str, Any]) -> dict[str, Any]:
    capped = dict(manual)
    current = str(capped.get("manual_confidence_level") or "MEDIUM").upper()
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()

    max_confidence = "HIGH"
    if reliability_level == "LOW":
        max_confidence = "LOW"
    elif reliability_level == "MEDIUM" or dependency == "HIGH":
        max_confidence = "MEDIUM"

    capped["manual_confidence_level"] = _min_confidence(current, max_confidence)
    capped["data_reliability_confidence_cap"] = max_confidence
    return capped


def apply_reliability_conviction_cap(conviction: dict[str, Any], reliability: dict[str, Any]) -> dict[str, Any]:
    adjusted = dict(conviction)
    score = float(adjusted.get("conviction_score") or 0.0)
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()
    automation_evidence = str(reliability.get("automation_evidence_level") or "WEAK").upper()

    cap: float | None = None
    if reliability_level == "LOW":
        cap = 55.0
    elif automation_evidence == "STRONG" and dependency != "HIGH":
        cap = 90.0
    elif dependency == "HIGH":
        cap = 75.0
    elif reliability_level == "MEDIUM":
        cap = 85.0

    if cap is not None and score > cap:
        adjusted["conviction_score_raw"] = score
        adjusted["conviction_score"] = cap
        adjusted["conviction_category"] = _conviction_category(cap)
        reasons = list(adjusted.get("conviction_reasons") or [])
        reasons.append(f"-{score - cap:.0f}: conviction plafonnée par fiabilité des données")
        adjusted["conviction_reasons"] = reasons
    return adjusted


def apply_reliability_cagr_cap(cagr: dict[str, Any], reliability: dict[str, Any]) -> dict[str, Any]:
    adjusted = dict(cagr)
    quality = str(adjusted.get("expected_cagr_quality") or "UNCERTAIN")
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()
    automation_evidence = str(reliability.get("automation_evidence_level") or "WEAK").upper()

    cap = "VERY_HIGH"
    if reliability_level == "LOW":
        cap = "UNCERTAIN"
    elif automation_evidence == "STRONG" and dependency != "HIGH":
        cap = "HIGH"
    elif dependency == "HIGH":
        cap = "MEDIUM"
    elif reliability_level == "MEDIUM":
        cap = "HIGH"

    capped_quality = _min_quality(quality, cap)
    if capped_quality != quality:
        adjusted["expected_cagr_quality_raw"] = quality
        adjusted["expected_cagr_quality"] = capped_quality
        adjusted["expected_cagr_reason"] = (
            f"{adjusted.get('expected_cagr_reason')} Fiabilité des données: qualité plafonnée à {capped_quality} "
            f"car plusieurs preuves reposent sur des estimations automatiques."
        )
    return adjusted


def apply_reliability_opportunity_cap(
    opportunity: dict[str, Any],
    reliability: dict[str, Any],
    thesis_status: str,
    liquidation_status: str,
    add_eligibility_status: str | None = None,
) -> dict[str, Any]:
    adjusted = dict(opportunity)
    status = str(adjusted.get("opportunity_cost_status") or "")
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()

    if status != "CLEARLY_BETTER_THAN_VFV":
        return adjusted
    if reliability_level == "HIGH" and dependency != "HIGH":
        return adjusted

    add_is_allowed = liquidation_status == "GREEN" or add_eligibility_status in {"ADD_ALLOWED", "ADD_ALLOWED_SMALL"}
    adjusted["opportunity_cost_status_raw"] = status
    adjusted["opportunity_cost_status"] = "SIMILAR_TO_VFV" if thesis_status == "INTACT" and add_is_allowed else "WORSE_THAN_VFV"
    adjusted["opportunity_cost_reason"] = (
        f"{adjusted.get('opportunity_cost_reason')} Avantage vs VFV plafonné: les données fondamentales "
        "reposent trop sur des estimations automatiques pour conclure clairement."
    )
    return adjusted


def compute_research_report_freshness(manual: dict[str, Any], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    report_fields = _field_set(manual.get("research_report_fields"))
    report_sources = _field_set(manual.get("research_report_sources"))
    if not report_fields and not report_sources:
        return _freshness_result(
            "NO_REPORT",
            None,
            None,
            0.0,
            False,
            "Aucun rapport BNCD/Morningstar local utilisé.",
        )

    parsed_dates = [_parse_report_date(value) for value in _as_values(manual.get("research_report_dates"))]
    parsed_dates = [value for value in parsed_dates if value is not None]
    if not parsed_dates:
        return _freshness_result(
            "UNKNOWN_DATE",
            None,
            None,
            10.0,
            True,
            "Rapport BNCD/Morningstar utilisé, mais date non détectée: validation fraîche recommandée avant grosse allocation.",
        )

    latest = max(parsed_dates)
    age_days = max(0, (today - latest).days)
    if age_days <= 180:
        return _freshness_result(
            "RECENT",
            latest.isoformat(),
            age_days,
            0.0,
            False,
            "Rapport BNCD/Morningstar récent: aucune pénalité de fraîcheur.",
        )
    if age_days <= 365:
        return _freshness_result(
            "AGING",
            latest.isoformat(),
            age_days,
            6.0,
            False,
            "Rapport BNCD/Morningstar plus ancien: légère pénalité de fraîcheur.",
        )
    return _freshness_result(
        "STALE",
        latest.isoformat(),
        age_days,
        22.0,
        True,
        "Rapport BNCD/Morningstar vieux de plus d’un an: pénalité importante et validation fraîche requise avant grosse allocation.",
    )


def _field_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        return {part.strip() for part in value.split(",") if part.strip()}
    return {str(part).strip() for part in value if str(part).strip()}


def _as_values(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part).strip() for part in value if str(part).strip()]


def _official_evidence_level(
    official_supported_fields: set[str],
    official_confirmed_fields: set[str],
    official_conflicts: list[str],
) -> str:
    if official_supported_fields:
        return "OFFICIAL_SUPPORT"
    if official_confirmed_fields:
        return "OFFICIAL_CONFIRMATION"
    if official_conflicts:
        return "OFFICIAL_CONFLICTS_ONLY"
    return "NO_OFFICIAL_EVIDENCE"


def _official_conflict_penalty(official_conflicts: list[str], official_evidence_fields: set[str]) -> float:
    if not official_conflicts:
        return 0.0
    profile = summarize_conflict_profile(official_conflicts)
    weighted = float(profile.get("weighted_conflict_score") or 0.0)
    directional = int(profile.get("directional_conflict_count") or 0)
    penalty = min(3.0, weighted * 0.75 + directional * 0.5)
    if official_evidence_fields:
        penalty = min(penalty, 2.0)
    return penalty


def _research_text_quality_penalty(manual: dict[str, Any]) -> tuple[float, bool, str]:
    report_fields = _field_set(manual.get("research_report_fields"))
    if not report_fields:
        return 0.0, False, ""

    status = str(manual.get("research_report_text_quality_status") or "").upper()
    if not status or status == "TEXT_OK":
        return 0.0, False, ""
    if status == "OCR_USED":
        return (
            6.0,
            True,
            "Rapport BNCD/Morningstar lu avec OCR: validation recommandée avant grosse allocation, car l’OCR peut mal lire certains chiffres.",
        )
    if status == "LOW_TEXT_QUALITY":
        return (
            4.0,
            True,
            "Qualité de texte du rapport BNCD/Morningstar moyenne: pénalité légère et validation utile avant grosse allocation.",
        )
    if status in {"OCR_NEEDED", "NO_TEXT_EXTRACTED", "UNREADABLE"}:
        return (
            10.0,
            True,
            "Rapport BNCD/Morningstar difficile à lire automatiquement: validation manuelle requise si ces champs influencent la décision.",
        )
    return 0.0, False, ""


def _parse_report_date(value: str) -> date | None:
    value = str(value or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y_%m_%d", "%m-%d-%Y", "%m/%d/%Y", "%m_%d_%Y"):
        try:
            return datetime.strptime(value[:10], fmt).date()
        except ValueError:
            continue
    return None


def _freshness_result(
    level: str,
    latest_date: str | None,
    age_days: int | None,
    penalty: float,
    requires_validation: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "research_report_freshness_level": level,
        "research_report_latest_date": latest_date,
        "research_report_age_days": age_days,
        "research_report_freshness_penalty": penalty,
        "research_report_requires_fresh_validation": requires_validation,
        "research_report_freshness_reason": reason,
    }


def _freshness_public_fields(freshness: dict[str, Any]) -> dict[str, Any]:
    return {
        "research_report_freshness_level": freshness.get("research_report_freshness_level"),
        "research_report_latest_date": freshness.get("research_report_latest_date"),
        "research_report_age_days": freshness.get("research_report_age_days"),
        "research_report_requires_fresh_validation": freshness.get("research_report_requires_fresh_validation"),
        "research_report_freshness_reason": freshness.get("research_report_freshness_reason"),
    }


def _data_quality_audit_metrics(
    *,
    confirmed_critical: list[str],
    official_evidence_fields: set[str],
    auto_critical: list[str],
    auto_quality_gates: list[str],
    missing_count: int,
    official_conflict_profile: dict[str, Any],
) -> dict[str, Any]:
    total_critical = len(CORE_RELIABILITY_FIELDS)
    total_quality = len(QUALITY_GATE_FIELDS)
    confirmed_set = set(confirmed_critical) & CORE_RELIABILITY_FIELDS
    official_set = set(official_evidence_fields) & CORE_RELIABILITY_FIELDS
    auto_set = set(auto_critical) & CORE_RELIABILITY_FIELDS
    auto_quality_set = set(auto_quality_gates) & QUALITY_GATE_FIELDS
    confirmed_rate = round(len(confirmed_set) / total_critical, 4) if total_critical else 0.0
    official_rate = round(len(official_set) / total_critical, 4) if total_critical else 0.0
    auto_rate = round(len(auto_set) / total_critical, 4) if total_critical else 0.0
    quality_auto_rate = round(len(auto_quality_set) / total_quality, 4) if total_quality else 0.0
    weighted_conflicts = float(official_conflict_profile.get("weighted_conflict_score") or 0.0)
    directional_conflicts = int(official_conflict_profile.get("directional_conflict_count") or 0)

    if confirmed_rate >= 0.65 and missing_count == 0 and directional_conflicts == 0:
        coverage_status = "STRONG_CONFIRMED_COVERAGE"
    elif confirmed_rate >= 0.35 or official_rate >= 0.25:
        coverage_status = "PARTIAL_COVERAGE"
    elif auto_rate >= 0.50:
        coverage_status = "AUTO_PROXY_HEAVY_COVERAGE"
    else:
        coverage_status = "THIN_COVERAGE"

    partial_flag = coverage_status in {"PARTIAL_COVERAGE", "AUTO_PROXY_HEAVY_COVERAGE", "THIN_COVERAGE"}
    note_parts = [
        f"champs critiques confirmés={len(confirmed_set)}/{total_critical}",
        f"preuves officielles={len(official_set)}/{total_critical}",
        f"proxys critiques={len(auto_set)}/{total_critical}",
    ]
    if missing_count:
        note_parts.append(f"données manquantes={missing_count}")
    if weighted_conflicts:
        note_parts.append(f"conflits pondérés={weighted_conflicts:.2f}")

    return {
        "critical_data_confirmed_field_rate": confirmed_rate,
        "critical_data_official_field_rate": official_rate,
        "critical_data_auto_proxy_field_rate": auto_rate,
        "critical_quality_auto_proxy_field_rate": quality_auto_rate,
        "critical_data_confirmed_field_count": len(confirmed_set),
        "critical_data_total_field_count": total_critical,
        "critical_data_auto_proxy_field_count": len(auto_set),
        "critical_data_missing_field_count": missing_count,
        "data_quality_partial_coverage_status": coverage_status,
        "data_quality_partial_coverage_flag": partial_flag,
        "data_quality_audit_note": "; ".join(note_parts),
    }


def _reliability_level(reliability: float) -> str:
    if reliability >= 80:
        return "HIGH"
    if reliability >= 60:
        return "MEDIUM"
    return "LOW"


def _automation_evidence_level(
    auto_quality: str,
    missing_count: int,
    auto_critical: list[str],
    auto_quality_gates: list[str],
) -> str:
    if auto_quality == "HIGH" and missing_count <= 1 and len(auto_critical) >= 8 and len(auto_quality_gates) >= 5:
        return "STRONG"
    if auto_quality in {"HIGH", "MEDIUM"} and missing_count <= 2 and len(auto_critical) >= 5:
        return "MODERATE"
    return "WEAK"


def _min_quality(current: str, cap: str) -> str:
    current_rank = QUALITY_ORDER.get(str(current).upper(), 0)
    cap_rank = QUALITY_ORDER.get(str(cap).upper(), 0)
    return QUALITY_BY_RANK[min(current_rank, cap_rank)]


def _min_confidence(current: str, cap: str) -> str:
    current_rank = CONFIDENCE_ORDER.get(str(current).upper(), 1)
    cap_rank = CONFIDENCE_ORDER.get(str(cap).upper(), 1)
    return CONFIDENCE_BY_RANK[min(current_rank, cap_rank)]


def _conviction_category(score: float) -> str:
    if score >= 85:
        return "VERY_HIGH"
    if score >= 70:
        return "HIGH"
    if score >= 55:
        return "MEDIUM"
    if score >= 40:
        return "LOW"
    return "VERY_LOW"
