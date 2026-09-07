"""Model/evidence identity, independent of runtime paths and Git branch names."""
from __future__ import annotations

from typing import Any, Mapping

from .model_version import MODEL_RULES_VERSION

MODEL_LINEAGE = "V2"
MODEL_LINEAGES = {"V1", "V2"}
PRODUCTION = "PRODUCTION"
SHADOW_ONLY = "SHADOW_ONLY"
NONE = "NONE"
VALIDATION_AUTHORITIES = {PRODUCTION, SHADOW_ONLY, NONE}
IDENTITY_FIELDS = ("model_lineage", "model_rules_version", "validation_schema_version", "validation_authority")


def current_model_identity() -> dict[str, str]:
    from .validation_evidence import VALIDATION_SCHEMA_VERSION

    return {
        "model_lineage": MODEL_LINEAGE,
        "model_rules_version": MODEL_RULES_VERSION,
        "validation_schema_version": VALIDATION_SCHEMA_VERSION,
        "validation_authority": PRODUCTION if MODEL_LINEAGE == "V1" else NONE,
    }


def explicit_true(value: Any) -> bool:
    """Accept JSON booleans and their CSV representation; never infer permission."""
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def identity_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Historical projection: missing fields stay missing, never use producer defaults."""
    return {field: payload.get(field, "") for field in IDENTITY_FIELDS}


def evidence_cohort(payload: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(payload.get(field) or "").strip() for field in (*IDENTITY_FIELDS, "baseline_id"))


def production_identity_reasons(payload: Mapping[str, Any], *, require_current_rules: bool = True) -> list[str]:
    from .validation_evidence import VALIDATION_SCHEMA_VERSION

    # PR2 recognizes V1 production evidence only. V2 promotion is not implemented.
    expected = {
        "model_lineage": ("V1", "MODEL_LINEAGE"),
        "validation_authority": (PRODUCTION, "VALIDATION_AUTHORITY"),
        "model_rules_version": (MODEL_RULES_VERSION, "MODEL_RULES_VERSION"),
        "validation_schema_version": (VALIDATION_SCHEMA_VERSION, "VALIDATION_SCHEMA"),
    }
    reasons = []
    for field, (value, label) in expected.items():
        actual = payload.get(field)
        if not actual or not str(actual).strip():
            reasons.append(f"{label}_MISSING")
        elif field == "model_rules_version" and not require_current_rules:
            if not isinstance(actual, str) or actual.strip().lower() in {"unknown", "none", "null", "false", "true"}:
                reasons.append("MODEL_RULES_VERSION_INVALID")
            continue
        elif actual != value:
            reasons.append("VALIDATION_AUTHORITY_NOT_PRODUCTION" if field == "validation_authority" else f"{label}_MISMATCH")
    return reasons


def matches_current_cohort(payload: Mapping[str, Any], *, lineage: str, rules_version: str) -> bool:
    from .validation_evidence import VALIDATION_SCHEMA_VERSION

    return (lineage in MODEL_LINEAGES and payload.get("model_lineage") == lineage
            and bool(rules_version) and payload.get("model_rules_version") == rules_version
            and payload.get("validation_schema_version") == VALIDATION_SCHEMA_VERSION)


def production_audit_scope(metrics: Mapping[str, Any]) -> bool:
    """Aggregate counts also need explicit provenance; legacy totals cannot grant."""
    return not production_identity_reasons({
        "model_lineage": metrics.get("current_model_lineage"),
        "model_rules_version": metrics.get("current_model_rules_version"),
        "validation_schema_version": metrics.get("validation_schema_version"),
        "validation_authority": metrics.get("validation_authority"),
    }, require_current_rules=False)
