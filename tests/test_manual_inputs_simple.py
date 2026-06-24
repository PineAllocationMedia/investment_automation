import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.manual_inputs import load_friendly_manual_inputs, merge_manual_inputs, simple_row_to_manual


class ManualInputsSimpleTest(unittest.TestCase):
    def test_simple_row_maps_to_full_manual_fields(self):
        row = {
            "ticker": "MSFT",
            "roic_5y_avg": "25",
            "eps_growth_5y": "15",
            "eps_growth_estimated_3_5y": "14",
            "sector_cagr_estimated": "9",
            "forward_pe_manual": "30",
            "peg_manual": "1.8",
            "fair_value": "500",
            "current_price_manual": "480",
            "moat_clear": "oui",
            "margin_stable_or_expanding": "yes",
            "valuation_reasonable": "true",
            "forward_pe_growth_acceptable": "1",
            "management_quality_good": "TRUE",
            "balance_sheet_strong": "TRUE",
            "thesis_health": "INTACT",
            "main_risks": "",
            "manual_confidence_level": "HIGH",
            "notes": "test",
        }
        manual = simple_row_to_manual(row)
        self.assertEqual(manual["ticker"], "MSFT")
        self.assertTrue(manual["moat_clear"])
        self.assertTrue(manual["net_margin_stable_or_expanding"])
        self.assertTrue(manual["valuation_vs_5y_avg_ok"])
        self.assertEqual(manual["manual_confidence_level"], "HIGH")

    def test_simple_values_override_detailed_when_present(self):
        detailed = {"MSFT": {"ticker": "MSFT", "roic_5y_avg": 10, "notes": "old"}}
        simple = {"MSFT": {"ticker": "MSFT", "roic_5y_avg": 25, "notes": "new"}}
        merged = merge_manual_inputs(detailed, simple)
        self.assertEqual(merged["MSFT"]["roic_5y_avg"], 25)
        self.assertEqual(merged["MSFT"]["notes"], "new")

    def test_friendly_text_file_is_loaded(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "manual_inputs_friendly.txt"
            path.write_text(
                """
[MSFT]
roic_5y_avg = 25
moat_clear = oui
thesis_health = INTACT
manual_confidence_level = HIGH
""".strip(),
                encoding="utf-8",
            )
            loaded = load_friendly_manual_inputs(path)
            self.assertIn("MSFT", loaded)
            self.assertEqual(loaded["MSFT"]["roic_5y_avg"], 25)
            self.assertTrue(loaded["MSFT"]["moat_clear"])
            self.assertEqual(loaded["MSFT"]["manual_confidence_level"], "HIGH")


if __name__ == "__main__":
    unittest.main()
