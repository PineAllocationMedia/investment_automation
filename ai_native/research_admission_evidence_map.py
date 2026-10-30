"""F3: distinguish researched issuers from investment admission in manual CC reports.

Read existing assembled IR/PI evidence layers. This does not run new research,
certify source rights or financial quality, verify method loading, qualify an
issuer or calculate an allocation. A case may contain MANY unrelated issuers:
therefore a case-level dossier cannot prove any one security investable.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

from .strategy_authority import assess_r1_mode

_SOURCE_STATUS = "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
_FUNDAMENTAL_STATUS = "INDICATIVE_FUNDAMENTAL_DOSSIER_NOT_CERTIFIED"
_QUOTE_STATUS = "PRIVATE_QUOTE_SOURCE_TRACE_NOT_CERTIFIED"
_ROOM = frozenset({"NOT_EVALUATED", "ROOM_UNAVAILABLE", "ROOM_CONDITIONAL",
                    "ROOM_EVIDENCE_SUPPORTED"})


def _date(raw: Any, name: str) -> date:
    if not isinstance(raw, str):
        raise ValueError("ADMISSION_MAP_" + name + "_INVALID")
    try:
        value = date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("ADMISSION_MAP_" + name + "_INVALID") from exc
    if value.isoformat() != raw:
        raise ValueError("ADMISSION_MAP_" + name + "_INVALID")
    return value


def prepare_research_admission_evidence_map(
    *, request: Mapping[str, Any], ir_capsule: Mapping[str, Any],
    integrated: Mapping[str, Any],
) -> dict[str, Any]:
    """Map existing components to explicit non-authorizing F3 evidence states."""
    if not all(isinstance(v, Mapping) for v in (request, ir_capsule, integrated)):
        raise ValueError("ADMISSION_MAP_INPUTS_REQUIRED")
    if request.get("ceo_initiated") is not True or request.get("research_needed") is not True:
        raise ValueError("ADMISSION_MAP_CEO_RESEARCH_MANDATE_REQUIRED")
    aid = request.get("analysis_id")
    mode = request.get("strategy_id")
    if not isinstance(aid, str) or not aid.strip() or len(aid) > 256:
        raise ValueError("ADMISSION_MAP_CASE_ID_INVALID")
    cutoff = _date(request.get("as_of"), "CUTOFF")
    ir_date = _date(ir_capsule.get("research_as_of"), "IR_DATE")
    if (ir_date > cutoff or ir_capsule.get("analysis_id") != aid
            or integrated.get("status") != "ASSEMBLED_COMPONENT_ONLY_NOT_END_TO_END_ACCEPTANCE"):
        raise ValueError("ADMISSION_MAP_IR_ID_DATE_OR_INTEGRATION_MISMATCH")
    policy = assess_r1_mode(mode)
    if integrated.get("strategy_policy_gate") != policy:
        raise ValueError("ADMISSION_MAP_POLICY_GATE_MISMATCH")
    facts = ir_capsule.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("ADMISSION_MAP_ORIGINAL_IR_FACTS_REQUIRED")
    if any(not isinstance(f, Mapping) or not isinstance(f.get("id"), str)
           or not f["id"].strip() for f in facts):
        raise ValueError("ADMISSION_MAP_IR_FACT_IDS_INVALID")

    src = integrated.get("source_evidence_annex_private")
    if src is None:
        source_stage = "SOURCE_ANNEX_NOT_SUPPLIED"
    else:
        if (not isinstance(src, Mapping)
                or src.get("status") != _SOURCE_STATUS
                or src.get("source_authentication") != "NOT_PERFORMED_BY_CODE"
                or src.get("analysis_id") != aid
                or src.get("analysis_as_of") != cutoff.isoformat()):
            raise ValueError("ADMISSION_MAP_SOURCE_AUTHORITY_OR_CASE_MISMATCH")
        unresolved = src.get("unresolved_count")
        uncovered = src.get("uncovered_ir_fact_ids")
        incompatible = src.get("noncomparable_basis_groups")
        if (type(unresolved) is not int or unresolved < 0
                or not isinstance(uncovered, list)
                or not isinstance(incompatible, list)):
            raise ValueError("ADMISSION_MAP_SOURCE_RESOLUTION_INVALID")
        source_stage = (
            "SOURCE_STRUCTURAL_GAPS_REQUIRE_RESOLUTION"
            if unresolved or uncovered or incompatible else
            "SOURCE_STRUCTURALLY_LINKED_NOT_AUTHENTICATED"
        )

    fundamental = integrated.get("fundamental_dossier_private")
    if fundamental is not None and (
        not isinstance(fundamental, Mapping)
        or fundamental.get("status") != _FUNDAMENTAL_STATUS
        or fundamental.get("analysis_id") != aid
    ):
        raise ValueError("ADMISSION_MAP_FUNDAMENTAL_AUTHORITY_MISMATCH")
    economics_stage = (
        "FUNDAMENTAL_RESEARCH_REPORTED_NOT_VERIFIED"
        if fundamental is not None else "ISSUER_ECONOMICS_NOT_ASSEMBLED"
    )

    quote = integrated.get("valuation_quote_trace_private")
    if quote is None:
        valuation_stage = "COMPARABLE_FORWARD_VALUE_NOT_ASSEMBLED"
    else:
        if (not isinstance(quote, Mapping)
                or quote.get("status") != _QUOTE_STATUS
                or quote.get("source_authentication") != "NOT_PERFORMED"):
            raise ValueError("ADMISSION_MAP_VALUATION_QUOTE_AUTHORITY_MISMATCH")
        if quote.get("review_stage") == "EVIDENCE_RESOLUTION":
            valuation_stage = "VALUATION_QUOTE_EVIDENCE_RESOLUTION"
        elif quote.get("review_stage") == "HUMAN_QUOTE_REVIEW_ONLY":
            valuation_stage = "VALUATION_ASSUMPTIONS_HUMAN_REVIEW_ONLY"
        else:
            raise ValueError("ADMISSION_MAP_QUOTE_REVIEW_STAGE_INVALID")

    weighted = integrated.get("weighted_cashflow_model_private")
    if weighted is not None and (
        not isinstance(weighted, Mapping)
        or weighted.get("status") != "CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED"
    ):
        raise ValueError("ADMISSION_MAP_WEIGHTED_MODEL_AUTHORITY_INVALID")
    # Even supplied scenario probability weights do not certify economic
    # likelihood, net Expected Return, or benchmark-relative alpha.
    er_stage = ("ASSUMPTION_WEIGHTED_CASHFLOWS_NOT_CERTIFIED_ER"
                if weighted is not None else "VERIFIED_COMPARABLE_ER_NOT_ESTABLISHED")

    room = integrated.get("portfolio_room_status")
    if room not in _ROOM:
        raise ValueError("ADMISSION_MAP_PI_ROOM_STATUS_INVALID")
    pi_stage = ("PI_NOT_EVALUATED" if room == "NOT_EVALUATED" else
                "PI_ROOM_REPORTED_NOT_ACCOUNT_AUTHENTICATED")
    policy_stage = (
        "EXISTING_V2_HIGH_CAGR_SCOPE_UNVERIFIED"
        if policy["policy_authority"] == "V2_HIGH_CAGR_EXISTING_SCOPE_ONLY" else
        "R1_FINANCIAL_POLICY_NOT_APPROVED_OR_NO_MODE_AUTHORITY"
    )

    # Each next step is an evidence request, not a pass/fail score for company
    # quality. At case level there can be multiple economic issuers and
    # multiple quoted instruments: no identity is silently mixed.
    next_steps = []
    if source_stage != "SOURCE_STRUCTURALLY_LINKED_NOT_AUTHENTICATED":
        next_steps.append("LINK_IR_FACTS_TO_DATED_COMPATIBLE_PRIMARY_SOURCES")
    next_steps.append("INDEPENDENTLY_VERIFY_CRITICAL_ORIGINAL_FACTS_AND_RIGHTS")
    if fundamental is None:
        next_steps.append("NORMALIZE_VIABILITY_FINANCING_CASH_AND_DILUTION_BY_ISSUER_MODEL")
    else:
        next_steps.append("REVIEW_ECONOMIC_MODEL_AND_ISSUER_SPECIFIC_COUNTERCASE")
    next_steps.append("ESTABLISH_COMPARABLE_FORWARD_ER_OR_MARK_UNAVAILABLE")
    next_steps.append("VERIFY_APPROVED_MODE_POLICY_SCOPE_AND_METHOD_VERSION")
    if room == "NOT_EVALUATED":
        next_steps.append("OBTAIN_DATED_PI_ACCOUNT_PLATFORM_AND_COST_SCOPE_IF_NEEDED")
    else:
        next_steps.append("VERIFY_PI_ROOM_PLATFORM_COSTS_AND_PORTFOLIO_PROVENANCE")

    return {
        "status": "F3_CASE_LEVEL_EVIDENCE_PATH_NOT_INVESTMENT_ADMISSION",
        "analysis_id": aid, "analysis_as_of": cutoff.isoformat(),
        "strategy_id": policy["r1_mode"],
        "subject_scope": "CASE_LEVEL_MULTIPLE_ISSUERS_MAY_BE_PRESENT",
        "research_stage": "IR_FACTS_REPORTED_NOT_INDEPENDENTLY_CERTIFIED",
        "source_stage": source_stage,
        "economic_stage": economics_stage,
        "valuation_stage": valuation_stage,
        "expected_return_stage": er_stage,
        "mode_policy_stage": policy_stage,
        "pi_stage": pi_stage,
        "investability_status": "NOT_ESTABLISHED",
        "instrument_eligibility": "NOT_VERIFIED",
        "source_rights_authentication": "NOT_PERFORMED",
        "policy_and_project_method_load": "NOT_VERIFIED",
        "new_contribution_percentage": None,
        "trade_authority": "NONE",
        "unknown_quality_interpretation": "UNKNOWN_EVIDENCE_IS_NOT_NEGATIVE_COMPANY_QUALITY",
        "next_evidence_actions": next_steps,
        "storage": "NONE",
    }


def render_research_admission_evidence_map(review: Mapping[str, Any]) -> str:
    """Fixed concise private CC gate report; no issuer/holding/fact details echoed."""
    if (not isinstance(review, Mapping)
            or review.get("status") != "F3_CASE_LEVEL_EVIDENCE_PATH_NOT_INVESTMENT_ADMISSION"
            or review.get("subject_scope") != "CASE_LEVEL_MULTIPLE_ISSUERS_MAY_BE_PRESENT"
            or review.get("research_stage") != "IR_FACTS_REPORTED_NOT_INDEPENDENTLY_CERTIFIED"
            or review.get("source_stage") not in {
                "SOURCE_ANNEX_NOT_SUPPLIED",
                "SOURCE_STRUCTURAL_GAPS_REQUIRE_RESOLUTION",
                "SOURCE_STRUCTURALLY_LINKED_NOT_AUTHENTICATED",
            }
            or review.get("economic_stage") not in {
                "ISSUER_ECONOMICS_NOT_ASSEMBLED",
                "FUNDAMENTAL_RESEARCH_REPORTED_NOT_VERIFIED",
            }
            or review.get("valuation_stage") not in {
                "COMPARABLE_FORWARD_VALUE_NOT_ASSEMBLED",
                "VALUATION_QUOTE_EVIDENCE_RESOLUTION",
                "VALUATION_ASSUMPTIONS_HUMAN_REVIEW_ONLY",
            }
            or review.get("investability_status") != "NOT_ESTABLISHED"
            or review.get("instrument_eligibility") != "NOT_VERIFIED"
            or review.get("source_rights_authentication") != "NOT_PERFORMED"
            or review.get("policy_and_project_method_load") != "NOT_VERIFIED"
            or review.get("new_contribution_percentage") is not None
            or review.get("trade_authority") != "NONE"
            or review.get("storage") != "NONE"):
        raise ValueError("ADMISSION_MAP_REPORT_AUTHORITY_INVALID")

    source = {
        "SOURCE_ANNEX_NOT_SUPPLIED": "aucune annexe primaire structuree dans ce dossier",
        "SOURCE_STRUCTURAL_GAPS_REQUIRE_RESOLUTION": "liaisons de faits manquantes, incompatibles ou contestables",
        "SOURCE_STRUCTURALLY_LINKED_NOT_AUTHENTICATED": "liaisons structurelles presentes, sans authentification",
    }[review["source_stage"]]
    economics = {
        "ISSUER_ECONOMICS_NOT_ASSEMBLED": "normalisation du modele economique non assemblee",
        "FUNDAMENTAL_RESEARCH_REPORTED_NOT_VERIFIED": "dossier economique present, non verifie independamment",
    }[review["economic_stage"]]
    valuation = {
        "COMPARABLE_FORWARD_VALUE_NOT_ASSEMBLED": "valorisation forward comparable non assemblee",
        "VALUATION_QUOTE_EVIDENCE_RESOLUTION": "prix/valeur : preuve de cotation a resoudre",
        "VALUATION_ASSUMPTIONS_HUMAN_REVIEW_ONLY": "scenarios chiffres a reviser humainement, pas un rendement espere",
    }[review["valuation_stage"]]
    return "\n".join([
        "## F3 — De la recherche a l'admissibilite financiere",
        "1. **Recherche IR :** faits signales, non authentifies; plusieurs entreprises "
        "peuvent coexister dans un meme dossier, sans admission globale.",
        "2. **Sources :** " + source + ".",
        "3. **Economie/viabilite :** " + economics + ".",
        "4. **Valorisation :** " + valuation
        + "; rendement espere comparable net de couts NON CERTIFIE.",
        "5. **Politique et portefeuille :** statut de methode chargee NON VERIFIE; "
        "strategie, instrument sur plateforme, risque, fiscalite et Room restent "
        "a examiner selon la politique reellement approuvee.",
        "**Conclusion :** aucune entreprise ni aucun vehicule declare admissible "
        "par ce controle; aucun montant ou pourcentage de contribution propose. "
        "L'absence de preuve ne vaut pas preuve d'une mauvaise entreprise.",
        "**Action :** qualifier un emetteur et un instrument a la fois, avec "
        "sources originales, financement/flux, comparaison forward, politique "
        "applicable et donnees PI/compte authentiques si requises.",
    ])
