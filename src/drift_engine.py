from __future__ import annotations

from typing import Any

from .utils import safe_float


def compute_drift_status(analysis: dict[str, Any]) -> dict[str, Any]:
    weight = safe_float(analysis.get("position_weight")) or 0.0
    if weight <= 0.30:
        return {"drift_status": "NORMAL_BUY_ALLOWED", "drift_reason": "Poids <= 30 %, achat normal permis."}
    if weight > 0.40:
        return {"drift_status": "NO_ADD_ABOVE_40", "drift_reason": "Poids > 40 %, ne jamais ajouter; laisser courir seulement."}

    allowed = (
        analysis.get("winner_accelerated") is True
        and (safe_float(analysis.get("conviction_score")) or 0.0) >= 80
        and analysis.get("thesis_status") == "INTACT"
        and analysis.get("liquidation_status") == "GREEN"
        and analysis.get("expected_cagr_quality") in {"HIGH", "VERY_HIGH"}
        and analysis.get("opportunity_cost_status") == "CLEARLY_BETTER_THAN_VFV"
        and analysis.get("quality_but_too_expensive") is not True
    )
    if allowed:
        return {"drift_status": "HIGH_CONVICTION_ADD_ALLOWED", "drift_reason": "Poids 30-40 %, mais les garde-fous de très forte conviction sont respectés."}
    return {"drift_status": "LIMITED_BY_DRIFT", "drift_reason": "Poids 30-40 % sans toutes les conditions de renforcement."}


def can_add_by_drift(analysis: dict[str, Any]) -> bool:
    return compute_drift_status(analysis)["drift_status"] in {"NORMAL_BUY_ALLOWED", "HIGH_CONVICTION_ADD_ALLOWED"}
