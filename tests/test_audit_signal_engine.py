from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from src.audit_signal_engine import (
    FULL_AUDIT_STALE_DAYS,
    MODEL_AUDIT_STALE_DAYS,
    compute_full_audit_signal,
    compute_model_audit_signal,
)
from src.mode_artifacts import mode_artifact_path


class AuditSignalEngineTest(unittest.TestCase):
    def test_full_audit_absent_returns_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signal = compute_full_audit_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "FULL_AUDIT_ABSENT")
        self.assertIn("full-audit", signal["command"])
        self.assertIn("high-cagr", signal["message"])

    def test_full_audit_healthy_uses_mode_specific_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            path = mode_artifact_path(reports_dir / "latest_full_audit_summary.csv", "high-cagr")
            path.write_text("section,metric,status,value\nRésumé,Santé,OK,90\n", encoding="utf-8")

            signal = compute_full_audit_signal(reports_dir, "high-cagr")

        self.assertEqual(signal["status"], "FULL_AUDIT_HEALTHY")
        self.assertEqual(signal["command"], "")

    def test_model_audit_stale_returns_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            path = mode_artifact_path(reports_dir / "latest_model_audit.csv", "high-cagr")
            path.write_text("section,metric,status,value\nRésumé,Santé,OK,90\n", encoding="utf-8")
            old_time = time.time() - ((MODEL_AUDIT_STALE_DAYS + 2) * 86400)
            os.utime(path, (old_time, old_time))

            signal = compute_model_audit_signal(reports_dir, "high-cagr")

        self.assertEqual(signal["status"], "MODEL_AUDIT_STALE")
        self.assertIn("model-audit", signal["command"])

    def test_full_audit_stale_returns_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports_dir = Path(tmp)
            path = reports_dir / "latest_full_audit_summary.csv"
            path.write_text("section,metric,status,value\nRésumé,Santé,OK,90\n", encoding="utf-8")
            old_time = time.time() - ((FULL_AUDIT_STALE_DAYS + 2) * 86400)
            os.utime(path, (old_time, old_time))

            signal = compute_full_audit_signal(reports_dir, "high-cagr")

        self.assertEqual(signal["status"], "FULL_AUDIT_STALE")
        self.assertIn("full-audit", signal["command"])


if __name__ == "__main__":
    unittest.main()
