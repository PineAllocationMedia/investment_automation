import unittest

from economic_facts import sec_current_verified_nonpayer as joined
from economic_facts.sec_verified_nonpayer import (
    NonpayerPeriodPolicy,
    VERIFIED_NONPAYER_CONTRACT_VERSION,
    VerifiedNonpayerRequest,
    resolve_sec_verified_nonpayer,
)
from tests.sec_common_stock_dividend_fixtures import dividend_row, dividend_source
from tests.sec_current_security_eps_qualification_fixtures import (
    companyfacts_rows,
    qualification_submission,
    source_rows,
    with_competing_common_security,
)
from tests.sec_filing_fixtures import raw as companyfacts_raw, source as companyfacts_source
from tests.sec_property4_temporal_boundary_fixtures import BOUNDARY_T1, current_request
from tests.sec_property4_temporal_fixtures import CIK
from tests.sec_submissions_fixtures import root as submissions_root
from tests import test_sec_current_eps_comparability_qualification as comparability_tests


class CurrentVerifiedNonpayerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = comparability_tests.SecCurrentEPSComparabilityTests(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def build(self, *, boundary=BOUNDARY_T1, dividend_payload=None,
              nonpayer_cik=CIK, latest_period="2024-12-31",
              expected_unit="USD/shares", nonpayer_capture=None,
              competing_class=False):
        payload = companyfacts_source(companyfacts_rows())
        payload["cik"] = int(CIK)
        payload["entityName"] = "Fictional Combined EPS and Nonpayer Issuer"
        dividend_payload = (dividend_source(cik=int(CIK))
                            if dividend_payload is None else dividend_payload)
        payload["facts"]["us-gaap"].update(dividend_payload["facts"]["us-gaap"])
        receipt = self.fixture.current_archive._capture_live(
            companyfacts_raw(payload), cik=CIK, captured_at=boundary)
        current = current_request(receipt, cik=CIK)
        parent = self.fixture.submissions_archive._capture_live(
            submissions_root(source_rows(), cik=CIK, sic=3571,
                             sicDescription="Electronic Computers"),
            cik=CIK, captured_at="2026-02-25T12:00:00Z")
        filings = None
        if competing_class:
            filings = list(self.fixture.filings())
            filings[4] = self.fixture.filing(
                2024,
                raw=with_competing_common_security(
                    qualification_submission(2024), 2024),
            )
            filings = tuple(filings)
        comparability_request = self.fixture.build_request(
            current=current, parent=parent, filings=filings)
        pr5c = self.fixture.qualify_request(comparability_request)
        nonpayer_receipt = receipt
        if nonpayer_capture is not None:
            nonpayer_receipt = self.fixture.current_archive._capture_live(
                companyfacts_raw(payload), cik=CIK, captured_at=nonpayer_capture)
        nonpayer_request = VerifiedNonpayerRequest(
            VERIFIED_NONPAYER_CONTRACT_VERSION,
            nonpayer_receipt.receipt_id,
            nonpayer_cik,
            latest_period,
            expected_unit,
            NonpayerPeriodPolicy.FIXED_MONTH_END_365_366,
        )
        source = resolve_sec_verified_nonpayer(self.fixture.current_archive, nonpayer_request)
        request = joined.SecCurrentVerifiedNonpayerRequest(
            comparability_request, pr5c.semantic_id, pr5c.evidence_id,
            nonpayer_request, source.semantic_hash, source.evidence_hash)
        return request

    def qualify(self, request):
        return joined.qualify_sec_current_verified_nonpayer(
            self.fixture.current_archive,
            self.fixture.submissions_archive,
            self.fixture.filing_archive,
            self.fixture.sec_archive,
            self.fixture.nasdaq_archive,
            request)

    def test_same_companyfacts_receipt_two_zero_concepts_establishes_route_local_nonpayer(self):
        result = self.qualify(self.build())
        self.assertIs(result.status,
                      joined.RouteLocalVerifiedNonpayerStatus.VERIFIED_NONPAYER_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual((result.period_start, result.period_end),
                         ("2024-01-01", "2024-12-31"))
        self.assertEqual(result.unit, "USD/shares")
        self.assertIsNotNone(result.route_local_security_key)
        self.assertIn("NO_GENERAL_MULTI_CLASS_DIVIDEND_ALLOCATION", result.limitations)

    def test_foreign_cik_and_wrong_latest_period_block(self):
        cases = (
            (self.build(nonpayer_cik="0000000001"),
             joined.RouteLocalNonpayerReason.FOREIGN_CIK),
            (self.build(latest_period="2023-12-31"),
             joined.RouteLocalNonpayerReason.WRONG_LATEST_FISCAL_PERIOD),
        )
        for request, reason in cases:
            with self.subTest(reason=reason):
                result = self.qualify(request)
                self.assertIs(result.status,
                              joined.RouteLocalVerifiedNonpayerStatus.NONPAYER_UNAVAILABLE)
                self.assertIn(reason, result.reasons)

    def test_positive_missing_and_conflicting_dividend_evidence_never_becomes_zero(self):
        missing = dividend_source(cik=int(CIK))
        del missing["facts"]["us-gaap"]["CommonStockDividendsPerShareDeclared"]
        conflicting_rows = [
            dividend_row(0),
            dividend_row(0.25, form="10-K/A", filed="2025-03-01",
                         accn="0000000000-25-000002"),
        ]
        cases = (
            (dividend_source(declared=[dividend_row(0.25)], cik=int(CIK)),
             joined.RouteLocalVerifiedNonpayerStatus.NONPAYER_UNAVAILABLE),
            (missing, joined.RouteLocalVerifiedNonpayerStatus.NONPAYER_UNAVAILABLE),
            (dividend_source(declared=conflicting_rows, cik=int(CIK)),
             joined.RouteLocalVerifiedNonpayerStatus.SOURCE_CONFLICT),
        )
        for payload, status in cases:
            with self.subTest(status=status):
                result = self.qualify(self.build(dividend_payload=payload))
                self.assertIs(result.status, status)
                self.assertIn(
                    joined.RouteLocalNonpayerReason.NONPAYER_SOURCE_NOT_ESTABLISHED,
                    result.reasons,
                )

    def test_post_boundary_capture_and_relevant_class_ambiguity_block(self):
        post_boundary = self.qualify(self.build(
            nonpayer_capture="2026-04-01T12:00:00Z"))
        self.assertIs(post_boundary.status,
                      joined.RouteLocalVerifiedNonpayerStatus.NONPAYER_UNAVAILABLE)
        self.assertIn(joined.RouteLocalNonpayerReason.POST_AUTHORITY_BOUNDARY_CAPTURE,
                      post_boundary.reasons)
        ambiguous = self.qualify(self.build(competing_class=True))
        self.assertIs(ambiguous.status,
                      joined.RouteLocalVerifiedNonpayerStatus.NONPAYER_UNSUPPORTED)
        self.assertIn(
            joined.RouteLocalNonpayerReason.RELEVANT_CLASS_NOT_UNIQUELY_ESTABLISHED,
            ambiguous.reasons,
        )


if __name__ == "__main__":
    unittest.main()
