"""Deterministic PR4D4C2 CURRENT SEC/Nasdaq source-bridge tests."""
import ast
from dataclasses import FrozenInstanceError, fields
import inspect
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import sec_current_registered_listing_bridge as bridge
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive, NasdaqListedArchiveError
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_property4_temporal_boundary import SecProperty4TemporalBoundaryRequest
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_ticker_exchange_archive import (
    SecTickerExchangeArchive,
    SecTickerExchangeArchiveError,
)
from tests.nasdaq_listed_fixtures import row as nasdaq_row
from tests.sec_current_registered_listing_bridge_fixtures import (
    NASDAQ_CAPTURE,
    SEC_CAPTURE,
    nasdaq_snapshot,
    registered_submission,
    sec_snapshot,
)
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    BOUNDARY_T2,
    POST_BOUNDARY_CAPTURE,
    PRE_BOUNDARY_CAPTURE,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import ACCESSION, CIK, FILENAME
from tests.sec_submissions_fixtures import root, row
from tests.sec_ticker_exchange_fixtures import row as sec_row


def source_row(number=1, **changes):
    return row(number, **{**{"accessionNumber": f"0000000001-26-{number:06d}",
                             "primaryDocument": FILENAME}, **changes})


class CurrentRegisteredListingBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name).resolve()
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")
        self.sec_archive = SecTickerExchangeArchive(base / "sec-associations")
        self.nasdaq_archive = NasdaqListedArchive(base / "nasdaq")

    def current(self, *, boundary=BOUNDARY_T1, live=True):
        receipt = capture_current(self.current_archive, boundary=boundary, live=live)
        return current_request(receipt)

    def parent(self, *, rows=None):
        return self.submissions_archive._capture_live(
            root([source_row()] if rows is None else rows), cik=CIK,
            captured_at="2026-09-20T12:00:00Z")

    def filing(self, *, accession=ACCESSION, captured_at=PRE_BOUNDARY_CAPTURE,
               symbol="FICT", exchange="NASDAQ", title="Class A Common Stock",
               form="10-K", raw_bytes=None, **changes):
        payload = (registered_submission(symbol=symbol, exchange=exchange, title=title,
                                         accession=accession, form=form, **changes)
                   if raw_bytes is None else raw_bytes)
        return self.filing_archive._capture_live(
            payload, cik=CIK, accession=accession, captured_at=captured_at)

    def sec(self, *, captured_at=SEC_CAPTURE, raw_bytes=None, **changes):
        payload = sec_snapshot(**changes) if raw_bytes is None else raw_bytes
        return self.sec_archive._capture_live(payload, captured_at=captured_at)

    def nasdaq(self, *, captured_at=NASDAQ_CAPTURE, raw_bytes=None, **changes):
        payload = nasdaq_snapshot(**changes) if raw_bytes is None else raw_bytes
        return self.nasdaq_archive._capture_live(payload, captured_at=captured_at)

    def request(self, current, parent, sec, nasdaq, *, filings=(), children=()):
        temporal = SecProperty4TemporalBoundaryRequest(
            current,
            parent.receipt_id,
            tuple(child.receipt_id for child in children),
            tuple(receipt.receipt_id for receipt in filings),
        )
        return bridge.SecCurrentRegisteredListingBridgeRequest(
            temporal, sec.receipt_id, nasdaq.receipt_id)

    def assess(self, *, current=None, parent=None, filings=None, sec=None, nasdaq=None):
        current = self.current() if current is None else current
        parent = self.parent() if parent is None else parent
        filings = (self.filing(),) if filings is None else filings
        sec = self.sec() if sec is None else sec
        nasdaq = self.nasdaq() if nasdaq is None else nasdaq
        return bridge.assess_sec_current_registered_listing_bridge(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive,
            self.request(current, parent, sec, nasdaq, filings=filings),
        )

    def test_exact_reviewed_profile_establishes_only_current_source_bridge(self):
        result = self.assess()
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
        self.assertEqual(result.profile,
                         bridge.SEC_NASDAQ_REGISTERED_LISTING_BRIDGE_V1)
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertEqual((candidate.source_cik, candidate.source_symbol), (CIK, "FICT"))
        self.assertEqual(candidate.d3a_titles, ("Class A Common Stock",))
        self.assertEqual(candidate.supporting_accessions, (ACCESSION,))
        self.assertIsNotNone(candidate.sec_association_row_semantic_id)
        self.assertIsNotNone(candidate.nasdaq_row_semantic_id)
        self.assertEqual(candidate.issues, ())

    def test_public_api_request_is_closed_and_caller_cannot_choose_target(self):
        self.assertEqual(tuple(inspect.signature(
            bridge.assess_sec_current_registered_listing_bridge).parameters), (
                "current_archive", "submissions_archive", "filing_archive",
                "ticker_exchange_archive", "nasdaq_listed_archive", "request"))
        self.assertEqual(tuple(field.name for field in fields(
            bridge.SecCurrentRegisteredListingBridgeRequest)), (
                "temporal_boundary_request", "sec_ticker_exchange_receipt_id",
                "nasdaq_listed_receipt_id"))
        current, parent, filing, sec, nasdaq = (
            self.current(), self.parent(), self.filing(), self.sec(), self.nasdaq())
        temporal = self.request(current, parent, sec, nasdaq, filings=(filing,)).temporal_boundary_request
        for keyword in ("cik", "ticker", "exchange", "security_title", "as_of",
                        "qualified", "admitted", "assessment", "source_bytes"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                bridge.SecCurrentRegisteredListingBridgeRequest(
                    temporal, sec.receipt_id, nasdaq.receipt_id,
                    **{keyword: "forbidden"})

    def test_prebuilt_upstream_outputs_cannot_bypass_receipt_replay(self):
        result = self.assess()
        for value in (result.temporal_boundary, result.sec_ticker_exchange_snapshot,
                      result.nasdaq_listed_snapshot, result):
            with self.subTest(value=type(value)), \
                 self.assertRaises(bridge.SecCurrentRegisteredListingBridgeRequestError):
                bridge.SecCurrentRegisteredListingBridgeRequest(
                    value, "0" * 64, "1" * 64)

    def test_all_three_upstream_assessments_are_freshly_replayed(self):
        current, parent, filing, sec, nasdaq = (
            self.current(), self.parent(), self.filing(), self.sec(), self.nasdaq())
        request = self.request(current, parent, sec, nasdaq, filings=(filing,))
        with patch.object(bridge, "assess_sec_property4_temporal_boundary",
                          wraps=bridge.assess_sec_property4_temporal_boundary) as d4b, \
             patch.object(bridge, "replay_sec_ticker_exchange_snapshot",
                          wraps=bridge.replay_sec_ticker_exchange_snapshot) as d4c1, \
             patch.object(bridge, "replay_nasdaq_listed_snapshot",
                          wraps=bridge.replay_nasdaq_listed_snapshot) as d2c:
            result = bridge.assess_sec_current_registered_listing_bridge(
                self.current_archive, self.submissions_archive, self.filing_archive,
                self.sec_archive, self.nasdaq_archive, request)
        self.assertEqual((d4b.call_count, d4c1.call_count, d2c.call_count), (1, 1, 1))
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)

    def test_auxiliary_captures_before_or_exactly_at_t_are_eligible(self):
        for timestamp in ("2026-02-28T23:59:59Z", BOUNDARY_T1):
            with self.subTest(timestamp=timestamp):
                result = self.assess(sec=self.sec(captured_at=timestamp),
                                     nasdaq=self.nasdaq(captured_at=timestamp))
                self.assertEqual(result.status,
                                 bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)

    def test_auxiliary_capture_after_t_cannot_repair_earlier_assessment(self):
        later_sec = self.sec(captured_at=POST_BOUNDARY_CAPTURE)
        later_nasdaq = self.nasdaq(captured_at=POST_BOUNDARY_CAPTURE)
        early = self.assess(sec=later_sec, nasdaq=later_nasdaq)
        self.assertEqual(early.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
        self.assertIn(bridge.BridgeIssue.SEC_ASSOCIATION_CAPTURE_AFTER_BOUNDARY, early.issues)
        self.assertIn(bridge.BridgeIssue.NASDAQ_CAPTURE_AFTER_BOUNDARY, early.issues)
        candidate = early.candidates[0]
        self.assertIsNone(candidate.sec_association_row_semantic_id)
        self.assertIsNone(candidate.nasdaq_row_semantic_id)

    def test_later_d1_boundary_may_use_same_auxiliary_evidence(self):
        later_sec = self.sec(captured_at=POST_BOUNDARY_CAPTURE)
        later_nasdaq = self.nasdaq(captured_at=POST_BOUNDARY_CAPTURE)
        filing = self.filing()
        early = self.assess(current=self.current(boundary=BOUNDARY_T1), filings=(filing,),
                            sec=later_sec, nasdaq=later_nasdaq)
        later = self.assess(current=self.current(boundary=BOUNDARY_T2), filings=(filing,),
                            sec=later_sec, nasdaq=later_nasdaq)
        self.assertEqual(early.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
        self.assertEqual(later.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
        self.assertNotEqual(early.semantic_id, later.semantic_id)

    def test_d4b_unavailable_incomplete_and_conflict_remain_distinct(self):
        unavailable = self.assess(current=self.current(live=False))
        self.assertEqual(unavailable.status,
                         bridge.BridgeAssessmentStatus.CURRENT_AUTHORITY_UNAVAILABLE)
        self.assertIn(bridge.BridgeIssue.D4B_CURRENT_BOUNDARY_UNAVAILABLE,
                      unavailable.issues)
        incomplete = self.assess(filings=())
        self.assertEqual(incomplete.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
        self.assertIn(bridge.BridgeIssue.D4B_BOUNDARY_EVIDENCE_INCOMPLETE,
                      incomplete.issues)
        conflicting = self.assess(filings=(
            self.filing(symbol="FICT"),
            self.filing(symbol="OTHER", captured_at="2026-02-03T12:00:00Z"),
        ))
        self.assertEqual(conflicting.status, bridge.BridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(bridge.BridgeIssue.D4B_SOURCE_CONFLICT, conflicting.issues)

    def test_no_relevant_periodic_filing_has_no_supported_candidate(self):
        parent = self.parent(rows=[source_row(form="8-K")])
        result = self.assess(parent=parent, filings=())
        self.assertEqual(
            result.status,
            bridge.BridgeAssessmentStatus.NO_SUPPORTED_REGISTERED_LISTING_CANDIDATE)
        self.assertEqual(result.candidates, ())

    def test_only_controlled_by_t_d3a_claims_participate(self):
        post = self.filing(captured_at=POST_BOUNDARY_CAPTURE)
        result = self.assess(filings=(post,))
        self.assertEqual(result.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.temporal_boundary.filings[0].controlled_captures_by_boundary, ())

    def test_d3a_incomplete_conflict_no_symbol_and_no_claim_are_not_repaired(self):
        missing_exchange = registered_submission().replace(
            b'<ix:nonNumeric name="dei:SecurityExchangeName" contextRef="registered">NASDAQ</ix:nonNumeric>',
            b"")
        conflict = registered_submission().replace(
            b'</body>', b'<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered">OTHER</ix:nonNumeric></body>')
        no_symbol = registered_submission().replace(
            b'<ix:nonNumeric name="dei:TradingSymbol" contextRef="registered">FICT</ix:nonNumeric>',
            b'<ix:nonNumeric name="dei:NoTradingSymbolFlag" contextRef="registered">true</ix:nonNumeric>')
        no_claim = registered_submission(include_registered=False)
        cases = (
            (missing_exchange, bridge.BridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE),
            (conflict, bridge.BridgeIssue.D3A_REGISTERED_SECURITY_CONFLICT),
            (no_symbol, bridge.BridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE),
            (no_claim, bridge.BridgeIssue.D3A_NO_SUPPORTED_REGISTERED_SECURITY),
        )
        for raw_bytes, expected in cases:
            with self.subTest(expected=expected):
                result = self.assess(filings=(self.filing(raw_bytes=raw_bytes),))
                self.assertNotEqual(result.status,
                                    bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
                self.assertIn(expected, result.issues)

    def test_exchange_profile_is_exact_finite_and_not_fuzzy(self):
        for exchange in ("Nasdaq", "NASDAQ Global Select", "xNASDAQ", " NASDAQ "):
            with self.subTest(exchange=exchange):
                result = self.assess(filings=(self.filing(exchange=exchange),))
                self.assertEqual(result.status,
                                 bridge.BridgeAssessmentStatus.UNSUPPORTED_SOURCE_PROFILE)
                self.assertIn(bridge.BridgeIssue.UNSUPPORTED_D3A_EXCHANGE_PROFILE,
                              result.issues)

    def test_sec_association_requires_exact_cik_symbol_and_exchange(self):
        cases = (
            (sec_snapshot(cik=124), bridge.BridgeIssue.NO_MATCHING_SEC_ASSOCIATION),
            (sec_snapshot(symbol="OTHER"), bridge.BridgeIssue.NO_MATCHING_SEC_ASSOCIATION),
            (sec_snapshot(exchange="NASDAQ"), bridge.BridgeIssue.NO_MATCHING_SEC_ASSOCIATION),
        )
        for raw_bytes, issue in cases:
            with self.subTest(raw=raw_bytes):
                result = self.assess(sec=self.sec(raw_bytes=raw_bytes))
                self.assertEqual(result.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
                self.assertIn(issue, result.issues)

    def test_sec_target_duplicate_occurrences_preserve_evidence_not_semantics(self):
        single = self.assess(sec=self.sec(raw_bytes=sec_snapshot()))
        duplicate_rows = [sec_row(123, "FICTIONAL D4C2 CORP", "FICT", "Nasdaq")] * 2
        duplicate = self.assess(sec=self.sec(raw_bytes=sec_snapshot(rows=duplicate_rows)))
        self.assertEqual(duplicate.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
        self.assertEqual(single.candidates[0].semantic_id, duplicate.candidates[0].semantic_id)
        self.assertNotEqual(single.candidates[0].evidence_id, duplicate.candidates[0].evidence_id)
        self.assertEqual(single.semantic_id, duplicate.semantic_id)
        self.assertNotEqual(single.evidence_id, duplicate.evidence_id)
        self.assertEqual(len(duplicate.candidates[0].sec_association_occurrence_ids), 2)

    def test_sec_target_semantic_ambiguity_and_cross_cik_ticker_fail_closed(self):
        semantic_rows = [
            sec_row(123, "NAME ONE", "FICT", "Nasdaq"),
            sec_row(123, "NAME TWO", "FICT", "Nasdaq"),
        ]
        ambiguous = self.assess(sec=self.sec(raw_bytes=sec_snapshot(rows=semantic_rows)))
        self.assertEqual(ambiguous.status, bridge.BridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(bridge.BridgeIssue.AMBIGUOUS_SEC_ASSOCIATION, ambiguous.issues)
        cross_cik_rows = [
            sec_row(123, "TARGET", "FICT", "Nasdaq"),
            sec_row(124, "OTHER", "FICT", "Nasdaq"),
        ]
        cross = self.assess(sec=self.sec(raw_bytes=sec_snapshot(rows=cross_cik_rows)))
        self.assertEqual(cross.status, bridge.BridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(bridge.BridgeIssue.SEC_TICKER_CROSS_CIK_AMBIGUITY, cross.issues)

    def test_unrelated_sec_ambiguity_and_other_cik_tickers_do_not_poison_target(self):
        rows = [
            sec_row(123, "TARGET", "FICT", "Nasdaq"),
            sec_row(123, "TARGET", "OTHER", "Nasdaq"),
            sec_row(999, "UNRELATED", "DUP", "Nasdaq"),
            sec_row(999, "UNRELATED", "DUP", "Nasdaq"),
        ]
        result = self.assess(sec=self.sec(raw_bytes=sec_snapshot(rows=rows)))
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)

    def test_nasdaq_symbol_is_exact_unique_and_non_test(self):
        absent = self.assess(nasdaq=self.nasdaq(symbol="OTHER"))
        self.assertIn(bridge.BridgeIssue.NO_MATCHING_NASDAQ_SYMBOL, absent.issues)
        duplicate_rows = [nasdaq_row("FICT"), nasdaq_row("FICT", **{"Security Name": "Different"})]
        duplicate = self.assess(nasdaq=self.nasdaq(
            raw_bytes=nasdaq_snapshot(rows=duplicate_rows)))
        self.assertEqual(duplicate.status, bridge.BridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(bridge.BridgeIssue.AMBIGUOUS_NASDAQ_SYMBOL, duplicate.issues)
        test_issue = self.assess(nasdaq=self.nasdaq(test_issue="Y"))
        self.assertEqual(test_issue.status, bridge.BridgeAssessmentStatus.INCOMPLETE_SOURCE_BRIDGE)
        self.assertIn(bridge.BridgeIssue.NASDAQ_TEST_ISSUE, test_issue.issues)

    def test_unrelated_nasdaq_conflict_is_target_local_only(self):
        rows = [nasdaq_row("FICT"), nasdaq_row("OTHER"), nasdaq_row("OTHER")]
        result = self.assess(nasdaq=self.nasdaq(raw_bytes=nasdaq_snapshot(rows=rows)))
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)

    def test_names_and_descriptive_nasdaq_fields_are_never_join_keys(self):
        result = self.assess(
            sec=self.sec(raw_bytes=sec_snapshot(name="COMPLETELY DIFFERENT SEC NAME")),
            nasdaq=self.nasdaq(security_name="NO RELATION TO FILING TITLE"),
        )
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)

    def test_equivalent_multiple_filings_cohere_without_durable_scope_promotion(self):
        second_accession = "0000000001-26-000002"
        parent = self.parent(rows=[source_row(1), source_row(2)])
        first = self.filing()
        second = self.filing(accession=second_accession,
                             captured_at="2026-02-05T12:00:00Z",
                             title="Common Stock, Class A")
        result = self.assess(parent=parent, filings=(second, first))
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
        candidate = result.candidates[0]
        self.assertEqual(candidate.supporting_accessions, (ACCESSION, second_accession))
        self.assertEqual(candidate.d3a_titles,
                         ("Class A Common Stock", "Common Stock, Class A"))
        self.assertEqual(len(candidate.d3a_filing_source_scopes), 2)
        self.assertFalse(hasattr(candidate, "security_id"))

    def test_repeated_equivalent_filing_relationship_does_not_strengthen_candidate_semantics(self):
        second_accession = "0000000001-26-000002"
        sec, nasdaq = self.sec(), self.nasdaq()
        one = self.assess(parent=self.parent(rows=[source_row(1)]),
                          filings=(self.filing(),), sec=sec, nasdaq=nasdaq)
        repeated = self.assess(
            parent=self.parent(rows=[source_row(1), source_row(2)]),
            filings=(self.filing(), self.filing(
                accession=second_accession, captured_at="2026-02-05T12:00:00Z")),
            sec=sec, nasdaq=nasdaq,
        )
        self.assertEqual(one.candidates[0].semantic_id,
                         repeated.candidates[0].semantic_id)
        self.assertNotEqual(one.candidates[0].evidence_id,
                            repeated.candidates[0].evidence_id)

    def test_amendment_remains_independent_supporting_evidence(self):
        amendment_accession = "0000000001-26-000002"
        parent = self.parent(rows=[source_row(1), source_row(2, form="10-K/A")])
        original = self.filing()
        amendment = self.filing(accession=amendment_accession, form="10-K/A",
                                captured_at="2026-02-05T12:00:00Z")
        result = self.assess(parent=parent, filings=(original, amendment))
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)
        self.assertEqual(result.candidates[0].supporting_accessions,
                         (ACCESSION, amendment_accession))

    def test_multiple_incompatible_filing_candidates_have_no_winner(self):
        second_accession = "0000000001-26-000002"
        parent = self.parent(rows=[source_row(1), source_row(2)])
        first = self.filing()
        second = self.filing(accession=second_accession, symbol="OTHER",
                             captured_at="2026-02-05T12:00:00Z")
        sec_rows = [sec_row(123, "TARGET", "FICT", "Nasdaq"),
                    sec_row(123, "TARGET", "OTHER", "Nasdaq")]
        nasdaq_rows = [nasdaq_row("FICT"), nasdaq_row("OTHER")]
        result = self.assess(
            parent=parent, filings=(first, second),
            sec=self.sec(raw_bytes=sec_snapshot(rows=sec_rows)),
            nasdaq=self.nasdaq(raw_bytes=nasdaq_snapshot(rows=nasdaq_rows)),
        )
        self.assertEqual(result.status, bridge.BridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertEqual(len(result.candidates), 2)
        self.assertIn(bridge.BridgeIssue.MULTIPLE_INCOMPATIBLE_BRIDGE_CANDIDATES,
                      result.issues)

    def test_request_order_and_repeated_filing_evidence_are_canonical(self):
        first = self.filing(captured_at="2026-02-02T12:00:00Z")
        recapture = self.filing(captured_at="2026-02-03T12:00:00Z")
        parent, current, sec, nasdaq = self.parent(), self.current(), self.sec(), self.nasdaq()
        left = bridge.assess_sec_current_registered_listing_bridge(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive,
            self.request(current, parent, sec, nasdaq, filings=(first, recapture)))
        right = bridge.assess_sec_current_registered_listing_bridge(
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive,
            self.request(current, parent, sec, nasdaq, filings=(recapture, first)))
        self.assertEqual(left, right)
        self.assertEqual(left.semantic_id, right.semantic_id)
        self.assertEqual(left.evidence_id, right.evidence_id)
        one = self.assess(current=current, parent=parent, filings=(first,), sec=sec, nasdaq=nasdaq)
        self.assertEqual(one.candidates[0].semantic_id, left.candidates[0].semantic_id)
        self.assertNotEqual(one.candidates[0].evidence_id, left.candidates[0].evidence_id)

    def test_records_are_frozen_slotted_and_expose_no_forbidden_authority(self):
        result = self.assess()
        forbidden = {
            "issuer_id", "security_id", "class_id", "listing_id", "pam_entity_id",
            "pam_security_id", "pam_listing_id", "qualified_listing", "quote_currency",
            "quote_unit", "continuity", "admitted", "mic",
        }
        for record in (bridge.SecCurrentRegisteredListingBridgeRequest,
                       bridge.CurrentRegisteredListingBridgeEvidence,
                       bridge.SecCurrentRegisteredListingBridgeAssessment):
            self.assertTrue(hasattr(record, "__slots__"))
            self.assertTrue(forbidden.isdisjoint(record.__dataclass_fields__))
        with self.assertRaises(FrozenInstanceError):
            result.status = bridge.BridgeAssessmentStatus.SOURCE_CONFLICT

    def test_domain_separated_semantic_and_evidence_identities_are_deterministic(self):
        first = self.assess()
        second = self.assess()
        self.assertEqual(first.semantic_id, second.semantic_id)
        # Separate exact archive receipts have the same capture time and bytes, so
        # their receipt identities and complete evidence identities are equal.
        self.assertEqual(first.evidence_id, second.evidence_id)
        identities = {first.semantic_id, first.evidence_id,
                      first.candidates[0].semantic_id, first.candidates[0].evidence_id}
        self.assertEqual(len(identities), 4)
        self.assertTrue(all(len(value) == 64 for value in identities))

    def test_archive_corruption_and_programming_failures_propagate(self):
        with patch.object(bridge, "replay_nasdaq_listed_snapshot",
                          side_effect=RuntimeError("programming defect")), \
             self.assertRaises(RuntimeError):
            self.assess()
        sec = self.sec()
        target = self.sec_archive.root / "objects" / sec.content_sha256
        target.chmod(0o600)
        target.write_bytes(b"x" * sec.byte_length)
        with self.assertRaises(SecTickerExchangeArchiveError):
            self.assess(sec=sec)

    def test_offline_replay_has_no_network_write_discovery_or_wall_clock(self):
        current, parent, filing, sec, nasdaq = (
            self.current(), self.parent(), self.filing(), self.sec(), self.nasdaq())
        request = self.request(current, parent, sec, nasdaq, filings=(filing,))
        real_fromisoformat = __import__("datetime").datetime.fromisoformat
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(os, "mkdir", side_effect=AssertionError("write")), \
             patch.object(os, "scandir", side_effect=AssertionError("discovery")), \
             patch.object(bridge, "datetime", side_effect=AssertionError("clock")):
            bridge.datetime.fromisoformat.side_effect = real_fromisoformat
            result = bridge.assess_sec_current_registered_listing_bridge(
                self.current_archive, self.submissions_archive, self.filing_archive,
                self.sec_archive, self.nasdaq_archive, request)
        self.assertEqual(result.status,
                         bridge.BridgeAssessmentStatus.CURRENT_SOURCE_BRIDGE_ESTABLISHED)


class CurrentRegisteredListingBridgeDependencyTests(unittest.TestCase):
    def test_dependency_direction_has_no_synthetic_identity_authority_or_consumers(self):
        root_dir = Path(__file__).resolve().parents[1]
        module = root_dir / "economic_facts/sec_current_registered_listing_bridge.py"
        tree = ast.parse(module.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
            if isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {"now", "today", "open", "float", "eval", "exec"})
        joined = " ".join(imported)
        for forbidden in ("security_identity", "source_authority", "expected_return",
                          "src", "main", "allocation", "runtime"):
            self.assertNotIn(forbidden, joined)
        for path in [root_dir / "main.py", *(root_dir / "src").rglob("*.py"),
                     *(root_dir / "pit_comparison").rglob("*.py"),
                     *(root_dir / "scripts").rglob("*.py")]:
            self.assertNotIn("sec_current_registered_listing_bridge", path.read_text(), str(path))

    def test_contract_keeps_property4_and_obligations_unresolved(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "contracts" / "v2"
                / "expected_return" / "EXPECTED_RETURN_PR4D4C2.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in ("Obligations 5–7 remain unresolved", "no quote currency",
                       "No D2B parent metadata", "Cross-source corroboration",
                       "durable economic identity", "separately reviewed"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
