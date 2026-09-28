"""Strict source-only verified-nonpayer resolution using fictional facts."""
import ast
from dataclasses import FrozenInstanceError, asdict, replace
from decimal import Decimal
import inspect
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts.sec_archive import SecArchive
from economic_facts.sec_common_stock_dividends import DECLARED_CONCEPT, PAID_CONCEPT
from economic_facts.sec_verified_nonpayer import (
    ConceptDecisionStatus, LIMITATIONS, NonpayerPeriodPolicy,
    VerifiedNonpayerReason as R, VerifiedNonpayerRequest,
    VerifiedNonpayerResolutionError, VerifiedNonpayerStatus as S,
    resolve_sec_verified_nonpayer,
)
from tests.sec_common_stock_dividend_fixtures import (
    capture_dividends, dividend_raw, dividend_row, dividend_source,
    nonpayer_request,
)
from tests.sec_filing_fixtures import CIK


class SecVerifiedNonpayerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.archive = SecArchive(Path(temporary.name).resolve() / "archive")

    def resolve(self, *, payload=None, raw=None, live=True, captured_at=None, **changes):
        kwargs = dict(payload=payload, raw=raw, live=live)
        if captured_at is not None:
            kwargs["captured_at"] = captured_at
        receipt = capture_dividends(self.archive, **kwargs)
        return resolve_sec_verified_nonpayer(self.archive,
                                             nonpayer_request(receipt, **changes))

    def assert_blocked(self, result, status, *reasons):
        self.assertIs(result.status, status)
        self.assertTrue(set(reasons) <= set(result.reasons), result.reasons)
        self.assertEqual(result.reasons,
                         tuple(sorted(set(result.reasons), key=lambda reason: reason.value)))

    def test_positive_exact_two_concept_annual_zero_route(self):
        result = self.resolve()
        self.assertIs(result.status, S.VERIFIED_NONPAYER_SOURCE_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual((result.period_start, result.period_end),
                         ("2024-01-01", "2024-12-31"))
        self.assertEqual(result.unit, "USD/shares")
        self.assertEqual({decision.concept for decision in result.decisions},
                         {DECLARED_CONCEPT, PAID_CONCEPT})
        for decision in result.decisions:
            self.assertIs(decision.status, ConceptDecisionStatus.EXACT_ZERO_ESTABLISHED)
            self.assertEqual(decision.distinct_values, (Decimal(0),))
            self.assertTrue(decision.representative_observation_id)
        self.assertEqual(result.limitations, LIMITATIONS)
        for limitation in ("NO_SELECTED_SECURITY_CLASS_JOIN",
                           "NO_SHARE_BASIS_QUALIFICATION",
                           "NO_REPORTING_SUBJECT_QUALIFICATION",
                           "NO_PR4B1_VERIFIED_NONPAYER_ROOT",
                           "PAYER_ROUTE_NOT_SUPPORTED"):
            self.assertIn(limitation, result.limitations)
        with self.assertRaises(FrozenInstanceError):
            result.status = S.UNAVAILABLE

    def test_supported_february_month_end_calendar(self):
        annual = dividend_row(0, start="2023-03-01", end="2024-02-29",
                              filed="2024-04-01", frame="CY2023")
        result = self.resolve(payload=dividend_source(declared=[annual], paid=[annual]),
                              latest_required_fiscal_end="2024-02-29")
        self.assertIs(result.status, S.VERIFIED_NONPAYER_SOURCE_ESTABLISHED)

    def test_missing_latest_period_does_not_fall_back_to_older_year(self):
        older = dividend_row(0, year=2023)
        result = self.resolve(payload=dividend_source(declared=[older], paid=[older]))
        self.assert_blocked(result, S.UNAVAILABLE, R.MISSING_REQUIRED_ANNUAL_PERIOD)

    def test_missing_declared_paid_or_both_never_becomes_zero(self):
        for missing, expected in (
            ((DECLARED_CONCEPT,), R.DECLARED_CONCEPT_UNAVAILABLE),
            ((PAID_CONCEPT,), R.PAID_CONCEPT_UNAVAILABLE),
            ((DECLARED_CONCEPT, PAID_CONCEPT), R.DECLARED_CONCEPT_UNAVAILABLE),
        ):
            payload = dividend_source()
            for concept in missing:
                del payload["facts"]["us-gaap"][concept]
            with self.subTest(missing=missing):
                result = self.resolve(payload=payload)
                self.assert_blocked(result, S.UNAVAILABLE, expected,
                                    R.MISSING_REQUIRED_ANNUAL_PERIOD)
                if len(missing) == 2:
                    self.assertIn(R.PAID_CONCEPT_UNAVAILABLE, result.reasons)

    def test_empty_fact_arrays_never_mean_zero(self):
        result = self.resolve(payload=dividend_source(declared=[], paid=[]))
        self.assert_blocked(result, S.UNAVAILABLE, R.DECLARED_CONCEPT_UNAVAILABLE,
                            R.PAID_CONCEPT_UNAVAILABLE, R.MISSING_REQUIRED_ANNUAL_PERIOD)

    def test_valid_payer_evidence_is_unavailable_not_malformed(self):
        cases = (
            ([dividend_row(0.25)], [dividend_row(0)], R.NONZERO_DECLARED_DIVIDEND),
            ([dividend_row(0)], [dividend_row(0.25)], R.NONZERO_PAID_DIVIDEND),
            ([dividend_row(0.25)], [dividend_row(0.25)], R.NONZERO_DECLARED_DIVIDEND),
        )
        for declared, paid, expected in cases:
            with self.subTest(expected=expected):
                result = self.resolve(payload=dividend_source(declared=declared, paid=paid))
                self.assert_blocked(result, S.UNAVAILABLE, expected)
                self.assertNotIn(R.MALFORMED_SOURCE, result.reasons)

    def test_zero_and_positive_cross_concept_contradictions(self):
        first = self.resolve(payload=dividend_source(
            declared=[dividend_row(0)], paid=[dividend_row(0.50)]))
        self.assert_blocked(first, S.UNAVAILABLE, R.NONZERO_PAID_DIVIDEND)
        second = self.resolve(payload=dividend_source(
            declared=[dividend_row(0.50)], paid=[dividend_row(0)]))
        self.assert_blocked(second, S.UNAVAILABLE, R.NONZERO_DECLARED_DIVIDEND)

    def test_original_and_amendment_disagreement_has_no_winner(self):
        zero = dividend_row(0)
        positive_amendment = dividend_row(0.25, form="10-K/A",
                                          filed="2025-03-01",
                                          accn="0000000000-25-000002")
        for rows in ((zero, positive_amendment), (positive_amendment, zero)):
            for concept in (DECLARED_CONCEPT, PAID_CONCEPT):
                payload = dividend_source()
                payload["facts"]["us-gaap"][concept]["units"]["USD/shares"] = list(rows)
                with self.subTest(concept=concept, rows=rows):
                    result = self.resolve(payload=payload)
                    self.assert_blocked(result, S.SOURCE_CONFLICT,
                                        R.UNRESOLVED_VALUE_CONFLICT)
                    self.assertEqual(len(next(d for d in result.decisions
                                              if d.concept == concept).conflicting_observation_ids), 2)

    def test_zero_majority_cannot_vote_away_one_positive_version(self):
        rows = [
            dividend_row(0),
            dividend_row(0, form="10-K/A", filed="2025-03-01",
                         accn="0000000000-25-000002"),
            dividend_row(0.25, form="10-K/A", filed="2025-04-01",
                         accn="0000000000-25-000003"),
        ]
        result = self.resolve(payload=dividend_source(declared=rows))
        self.assert_blocked(result, S.SOURCE_CONFLICT,
                            R.UNRESOLVED_VALUE_CONFLICT,
                            R.NONZERO_DECLARED_DIVIDEND)

    def test_repeated_equivalent_versions_and_decimal_zero_spellings_agree(self):
        rows = [dividend_row(0), dividend_row(0.0, form="10-K/A",
                                             filed="2025-03-01",
                                             accn="0000000000-25-000002")]
        result = self.resolve(payload=dividend_source(declared=rows, paid=rows))
        self.assertIs(result.status, S.VERIFIED_NONPAYER_SOURCE_ESTABLISHED)
        self.assertTrue(all(decision.distinct_values == (Decimal(0),)
                            for decision in result.decisions))

    def test_intra_period_positive_fact_blocks_without_summing(self):
        quarter = dividend_row(0.25, start="2024-04-01", end="2024-06-30",
                               fy=2024, fp="Q2", form="10-Q", filed="2024-08-01",
                               accn="0000000000-24-000002", frame="CY2024Q2")
        for concept in (DECLARED_CONCEPT, PAID_CONCEPT):
            payload = dividend_source()
            payload["facts"]["us-gaap"][concept]["units"]["USD/shares"].append(quarter)
            with self.subTest(concept=concept):
                result = self.resolve(payload=payload)
                self.assert_blocked(result, S.UNAVAILABLE,
                                    R.INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE)

    def test_overlapping_positive_context_fails_conservatively(self):
        overlap = dividend_row(0.10, start="2023-10-01", end="2024-03-31",
                               fp="Q1", form="10-Q", filed="2024-05-01",
                               accn="0000000000-24-000003")
        payload = dividend_source(declared=[dividend_row(), overlap])
        self.assert_blocked(self.resolve(payload=payload), S.UNAVAILABLE,
                            R.INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE)

    def test_unlocatable_nonzero_period_fails_conservatively(self):
        for missing in ("start", "end"):
            row = dividend_row(0.10, fp="Q2", form="10-Q",
                               filed="2024-08-01", accn="0000000000-24-000004")
            row.pop(missing)
            with self.subTest(missing=missing):
                result = self.resolve(payload=dividend_source(declared=[dividend_row(), row]))
                self.assert_blocked(result, S.UNSUPPORTED_SOURCE_PROFILE,
                                    R.INSUFFICIENT_FILING_IDENTITY)

    def test_later_short_positive_fact_does_not_retroactively_invalidate(self):
        later = dividend_row(0.25, year=2025, start="2025-01-01", end="2025-03-31",
                             fp="Q1", form="10-Q", filed="2025-05-01",
                             accn="0000000000-25-000003", frame="CY2025Q1")
        payload = dividend_source(declared=[dividend_row(), later])
        result = self.resolve(payload=payload)
        self.assertIs(result.status, S.VERIFIED_NONPAYER_SOURCE_ESTABLISHED)

    def test_later_complete_annual_period_blocks_older_caller_selection(self):
        later = dividend_row(0, year=2025, filed="2026-02-01",
                             accn="0000000000-26-000001")
        payload = dividend_source(declared=[dividend_row(), later])
        self.assert_blocked(self.resolve(payload=payload), S.UNAVAILABLE,
                            R.LATER_ANNUAL_PERIOD_PRESENT)

    def test_tiny_positive_has_no_tolerance_and_negative_is_conflict(self):
        tiny_raw = dividend_raw().replace(b'"val":0',
                                          b'"val":0.0000000000000000000000001', 1)
        tiny = self.resolve(raw=tiny_raw)
        self.assert_blocked(tiny, S.UNAVAILABLE, R.NONZERO_DECLARED_DIVIDEND)
        negative = self.resolve(payload=dividend_source(declared=[dividend_row(-0.01)]))
        self.assert_blocked(negative, S.SOURCE_CONFLICT, R.UNSUPPORTED_NEGATIVE_VALUE)

    def test_wrong_cik_unit_and_source_cik_fail_closed(self):
        result = self.resolve(cik="0000000001")
        self.assert_blocked(result, S.UNSUPPORTED_SOURCE_PROFILE, R.CIK_MISMATCH)
        payload = dividend_source()
        for concept in (DECLARED_CONCEPT, PAID_CONCEPT):
            node = payload["facts"]["us-gaap"][concept]["units"]
            node["CAD/shares"] = node.pop("USD/shares")
        self.assert_blocked(self.resolve(payload=payload), S.UNSUPPORTED_SOURCE_PROFILE,
                            R.UNIT_MISMATCH)
        wrong_source = dividend_source(cik=1)
        self.assert_blocked(self.resolve(payload=wrong_source), S.UNSUPPORTED_SOURCE_PROFILE,
                            R.MALFORMED_SOURCE)

    def test_malformed_dates_accession_form_and_fp(self):
        cases = (
            ({"start": "bad"}, R.INSUFFICIENT_FILING_IDENTITY),
            ({"end": "2024-02-30"}, R.INSUFFICIENT_FILING_IDENTITY),
            ({"accn": None}, R.INSUFFICIENT_FILING_IDENTITY),
            ({"form": "8-K"}, R.UNSUPPORTED_FORM),
            ({"fp": "Q4"}, R.NON_FY_PERIOD),
        )
        for changes, reason in cases:
            with self.subTest(changes=changes):
                row = dividend_row(**changes)
                result = self.resolve(payload=dividend_source(declared=[row]))
                self.assertIn(reason, result.reasons)
                self.assertIsNot(result.status, S.VERIFIED_NONPAYER_SOURCE_ESTABLISHED)

    def test_unsupported_52_53_week_calendars(self):
        for start in ("2024-01-02", "2023-12-27"):
            with self.subTest(start=start):
                row = dividend_row(start=start)
                result = self.resolve(payload=dividend_source(declared=[row]))
                self.assert_blocked(result, S.UNSUPPORTED_SOURCE_PROFILE,
                                    R.UNSUPPORTED_CALENDAR)

    def test_filing_chronology_violation(self):
        for filed in ("2024-01-01", "2027-01-01"):
            with self.subTest(filed=filed):
                result = self.resolve(payload=dividend_source(
                    declared=[dividend_row(filed=filed)]))
                self.assert_blocked(result, S.UNSUPPORTED_SOURCE_PROFILE,
                                    R.INVALID_FILING_CHRONOLOGY)

    def test_unknown_context_is_unsupported_not_silently_ignored(self):
        result = self.resolve(payload=dividend_source(
            declared=[dividend_row(segment={"axis": "fictional"})]))
        self.assert_blocked(result, S.UNSUPPORTED_SOURCE_PROFILE, R.UNRESOLVED_CONTEXT)

    def test_offline_capture_cannot_establish_positive_source_route(self):
        result = self.resolve(live=False)
        self.assert_blocked(result, S.UNAVAILABLE, R.OFFLINE_CAPTURE_ONLY)

    def test_row_and_mapping_order_semantics_are_stable(self):
        rows = [dividend_row(0), dividend_row(0, form="10-K/A",
                                             filed="2025-03-01",
                                             accn="0000000000-25-000002")]
        first = self.resolve(payload=dividend_source(declared=rows, paid=rows))
        second = self.resolve(payload=dividend_source(declared=list(reversed(rows)),
                                                      paid=list(reversed(rows))))
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)
        third = self.resolve(raw=dividend_raw(reverse=True))
        baseline = self.resolve()
        self.assertEqual(baseline.semantic_hash, third.semantic_hash)
        self.assertNotEqual(baseline.evidence_hash, third.evidence_hash)

    def test_equivalent_recapture_changes_evidence_not_semantics(self):
        raw = dividend_raw()
        first = self.resolve(raw=raw, captured_at="2026-03-01T12:00:00Z")
        second = self.resolve(raw=raw, captured_at="2026-04-01T12:00:00Z")
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)

    def test_request_surface_is_closed_and_immutable(self):
        receipt = capture_dividends(self.archive)
        request = nonpayer_request(receipt)
        self.assertEqual(set(inspect.signature(resolve_sec_verified_nonpayer).parameters),
                         {"archive", "request"})
        self.assertEqual(set(VerifiedNonpayerRequest.__dataclass_fields__), {
            "contract_version", "receipt_id", "cik", "latest_required_fiscal_end",
            "expected_unit", "period_policy",
        })
        for forbidden in ("ticker", "share_class", "security_id", "nonpayer",
                          "qualified", "as_of", "source_bytes", "provider_url"):
            self.assertNotIn(forbidden, VerifiedNonpayerRequest.__dataclass_fields__)
        with self.assertRaises(FrozenInstanceError):
            request.cik = CIK
        with self.assertRaises(TypeError):
            VerifiedNonpayerRequest(**asdict(request), ticker="FAKE")
        with self.assertRaises(VerifiedNonpayerResolutionError):
            resolve_sec_verified_nonpayer(self.archive, asdict(request))
        with self.assertRaises(VerifiedNonpayerResolutionError):
            resolve_sec_verified_nonpayer(self.archive, replace(
                request, period_policy="fake"))

    def test_no_network_clock_archive_write_or_latest_selection(self):
        receipt = capture_dividends(self.archive)
        request = nonpayer_request(receipt)
        def inventory():
            return {str(path.relative_to(self.archive.root)):
                    (path.read_bytes(), path.stat().st_mode, path.stat().st_mtime_ns)
                    for path in self.archive.root.rglob("*") if path.is_file()}
        before = inventory()
        with patch.object(SecArchive, "capture", side_effect=AssertionError("write")), \
             patch.object(SecArchive, "_publish", side_effect=AssertionError("write")), \
             patch.object(SecArchive, "captures_as_of", side_effect=AssertionError("latest")), \
             patch.object(socket.socket, "connect", side_effect=AssertionError("network")), \
             patch.object(socket, "getaddrinfo", side_effect=AssertionError("network")):
            resolve_sec_verified_nonpayer(self.archive, request)
        self.assertEqual(before, inventory())

    def test_hash_seed_determinism_and_no_model_import(self):
        receipt = capture_dividends(self.archive)
        code = '''import sys
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_verified_nonpayer import resolve_sec_verified_nonpayer
from tests.sec_common_stock_dividend_fixtures import nonpayer_request
a=SecArchive(sys.argv[1]); r=a.read_receipt(sys.argv[2])
x=resolve_sec_verified_nonpayer(a, nonpayer_request(r))
assert "src.expected_return_assumptions" not in sys.modules
assert "economic_facts.sec_acquisition" not in sys.modules
print(x.semantic_hash, x.evidence_hash)
'''
        outputs = [subprocess.check_output(
            [sys.executable, "-B", "-c", code, str(self.archive.root), receipt.receipt_id],
            env={**os.environ, "PYTHONHASHSEED": seed}, text=True)
            for seed in ("1", "777")]
        self.assertEqual(outputs[0], outputs[1])

    def test_static_purity_and_no_expected_return_consumer(self):
        root = Path(__file__).resolve().parents[1]
        allowed = {
            "sec_common_stock_dividends.py": {
                "dataclasses", "decimal", "hashlib", "json", "re", "sec_archive",
            },
            "sec_verified_nonpayer.py": {
                "calendar", "dataclasses", "datetime", "decimal", "enum", "json", "re",
                "sec_archive", "sec_common_stock_dividends",
            },
        }
        for filename, permitted in allowed.items():
            tree = ast.parse((root / "economic_facts" / filename).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name in permitted for alias in node.names))
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module, permitted)
                if isinstance(node, ast.Call):
                    name = (node.func.id if isinstance(node.func, ast.Name)
                            else node.func.attr if isinstance(node.func, ast.Attribute) else "")
                    self.assertNotIn(name, {"open", "write", "write_text", "write_bytes",
                                            "capture", "_capture_live", "_publish", "now",
                                            "today", "getenv", "system", "run", "exec", "eval",
                                            "__import__"})
        assumptions = (root / "src" / "expected_return_assumptions.py").read_text()
        self.assertNotIn("sec_verified_nonpayer", assumptions)
        self.assertNotIn("sec_common_stock_dividends", assumptions)
        production = "\n".join(path.read_text(errors="ignore") for path in (root / "src").glob("*.py"))
        self.assertNotIn("resolve_sec_verified_nonpayer", production)


if __name__ == "__main__":
    unittest.main()
