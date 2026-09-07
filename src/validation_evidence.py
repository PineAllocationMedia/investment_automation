from __future__ import annotations

from enum import Enum
from typing import Any, Iterable

from .utils import safe_float
from .model_identity import explicit_true, production_identity_reasons


VALIDATION_SCHEMA_VERSION = "2026-09-06-validation-identity-v4"
AUTO_TUNING_POLICY = "PROPOSAL_ONLY"
EXPLICIT_DECISION_ELIGIBILITY_BASIS = "EXPLICIT_DECISION_PURPOSE"
LEGACY_PARTIALLY_RECOVERABLE_BASIS = "LEGACY_PARTIALLY_RECOVERABLE"


class EvidenceClass(str, Enum):
    LIVE_FORWARD_EVIDENCE = "LIVE_FORWARD_EVIDENCE"
    POINT_IN_TIME_WALK_FORWARD = "POINT_IN_TIME_WALK_FORWARD"
    HISTORICAL_STRESS_SENSITIVITY = "HISTORICAL_STRESS_SENSITIVITY"
    MECHANICAL_DIAGNOSTIC = "MECHANICAL_DIAGNOSTIC"
    HEURISTIC_QUALITATIVE = "HEURISTIC_QUALITATIVE"


EVIDENCE_HIERARCHY = {
    EvidenceClass.LIVE_FORWARD_EVIDENCE.value: 1,
    EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value: 2,
    EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value: 3,
    EvidenceClass.MECHANICAL_DIAGNOSTIC.value: 4,
    EvidenceClass.HEURISTIC_QUALITATIVE.value: 5,
}


class EvidenceMaturity(str, Enum):
    INSUFFICIENT = "INSUFFICIENT"
    EARLY = "EARLY"
    DEVELOPING = "DEVELOPING"
    SUBSTANTIAL = "SUBSTANTIAL"


class RunPurpose(str, Enum):
    SCHEDULED_DECISION = "SCHEDULED_DECISION"
    MANUAL_DECISION = "MANUAL_DECISION"
    DIAGNOSTIC = "DIAGNOSTIC"
    DEVELOPMENT_TEST = "DEVELOPMENT_TEST"
    ZERO_CAPITAL_ANALYSIS = "ZERO_CAPITAL_ANALYSIS"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN_LEGACY = "UNKNOWN_LEGACY"


DECISION_RUN_PURPOSES = {
    RunPurpose.SCHEDULED_DECISION.value,
    RunPurpose.MANUAL_DECISION.value,
}


def normalize_run_purpose(value: Any) -> str:
    normalized = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    return normalized if normalized in {item.value for item in RunPurpose} else RunPurpose.UNKNOWN_LEGACY.value


def resolve_analysis_run_purpose(explicit: Any, *, capital: Any = None) -> str:
    if str(explicit or "").strip():
        return normalize_run_purpose(explicit)
    numeric_capital = safe_float(capital)
    if numeric_capital is not None and numeric_capital <= 0:
        return RunPurpose.ZERO_CAPITAL_ANALYSIS.value
    # An untagged interactive invocation may be a decision or a diagnostic.
    # Preserve that uncertainty instead of manufacturing forward evidence.
    return RunPurpose.UNKNOWN_LEGACY.value


def snapshot_run_purpose(payload: dict[str, Any] | None) -> str:
    payload = payload or {}
    explicit = payload.get("run_purpose")
    if str(explicit or "").strip():
        return normalize_run_purpose(explicit)
    command = str(payload.get("command") or "").strip().lower()
    if command in {"health-check", "model-audit", "full-audit", "walk-forward-backtest", "backtest"}:
        return RunPurpose.DIAGNOSTIC.value
    if command in {"maintenance", "scheduled-maintenance"}:
        return RunPurpose.MAINTENANCE.value
    if command in {"test", "development-test"}:
        return RunPurpose.DEVELOPMENT_TEST.value
    capital_value = payload.get("capital") if "capital" in payload else payload.get("monthly_contribution")
    capital = safe_float(capital_value)
    if capital is not None and capital <= 0:
        return RunPurpose.ZERO_CAPITAL_ANALYSIS.value
    return RunPurpose.UNKNOWN_LEGACY.value


def purpose_is_genuine_decision(value: Any) -> bool:
    return normalize_run_purpose(value) in DECISION_RUN_PURPOSES


def purpose_is_walk_forward_decision(value: Any) -> bool:
    return purpose_is_genuine_decision(value)


