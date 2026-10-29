"""Check optional returned strategy echoes at manual IR/PI handoff boundaries.

A matching string is caller/specialist-reported context only; no proof of
method loading, CEO authorization or research provenance. Missing echoes
remain unverified rather than being invented, for legacy packet compatibility.
"""
from __future__ import annotations

from typing import Any, Mapping

from .strategy_authority import assess_r1_mode


def check_specialist_mode_echo(
    strategy_id: str, packet: Mapping[str, Any], *, specialist: str
) -> str:
    """Reject explicitly contradictory IR/PI mode labels, never upgrade policy."""
    if specialist not in {"IR", "PI"}:
        raise ValueError("SPECIALIST_MODE_ECHO_ROLE_INVALID")
    if not isinstance(packet, Mapping):
        raise ValueError(f"{specialist}_MODE_ECHO_PACKET_MAPPING_REQUIRED")
    # Includes the R1 objective-versus-mode guard, not policy certification.
    assess_r1_mode(strategy_id)
    if "strategy_id" not in packet:
        return "NOT_ECHOED_MODE_NOT_VERIFIED"
    reported = packet["strategy_id"]
    if not isinstance(reported, str) or not reported.strip():
        raise ValueError(f"{specialist}_STRATEGY_MODE_ECHO_INVALID")
    if reported.strip().lower() != strategy_id.strip().lower():
        raise ValueError(f"{specialist}_STRATEGY_MODE_MISMATCH")
    return "MATCHED_SELF_REPORTED_NOT_AUTHENTICATED"
