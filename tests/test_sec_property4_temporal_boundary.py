"""PR4D4B fictional, offline, deterministic temporal-boundary tests."""
import ast
from dataclasses import FrozenInstanceError, asdict, fields, replace
import inspect
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_property4_temporal_boundary as b
from economic_facts import sec_property4_temporal_dossier as d4a
from economic_facts.current_authority import AssessmentStatus
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_eps_series import ResolutionMode
from economic_facts.sec_filing_archive import FilingArchiveError, SecFilingArchive
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.source_authority import PublicationSemantics
from tests.sec_eps_series_fixtures import annual_rows
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    BOUNDARY_T2,
    POST_BOUNDARY_CAPTURE,
    PRE_BOUNDARY_CAPTURE,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import ACCESSION, CIK, FILENAME, combined_submission
from tests.sec_submissions_fixtures import root, row


def source_row(number=1, **changes):
    return row(number, **{**{"accessionNumber": f"0000000001-26-{number:06d}",
                             "primaryDocument": FILENAME}, **changes})


class TemporalBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")

    def current(self, *, boundary=BOUNDARY_T1, live=True, cik=CIK, rows=None, mode=None):
        receipt = capture_current(self.current_archive, cik=cik, boundary=boundary,
                                  live=live, rows=rows)
        return current_request(receipt, cik=cik,
                               mode=ResolutionMode.CURRENT_AS_REPORTED if mode is None else mode)

    def parent(self, *, rows=None, cik=CIK):
        return self.submissions_archive._capture_live(
            root([source_row()] if rows is None else rows), cik=cik,
            captured_at="2026-09-20T12:00:00Z")

    def filing(self, *, accession=ACCESSION, cik=CIK, captured_at=PRE_BOUNDARY_CAPTURE,
               form="10-K", raw_bytes=None, **inline_changes):
        payload = (combined_submission(cik=cik, accession=accession, form=form,
                                       **inline_changes)
                   if raw_bytes is None else raw_bytes)
        return self.filing_archive._capture_live(
            payload, cik=cik, accession=accession, captured_at=captured_at)

    def request(self, current_request, parent, *, filings=(), children=()):
        return b.SecProperty4TemporalBoundaryRequest(
            current_request,
            parent.receipt_id,
            tuple(child.receipt_id for child in children),
            tuple(receipt.receipt_id for receipt in filings),
        )

    def assess(self, *, current_request=None, parent=None, filings=None):
        current_request = self.current() if current_request is None else current_request
        parent = self.parent() if parent is None else parent
        filings = (self.filing(),) if filings is None else filings
        return b.assess_sec_property4_temporal_boundary(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.request(current_request, parent, filings=filings),
        )

    def test_valid_d1_and_d4a_are_replayed_into_narrow_boundary_state(self):
        result = self.assess()
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED)
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertEqual(result.source_cik, CIK)
        self.assertEqual(result.series_evidence_horizon_start, "2020-01-01")
        self.assertEqual(result.series_evidence_horizon_end, "2024-12-31")
        filing = result.filings[0]
        self.assertEqual(filing.status, b.FilingBoundaryStatus.CONTROLLED_CAPTURE_BY_BOUNDARY)
        self.assertEqual([capture.receipt.captured_at
                          for capture in filing.controlled_captures_by_boundary],
                         [PRE_BOUNDARY_CAPTURE])
        self.assertFalse(hasattr(result, "continuity"))

    def test_both_upstream_chains_are_internally_replayed(self):
        current, parent, filing = self.current(), self.parent(), self.filing()
        request = self.request(current, parent, filings=(filing,))
        with patch.object(b, "assess_sec_current_evidence",
                          wraps=b.assess_sec_current_evidence) as d1, \
             patch.object(b, "build_sec_property4_temporal_dossier",
                          wraps=b.build_sec_property4_temporal_dossier) as dossier:
            result = b.assess_sec_property4_temporal_boundary(
                self.current_archive, self.submissions_archive, self.filing_archive, request)
        d1.assert_called_once_with(self.current_archive, current)
        self.assertEqual(dossier.call_count, 1)
        self.assertIsInstance(result.current_evidence, b.SecCurrentEvidenceAssessment)
        self.assertIsInstance(result.temporal_dossier, d4a.SecProperty4TemporalDossier)

    def test_exact_cik_join_is_required_without_fuzzy_fallback(self):
        current = self.current(cik="0000000000")
        with self.assertRaises(b.SecProperty4TemporalBoundaryRequestError):
            self.assess(current_request=current)

    def test_offline_and_historical_d1_are_explicitly_unavailable(self):
        cases = (
            self.current(live=False),
            self.current(mode=ResolutionMode.HISTORICAL_AS_OF),
        )
        for current in cases:
            with self.subTest(mode=current.mode):
                result = self.assess(current_request=current)
                self.assertEqual(result.status,
                                 b.BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE)
                self.assertIsNone(result.current_authority_boundary)
                self.assertIn(b.BoundaryIssue.D1_CURRENT_AUTHORITY_UNAVAILABLE, result.issues)
                self.assertEqual(result.filings[0].status,
                                 b.FilingBoundaryStatus.CURRENT_AUTHORITY_UNAVAILABLE)
                self.assertEqual(len(result.filings[0].unclassified_captures), 1)

    def test_unresolved_live_d1_is_unavailable_not_a_manufactured_boundary(self):
        result = self.assess(current_request=self.current(rows=annual_rows()[:-1]))
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE)
        self.assertIsNone(result.current_authority_boundary)

    def test_d4a_source_conflict_propagates_without_a_winner(self):
        first = self.filing(symbol="LEFT")
        second = self.filing(symbol="RIGHT", captured_at="2026-02-03T12:00:00Z")
        result = self.assess(filings=(first, second))
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(b.BoundaryIssue.D4A_SOURCE_CONFLICT, result.issues)
        self.assertEqual(len(result.filings[0].controlled_captures_by_boundary), 2)

    def test_d4a_incomplete_and_no_relevant_states_remain_distinct(self):
        incomplete = self.assess(filings=())
        self.assertEqual(incomplete.status,
                         b.BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE)
        self.assertIn(b.BoundaryIssue.D4A_TEMPORAL_DOSSIER_INCOMPLETE,
                      incomplete.issues)
        parent = self.parent(rows=[source_row(form="8-K")])
        absent = self.assess(parent=parent, filings=())
        self.assertEqual(absent.status,
                         b.BoundaryAssessmentStatus.NO_RELEVANT_PERIODIC_FILINGS)
        self.assertIn(b.BoundaryIssue.NO_RELEVANT_PERIODIC_FILINGS, absent.issues)

    def test_capture_exactly_at_boundary_qualifies(self):
        result = self.assess(filings=(self.filing(captured_at=BOUNDARY_T1),))
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED)
        self.assertEqual(len(result.filings[0].controlled_captures_by_boundary), 1)

    def test_post_boundary_capture_cannot_retroactively_repair_gap(self):
        receipt = self.filing(captured_at=POST_BOUNDARY_CAPTURE)
        result = self.assess(filings=(receipt,))
        self.assertEqual(result.status,
                         b.BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE)
        filing = result.filings[0]
        self.assertEqual(filing.controlled_captures_by_boundary, ())
        self.assertEqual([item.receipt.receipt_id for item in filing.post_boundary_captures],
                         [receipt.receipt_id])
        self.assertIn(b.BoundaryIssue.NO_CAPTURE_BY_CURRENT_BOUNDARY, filing.issues)

    def test_new_later_d1_boundary_can_include_same_exact_archive_capture(self):
        receipt = self.filing(captured_at=POST_BOUNDARY_CAPTURE)
        early = self.assess(current_request=self.current(boundary=BOUNDARY_T1),
                            filings=(receipt,))
        later = self.assess(current_request=self.current(boundary=BOUNDARY_T2),
                            filings=(receipt,))
        self.assertEqual(early.status, b.BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE)
        self.assertEqual(later.status, b.BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED)
        self.assertNotEqual(early.semantic_id, later.semantic_id)
        self.assertEqual(early.current_authority_boundary, BOUNDARY_T1)

    def test_identical_recaptures_do_not_strengthen_semantics(self):
        first = self.filing(captured_at=PRE_BOUNDARY_CAPTURE)
        later = self.filing(captured_at=POST_BOUNDARY_CAPTURE)
        one = self.assess(filings=(first,))
        two = self.assess(filings=(later, first))
        self.assertEqual(one.semantic_id, two.semantic_id)
        self.assertNotEqual(one.evidence_id, two.evidence_id)
        self.assertEqual(one.filings[0].semantic_capture_claims_observed_by_boundary,
                         two.filings[0].semantic_capture_claims_observed_by_boundary)
        self.assertEqual(len(two.filings[0].post_boundary_captures), 1)

    def test_identical_multiple_pre_boundary_recaptures_keep_semantics(self):
        first = self.filing(captured_at="2026-02-02T12:00:00Z")
        second = self.filing(captured_at="2026-02-03T12:00:00Z")
        one = self.assess(filings=(first,))
        two = self.assess(filings=(second, first))
        self.assertEqual(one.semantic_id, two.semantic_id)
        self.assertNotEqual(one.evidence_id, two.evidence_id)
        self.assertEqual(len(two.filings[0].controlled_captures_by_boundary), 2)
        self.assertEqual(len(two.filings[0].semantic_capture_claims_observed_by_boundary), 1)

    def test_source_acceptance_before_capture_is_normal_chronology(self):
        result = self.assess()
        self.assertNotIn(b.BoundaryIssue.CAPTURE_PRECEDES_SOURCE_ACCEPTANCE, result.issues)
        event = result.filings[0].source_acceptance_events[0]
        self.assertEqual(event.relation,
                         b.SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY)

    def test_capture_preceding_source_acceptance_is_source_conflict(self):
        parent = self.parent(rows=[source_row(
            acceptanceDateTime="2026-02-02T13:00:00Z")])
        receipt = self.filing(captured_at="2026-02-02T12:00:00Z")
        result = self.assess(parent=parent, filings=(receipt,))
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(b.BoundaryIssue.CAPTURE_PRECEDES_SOURCE_ACCEPTANCE, result.issues)

    def test_genuinely_post_boundary_source_event_is_visible_but_excluded(self):
        parent = self.parent(rows=[source_row(
            filingDate="2026-04-01", reportDate="2026-03-31",
            acceptanceDateTime="2026-04-01T15:30:00Z")])
        receipt = self.filing(captured_at=POST_BOUNDARY_CAPTURE)
        result = self.assess(parent=parent, filings=(receipt,))
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED)
        filing = result.filings[0]
        self.assertEqual(filing.status, b.FilingBoundaryStatus.POST_BOUNDARY_SOURCE_EVENT)
        self.assertIn(b.BoundaryIssue.SOURCE_ACCEPTANCE_AFTER_CURRENT_BOUNDARY,
                      filing.issues)
        self.assertEqual(filing.controlled_captures_by_boundary, ())
        self.assertEqual(len(filing.post_boundary_captures), 1)

    def test_acceptance_before_t_without_capture_by_t_is_insufficient(self):
        result = self.assess(filings=(self.filing(captured_at=POST_BOUNDARY_CAPTURE),))
        event = result.filings[0].source_acceptance_events[0]
        self.assertEqual(event.relation,
                         b.SourceEventBoundaryRelation.ON_OR_BEFORE_CURRENT_BOUNDARY)
        self.assertEqual(result.filings[0].status,
                         b.FilingBoundaryStatus.NO_CONTROLLED_CAPTURE_BY_BOUNDARY)

    def test_filing_and_report_dates_never_substitute_for_capture(self):
        parent = self.parent(rows=[source_row(
            filingDate="2020-01-01", reportDate="2019-12-31",
            acceptanceDateTime="2026-02-01T15:30:00Z")])
        result = self.assess(parent=parent,
                             filings=(self.filing(captured_at=POST_BOUNDARY_CAPTURE),))
        self.assertEqual(result.status,
                         b.BoundaryAssessmentStatus.INCOMPLETE_BOUNDARY_EVIDENCE)
        self.assertEqual(result.filings[0].controlled_captures_by_boundary, ())

    def test_d1_boundary_remains_capture_bound_and_publication_unknown(self):
        result = self.assess()
        authority = result.current_evidence.current_authority
        self.assertEqual(authority.current_authority_boundary,
                         authority.observed_available_by)
        self.assertEqual(authority.current_authority_boundary,
                         result.current_evidence.receipt.captured_at)
        self.assertIs(authority.publication, PublicationSemantics.UNKNOWN)
        self.assertFalse(hasattr(result, "published_at"))
        self.assertFalse(hasattr(result, "available_at"))

    def test_request_order_does_not_change_result_or_identities(self):
        parent = self.parent()
        first = self.filing(captured_at=PRE_BOUNDARY_CAPTURE)
        second = self.filing(captured_at="2026-02-03T12:00:00Z")
        current = self.current()
        left = b.assess_sec_property4_temporal_boundary(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.request(current, parent, filings=(first, second)))
        right = b.assess_sec_property4_temporal_boundary(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.request(current, parent, filings=(second, first)))
        self.assertEqual(left, right)
        self.assertEqual((left.semantic_id, left.evidence_id),
                         (right.semantic_id, right.evidence_id))

    def test_exact_public_api_and_request_closure(self):
        self.assertEqual(tuple(inspect.signature(
            b.assess_sec_property4_temporal_boundary).parameters),
            ("current_archive", "submissions_archive", "filing_archive", "request"))
        self.assertEqual({field.name for field in fields(b.SecProperty4TemporalBoundaryRequest)}, {
            "current_request", "parent_submissions_receipt_id",
            "child_submissions_receipt_ids", "filing_receipt_ids"})
        current, parent = self.current(), self.parent()
        for keyword in ("boundary", "as_of", "published_at", "available_at", "cik",
                        "ticker", "continuity", "qualified", "complete", "raw"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                b.SecProperty4TemporalBoundaryRequest(current, parent.receipt_id,
                                                      **{keyword: "forbidden"})

    def test_prebuilt_assessments_and_dossiers_cannot_enter_request(self):
        current, parent, receipt = self.current(), self.parent(), self.filing()
        result = self.assess(current_request=current, parent=parent, filings=(receipt,))
        for value in (result.current_evidence, result.temporal_dossier, asdict(current), "x"):
            with self.subTest(value=type(value)), \
                 self.assertRaises(b.SecProperty4TemporalBoundaryRequestError):
                b.SecProperty4TemporalBoundaryRequest(value, parent.receipt_id)

    def test_records_are_frozen_slotted_and_non_economic(self):
        result = self.assess()
        forbidden = {"issuer_id", "security_id", "class_id", "listing_id", "continuity",
                     "complete", "qualified", "admitted", "published_at", "available_at",
                     "quote_currency", "entitled", "applicable"}
        for record in (b.SecProperty4TemporalBoundaryRequest,
                       b.SourceAcceptanceBoundaryEvidence,
                       b.TemporalBoundaryFilingEvidence,
                       b.SecProperty4TemporalBoundaryAssessment):
            self.assertTrue(hasattr(record, "__slots__"))
            self.assertTrue(forbidden.isdisjoint(record.__dataclass_fields__))
        with self.assertRaises(FrozenInstanceError):
            result.status = b.BoundaryAssessmentStatus.SOURCE_CONFLICT

    def test_internal_d1_inconsistency_fails_as_contract_error(self):
        current, parent, receipt = self.current(), self.parent(), self.filing()
        valid = b.assess_sec_current_evidence(self.current_archive, current)
        broken = replace(valid, current_authority=replace(
            valid.current_authority, observed_available_by=BOUNDARY_T2))
        with patch.object(b, "assess_sec_current_evidence", return_value=broken), \
             self.assertRaises(b.SecProperty4TemporalBoundaryContractError):
            b.assess_sec_property4_temporal_boundary(
                self.current_archive, self.submissions_archive, self.filing_archive,
                self.request(current, parent, filings=(receipt,)))

    def test_archive_corruption_and_programming_errors_propagate(self):
        current, parent, receipt = self.current(), self.parent(), self.filing()
        target = self.filing_archive.root / "objects" / receipt.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"x" * receipt.byte_length)
        with self.assertRaises(FilingArchiveError):
            self.assess(current_request=current, parent=parent, filings=(receipt,))
        with patch.object(b, "assess_sec_current_evidence",
                          side_effect=RuntimeError("programming defect")), \
             self.assertRaises(RuntimeError):
            b.assess_sec_property4_temporal_boundary(
                self.current_archive, self.submissions_archive, self.filing_archive,
                self.request(current, parent))

    def test_no_network_writes_directory_discovery_or_current_clock(self):
        current, parent, receipt = self.current(), self.parent(), self.filing()
        request = self.request(current, parent, filings=(receipt,))
        real_fromisoformat = __import__("datetime").datetime.fromisoformat
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(os, "mkdir", side_effect=AssertionError("write")), \
             patch.object(os, "scandir", side_effect=AssertionError("discovery")), \
             patch.object(b, "datetime", side_effect=AssertionError("clock")):
            b.datetime.fromisoformat.side_effect = real_fromisoformat
            result = b.assess_sec_property4_temporal_boundary(
                self.current_archive, self.submissions_archive, self.filing_archive, request)
        self.assertEqual(result.status, b.BoundaryAssessmentStatus.BOUNDARY_EVIDENCE_ESTABLISHED)

    def test_domain_separated_deterministic_identities(self):
        result = self.assess()
        identities = {result.semantic_id, result.evidence_id,
                      result.filings[0].semantic_id, result.filings[0].evidence_id}
        self.assertEqual(len(identities), 4)
        self.assertTrue(all(len(value) == 64 for value in identities))


