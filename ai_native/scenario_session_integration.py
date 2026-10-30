"""Tie an illustrative P11 displayed-weight scenario to the actual private M3 PI ledger.

This checker only compares *caller-reported visible rows* for parity. It does
not authenticate a Blossom account, scenario source, tax/FX, or financial policy.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping

from .scenario_weight_sensitivity import evaluate_scenario_weight_sensitivity


def prepare_scoped_scenario_review(
    *, request: Mapping[str, Any], pi_delta: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
    scenario_weight_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate analysis/PI identity and exact observed weight parity, then compute."""
    if not isinstance(scenario_weight_inputs, Mapping) or set(scenario_weight_inputs) != {
        "analysis_id", "analysis_as_of", "strategy_id", "denominator_evidence",
        "positions", "scenarios",
    }:
        raise ValueError("SCENARIO_REVIEW_EXACT_SCHEMA_REQUIRED")
    if not isinstance(observation, Mapping) or not isinstance(pi_delta, Mapping):
        raise ValueError("SCENARIO_REVIEW_REQUIRES_PRIVATE_PI_OBSERVATION")
    if (observation.get("private_scope") is not True
            or observation.get("source_type") == "PUBLIC_BLOSSOM_REFERENCE"
            or observation.get("decision_authority") != "CEO_ONLY"
            or observation.get("verification") !=
                "CALLER_ASSERTED_NOT_INDEPENDENTLY_AUTHENTICATED"):
        raise ValueError("SCENARIO_REVIEW_OBSERVATION_AUTHORITY_INVALID")
    mode_input = scenario_weight_inputs["strategy_id"]
    if not isinstance(mode_input, str) or not mode_input.strip():
        raise ValueError("SCENARIO_REVIEW_STRATEGY_ID_INVALID")
    if (scenario_weight_inputs["analysis_id"] != request.get("analysis_id")
            or scenario_weight_inputs["analysis_as_of"] != request.get("as_of")
            or mode_input.strip().lower()
                != str(request.get("strategy_id", "")).strip().lower()
            or observation.get("analysis_id") != request.get("analysis_id")
            or observation.get("analysis_as_of") != request.get("as_of")
            or observation.get("observed_on") != pi_delta.get("portfolio_as_of")):
        raise ValueError("SCENARIO_REVIEW_ID_DATE_OR_MODE_MISMATCH")

    records = observation.get("p_ledger_private")
    positions = scenario_weight_inputs["positions"]
    if not isinstance(records, list) or not isinstance(positions, list):
        raise ValueError("SCENARIO_REVIEW_POSITIONS_REQUIRED")
    by_id: dict[str, str] = {}
    for row in records:
        if not isinstance(row, Mapping) or not isinstance(row.get("p_id"), str):
            raise ValueError("SCENARIO_REVIEW_LEDGER_INVALID")
        if row["p_id"] in by_id:
            raise ValueError("SCENARIO_REVIEW_DUPLICATE_P_ID")
        if (row.get("displayed_weight_visibility") != "VERIFIED_VISIBLE"
                or not isinstance(row.get("displayed_weight_pct_private"), str)):
            raise ValueError("SCENARIO_REVIEW_VISIBLE_WEIGHTS_REQUIRED")
        by_id[row["p_id"]] = row["displayed_weight_pct_private"]
    if len(by_id) != len(positions):
        raise ValueError("SCENARIO_REVIEW_POSITION_COVERAGE_MISMATCH")
    for row in positions:
        if not isinstance(row, Mapping) or row.get("p_id") not in by_id:
            raise ValueError("SCENARIO_REVIEW_POSITION_ID_MISMATCH")
        # The downstream calculator strictly validates finite strings, scale
        # and duplication; this parity check also forbids retyped proportions.
        try:
            if not isinstance(row.get("weight_pct"), str):
                raise ValueError("SCENARIO_REVIEW_DISPLAYED_WEIGHT_INVALID")
            if Decimal(row["weight_pct"]) != Decimal(by_id[row["p_id"]]):
                raise ValueError("SCENARIO_REVIEW_DISPLAYED_WEIGHT_MISMATCH")
        except (ArithmeticError, TypeError) as exc:
            raise ValueError("SCENARIO_REVIEW_DISPLAYED_WEIGHT_INVALID") from exc

    result = evaluate_scenario_weight_sensitivity(**scenario_weight_inputs)
    # Status remains bound to a caller-reported *displayed view*, even if every
    # visible weight has a shock. It is not a full private-account calculation.
    if (result.get("policy_authority") != "NONE"
            or result.get("historical_calibration") != "NOT_PERFORMED"
            or result.get("source_authentication") != "NOT_PERFORMED"
            or result.get("storage") != "NONE"):
        raise ValueError("SCENARIO_REVIEW_AUTHORITY_INVALID")
    return result


def render_scoped_scenario_lines(review: Mapping[str, Any]) -> str:
    """Compact, no-ID/no-holding/no-source scenario section for private CC reports."""
    if (not isinstance(review, Mapping)
            or review.get("status") != "NON_BINDING_CALLER_SUPPLIED_SCENARIO_SENSITIVITY"
            or review.get("policy_authority") != "NONE"
            or review.get("source_authentication") != "NOT_PERFORMED"
            or review.get("historical_calibration") != "NOT_PERFORMED"
            or review.get("storage") != "NONE"
            or not isinstance(review.get("scenarios"), list)):
        raise ValueError("SCENARIO_REPORT_AUTHORITY_INVALID")
    lines = [
        "## Sensibilité aux scénarios — poids affichés, hypothèses non certifiées",
        "Chocs fournis par le demandeur; calcul hypothétique sur le seul périmètre "
        "visible. Ni historique calibré, ni rendement prévu, ni portefeuille "
        "personnel authentifié, ni budget de risque, ni recommandation.",
    ]
    for i, row in enumerate(review["scenarios"][:5], start=1):
        if not isinstance(row, Mapping) or row.get("status") not in {
            "UNAVAILABLE_DENOMINATOR",
            "UNAVAILABLE_WEIGHTS_EXCEED_100_NO_NORMALIZATION",
            "PARTIAL_SCOPED_SENSITIVITY_ONLY",
            "COMPLETE_DISPLAYED_VIEW_HYPOTHETICAL_ONLY",
        } or row.get("is_drawdown_or_loss_bound") is not False:
            raise ValueError("SCENARIO_REPORT_STATUS_INVALID")
        status = row["status"]
        # Do not echo caller-controlled scenario IDs, P_IDs, account IDs,
        # evidence refs or instrument names into the short/private report.
        if status == "COMPLETE_DISPLAYED_VIEW_HYPOTHETICAL_ONLY":
            value = row.get("scoped_displayed_hypothetical_return_pct")
            line = f"- Scénario {i}: variation hypothétique de la vue {value}%."
        elif status == "PARTIAL_SCOPED_SENSITIVITY_ONLY":
            value = row.get("partial_contribution_pct_points")
            coverage = row.get("modeled_coverage_weight_pct")
            line = (f"- Scénario {i}: contribution partielle {value} points; "
                    f"couverture modélisée {coverage}% seulement. Rendement global INDISPONIBLE.")
        else:
            line = f"- Scénario {i}: INDISPONIBLE ({status})."
        lines.append(line)
    if len(review["scenarios"]) > 5:
        lines.append(f"- {len(review['scenarios']) - 5} scénario(s) supplémentaires dans l'annexe privée.")
    lines.append(
        "Provenance et identité des scénarios seulement dans l'objet privé. "
        "Aucune politique ou admissibilité d'investissement n'est créée.")
    return "\n".join(lines)
