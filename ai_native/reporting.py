"""Read-only, evidence-preserving R1 report rendering.

No source retrieval, source verification, storage, scheduling, or trades.
All input statuses are caller-provided and preserved, never upgraded.
"""
from __future__ import annotations

from datetime import date
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


def render_report(packet: Mapping[str, Any]) -> str:
    """Render a concise markdown research or weekly brief from supplied observations.

    The presence of evidence metadata does not independently validate a claim.
    Portfolio-sensitive packets must remain in the user's private environment.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("packet: mapping required")
    kind = _string(packet.get("kind"), "kind")
    if kind not in {"DECISION", "WEEKLY"}:
        raise ValueError("kind: DECISION or WEEKLY required")
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
    lines = [
        f"# {'Weekly intelligence' if kind == 'WEEKLY' else 'Investment decision research'} — {analysis_id}",
        f"**As of:** {as_of} | **Strategy:** {strategy} | **Method:** {method_version} | **Status:** {status}",
        f"**Question:** {objective}",
        "", "## Decision line", decision_line, "", "## Key findings",
    ]
    lines += [f"- {item.strip()}" for item in packet["summary"]]
    lines += ["", "## Supporting observations"]
    if facts:
        for item in facts:
            ref = item["id"].strip()
            evidence_status = item["status"].strip()
            locator = item.get("source_url") or "SOURCE_NOT_SUPPLIED"
            period = item.get("period") or "PERIOD_UNKNOWN"
            lines.append(f"- [{ref} / {evidence_status}] {item['claim'].strip()} (period: {period}; source: {locator})")
    else:
        lines.append("No underlying fact records supplied; no factual verification is asserted.")
    if kind == "WEEKLY":
        start = _iso_date(packet.get("period_start"), "period_start")
        end = _iso_date(packet.get("period_end"), "period_end")
        if start > end or end > as_of:
            raise ValueError("weekly period must be ordered and end by as_of")
        changes = packet.get("changes")
        if not isinstance(changes, list):
            raise ValueError("changes: list required, possibly empty")
        lines += ["", f"## Changes reviewed ({start} to {end})"]
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
