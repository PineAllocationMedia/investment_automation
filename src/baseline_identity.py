from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

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
) -> dict[str, Any]:
    identity = load_baseline_identity(config_path)
    purpose = normalize_run_purpose(run_purpose)
    run_at = _parse_datetime(run_timestamp)
    started_at = _parse_datetime(identity.get("baseline_started_at"))
    numeric_capital = safe_float(capital)
    eligible = False
    if identity["baseline_id"] != VALIDATION_BASELINE_ID:
        evidence_status = "BASELINE_ID_MISMATCH"
    elif started_at is None:
        evidence_status = "PRE_BASELINE_PENDING_APPROVED_DEPLOYMENT"
    elif run_at is None:
        evidence_status = "INVALID_RUN_TIMESTAMP"
    elif run_at < started_at:
        evidence_status = "PRE_BASELINE_OBSERVATION"
    elif numeric_capital is not None and numeric_capital <= 0:
        evidence_status = "BASELINE_ZERO_CAPITAL_OBSERVATION"
    elif not purpose_is_genuine_decision(purpose):
        evidence_status = "BASELINE_NON_DECISION_OBSERVATION"
    else:
        evidence_status = "BASELINE_V1_FORWARD_OBSERVATION"
        eligible = True
    return {
        **identity,
        "run_purpose": purpose,
        "baseline_evidence_status": evidence_status,
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
