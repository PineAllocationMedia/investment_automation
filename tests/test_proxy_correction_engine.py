import tempfile
import unittest
from pathlib import Path

from src.proxy_correction_engine import (
    apply_proxy_correction,
    build_proxy_correction_audit,
    create_proxy_corrections_template,
    load_proxy_corrections,
)


class ProxyCorrectionEngineTest(unittest.TestCase):
    def test_template_is_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_corrections.yaml"
            create_proxy_corrections_template(path)
            state = load_proxy_corrections(path)

        self.assertFalse(state["enabled"])
        self.assertEqual(state["active_corrections"], {})

    def test_valid_active_numeric_correction_can_be_applied(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_corrections.yaml"
            path.write_text(
                """
version: 1
enabled: true
max_factor_change: 0.25
corrections:
  roic_5y_avg:
    status: ACTIVE
    factor: 1.12
    confidence: HIGH
    sample_count: 8
    last_updated: 2026-06-25
""",
                encoding="utf-8",
            )
            state = load_proxy_corrections(path)

        value, metadata = apply_proxy_correction("roic_5y_avg", 20, state)

        self.assertEqual(value, 22.4)
        self.assertEqual(metadata["factor"], 1.12)
        self.assertIn("roic_5y_avg", state["active_corrections"])

    def test_extreme_factor_is_rejected_instead_of_clamped_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_corrections.yaml"
            path.write_text(
                """
version: 1
enabled: true
max_factor_change: 0.25
corrections:
  fair_value:
    status: ACTIVE
    factor: 1.60
    confidence: HIGH
    sample_count: 12
""",
                encoding="utf-8",
            )
            state = load_proxy_corrections(path)

        value, metadata = apply_proxy_correction("fair_value", 100, state)

        self.assertEqual(value, 100)
        self.assertIsNone(metadata)
        self.assertEqual(state["active_corrections"], {})
        self.assertTrue(state["warnings"])

    def test_boolean_field_cannot_receive_multiplicative_correction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proxy_corrections.yaml"
            path.write_text(
                """
version: 1
enabled: true
max_factor_change: 0.25
corrections:
  moat_clear:
    status: ACTIVE
    factor: 1.10
    confidence: HIGH
    sample_count: 10
""",
                encoding="utf-8",
            )
            state = load_proxy_corrections(path)

        value, metadata = apply_proxy_correction("moat_clear", True, state)

        self.assertTrue(value)
        self.assertIsNone(metadata)
        self.assertEqual(state["active_corrections"], {})

    def test_proxy_correction_audit_marks_supported_active_correction_ok(self):
        state = {
            "enabled": True,
            "max_factor_change": 0.25,
            "active_corrections": {
                "roic_5y_avg": {
                    "factor": 1.12,
                    "confidence": "HIGH",
                    "sample_count": 8,
                    "last_updated": "2026-06-25",
                }
            },
            "warnings": [],
        }

        rows = build_proxy_correction_audit(
            state,
            [
                {
                    "field": "roic_5y_avg",
                    "status": "BIAS_CANDIDATE_SAFE_SIGNAL",
                    "confidence": "HIGH",
                    "usable_sample_count": 8,
                    "proxy_direction": "PROXY_TOO_LOW",
                    "suggested_factor": 1.11,
                }
            ],
        )

        self.assertEqual(rows[0]["status"], "ACTIVE_OK")
        self.assertEqual(rows[0]["risk_level"], "LOW")

    def test_proxy_correction_audit_flags_conflicting_fresh_evidence(self):
        state = {
            "enabled": True,
            "max_factor_change": 0.25,
            "active_corrections": {
                "roic_5y_avg": {
                    "factor": 1.12,
                    "confidence": "HIGH",
                    "sample_count": 8,
                    "last_updated": "2026-06-25",
                }
            },
            "warnings": [],
        }

        rows = build_proxy_correction_audit(
            state,
            [
                {
                    "field": "roic_5y_avg",
                    "status": "BIAS_CANDIDATE_SAFE_SIGNAL",
                    "confidence": "HIGH",
                    "usable_sample_count": 8,
                    "proxy_direction": "PROXY_TOO_HIGH",
                    "suggested_factor": 0.92,
                }
            ],
        )

        self.assertEqual(rows[0]["status"], "REVIEW_CONFLICTING_EVIDENCE")
        self.assertEqual(rows[0]["risk_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
