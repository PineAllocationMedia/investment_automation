from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.ticker_memory_engine import (
    apply_ticker_memory_to_exposure_map,
    apply_ticker_memory_to_sector_map,
    build_ticker_memory_rows,
    load_ticker_memory,
    update_ticker_memory,
)


class TickerMemoryEngineTests(unittest.TestCase):
    def test_memory_fills_only_missing_sector_and_exposure(self):
        memory = {
            "ABC.TO": {
                "ticker": "ABC.TO",
                "sector": "Industrial Automation",
                "region": "Canada",
                "currency": "CAD",
                "factor_exposure": "industrial; automation",
            }
        }

        sectors = apply_ticker_memory_to_sector_map({"ABC.TO": "Unknown", "MSFT": "Cloud Computing"}, ["ABC.TO", "MSFT"], memory)
        exposures = apply_ticker_memory_to_exposure_map(
            {"ABC.TO": {"region": "Unknown", "currency": "Unknown", "factor_exposure": []}},
            ["ABC.TO"],
            memory,
        )

        self.assertEqual(sectors["ABC.TO"], "Industrial Automation")
        self.assertEqual(sectors["MSFT"], "Cloud Computing")
        self.assertEqual(exposures["ABC.TO"]["region"], "Canada")
        self.assertEqual(exposures["ABC.TO"]["currency"], "CAD")
        self.assertEqual(exposures["ABC.TO"]["factor_exposure"], ["industrial", "automation"])

    def test_build_rows_marks_low_coverage_without_overwriting_useful_previous_fields(self):
        rows = build_ticker_memory_rows(
            {
                "MARKET_SCANNER": {
                    "XYZ.TO": {
                        "ticker_display": "XYZ.TO*",
                        "sector": "Unknown",
                        "region": "Unknown",
                        "currency": "CAD",
                        "ticker_validation_status": "OK",
                        "ticker_coverage_status": "LOW_FREE_DATA_COVERAGE",
                        "free_data_coverage_score": 0.4,
                        "ticker_issue_reasons": ["LOW_FREE_DATA_COVERAGE"],
                    }
                }
            },
            existing_memory={"XYZ.TO": {"ticker": "XYZ.TO", "sector": "Clean Power", "region": "Canada"}},
            date="2026-05-30",
        )

        row = rows[0]
        self.assertEqual(row["ticker_memory_status"], "LOW_FREE_COVERAGE")
        self.assertEqual(row["sector"], "Clean Power")
        self.assertIn("BNCD", row["ticker_memory_action"])

    def test_update_and_load_memory_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ticker_memory.csv"
            rows = build_ticker_memory_rows(
                {
                    "CORE_PORTFOLIO": {
                        "MSFT": {
                            "ticker": "MSFT",
                            "ticker_display": "MSFT",
                            "long_name": "Microsoft Corporation",
                            "sector": "Cloud Computing",
                            "region": "United States",
                            "currency": "USD",
                            "ticker_validation_status": "OK",
                            "ticker_coverage_status": "OK",
                            "free_data_coverage_score": 0.9,
                        }
                    }
                },
                date="2026-05-30",
            )
            update_ticker_memory(path, rows)
            loaded = load_ticker_memory(path)

        self.assertIn("MSFT", loaded)
        self.assertEqual(loaded["MSFT"]["sector"], "Cloud Computing")
        self.assertEqual(loaded["MSFT"]["ticker_memory_status"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
