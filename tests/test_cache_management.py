import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from src.cache_management_engine import reset_expired_market_circuit_breakers, run_cache_maintenance
from src.utils import load_json


class CacheManagementEngineTest(unittest.TestCase):
    def test_repair_safe_backfills_lkg_and_cleans_unusable_artifacts(self):
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            direct = cache / "MSFT.json"
            direct.write_text('{"ticker":"MSFT","source":"yfinance","current_price":100,"fetched_at":"2026-05-01T10:00:00"}', encoding="utf-8")
            stale = cache / "AAPL.json"
            stale.write_text('{"ticker":"AAPL","source":"stale_cache","current_price":90}', encoding="utf-8")
            lkg = cache / "last_known_good"
            lkg.mkdir()
            (lkg / "AAPL.json").write_text('{"ticker":"AAPL","source":"yfinance","current_price":91}', encoding="utf-8")
            unavailable = cache / "BROKEN.json"
            unavailable.write_text('{"ticker":"BROKEN","source":"unavailable"}', encoding="utf-8")
            corrupt = cache / "BAD.json"
            corrupt.write_text("{bad json", encoding="utf-8")
            temp = cache / ".MSFT.json.tmp"
            temp.write_text("tmp", encoding="utf-8")

            for path in [stale, unavailable, corrupt, temp]:
                self._make_old(path, hours=200)

            rows = run_cache_maintenance(cache, repair_safe=True)

            self.assertTrue((lkg / "MSFT.json").exists())
            self.assertFalse(stale.exists())
            self.assertFalse(unavailable.exists())
            self.assertFalse(corrupt.exists())
            self.assertFalse(temp.exists())
            self.assertTrue(any((cache / "quarantine").glob("BAD.json.*.corrupt")))
            summary = next(row for row in rows if row["category"] == "summary")
            self.assertGreaterEqual(int(summary["cleaned_count"]), 4)
            self.assertEqual(load_json(lkg / "MSFT.json")["last_known_good_source"], "yfinance")

    def test_usable_legacy_fallback_is_converted_to_lkg_before_cleanup(self):
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            stale = cache / "TSLA.json"
            stale.write_text('{"ticker":"TSLA","source":"stale_cache","current_price":200}', encoding="utf-8")
            self._make_old(stale, hours=240)

            rows = run_cache_maintenance(cache, repair_safe=True)

            self.assertFalse(stale.exists())
            self.assertTrue((cache / "last_known_good" / "TSLA.json").exists())
            legacy = next(row for row in rows if row["category"] == "legacy_fallback_cache")
            self.assertEqual(int(legacy["count"]), 1)
            self.assertEqual(int(legacy["cleaned_count"]), 1)

    def test_inspection_mode_does_not_modify_files(self):
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            unavailable = cache / "BROKEN.json"
            unavailable.write_text('{"ticker":"BROKEN","source":"unavailable"}', encoding="utf-8")
            self._make_old(unavailable, hours=240)

            rows = run_cache_maintenance(cache, repair_safe=False)

            self.assertTrue(unavailable.exists())
            unavailable_row = next(row for row in rows if row["category"] == "unavailable_cache")
            self.assertEqual(int(unavailable_row["cleaned_count"]), 0)

    def test_reset_expired_market_circuit_breaker_preserves_price_cache(self):
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            old_failure = (datetime.now() - timedelta(seconds=600)).isoformat(timespec="seconds")
            path = cache / "MSFT.json"
            path.write_text(
                (
                    '{"ticker":"MSFT","source":"yfinance","current_price":100,'
                    '"market_data_circuit_breaker_open":true,'
                    '"market_data_warning_flags":["CIRCUIT_OPEN","FETCH_FAILED"],'
                    f'"market_data_fetch_attempted_at":"{old_failure}",'
                    '"market_data_last_error":"Coupe-circuit données de marché actif."}'
                ),
                encoding="utf-8",
            )

            row = reset_expired_market_circuit_breakers(cache, cooldown_seconds=180)
            payload = load_json(path)

            self.assertEqual(int(row["cleaned_count"]), 1)
            self.assertEqual(payload["current_price"], 100)
            self.assertFalse(payload["market_data_circuit_breaker_open"])
            self.assertNotIn("CIRCUIT_OPEN", payload["market_data_warning_flags"])
            self.assertEqual(payload["failure_count"], 0)

    def test_reset_expired_market_circuit_breaker_keeps_recent_cooldown(self):
        with TemporaryDirectory() as directory:
            cache = Path(directory)
            recent_failure = (datetime.now() - timedelta(seconds=30)).isoformat(timespec="seconds")
            path = cache / "AAPL.json"
            path.write_text(
                (
                    '{"ticker":"AAPL","source":"yfinance","current_price":200,'
                    '"market_data_circuit_breaker_open":true,'
                    '"market_data_warning_flags":["CIRCUIT_OPEN"],'
                    f'"market_data_fetch_attempted_at":"{recent_failure}"'
                    "}"
                ),
                encoding="utf-8",
            )

            row = reset_expired_market_circuit_breakers(cache, cooldown_seconds=180)
            payload = load_json(path)

            self.assertEqual(int(row["cleaned_count"]), 0)
            self.assertTrue(payload["market_data_circuit_breaker_open"])
            self.assertIn("CIRCUIT_OPEN", payload["market_data_warning_flags"])

    def _make_old(self, path: Path, *, hours: int) -> None:
        old_time = path.stat().st_mtime - hours * 3600
        os.utime(path, (old_time, old_time))


if __name__ == "__main__":
    unittest.main()
