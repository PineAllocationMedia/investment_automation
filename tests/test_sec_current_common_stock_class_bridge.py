"""PR4D4D3A CURRENT same-filing common-stock source correspondence tests."""
import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import os
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch

from economic_facts import sec_current_common_stock_class_bridge as class_bridge
from economic_facts import sec_registered_securities as d3a
from economic_facts.nasdaq_listed_archive import NasdaqListedArchive
from economic_facts.sec_archive import SecArchive
from economic_facts.sec_current_registered_listing_bridge import (
    SecCurrentRegisteredListingBridgeRequest,
)
from economic_facts.sec_filing_archive import SecFilingArchive
from economic_facts.sec_property4_temporal_boundary import (
    SecProperty4TemporalBoundaryRequest,
)
from economic_facts.sec_section12_rights_source_claims import (
    SecSection12RightsSourceClaimsRequest,
    SecSection12RightsSourceTopic,
)
from economic_facts.sec_submissions_archive import SecSubmissionsArchive
from economic_facts.sec_ticker_exchange_archive import SecTickerExchangeArchive
from tests.sec_current_common_stock_class_bridge_fixtures import (
    class_bridge_submission,
)
from tests.sec_current_registered_listing_bridge_fixtures import (
    NASDAQ_CAPTURE,
    SEC_CAPTURE,
    nasdaq_snapshot,
    sec_snapshot,
)
from tests.sec_direct_section12_description_fixtures import description_text
from tests.sec_filing_document_inventory_fixtures import embedded_document
from tests.sec_property4_temporal_boundary_fixtures import (
    BOUNDARY_T1,
    BOUNDARY_T2,
    POST_BOUNDARY_CAPTURE,
    PRE_BOUNDARY_CAPTURE,
    capture_current,
    current_request,
)
from tests.sec_property4_temporal_fixtures import ACCESSION, CIK, FILENAME
from tests.sec_section12_rights_source_claims_fixtures import rights_html
from tests.sec_submissions_fixtures import root as submissions_root, row


def source_row(number=1, **changes):
    return row(number, **{**{
        "accessionNumber": f"0000000001-26-{number:06d}",
        "primaryDocument": FILENAME,
    }, **changes})


class CurrentCommonStockClassBridgeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self._set_archives(self.base)

    def _set_archives(self, base):
        self.current_archive = SecArchive(base / "current")
        self.submissions_archive = SecSubmissionsArchive(base / "submissions")
        self.filing_archive = SecFilingArchive(base / "filings")
        self.sec_archive = SecTickerExchangeArchive(base / "sec-associations")
        self.nasdaq_archive = NasdaqListedArchive(base / "nasdaq")

    def current(self, *, boundary=BOUNDARY_T1, live=True):
        return current_request(capture_current(
            self.current_archive, boundary=boundary, live=live))

    def parent(self, *, rows=None, cik=CIK):
        return self.submissions_archive._capture_live(
            submissions_root([source_row()] if rows is None else rows, cik=cik),
            cik=cik,
            captured_at="2026-02-02T12:00:00Z",
        )

    def filing(self, *, raw=None, cik=CIK, accession=ACCESSION,
               captured_at=PRE_BOUNDARY_CAPTURE, **changes):
        payload = (class_bridge_submission(cik=cik, accession=accession, **changes)
                   if raw is None else raw)
        return self.filing_archive._capture_live(
            payload, cik=cik, accession=accession, captured_at=captured_at)

    def sec(self, *, captured_at=SEC_CAPTURE, raw=None, **changes):
        return self.sec_archive._capture_live(
            sec_snapshot(**changes) if raw is None else raw,
            captured_at=captured_at,
        )

    def nasdaq(self, *, captured_at=NASDAQ_CAPTURE, raw=None, **changes):
        return self.nasdaq_archive._capture_live(
            nasdaq_snapshot(**changes) if raw is None else raw,
            captured_at=captured_at,
        )

    def request(self, current, parent, sec, nasdaq, rights_receipt, *, filings=()):
        temporal = SecProperty4TemporalBoundaryRequest(
            current,
            parent.receipt_id,
            (),
            tuple(receipt.receipt_id for receipt in filings),
        )
        d4c2 = SecCurrentRegisteredListingBridgeRequest(
            temporal, sec.receipt_id, nasdaq.receipt_id)
        rights = SecSection12RightsSourceClaimsRequest(rights_receipt.receipt_id)
        return class_bridge.SecCurrentCommonStockClassBridgeRequest(d4c2, rights)

    def inputs(self, *, current=None, parent=None, filings=None, rights_receipt=None,
               sec=None, nasdaq=None):
        current = self.current() if current is None else current
        parent = self.parent() if parent is None else parent
        if filings is None:
            filings = (self.filing(),)
        sec = self.sec() if sec is None else sec
        nasdaq = self.nasdaq() if nasdaq is None else nasdaq
        rights_receipt = filings[0] if rights_receipt is None else rights_receipt
        request = self.request(
            current, parent, sec, nasdaq, rights_receipt, filings=filings)
        return request

    def assess_request(self, request):
        return class_bridge.assess_sec_current_common_stock_class_bridge(
            self.current_archive,
            self.submissions_archive,
            self.filing_archive,
            self.sec_archive,
            self.nasdaq_archive,
            request,
        )

    def assess(self, **kwargs):
        return self.assess_request(self.inputs(**kwargs))

    def test_exact_public_api_request_shape_types_and_frozen_records(self):
        self.assertEqual(tuple(inspect.signature(
            class_bridge.assess_sec_current_common_stock_class_bridge).parameters), (
                "current_archive", "submissions_archive", "filing_archive",
                "ticker_exchange_archive", "nasdaq_listed_archive", "request"))
        self.assertEqual(tuple(field.name for field in fields(
            class_bridge.SecCurrentCommonStockClassBridgeRequest)), (
                "registered_listing_bridge_request", "rights_claims_request"))
        request = self.inputs()
        for keyword in ("cik", "ticker", "title", "exchange", "class_heading",
                        "source_scope_id", "security_id", "candidate", "as_of",
                        "rights_value", "qualified", "raw", "url", "clock"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                class_bridge.SecCurrentCommonStockClassBridgeRequest(
                    request.registered_listing_bridge_request,
                    request.rights_claims_request,
                    **{keyword: "forbidden"},
                )
        for invalid in (object(), request.registered_listing_bridge_request):
            with self.assertRaises(
                    class_bridge.SecCurrentCommonStockClassBridgeRequestError):
                class_bridge.assess_sec_current_common_stock_class_bridge(
                    self.current_archive, self.submissions_archive,
                    self.filing_archive, self.sec_archive, self.nasdaq_archive,
                    invalid)
        result = self.assess_request(request)
        with self.assertRaises(FrozenInstanceError):
            result.status = "changed"
        with self.assertRaises(FrozenInstanceError):
            result.candidates[0].source_symbol = "changed"

    def test_each_public_archive_argument_requires_its_exact_type(self):
        request = self.inputs()
        arguments = [
            self.current_archive, self.submissions_archive, self.filing_archive,
            self.sec_archive, self.nasdaq_archive, request,
        ]
        for index in range(len(arguments)):
            wrong = list(arguments)
            wrong[index] = object()
            with self.subTest(index=index), self.assertRaises(
                    class_bridge.SecCurrentCommonStockClassBridgeRequestError):
                class_bridge.assess_sec_current_common_stock_class_bridge(*wrong)

    def test_positive_bridge_replays_all_three_rails_and_preserves_provenance(self):
        request = self.inputs()
        with patch.object(
                class_bridge, "assess_sec_current_registered_listing_bridge",
                wraps=class_bridge.assess_sec_current_registered_listing_bridge) as d4c2, \
             patch.object(
                class_bridge, "extract_sec_section12_rights_source_claims",
                wraps=class_bridge.extract_sec_section12_rights_source_claims) as d4d2b, \
             patch.object(
                class_bridge, "extract_sec_registered_security_claims",
                wraps=class_bridge.extract_sec_registered_security_claims) as selected_d3a:
            result = self.assess_request(request)
        self.assertEqual((d4c2.call_count, d4d2b.call_count, selected_d3a.call_count),
                         (1, 1, 1))
        self.assertEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertEqual(len(result.candidates), 1)
        candidate = result.candidates[0]
        self.assertEqual(candidate.profile,
            class_bridge.SEC_NASDAQ_CURRENT_COMMON_STOCK_CLASS_SOURCE_BRIDGE_V1)
        self.assertEqual((candidate.source_cik, candidate.source_symbol), (CIK, "FICT"))
        self.assertEqual(candidate.exact_d3a_title,
                         "Class A Common Stock, $0.01 par value")
        self.assertEqual(candidate.canonical_source_class_label,
                         "CLASS A COMMON STOCK")
        self.assertEqual(candidate.exact_d3a_title_suffix, ", $0.01 par value")
        self.assertEqual(candidate.exact_d4d2b_class_heading, "CLASS A COMMON STOCK")
        self.assertEqual(candidate.source_topics, (
            SecSection12RightsSourceTopic.DIVIDEND,
            SecSection12RightsSourceTopic.VOTING,
        ))
        self.assertEqual(len(candidate.passage_semantic_ids), 1)
        self.assertEqual(len(candidate.passage_evidence_ids), 1)
        self.assertEqual(candidate.status, result.status)
        self.assertEqual(candidate.issues, ())

    def test_prebuilt_assessments_cannot_bypass_any_fresh_replay(self):
        result = self.assess()
        with self.assertRaises(
                class_bridge.SecCurrentCommonStockClassBridgeRequestError):
            class_bridge.SecCurrentCommonStockClassBridgeRequest(
                result.current_listing_bridge, result.rights_source_claims)
        with self.assertRaises(
                class_bridge.SecCurrentCommonStockClassBridgeRequestError):
            class_bridge.SecCurrentCommonStockClassBridgeRequest(
                result.current_listing_bridge, result.selected_d3a)

    def test_closed_title_parser_positive_profile_and_opaque_suffix(self):
        cases = {
            "Common Stock": ("COMMON STOCK", None),
            " class\u2003a\tcommon stock ": ("CLASS A COMMON STOCK", None),
            "CLASS 1 COMMON STOCK": ("CLASS 1 COMMON STOCK", None),
            "Class A Common Stock, $0.01 par value": (
                "CLASS A COMMON STOCK", ", $0.01 par value"),
            "Common Stock, $1 par value per share": (
                "COMMON STOCK", ", $1 par value per share"),
            "Common Stock, par value $0.001": (
                "COMMON STOCK", ", par value $0.001"),
            "Common Stock, par value $0.001 per share": (
                "COMMON STOCK", ", par value $0.001 per share"),
            "Common Stock, no par value": (
                "COMMON STOCK", ", no par value"),
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(
                    class_bridge._parse_d3a_common_stock_title(value), expected)

    def test_closed_title_parser_rejects_every_unreviewed_near_match(self):
        unsupported = (
            "Common Shares", "Ordinary Shares", "Class AA Common Stock",
            "Class A Voting Common Stock", "Common Stock and Preferred Stock",
            "Common Stock, nominal value $0.01", "Common Stock, approximately $0.01 par value",
            "Common Stock (Class A)", "Common Stock.", "Class-A Common Stock",
            "CΟMMON STOCK", "Common Stock, $0.12345678901 par value",
            "Common Stock, $1. par value", "Common Stock, par value USD 1",
        )
        for value in unsupported:
            with self.subTest(value=value):
                self.assertIsNone(class_bridge._parse_d3a_common_stock_title(value))

    def test_common_class_and_numeric_class_exact_matches(self):
        for index, (title, heading) in enumerate((
                ("Common Stock", "COMMON STOCK"),
                ("Class 1 Common Stock", "CLASS 1 COMMON STOCK"))):
            filing = self.filing(
                title=title,
                rights_blocks=(("h2", heading), ("p", "Voting rights.")),
                captured_at=f"2026-02-0{index + 2}T12:00:00Z",
            )
            result = self.assess(filings=(filing,))
            with self.subTest(title=title):
                self.assertEqual(result.status,
                    class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)

    def test_exact_scope_matching_zero_and_cross_class_mismatch(self):
        for index, heading in enumerate(("COMMON STOCK", "CLASS B COMMON STOCK")):
            filing = self.filing(
                rights_blocks=(("h2", heading), ("p", "Voting rights.")),
                captured_at=f"2026-02-0{index + 2}T13:00:00Z",
            )
            result = self.assess(filings=(filing,))
            with self.subTest(heading=heading):
                self.assertEqual(result.status,
                    class_bridge.ClassBridgeAssessmentStatus.NO_SUPPORTED_CLASS_CANDIDATE)
                self.assertIn(class_bridge.ClassBridgeIssue.NO_MATCHING_RIGHTS_CLASS_SCOPE,
                              result.issues)
                self.assertIsNone(result.candidates[0].d4d2b_source_class_scope_id)

    def test_duplicate_matching_scopes_remain_ambiguous_without_passage_winner(self):
        filing = self.filing(rights_blocks=(
            ("h2", "CLASS A COMMON STOCK"),
            ("p", "Voting rights."),
            ("p", "Dividend rights."),
            ("h2", "CLASS A COMMON STOCK"),
            ("p", "Voting rights."),
        ))
        result = self.assess(filings=(filing,))
        self.assertEqual(result.status,
                         class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(class_bridge.ClassBridgeIssue.AMBIGUOUS_RIGHTS_CLASS_SCOPE,
                      result.issues)
        candidate = result.candidates[0]
        self.assertEqual(len(candidate.matching_scope_semantic_ids), 2)
        self.assertIsNone(candidate.d4d2b_source_class_scope_id)
        self.assertEqual(candidate.passage_semantic_ids, ())

    def test_unsupported_title_is_explicit_and_never_fuzzily_matched(self):
        filing = self.filing(
            title="Class A Voting Common Stock",
            rights_blocks=(("h2", "CLASS A COMMON STOCK"),
                           ("p", "Voting rights.")),
        )
        result = self.assess(filings=(filing,))
        self.assertEqual(result.status,
                         class_bridge.ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE)
        self.assertIn(
            class_bridge.ClassBridgeIssue.UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE,
            result.issues)
        self.assertIsNone(result.candidates[0].canonical_source_class_label)

    def test_d4c2_nonpositive_states_are_rejected_without_cherry_picking(self):
        incomplete = self.assess(current=self.current(live=False))
        self.assertEqual(incomplete.status,
            class_bridge.ClassBridgeAssessmentStatus.UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE)
        self.assertEqual(incomplete.candidates, ())

        conflicting = self.assess(filings=(
            self.filing(symbol="FICT"),
            self.filing(symbol="OTHER", captured_at="2026-02-03T12:00:00Z"),
        ))
        self.assertEqual(conflicting.status,
                         class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(class_bridge.ClassBridgeIssue.D4C2_CURRENT_BRIDGE_CONFLICT,
                      conflicting.issues)

        unsupported = self.assess(filings=(self.filing(exchange="NYSE"),))
        self.assertEqual(unsupported.status,
                         class_bridge.ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE)
        self.assertIn(class_bridge.ClassBridgeIssue.D4C2_UNSUPPORTED_SOURCE_PROFILE,
                      unsupported.issues)

        rights_receipt = self.filing(captured_at="2026-02-04T12:00:00Z")
        no_candidate = self.assess(
            parent=self.parent(rows=[source_row(form="8-K")]),
            filings=(),
            rights_receipt=rights_receipt,
        )
        self.assertEqual(no_candidate.status,
            class_bridge.ClassBridgeAssessmentStatus.UPSTREAM_CURRENT_BRIDGE_UNAVAILABLE)
        self.assertIn(class_bridge.ClassBridgeIssue.D4C2_NO_SUPPORTED_CANDIDATE,
                      no_candidate.issues)

    def test_d4d2b_nonpositive_states_are_rejected_without_cherry_picking(self):
        ambiguous = self.filing(rights_blocks=(
            ("h2", "CLASS AA COMMON STOCK"), ("p", "Voting rights.")))
        result = self.assess(filings=(ambiguous,))
        self.assertEqual(result.status,
                         class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(class_bridge.ClassBridgeIssue.D4D2B_SOURCE_AMBIGUITY,
                      result.issues)
        self.assertEqual(result.candidates, ())

        text_payload = description_text() + b"\nCLASS A COMMON STOCK\nVoting rights.\n"
        raw = class_bridge_submission(rights_documents=((
            "EX-4.1", "2", "rights.txt", "Opaque", text_payload),))
        unsupported = self.assess(filings=(self.filing(raw=raw),))
        self.assertEqual(unsupported.status,
                         class_bridge.ClassBridgeAssessmentStatus.UNSUPPORTED_CLASS_PROFILE)
        self.assertIn(class_bridge.ClassBridgeIssue.D4D2B_UNSUPPORTED_SOURCE_PROFILE,
                      unsupported.issues)

        good = ("EX-4.1", "2", "good.htm", "Opaque", rights_html(blocks=(
            ("h2", "CLASS A COMMON STOCK"), ("p", "Voting rights."))))
        bad = ("EX-4.B", "3", "bad.htm", "Opaque", b"<html><body>broken</html>")
        mixed_raw = class_bridge_submission(rights_documents=(good, bad))
        mixed = self.assess(filings=(self.filing(raw=mixed_raw),))
        self.assertEqual(mixed.status,
                         class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertEqual(mixed.candidates, ())

    def test_d4d2b_no_scope_and_no_passage_states_remain_unavailable(self):
        cases = (
            ((("h2", "PREFERRED STOCK"), ("p", "Voting rights.")),
             class_bridge.ClassBridgeIssue.D4D2B_NO_SUPPORTED_COMMON_STOCK_SCOPE),
            ((("h2", "CLASS A COMMON STOCK"), ("p", "Opaque class prose.")),
             class_bridge.ClassBridgeIssue.D4D2B_NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS),
        )
        for index, (blocks, issue) in enumerate(cases):
            if index:
                self._set_archives(self.base / f"rights-unavailable-{index}")
            result = self.assess(filings=(self.filing(rights_blocks=blocks),))
            with self.subTest(issue=issue):
                self.assertEqual(result.status,
                    class_bridge.ClassBridgeAssessmentStatus.UPSTREAM_RIGHTS_SOURCE_UNAVAILABLE)
                self.assertIn(issue, result.issues)
                self.assertEqual(result.candidates, ())

    def test_rights_receipt_accession_and_cik_must_share_current_candidate(self):
        participating = self.filing()
        other_receipt = self.filing(captured_at="2026-02-03T12:00:00Z")
        different_receipt = self.assess(
            filings=(participating,), rights_receipt=other_receipt)
        self.assertIn(
            class_bridge.ClassBridgeIssue.RIGHTS_RECEIPT_NOT_IN_CURRENT_BRIDGE,
            different_receipt.issues)

        other_accession = "0000000001-26-000002"
        other = self.filing(accession=other_accession,
                            captured_at="2026-02-04T12:00:00Z")
        different_accession = self.assess(
            filings=(participating,), rights_receipt=other)
        self.assertIn(
            class_bridge.ClassBridgeIssue.RIGHTS_ACCESSION_NOT_IN_CURRENT_BRIDGE,
            different_accession.issues)

        other_cik = "0000000456"
        other_issuer = self.filing(cik=other_cik,
                                   captured_at="2026-02-05T12:00:00Z")
        different_cik = self.assess(
            filings=(participating,), rights_receipt=other_issuer)
        self.assertIn(class_bridge.ClassBridgeIssue.SOURCE_CIK_MISMATCH,
                      different_cik.issues)

    def test_post_boundary_recapture_cannot_repair_current_t(self):
        raw = class_bridge_submission()
        before = self.filing(raw=raw)
        after = self.filing(raw=raw, captured_at=POST_BOUNDARY_CAPTURE)
        result = self.assess(filings=(before, after), rights_receipt=after)
        self.assertEqual(result.current_authority_boundary, BOUNDARY_T1)
        self.assertIn(
            class_bridge.ClassBridgeIssue.RIGHTS_RECEIPT_NOT_IN_CURRENT_BRIDGE,
            result.issues)
        self.assertNotEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)

    def test_primary_and_rights_exhibit_documents_may_differ_within_same_receipt(self):
        result = self.assess()
        candidate = result.candidates[0]
        d3a_document = result.selected_d3a.primary_document.evidence_id
        scope_document = result.rights_source_claims.class_scopes[0].document_evidence_id
        self.assertNotEqual(d3a_document, scope_document)
        self.assertEqual(candidate.filing_receipt_id,
                         result.selected_d3a.receipt.receipt_id)
        self.assertEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)

    def _patched_d3a_result(self, request, transform):
        real = d3a.extract_sec_registered_security_claims(
            self.filing_archive,
            d3a.SecRegisteredSecurityExtractionRequest(
                request.rights_claims_request.filing_receipt_id),
        )
        altered = transform(real)
        with patch.object(class_bridge, "extract_sec_registered_security_claims",
                          return_value=altered):
            return self.assess_request(request)

    def test_fresh_d3a_replay_must_agree_with_embedded_d4c2_replay(self):
        request = self.inputs()
        result = self._patched_d3a_result(
            request, lambda value: replace(value, contract_version=value.contract_version + "-x"))
        self.assertEqual(result.status,
                         class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(class_bridge.ClassBridgeIssue.D3A_REPLAY_DISAGREEMENT,
                      result.issues)

    def test_d3a_symbol_title_scope_exchange_and_multiple_claims_fail_closed(self):
        transformations = {
            class_bridge.ClassBridgeIssue.D3A_SYMBOL_MISMATCH:
                lambda value: replace(value, claims=(replace(
                    value.claims[0], trading_symbols=("OTHER",)),)),
            class_bridge.ClassBridgeIssue.D3A_TITLE_NOT_IN_D4C2_CANDIDATE:
                lambda value: replace(value, claims=(replace(
                    value.claims[0], titles=("Common Stock",)),)),
            class_bridge.ClassBridgeIssue.D3A_SCOPE_NOT_IN_D4C2_CANDIDATE:
                lambda value: replace(value, claims=(replace(
                    value.claims[0], source_security_scope_id="f" * 64),)),
            class_bridge.ClassBridgeIssue.D3A_EXCHANGE_MISMATCH:
                lambda value: replace(value, claims=(replace(
                    value.claims[0], exchange_names=("Nasdaq",)),)),
            class_bridge.ClassBridgeIssue.D3A_MULTIPLE_ELIGIBLE_CLASS_CLAIMS:
                lambda value: replace(value, claims=(
                    value.claims[0], replace(
                        value.claims[0], context_semantic_id="e" * 64,
                        source_security_scope_id="d" * 64,
                        titles=("Common Stock",)),
                )),
        }
        for index, (issue, transform) in enumerate(transformations.items()):
            if index:
                self._set_archives(self.base / f"patched-{index}")
            request = self.inputs()
            result = self._patched_d3a_result(request, transform)
            with self.subTest(issue=issue):
                self.assertEqual(result.status,
                                 class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
                self.assertIn(issue, result.issues)

    def test_d3a_claim_issues_and_noncaptured_status_block_eligibility(self):
        request = self.inputs()
        result = self._patched_d3a_result(
            request,
            lambda value: replace(
                value,
                status=d3a.ExtractionStatus.INCOMPLETE_REGISTERED_SECURITY_CLAIMS,
                claims=(replace(value.claims[0], issues=(d3a.ClaimIssue.MISSING_TITLE,)),),
            ),
        )
        self.assertEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.SOURCE_CONFLICT)
        self.assertIn(class_bridge.ClassBridgeIssue.D3A_REGISTERED_SECURITY_INCOMPLETE,
                      result.issues)
        self.assertIn(class_bridge.ClassBridgeIssue.D3A_REPLAY_DISAGREEMENT,
                      result.issues)
        self.assertEqual(result.candidates, ())

    def test_topics_are_retained_only_as_source_topics_not_interpreted_rights(self):
        result = self.assess()
        candidate = result.candidates[0]
        forbidden = {
            "has_voting_rights", "votes_per_share", "has_dividend_rights",
            "has_preemptive_rights", "redeemable", "convertible",
            "liquidation_preference", "rights_complete", "legal_rights",
        }
        self.assertFalse(forbidden & set(candidate.__dataclass_fields__))
        self.assertTrue(candidate.source_topics)

        no_topic_match = self.filing(rights_blocks=(
            ("h2", "CLASS A COMMON STOCK"), ("p", "Opaque class prose."),
            ("h2", "COMMON STOCK"), ("p", "Voting rights."),
        ))
        result = self.assess(filings=(no_topic_match,))
        self.assertEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)
        self.assertEqual(result.candidates[0].source_topics, ())
        self.assertEqual(result.candidates[0].passage_semantic_ids, ())

    def test_no_durable_identity_admission_authority_or_model_fields(self):
        exact_forbidden = {
            "issuer_id", "security_id", "class_id", "listing_id", "pam_class_id",
            "pam_security_id", "durable_class_id", "qualified_class",
            "admitted_class", "rights_complete", "legal_rights", "instrument_type",
            "authority", "qualified", "admitted",
        }
        for record in (
                class_bridge.SecCurrentCommonStockClassBridgeRequest,
                class_bridge.CurrentCommonStockClassBridgeEvidence,
                class_bridge.SecCurrentCommonStockClassBridgeAssessment):
            self.assertFalse(exact_forbidden & set(record.__dataclass_fields__))

    def test_semantic_and_evidence_identities_are_deterministic_and_sensitive(self):
        first = self.assess()
        second = self.assess_request(self.inputs())
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))
        self.assertEqual(first.candidates[0].semantic_id,
                         second.candidates[0].semantic_id)

        self._set_archives(self.base / "changed-title")
        changed_title = self.assess(filings=(self.filing(
            title="Class A Common Stock, $0.02 par value"),))
        self.assertNotEqual(first.semantic_id, changed_title.semantic_id)

        self._set_archives(self.base / "changed-heading")
        changed_heading = self.assess(filings=(self.filing(rights_blocks=(
            ("h2", "Class A Common Stock"), ("p", "Voting and dividend rights."))),))
        self.assertNotEqual(first.semantic_id, changed_heading.semantic_id)

        self._set_archives(self.base / "changed-passage")
        changed_passage = self.assess(filings=(self.filing(rights_blocks=(
            ("h2", "CLASS A COMMON STOCK"),
            ("p", "Holders have voting and dividend rights under this source."))),))
        self.assertNotEqual(first.semantic_id, changed_passage.semantic_id)

    def test_identical_recapture_preserves_semantics_and_changes_evidence(self):
        raw = class_bridge_submission()
        first_receipt = self.filing(raw=raw, captured_at="2026-02-02T12:00:00Z")
        second_receipt = self.filing(raw=raw, captured_at="2026-02-03T12:00:00Z")
        current = self.current(boundary=BOUNDARY_T2)
        parent = self.parent()
        sec = self.sec()
        nasdaq = self.nasdaq()
        first = self.assess_request(self.request(
            current, parent, sec, nasdaq, first_receipt, filings=(first_receipt,)))
        second = self.assess_request(self.request(
            current, parent, sec, nasdaq, second_receipt, filings=(second_receipt,)))
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(first.candidates[0].semantic_id,
                         second.candidates[0].semantic_id)
        self.assertNotEqual(first.candidates[0].evidence_id,
                            second.candidates[0].evidence_id)

    def test_filesystem_path_does_not_enter_identity(self):
        first = self.assess()
        self._set_archives(self.base / "other-root")
        second = self.assess()
        self.assertEqual((first.semantic_id, first.evidence_id),
                         (second.semantic_id, second.evidence_id))

    def test_no_network_writes_clock_directory_scan_or_latest_selection(self):
        request = self.inputs()
        roots = (self.current_archive.root, self.submissions_archive.root,
                 self.filing_archive.root, self.sec_archive.root, self.nasdaq_archive.root)
        before = {(root, path.relative_to(root)): path.read_bytes()
                  for root in roots for path in root.rglob("*") if path.is_file()}
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")), \
             patch.object(os, "listdir", side_effect=AssertionError("directory scan")), \
             patch.object(os, "scandir", side_effect=AssertionError("directory scan")), \
             patch.object(time, "time", side_effect=AssertionError("clock")), \
             patch.object(time, "monotonic", side_effect=AssertionError("clock")):
            result = self.assess_request(request)
        after = {(root, path.relative_to(root)): path.read_bytes()
                 for root in roots for path in root.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(result.status,
            class_bridge.ClassBridgeAssessmentStatus.CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED)


class CurrentCommonStockClassBridgeDependencyTests(unittest.TestCase):
    def test_exact_dependency_direction_and_no_forbidden_operations(self):
        root = Path(__file__).resolve().parents[1]
        module = root / "economic_facts/sec_current_common_stock_class_bridge.py"
        tree = ast.parse(module.read_text())
        allowed_standard = {"dataclasses", "enum", "re"}
        allowed_relative = {
            "nasdaq_listed_archive", "sec_archive",
            "sec_current_registered_listing_bridge", "sec_filing_archive",
            "sec_registered_securities", "sec_section12_rights_source_claims",
            "sec_submissions_archive", "sec_ticker_exchange_archive",
        }
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name in allowed_standard for alias in node.names))
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
                self.assertTrue((node.level == 1 and node.module in allowed_relative)
                                or (node.level == 0 and node.module in allowed_standard))
            elif isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {
                    "open", "float", "eval", "exec", "__import__", "now", "today",
                    "listdir", "scandir",
                })
        joined = " ".join(imported)
        for forbidden in ("security_identity", "source_authority", "expected_return",
                          "src", "pit_comparison", "model", "portfolio", "runtime",
                          "main"):
            self.assertNotIn(forbidden, joined)

    def test_no_reverse_model_runtime_v1_or_authority_consumer(self):
        root = Path(__file__).resolve().parents[1]
        module_name = "sec_current_common_stock_class_bridge"
        for path in [root / "main.py", *(root / "src").rglob("*.py"),
                     *(root / "pit_comparison").rglob("*.py"),
                     *(root / "scripts").rglob("*.py")]:
            self.assertNotIn(module_name, path.read_text(), str(path))

    def test_no_decimal_or_par_value_economics(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "economic_facts/sec_current_common_stock_class_bridge.py").read_text()
        tree = ast.parse(source)
        imports = {node.module or "" for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree)
                       if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any("decimal" in name.lower() for name in imports))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = (node.func.id if isinstance(node.func, ast.Name) else
                        node.func.attr if isinstance(node.func, ast.Attribute) else "")
                self.assertNotIn(name, {"float", "Decimal"})

    def test_contract_documents_nonclaims_property4_and_handoff(self):
        text = (Path(__file__).resolve().parents[1] / "docs" / "contracts" / "v2"
                / "expected_return" / "EXPECTED_RETURN_PR4D4D3A.md").read_text()
        for property_name in ("4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H"):
            self.assertIn("| " + property_name + " |", text)
        for phrase in (
                "Obligations 5–7 remain unresolved",
                "same-filing common-stock source correspondence",
                "no durable class or security identity",
                "rights topics remain uninterpreted",
                "TEMPORAL CLASS CONTINUITY",
                "LEGAL-RIGHTS VALUE INTERPRETATION"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
