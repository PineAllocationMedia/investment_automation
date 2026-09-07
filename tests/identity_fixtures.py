"""Explicit synthetic V1 evidence; never used by production readers or writers."""
from src.model_version import MODEL_RULES_VERSION
from src.validation_evidence import VALIDATION_SCHEMA_VERSION


def production_identity():
    return {"model_lineage": "V1", "model_rules_version": MODEL_RULES_VERSION,
            "validation_schema_version": VALIDATION_SCHEMA_VERSION,
            "validation_authority": "PRODUCTION", "strategy_validation_authority": True,
            "eligibility_basis": "EXPLICIT_DECISION_PURPOSE"}


def production_observation(**changes):
    return {**production_identity(), "baseline_id": "VALIDATION_BASELINE_V1",
            "baseline_started_at": "2026-01-01T00:00:00", "baseline_status": "ACTIVE",
            "run_timestamp": "2026-09-01T12:00:00", "analysis_date": "2026-09-01",
            "run_purpose": "MANUAL_DECISION", "capital": 1000,
            "run_succeeded": True, "critical_input_passed": True,
            "approved_config_active": True, "dependency_status": "MATCH",
            "git_tracked_worktree_clean": True, "baseline_forward_eligible": True,
            "run_id": "fixture-run", "analysis_mode": "high-cagr",
            "manifest_fingerprint": "fixture-manifest", "manifest_reference": "fixture.json",
            "evidence_class": "POINT_IN_TIME_WALK_FORWARD", **changes}
