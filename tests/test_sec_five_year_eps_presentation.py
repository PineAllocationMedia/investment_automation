"""Tests for the finite PR5C five-year SEC presentation extractor."""
from dataclasses import fields
from decimal import Decimal
from pathlib import Path
import inspect
import tempfile
import unittest

from economic_facts import sec_five_year_eps_presentation as presentation
from economic_facts.sec_filing_archive import SecFilingArchive
from tests.sec_filing_document_inventory_fixtures import embedded_document, filing_inventory
from tests.sec_five_year_eps_presentation_fixtures import five_year_table
from tests.sec_original_filing_fixtures import ACCESSION, CIK


class SecFiveYearEPSPresentationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = SecFilingArchive(Path(temporary.name).resolve() / "filings")

    def capture(self, *tables, form="10-K", captured_at="2026-02-20T12:00:00Z",
                extra=""):
        html = ("<!doctype html><html><head><title>Annual Report</title></head><body>"
                + extra + "".join(tables) + "</body></html>").encode()
        raw = filing_inventory(
            cik=CIK, accession=ACCESSION, form=form,
            documents=(embedded_document(
                document_type=form, sequence="1", filename="annual.htm",
                description="Fictional annual report", payload=html),))
        return self.archive._capture_live(
            raw, cik=CIK, accession=ACCESSION, captured_at=captured_at)

    def extract(self, receipt):
        return presentation.extract_sec_five_year_eps_presentation(
            self.archive,
            presentation.SecFiveYearEPSPresentationRequest(receipt.receipt_id),
        )

    def test_exact_public_api_and_positive_realistic_table(self):
        self.assertEqual(tuple(inspect.signature(
            presentation.extract_sec_five_year_eps_presentation).parameters),
            ("filing_archive", "request"))
        self.assertEqual(tuple(field.name for field in fields(
            presentation.SecFiveYearEPSPresentationRequest)),
            ("filing_receipt_id",))
        result = self.extract(self.capture(five_year_table()))
        self.assertEqual(result.status, presentation.PresentationStatus.
                         CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION)
        self.assertEqual(len(result.values), 5)
        self.assertEqual([item.period_end for item in result.values], [
            "2024-12-31", "2023-12-31", "2022-12-31", "2021-12-31", "2020-12-31"])
        self.assertEqual([item.value for item in result.values],
                         [Decimal("6"), Decimal("5"), Decimal("4"),
                          Decimal("3"), Decimal("2")])
        self.assertIsNotNone(result.exact_table_html)
        self.assertRegex(result.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(result.evidence_id, r"^[0-9a-f]{64}$")

    def test_missing_six_and_duplicate_periods_fail_closed(self):
        cases = (
            five_year_table(years=(2024, 2023, 2022, 2021)),
            five_year_table(values={2019: 1, 2020: 2, 2021: 3, 2022: 4,
                                    2023: 5, 2024: 6},
                            years=(2024, 2023, 2022, 2021, 2020, 2019)),
            five_year_table(years=(2024, 2024, 2022, 2021, 2020)),
        )
        for table in cases:
            with self.subTest(table=table):
                result = self.extract(self.capture(table))
                self.assertIsNot(result.status, presentation.PresentationStatus.
                                 CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION)

    def test_basic_adjusted_and_ambiguous_rows_are_rejected(self):
        basic = five_year_table(row_label="Basic earnings per share")
        adjusted = five_year_table(row_label="Adjusted diluted earnings per share")
        ambiguous = five_year_table().replace(
            "</tbody>",
            "<tr><th>Diluted net income per common share</th>"
            "<td>6</td><td>5</td><td>4</td><td>3</td><td>2</td></tr></tbody>")
        expected = (
            (basic, presentation.PresentationIssue.BASIC_EPS_ONLY),
            (adjusted, presentation.PresentationIssue.ADJUSTED_OR_NON_GAAP_EPS_ROW),
            (ambiguous, presentation.PresentationIssue.AMBIGUOUS_DILUTED_EPS_ROW),
        )
        for table, issue in expected:
            with self.subTest(issue=issue):
                result = self.extract(self.capture(table))
                self.assertIn(issue, result.issues)
                self.assertNotEqual(result.status, presentation.PresentationStatus.
                                    CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION)

    def test_multiple_presentations_conflict_without_winner(self):
        result = self.extract(self.capture(five_year_table(), five_year_table()))
        self.assertEqual(result.status, presentation.PresentationStatus.SOURCE_CONFLICT)
        self.assertIn(presentation.PresentationIssue.MULTIPLE_CANDIDATE_PRESENTATIONS,
                      result.issues)

    def test_wrong_heading_invalid_decimal_and_unsupported_form(self):
        cases = (
            (self.capture(five_year_table(heading="Fiscal Years")),
             presentation.PresentationIssue.PERIOD_LABEL_UNSUPPORTED),
            (self.capture(five_year_table().replace("<td>4</td>", "<td>4.0x</td>")),
             presentation.PresentationIssue.INVALID_EXACT_DECIMAL),
            (self.capture(five_year_table(), form="10-Q"),
             presentation.PresentationIssue.UNSUPPORTED_FILING_FORM),
        )
        for receipt, issue in cases:
            with self.subTest(issue=issue):
                self.assertIn(issue, self.extract(receipt).issues)

    def test_high_precision_negative_zero_and_signed_zero_are_exact_decimals(self):
        values = {
            2024: Decimal("123.45678901234567890123456789"),
            2023: Decimal("0"),
            2022: Decimal("-4.25"),
            2021: Decimal("-0"),
            2020: Decimal("2.0000000000000000001"),
        }
        result = self.extract(self.capture(five_year_table(values=values)))
        self.assertEqual(result.status, presentation.PresentationStatus.
                         CAPTURED_FIVE_YEAR_DILUTED_EPS_PRESENTATION)
        self.assertEqual(tuple(item.value for item in result.values),
                         tuple(values[year] for year in sorted(values, reverse=True)))
        self.assertTrue(result.values[3].value.is_signed())

    def test_equivalent_recapture_preserves_semantics_but_changes_evidence(self):
        raw = five_year_table()
        first = self.extract(self.capture(raw, captured_at="2026-02-20T12:00:00Z"))
        second = self.extract(self.capture(raw, captured_at="2026-02-21T12:00:00Z"))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_request_and_archive_types_fail_closed(self):
        for receipt_id in (None, True, "", "A" * 64, "0" * 63):
            with self.subTest(receipt_id=receipt_id), self.assertRaises(
                    presentation.SecFiveYearEPSPresentationError):
                presentation.SecFiveYearEPSPresentationRequest(receipt_id)
        request = presentation.SecFiveYearEPSPresentationRequest("0" * 64)
        with self.assertRaises(presentation.SecFiveYearEPSPresentationError):
            presentation.extract_sec_five_year_eps_presentation(object(), request)


if __name__ == "__main__":
    unittest.main()
