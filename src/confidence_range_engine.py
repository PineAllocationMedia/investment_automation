from __future__ import annotations

from typing import Any

from .utils import clamp, safe_float


def compute_conviction_confidence_range(
    conviction_score: float | int | str | None,
    reliability: dict[str, Any],
    proof_score: dict[str, Any],
) -> dict[str, Any]:
    score = safe_float(conviction_score)
    if score is None:
        return {
            "conviction_confidence_low": "",
            "conviction_confidence_high": "",
            "conviction_confidence_range": "",
            "conviction_confidence_label": "",
            "conviction_confidence_reason": "Non applicable.",
        }

    band = 4.0
    reliability_level = str(reliability.get("data_reliability_level") or "MEDIUM").upper()
    dependency = str(reliability.get("auto_estimate_dependency") or "LOW").upper()
    evidence_level = str(proof_score.get("score_evidence_level") or "").upper()
    estimate_gap = safe_float(proof_score.get("score_estimate_gap")) or 0.0

    if reliability_level == "LOW":
        band += 9.0
    elif reliability_level == "MEDIUM":
        band += 5.0
    elif reliability_level == "HIGH":
        band += 1.5

    if dependency == "HIGH":
        band += 4.0
    elif dependency == "MEDIUM":
        band += 1.5

    if evidence_level in {"ESTIMATE_HEAVY", "INSUFFICIENT_CONFIRMED"}:
        band += 5.0
    elif evidence_level == "MIXED":
        band += 2.5
    elif evidence_level == "AUTOMATED_STRONG":
        band += 1.0

    band += min(4.0, estimate_gap * 1.5)
    band = clamp(band, 3.0, 22.0)
    low = round(clamp(score - band, 0, 100), 2)
    high = round(clamp(score + min(7.0, band * 0.35), 0, 100), 2)
    width = high - low
    label = _confidence_label(width)

    return {
        "conviction_confidence_low": low,
        "conviction_confidence_high": high,
        "conviction_confidence_range": f"{low:.2f}-{high:.2f}",
        "conviction_confidence_label": label,
        "conviction_confidence_reason": _reason(label, "conviction"),
    }


def _confidence_label(width: float) -> str:
    if width <= 6:
        return "TIGHT"
    if width <= 11:
        return "NORMAL"
    if width <= 18:
        return "WIDE"
    return "VERY_WIDE"


def _reason(label: str, subject: str) -> str:
    if label == "TIGHT":
        return f"Fourchette serrée: le {subject} score est bien appuyé par les données disponibles."
    if label == "NORMAL":
        return f"Fourchette normale: le {subject} score reste robuste, avec une incertitude raisonnable."
    if label == "WIDE":
        return f"Fourchette large: le {subject} score doit être lu comme une zone, pas comme un chiffre exact."
    return f"Fourchette très large: le {subject} score dépend fortement de données estimées ou incomplètes."
