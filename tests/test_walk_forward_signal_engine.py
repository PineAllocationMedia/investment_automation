from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from src.mode_artifacts import mode_artifact_path
from src.walk_forward_signal_engine import compute_walk_forward_signal


class WalkForwardSignalEngineTests(unittest.TestCase):
    def test_absent_when_inventory_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signal = compute_walk_forward_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "WALK_FORWARD_ABSENT")
        self.assertIn("walk-forward-backtest", signal["command"])

    def test_stale_when_inventory_older_than_twenty_one_days(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = mode_artifact_path(Path(tmp) / "latest_walk_forward_inventory.csv", "high-cagr")
            path.write_text("mode,usable_for_walk_forward\nhigh-cagr,True\n", encoding="utf-8")
            old = time.time() - 22 * 86400
            os.utime(path, (old, old))

            signal = compute_walk_forward_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "WALK_FORWARD_STALE")

    def test_dormant_when_fewer_than_four_periods_simulated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = mode_artifact_path(Path(tmp) / "latest_walk_forward_inventory.csv", "high-cagr")
            inventory.write_text("mode,usable_for_walk_forward\nhigh-cagr,True\n", encoding="utf-8")
            summary = mode_artifact_path(Path(tmp) / "latest_walk_forward_summary.csv", "high-cagr")
            summary.write_text("mode,simulated_periods,regime_count\nhigh-cagr,3,1\n", encoding="utf-8")

            signal = compute_walk_forward_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "WALK_FORWARD_DORMANT")

    def test_early_when_four_to_seven_periods_and_one_regime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = mode_artifact_path(Path(tmp) / "latest_walk_forward_inventory.csv", "high-cagr")
            inventory.write_text("mode,usable_for_walk_forward\nhigh-cagr,True\n", encoding="utf-8")
            summary = mode_artifact_path(Path(tmp) / "latest_walk_forward_summary.csv", "high-cagr")
            summary.write_text("mode,simulated_periods,regime_count\nhigh-cagr,6,1\n", encoding="utf-8")

            signal = compute_walk_forward_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "WALK_FORWARD_EARLY")

    def test_healthy_when_eight_periods_and_two_regimes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = mode_artifact_path(Path(tmp) / "latest_walk_forward_inventory.csv", "high-cagr")
            inventory.write_text("mode,usable_for_walk_forward\nhigh-cagr,True\n", encoding="utf-8")
            summary = mode_artifact_path(Path(tmp) / "latest_walk_forward_summary.csv", "high-cagr")
            summary.write_text("mode,simulated_periods,regime_count\nhigh-cagr,8,2\n", encoding="utf-8")

            signal = compute_walk_forward_signal(tmp, "high-cagr")

        self.assertEqual(signal["status"], "WALK_FORWARD_HEALTHY")
        self.assertEqual(signal["command"], "")


if __name__ == "__main__":
    unittest.main()
