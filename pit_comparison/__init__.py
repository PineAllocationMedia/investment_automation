"""Diagnostic PIT comparisons. Importing this package never imports a model."""

PIT_BUNDLE_SCHEMA_VERSION = "pit-bundle-v2"
PIT_INPUT_CONTRACT_VERSION = "decision-inputs-v2"
PIT_COMPARISON_SCHEMA_VERSION = "pit-comparison-v2"
PIT_ADAPTER_VERSION = "allocation-room-v7-adapter-v1"
CONTAINMENT_LEVEL = "APPLICATION_GUARDED"
AUTHORITY = {
    "comparison_mode": "RETROSPECTIVE_PIT",
    "run_purpose": "DIAGNOSTIC",
    "validation_authority": "NONE",
    "strategy_validation_authority": False,
    "baseline_forward_eligible": False,
    "genuine_forward_evidence": False,
}

PIT_EXPECTED_RETURN_INPUT_CONTRACT_VERSION = "pit-expected-return-inputs-v1"
PIT_EXPECTED_RETURN_DIAGNOSTIC_ADAPTER_VERSION = "pit-expected-return-diagnostic-adapter-v1"
PIT_EXPECTED_RETURN_DIAGNOSTIC_SCHEMA_VERSION = "pit-expected-return-diagnostic-v1"
