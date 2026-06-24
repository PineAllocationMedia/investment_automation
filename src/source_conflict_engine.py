from __future__ import annotations

import re
from typing import Any

from .utils import safe_float


SOURCE_CONFLICT_COLUMNS = [
    "ticker",
    "ticker_display",
    "universe",
    "conflict_count",
    "technical_conflict_count",
    "material_conflict_count",
    "directional_conflict_count",
    "weighted_conflict_score",
    "conflict_profile",
    "severity",
    "conflicts",
    "conflict_interpretation",
    "source_policy",
    "recommended_action",
]

TECHNICAL_OR_PERIOD_FIELDS = {
    "capital_expenditures",
    "diluted_average_shares",
    "fcf_per_share",
    "free_cash_flow",
    "net_income",
    "operating_cash_flow",
    "share_count_cagr_3y",
    "share_count_cagr_5y",
    "share_count_growth_1y",
    "share_repurchases",
    "sbc_to_revenue",
    "stock_based_compensation",
    "total_revenue",
}

DIRECTIONAL_FIELDS = {
    "earnings_growth",
    "fcf_per_share_growth",
    "free_cash_flow_growth",
    "profit_margins",
    "revenue_growth",
}

MATERIAL_RATIO_FIELDS = {
    "debt_to_equity",
    "fcf_conversion",
    "free_cash_flow_margin",
    "gross_margins",
    "net_debt_to_fcf",
    "operating_margins",
    "return_on_assets",
    "return_on_equity",
}

_FIELD_RE = re.compile(r"^\s*([^:]+)\s*:")
_DIFF_RE = re.compile(r"ecart\s*=\s*([0-9]+(?:[.,][0-9]+)?)\s*%")
_YF_RE = re.compile(r"yfinance\s*=\s*([-+]?[0-9]+(?:[.,][0-9]+)?(?:e[-+]?[0-9]+)?)", re.IGNORECASE)
_SEC_RE = re.compile(r"\bSEC\s*=\s*([-+]?[0-9]+(?:[.,][0-9]+)?(?:e[-+]?[0-9]+)?)", re.IGNORECASE)
_CANADIAN_RE = re.compile(
    r"source_canadienne\s*=\s*([-+]?[0-9]+(?:[.,][0-9]+)?(?:e[-+]?[0-9]+)?)",
    re.IGNORECASE,
)


