"""Private ChatGPT Work/Blossom visual-observation handoff, not a browser client.

Converts an explicitly user-authorized, structured Work report or manually
supplied screenshot transcript into the existing M3 P-ledger contract. The
browser's claims and displayed fields are not independently authenticated.
No site access, disk/network write, logging, secret handling or trading.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .portfolio_observation import prepare_observation_ledger

WORK_HOSTS = frozenset({"www.blossomsocial.com", "blossomsocial.com"})
MODES = frozenset({"WORK_BROWSER", "USER_SCREENSHOT"})
COVERAGE_FLAGS = (
    "account_filter_visible", "all_rows_visible", "other_group_expanded_or_absent",
    "cash_checked", "same_currency_basis_visible",
)


def _bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name}: explicit boolean required")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty text required")
    return value.strip()


def prepare_work_blossom_observation(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Prepare a private P-ledger from explicitly reported browser visibility.

    A Work browser task must be started separately by the user. This function
    cannot browse, sign in, attest the displayed portfolio or forward to a
    different ChatGPT Project. Its result is for a manual authorized handoff.
    """
    if not isinstance(packet, Mapping):
        raise ValueError("packet: mapping required")
    mode = _text(packet.get("capture_mode"), "capture_mode")
    if mode not in MODES:
        raise ValueError("capture_mode: WORK_BROWSER or USER_SCREENSHOT")
    state = _text(packet.get("view_status"), "view_status")
    if state not in {"VISIBLE", "UNAVAILABLE"}:
        raise ValueError("view_status: VISIBLE or UNAVAILABLE")
    if state == "UNAVAILABLE":
        # Do not inspect or carry private fields from an inaccessible view.
        return {"status": "VISUAL_SOURCE_UNAVAILABLE_USE_SCREENSHOT_FALLBACK",
                "observation_inputs_private": None, "p_ledger_private": None,
                "work_compatibility": "UNVERIFIED_OR_UNAVAILABLE",
                "transfer": "MANUAL_ONLY", "project_invocation": "NONE"}
    if _bool(packet.get("user_authorized_read_only"), "user_authorized_read_only") is not True:
        raise ValueError("CEO_READ_ONLY_AUTHORIZATION_REQUIRED")
    if _bool(packet.get("private_portfolio_view"), "private_portfolio_view") is not True:
        raise ValueError("PUBLIC_VIEW_NOT_PRIVATE_HOLDINGS")
    if mode == "WORK_BROWSER":
        host = _text(packet.get("browser_hostname"), "browser_hostname").lower()
        if host not in WORK_HOSTS:
            raise ValueError("UNEXPECTED_BLOSSOM_BROWSER_HOST")
        if _bool(packet.get("work_reported_signed_in"), "work_reported_signed_in") is not True:
            raise ValueError("PRIVATE_AUTHENTICATED_VIEW_NOT_REPORTED")
    # Screenshot mode never implies a Work browser session or a Blossom login.
    caller_source_visible = _bool(packet.get("source_access_reported"), "source_access_reported")
    evidence = packet.get("coverage_evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("coverage_evidence: explicit flags required")
    flags = {name: _bool(evidence.get(name), name) for name in COVERAGE_FLAGS}
    scope_complete = all(flags[name] for name in COVERAGE_FLAGS[:-1])
    same_currency = flags["same_currency_basis_visible"]
    rows = packet.get("positions")
    if not isinstance(rows, list) or not rows:
        raise ValueError("positions: explicit nonempty observed rows required")
    # No raw HTML, page URLs, authentication tokens, screenshots or extra
    # fields are forwarded; only a strict subset of structured observations.
    positions = []
    for index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ValueError(f"positions[{index}]: mapping required")
        positions.append({key: deepcopy(raw.get(key)) for key in
                          ("p_id", "security_id", "market_value_base", "currency",
                           "account_scope", "field_statuses", "displayed_weight_pct",
                           "displayed_weight_visibility")})
    kwargs = {
        "analysis_id": _text(packet.get("analysis_id"), "analysis_id"),
        "observed_on": _text(packet.get("observed_on"), "observed_on"),
        "analysis_as_of": _text(packet.get("analysis_as_of"), "analysis_as_of"),
        "captured_at": _text(packet.get("captured_at"), "captured_at"),
        "source_type": ("AUTHORIZED_BLOSSOM_TRANSCRIPTION" if mode == "WORK_BROWSER"
                        else "PRIVATE_SCREENSHOT_TRANSCRIPTION"),
        "private_scope": True,
        "source_access_confirmed_by_caller": caller_source_visible,
        "account_scope": _text(packet.get("account_scope"), "account_scope"),
        "currency": _text(packet.get("currency"), "currency"),
        "scope_complete": scope_complete,
        "cash_base": packet.get("cash_base"),
        "cash_visibility": _text(packet.get("cash_visibility"), "cash_visibility"),
        "same_currency_basis_confirmed_by_caller": same_currency,
        "positions": positions,
    }
    # Reuse M3 actual ledger guardrails; do not invent another weight engine.
    ledger = prepare_observation_ledger(**kwargs)
    return {
        "status": "PRIVATE_OBSERVATION_PACKET_PREPARED_NOT_SENT",
        "observation_inputs_private": kwargs,
        "p_ledger_private": ledger,
        "capture_mode": mode,
        "visibility_basis": "WORK_OR_USER_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
        "work_compatibility": "NOT_INDEPENDENTLY_TESTED_BY_ADAPTER",
        "transfer": "MANUAL_ONLY", "project_invocation": "NONE",
    }
