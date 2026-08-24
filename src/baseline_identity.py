from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .model_version import MODEL_RULES_VERSION
from .utils import CONFIG_DIR, load_yaml, safe_float
from .validation_evidence import (
    VALIDATION_SCHEMA_VERSION,
    normalize_run_purpose,
    purpose_is_genuine_decision,
)


VALIDATION_BASELINE_ID = "VALIDATION_BASELINE_V1"
BASELINE_CONFIG_FILENAME = "baseline.yaml"
BASELINE_PENDING_STATUS = "PENDING_APPROVED_DEPLOYMENT"
BASELINE_FORWARD_OBSERVATION_STATUS = "BASELINE_V1_FORWARD_OBSERVATION"
BASELINE_SNAPSHOT_FIELDS = (
    "baseline_id",
    "baseline_started_at",
    "baseline_status",
    "baseline_evidence_status",
    "baseline_forward_eligible",
    "baseline_authority_reasons",
    "run_timestamp",
    "capital",
    "run_succeeded",
    "critical_input_passed",
    "approved_config_active",
    "dependency_status",
    "git_tracked_worktree_clean",
    "git_tracked_diff_fingerprint",
    "eligibility_basis",
)


def load_baseline_identity(config_path: str | Path | None = None) -> dict[str, str]:
    path = Path(config_path) if config_path is not None else CONFIG_DIR / BASELINE_CONFIG_FILENAME
    payload = load_yaml(path)
    baseline_id = str(payload.get("baseline_id") or VALIDATION_BASELINE_ID).strip()
    started_at = str(
        os.environ.get("INVESTMENT_AUTOMATION_BASELINE_STARTED_AT")
        or payload.get("baseline_started_at")
        or ""
    ).strip()
    configured_status = str(payload.get("baseline_status") or "").strip().upper()
    if baseline_id != VALIDATION_BASELINE_ID:
        configured_status = "BASELINE_ID_MISMATCH"
    elif not started_at:
        configured_status = BASELINE_PENDING_STATUS
    elif not configured_status or configured_status == BASELINE_PENDING_STATUS:
        configured_status = "ACTIVE"
    return {
        "baseline_id": baseline_id,
        "baseline_started_at": started_at,
        "baseline_status": configured_status,
        "approved_config_fingerprint": str(payload.get("approved_config_fingerprint") or "").strip().lower(),
        "model_rules_version": MODEL_RULES_VERSION,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
    }


def baseline_observation_metadata(
    *,
    run_timestamp: str | datetime,
    run_purpose: Any,
    capital: Any = None,
    config_path: str | Path | None = None,
    run_succeeded: bool = True,
    critical_input_passed: bool = True,
    approved_config_active: bool = True,
    dependency_status: str = "MATCH",
    git_tracked_worktree_clean: bool = True,
    git_tracked_diff_fingerprint: str = "",
    eligibility_basis: str = "EXPLICIT_RUN_PURPOSE",
) -> dict[str, Any]:
    identity = load_baseline_identity(config_path)
    purpose = normalize_run_purpose(run_purpose)
    observation = {
        **identity,
        "run_timestamp": run_timestamp.isoformat() if isinstance(run_timestamp, datetime) else str(run_timestamp or ""),
        "run_purpose": purpose,
        "capital": capital,
        "run_succeeded": run_succeeded,
        "critical_input_passed": critical_input_passed,
        "approved_config_active": approved_config_active,
        "dependency_status": str(dependency_status or "UNKNOWN").upper(),
        "git_tracked_worktree_clean": git_tracked_worktree_clean,
        "git_tracked_diff_fingerprint": str(git_tracked_diff_fingerprint or ""),
        "eligibility_basis": eligibility_basis,
    }
    return baseline_forward_authority(observation)


