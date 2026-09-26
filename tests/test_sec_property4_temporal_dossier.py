"""PR4D4A fictional offline temporal-dossier and authority-boundary tests."""
import ast
from dataclasses import FrozenInstanceError, asdict, fields
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_class_eps_claims as d3b
from economic_facts import sec_filing_archive as fa
from economic_facts import sec_property4_temporal_dossier as d
from economic_facts import sec_registered_securities as d3a
from economic_facts import sec_submissions_archive as sa
from tests.sec_property4_temporal_fixtures import (
    ACCESSION, CAPTURE_1, CAPTURE_2, CIK, FILENAME, PROFILES, combined_submission,
)
from tests.sec_submissions_fixtures import NAME, history, reference, root, row


def source_row(number=1, **changes):
    return row(number, **{**{"accessionNumber": f"0000000001-26-{number:06d}",
                             "primaryDocument": FILENAME}, **changes})


class TemporalDossierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.submissions = sa.SecSubmissionsArchive(base / "submissions")
        self.filings = fa.SecFilingArchive(base / "filings")

    def parent(self, *, rows=None, refs=None, captured_at=CAPTURE_1):
        return self.submissions._capture_live(
            root([source_row()] if rows is None else rows, refs), cik=CIK,
            captured_at=captured_at)

    def child(self, parent, *, rows=None, captured_at=CAPTURE_2):
        return self.submissions._capture_live(
            history([] if rows is None else rows), cik=CIK, captured_at=captured_at,
            parent_receipt_id=parent.receipt_id, history_filename=NAME)

    def filing(self, *, accession=ACCESSION, cik=CIK, form="10-K", captured_at=CAPTURE_1,
               filename=FILENAME, raw=None, **inline_changes):
        body = (combined_submission(cik=cik, accession=accession, form=form,
                                    filename=filename, **inline_changes)
                if raw is None else raw)
        return self.filings._capture_live(body, cik=cik, accession=accession,
                                          captured_at=captured_at)

    def build(self, parent, *, children=(), filings=()):
        request = d.SecProperty4TemporalDossierRequest(
            parent.receipt_id, tuple(child.receipt_id for child in children),
            tuple(receipt.receipt_id for receipt in filings))
        return d.build_sec_property4_temporal_dossier(
            self.submissions, self.filings, request)

    def test_one_valid_10k_replays_typed_d2b_d2a_d3a_d3b(self):
        result = self.build(self.parent(), filings=(self.filing(),))
        self.assertEqual(result.status, d.DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER)
        self.assertEqual(result.source_cik, CIK)
        self.assertEqual(len(result.filings), 1)
        capture = result.filings[0].captures[0]
        self.assertIsInstance(capture.registered_security_claims,
                              d3a.SecRegisteredSecurityExtractionAssessment)
        self.assertIsInstance(capture.class_eps_claims,
                              d3b.SecClassEPSExtractionAssessment)
        self.assertEqual(capture.registered_security_claims.status,
                         d3a.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
        self.assertEqual(capture.class_eps_claims.status,
                         d3b.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS)

    def test_multi_year_10k_chronology_uses_source_acceptance_then_filing_date(self):
        rows = [source_row(3, filingDate="2024-02-01", reportDate="2023-12-31",
                           acceptanceDateTime="2024-02-01T15:30:00Z"),
                source_row(2, filingDate="2025-02-01", reportDate="2024-12-31",
                           acceptanceDateTime="2025-02-01T15:30:00Z"),
                source_row(1)]
        captures = tuple(self.filing(accession=entry["accessionNumber"]) for entry in rows)
        result = self.build(self.parent(rows=rows), filings=tuple(reversed(captures)))
        self.assertEqual([entry.accession for entry in result.filings],
                         [rows[0]["accessionNumber"], rows[1]["accessionNumber"], ACCESSION])
        self.assertEqual(result.status, d.DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER)

    def test_10k_and_10q_sequence_and_all_four_supported_forms(self):
        forms = ("10-K", "10-K/A", "10-Q", "10-Q/A")
        rows = [source_row(index + 1, form=form,
                           filingDate=f"2026-0{index + 1}-01",
                           acceptanceDateTime=f"2026-0{index + 1}-01T15:30:00Z")
                for index, form in enumerate(forms)]
        captures = tuple(self.filing(accession=entry["accessionNumber"], form=entry["form"])
                         for entry in rows)
        result = self.build(self.parent(rows=rows), filings=captures)
        self.assertEqual([dict(entry.inventory_occurrences[0].fields)["form"]
                          for entry in result.filings], list(forms))
        self.assertEqual(result.status, d.DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER)

    def test_amendments_are_separate_and_never_replace_originals(self):
        for original, amendment in (("10-K", "10-K/A"), ("10-Q", "10-Q/A")):
            with self.subTest(original=original):
                rows = [source_row(1, form=original), source_row(2, form=amendment,
                        acceptanceDateTime="2026-03-01T15:30:00Z")]
                result = self.build(self.parent(rows=rows), filings=(
                    self.filing(form=original),
                    self.filing(accession=rows[1]["accessionNumber"], form=amendment),
                ))
                self.assertEqual(len(result.filings), 2)
                self.assertEqual({entry.accession for entry in result.filings},
                                 {entry["accessionNumber"] for entry in rows})

    def test_8k_and_unrelated_forms_are_excluded_without_absence_authority(self):
        rows = [source_row(1, form="8-K"), source_row(2, form="20-F")]
        result = self.build(self.parent(rows=rows))
        self.assertEqual(result.status, d.DossierStatus.NO_RELEVANT_PERIODIC_FILINGS)
        self.assertEqual(result.filings, ())
        self.assertEqual(d.RELEVANT_FORMS, frozenset(("10-K", "10-K/A", "10-Q", "10-Q/A")))

    def test_missing_relevant_capture_is_incomplete_and_remains_visible(self):
        result = self.build(self.parent(rows=[source_row(), source_row(2)]),
                            filings=(self.filing(),))
        self.assertEqual(result.status, d.DossierStatus.INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER)
        missing = next(entry for entry in result.filings if not entry.captures)
        self.assertIn(d.DossierIssue.MISSING_D2A_CAPTURE, missing.issues)

    def test_filing_receipt_cik_mismatch_and_absent_accession_are_rejected(self):
        parent = self.parent()
        foreign_cik = "0000000456"
        foreign = self.filing(cik=foreign_cik)
        absent = self.filing(accession="0000000001-26-999999")
        for receipt in (foreign, absent):
            with self.subTest(receipt=receipt.accession), \
                 self.assertRaises(d.SecProperty4TemporalDossierRequestError):
                self.build(parent, filings=(receipt,))

    def test_selected_receipt_for_irrelevant_inventory_form_is_rejected(self):
        parent = self.parent(rows=[source_row(form="8-K")])
        receipt = self.filing(form="8-K", raw=combined_submission().replace(b"10-K", b"8-K "))
        with self.assertRaises(d.SecProperty4TemporalDossierRequestError):
            self.build(parent, filings=(receipt,))

    def test_form_and_primary_filename_mismatches_are_source_conflicts(self):
        cases = ((source_row(form="10-Q"), self.filing(), d.DossierIssue.D2B_D2A_FORM_MISMATCH),
                 (source_row(primaryDocument="other.htm"), self.filing(),
                  d.DossierIssue.D2B_D2A_PRIMARY_DOCUMENT_MISMATCH))
        for source, receipt, issue in cases:
            with self.subTest(issue=issue):
                result = self.build(self.parent(rows=[source]), filings=(receipt,))
                self.assertEqual(result.status, d.DossierStatus.SOURCE_CONFLICT)
                self.assertIn(issue, result.issues)

    def test_identical_d2b_duplicates_retain_occurrences_without_false_conflict(self):
        result = self.build(self.parent(rows=[source_row(), source_row()]),
                            filings=(self.filing(),))
        entry = result.filings[0]
        self.assertEqual(len(entry.inventory_occurrences), 2)
        self.assertEqual(len({item.semantic_id for item in entry.inventory_occurrences}), 1)
        self.assertEqual(len({item.occurrence_id for item in entry.inventory_occurrences}), 2)
        self.assertEqual(result.status, d.DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER)

    def test_differing_d2b_rows_for_same_accession_propagate_source_conflict(self):
        result = self.build(self.parent(rows=[source_row(), source_row(size=9999)]),
                            filings=(self.filing(),))
        self.assertEqual(result.status, d.DossierStatus.SOURCE_CONFLICT)
        self.assertIn(d.DossierIssue.D2B_RELEVANT_INVENTORY_CONFLICT, result.issues)
        self.assertEqual(len(result.filings[0].inventory_occurrences), 2)

    def test_d2b_range_conflict_and_reference_incompleteness_propagate(self):
        parent = self.parent(rows=[], refs=[reference(filingFrom="2026-03-01")])
        child = self.child(parent, rows=[source_row()])
        conflict = self.build(parent, children=(child,))
        self.assertEqual(conflict.status, d.DossierStatus.SOURCE_CONFLICT)
        self.assertIn(d.DossierIssue.D2B_RANGE_CONFLICT, conflict.issues)
        incomplete = self.build(self.parent(refs=[reference()]), filings=(self.filing(),))
        self.assertEqual(incomplete.status, d.DossierStatus.INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER)
        self.assertIn(d.DossierIssue.D2B_REFERENCE_CLOSURE_INCOMPLETE, incomplete.issues)

    def test_identical_byte_recapture_preserves_semantics_and_changes_evidence(self):
        parent = self.parent()
        first = self.filing()
        second = self.filing(captured_at=CAPTURE_2)
        one = self.build(parent, filings=(first,))
        two = self.build(parent, filings=(second, first))
        self.assertEqual(one.semantic_id, two.semantic_id)
        self.assertNotEqual(one.evidence_id, two.evidence_id)
        self.assertEqual({capture.receipt.captured_at for capture in two.filings[0].captures},
                         {CAPTURE_1, CAPTURE_2})

    def test_differing_bytes_for_one_accession_are_conflict_without_winner(self):
        parent = self.parent()
        left = self.filing(symbol="LEFT")
        right = self.filing(symbol="RIGHT", captured_at=CAPTURE_2)
        result = self.build(parent, filings=(left, right))
        self.assertEqual(result.status, d.DossierStatus.SOURCE_CONFLICT)
        self.assertIn(d.DossierIssue.DIFFERING_D2A_CAPTURE_BYTES, result.issues)
        self.assertEqual({capture.receipt.content_sha256 for capture in result.filings[0].captures},
                         {left.content_sha256, right.content_sha256})

    def test_d3a_statuses_are_preserved_and_classified(self):
        cases = (
            ({}, d3a.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS, None),
            ({"include_registered": False,
              "extra_registered": '<ix:nonNumeric name="dei:Security12bTitle" contextRef="registered">Only title</ix:nonNumeric>'},
             d3a.ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS, d.DossierIssue.D3A_INCOMPLETE),
            ({"extra_registered": '<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered">OTHER</ix:nonNumeric>'},
             d3a.ExtractionStatus.SOURCE_CONFLICT, d.DossierIssue.D3A_SOURCE_CONFLICT),
            ({"include_registered": False},
             d3a.ExtractionStatus.NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS,
             d.DossierIssue.D3A_NO_SUPPORTED_CLAIMS),
        )
        for changes, status, issue in cases:
            with self.subTest(status=status):
                result = self.build(self.parent(), filings=(self.filing(**changes),))
                capture = result.filings[0].captures[0]
                self.assertEqual(capture.registered_security_claims.status, status)
                if issue is not None:
                    self.assertIn(issue, capture.issues)

    def test_d3b_statuses_are_preserved_and_classified(self):
        cases = (
            ({}, d3b.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS, None),
            ({"include_eps": False}, d3b.ExtractionStatus.INCOMPLETE_CLASS_EPS_SOURCE_CLAIMS,
             d.DossierIssue.D3B_INCOMPLETE),
            ({"extra_class_eps": '<ix:nonFraction name="us-gaap:EarningsPerShareDiluted" contextRef="eps" unitRef="u-usd-per-share" decimals="2">9.99</ix:nonFraction>'},
             d3b.ExtractionStatus.SOURCE_CONFLICT, d.DossierIssue.D3B_SOURCE_CONFLICT),
            ({"include_shares": False, "include_eps": False},
             d3b.ExtractionStatus.NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS,
             d.DossierIssue.D3B_NO_SUPPORTED_CLAIMS),
        )
        for changes, status, issue in cases:
            with self.subTest(status=status):
                result = self.build(self.parent(), filings=(self.filing(**changes),))
                capture = result.filings[0].captures[0]
                self.assertEqual(capture.class_eps_claims.status, status)
                if issue is not None:
                    self.assertIn(issue, capture.issues)

    def test_reviewed_unsupported_exceptions_become_stable_independent_gaps(self):
        parent, receipt = self.parent(), self.filing()
        with patch.object(d, "extract_sec_registered_security_claims",
                          side_effect=d3a.UnsupportedRegisteredSecuritySource("varying detail")):
            result = self.build(parent, filings=(receipt,))
        capture = result.filings[0].captures[0]
        self.assertIsNone(capture.registered_security_claims)
        self.assertIsNotNone(capture.class_eps_claims)
        self.assertIn(d.DossierIssue.D3A_UNSUPPORTED_SOURCE, capture.issues)
        with patch.object(d, "extract_sec_class_eps_claims",
                          side_effect=d3b.UnsupportedSecClassEPSSource("other detail")):
            result = self.build(parent, filings=(receipt,))
        capture = result.filings[0].captures[0]
        self.assertIsNotNone(capture.registered_security_claims)
        self.assertIsNone(capture.class_eps_claims)
        self.assertIn(d.DossierIssue.D3B_UNSUPPORTED_SOURCE, capture.issues)

    def test_real_unsupported_primary_representation_records_both_gaps(self):
        receipt = self.filing(raw=combined_submission().replace(
            b'<html xmlns="http://www.w3.org/1999/xhtml"', b'<html'))
        result = self.build(self.parent(), filings=(receipt,))
        capture = result.filings[0].captures[0]
        self.assertEqual(capture.registered_security_claims, None)
        self.assertEqual(capture.class_eps_claims, None)
        self.assertEqual(set(capture.issues), {d.DossierIssue.D3A_UNSUPPORTED_SOURCE,
                                               d.DossierIssue.D3B_UNSUPPORTED_SOURCE})

    def test_archive_corruption_and_programming_errors_propagate(self):
        parent, receipt = self.parent(), self.filing()
        target = self.filings.root / "objects" / receipt.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"x" * receipt.byte_length)
        with self.assertRaises(fa.FilingArchiveError):
            self.build(parent, filings=(receipt,))
        clean = self.filing(captured_at=CAPTURE_2, symbol="CLEAN")
        with patch.object(d, "extract_sec_registered_security_claims",
                          side_effect=RuntimeError("programming defect")), \
             self.assertRaises(RuntimeError):
            self.build(parent, filings=(clean,))

    def test_historical_d3c_profiles_flow_through_both_rails(self):
        for year in (2019, 2026):
            with self.subTest(year=year):
                result = self.build(self.parent(), filings=(self.filing(profile=PROFILES[year]),))
                capture = result.filings[0].captures[0]
                self.assertEqual(capture.registered_security_claims.status,
                                 d3a.ExtractionStatus.CAPTURED_REGISTERED_SECURITY_CLAIMS)
                self.assertEqual(capture.class_eps_claims.status,
                                 d3b.ExtractionStatus.CAPTURED_CLASS_EPS_SOURCE_CLAIMS)

    def test_source_clocks_remain_distinct_and_verbatim(self):
        source = source_row(filingDate="2026-02-01", reportDate="2025-12-31",
                            acceptanceDateTime="2026-02-01T15:30:00.123Z")
        result = self.build(self.parent(rows=[source]), filings=(self.filing(),))
        fields_map = dict(result.filings[0].inventory_occurrences[0].fields)
        self.assertEqual(fields_map["filingDate"], "2026-02-01")
        self.assertEqual(fields_map["reportDate"], "2025-12-31")
        self.assertEqual(fields_map["acceptanceDateTime"], "2026-02-01T15:30:00.123Z")
        self.assertEqual(result.filings[0].captures[0].receipt.captured_at, CAPTURE_1)
        self.assertTrue({"published_at", "available_at", "historically_known_by"}.isdisjoint(
            asdict(result)))

    def test_request_order_never_changes_chronology_status_or_identity(self):
        rows = [source_row(1), source_row(2, filingDate="2025-02-01",
                       acceptanceDateTime="2025-02-01T15:30:00Z")]
        parent = self.parent(rows=rows)
        receipts = (self.filing(), self.filing(accession=rows[1]["accessionNumber"]))
        left = self.build(parent, filings=receipts)
        right = self.build(parent, filings=tuple(reversed(receipts)))
        self.assertEqual(left, right)
        self.assertEqual(left.semantic_id, right.semantic_id)
        self.assertEqual(left.evidence_id, right.evidence_id)

    def test_repeated_or_changed_ticker_and_member_create_no_cross_filing_identity(self):
        rows = [source_row(1), source_row(2, acceptanceDateTime="2026-03-01T15:30:00Z")]
        parent = self.parent(rows=rows)
        for second_symbol in ("FICT", "CHANGED"):
            with self.subTest(symbol=second_symbol):
                result = self.build(parent, filings=(
                    self.filing(symbol="FICT"),
                    self.filing(accession=rows[1]["accessionNumber"], symbol=second_symbol),
                ))
                self.assertEqual(len(result.filings), 2)
                self.assertFalse(hasattr(result, "security_identity"))
                self.assertFalse(hasattr(result, "continuity"))
                scopes = [entry.captures[0].class_eps_claims.claims[0].source_class_scope_id
                          for entry in result.filings]
                self.assertTrue(all(scope is not None for scope in scopes))

    def test_records_are_frozen_slotted_and_have_no_economic_authority_fields(self):
        result = self.build(self.parent(), filings=(self.filing(),))
        forbidden = {"issuer_id", "security_id", "class_id", "listing_id", "continuity",
                     "complete", "applicable", "entitled", "quote_currency", "authority",
                     "qualified", "admitted", "available_at", "published_at", "as_of"}
        for record in (d.SecProperty4TemporalDossierRequest, d.FilingCaptureEvidence,
                       d.TemporalFilingEvidence, d.SecProperty4TemporalDossier):
            self.assertTrue(forbidden.isdisjoint(record.__dataclass_fields__))
            self.assertTrue(hasattr(record, "__slots__"))
        with self.assertRaises(FrozenInstanceError):
            result.status = d.DossierStatus.SOURCE_CONFLICT

    def test_exact_request_shape_validation_and_bounds(self):
        self.assertEqual({field.name for field in fields(d.SecProperty4TemporalDossierRequest)},
                         {"parent_submissions_receipt_id", "child_submissions_receipt_ids",
                          "filing_receipt_ids"})
        bad = (("x", (), ()), ("0" * 64, [], ()), ("0" * 64, (), []),
               ("0" * 64, ("1" * 64, "1" * 64), ()),
               ("0" * 64, (), ("1" * 64, "1" * 64)))
        for args in bad:
            with self.subTest(args=args), \
                 self.assertRaises(d.SecProperty4TemporalDossierRequestError):
                d.SecProperty4TemporalDossierRequest(*args)
        with patch.object(d, "MAX_FILING_RECEIPTS", 0), \
             self.assertRaises(d.SecProperty4TemporalDossierRequestError):
            d.SecProperty4TemporalDossierRequest("0" * 64, (), ("1" * 64,))

    def test_dossier_cannot_enter_d1_c4_or_expected_return(self):
        result = self.build(self.parent(), filings=(self.filing(),))
        from economic_facts.current_authority import CurrentAuthorityError
        from economic_facts.sec_current_evidence import assess_sec_current_evidence
        from economic_facts.security_identity import IdentityContractError, qualify_security_identity
        from src.expected_return_assumptions import ConstructorContractError, construct_expected_return
        from src.expected_return_engine import ExpectedReturnError, calculate_expected_return
        with self.assertRaises(CurrentAuthorityError):
            assess_sec_current_evidence(self.filings, result)
        with self.assertRaises(IdentityContractError):
            qualify_security_identity(result, result, result)
        with self.assertRaises(ConstructorContractError):
            construct_expected_return(result)
        with self.assertRaises(ExpectedReturnError):
            calculate_expected_return(result)

    def test_replay_has_no_network_write_clock_or_directory_discovery(self):
        parent, receipt = self.parent(), self.filing()
        before_submissions = {str(path.relative_to(self.submissions.root)): path.read_bytes()
                              for path in self.submissions.root.rglob("*") if path.is_file()}
        before_filings = {str(path.relative_to(self.filings.root)): path.read_bytes()
                          for path in self.filings.root.rglob("*") if path.is_file()}
        real_open = os.open

        def read_only(path, flags, *args, **kwargs):
            self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
            return real_open(path, flags, *args, **kwargs)

        with patch.object(os, "open", side_effect=read_only), \
             patch.object(os, "mkdir", side_effect=AssertionError("write forbidden")), \
             patch.object(os, "scandir", side_effect=AssertionError("discovery forbidden")), \
             patch.object(socket, "create_connection", side_effect=AssertionError("network forbidden")), \
             patch.object(d, "datetime", side_effect=AssertionError("clock forbidden")):
            # datetime.fromisoformat is chronology parsing, not a clock read; keep
            # the real class available through an explicit shim.
            d.datetime.fromisoformat.side_effect = __import__("datetime").datetime.fromisoformat
            result = self.build(parent, filings=(receipt,))
        self.assertEqual(result.status, d.DossierStatus.CAPTURED_TEMPORAL_EVIDENCE_DOSSIER)
        self.assertEqual(before_submissions, {str(path.relative_to(self.submissions.root)): path.read_bytes()
                                              for path in self.submissions.root.rglob("*") if path.is_file()})
        self.assertEqual(before_filings, {str(path.relative_to(self.filings.root)): path.read_bytes()
                                         for path in self.filings.root.rglob("*") if path.is_file()})

    def test_domain_separated_deterministic_identities(self):
        result = self.build(self.parent(), filings=(self.filing(),))
        entry, capture = result.filings[0], result.filings[0].captures[0]
        identities = {result.semantic_id, result.evidence_id, entry.semantic_id,
                      entry.evidence_id, capture.semantic_id, capture.evidence_id}
        self.assertEqual(len(identities), 6)
        self.assertTrue(all(len(identity) == 64 for identity in identities))


class TemporalDossierBoundaryTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_reverse_consumers(self):
        root_dir = Path(__file__).resolve().parents[1]
        module = root_dir / "economic_facts/sec_property4_temporal_dossier.py"
        allowed_stdlib = {"dataclasses", "datetime", "enum", "re"}
        allowed_relative = {"sec_submissions_archive", "sec_submissions_inventory",
                            "sec_filing_archive", "sec_registered_securities",
                            "sec_class_eps_claims", "sec_primary_document"}
        for node in ast.walk(ast.parse(module.read_text())):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed_stdlib for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertTrue((node.level == 1 and node.module in allowed_relative)
                                or (node.level == 0 and node.module in allowed_stdlib))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotIn(node.func.id, {"open", "float", "eval", "exec", "__import__"})
        for path in [root_dir / "main.py", *(root_dir / "src").rglob("*.py"),
                     *(root_dir / "pit_comparison").rglob("*.py"),
                     *(root_dir / "scripts").rglob("*.py")]:
            self.assertNotIn("sec_property4_temporal_dossier", path.read_text(), str(path))

    def test_contract_documents_all_unresolved_properties_and_handoff(self):
        text = (Path(__file__).resolve().parents[1] / "EXPECTED_RETURN_PR4D4A.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in ("Obligations 5–7 remain unresolved", "acceptanceDateTime != published_at",
                       "Reference closure is not historical completeness",
                       "dossier is not continuity", "D1", "D2C", "separately reviewed"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