class TemporalBoundaryDependencyTests(unittest.TestCase):
    def test_dependency_direction_excludes_d2c_synthetic_identity_models_and_clocks(self):
        root_dir = Path(__file__).resolve().parents[1]
        module = root_dir / "economic_facts/sec_property4_temporal_boundary.py"
        tree = ast.parse(module.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module)
            if isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {"now", "today", "open", "float", "eval", "exec"})
        joined = " ".join(name or "" for name in imported)
        for forbidden in ("nasdaq_listed", "security_identity", "expected_return", "src",
                          "main", "allocation", "runtime"):
            self.assertNotIn(forbidden, joined)
        for path in [root_dir / "main.py", *(root_dir / "src").rglob("*.py"),
                     *(root_dir / "pit_comparison").rglob("*.py"),
                     *(root_dir / "scripts").rglob("*.py")]:
            self.assertNotIn("sec_property4_temporal_boundary", path.read_text(), str(path))

    def test_contract_keeps_all_property_and_obligation_boundaries_unresolved(self):
        text = (Path(__file__).resolve().parents[1] / "EXPECTED_RETURN_PR4D4B.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in ("Obligations 5–7 remain unresolved",
                       "Reference closure is not historical completeness",
                       "acceptanceDateTime != publication",
                       "No D2C", "No synthetic identity", "AuthorityProperty",
                       "separately reviewed"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