def build_source_conflict_rows(analysis_groups: dict[str, dict[str, dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for universe, group in analysis_groups.items():
        for ticker, analysis in sorted(group.items()):
            conflicts = _as_list(analysis.get("official_data_conflicts"))
            count = int(safe_float(analysis.get("official_data_conflict_count")) or len(conflicts))
            if count <= 0 and not conflicts:
                continue
            profile = summarize_conflict_profile(conflicts)
            severity = _severity(count, analysis, profile)
            rows.append(
                {
                    "ticker": ticker,
                    "ticker_display": analysis.get("ticker_display") or ticker,
                    "universe": universe,
                    "conflict_count": count,
                    "technical_conflict_count": profile["technical_conflict_count"],
                    "material_conflict_count": profile["material_conflict_count"],
                    "directional_conflict_count": profile["directional_conflict_count"],
                    "weighted_conflict_score": profile["weighted_conflict_score"],
                    "conflict_profile": profile["conflict_profile"],
                    "severity": severity,
                    "report_priority": _report_priority(universe, analysis),
                    "conflicts": _compact("; ".join(conflicts), 900),
                    "conflict_interpretation": profile["interpretation"],
                    "source_policy": _compact("; ".join(_as_list(analysis.get("official_source_policy"))), 500),
                    "recommended_action": _recommended_action(severity, analysis),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            int(row.get("report_priority") or 0),
            _severity_rank(row.get("severity")),
            int(row.get("conflict_count") or 0),
        ),
        reverse=True,
    )


def compact_source_conflict_rows(rows: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    if not rows:
        return [
            {
                "ticker": "",
                "universe": "",
                "severity": "AUCUNE_CONTRADICTION_VISIBLE",
                "conflict_count": "",
                "recommended_action": "Aucun conflit important entre sources gratuites/officielles détecté dans cette analyse.",
            }
        ]
    priority_rows = [row for row in rows if int(row.get("report_priority") or 0) > 0]
    display_rows = priority_rows or rows
    return [
        {
            "ticker": row.get("ticker_display") or row.get("ticker"),
            "universe": row.get("universe"),
            "severity": row.get("severity"),
            "conflict_count": row.get("conflict_count"),
            "conflict_profile": row.get("conflict_profile"),
            "recommended_action": row.get("recommended_action"),
        }
        for row in display_rows[:limit]
    ]


def source_conflict_summary(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "aucune contradiction importante entre sources gratuites/officielles."
    priority_rows = [row for row in rows if int(row.get("report_priority") or 0) > 0]
    if not priority_rows:
        return "aucune contradiction prioritaire sur positions core ou recommandations; détails complets dans latest_source_conflicts.csv."
    high = [row for row in priority_rows if row.get("severity") in {"HIGH_REVIEW", "REVIEW"}]
    tickers = ", ".join(str(row.get("ticker") or "") for row in priority_rows[:5])
    if high:
        return f"{len(priority_rows)} ticker(s) prioritaire(s) avec contradictions visibles, dont {len(high)} à revoir: {tickers}."
    return f"{len(priority_rows)} ticker(s) prioritaire(s) avec petites contradictions à surveiller: {tickers}."


def summarize_conflict_profile(conflicts: list[str]) -> dict[str, Any]:
    """Classify raw source gaps so technical differences do not look like thesis breaks."""

    classifications = [classify_source_conflict(text) for text in conflicts]
    technical = sum(1 for item in classifications if item["classification"] in {"TECHNICAL_OR_PERIOD", "MINOR_METHOD"})
    material = sum(1 for item in classifications if item["classification"] == "MATERIAL_REVIEW")
    directional = sum(1 for item in classifications if item["classification"] == "DIRECTIONAL_REVIEW")
    unknown = sum(1 for item in classifications if item["classification"] == "UNPARSED_REVIEW")
    weighted = round(sum(float(item["weight"]) for item in classifications), 2)
    if directional:
        profile = "DIRECTIONAL_REVIEW"
        interpretation = (
            "Au moins une source change le sens économique d'un champ clé; validation utile avant grosse allocation."
        )
    elif material:
        profile = "MATERIAL_REVIEW"
        interpretation = (
            "Écart matériel sur ratio/croissance comparable; probablement non bloquant, mais à valider si le titre reçoit beaucoup de capital."
        )
    elif technical:
        profile = "TECHNICAL_OR_PERIOD_DIFFERENCE"
        interpretation = (
            "Écart probablement lié aux périodes, unités, définitions ou calculs; faible impact mécanique."
        )
    elif unknown:
        profile = "UNPARSED_REVIEW"
        interpretation = "Écart de source non classé automatiquement; à lire comme simple alerte de validation."
    else:
        profile = "NO_CONFLICT"
        interpretation = "Aucun conflit classable."
    return {
        "technical_conflict_count": technical,
        "material_conflict_count": material + unknown,
        "directional_conflict_count": directional,
        "weighted_conflict_score": weighted,
        "conflict_profile": profile,
        "interpretation": interpretation,
        "classifications": classifications,
    }


def classify_source_conflict(text: str) -> dict[str, Any]:
    field = _extract_field(text)
    difference = _extract_difference(text)
    yfinance_value = _extract_number(_YF_RE, text)
    comparison_value = _extract_number(_SEC_RE, text)
    if comparison_value is None:
        comparison_value = _extract_number(_CANADIAN_RE, text)

    if not field:
        return _classification("UNPARSED_REVIEW", field, difference, 0.75, "Champ non reconnu.")

    if field in TECHNICAL_OR_PERIOD_FIELDS:
        return _classification(
            "TECHNICAL_OR_PERIOD",
            field,
            difference,
            0.25,
            "Champ sensible aux unités, périodes fiscales ou méthodes de calcul.",
        )

    if _has_directional_disagreement(field, yfinance_value, comparison_value):
        return _classification(
            "DIRECTIONAL_REVIEW",
            field,
            difference,
            1.5,
            "Les sources ne donnent pas le même sens économique sur un champ clé.",
        )

    if difference is not None and difference <= 35:
        return _classification(
            "MINOR_METHOD",
            field,
            difference,
            0.25,
            "Écart modéré probablement causé par une méthode ou période différente.",
        )

    if field in MATERIAL_RATIO_FIELDS or field in DIRECTIONAL_FIELDS:
        if difference is not None and difference >= 90:
            weight = 1.25
        else:
            weight = 0.75
        return _classification(
            "MATERIAL_REVIEW",
            field,
            difference,
            weight,
            "Ratio ou croissance comparable avec écart important.",
        )

    return _classification(
        "TECHNICAL_OR_PERIOD",
        field,
        difference,
        0.35,
        "Écart traité comme technique sauf preuve contraire.",
    )


def effective_conflict_penalty_score(conflicts: list[str]) -> float:
    return float(summarize_conflict_profile(conflicts)["weighted_conflict_score"])


def _severity(count: int, analysis: dict[str, Any], profile: dict[str, Any]) -> str:
    allocated = safe_float(analysis.get("recommended_allocation_amount")) or safe_float(analysis.get("allocation_amount")) or 0.0
    core = str(analysis.get("universe") or "").upper() == "CORE_PORTFOLIO"
    directional = int(profile.get("directional_conflict_count") or 0)
    material = int(profile.get("material_conflict_count") or 0)
    weighted = safe_float(profile.get("weighted_conflict_score")) or 0.0
    if directional >= 2 or material >= 4 or weighted >= 4.0:
        return "HIGH_REVIEW" if core or allocated > 0 else "REVIEW"
    if directional >= 1 or material >= 2 or (weighted >= 1.5 and (allocated > 0 or core)):
        return "REVIEW"
    return "WATCH"


def _report_priority(universe: str, analysis: dict[str, Any]) -> int:
    if str(universe or "").upper() == "CORE_PORTFOLIO":
        return 3
    if str(analysis.get("allocation_decision") or "").upper() in {"BUY", "ADD"}:
        return 3
    if str(analysis.get("watchlist_status") or "") == "HIGH_PRIORITY_WATCH":
        return 2
    if str(analysis.get("candidate_status") or "") == "MANUAL_REVIEW_TOP_CANDIDATE":
        return 2
    if str(analysis.get("discovery_status") or "") == "ADD_TO_MARKET_UNIVERSE_REVIEW":
        return 1
    return 0


def _severity_rank(value: Any) -> int:
    return {"HIGH_REVIEW": 3, "REVIEW": 2, "WATCH": 1}.get(str(value), 0)


def _recommended_action(severity: str, analysis: dict[str, Any]) -> str:
    allocation_decision = str(analysis.get("allocation_decision") or "").upper()
    if severity == "HIGH_REVIEW":
        return "Valider avant grosse allocation; les sources peuvent utiliser des périodes ou unités différentes, mais le conflit mérite une lecture du rapport annuel/BNCD."
    if severity == "REVIEW":
        if allocation_decision in {"BUY", "ADD"}:
            return "Surveiller avant achat important; vérifier si l'écart vient d'une période différente ou d'un champ non comparable."
        return "Surveiller; ne pas traiter ce conflit comme une vente automatique."
    return "Simple avertissement; aucune pénalité automatique."


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.replace("|", ";").split(";") if part.strip()]


def _compact(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _classification(
    classification: str,
    field: str,
    difference: float | None,
    weight: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "field": field,
        "difference_percent": difference,
        "classification": classification,
        "weight": weight,
        "reason": reason,
    }


def _extract_field(text: str) -> str:
    match = _FIELD_RE.search(str(text or ""))
    return str(match.group(1)).strip() if match else ""


def _extract_difference(text: str) -> float | None:
    match = _DIFF_RE.search(str(text or ""))
    if not match:
        return None
    value = str(match.group(1)).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def _extract_number(pattern: re.Pattern[str], text: str) -> float | None:
    match = pattern.search(str(text or ""))
    if not match:
        return None
    value = str(match.group(1)).replace(",", ".")
    try:
        return float(value)
    except ValueError:
        return None


def _has_directional_disagreement(field: str, left: float | None, right: float | None) -> bool:
    if field not in DIRECTIONAL_FIELDS:
        return False
    if left is None or right is None:
        return False
    if abs(left) < 1e-9 or abs(right) < 1e-9:
        return False
    return (left > 0 > right) or (right > 0 > left)
