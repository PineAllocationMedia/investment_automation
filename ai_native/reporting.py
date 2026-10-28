"""Read-only, evidence-preserving R1 report rendering.

No source retrieval, source verification, storage, scheduling, or trades.
All input statuses are caller-provided and preserved, never upgraded.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

EVIDENCE_STATUSES = frozenset({"VERIFIED", "INDICATIVE", "CONFLICTED", "MISSING"})
REPORT_STATUSES = frozenset({"EXPLORATORY", "CONDITIONAL", "COMPONENT_SUPPORTED"})


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}: nonempty string required")
    return value.strip()


def _iso_date(value: Any, field: str) -> str:
    text = _string(value, field)
    try:
        if date.fromisoformat(text).isoformat() != text:
            raise ValueError
    except ValueError as exc:
        raise ValueError(f"{field}: ISO date YYYY-MM-DD required") from exc
    return text


def _facts(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("facts: list required")
    identifiers: set[str] = set()
    for i, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"facts[{i}]: record required")
        ref = _string(item.get("id"), f"facts[{i}].id")
        if ref in identifiers:
            raise ValueError(f"facts[{i}]: duplicate evidence ID")
        identifiers.add(ref)
        _string(item.get("claim"), f"facts[{i}].claim")
        status = _string(item.get("status"), f"facts[{i}].status")
        if status not in EVIDENCE_STATUSES:
            raise ValueError(f"facts[{i}]: invalid evidence status")
        if status == "VERIFIED":
            url = _string(item.get("source_url"), f"facts[{i}].source_url")
            if not url.startswith("https://"):
                raise ValueError(f"facts[{i}]: verified claim needs HTTPS source URL")
            _string(item.get("period"), f"facts[{i}].period")
            _string(item.get("checked_by"), f"facts[{i}].checked_by")
            _iso_date(item.get("checked_at"), f"facts[{i}].checked_at")
    return value


def _source_review(packet: Mapping[str, Any], analysis_id: str, as_of: str,
                   facts: list[Mapping[str, Any]]) -> tuple[dict[str, list[str]], int] | None:
    """Validate private structural-review handoff, never certify research facts."""
    review = packet.get("fact_source_alignment_private")
    if review is None:
        return None
    if not isinstance(review, Mapping) or (
        review.get("status") != "PRIVATE_FACT_SOURCE_ALIGNMENT_NOT_CERTIFIED"
        or review.get("analysis_id") != analysis_id
        or review.get("analysis_as_of") != as_of
        or review.get("source_authentication") != "NOT_PERFORMED"
        or review.get("evidence_upgrade") != "NONE"
        or review.get("decision_grade_status") != "NOT_ESTABLISHED"
    ):
        raise ValueError("REPORT_SOURCE_REVIEW_AUTHORITY_OR_ID_MISMATCH")
    expected = {f["id"]: f["status"] for f in facts}
    rows = review.get("facts_private")
    if not isinstance(rows, list):
        raise ValueError("REPORT_SOURCE_REVIEW_FACTS_REQUIRED")
    by_id: dict[str, list[str]] = {}
    for entry in rows:
        if not isinstance(entry, Mapping):
            raise ValueError("REPORT_SOURCE_REVIEW_ENTRY_INVALID")
        fid = entry.get("fact_id_private")
        if fid not in expected or fid in by_id or entry.get("ir_reported_status") != expected[fid]:
            raise ValueError("REPORT_SOURCE_REVIEW_FACT_MISMATCH")
        flags = entry.get("review_flags")
        if not isinstance(flags, list) or any(
            not isinstance(f, str) or not f or not all(c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in f)
            for f in flags
        ):
            raise ValueError("REPORT_SOURCE_REVIEW_FLAGS_INVALID")
        alignment = "REVIEW_REQUIRED" if flags else "CALLER_REPORTED_STRUCTURALLY_ALIGNED_ONLY"
        if entry.get("alignment") != alignment:
            raise ValueError("REPORT_SOURCE_REVIEW_ALIGNMENT_MISMATCH")
        by_id[fid] = flags
    count = sum(bool(x) for x in by_id.values())
    if set(by_id) != set(expected) or review.get("facts_needing_review") != count:
        raise ValueError("REPORT_SOURCE_REVIEW_COVERAGE_MISMATCH")
    return by_id, count



def _new_contribution_lines(packet: Mapping[str, Any], analysis_id: str,
                            as_of: str) -> list[str]:
    """Show only supplied NEW-capital percentages, never private positions.

    The gross/funded statuses are computed by the existing M3 helpers. This
    renderer cannot independently validate brokerage economics or holdings.
    """
    summary = packet.get("new_contribution_summary_private")
    if summary is None:
        return []
    if not isinstance(summary, Mapping) or (
        summary.get("analysis_id") != analysis_id
        or summary.get("source_authentication") != "NOT_PERFORMED"
    ):
        raise ValueError("CONTRIBUTION_REPORT_ID_OR_AUTHORITY_MISMATCH")
    observed_at = _iso_date(summary.get("portfolio_as_of"), "portfolio_as_of")
    if observed_at > as_of:
        raise ValueError("CONTRIBUTION_REPORT_OBSERVATION_AFTER_CUTOFF")
    gross = summary.get("gross_status")
    costs = summary.get("cost_status")
    funded = summary.get("funded_status")
    if gross not in {"GROSS_PROJECTION_ONLY", "UNAVAILABLE"} or not isinstance(costs, str) or not isinstance(funded, str):
        raise ValueError("CONTRIBUTION_REPORT_INVALID_STATUS")
    lines = ["", "## New contributions — private, caller-supplied plan"]
    if gross != "GROSS_PROJECTION_ONLY":
        if summary.get("allocations_pct") is not None:
            raise ValueError("CONTRIBUTION_REPORT_UNSUPPORTED_PERCENTAGES")
        lines.append("Gross contribution projection UNAVAILABLE: portfolio scope, cash, currency or identity inputs are not established.")
    else:
        allocations = summary.get("allocations_pct")
        if not isinstance(allocations, Mapping) or not allocations:
            raise ValueError("CONTRIBUTION_REPORT_ALLOCATIONS_REQUIRED")
        exact = {}
        for instrument, raw in allocations.items():
            if (not isinstance(instrument, str) or not instrument.strip()
                    or len(instrument) > 80 or any(ord(c) < 32 for c in instrument)
                    or not isinstance(raw, str)):
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            try:
                pct = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION") from exc
            if not pct.is_finite() or pct < 0 or pct > 100:
                raise ValueError("CONTRIBUTION_REPORT_INVALID_ALLOCATION")
            exact[instrument] = pct
        if sum(exact.values()) != 100:
            raise ValueError("CONTRIBUTION_REPORT_PERCENTAGES_NOT_100")
        lines.append("Percentages of **NEW contribution only** (user/analyst supplied, gross of costs; not portfolio target weights):")
        ordered = sorted(exact, key=lambda key: (-exact[key], key))
        for instrument in ordered[:8]:
            safe = instrument.replace("\\", "\\\\").replace("`", "\\`").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"- `{safe}`: {format(exact[instrument], 'g')}% of new capital")
        if len(ordered) > 8:
            lines.append(f"- {len(ordered) - 8} other destinations in private M3 annex.")
    if costs == "NOT_SUPPLIED" and funded == "NOT_ASSESSED":
        lines.append("Costs/funding NOT ASSESSED: gross plan only; no executable allocation.")
    elif (costs == "SUPPLIED_COST_TALLY_ONLY"
          and funded == "CONDITIONAL_SUPPLIED_COST_BUDGET_RECONCILED"
          and gross == "GROSS_PROJECTION_ONLY"):
        lines.append("Cost-funded budget CONDITIONALLY RECONCILED using caller-supplied fixed fees; percentages are unchanged, but net amounts and funding differ. Requote size-dependent costs and verify account taxes/FX before any decision.")
    elif (costs in {"NOT_SUPPLIED", "INCOMPLETE_COST_INPUTS", "UNAVAILABLE_GROSS_PROJECTION",
                     "UNAVAILABLE_COSTS_EXCEED_CONTRIBUTION", "SUPPLIED_COST_TALLY_ONLY"}
          and (funded == "NOT_ASSESSED" or funded.startswith("UNAVAILABLE_"))):
        lines.append("After-cost funded allocation UNAVAILABLE: charges, funding or scope are incomplete or inconsistent. Do not treat the gross percentages as an executable plan.")
    else:
        raise ValueError("CONTRIBUTION_REPORT_COST_FUNDING_STATUS_MISMATCH")
    lines.append("PI observations and allocations are caller-supplied; no holdings authentication, source certification, price, trade or investment recommendation.")
    return lines

def render_report(packet: Mapping[str, Any]) -> str:
    """Render a concise markdown research report or user-requested follow-up.

    The presence of evidence metadata does not independently validate a claim.
    Portfolio-sensitive packets must remain in the user's private environment.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("packet: mapping required")
    kind = _string(packet.get("kind"), "kind")
    if kind not in {"DECISION", "FOLLOWUP"}:
        raise ValueError("kind: DECISION or FOLLOWUP required")
    analysis_id = _string(packet.get("analysis_id"), "analysis_id")
    as_of = _iso_date(packet.get("as_of"), "as_of")
    strategy = _string(packet.get("strategy"), "strategy")
    method_version = _string(packet.get("method_version"), "method_version")
    status = _string(packet.get("status"), "status")
    if status not in REPORT_STATUSES:
        raise ValueError("unsupported report status")
    objective = _string(packet.get("objective"), "objective")
    decision_line = _string(packet.get("decision_line"), "decision_line")
    next_action = _string(packet.get("next_action"), "next_action")
    if not isinstance(packet.get("summary"), list) or not (1 <= len(packet["summary"]) <= 6):
        raise ValueError("summary: 1 to 6 points required")
    for i, item in enumerate(packet["summary"]):
        _string(item, f"summary[{i}]")
    facts = _facts(packet.get("facts"))
    source_review = _source_review(packet, analysis_id, as_of, facts)
    lines = [
        f"# {'User-requested reassessment' if kind == 'FOLLOWUP' else 'Investment decision research'} — {analysis_id}",
        f"**As of:** {as_of} | **Strategy:** {strategy} | **Method:** {method_version} | **Status:** {status}",
        f"**Question:** {objective}",
        "", "## Decision line", decision_line, "", "## Key findings",
    ]
    lines += [f"- {item.strip()}" for item in packet["summary"]]
    lines += [
        "", "**Source assurance:** IR evidence statuses are research-reported, not "
        "independently authenticated by this report (including rights and historical availability)."
    ]
    if source_review is not None:
        _, flagged_count = source_review
        lines.append(
            f"**Source reconciliation:** {flagged_count}/{len(facts)} facts require "
            "human source-use review based on supplied observations; no status was upgraded."
        )
    lines += ["", "## Supporting observations"]
    if facts:
        for item in facts:
            ref = item["id"].strip()
            evidence_status = item["status"].strip()
            locator = item.get("source_url") or "SOURCE_NOT_SUPPLIED"
            period = item.get("period") or "PERIOD_UNKNOWN"
            lines.append(f"- [{ref} / {evidence_status}] {item['claim'].strip()} (period: {period}; source: {locator})")
            if source_review is not None and source_review[0][ref]:
                flags = ", ".join(source_review[0][ref])
                lines.append(f"  - **Source review required:** {flags}. IR-reported label is not independently corroborated.")
    else:
        lines.append("No underlying fact records supplied; no factual verification is asserted.")
    lines += _new_contribution_lines(packet, analysis_id, as_of)
    if kind == "FOLLOWUP":
        previous_id = packet.get("prior_analysis_id")
        if previous_id is None:
            prior_line = "BASELINE_NOT_AVAILABLE: no previous analysis was provided."
        else:
            prior_line = f"Prior analysis: {_string(previous_id, 'prior_analysis_id')}"
        start_raw, end_raw = packet.get("period_start"), packet.get("period_end")
        if (start_raw is None) != (end_raw is None):
            raise ValueError("follow-up comparison dates must be supplied together")
        if start_raw is None:
            window_label = "no fixed reporting window"
        else:
            start = _iso_date(start_raw, "period_start")
            end = _iso_date(end_raw, "period_end")
            if start > end or end > as_of:
                raise ValueError("follow-up period must be ordered and end by as_of")
            window_label = f"{start} to {end}"
        changes = packet.get("changes")
        if not isinstance(changes, list):
            raise ValueError("changes: list required, possibly empty")
        lines += ["", f"## Requested comparison ({window_label})", prior_line]
        if not changes:
            lines.append("No changes entered in this packet; this is NOT proof that no market or thesis events occurred.")
        else:
            for i, change in enumerate(changes):
                if not isinstance(change, Mapping):
                    raise ValueError(f"changes[{i}]: record required")
                subject = _string(change.get("subject"), f"changes[{i}].subject")
                finding = _string(change.get("finding"), f"changes[{i}].finding")
                cstatus = _string(change.get("status"), f"changes[{i}].status")
                if cstatus not in EVIDENCE_STATUSES:
                    raise ValueError(f"changes[{i}]: invalid status")
                lines.append(f"- **{subject}** [{cstatus}]: {finding}")
    lines += [
        "", "## Strongest countercase / limitation",
        _string(packet.get("countercase"), "countercase"),
        "", "## Evidence and portfolio boundaries",
        _string(packet.get("limitations"), "limitations"),
        "", "## Next human action", next_action,
        "", "_Rendered from supplied data only. No source checks, monitoring, archival or investment execution performed by this formatter._",
    ]
    return "\n".join(lines) + "\n"
