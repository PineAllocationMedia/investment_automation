from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .model_version import MODEL_RULES_VERSION
from .model_identity import (IDENTITY_FIELDS, current_model_identity, identity_fields,
                             evidence_cohort, explicit_true, production_identity_reasons)
from .utils import CONFIG_DIR, load_yaml, safe_float
from .validation_evidence import (
    VALIDATION_SCHEMA_VERSION,
    normalize_run_purpose,
    purpose_is_genuine_decision,
    EXPLICIT_DECISION_ELIGIBILITY_BASIS,
    EvidenceClass,
    walk_forward_period_has_strategy_validation_authority,
)


VALIDATION_BASELINE_ID = "VALIDATION_BASELINE_V1"
BASELINE_CONFIG_FILENAME = "baseline.yaml"
BASELINE_PENDING_STATUS = "PENDING_APPROVED_DEPLOYMENT"
BASELINE_FORWARD_OBSERVATION_STATUS = "BASELINE_V1_FORWARD_OBSERVATION"
BASELINE_SNAPSHOT_FIELDS = (
    *IDENTITY_FIELDS,
    "run_id",
    "strategy_validation_authority",
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
    identity = current_model_identity()
    if identity["model_lineage"] != "V1":
        return {**identity, "baseline_id": "", "baseline_started_at": "",
                "baseline_status": "NOT_ESTABLISHED", "approved_config_fingerprint": ""}
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
        **identity,
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
    eligibility_basis: str = EXPLICIT_DECISION_ELIGIBILITY_BASIS,
    run_id: str = "",
) -> dict[str, Any]:
    identity = load_baseline_identity(config_path)
    purpose = normalize_run_purpose(run_purpose)
    observation = {
        **identity,
        "run_id": run_id,
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
    result = baseline_forward_authority(observation)
    strategy_candidate = {
        **observation, "evidence_class": EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
        "strategy_validation_authority": (
            run_succeeded is True and critical_input_passed is True and approved_config_active is True
            and dependency_status == "MATCH" and git_tracked_worktree_clean is True
            and (safe_float(capital) or 0) > 0
        ),
    }
    result["strategy_validation_authority"] = walk_forward_period_has_strategy_validation_authority(strategy_candidate)
    return result


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

    reasons = production_identity_reasons(payload)
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
    elif eligibility_basis not in {EXPLICIT_DECISION_ELIGIBILITY_BASIS, "EXPLICIT_RUN_PURPOSE"}:
        reasons.append("BASELINE_ELIGIBILITY_BASIS_INVALID")
    if "strategy_validation_authority" in payload and not explicit_true(payload["strategy_validation_authority"]):
        reasons.append("STRATEGY_VALIDATION_AUTHORITY_DENIED")
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
    if (require_declared_eligibility or "baseline_forward_eligible" in payload) and not explicit_true(payload.get("baseline_forward_eligible")):
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
    return {field: payload.get(field, False if field in {"baseline_forward_eligible", "strategy_validation_authority"} else "") for field in BASELINE_SNAPSHOT_FIELDS}


def producer_baseline_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Fresh writers use their own code identity, never a supplied V1 label in V2."""
    supplied = dict(metadata or {})
    payload = {**supplied, **current_model_identity()}
    if payload["model_lineage"] == "V1":
        if supplied.get("validation_authority") in {"NONE", "SHADOW_ONLY"}:
            payload["validation_authority"] = supplied["validation_authority"]
        if supplied.get("model_lineage") not in {None, "V1"}:
            payload["validation_authority"] = "NONE"
        if payload["validation_authority"] != "PRODUCTION":
            payload.update(baseline_forward_eligible=False, strategy_validation_authority=False)
    if payload["model_lineage"] != "V1":
        payload.update(baseline_id="", baseline_started_at="", baseline_status="NOT_ESTABLISHED",
                       baseline_evidence_status="MODEL_LINEAGE_MISMATCH", baseline_forward_eligible=False,
                       strategy_validation_authority=False)
        payload["baseline_authority_reasons"] = production_identity_reasons(payload)
    return payload


def paired_snapshot_identity_matches(snapshots: list[Mapping[str, Any]]) -> bool:
    if len(snapshots) != 2:
        return False
    left, right = snapshots
    if evidence_cohort(left) != evidence_cohort(right):
        return False
    for field in (*IDENTITY_FIELDS, "run_id", "manifest_fingerprint", "analysis_mode", "run_purpose"):
        if not left.get(field) or left.get(field) != right.get(field):
            return False
    return left.get("baseline_started_at", "") == right.get("baseline_started_at", "")


def combined_baseline_snapshot_authority(
    payloads: Iterable[Mapping[str, Any]], *, run_purpose: Any,
) -> dict[str, Any]:
    """Revalidate a same-run pair; neither missing identity nor denial can grant."""
    snapshots = [dict(payload) for payload in payloads]
    selected = snapshots[0] if snapshots else {}
    metadata = {**identity_fields(selected), "run_id": selected.get("run_id", ""),
                "manifest_reference": selected.get("manifest_reference", ""),
                "manifest_fingerprint": selected.get("manifest_fingerprint", ""),
                "baseline_id": selected.get("baseline_id", ""),
                "baseline_forward_eligible": False, "strategy_validation_authority": False}
    if len(snapshots) != 2:
        return {**metadata, "baseline_evidence_status": "BASELINE_PAIRED_SNAPSHOT_REQUIRED"}
    if not paired_snapshot_identity_matches(snapshots) or any(
        normalize_run_purpose(p.get("run_purpose")) != normalize_run_purpose(run_purpose) for p in snapshots
    ):
        return {**metadata, "baseline_evidence_status": "BASELINE_PAIRED_IDENTITY_MISMATCH"}
    authorities = [baseline_forward_authority(p, require_declared_eligibility=True) for p in snapshots]
    eligible = all(p["baseline_forward_eligible"] for p in authorities)
    # Generic PIT authority is distinct from Baseline authority, but must be
    # explicitly declared on both originating observations.
    strategy = all(walk_forward_period_has_strategy_validation_authority({
        **p, "evidence_class": p.get("evidence_class") or EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value,
    }) for p in snapshots)
    return {**metadata, "baseline_forward_eligible": eligible,
            "strategy_validation_authority": strategy,
            "baseline_evidence_status": BASELINE_FORWARD_OBSERVATION_STATUS if eligible else next(
                p["baseline_evidence_status"] for p in authorities if not p["baseline_forward_eligible"])}


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
