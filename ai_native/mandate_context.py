"""Private, non-authorizing investor profile and per-request mandate context.

Values here are CEO/caller-supplied, not evidence, system instructions, an
authenticated mandate, or a way to change a mode's approved investment policy.
No external access, storage, hidden defaults or prompt execution.
"""
from __future__ import annotations

from typing import Any, Mapping

PREFERENCE_KEYS = frozenset({
    "analysis_focus", "comparison_focus", "communication_style",
})
PROFILE_KEYS = frozenset({"summary", "preferences"})
MAX_PROFILE_SUMMARY = 800
MAX_MANDATE_PROMPT = 3000
MAX_PREFERENCE = 200


def _text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise ValueError("MANDATE_CONTEXT_INVALID_" + label)
    return value.strip()


def _preferences(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) - PREFERENCE_KEYS:
        raise ValueError("MANDATE_CONTEXT_INVALID_" + label)
    return {
        key: _text(value[key], "PREFERENCE", MAX_PREFERENCE)
        for key in sorted(value)
    }


def prepare_mandate_context(request: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve optional profile versus explicit *preference* overrides only.

    A free-text mandate is preserved verbatim as private user data; it does
    not overwrite structural request fields (strategy, horizon, limits, dates,
    account costs) or override evidence / CEO-approved policy. Project-facing
    instructions must also respect these trust boundaries.
    """
    if not isinstance(request, Mapping):
        raise ValueError("MANDATE_CONTEXT_REQUEST_MAPPING_REQUIRED")
    supplied_profile = request.get("investor_profile_private")
    profile = None
    profile_preferences: dict[str, str] = {}
    if supplied_profile is not None:
        if not isinstance(supplied_profile, dict) or not supplied_profile or set(supplied_profile) - PROFILE_KEYS:
            raise ValueError("MANDATE_CONTEXT_INVALID_PROFILE")
        summary = (
            _text(supplied_profile["summary"], "PROFILE_SUMMARY", MAX_PROFILE_SUMMARY)
            if "summary" in supplied_profile else None
        )
        profile_preferences = _preferences(
            supplied_profile.get("preferences", {}), "PROFILE_PREFERENCES"
        )
        if summary is None and not profile_preferences:
            raise ValueError("MANDATE_CONTEXT_EMPTY_PROFILE")
        profile = {"summary": summary, "preferences": profile_preferences}
    prompt = request.get("mandate_prompt_private")
    if prompt is not None:
        prompt = _text(prompt, "MANDATE_PROMPT", MAX_MANDATE_PROMPT)
    mandate_preferences = request.get("mandate_preferences_private", {})
    overrides = _preferences(mandate_preferences, "MANDATE_PREFERENCES")
    effective = {**profile_preferences, **overrides}
    provenance = {
        key: "EXPLICIT_MANDATE" if key in overrides else "OPTIONAL_PROFILE"
        for key in sorted(effective)
    }
    return {
        "status": (
            "USER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED"
            if profile is not None or prompt is not None or overrides
            else "NOT_SUPPLIED"
        ),
        "investor_profile_private": profile,
        "mandate_prompt_private": prompt,
        "effective_preferences_private": effective,
        "preference_provenance": provenance,
        "priority": "EXPLICIT_MANDATE_OVERRIDES_OPTIONAL_PROFILE_PREFERENCES_ONLY",
        "structural_request_override": "NONE",
        "financial_policy_override": "NONE",
        "method_loading": "NOT_PERFORMED",
        "source_authentication": "NOT_PERFORMED",
        "storage": "NONE",
    }