def baseline_forward_authority(
    observation: Mapping[str, Any],
    *,
    require_declared_eligibility: bool = False,
) -> dict[str, Any]:
    """Classify only VALIDATION_BASELINE_V1 forward authority.

    This deliberately does not replace the generic P2/OOS evidence hierarchy.
    Historical reporting passes ``require_declared_eligibility=True`` so an old
    snapshot can never be retroactively promoted into the Baseline.
    """
    payload = dict(observation)
    baseline_id = str(payload.get("baseline_id") or "").strip()
    baseline_status = str(payload.get("baseline_status") or "").strip().upper()
    run_at = _parse_datetime(payload.get("run_timestamp") or payload.get("created_at"))
    started_at = _parse_datetime(payload.get("baseline_started_at"))
    purpose = normalize_run_purpose(payload.get("run_purpose"))
    numeric_capital = safe_float(payload.get("capital"))
    eligibility_basis = str(payload.get("eligibility_basis") or "").strip().upper()

    reasons: list[str] = []
    if baseline_id != VALIDATION_BASELINE_ID:
        reasons.append("BASELINE_ID_MISMATCH")
    if baseline_status == BASELINE_PENDING_STATUS or started_at is None:
        reasons.append("PRE_BASELINE_PENDING_APPROVED_DEPLOYMENT")
    elif baseline_status != "ACTIVE":
        reasons.append("BASELINE_STATUS_NOT_ACTIVE")
    if run_at is None:
        reasons.append("INVALID_RUN_TIMESTAMP")
    elif started_at is not None and run_at < started_at:
        reasons.append("PRE_BASELINE_OBSERVATION")
    if numeric_capital is None:
        reasons.append("BASELINE_INVALID_CAPITAL_OBSERVATION")
    elif numeric_capital == 0:
        reasons.append("BASELINE_ZERO_CAPITAL_OBSERVATION")
    elif numeric_capital < 0:
        reasons.append("BASELINE_NONPOSITIVE_CAPITAL_OBSERVATION")
    if not purpose_is_genuine_decision(purpose):
        reasons.append("BASELINE_NON_DECISION_OBSERVATION")
    if eligibility_basis == "LEGACY_PARTIALLY_RECOVERABLE":
        reasons.append("BASELINE_LEGACY_AUTHORITY_EXCLUDED")
    if payload.get("run_succeeded") is not True:
        reasons.append("BASELINE_RUN_NOT_SUCCESSFUL")
    if payload.get("critical_input_passed") is not True:
        reasons.append("BASELINE_CRITICAL_INPUT_AUDIT_NOT_PASSED")
    if payload.get("approved_config_active") is not True:
        reasons.append("BASELINE_APPROVED_CONFIG_NOT_ACTIVE")
    if str(payload.get("dependency_status") or "").strip().upper() != "MATCH":
        reasons.append("BASELINE_DEPENDENCY_ENVIRONMENT_INVALID")
    if payload.get("git_tracked_worktree_clean") is not True:
        reasons.append("BASELINE_TRACKED_GIT_STATE_INVALID")
    if require_declared_eligibility and payload.get("baseline_forward_eligible") is not True:
        reasons.append("BASELINE_NOT_DECLARED_FORWARD_ELIGIBLE")

    eligible = not reasons
    return {
        **payload,
        "run_purpose": purpose,
        "baseline_evidence_status": BASELINE_FORWARD_OBSERVATION_STATUS if eligible else reasons[0],
        "baseline_forward_eligible": eligible,
        "baseline_authority_reasons": reasons,
    }


def baseline_snapshot_fields(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(metadata or {})
    return {field: payload.get(field, False if field == "baseline_forward_eligible" else "") for field in BASELINE_SNAPSHOT_FIELDS}


def combined_baseline_snapshot_authority(
    payloads: Iterable[Mapping[str, Any]],
    *,
    run_purpose: Any,
) -> dict[str, Any]:
    """Apply the canonical authority formula to a paired analysis/allocation run."""
    snapshots = [dict(payload) for payload in payloads]
    if len(snapshots) != 2:
        return {
            "baseline_id": next((str(payload.get("baseline_id") or "") for payload in snapshots), ""),
            "baseline_evidence_status": "BASELINE_PAIRED_SNAPSHOT_REQUIRED",
            "baseline_forward_eligible": False,
        }
    authorities = [
        baseline_forward_authority(
            {
                **payload,
                "run_timestamp": payload.get("run_timestamp") or payload.get("created_at"),
                "run_purpose": run_purpose,
            },
            require_declared_eligibility=True,
        )
        for payload in snapshots
    ]
    manifest_fingerprints = {str(payload.get("manifest_fingerprint") or "") for payload in snapshots}
    same_manifest = len(manifest_fingerprints) == 1 and "" not in manifest_fingerprints
    eligible = same_manifest and all(authority.get("baseline_forward_eligible") is True for authority in authorities)
    selected = authorities[0]
    return {
        "baseline_id": str(selected.get("baseline_id") or ""),
        "baseline_evidence_status": (
            BASELINE_FORWARD_OBSERVATION_STATUS
            if eligible
            else "BASELINE_PAIRED_MANIFEST_MISMATCH"
            if not same_manifest
            else next(
                (
                    str(authority.get("baseline_evidence_status") or "")
                    for authority in authorities
                    if not authority.get("baseline_forward_eligible")
                ),
                "BASELINE_NOT_FORWARD_ELIGIBLE",
            )
        ),
        "baseline_forward_eligible": eligible,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed
