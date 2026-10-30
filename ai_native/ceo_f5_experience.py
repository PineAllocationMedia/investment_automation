"""F5: concise CEO decision-layer and measured (not inferred) human effort.

Only reconstruct a validated existing executive+detail report; never recalculate
financial conclusions, copy user notes, authenticate Projects or create files.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

_STAGES = frozenset({
    "PI_SOURCE_CAPTURE", "HANDOFF_TO_PI", "HANDOFF_TO_IR",
    "SPECIALIST_RETURN_TO_CC", "CC_REVIEW", "REPORT_READ",
})
_MANUAL_HANDOFF = frozenset({
    "HANDOFF_TO_PI", "HANDOFF_TO_IR", "SPECIALIST_RETURN_TO_CC",
})
_COVERAGE = frozenset({
    "PARTIAL_REPORTED_ACTIONS", "CEO_REPORTED_COMPLETE_CYCLE",
})
_ANNEX = "## Dossier détaillé et traçabilité (annexe)"
_EXECUTIVE = "# PAM R1 — Synthèse décisionnelle"


def prepare_human_effort_summary(
    *, request: Mapping[str, Any],
    effort_inputs: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Report explicit active seconds/observed handoffs, never predicted effort."""
    if not isinstance(request, Mapping) or request.get("ceo_initiated") is not True:
        raise ValueError("F5_EFFORT_CEO_CASE_REQUIRED")
    aid = request.get("analysis_id")
    as_of = request.get("as_of")
    if not isinstance(aid, str) or not aid.strip() or not isinstance(as_of, str):
        raise ValueError("F5_EFFORT_CASE_ID_INVALID")
    if effort_inputs is None:
        status = "NOT_MEASURED"
        coverage = "NOT_RECORDED"
        steps: list[Mapping[str, Any]] = []
    else:
        if (not isinstance(effort_inputs, Mapping)
                or set(effort_inputs) != {
                    "analysis_id", "analysis_as_of", "source", "coverage", "steps",
                }
                or effort_inputs.get("analysis_id") != aid
                or effort_inputs.get("analysis_as_of") != as_of
                or effort_inputs.get("source") != "CEO_REPORTED_ACTIVE_WORK"):
            raise ValueError("F5_EFFORT_RECORD_CASE_OR_SOURCE_INVALID")
        coverage = effort_inputs["coverage"]
        steps = effort_inputs["steps"]
        if (not isinstance(coverage, str) or coverage not in _COVERAGE
                or not isinstance(steps, list) or not 1 <= len(steps) <= 40):
            raise ValueError("F5_EFFORT_COVERAGE_OR_STEPS_INVALID")
        for step in steps:
            if (not isinstance(step, Mapping)
                    or set(step) != {"stage", "active_seconds"}
                    or not isinstance(step.get("stage"), str)
                    or step["stage"] not in _STAGES
                    or type(step.get("active_seconds")) is not int
                    or not 1 <= step["active_seconds"] <= 21600):
                raise ValueError("F5_EFFORT_STEP_INVALID")
        status = "CEO_REPORTED_COMPLETE_NOT_INDEPENDENTLY_TIMED" if (
            coverage == "CEO_REPORTED_COMPLETE_CYCLE") else "PARTIAL_MEASURED_SUBTOTAL_ONLY"
    total = sum(step["active_seconds"] for step in steps)
    reading = sum(step["active_seconds"] for step in steps if step["stage"] == "REPORT_READ")
    reading_known = any(step["stage"] == "REPORT_READ" for step in steps)
    transfers = sum(step["stage"] in _MANUAL_HANDOFF for step in steps)
    return {
        "status": status,
        "analysis_id": aid, "analysis_as_of": as_of,
        "coverage": coverage,
        "reported_manual_handoffs": transfers if steps else None,
        "reported_active_minutes": str((Decimal(total) / 60).quantize(Decimal("0.01")))
        if steps else None,
        "reported_read_minutes": str((Decimal(reading) / 60).quantize(Decimal("0.01")))
        if reading_known else None,
        "target_read_10_min": (
            "CEO_REPORTED_WITHIN_TARGET" if reading <= 600 else "CEO_REPORTED_ABOVE_TARGET"
        ) if reading_known and coverage == "CEO_REPORTED_COMPLETE_CYCLE" else "NOT_ASSESSED",
        "measurement_reliability": "CEO_REPORTED_NOT_INDEPENDENTLY_TIMED" if steps
        else "NO_MEASUREMENT",
        "weekly_one_hour_target": "NOT_ASSESSED_SINGLE_SESSION_ONLY",
        "method_policy_or_trade_authority": "NONE",
        "source_authentication": "NOT_PERFORMED",
        "storage": "NONE",
    }


