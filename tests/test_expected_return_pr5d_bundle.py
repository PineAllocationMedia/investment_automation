from datetime import datetime
from pathlib import Path
import tempfile
import unittest

from economic_facts import sec_current_verified_nonpayer as joined_nonpayer
from economic_facts import sec_ordinary_compounder_profile as profile_module
from economic_facts import sec_quote_eps_basis_bridge as bridge_module
from economic_facts import yahoo_current_quote as quote_module
from economic_facts import yahoo_split_history as split_module
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from economic_facts.yahoo_split_history_archive import YahooSplitHistoryArchive
from src import expected_return_pr5d_bundle as bundle
from tests import test_sec_current_verified_nonpayer as nonpayer_tests
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

    def test_complete_free_nonpayer_bundle_retains_exact_roots_without_calculation(self):
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
        recent_basis = pr5c.upstream_share_basis_source
        bridge_request = bridge_module.SecQuoteEPSBasisBridgeRequest(
            nonpayer_request.comparability_request, pr5c.semantic_id, pr5c.evidence_id,
            quote_request, quote.semantic_id, quote.evidence_id,
            nonpayer_request.comparability_request.share_basis_source_request,
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
        self.assertIs(result.status,
                      bundle.PR5D2BundleStatus.PR5D_REAL_ROOTS_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual(str(result.quote_price), "123.4500")
        self.assertEqual((result.basis_multiplier_numerator,
                          result.basis_multiplier_denominator), (1, 1))
        self.assertEqual(len(result.period_decisions), 5)
        self.assertEqual(result.quote_currency, "USD")
        self.assertIn("NO_EXPECTED_RETURN_CALCULATION", result.limitations)
        self.assertFalse(hasattr(result, "expected_return"))


if __name__ == "__main__":
    unittest.main()
