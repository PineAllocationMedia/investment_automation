"""Lossless extraction tests for fictional common-stock dividend facts."""
from dataclasses import FrozenInstanceError
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from economic_facts.sec_archive import ArchiveError, SecArchive
from economic_facts.sec_common_stock_dividends import (
    CONCEPTS, DECLARED_CONCEPT, PAID_CONCEPT, extract_common_stock_dividends,
)
from tests.sec_common_stock_dividend_fixtures import (
    capture_dividends, dividend_raw, dividend_row, dividend_source,
)


class SecCommonStockDividendExtractionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = SecArchive(Path(temporary.name).resolve() / "archive")

    def extract(self, payload=None, *, raw=None):
        receipt = capture_dividends(self.archive, payload=payload, raw=raw)
        return extract_common_stock_dividends(self.archive.read_object(receipt), receipt)

    def test_extracts_exact_two_concepts_with_full_provenance(self):
        extraction = self.extract()
        self.assertEqual({row.concept for row in extraction.observations}, set(CONCEPTS))
        self.assertEqual(len(extraction.observations), 2)
        for row in extraction.observations:
            self.assertEqual(row.value, Decimal(0))
            self.assertEqual(row.unit, "USD/shares")
            self.assertEqual(row.start, "2024-01-01")
            self.assertEqual(row.end, "2024-12-31")
            self.assertEqual(row.fy, 2024)
            self.assertEqual(row.fp, "FY")
            self.assertEqual(row.form, "10-K")
            self.assertEqual(row.filed, "2025-02-01")
            self.assertEqual(row.accession, "0000000000-25-000001")
            self.assertEqual(row.frame, "CY2024")
            self.assertTrue(row.source_locator.startswith("/facts/us-gaap/"))
            self.assertIn("/sha256:", row.semantic_locator)
            self.assertEqual(len(row.observation_id), 64)
            self.assertEqual(len(row.semantic_id), 64)
            self.assertEqual(row.metadata_limitations, ())
            self.assertEqual(json.loads(row.row_json, parse_float=Decimal)["val"], 0)
        with self.assertRaises(FrozenInstanceError):
            extraction.observations = ()

    def test_missing_or_empty_concepts_are_explicitly_unavailable(self):
        for missing in (DECLARED_CONCEPT, PAID_CONCEPT):
            payload = dividend_source()
            del payload["facts"]["us-gaap"][missing]
            extraction = self.extract(payload)
            self.assertIn(missing + "_UNAVAILABLE", extraction.issues)
            self.assertEqual({row.concept for row in extraction.observations},
                             set(CONCEPTS) - {missing})
        payload = dividend_source(declared=[], paid=[])
        extraction = self.extract(payload)
        self.assertEqual(set(extraction.issues),
                         {concept + "_UNAVAILABLE" for concept in CONCEPTS})
        self.assertEqual(extraction.observations, ())

    def test_only_exact_standard_concepts_are_consumed(self):
        extras = {
            "Dividends": {"units": {"USD": [dividend_row(999)]}},
            "DividendsCommonStockCash": {"units": {"USD": [dividend_row(999)]}},
            "PaymentsOfDividendsCommonStock": {"units": {"USD": [dividend_row(999)]}},
            "IssuerExtensionDividendPerShare": {"units": {"USD/shares": [dividend_row(999)]}},
        }
        extraction = self.extract(dividend_source(extra_facts=extras))
        self.assertEqual(len(extraction.observations), 2)
        self.assertEqual({row.value for row in extraction.observations}, {Decimal(0)})

    def test_all_rows_units_and_unknown_context_are_preserved(self):
        declared = [dividend_row(0), dividend_row("bad"),
                    dividend_row(1, segment={"axis": "fictional"})]
        payload = dividend_source(declared=declared)
        payload["facts"]["us-gaap"][DECLARED_CONCEPT]["units"]["CAD/shares"] = [dividend_row(2)]
        extraction = self.extract(payload)
        rows = [row for row in extraction.observations if row.concept == DECLARED_CONCEPT]
        self.assertEqual(len(rows), 4)
        self.assertIn("INVALID_VALUE", next(row for row in rows if row.value is None).metadata_limitations)
        self.assertTrue(any("segment" in row.row_json for row in rows))
        self.assertEqual({row.unit for row in rows}, {"USD/shares", "CAD/shares"})

    def test_decimal_exactness_and_semantic_canonicalization(self):
        a = self.extract(dividend_source(declared=[dividend_row(0)]))
        b = self.extract(dividend_source(declared=[dividend_row(0.0)]))
        declared_a = next(row for row in a.observations if row.concept == DECLARED_CONCEPT)
        declared_b = next(row for row in b.observations if row.concept == DECLARED_CONCEPT)
        self.assertEqual(declared_a.value, Decimal(0))
        self.assertEqual(declared_b.value, Decimal("0.0"))
        self.assertEqual(declared_a.semantic_id, declared_b.semantic_id)
        precise = dividend_raw().replace(b'"val":0', b'"val":0.0000000000000000000000001', 1)
        row = next(item for item in self.extract(raw=precise).observations
                   if item.concept == DECLARED_CONCEPT)
        self.assertEqual(row.value, Decimal("0.0000000000000000000000001"))

    def test_row_order_preserves_semantics_but_exact_pointers_change_evidence(self):
        rows = [dividend_row(0), dividend_row(0, accn="0000000000-25-000002")]
        first = self.extract(dividend_source(declared=rows))
        second = self.extract(dividend_source(declared=list(reversed(rows))))
        self.assertEqual({row.semantic_id for row in first.observations},
                         {row.semantic_id for row in second.observations})
        self.assertNotEqual({row.observation_id for row in first.observations},
                            {row.observation_id for row in second.observations})

    def test_mapping_order_preserves_semantic_identity(self):
        first = self.extract()
        second = self.extract(raw=dividend_raw(reverse=True))
        self.assertEqual({row.semantic_id for row in first.observations},
                         {row.semantic_id for row in second.observations})
        self.assertNotEqual({row.observation_id for row in first.observations},
                            {row.observation_id for row in second.observations})

    def test_source_and_receipt_integrity_fail_closed(self):
        receipt = capture_dividends(self.archive)
        with self.assertRaises(ArchiveError):
            extract_common_stock_dividends(b"{}", receipt)
        wrong = dividend_source(cik=1)
        other = capture_dividends(self.archive, payload=wrong)
        with self.assertRaises(ArchiveError):
            extract_common_stock_dividends(self.archive.read_object(other), other)

    def test_malformed_structures_fail_instead_of_becoming_absence(self):
        for payload in ([], {"cik": 0, "facts": []},
                        {"cik": 0, "facts": {"us-gaap": []}},
                        {"cik": 0, "facts": {"us-gaap": {DECLARED_CONCEPT: []}}}):
            with self.subTest(payload=payload), self.assertRaises(ArchiveError):
                self.extract(payload if type(payload) is dict else None,
                             raw=json.dumps(payload).encode())


if __name__ == "__main__":
    unittest.main()
