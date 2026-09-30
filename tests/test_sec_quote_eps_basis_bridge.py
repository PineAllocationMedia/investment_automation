from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from economic_facts import sec_quote_eps_basis_bridge as bridge
from economic_facts import yahoo_current_quote as quote
from economic_facts import yahoo_split_history as split_history
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from economic_facts.yahoo_split_history_archive import YahooSplitHistoryArchive
from economic_facts.sec_share_basis_source_claims import (
    SecShareBasisSourceRequest,
    build_sec_share_basis_source_foundation,
)
from tests.sec_current_security_eps_qualification_fixtures import source_rows
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_share_basis_source_claims_fixtures import share_basis_filing
from tests.sec_submissions_fixtures import row as submissions_row
from tests.sec_submissions_fixtures import root as submissions_root
from tests import test_sec_current_eps_comparability_qualification as comparability_tests
from tests.yahoo_quote_fixtures import CAPTURED_AT, MARKET_EPOCH, chart_response
from tests.yahoo_split_history_fixtures import split_chart_response, split_event


class SecQuoteEPSBasisBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        self.quote_archive = YahooQuoteArchive(root / "quotes")
        self.split_archive = YahooSplitHistoryArchive(root / "splits")
        self.comparability = comparability_tests.SecCurrentEPSComparabilityTests(
            methodName="runTest")
        self.comparability.setUp()
        self.addCleanup(self.comparability.doCleanups)

    def build(self, *, split_events=(), action_blocks=(), split_raw=None,
              omit_action_receipts=False, uncaptured_outside_window=False,
              recent_capture=CAPTURED_AT, drop_recent_row_index=None,
              force_recent_inventory=False,
              split_symbol="FICT",
              split_start_delta=0, split_end_delta=0,
              sic=3571, sic_description="Electronic Computers"):
        parent = self.comparability.submissions_archive._capture_live(
            submissions_root(source_rows(), cik=CIK, sic=sic,
                             sicDescription=sic_description),
            cik=CIK, captured_at="2026-02-25T12:00:00Z")
        comparability_request = self.comparability.build_request(parent=parent)
        pr5c = self.comparability.qualify_request(comparability_request)
        quote_receipt = self.quote_archive._capture_live(
            chart_response(), symbol="FICT", captured_at=CAPTURED_AT)
        quote_extraction = quote.extract_yahoo_current_quote(
            self.quote_archive, quote_receipt.receipt_id)
        quote_request = quote.YahooCurrentQuoteQualificationRequest(
            comparability_request.security_eps_request,
            pr5c.upstream_security_eps.semantic_id,
            pr5c.upstream_security_eps.evidence_id,
            quote_receipt.receipt_id,
            quote_extraction.semantic_id,
            quote_extraction.evidence_id,
        )
        qualified_quote = quote.qualify_yahoo_current_quote(
            self.quote_archive,
            self.comparability.current_archive,
            self.comparability.submissions_archive,
            self.comparability.filing_archive,
            self.comparability.sec_archive,
            self.comparability.nasdaq_archive,
            quote_request,
        )
        presentation_row = next(
            item for item in pr5c.upstream_share_basis_source.submissions_inventory.occurrences
            if dict(item.fields)["accessionNumber"] == pr5c.presentation.accession)
        start = int(datetime.fromisoformat(
            dict(presentation_row.fields)["acceptanceDateTime"].replace(
                "Z", "+00:00")).timestamp())
        split_receipt = self.split_archive._capture_live(
            (split_chart_response(symbol=split_symbol, events=split_events)
             if split_raw is None else split_raw),
            symbol=split_symbol,
            start_epoch=start + split_start_delta,
            end_epoch=MARKET_EPOCH + split_end_delta,
            captured_at=CAPTURED_AT,
        )
        split = split_history.extract_yahoo_split_history(
            self.split_archive, split_receipt.receipt_id)
        recent_request = comparability_request.share_basis_source_request
        if (action_blocks or uncaptured_outside_window
                or drop_recent_row_index is not None or force_recent_inventory):
            recent_rows = list(source_rows())
            if drop_recent_row_index is not None:
                del recent_rows[drop_recent_row_index]
            action_receipts = []
            if uncaptured_outside_window:
                recent_rows.append(submissions_row(
                    89,
                    accessionNumber="0000000123-24-000089",
                    filingDate="2024-01-02",
                    reportDate="2023-12-31",
                    acceptanceDateTime="2024-01-02T15:30:00.000Z",
                    form="8-K",
                    primaryDocument="old-action-89.htm",
                    items="8.01",
                    isXBRL=0,
                    isInlineXBRL=0,
                ))
            for index, block in enumerate(action_blocks, start=90):
                accession = f"0000000123-26-{index:06d}"
                accepted = f"2026-01-{index - 89:02d}T15:30:00.000Z"
                recent_rows.append(submissions_row(
                    index,
                    accessionNumber=accession,
                    filingDate=accepted[:10],
                    reportDate="2025-12-31",
                    acceptanceDateTime=accepted,
                    form="8-K",
                    primaryDocument=f"action-{index}.htm",
                    items="8.01",
                    isXBRL=0,
                    isInlineXBRL=0,
                ))
                if not omit_action_receipts:
                    action_receipts.append(
                        self.comparability.filing_archive._capture_live(
                            share_basis_filing(
                                cik=CIK, accession=accession, form="8-K",
                                blocks=(block,)),
                            cik=CIK,
                            accession=accession,
                            captured_at=f"2026-02-20T12:01:{index - 90:02d}Z",
                        ))
            recent_parent = self.comparability.submissions_archive._capture_live(
                submissions_root(
                    recent_rows, cik=CIK, sic=sic, sicDescription=sic_description),
                cik=CIK,
                captured_at=recent_capture,
            )
            route_filing_ids = (
                comparability_request.share_basis_source_request.filing_receipt_ids)
            if drop_recent_row_index is not None:
                recent_accessions = {
                    dict(item)["accessionNumber"] for item in recent_rows
                }
                route_filing_ids = tuple(
                    receipt_id for receipt_id in route_filing_ids
                    if self.comparability.filing_archive.read_receipt(
                        receipt_id).accession in recent_accessions
                )
            recent_request = SecShareBasisSourceRequest(
                recent_parent.receipt_id,
                (),
                (route_filing_ids
                 + tuple(item.receipt_id for item in action_receipts)),
            )
        recent_basis = build_sec_share_basis_source_foundation(
            self.comparability.submissions_archive,
            self.comparability.filing_archive,
            recent_request,
        )
        request = bridge.SecQuoteEPSBasisBridgeRequest(
            comparability_request, pr5c.semantic_id, pr5c.evidence_id,
            quote_request, qualified_quote.semantic_id, qualified_quote.evidence_id,
            recent_request,
            recent_basis.semantic_id, recent_basis.evidence_id,
            split_receipt.receipt_id, split.semantic_id, split.evidence_id,
        )
        return request

    def qualify(self, **changes):
        return bridge.qualify_sec_quote_eps_basis_bridge(
            self.comparability.current_archive,
            self.comparability.submissions_archive,
            self.comparability.filing_archive,
            self.comparability.sec_archive,
            self.comparability.nasdaq_archive,
            self.quote_archive,
            self.split_archive,
            self.build(**changes),
        )

    def test_complete_bounded_no_action_route_establishes_one_to_one(self):
        result = self.qualify()
        self.assertIs(result.status, bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual((result.eps_to_quote_basis_multiplier_numerator,
                          result.eps_to_quote_basis_multiplier_denominator), (1, 1))
        self.assertEqual(result.filing_window_accessions, ())
        self.assertEqual(result.reconciled_actions, ())
        self.assertEqual(result.sec_inventory_snapshot_boundary, CAPTURED_AT)
        self.assertEqual(
            result.route_inventory_semantic_id,
            result.upstream_comparability.upstream_share_basis_source
            .submissions_inventory.semantic_id,
        )
        self.assertIn("NO_UNIVERSAL_CORPORATE_ACTION_COMPLETENESS_CLAIM",
                      result.limitations)

    def test_stale_detached_same_cik_inventory_cannot_establish_one_to_one(self):
        result = self.qualify(
            force_recent_inventory=True,
            recent_capture="2026-02-25T11:59:59Z",
            drop_recent_row_index=0,
        )
        self.assertIs(result.status, bridge.ShareBasisBridgeStatus.SOURCE_CONFLICT)
        self.assertIn(
            bridge.ShareBasisBridgeReason.RECENT_INVENTORY_NOT_MONOTONIC_CONTINUATION,
            result.reasons,
        )
        self.assertIn(
            bridge.ShareBasisBridgeReason.RECENT_SEC_SNAPSHOT_BEFORE_QUOTE_CAPTURE,
            result.reasons,
        )

    def test_monotonic_controlled_newer_inventory_can_establish_one_to_one(self):
        result = self.qualify(
            force_recent_inventory=True,
            recent_capture="2026-02-25T12:30:00Z",
        )
        self.assertIs(
            result.status, bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
        self.assertEqual(result.sec_inventory_snapshot_boundary,
                         "2026-02-25T12:30:00Z")
        self.assertEqual(
            (result.eps_to_quote_basis_multiplier_numerator,
             result.eps_to_quote_basis_multiplier_denominator),
            (1, 1),
        )

    def test_empty_yahoo_alone_cannot_repair_wrong_interval(self):
        result = self.qualify(split_start_delta=1)
        self.assertIs(result.status, bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE)
        self.assertIn(bridge.ShareBasisBridgeReason.SPLIT_HISTORY_INTERVAL_MISMATCH,
                      result.reasons)

    def test_uncaptured_filing_outside_bounded_window_does_not_block(self):
        result = self.qualify(uncaptured_outside_window=True)
        self.assertIs(result.status,
                      bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
        self.assertEqual((result.eps_to_quote_basis_multiplier_numerator,
                          result.eps_to_quote_basis_multiplier_denominator), (1, 1))

    def test_uncorroborated_yahoo_split_blocks(self):
        event = split_event(1767225600, 2, 1)  # 2026-01-01 UTC
        result = self.qualify(split_events=(event,))
        self.assertIs(result.status, bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE)
        self.assertIn(
            bridge.ShareBasisBridgeReason.YAHOO_ACTION_MISSING_SEC_CONFIRMATION,
            result.reasons)

    @staticmethod
    def event(date, numerator, denominator):
        epoch = int(datetime.fromisoformat(date + "T00:00:00+00:00").timestamp())
        return split_event(epoch, numerator, denominator)

    def test_exact_supported_action_matrix(self):
        cases = (
            ("A 2-for-1 stock split of our Class A Common Stock became effective "
             "on January 1, 2026.", "2026-01-01", 2, 1, (1, 2)),
            ("A 3-for-2 stock split of our Class A Common Stock became effective "
             "on January 1, 2026.", "2026-01-01", 3, 2, (2, 3)),
            ("A 1-for-10 reverse stock split of our Class A Common Stock became "
             "effective on January 1, 2026.", "2026-01-01", 1, 10, (10, 1)),
            ("A 5-for-4 stock dividend on our Class A Common Stock was implemented "
             "effective on January 1, 2026.", "2026-01-01", 5, 4, (4, 5)),
        )
        for block, date, numerator, denominator, expected in cases:
            with self.subTest(block=block):
                result = self.qualify(
                    action_blocks=(block,),
                    split_events=(self.event(date, numerator, denominator),),
                )
                self.assertIs(
                    result.status,
                    bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED,
                )
                self.assertEqual(
                    (result.eps_to_quote_basis_multiplier_numerator,
                     result.eps_to_quote_basis_multiplier_denominator),
                    expected,
                )
                self.assertEqual(len(result.reconciled_actions), 1)
                self.assertGreaterEqual(
                    len(result.reconciled_actions[0].sec_claim_semantic_ids), 1)

    def test_two_sequential_splits_reduce_exactly(self):
        blocks = (
            "A 2-for-1 stock split of our Class A Common Stock became effective "
            "on January 1, 2026.",
            "A 3-for-2 stock split of our Class A Common Stock became effective "
            "on January 2, 2026.",
        )
        result = self.qualify(
            action_blocks=blocks,
            split_events=(self.event("2026-01-01", 2, 1),
                          self.event("2026-01-02", 3, 2)),
        )
        self.assertIs(result.status,
                      bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
        self.assertEqual((result.eps_to_quote_basis_multiplier_numerator,
                          result.eps_to_quote_basis_multiplier_denominator), (1, 3))
        self.assertEqual(len(result.reconciled_actions), 2)

    def test_outside_interval_actions_are_not_reapplied(self):
        cases = (
            "A 2-for-1 stock split of our Class A Common Stock became effective "
            "on January 1, 2024.",
            "A 2-for-1 stock split of our Class A Common Stock became effective "
            "on March 1, 2026.",
        )
        for block in cases:
            with self.subTest(block=block):
                result = self.qualify(action_blocks=(block,))
                self.assertIs(result.status,
                              bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
                self.assertEqual(
                    (result.eps_to_quote_basis_multiplier_numerator,
                     result.eps_to_quote_basis_multiplier_denominator),
                    (1, 1),
                )
                self.assertEqual(result.reconciled_actions, ())

    def test_presentation_calendar_date_is_ambiguous(self):
        result = self.qualify(action_blocks=(
            "A 2-for-1 stock split of our Class A Common Stock became effective "
            "on February 1, 2025.",
        ))
        self.assertIs(result.status,
                      bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE)
        self.assertIn(
            bridge.ShareBasisBridgeReason.ACTION_ON_PRESENTATION_BOUNDARY_DATE,
            result.reasons,
        )

    def test_approved_or_proposed_action_not_proven_future_fails_closed(self):
        cases = (
            ("The stockholders approved a 2-for-1 stock split of our Class A "
             "Common Stock with an effective date of January 1, 2026."),
            ("The Company proposed a 2-for-1 stock split of our Class A Common "
             "Stock."),
        )
        for block in cases:
            with self.subTest(block=block):
                result = self.qualify(action_blocks=(block,))
                self.assertIs(
                    result.status,
                    bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE,
                )
                self.assertIn(
                    bridge.ShareBasisBridgeReason.ACTION_LIFECYCLE_UNRESOLVED,
                    result.reasons,
                )

    def test_proposed_action_with_exact_post_quote_date_can_be_ignored(self):
        result = self.qualify(action_blocks=(
            "The Company proposed a 2-for-1 stock split of our Class A Common "
            "Stock with an effective date of March 1, 2026.",
        ))
        self.assertIs(
            result.status, bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_ESTABLISHED)
        self.assertEqual(
            (result.eps_to_quote_basis_multiplier_numerator,
             result.eps_to_quote_basis_multiplier_denominator),
            (1, 1),
        )

    def test_missing_bounded_filing_or_split_history_blocks(self):
        block = ("A 2-for-1 stock split of our Class A Common Stock became effective "
                 "on January 1, 2026.")
        missing_filing = self.qualify(
            action_blocks=(block,), omit_action_receipts=True)
        self.assertIs(missing_filing.status,
                      bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE)
        self.assertIn(
            bridge.ShareBasisBridgeReason.RECENT_FILING_WINDOW_INCOMPLETE,
            missing_filing.reasons,
        )
        missing_yahoo = self.qualify(
            split_raw=b'{"chart":{"result":null,"error":null}}')
        self.assertIs(missing_yahoo.status,
                      bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE)
        self.assertIn(
            bridge.ShareBasisBridgeReason.YAHOO_SPLIT_HISTORY_UNAVAILABLE,
            missing_yahoo.reasons,
        )

    def test_ratio_and_effective_date_disagreement_are_conflicts(self):
        block = ("A 2-for-1 stock split of our Class A Common Stock became effective "
                 "on January 1, 2026.")
        cases = (
            ((self.event("2026-01-01", 3, 1),),
             bridge.ShareBasisBridgeReason.ACTION_RATIO_CONFLICT),
            ((self.event("2026-01-02", 2, 1),),
             bridge.ShareBasisBridgeReason.ACTION_EFFECTIVE_DATE_CONFLICT),
        )
        for events, reason in cases:
            with self.subTest(reason=reason):
                result = self.qualify(action_blocks=(block,), split_events=events)
                self.assertIs(result.status, bridge.ShareBasisBridgeStatus.SOURCE_CONFLICT)
                self.assertIn(reason, result.reasons)

    def test_class_mismatch_and_unsupported_transformations_fail_closed(self):
        cases = (
            ("A 2-for-1 stock split of our Class B Common Stock became effective "
             "on January 1, 2026.",
             bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNAVAILABLE,
             bridge.ShareBasisBridgeReason.ACTION_CLASS_MISMATCH),
            ("Every 1 share of our Class A Common Stock became converted into 2 shares "
             "effective on January 1, 2026 in a share class conversion.",
             bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED,
             bridge.ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION),
            ("A merger security exchange of our Class A Common Stock became effective "
             "on January 1, 2026 and every 1 share became converted into 2 shares.",
             bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED,
             bridge.ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION),
            ("A spin-off affecting our Class A Common Stock became effective on "
             "January 1, 2026 with every 1 share becoming 2 shares.",
             bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED,
             bridge.ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION),
            ("A share redenomination affecting our Class A Common Stock became "
             "effective on January 1, 2026 with every 1 share becoming 2 shares.",
             bridge.ShareBasisBridgeStatus.BASIS_BRIDGE_UNSUPPORTED,
             bridge.ShareBasisBridgeReason.UNSUPPORTED_BASIS_ACTION),
        )
        for block, status, reason in cases:
            with self.subTest(block=block):
                result = self.qualify(
                    action_blocks=(block,),
                    split_events=(self.event("2026-01-01", 2, 1),),
                )
                self.assertIs(result.status, status)
                self.assertIn(reason, result.reasons)


if __name__ == "__main__":
    unittest.main()
