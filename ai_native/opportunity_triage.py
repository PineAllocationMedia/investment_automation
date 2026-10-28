"""Non-ranking, private opportunity research triage from supplied IR/source records.

This is a provenance-aware *research queue*, not market discovery, a stock screen,
investment suitability, normalized Expected Return, or investment admission.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Mapping

SCOPES = frozenset({"OWN_PORTFOLIO", "WATCHLIST", "GLOBAL_DISCOVERY", "MIXED_REQUEST"})
ORIGINS = frozenset({"OWN_PORTFOLIO", "WATCHLIST", "PUBLIC_DISCOVERY", "CEO_NOMINATED"})
TARGETS = frozenset({"ISSUER", "SECTOR_ETF", "REFERENCE_ETF"})
IR_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
SOURCE_STATUSES = frozenset({"CALLER_REPORTED_ONLY", "INCOMPLETE", "CONFLICTED", "UNAVAILABLE"})


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty text required")
    return value.strip()


def _items(value: Any, field: str, *, required: bool = False) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        raise ValueError(f"{field}: explicit list required")
    out = [_text(x, field) for x in value]
    if len(out) != len(set(out)):
        raise ValueError(f"{field}: duplicate entry")
    return out


def prepare_opportunity_triage(
    *, analysis_id: str, analysis_as_of: str, strategy_id: str,
    universe_scope: str, universe_note: str,
    candidates: list[Mapping[str, Any]],
    ir_facts: list[Mapping[str, Any]], source_annex: Mapping[str, Any],
) -> dict[str, Any]:
    """Preserve nominated candidates and classify *research work*, without ranking.

    An observation can never certify its own source. Any unusable observation
    linked to a candidate keeps it in the evidence-resolution queue even if
    another observation looks clean; no veto on researching that candidate.
    """
    aid = _text(analysis_id, "analysis_id")
    cutoff = _text(analysis_as_of, "analysis_as_of")
    try:
        parsed_cutoff = date.fromisoformat(cutoff)
    except ValueError as exc:
        raise ValueError("ANALYSIS_DATE_INVALID") from exc
    if parsed_cutoff.isoformat() != cutoff:
        raise ValueError("ANALYSIS_DATE_INVALID")
    strategy = _text(strategy_id, "strategy_id")
    scope = _text(universe_scope, "universe_scope")
    note = _text(universe_note, "universe_note")
    if scope not in SCOPES:
        raise ValueError("UNIVERSE_SCOPE_UNSUPPORTED")
    if (not isinstance(source_annex, Mapping)
            or source_annex.get("status") != "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
            or source_annex.get("analysis_id") != aid
            or source_annex.get("analysis_as_of") != cutoff
            or source_annex.get("source_authentication") != "NOT_PERFORMED_BY_CODE"):
        raise ValueError("OPPORTUNITY_SOURCE_ANNEX_MISMATCH")
    if not isinstance(ir_facts, list):
        raise ValueError("IR_FACTS_LIST_REQUIRED")
    facts: dict[str, str] = {}
    for raw in ir_facts:
        if not isinstance(raw, Mapping):
            raise ValueError("IR_FACT_INVALID")
        fid = _text(raw.get("id"), "ir_fact.id")
        status = _text(raw.get("status"), "ir_fact.status")
        if fid in facts or status not in IR_STATUSES:
            raise ValueError("IR_FACT_ID_OR_STATUS_INVALID")
        facts[fid] = status
    observations = source_annex.get("observations_private")
    if not isinstance(observations, list):
        raise ValueError("SOURCE_OBSERVATIONS_INVALID")
    by_fact: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    seen_observations: set[str] = set()
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise ValueError("SOURCE_OBSERVATION_INVALID")
        oid = _text(raw.get("observation_id"), "observation_id")
        fid = _text(raw.get("fact_id"), "source.fact_id")
        status = _text(raw.get("claim_use_status"), "source.claim_use_status")
        if oid in seen_observations or fid not in facts or status not in SOURCE_STATUSES:
            raise ValueError("SOURCE_OBSERVATION_ID_OR_STATUS_INVALID")
        seen_observations.add(oid)
        by_fact[fid].append(raw)
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= 30:
        raise ValueError("CANDIDATE_COUNT_MUST_BE_1_TO_30")
    ids: set[str] = set()
    targets: set[tuple[str, str]] = set()
    results = []
    review_counts = {"EVIDENCE_RESOLUTION": 0, "HUMAN_DEEP_DIVE": 0}
    for index, raw in enumerate(candidates):
        if not isinstance(raw, Mapping):
            raise ValueError(f"CANDIDATE_{index}_INVALID")
        cid = _text(raw.get("candidate_id"), "candidate_id")
        issuer = _text(raw.get("economic_issuer"), "economic_issuer")
        instrument = _text(raw.get("instrument"), "instrument")
        target = _text(raw.get("target_type"), "target_type")
        origin = _text(raw.get("origin_scope"), "origin_scope")
        question = _text(raw.get("research_question"), "research_question")
        refs = _items(raw.get("ir_fact_ids"), "ir_fact_ids")
        open_questions = _items(raw.get("open_questions"), "open_questions", required=True)
        known_risks = _items(raw.get("known_risks"), "known_risks")
        if cid in ids or (issuer, instrument) in targets:
            raise ValueError("DUPLICATE_CANDIDATE_OR_SECURITY")
        if target not in TARGETS or origin not in ORIGINS:
            raise ValueError("CANDIDATE_KIND_OR_ORIGIN_UNSUPPORTED")
        if any(fid not in facts for fid in refs):
            raise ValueError("CANDIDATE_UNKNOWN_ORIGINAL_IR_FACT")
        ids.add(cid)
        targets.add((issuer, instrument))
        issues: set[str] = set()
        obs_ids: list[str] = []
        if not refs:
            issues.add("NO_ORIGINAL_IR_FACT_LINKS")
        for fid in refs:
            if facts[fid] in {"MISSING", "CONFLICTED"}:
                issues.add("IR_FACT_UNRESOLVED")
            linked = by_fact.get(fid, [])
            if not linked:
                issues.add("NO_SOURCE_OBSERVATION")
            for observation in linked:
                obs_ids.append(observation["observation_id"])
                if (observation.get("economic_issuer") != issuer
                        or observation.get("instrument") != instrument):
                    issues.add("SOURCE_SECURITY_IDENTITY_MISMATCH")
                if observation["claim_use_status"] != "CALLER_REPORTED_ONLY":
                    issues.add("SOURCE_UNRESOLVED_OR_UNUSABLE")
                if observation.get("rights_status") != "PERMITTED":
                    issues.add("SOURCE_RIGHTS_NOT_ESTABLISHED")
                if (observation.get("source_kind") != "ISSUER_OR_REGULATOR"
                        or observation.get("classification") != "SOURCE_FACT"):
                    issues.add("PRIMARY_SOURCE_FACT_NOT_DOCUMENTED")
        stage = "EVIDENCE_RESOLUTION" if issues else "HUMAN_DEEP_DIVE"
        review_counts[stage] += 1
        results.append({
            "candidate_id_private": cid,
            "economic_issuer_private": issuer,
            "instrument_private": instrument,
            "target_type": target, "origin_scope": origin,
            "research_question_private": question,
            "ir_fact_ids_private": refs,
            "source_observation_ids_private": sorted(set(obs_ids)),
            "open_questions_private": open_questions,
            "known_risks_private": known_risks,
            "research_work_stage": stage,
            "review_reasons": sorted(issues),
            "selection_status": "CEO_OR_ANALYST_REVIEW_ONLY",
            "investability": "NOT_EVALUATED",
        })
    return {
        "status": "PRIVATE_RESEARCH_TRIAGE_PREPARED_NOT_RANKED",
        "analysis_id": aid, "analysis_as_of": cutoff,
        "strategy_id": strategy, "universe_scope": scope,
        "universe_note_private": note,
        "declared_candidate_count": len(results),
        "stage_counts": review_counts,
        "candidates_private_in_supplied_order": results,
        "universe_completeness": "NOT_VERIFIED_NOT_GLOBAL_SCREENING",
        "source_authentication": "NOT_PERFORMED",
        "normalized_expected_return": "NOT_ESTABLISHED",
        "ranking_or_buy_recommendation": "NONE",
        "portfolio_allocation": "NONE",
        "external_discovery_or_storage": "NONE",
    }
