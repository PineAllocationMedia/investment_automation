from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from economic_facts import sec_current_verified_nonpayer as joined_nonpayer
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts import sec_quote_eps_basis_bridge as bridge_module
from economic_facts import yahoo_current_quote as quote_module
from economic_facts import yahoo_split_history as split_module
from economic_facts.sec_share_basis_source_claims import (
    SecShareBasisSourceRequest,
    build_sec_share_basis_source_foundation,
)
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from economic_facts.yahoo_split_history_archive import YahooSplitHistoryArchive
from src import expected_return_pr5d_bundle as bundle
from tests import test_sec_current_verified_nonpayer as nonpayer_tests
from tests.sec_current_security_eps_qualification_fixtures import source_rows
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root
from tests.yahoo_quote_fixtures import chart_response
from tests.yahoo_split_history_fixtures import split_chart_response


class ExpectedReturnPR5D2BundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name).resolve()
        self.quote_archive = YahooQuoteArchive(root / "quotes")
        self.split_archive = YahooSplitHistoryArchive(root / "splits")
        self.nonpayer_fixture = nonpayer_tests.CurrentVerifiedNonpayerTests(
            methodName="runTest")
        self.nonpayer_fixture.setUp()
        self.addCleanup(self.nonpayer_fixture.doCleanups)

    def _build_complete_bundle(self):
        current_boundary = "2026-10-01T12:00:00Z"
        nonpayer_request = self.nonpayer_fixture.build(boundary=current_boundary)
        fixture = self.nonpayer_fixture.fixture
        pr5c = fixture.qualify_request(nonpayer_request.comparability_request)
        market_timestamp = "2026-09-29T16:00:00Z"
        market_epoch = int(datetime.fromisoformat(
            market_timestamp.replace("Z", "+00:00")).timestamp())
        captured_at = "2026-09-29T17:00:00Z"
        quote_receipt = self.quote_archive._capture_live(
            chart_response(market_time=market_epoch), symbol="FICT",
            captured_at=captured_at)
        quote_extraction = quote_module.extract_yahoo_current_quote(
            self.quote_archive, quote_receipt.receipt_id)
        quote_request = quote_module.YahooCurrentQuoteQualificationRequest(
            nonpayer_request.comparability_request.security_eps_request,
            pr5c.upstream_security_eps.semantic_id,
            pr5c.upstream_security_eps.evidence_id,
            quote_receipt.receipt_id,
            quote_extraction.semantic_id,
            quote_extraction.evidence_id)
        quote = quote_module.qualify_yahoo_current_quote(
            self.quote_archive, fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            quote_request)
        presentation_occurrence = next(
            item for item in pr5c.upstream_share_basis_source.submissions_inventory.occurrences
            if dict(item.fields)["accessionNumber"] == pr5c.presentation.accession)
        start_epoch = int(datetime.fromisoformat(
            dict(presentation_occurrence.fields)["acceptanceDateTime"].replace(
                "Z", "+00:00")).timestamp())
        split_receipt = self.split_archive._capture_live(
            split_chart_response(), symbol="FICT", start_epoch=start_epoch,
            end_epoch=market_epoch, captured_at=captured_at)
        split = split_module.extract_yahoo_split_history(
            self.split_archive, split_receipt.receipt_id)
        recent_parent = fixture.submissions_archive._capture_live(
            submissions_root(source_rows(), cik=CIK, sic=3571,
                             sicDescription="Electronic Computers"),
            cik=CIK, captured_at=captured_at)
        recent_request = SecShareBasisSourceRequest(
            recent_parent.receipt_id, (),
            nonpayer_request.comparability_request.share_basis_source_request
            .filing_receipt_ids)
        recent_basis = build_sec_share_basis_source_foundation(
            fixture.submissions_archive, fixture.filing_archive, recent_request)
        bridge_request = bridge_module.SecQuoteEPSBasisBridgeRequest(
            nonpayer_request.comparability_request, pr5c.semantic_id, pr5c.evidence_id,
            quote_request, quote.semantic_id, quote.evidence_id,
            recent_request,
            recent_basis.semantic_id, recent_basis.evidence_id,
            split_receipt.receipt_id, split.semantic_id, split.evidence_id)
        bridge = bridge_module.qualify_sec_quote_eps_basis_bridge(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            self.quote_archive, self.split_archive, bridge_request)
        nonpayer = joined_nonpayer.qualify_sec_current_verified_nonpayer(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            nonpayer_request)
        profile_request = profile_module.SecOrdinaryCompounderProfileRequest(
            nonpayer_request.comparability_request, pr5c.semantic_id, pr5c.evidence_id)
        profile = profile_module.qualify_sec_ordinary_compounder_profile(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            profile_request)
        request = bundle.PR5D2RealExpectedReturnRootsRequest(
            bridge_request, bridge.semantic_id, bridge.evidence_id,
            nonpayer_request, nonpayer.semantic_id, nonpayer.evidence_id,
            profile_request, profile.semantic_id, profile.evidence_id)
        result = bundle.assemble_expected_return_pr5d_bundle(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            self.quote_archive, self.split_archive, request)
        return {
            "result": result,
            "request": request,
            "bridge_request": bridge_request,
            "nonpayer_request": nonpayer_request,
            "profile_request": profile_request,
            "fixture": fixture,
            "pr5c": pr5c,
        }

    def test_complete_free_nonpayer_bundle_retains_exact_roots_without_calculation(self):
        built = self._build_complete_bundle()
        result = built["result"]
        self.assertIs(result.status,
                      bundle.PR5D2BundleStatus.PR5D_REAL_ROOTS_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual(str(result.quote_price), "123.4500")
        self.assertEqual((result.basis_multiplier_numerator,
                          result.basis_multiplier_denominator), (1, 1))
        self.assertEqual(len(result.period_decisions), 5)
        self.assertEqual(result.quote_currency, "USD")
        self.assertEqual(result.accounting_basis, "US_GAAP")
        self.assertIn("NO_EXPECTED_RETURN_CALCULATION", result.limitations)
        self.assertFalse(hasattr(result, "expected_return"))

    def test_bundle_rejects_distinct_successful_pr5c_evidence_on_same_route(self):
        built = self._build_complete_bundle()
        fixture = built["fixture"]
        request_a = built["nonpayer_request"].comparability_request
        filing_ids = request_a.share_basis_source_request.filing_receipt_ids
        filings = tuple(fixture.filing_archive.read_receipt(item) for item in filing_ids)
        presentation_receipt = fixture.filing_archive.read_receipt(
            request_a.presentation_request.filing_receipt_id)
        duplicate = fixture.filing_archive._capture_live(
            fixture.filing_archive.read_object(presentation_receipt),
            cik=presentation_receipt.cik,
            accession=presentation_receipt.accession,
            captured_at="2026-02-21T12:00:04Z",
        )
        temporal_request = (
            request_a.security_eps_request.temporal_source_series_request
            .registered_listing_bridge_request.temporal_boundary_request)
        request_b = fixture.build_request(
            filings=filings,
            current=temporal_request.current_request,
            parent=fixture.submissions_archive.read_receipt(
                request_a.share_basis_source_request.parent_submissions_receipt_id),
            subject_filing_ids=filing_ids + (duplicate.receipt_id,),
            basis_filing_ids=filing_ids + (duplicate.receipt_id,),
            presentation_receipt=duplicate,
        )
        pr5c_b = fixture.qualify_request(request_b)
        self.assertIs(pr5c_b.outcome, built["pr5c"].outcome)
        self.assertEqual(
            (pr5c_b.route_local_issuer_key, pr5c_b.route_local_security_key),
            (built["pr5c"].route_local_issuer_key,
             built["pr5c"].route_local_security_key),
        )
        self.assertNotEqual(pr5c_b.evidence_id, built["pr5c"].evidence_id)
        nonpayer_a = built["nonpayer_request"]
        nonpayer_request_b = joined_nonpayer.SecCurrentVerifiedNonpayerRequest(
            request_b, pr5c_b.semantic_id, pr5c_b.evidence_id,
            nonpayer_a.nonpayer_request,
            nonpayer_a.expected_nonpayer_semantic_id,
            nonpayer_a.expected_nonpayer_evidence_id,
        )
        nonpayer_b = joined_nonpayer.qualify_sec_current_verified_nonpayer(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            nonpayer_request_b,
        )
        profile_request_b = profile_module.SecOrdinaryCompounderProfileRequest(
            request_b, pr5c_b.semantic_id, pr5c_b.evidence_id)
        profile_b = profile_module.qualify_sec_ordinary_compounder_profile(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            profile_request_b,
        )
        mixed = bundle.PR5D2RealExpectedReturnRootsRequest(
            built["bridge_request"],
            built["request"].expected_basis_bridge_semantic_id,
            built["request"].expected_basis_bridge_evidence_id,
            nonpayer_request_b, nonpayer_b.semantic_id, nonpayer_b.evidence_id,
            profile_request_b, profile_b.semantic_id, profile_b.evidence_id,
        )
        result = bundle.assemble_expected_return_pr5d_bundle(
            fixture.current_archive, fixture.submissions_archive,
            fixture.filing_archive, fixture.sec_archive, fixture.nasdaq_archive,
            self.quote_archive, self.split_archive, mixed,
        )
        self.assertIs(result.status, bundle.PR5D2BundleStatus.SOURCE_CONFLICT)
        self.assertIn(bundle.PR5D2BundleReason.UPSTREAM_COMPARABILITY_MISMATCH,
                      result.reasons)


if __name__ == "__main__":
    unittest.main()
