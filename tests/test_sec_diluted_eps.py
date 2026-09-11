from dataclasses import FrozenInstanceError
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from economic_facts.sec_archive import (ACQUISITION_CONTRACT_VERSION, ArchiveError, CaptureReceipt,
                                        RECEIPT_SCHEMA_VERSION, SOURCE_KIND, SecArchive, digest, endpoint_for)
from economic_facts.sec_diluted_eps import (assess_candidate, extract_diluted_eps, inspect_archive)
from tests.sec_filing_fixtures import CIK, T1, T2, amendment, raw, row, source


def extract(payload=None, *, content=None):
    content = raw(payload) if content is None else content
    receipt = CaptureReceipt(RECEIPT_SCHEMA_VERSION, SOURCE_KIND, CIK, endpoint_for(CIK),
                             digest(content), len(content), T2, "fixture:source", ACQUISITION_CONTRACT_VERSION)
    return extract_diluted_eps(content, receipt)


class SecDilutedEPSTests(unittest.TestCase):
    def inspect(self, payload):
        with tempfile.TemporaryDirectory() as temporary:
            archive = SecArchive(Path(temporary).resolve() / "archive")
            archive.capture(raw(payload), cik=CIK, captured_at=T2, source_locator="fixture:source")
            return inspect_archive(archive, cik=CIK, cutoff=T2)

    def test_five_positive_annual_candidates(self):
        result = extract()
        self.assertEqual(len(result.observations), 5)
        self.assertEqual({r.end for r in result.observations}, {f"{year}-12-31" for year in range(2020, 2025)})
        for observation in result.observations:
            assessment = assess_candidate(observation)
            self.assertEqual(assessment.status, "ANNUAL_DILUTED_EPS_CANDIDATE")
            self.assertTrue(assessment.qualification_blockers)
        self.assertEqual(self.inspect(source()).status, "UPSTREAM_EVIDENCE_ONLY")

    def test_only_exact_namespace_concept_no_basic_income_or_estimate_fallback(self):
        substitutes = ("EarningsPerShareBasic", "NetIncomeLoss", "WeightedAverageNumberOfDilutedSharesOutstanding",
                       "trailingEps", "forwardEps", "AdjustedEarningsPerShare")
        for concept in substitutes:
            payload = source()
            facts = payload["facts"]["us-gaap"]
            facts[concept] = facts.pop("EarningsPerShareDiluted")
            with self.subTest(concept=concept):
                result = extract(payload)
                self.assertEqual(result.observations, ())
                self.assertIn("DILUTED_EPS_UNAVAILABLE", result.issues)
        payload = source()
        payload["facts"]["ifrs-full"] = payload["facts"].pop("us-gaap")
        self.assertEqual(extract(payload).observations, ())

    def test_preserves_all_required_metadata(self):
        original = row()
        observation = extract(source([original])).observations[0]
        for key in ("start", "end", "fy", "fp", "form", "filed", "accn", "frame"):
            self.assertEqual(getattr(observation, key), original[key])
        self.assertEqual(observation.cik, CIK)
        self.assertEqual(observation.unit, "USD/shares")
        self.assertEqual(observation.namespace, "us-gaap")
        self.assertEqual(observation.concept, "EarningsPerShareDiluted")
        self.assertEqual(observation.candidate_accounting_basis, "US_GAAP")
        self.assertTrue(observation.source_object_hash)
        self.assertTrue(observation.capture_receipt_id)

    def test_source_pointer_locates_exact_row_with_escaped_unit(self):
        payload = source(units={"USD/shares": [row()], "odd~/unit": [row(value=3)]})
        for observation in extract(payload).observations:
            value = payload
            for token in observation.source_locator.split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if type(value) is list else value[token]
            self.assertEqual(Decimal(str(value["val"])), observation.value)
            self.assertTrue(observation.semantic_locator.endswith(observation.semantic_id))

    def test_absent_frame_stays_none(self):
        original = row()
        del original["frame"]
        observation = extract(source([original])).observations[0]
        self.assertIsNone(observation.frame)
        self.assertNotIn("MISSING_FRAME", observation.metadata_limitations)

    def test_missing_critical_metadata_is_explicit(self):
        for field in ("accn", "start", "end", "fy", "fp", "form", "filed", "val"):
            original = row()
            del original[field]
            observation = extract(source([original])).observations[0]
            with self.subTest(field=field):
                self.assertIsNone(getattr(observation, "value" if field == "val" else field))
                reason = "MISSING_VALUE" if field == "val" else "MISSING_" + field.upper()
                self.assertIn(reason, assess_candidate(observation).reasons)

    def test_unknown_extra_context_retained_without_qualification(self):
        observation = extract(source([row(share_class="FALSE_CLASS", security_id="FALSE_SECURITY",
                                           segment={"axis": "fictional-axis"})])).observations[0]
        self.assertIn("FALSE_CLASS", observation.row_json)
        self.assertFalse(hasattr(observation, "security_id"))
        self.assertFalse(hasattr(observation, "share_class"))
        self.assertIn("SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED", assess_candidate(observation).qualification_blockers)

    def test_amendment_preserved_with_original_and_competing_value(self):
        payload = source([row(), amendment()])
        result = self.inspect(payload)
        observations = result.extractions[0].observations
        self.assertEqual({r.form for r in observations}, {"10-K", "10-K/A"})
        self.assertEqual({r.accn for r in observations}, {row()["accn"], amendment()["accn"]})
        self.assertEqual({r.value for r in observations}, {Decimal("2"), Decimal("1.75")})
        self.assertIn("MULTIPLE_FILING_VERSIONS_UNRESOLVED", {r.kind for r in result.ambiguities})
        self.assertIn("COMPETING_PERIOD_VALUES_UNRESOLVED", {r.kind for r in result.ambiguities})

    def test_conflicting_same_claim_is_collision(self):
        result = self.inspect(source([row(value=2), row(value=3)]))
        self.assertIn("SEMANTIC_IDENTITY_COLLISION", {r.kind for r in result.ambiguities})

    def test_duplicate_rows_visible_but_not_conflicting(self):
        result = self.inspect(source([row(), row()]))
        observations = result.extractions[0].observations
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0].semantic_id, observations[1].semantic_id)
        self.assertNotEqual(observations[0].observation_id, observations[1].observation_id)
        self.assertEqual(result.ambiguities, ())

    def test_multiple_units_not_selected_or_converted(self):
        result = self.inspect(source(units={"USD/shares": [row()], "CAD/shares": [row(value=3)]}))
        self.assertEqual({r.unit for r in result.extractions[0].observations}, {"USD/shares", "CAD/shares"})
        self.assertIn("MULTIPLE_UNITS_UNRESOLVED", {r.kind for r in result.ambiguities})

    def test_unknown_unit_preserved_with_limitation(self):
        for unit in ("", "shares", "USD", "USD/share"):
            observation = extract(source(units={unit: [row()]})).observations[0]
            self.assertEqual(observation.unit, unit)
            self.assertIn("UNSUPPORTED_OR_MISSING_UNIT", observation.metadata_limitations)

    def test_comparative_prior_period_retains_later_vintage(self):
        original = row(2023, 1.6, fy=2025, filed="2026-02-01", accn="0000000000-26-000003")
        observation = extract(source([original])).observations[0]
        self.assertEqual(observation.end, "2023-12-31")
        self.assertEqual(observation.fy, 2025)
        self.assertEqual(observation.filed, "2026-02-01")
        self.assertEqual(observation.accn, "0000000000-26-000003")

    def test_inclusive_365_and_366_days(self):
        for year, expected in ((2023, 365), (2024, 366)):
            assessment = assess_candidate(extract(source([row(year)])).observations[0])
            self.assertEqual(assessment.inclusive_duration_days, expected)
            self.assertTrue(assessment.supported_annual_period)

    def test_week_calendars_and_stubs_preserved_unsupported(self):
        for start, end, expected in (("2023-01-01", "2023-12-30", 364),
                                     ("2023-01-01", "2024-01-06", 371),
                                     ("2023-07-01", "2023-12-31", 184)):
            observation = extract(source([row(start=start, end=end)])).observations[0]
            self.assertEqual((observation.start, observation.end), (start, end))
            assessment = assess_candidate(observation)
            self.assertEqual(assessment.inclusive_duration_days, expected)
            self.assertIn("UNSUPPORTED_BY_CURRENT_PR4B1_PERIOD_CONTRACT", assessment.reasons)

    def test_calendar_changes_remain_unresolved_source_evidence(self):
        result = self.inspect(source([row(2023), row(2024, start="2024-01-01", end="2024-06-30")]))
        self.assertEqual(len(result.assessments), 2)
        self.assertIn("COMPARABLE_SERIES_NOT_RESOLVED", result.qualification_blockers)

    def test_zero_and_negative_eps_preserved(self):
        for value in (0, -2):
            observation = extract(source([row(value=value)])).observations[0]
            self.assertEqual(observation.value, Decimal(value))
            self.assertIn("NOT_USABLE_BY_CURRENT_POSITIVE_EPS_ROUTE", assess_candidate(observation).reasons)

    def test_quarterly_and_foreign_forms_preserved_but_not_annual_candidates(self):
        for form, fp in (("10-Q", "Q4"), ("20-F", "FY"), ("40-F", "FY"), ("10-K", "Q4"), ("10-K", "")):
            observation = extract(source([row(form=form, fp=fp)])).observations[0]
            self.assertIn("NOT_ANNUAL_FORM_CANDIDATE", assess_candidate(observation).reasons)
            self.assertEqual(json.loads(observation.row_json)["form"], form)

    def test_mapping_order_changes_byte_identity_not_semantic_identity(self):
        first = extract()
        second = extract(content=raw(reverse=True))
        self.assertEqual([r.semantic_id for r in first.observations], [r.semantic_id for r in second.observations])
        self.assertNotEqual(first.receipt_id, second.receipt_id)
        self.assertNotEqual(first.observations[0].source_object_hash, second.observations[0].source_object_hash)
        self.assertEqual(first, extract())

    def test_array_reordering_keeps_semantic_locators_and_updates_exact_pointers(self):
        first = extract(source([row(2023), row(2024)]))
        second = extract(source([row(2024), row(2023)]))
        self.assertEqual([r.semantic_locator for r in first.observations], [r.semantic_locator for r in second.observations])
        self.assertNotEqual([r.source_locator for r in first.observations], [r.source_locator for r in second.observations])

    def test_decimal_precision_not_lost_to_binary_float(self):
        content = raw(source([row()])).replace(b'"val":2', b'"val":2.123456789012345678901234567890123456789')
        observation = extract(content=content).observations[0]
        self.assertEqual(observation.value, Decimal("2.123456789012345678901234567890123456789"))

    def test_missing_source_cik_remains_unqualified(self):
        payload = source()
        del payload["cik"]
        observation = extract(payload).observations[0]
        self.assertIn("MISSING_SOURCE_CIK", observation.metadata_limitations)

    def test_source_cik_mismatch_rejected(self):
        payload = source()
        payload["cik"] = 1
        with self.assertRaises(ArchiveError):
            extract(payload)

    def test_malformed_json_and_duplicate_keys_rejected(self):
        for content in (b"not json", b'{"cik":0,"cik":1}', b'{"cik":NaN}', b"[]"):
            with self.subTest(content=content), self.assertRaises(ArchiveError):
                extract(content=content)

    def test_invalid_metadata_keeps_raw_row(self):
        observation = extract(source([row(start="bad", fy=True, val="bad", frame=123)])).observations[0]
        self.assertIn('"fy":true', observation.row_json)
        self.assertIn("INVALID_START", assess_candidate(observation).reasons)
        self.assertIn("INVALID_FY", observation.metadata_limitations)
        self.assertIn("INVALID_VALUE", observation.metadata_limitations)
        self.assertIn("INVALID_FRAME", observation.metadata_limitations)

    def test_impossible_period_and_filing_chronology_limited(self):
        for changes, reason in (({"start": "2024-12-31", "end": "2024-01-01"}, "REVERSED_PERIOD"),
                                ({"filed": "2024-01-01"}, "PERIOD_END_AFTER_FILED_DATE"),
                                ({"filed": "2027-01-01"}, "FILED_DATE_AFTER_CAPTURE_UTC_DATE")):
            observation = extract(source([row(**changes)])).observations[0]
            self.assertIn(reason, assess_candidate(observation).reasons)

    def test_malformed_row_is_preserved_with_limitation(self):
        observation = extract(source([None])).observations[0]
        self.assertEqual(observation.row_json, "null")
        self.assertIn("MALFORMED_ROW", observation.metadata_limitations)

    def test_extracted_records_are_immutable(self):
        observation = extract().observations[0]
        with self.assertRaises(FrozenInstanceError):
            observation.value = Decimal("99")
