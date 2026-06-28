from __future__ import annotations

from typing import Any

from .utils import safe_float


PROFILE_CAGR_CAPS = {
    "BANK": "MEDIUM",
    "INSURANCE": "MEDIUM",
    "UTILITY": "MEDIUM",
    "PIPELINE": "MEDIUM",
    "RESOURCES": "MEDIUM",
    "ENERGY_CYCLICAL": "MEDIUM",
    "REIT": "MEDIUM",
    "ALT_ASSET_MANAGER": "MEDIUM",
    "ASSET_MANAGER": "MEDIUM",
}
QUALITY_ORDER = {"UNCERTAIN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}
QUALITY_BY_RANK = {rank: quality for quality, rank in QUALITY_ORDER.items()}
# Module-private valuation severity labels shared by the functions below. Keep
# them stable because downstream reports display these exact strings.
VALUATION_OK = "VALUATION_OK"
MODERATELY_EXPENSIVE = "MODERATELY_EXPENSIVE"
EXPENSIVE_BUT_EXCEPTIONAL = "EXPENSIVE_BUT_EXCEPTIONAL"
EXTREMELY_EXPENSIVE = "EXTREMELY_EXPENSIVE"


def compute_expected_cagr_quality(
    manual: dict[str, Any],
    score: dict[str, Any],
    conviction_score: float,
    thesis_status: str,
) -> dict[str, Any]:
    score_total = safe_float(score.get("score_total")) or 0.0
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    roic = safe_float(score.get("roic_5y_avg"))
    sector_cagr = safe_float(score.get("sector_cagr_estimated"))
    price_to_fair_value = safe_float(score.get("price_to_fair_value"))
    missing_count = int(score.get("score_missing_data_count") or 0)
    valuation_non_extreme = price_to_fair_value is None or price_to_fair_value <= 1.40
    company_growth_quality = (
        eps_est is not None
        and eps_est >= 12
        and roic is not None
        and roic >= 15
        and manual.get("moat_clear") is True
    )
    sector_supportive = sector_cagr is not None and sector_cagr >= 6

    if missing_count > 3 or thesis_status == "UNCERTAIN":
        return {
            "expected_cagr_quality": "UNCERTAIN",
            "expected_cagr_reason": "Trop de données critiques manquent ou la thèse est incertaine.",
        }

    if (
        score_total >= 8.5
        and conviction_score >= 85
        and eps_est is not None
        and eps_est >= 15
        and roic is not None
        and roic >= 15
        and manual.get("moat_clear") is True
        and (sector_cagr is None or sector_cagr >= 8 or (score_total >= 9 and eps_est >= 18))
        and valuation_non_extreme
        and thesis_status == "INTACT"
    ):
        return _with_profile_cap(score, {
            "expected_cagr_quality": "VERY_HIGH",
            "expected_cagr_reason": "Qualité, croissance, moat et conviction très élevés sans valorisation extrême.",
        })

    if (
        score_total >= 8
        and conviction_score >= 70
        and eps_est is not None
        and eps_est >= 10
        and (sector_supportive or company_growth_quality)
        and thesis_status == "INTACT"
    ):
        return _with_profile_cap(score, {
            "expected_cagr_quality": "HIGH",
            "expected_cagr_reason": "Score élevé, conviction forte, thèse intacte et croissance entreprise suffisante.",
        })

    if 7 <= score_total < 8 and conviction_score >= 55 and thesis_status in {"INTACT", "UNCERTAIN"} and valuation_non_extreme:
        return _with_profile_cap(score, {
            "expected_cagr_quality": "MEDIUM",
            "expected_cagr_reason": "Qualité correcte, mais avantage long terme moins évident.",
        })

    return _with_profile_cap(score, {
        "expected_cagr_quality": "LOW",
        "expected_cagr_reason": "Score, conviction, croissance ou thèse insuffisants pour une qualité CAGR élevée.",
    })


def compute_quality_but_too_expensive(manual: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    score_total = safe_float(score.get("score_total")) or 0.0
    peg = safe_float(score.get("peg"))
    forward_pe = safe_float(score.get("forward_pe"))
    eps_est = safe_float(score.get("eps_growth_estimated_3_5y"))
    roic = safe_float(score.get("roic_5y_avg"))
    price_to_fair_value = safe_float(score.get("price_to_fair_value"))
    valuation_ok = manual.get("valuation_vs_5y_avg_ok")
    reasons: list[str] = []
    extreme_reasons: list[str] = []

    if peg is not None and peg > 3:
        reasons.append("PEG > 3")
        if peg > 4:
            extreme_reasons.append("PEG > 4")
    if price_to_fair_value is not None and price_to_fair_value > 1.40:
        reasons.append("prix / juste valeur > 1.40")
        if price_to_fair_value > 1.70:
            extreme_reasons.append("prix / juste valeur > 1.70")
    if forward_pe is not None and eps_est is not None and eps_est > 0 and forward_pe > max(35, eps_est * 3):
        reasons.append("Forward P/E très élevé par rapport à la croissance")
        if forward_pe > max(45, eps_est * 4):
            extreme_reasons.append("Forward P/E extrême par rapport à la croissance")
    if valuation_ok is False:
        reasons.append("valorisation supérieure à la moyenne 5 ans")

    flag = score_total >= 8 and bool(reasons)
    exceptional_quality = (
        flag
        and not extreme_reasons
        and score_total >= 8.5
        and eps_est is not None
        and eps_est >= 15
        and roic is not None
        and roic >= 15
        and manual.get("moat_clear") is True
        and (peg is None or peg <= 2.5)
        and (price_to_fair_value is None or price_to_fair_value <= 1.55)
        and (forward_pe is None or forward_pe <= max(35, eps_est * 2.1))
    )
    if not flag:
        severity = VALUATION_OK
    elif extreme_reasons:
        severity = EXTREMELY_EXPENSIVE
    elif exceptional_quality:
        severity = EXPENSIVE_BUT_EXCEPTIONAL
    else:
        severity = MODERATELY_EXPENSIVE

    severity_reason = _valuation_severity_reason(severity, reasons, extreme_reasons)
    return {
        "quality_but_too_expensive": flag,
        "quality_expensive_reasons": reasons,
        "valuation_severity": severity,
        "valuation_severity_reason": severity_reason,
    }


def _valuation_severity_reason(severity: str, reasons: list[str], extreme_reasons: list[str]) -> str:
    if severity == VALUATION_OK:
        return "Valorisation non bloquante selon les données disponibles."
    if severity == EXPENSIVE_BUT_EXCEPTIONAL:
        return (
            "Valorisation exigeante, mais qualité/croissance/moat assez forts pour permettre seulement "
            "une allocation limitée si les autres garde-fous sont verts."
        )
    if severity == EXTREMELY_EXPENSIVE:
        return "Valorisation extrême: " + "; ".join(extreme_reasons or reasons)
    return "Valorisation exigeante: " + "; ".join(reasons)


def _with_profile_cap(score: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    profile = str(score.get("business_profile") or "")
    cap = PROFILE_CAGR_CAPS.get(profile)
    if not cap:
        return result
    current = str(result.get("expected_cagr_quality") or "UNCERTAIN")
    capped = QUALITY_BY_RANK[min(QUALITY_ORDER.get(current, 0), QUALITY_ORDER[cap])]
    if capped == current:
        return result
    adjusted = dict(result)
    adjusted["expected_cagr_quality_raw"] = current
    adjusted["expected_cagr_quality"] = capped
    adjusted["expected_cagr_reason"] = (
        f"{result.get('expected_cagr_reason')} Profil {profile}: qualité CAGR plafonnée à {capped} "
        "car le secteur est défensif, régulé ou cyclique."
    )
    return adjusted
