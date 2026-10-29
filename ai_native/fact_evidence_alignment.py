"""Read-only IR fact versus supplied-source-annex alignment, private and noncertifying.

No fact or source is authenticated; conditional flags never upgrade caller labels.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Mapping

STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
USES = frozenset({"CALLER_REPORTED_ONLY", "INCOMPLETE", "CONFLICTED", "UNAVAILABLE"})


def align_ir_facts_to_sources(
    *, analysis_id: str, analysis_as_of: str,
    ir_facts: list[Mapping[str, Any]], source_annex: Mapping[str, Any],
    ir_research_as_of: str | None = None,
) -> dict[str, Any]:
    """Classify supplied provenance gaps; never replace IR's reported evidence status.

    One negative observation for a fact blocks a clean alignment, even if another
    observation for that fact appears complete. Source quality and source rights
    remain external responsibilities, not verdicts from this helper.
    """
    if not isinstance(analysis_id, str) or not analysis_id.strip():
        raise ValueError("ANALYSIS_ID_REQUIRED")
    if not isinstance(analysis_as_of, str) or not analysis_as_of.strip():
        raise ValueError("ANALYSIS_AS_OF_REQUIRED")
    if not isinstance(ir_facts, list) or not isinstance(source_annex, Mapping):
        raise ValueError("IR_FACTS_AND_ANNEX_REQUIRED")
    if (source_annex.get("status") != "PRIVATE_SOURCE_ANNEX_PREPARED_NOT_CERTIFIED"
            or source_annex.get("analysis_id") != analysis_id
            or source_annex.get("analysis_as_of") != analysis_as_of
            or source_annex.get("source_authentication") != "NOT_PERFORMED_BY_CODE"):
        raise ValueError("ANNEX_ID_DATE_OR_AUTHORITY_MISMATCH")
    ir_cutoff = None
    if ir_research_as_of is not None:
        try:
            ir_cutoff = date.fromisoformat(ir_research_as_of)
            analysis_cutoff = date.fromisoformat(analysis_as_of)
            if (ir_cutoff.isoformat() != ir_research_as_of
                    or analysis_cutoff.isoformat() != analysis_as_of
                    or ir_cutoff > analysis_cutoff):
                raise ValueError("IR_RESEARCH_CUTOFF_INVALID")
        except (TypeError, ValueError) as exc:
            raise ValueError("IR_RESEARCH_CUTOFF_INVALID") from exc
    facts = {}
    for i, fact in enumerate(ir_facts):
        if not isinstance(fact, Mapping):
            raise ValueError(f"IR_FACT_NOT_MAPPING:{i}")
        fid, status = fact.get("id"), fact.get("status")
        if not isinstance(fid, str) or not fid.strip():
            raise ValueError("IR_FACT_ID_REQUIRED")
        if fid in facts:
            raise ValueError("DUPLICATE_IR_FACT_ID")
        if status not in STATUSES:
            raise ValueError("INVALID_IR_FACT_STATUS")
        facts[fid] = status
    observations = source_annex.get("observations_private")
    if not isinstance(observations, list):
        raise ValueError("SOURCE_OBSERVATIONS_LIST_REQUIRED")
    by_fact: dict[str, list[tuple[str, str, bool]]] = defaultdict(list)
    seen = set()
    for item in observations:
        if not isinstance(item, Mapping):
            raise ValueError("SOURCE_OBSERVATION_NOT_MAPPING")
        fid, oid, use = item.get("fact_id"), item.get("observation_id"), item.get("claim_use_status")
        if fid not in facts:
            raise ValueError("SOURCE_ANNEX_UNKNOWN_IR_FACT_ID")
        if not isinstance(oid, str) or not oid.strip() or oid in seen:
            raise ValueError("DUPLICATE_OR_INVALID_OBSERVATION_ID")
        if use not in USES:
            raise ValueError("INVALID_SOURCE_USE_STATUS")
        post_ir = False
        if ir_cutoff is not None:
            value = item.get("observed_at")
            try:
                observed = date.fromisoformat(value)
                if observed.isoformat() != value:
                    raise ValueError("SOURCE_OBSERVATION_DATE_INVALID")
            except (ValueError, TypeError) as exc:
                raise ValueError("SOURCE_OBSERVATION_DATE_INVALID") from exc
            post_ir = observed > ir_cutoff
        seen.add(oid)
        by_fact[fid].append((oid, use, post_ir))
    output = []
    count = 0
    for fid, status in facts.items():
        matched = by_fact.get(fid, [])
        uses = {use for _, use, _ in matched}
        prior_uses = {use for _, use, post in matched if not post}
        flags = []
        if any(post for _, _, post in matched):
            flags.append("CC_SOURCE_POSTDATES_ORIGINAL_IR")
        if not matched:
            flags.append("NO_OBSERVATION_FOR_IR_FACT")
        if "UNAVAILABLE" in uses:
            flags.append("SOURCE_UNAVAILABLE")
        if "CONFLICTED" in uses:
            flags.append("SOURCE_CONFLICTED")
        if "INCOMPLETE" in uses:
            flags.append("SOURCE_INCOMPLETE")
        if status in {"MISSING", "CONFLICTED"}:
            flags.append("IR_FACT_REPORTED_UNRESOLVED")
        if status == "VERIFIED" and (
                not matched or uses != {"CALLER_REPORTED_ONLY"}
                or (ir_cutoff is not None
                    and prior_uses != {"CALLER_REPORTED_ONLY"})):
            flags.append("IR_VERIFIED_LABEL_NOT_SUPPORTED_BY_SUPPLIED_ANNEX")
        if flags:
            count += 1
        output.append({
            "fact_id_private": fid, "ir_reported_status": status,
            "observation_ids_private": [oid for oid, _, _ in matched],
            "source_use_statuses": sorted(uses),
            "review_flags": sorted(set(flags)),
            "alignment": "REVIEW_REQUIRED" if flags else "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY",
        })
    return {
        "status": "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED",
        "analysis_id": analysis_id, "analysis_as_of": analysis_as_of,
        "fact_count": len(facts), "source_observation_count": len(observations),
        "facts_needing_review": count,
        "facts_private": output,
        "source_authentication": "NOT_PERFORMED",
        "evidence_upgrade": "NONE",
        "decision_grade_status": "NOT_ESTABLISHED",
        "public_disclosure": "NONE",
    }