def walk_forward_period_evidence_class(
    run_purpose: Any,
    eligibility_basis: Any = "",
) -> str:
    purpose = normalize_run_purpose(run_purpose)
    basis = str(eligibility_basis or "").strip().upper()
    if purpose in DECISION_RUN_PURPOSES and basis != LEGACY_PARTIALLY_RECOVERABLE_BASIS:
        return EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value
    return EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value


def walk_forward_period_has_strategy_validation_authority(payload: dict[str, Any] | None) -> bool:
    payload = payload or {}
    if production_identity_reasons(payload, require_current_rules=False):
        return False
    purpose = normalize_run_purpose(payload.get("run_purpose"))
    basis = str(payload.get("eligibility_basis") or "").strip().upper()
    evidence_class = str(
        payload.get("evidence_class") or ""
    ).strip().upper()
    if purpose not in DECISION_RUN_PURPOSES:
        return False
    if basis != EXPLICIT_DECISION_ELIGIBILITY_BASIS:
        return False
    if evidence_class != EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value:
        return False
    return explicit_true(payload.get("strategy_validation_authority"))


def walk_forward_period_is_legacy_diagnostic(payload: dict[str, Any] | None) -> bool:
    payload = payload or {}
    purpose = normalize_run_purpose(payload.get("run_purpose"))
    basis = str(payload.get("eligibility_basis") or "").strip().upper()
    return purpose == RunPurpose.UNKNOWN_LEGACY.value and basis in {
        "",
        LEGACY_PARTIALLY_RECOVERABLE_BASIS,
    }


def evidence_maturity(sample_count: Any) -> str:
    count = max(0, int(safe_float(sample_count) or 0))
    if count < 4:
        return EvidenceMaturity.INSUFFICIENT.value
    if count < 6:
        return EvidenceMaturity.EARLY.value
    if count < 12:
        return EvidenceMaturity.DEVELOPING.value
    return EvidenceMaturity.SUBSTANTIAL.value


def strategy_validation_confidence(*, live_periods: Any = 0, walk_forward_periods: Any = 0) -> str:
    live_count = max(0, int(safe_float(live_periods) or 0))
    walk_count = max(0, int(safe_float(walk_forward_periods) or 0))
    return evidence_maturity(live_count + walk_count)


def source_confidence_from_score(score: Any) -> str:
    numeric = safe_float(score)
    if numeric is None:
        return "UNKNOWN"
    if numeric >= 80:
        return "HIGH"
    if numeric >= 60:
        return "MEDIUM"
    return "LOW"


def validation_confidence_dimensions(
    *,
    run_succeeded: bool,
    source_health_score: Any,
    current_version_observations: Any,
    walk_forward_periods: Any,
    live_periods: Any = 0,
) -> dict[str, Any]:
    walk_count = max(0, int(safe_float(walk_forward_periods) or 0))
    current_count = max(0, int(safe_float(current_version_observations) or 0))
    return {
        "run_execution_confidence": "HIGH" if run_succeeded else "LOW",
        "data_integrity_confidence": source_confidence_from_score(source_health_score),
        "source_confidence": source_confidence_from_score(source_health_score),
        "strategy_validation_confidence": strategy_validation_confidence(
            live_periods=live_periods,
            walk_forward_periods=walk_count,
        ),
        "walk_forward_confidence": evidence_maturity(walk_count),
        "current_version_evidence_maturity": evidence_maturity(current_count),
        "current_version_observation_count": current_count,
        "walk_forward_period_count": walk_count,
        "live_forward_period_count": max(0, int(safe_float(live_periods) or 0)),
    }


def combined_snapshot_purpose(payloads: Iterable[dict[str, Any] | None]) -> tuple[str, str]:
    purposes = {snapshot_run_purpose(payload) for payload in payloads if payload}
    if not purposes:
        return RunPurpose.UNKNOWN_LEGACY.value, "LEGACY_UNCERTAINTY"
    explicit = {purpose for purpose in purposes if purpose != RunPurpose.UNKNOWN_LEGACY.value}
    if len(explicit) == 1:
        purpose = next(iter(explicit))
        if RunPurpose.UNKNOWN_LEGACY.value in purposes:
            return purpose, "PARTIALLY_RECOVERABLE"
        return purpose, "EXPLICIT"
    if not explicit:
        return RunPurpose.UNKNOWN_LEGACY.value, "LEGACY_UNCERTAINTY"
    return RunPurpose.UNKNOWN_LEGACY.value, "PURPOSE_CONFLICT"
