import tempfile
import unittest
from pathlib import Path

from src.qualitative_moat_engine import (
    build_qualitative_moat_rows,
    qualitative_moat_markdown,
)
from src.utils import write_csv_records


class QualitativeMoatEngineTest(unittest.TestCase):
    def test_builds_continuous_source_based_text_for_allocated_ticker(self):
        with tempfile.TemporaryDirectory() as folder:
            report_dir = Path(folder) / "reports"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "MSFT_2026-04-21_MORNINGSTAR_STOCK_ANALYST_REPORT.txt").write_text(
                "Microsoft has a wide moat supported by switching costs and network effects. "
                "Its mission-critical software and recurring revenue support resilience in downturns. "
                "The company benefits from pricing power and price increases across cloud and software products.",
                encoding="utf-8",
            )

            rows = build_qualitative_moat_rows(
                {
                    "MSFT": {
                        "ticker": "MSFT",
                        "company_name": "Microsoft",
                        "add_eligibility_status": "ADD_ALLOWED",
                        "capital_allocation_score": 90,
                    }
                },
                [{"ticker": "MSFT", "amount": 100, "percentage": 0.2}],
                report_dir=report_dir,
                index_path=index_path,
            )

        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertEqual(rows[0]["source_status"], "LOCAL_RESEARCH_REPORT")
        self.assertIn("wide moat", rows[0]["moat_label"])
        self.assertIn("coûts de changement", rows[0]["competitive_advantage_themes"])
        self.assertIn("revenus récurrents", rows[0]["crisis_protection_themes"])
        self.assertIn("pouvoir de prix", rows[0]["pricing_power_themes"])
        self.assertGreaterEqual(rows[0]["qualitative_text"].count("."), 4)

    def test_includes_eligible_not_selected_ticker(self):
        with tempfile.TemporaryDirectory() as folder:
            report_dir = Path(folder) / "reports"
            report_dir.mkdir()
            index_path = Path(folder) / "research_index.csv"
            write_csv_records(index_path, [], ["ticker", "provider", "report_date", "file_name", "notes"])
            (report_dir / "INTU_2026-04-21_MORNINGSTAR_STOCK_ANALYST_REPORT.txt").write_text(
                "Intuit has a narrow moat from switching costs. Recurring revenue helps resilience. Pricing power is supported by sticky customers.",
                encoding="utf-8",
            )

            rows = build_qualitative_moat_rows(
                {
                    "INTU": {
                        "ticker": "INTU",
                        "company_name": "Intuit",
                        "add_eligibility_status": "ADD_ALLOWED_SMALL",
                        "capital_allocation_score": 70,
                    }
                },
                [],
                report_dir=report_dir,
                index_path=index_path,
            )

        self.assertEqual(rows[0]["target_status"], "ÉLIGIBLE_NON_RETENU")

    def test_missing_source_refuses_generic_text(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = build_qualitative_moat_rows(
                {
                    "GOOGL": {
                        "ticker": "GOOGL",
                        "company_name": "Alphabet",
                        "add_eligibility_status": "ADD_ALLOWED",
                        "capital_allocation_score": 80,
                    }
                },
                [{"ticker": "GOOGL", "amount": 50, "percentage": 0.1}],
                report_dir=Path(folder),
                index_path=Path(folder) / "research_index.csv",
            )

        self.assertEqual(rows[0]["source_status"], "SOURCE_MISSING")
        self.assertIn("n’invente", rows[0]["qualitative_text"])

    def test_markdown_uses_paragraphs_not_a_table(self):
        lines = qualitative_moat_markdown(
            [
                {
                    "ticker": "MSFT",
                    "ticker_display": "MSFT",
                    "target_status": "RECOMMANDÉ",
                    "qualitative_text": "Phrase une. Phrase deux. Phrase trois. Phrase quatre.",
                }
            ]
        )

        text = "\n".join(lines)
        self.assertIn("**MSFT — RECOMMANDÉ.**", text)
        self.assertNotIn("| ticker |", text)


if __name__ == "__main__":
    unittest.main()
