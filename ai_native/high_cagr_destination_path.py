"""Trace existing High-CAGR company -> VFV -> exceptional reserve hierarchy.

Third CEO test F1: do not stop at UNKNOWN company alpha without examining
the ordinary VFV fallback. This is a non-authorizing *decision coverage*
checklist, not a new admission test, account verification, or allocation.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Mapping

ROOM = frozenset({"ROOM_EVIDENCE_SUPPORTED", "ROOM_CONDITIONAL", "ROOM_UNAVAILABLE"})


def _date(value: Any, key: str) -> date:
    if not isinstance(value, str):
        raise ValueError("CAPITAL_PATH_" + key + "_INVALID")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("CAPITAL_PATH_" + key + "_INVALID") from exc
    if result.isoformat() != value:
        raise ValueError("CAPITAL_PATH_" + key + "_INVALID")
    return result


def prepare_high_cagr_destination_review(
    *, request: Mapping[str, Any], ir_capsule: Mapping[str, Any] | None,
    pi_delta: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a complete non-authorizing branch-by-branch evidence review.

    A specialist-supplied research packet or PI room state is not independently
    authenticated. Even a supported-looking PI state does not prove a company,
    the VFV vehicle, after-cost return or reserve to be investment-eligible.
    """
    if not isinstance(request, Mapping) or not isinstance(pi_delta, Mapping):
        raise ValueError("CAPITAL_PATH_PACKETS_REQUIRED")
    if request.get("strategy_id") != "high-cagr":
        raise ValueError("CAPITAL_PATH_HIGH_CAGR_SCOPE_ONLY")
    if request.get("ceo_initiated") is not True or request.get("portfolio_needed") is not True:
        raise ValueError("CAPITAL_PATH_CEO_PORTFOLIO_MANDATE_REQUIRED")
    analysis_id = request.get("analysis_id")
    if not isinstance(analysis_id, str) or not analysis_id.strip() or len(analysis_id) > 256:
        raise ValueError("CAPITAL_PATH_ANALYSIS_ID_INVALID")
    cutoff = _date(request.get("as_of"), "CUTOFF")
    pi_date = _date(pi_delta.get("portfolio_as_of"), "PI_DATE")
    if pi_date > cutoff or pi_delta.get("analysis_id") != analysis_id:
        raise ValueError("CAPITAL_PATH_PI_ID_DATE_MISMATCH")
    room = pi_delta.get("room_status")
    if room not in ROOM:
        raise ValueError("CAPITAL_PATH_PI_ROOM_INVALID")
    if ir_capsule is not None:
        if not isinstance(ir_capsule, Mapping) or ir_capsule.get("analysis_id") != analysis_id:
            raise ValueError("CAPITAL_PATH_IR_ID_MISMATCH")
        ir_date = _date(ir_capsule.get("research_as_of"), "IR_DATE")
        if ir_date > cutoff:
            raise ValueError("CAPITAL_PATH_IR_AFTER_CUTOFF")
    research = (
        "RESEARCH_PRESENT_ADMISSION_UNVERIFIED" if ir_capsule is not None
        else "RESEARCH_NOT_PROVIDED"
    )
    # Fourth CEO test: company/VFV total-ER comparability and private Room
    # are independent. Neither the mere IR presence nor reported PI coverage
    # certifies a forward return, cost basis, account or allocation.
    economic_dependency = (
        "ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_NOT_ESTABLISHED"
        if ir_capsule is not None
        else "ORIGINAL_IR_AND_VFV_COMPARABLE_TOTAL_ER_NOT_SUPPLIED"
    )
    room_dependency = {
        "ROOM_EVIDENCE_SUPPORTED":
            "REPORTED_ROOM_REQUIRES_PRIVATE_ACCOUNT_AUTHENTICATION",
        "ROOM_CONDITIONAL":
            "CONDITIONAL_ROOM_REQUIRES_PRIVATE_ACCOUNT_VALIDATION",
        "ROOM_UNAVAILABLE": "PRIVATE_ACCOUNT_ROOM_NOT_AVAILABLE",
    }[room]
    economic_action = (
        "ESTABLISH_ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_WITH_PRIMARY_EVIDENCE"
        if ir_capsule is not None
        else "OBTAIN_ISSUER_LEVEL_IR_AND_COMPARABLE_VFV_RETURN_EVIDENCE"
    )
    return {
        "status": "COMPLETE_BRANCH_COVERAGE_WITHOUT_FINANCIAL_ADMISSION",
        "analysis_id": analysis_id, "analysis_as_of": cutoff.isoformat(),
        "strategy_id": "high-cagr",
        "existing_policy_hierarchy": [
            "QUALIFIED_INDIVIDUAL_OPPORTUNITY",
            "VFV_NORMAL_BENCHMARK_FALLBACK",
            "EXCEPTIONAL_TEMPORARY_RESERVE",
        ],
        "company_branch": research,
        "vfv_branch": "ELIGIBILITY_AND_COST_CHECK_REQUIRED",
        "reserve_branch": "EXCEPTIONAL_ONLY_NOT_JUSTIFIED_BY_MISSING_DATA",
        "pi_room_reported": room,
        "pi_room_authentication": "NOT_PERFORMED",
        "original_source_check": "NOT_PERFORMED",
        "expected_return_or_alpha": "NOT_ESTABLISHED_BY_ASSEMBLER",
        "benchmark_instrument_access": "NOT_VERIFIED",
        "after_cost_economics": "NOT_CERTIFIED",
        "decision_stage": "EVIDENCE_GAP_NOT_AN_ALLOCATION_DECISION",
        "independent_dependencies": {
            "economic": economic_dependency,
            "personal_room": room_dependency,
            "vfv_account_costs_tax": "UNVERIFIED",
        },
        "primary_next_action": economic_action,
        "secondary_next_action":
            "VERIFY_VFV_ACCOUNT_ACCESS_COSTS_FX_TAX_AND_DATED_PORTFOLIO_ROOM",
        "allocation_percentage": None,
        "trade_authority": "NONE",
        "review_next": economic_action,
        "storage": "NONE",
    }


