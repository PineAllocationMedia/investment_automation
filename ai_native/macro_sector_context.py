"""Private source-linked macro/sector causal research review, never timing.

Requires original IR fact IDs and a structurally assembled source annex. All
links and impacts are human-reported; no source or causality is certified.
"""
from __future__ import annotations
from datetime import date
import re
from typing import Any, Mapping

IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
SCOPES = {"MACRO", "SECTOR"}
EFFECTS = {"TAILWIND_REPORTED", "HEADWIND_REPORTED", "MIXED_REPORTED", "UNKNOWN"}
FACT_STATUSES = {"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"}
SOURCE_STATUSES = {"CALLER_REPORTED_ONLY", "INCOMPLETE", "CONFLICTED", "UNAVAILABLE"}
DRIVER_KEYS = {"driver_id", "scope", "reported_effect", "ir_fact_ids",
               "source_observation_ids", "hypothesis_private", "countercase_private",
               "next_check_private"}


def _id(value: Any) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise ValueError("CONTEXT_SAFE_IDENTIFIER_REQUIRED")
    return value


def _date(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("CONTEXT_DATE_INVALID")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise ValueError("CONTEXT_DATE_INVALID") from exc
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 1500:
        raise ValueError("CONTEXT_NONEMPTY_BOUNDED_TEXT_REQUIRED")
    return value.strip()


def _ids(value: Any) -> list[str]:
    if not isinstance(value, list) or len(value) > 20:
        raise ValueError("CONTEXT_LINK_LIST_INVALID")
    result = [_id(item) for item in value]
    if len(set(result)) != len(result):
        raise ValueError("CONTEXT_DUPLICATE_LINK")
    return result


def prepare_macro_sector_context(*, analysis_id: str, analysis_as_of: str,
                                 strategy_id: str, drivers: list[Mapping[str, Any]],
                                 ir_facts: list[Mapping[str, Any]],
                                 source_annex: Mapping[str, Any]) -> dict[str, Any]:
    aid, cutoff, strategy = _id(analysis_id), _date(analysis_as_of), _text(strategy_id)
    if (not isinstance(source_annex, Mapping)
            or source_annex.get("status") != "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
            or source_annex.get("analysis_id") != aid
            or source_annex.get("analysis_as_of") != cutoff
            or source_annex.get("source_authentication") != "NOT_PERFORMED_BY_CODE"):
        raise ValueError("CONTEXT_SOURCE_ANNEX_MISMATCH")
    if not isinstance(ir_facts, list):
        raise ValueError("CONTEXT_IR_FACTS_INVALID")
    facts = {}
    for fact in ir_facts:
        if not isinstance(fact, Mapping):
            raise ValueError("CONTEXT_IR_FACT_INVALID")
        fid = _id(fact.get("id"))
        if fid in facts or fact.get("status") not in FACT_STATUSES:
            raise ValueError("CONTEXT_IR_FACT_ID_OR_STATUS_INVALID")
        facts[fid] = fact["status"]
    source_rows = source_annex.get("observations_private")
    if not isinstance(source_rows, list):
        raise ValueError("CONTEXT_OBSERVATION_LIST_INVALID")
    sources = {}
    for source in source_rows:
        if not isinstance(source, Mapping):
            raise ValueError("CONTEXT_SOURCE_ROW_INVALID")
        sid = _id(source.get("observation_id"))
        if (sid in sources or source.get("fact_id") not in facts
                or source.get("claim_use_status") not in SOURCE_STATUSES):
            raise ValueError("CONTEXT_OBSERVATION_ID_OR_FACT_INVALID")
        sources[sid] = source
    if not isinstance(drivers, list) or not 1 <= len(drivers) <= 8:
        raise ValueError("CONTEXT_DRIVER_COUNT_INVALID")
    prepared, used = [], set()
    counts = {"EVIDENCE_RESOLUTION": 0, "HUMAN_CAUSAL_REVIEW": 0}
    for driver in drivers:
        if not isinstance(driver, Mapping) or set(driver) != DRIVER_KEYS:
            raise ValueError("CONTEXT_DRIVER_EXACT_SCHEMA_REQUIRED")
        did = _id(driver["driver_id"])
        if did in used:
            raise ValueError("CONTEXT_DUPLICATE_DRIVER")
        used.add(did)
        scope, effect = driver["scope"], driver["reported_effect"]
        if scope not in SCOPES or effect not in EFFECTS:
            raise ValueError("CONTEXT_SCOPE_OR_EFFECT_INVALID")
        refs, links = _ids(driver["ir_fact_ids"]), _ids(driver["source_observation_ids"])
        if not refs or any(fid not in facts for fid in refs):
            raise ValueError("CONTEXT_UNKNOWN_OR_MISSING_IR_FACT")
        reasons = set()
        if not links:
            reasons.add("NO_LINKED_SOURCE_OBSERVATIONS")
        if any(facts[fid] in {"MISSING", "CONFLICTED"} for fid in refs):
            reasons.add("IR_FACT_UNRESOLVED")
        for sid in links:
            if sid not in sources:
                raise ValueError("CONTEXT_UNKNOWN_SOURCE_OBSERVATION")
            source = sources[sid]
            if source["fact_id"] not in refs:
                raise ValueError("CONTEXT_SOURCE_FACT_LINK_MISMATCH")
            if source["claim_use_status"] != "CALLER_REPORTED_ONLY":
                reasons.add("SOURCE_UNRESOLVED_OR_UNUSABLE")
            if source.get("rights_status") != "PERMITTED":
                reasons.add("SOURCE_RIGHTS_NOT_ESTABLISHED")
            if source.get("source_kind") != "ISSUER_OR_REGULATOR":
                reasons.add("PRIMARY_SOURCE_NOT_DOCUMENTED")
        if effect == "UNKNOWN":
            reasons.add("DIRECTIONAL_EFFECT_UNKNOWN")
        stage = "EVIDENCE_RESOLUTION" if reasons else "HUMAN_CAUSAL_REVIEW"
        counts[stage] += 1
        prepared.append({
            "driver_id": did, "scope": scope, "reported_effect": effect,
            "research_work_stage": stage, "review_reasons": sorted(reasons),
            "ir_fact_ids_private": refs, "source_observation_ids_private": links,
            "hypothesis_private": _text(driver["hypothesis_private"]),
            "countercase_private": _text(driver["countercase_private"]),
            "next_check_private": _text(driver["next_check_private"]),
            "causal_authentication": "NOT_PERFORMED"})
    return {
        "status": "PRIVATE_MACRO_SECTOR_CONTEXT_PREPARED_NOT_CERTIFIED",
        "analysis_id": aid, "analysis_as_of": cutoff, "strategy_id": strategy,
        "driver_count": len(prepared), "stage_counts": counts,
        "drivers_private_in_supplied_order": prepared,
        "source_authentication": "NOT_PERFORMED",
        "causal_inference": "ANALYST_HYPOTHESIS_NOT_CERTIFIED",
        "market_timing_or_price_prediction": "NONE",
        "ranking_or_trading_authority": "NONE", "public_memory_write": "NONE"}