def render_human_effort_line(summary: Mapping[str, Any]) -> str:
    if (not isinstance(summary, Mapping)
            or summary.get("status") not in {
                "NOT_MEASURED", "CEO_REPORTED_COMPLETE_NOT_INDEPENDENTLY_TIMED",
                "PARTIAL_MEASURED_SUBTOTAL_ONLY",
            }
            or summary.get("method_policy_or_trade_authority") != "NONE"
            or summary.get("measurement_reliability") not in {
                "CEO_REPORTED_NOT_INDEPENDENTLY_TIMED", "NO_MEASUREMENT",
            }
            or summary.get("storage") != "NONE"):
        raise ValueError("F5_EFFORT_RENDER_AUTHORITY_INVALID")
    if summary["status"] == "NOT_MEASURED":
        return "Effort humain : NOT_MEASURED — aucun temps ni transfert n'est présumé."
    kind = ("cycle déclaré complet" if summary["status"] ==
            "CEO_REPORTED_COMPLETE_NOT_INDEPENDENTLY_TIMED" else
            "sous-total partiel, non extrapolable")
    read = summary["reported_read_minutes"]
    reading = f"; lecture déclarée {read} min" if read is not None else (
        "; lecture NON MESURÉE")
    return (
        f"Effort humain ({kind}) : {summary['reported_manual_handoffs']} "
        f"transfert(s) rapporté(s), {summary['reported_active_minutes']} min "
        f"d'activité rapportée{reading}. Temps non vérifiés indépendamment."
    )


def finalize_decision_first_executive(
    *, original_executive: str, original_detail: str, complete_detail: str,
    high_cagr_review: bool, admission_review: bool,
    public_view_review: bool, method_receipt_review: bool,
    human_effort_summary: Mapping[str, Any],
) -> str:
    """Lift fixed F1–F5 status into first-read area, retain complete new annex.

    Original validated executive is not trusted to certify a financial conclusion:
    this function only moves presentation, with no new security/return values.
    Synthetic stubs without the actual report template are returned unchanged.
    """
    if not all(isinstance(x, str) for x in (
            original_executive, original_detail, complete_detail)):
        raise ValueError("F5_REPORT_INPUT_INVALID")
    if not all(type(x) is bool for x in (
            high_cagr_review, admission_review, public_view_review, method_receipt_review)):
        raise ValueError("F5_REPORT_FLAGS_INVALID")
    effort_line = render_human_effort_line(human_effort_summary)
    if not original_executive.startswith(_EXECUTIVE):
        # Keep old lightweight mocks/legacy responses unchanged; do not
        # reconstruct unvalidated financial report structure.
        return original_executive
    if (original_executive.count(_ANNEX) != 1
            or not original_detail.startswith("# ")
            or not complete_detail.startswith(original_detail)
            or not original_executive.endswith(original_detail.rstrip("\n") + "\n")):
        raise ValueError("F5_EXECUTIVE_DETAIL_PARITY_INVALID")
    marker_start = original_executive.index(_ANNEX)
    orig_detail_pos = len(original_executive) - len(original_detail.rstrip("\n") + "\n")
    if orig_detail_pos <= marker_start:
        raise ValueError("F5_EXECUTIVE_DETAIL_PARITY_INVALID")
    prefix = original_executive[:marker_start]
    annex_intro = original_executive[marker_start:orig_detail_pos]
    signals = ["## Points décisifs pour le CEO — contrôles intégrés"]
    if high_cagr_review:
        signals.append("- **F1 :** entreprise → VFV → réserve examinés; destination financière non certifiée par ce contrôle.")
    if public_view_review:
        signals.append("- **F2 :** poids de vue conditionnels; aucun compte privé authentifié.")
    if admission_review:
        signals.append("- **F3 :** recherche et admission restent distinctes; critères financiers non réputés approuvés.")
    signals.append(
        "- **F4 :** "
        + ("comparaison du contenu reçu effectuée; consulter l'annexe pour "
           "MATCHED/BLOCKED/NOT_RETRIEVED;" if method_receipt_review else
           "correspondance du contenu reçu NON MESURÉE;")
        + " chargement, application et paramètres actifs des Projects NON VÉRIFIÉS."
    )
    signals.append("- **F5 :** " + effort_line)
    signals.append(
        "- **Décision :** aucune de ces vérifications de forme n'autorise "
        "une allocation, une transaction ou un statut d'acceptation R1."
    )
    return (prefix + "\n".join(signals) + "\n\n" + annex_intro
            + complete_detail.rstrip("\n") + "\n")