def render_high_cagr_destination_review(review: Mapping[str, Any]) -> str:
    """Fixed, privacy-neutral decision trace; never echo source or holding IDs."""
    if not isinstance(review, Mapping):
        raise ValueError("CAPITAL_PATH_RENDER_AUTHORITY_INVALID")
    research_present = (
        review.get("company_branch") == "RESEARCH_PRESENT_ADMISSION_UNVERIFIED"
    )
    econ = (
        "ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_NOT_ESTABLISHED"
        if research_present else
        "ORIGINAL_IR_AND_VFV_COMPARABLE_TOTAL_ER_NOT_SUPPLIED"
    )
    room = review.get("pi_room_reported")
    room_dependency = {
        "ROOM_EVIDENCE_SUPPORTED":
            "REPORTED_ROOM_REQUIRES_PRIVATE_ACCOUNT_AUTHENTICATION",
        "ROOM_CONDITIONAL":
            "CONDITIONAL_ROOM_REQUIRES_PRIVATE_ACCOUNT_VALIDATION",
        "ROOM_UNAVAILABLE": "PRIVATE_ACCOUNT_ROOM_NOT_AVAILABLE",
    }.get(room)
    economic_action = (
        "ESTABLISH_ISSUER_AND_VFV_COMPARABLE_TOTAL_ER_WITH_PRIMARY_EVIDENCE"
        if research_present else
        "OBTAIN_ISSUER_LEVEL_IR_AND_COMPARABLE_VFV_RETURN_EVIDENCE"
    )
    if (review.get("decision_stage") != "EVIDENCE_GAP_NOT_AN_ALLOCATION_DECISION"
            or review.get("independent_dependencies") != {
                "economic": econ, "personal_room": room_dependency,
                "vfv_account_costs_tax": "UNVERIFIED"
            }
            or review.get("primary_next_action") != economic_action
            or review.get("review_next") != economic_action
            or review.get("secondary_next_action") !=
                "VERIFY_VFV_ACCOUNT_ACCESS_COSTS_FX_TAX_AND_DATED_PORTFOLIO_ROOM"):
        raise ValueError("CAPITAL_PATH_RENDER_AUTHORITY_INVALID")
    if (not isinstance(review, Mapping)
            or review.get("status") != "COMPLETE_BRANCH_COVERAGE_WITHOUT_FINANCIAL_ADMISSION"
            or review.get("strategy_id") != "high-cagr"
            or review.get("existing_policy_hierarchy") != [
                "QUALIFIED_INDIVIDUAL_OPPORTUNITY",
                "VFV_NORMAL_BENCHMARK_FALLBACK",
                "EXCEPTIONAL_TEMPORARY_RESERVE",
            ]
            or review.get("company_branch") not in {
                "RESEARCH_PRESENT_ADMISSION_UNVERIFIED", "RESEARCH_NOT_PROVIDED"
            }
            or review.get("vfv_branch") != "ELIGIBILITY_AND_COST_CHECK_REQUIRED"
            or review.get("reserve_branch") != "EXCEPTIONAL_ONLY_NOT_JUSTIFIED_BY_MISSING_DATA"
            or review.get("pi_room_reported") not in ROOM
            or review.get("pi_room_authentication") != "NOT_PERFORMED"
            or review.get("expected_return_or_alpha") != "NOT_ESTABLISHED_BY_ASSEMBLER"
            or review.get("allocation_percentage") is not None
            or review.get("trade_authority") != "NONE"
            or review.get("storage") != "NONE"):
        raise ValueError("CAPITAL_PATH_RENDER_AUTHORITY_INVALID")
    first = ("IR fourni; aucune admission d'entreprise certifiee par cet assembleur."
             if review["company_branch"] == "RESEARCH_PRESENT_ADMISSION_UNVERIFIED"
             else "Recherche IR originale non fournie; aucune admission etablie.")
    room_label = (
        "Room PI rapporte; compte original non authentifie."
        if review["pi_room_reported"] == "ROOM_EVIDENCE_SUPPORTED" else
        "Room conditionnel; pieces privees a confirmer."
        if review["pi_room_reported"] == "ROOM_CONDITIONAL" else
        "Room personnel non etabli."
    )
    room = ("PI a signale un perimetre conditionnel, non authentifie."
            if review["pi_room_reported"] == "ROOM_CONDITIONAL"
            else "PI ne permet pas de conclure au Portfolio Room prive."
            if review["pi_room_reported"] == "ROOM_UNAVAILABLE"
            else "PI a rapporte un Room supported, sans certification independante.")
    return "\n".join([
        "## High-CAGR — decision de destination du capital, chemin complet",
        "Cette revue suit la hierarchie V2 existante; elle n'est ni une "
        "recommandation, ni un nouveau critere d'admission.",
        "1. **Entreprise individuelle qualifiee :** " + first,
        "2. **VFV, repli normal :** admissibilite reelle sur la plateforme, "
        "cours/date/source, frais, change, fiscalite applicable et concentration "
        "du compte A VERIFIER. Une entreprise non qualifiee ne justifie pas "
        "automatiquement une allocation VFV.",
        "3. **Reserve temporaire exceptionnelle :** uniquement si une justification "
        "extraordinaire et sa politique applicable sont etablies; des donnees "
        "manquantes ne creent pas une reserve strategique.",
        "**Portfolio Room :** " + room,
        "**Conclusion :** destination et pourcentages des nouvelles contributions "
        "NON ETABLIS dans cet assemblage. Ne pas omettre l'examen de VFV; "
        "ne pas inventer rendement espere, encaisse ou achat.",
        "**Deux blocages independants :** (A) rendement total attendu "
        "entreprise/VFV non compare sur une base economique coherente; "
        "un CAGR de prix ou un scenario non pondere ne constitue pas un ER net. "
        "(B) " + room_label + " Une capture de portefeuille ne peut PAS "
        "reparer l'ER manquant.",
        "**Decision :** EVIDENCE_GAP : la prudence sur une allocation ne "
        "conclut pas que les entreprises sont de mauvaise qualite.",
        "**Prochaine action prioritaire :** rechercher et verifier par "
        "instrument une comparaison entreprise/VFV du rendement total "
        "prospectif, des hypothese, horizon, devise, distributions et "
        "sources; signaler ER_UNAVAILABLE si impossible sans conjecture.",
        "**Verification parallele et distincte :** compte et eligibilite "
        "VFV, frais/FX/fiscalite et Room prive date. La reserve reste "
        "exceptionnelle, aucun achat n'est autorise.",
    ])
