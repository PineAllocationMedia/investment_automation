from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import ast
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from economic_facts import vfv_current_evidence as evidence
from economic_facts.source_authority import (
    AvailabilitySemantics, PublicationSemantics, UseStatus,
)
from economic_facts.vanguard_vfv_archive import VanguardVFVArtifactFamily
from tests.vfv_current_evidence_fixtures import (
    etf_facts_pdf,
    factsheet_pdf,
    product_html,
    publish_bundle,
    request_for,
)


class VFVCurrentEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "vfv"
        self.archive, self.product, self.etf, self.factsheet = publish_bundle(self.root)

    def qualify(self, *, root=None, product_raw=None, etf_raw=None,
                factsheet_raw=None, request_changes=None,
                product_time="2026-09-30T18:00:00-04:00",
                document_time="2026-09-30T18:05:00-04:00"):
        if any(value is not None for value in (root, product_raw, etf_raw, factsheet_raw)):
            target = root or self.root.parent / ("case-" + str(len(list(self.root.parent.iterdir()))))
            archive, product, etf, factsheet = publish_bundle(
                target,
                product_raw=product_raw,
                etf_raw=etf_raw,
                factsheet_raw=factsheet_raw,
                product_time=product_time,
                document_time=document_time,
            )
        else:
            archive, product, etf, factsheet = (
                self.archive, self.product, self.etf, self.factsheet)
        request = request_for(archive, product, etf, factsheet,
                              **(request_changes or {}))
        return evidence.qualify_vfv_current_evidence(archive, request)

    def test_positive_route_exact_typed_facts_and_contract_versions(self):
        result = self.qualify()
        self.assertIs(result.status, evidence.VFVCurrentEvidenceStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.contract_version,
                         "2026-09-30-vfv-current-evidence-foundation-v1")
        self.assertEqual(result.qualification_version,
                         "2026-09-30-vfv-current-evidence-qualification-v1")
        self.assertEqual(result.identity, evidence.VFVFundIdentity(
            "Vanguard S&P 500 Index ETF", "ETF Units", "Toronto Stock Exchange",
            "VFV", "CA92205Y1051", "CAD", "CAD", "S&P 500 Index",
            "Vanguard S&P 500 ETF", "United States"))
        self.assertEqual(result.market_observation.market_price, Decimal("193.1200"))
        self.assertIs(result.market_observation.observation_type,
                      evidence.VFVObservationType.ISSUER_DAILY_MARKET_PRICE)
        self.assertEqual(result.market_observation.currency, "CAD")
        self.assertIs(result.market_observation.unit,
                      evidence.VFVFactUnit.CAD_PER_ETF_UNIT)
        self.assertEqual(result.market_observation.field_effective_as_of, "2026-09-30")
        self.assertEqual(result.market_observation.nav, Decimal("193.0785"))
        self.assertIs(result.market_observation.nav_observation_type,
                      evidence.VFVObservationType.ISSUER_DAILY_NAV)

    def test_expenses_remain_distinct_and_latest_explicit_period_wins(self):
        result = self.qualify()
        self.assertEqual(result.expenses.management_fee, Decimal("0.08"))
        self.assertEqual(result.expenses.mer, Decimal("0.08"))
        self.assertEqual(result.expenses.mer_period_end, "2026-06-30")
        self.assertEqual(result.expenses.ter, Decimal("0.00"))
        self.assertEqual(result.expenses.ter_period_end, "2026-06-30")
        self.assertTrue(result.expenses.mer_annualized)
        self.assertTrue(result.expenses.ter_annualized)
        self.assertNotEqual(result.expenses.mer_period_end, "2025-12-31")
        source = inspect.getsource(evidence.qualify_vfv_current_evidence)
        self.assertNotIn("management_fee +", source)
        self.assertNotIn("mer +", source)

    def test_distribution_is_exact_not_annualized_or_extrapolated(self):
        result = self.qualify()
        event = result.distributions.latest_event
        self.assertEqual(result.distributions.distribution_frequency, "Quarterly")
        self.assertEqual(event.type, "Income")
        self.assertEqual(event.cash_distribution_per_unit, Decimal("0.40776"))
        self.assertEqual(event.reinvestment_distribution_per_unit, Decimal("0.00000"))
        self.assertEqual(event.total_distribution_per_unit, Decimal("0.40776"))
        self.assertEqual((event.ex_date, event.record_date, event.payment_date),
                         ("2026-09-28", "2026-09-28", "2026-10-06"))
        self.assertEqual(result.distributions.trailing_distribution_yield,
                         Decimal("0.84"))
        self.assertIs(result.distributions.trailing_yield_semantics,
                      evidence.VFVTrailingYieldSemantics.
                      ISSUER_TRAILING_12_MONTH_DISTRIBUTION_YIELD)
        self.assertNotIn("annualized_latest_distribution", {
            field.name for field in fields(evidence.VFVDistributionFacts)})

    def test_trailing_fund_portfolio_pe_and_currency_exposure_only(self):
        result = self.qualify()
        self.assertEqual(result.trailing_valuation.weighted_pe, Decimal("25.2"))
        self.assertIs(result.trailing_valuation.metric_subject,
                      evidence.VFVValuationMetricSubject.FUND_PORTFOLIO)
        self.assertIs(result.trailing_valuation.metric_semantics,
                      evidence.VFVValuationMetricSemantics.PROVIDER_TRAILING_WEIGHTED_P_E)
        self.assertEqual(result.currency_exposure, evidence.VFVCurrencyExposureFacts(
            "CAD", "CAD", "USD", False, "2026-08-31"))
        forbidden = {"forward_pe", "terminal_pe", "fair_value_multiple", "fx_forecast",
                     "fx_expected_return", "currency_adjusted_expected_return"}
        for record in (evidence.VFVTrailingValuation,
                       evidence.VFVCurrencyExposureFacts,
                       evidence.VFVCurrentEvidenceQualification):
            self.assertTrue(forbidden.isdisjoint({field.name for field in fields(record)}))

    def test_tracked_index_and_performance_series_are_separate(self):
        result = self.qualify()
        self.assertEqual(result.identity.tracked_economic_index, "S&P 500 Index")
        self.assertEqual(result.performance_series_label,
                         "S&P 500 (CAD NY Rate) NTR 15%")
        self.assertNotEqual(result.identity.tracked_economic_index,
                            result.performance_series_label)

    def test_exact_decimal_tokens_never_become_float(self):
        result = self.qualify(product_raw=product_html(market_price="193.12000001"))
        self.assertEqual(result.market_observation.market_price, Decimal("193.12000001"))
        self.assertIs(type(result.market_observation.market_price), Decimal)
        for record in (result.market_observation, result.expenses,
                       result.distributions.latest_event, result.trailing_valuation):
            self.assertNotIn(float, {type(getattr(record, field.name))
                                     for field in fields(record)})

    def test_nav_cannot_substitute_for_missing_market_price(self):
        result = self.qualify(product_raw=product_html(market_price="—", nav="999.1234"))
        self.assertIs(result.status, evidence.VFVCurrentEvidenceStatus.UNAVAILABLE)
        self.assertIn(evidence.VFVCurrentEvidenceReason.PRICE_UNAVAILABLE, result.reasons)
        self.assertIsNone(result.market_observation)

    def test_ticker_alone_or_missing_primary_identity_cannot_qualify(self):
        minimal = factsheet_pdf(
            fund_name="Unrelated document", isin="", exchange="Other", currency="USD")
        result = self.qualify(factsheet_raw=minimal)
        self.assertIs(result.status, evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
        self.assertIn(evidence.VFVCurrentEvidenceReason.IDENTITY_MISMATCH, result.reasons)
        self.assertIsNone(result.identity)

    def test_wrong_isin_ticker_or_exchange_is_source_conflict(self):
        cases = (
            {"isin": "CA0000000000"},
            {"ticker": "OTHER"},
            {"exchange": "Other Exchange"},
        )
        for index, changes in enumerate(cases):
            with self.subTest(changes=changes):
                result = self.qualify(
                    root=self.root.parent / f"identity-{index}",
                    factsheet_raw=factsheet_pdf(**changes))
                self.assertIs(result.status,
                              evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
                self.assertIn(evidence.VFVCurrentEvidenceReason.IDENTITY_MISMATCH,
                              result.reasons)

    def test_tracked_index_disagreement_is_not_performance_label_conflict(self):
        result = self.qualify(factsheet_raw=factsheet_pdf(index="S&P/TSX 60 Index"))
        self.assertIs(result.status, evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
        self.assertEqual(result.reasons,
                         (evidence.VFVCurrentEvidenceReason.TRACKED_INDEX_DISAGREEMENT,))

    def test_same_expense_metric_same_date_conflicts_but_different_period_does_not(self):
        conflict = self.qualify(etf_raw=etf_facts_pdf(period="June 30, 2026"))
        self.assertIs(conflict.status, evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
        self.assertIn(evidence.VFVCurrentEvidenceReason.SAME_METRIC_SAME_DATE_CONFLICT,
                      conflict.reasons)
        self.assertIs(self.qualify().status, evidence.VFVCurrentEvidenceStatus.AVAILABLE)

    def test_ambiguous_expense_period_is_unavailable_and_never_averaged(self):
        result = self.qualify(
            etf_raw=etf_facts_pdf(period="unknown"),
            factsheet_raw=factsheet_pdf(mer_period="unknown", ter_period="unknown"))
        self.assertIs(result.status, evidence.VFVCurrentEvidenceStatus.UNAVAILABLE)
        self.assertIn(evidence.VFVCurrentEvidenceReason.EXPENSE_PERIOD_AMBIGUOUS,
                      result.reasons)

    def test_distribution_and_field_chronology_fail_closed(self):
        distribution = self.qualify(product_raw=product_html(
            ex_date="Oct 08 2026", record_date="Oct 07 2026",
            payment_date="Oct 06 2026"))
        self.assertIs(distribution.status,
                      evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
        self.assertIn(evidence.VFVCurrentEvidenceReason.FIELD_CHRONOLOGY_INVALID,
                      distribution.reasons)
        future_price = self.qualify(product_raw=product_html(market_date="Oct 01 2026"))
        self.assertIs(future_price.status,
                      evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)

    def test_unsupported_source_structure_and_free_source_field_are_distinct(self):
        structure = self.qualify(factsheet_raw=b"%PDF-1.7\nnot a complete pdf")
        self.assertIs(structure.status, evidence.VFVCurrentEvidenceStatus.UNSUPPORTED)
        self.assertIn(evidence.VFVCurrentEvidenceReason.SOURCE_STRUCTURE_UNSUPPORTED,
                      structure.reasons)
        field = self.qualify(factsheet_raw=factsheet_pdf(exposure="", hedged=""))
        self.assertIs(field.status, evidence.VFVCurrentEvidenceStatus.UNSUPPORTED)
        self.assertIn(
            evidence.VFVCurrentEvidenceReason.
            REQUIRED_FIELD_UNSUPPORTED_BY_REVIEWED_FREE_SOURCE,
            field.reasons)

    def test_expected_semantic_or_evidence_mismatch_is_source_conflict(self):
        for key in ("expected_product_semantic_id", "expected_etf_facts_evidence_id",
                    "expected_factsheet_semantic_id"):
            with self.subTest(key=key):
                result = self.qualify(request_changes={key: "0" * 64})
                self.assertIs(result.status,
                              evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT)
                self.assertEqual(result.reasons, (
                    evidence.VFVCurrentEvidenceReason.REPLAY_IDENTITY_MISMATCH,))

    def test_all_four_statuses_and_reason_mapping_are_closed(self):
        available = self.qualify()
        unavailable = self.qualify(product_raw=product_html(market_price="missing"))
        unsupported = self.qualify(factsheet_raw=factsheet_pdf(exposure=""))
        conflict = self.qualify(request_changes={"expected_product_evidence_id": "0" * 64})
        self.assertEqual({item.status for item in (
            available, unavailable, unsupported, conflict)},
            set(evidence.VFVCurrentEvidenceStatus))
        mappings = {
            evidence.VFVCurrentEvidenceStatus.SOURCE_CONFLICT: {
                evidence.VFVCurrentEvidenceReason.REPLAY_IDENTITY_MISMATCH,
                evidence.VFVCurrentEvidenceReason.IDENTITY_MISMATCH,
                evidence.VFVCurrentEvidenceReason.TRACKED_INDEX_DISAGREEMENT,
                evidence.VFVCurrentEvidenceReason.SAME_METRIC_SAME_DATE_CONFLICT,
                evidence.VFVCurrentEvidenceReason.FIELD_CHRONOLOGY_INVALID,
            },
            evidence.VFVCurrentEvidenceStatus.UNSUPPORTED: {
                evidence.VFVCurrentEvidenceReason.SOURCE_STRUCTURE_UNSUPPORTED,
                evidence.VFVCurrentEvidenceReason.
                REQUIRED_FIELD_UNSUPPORTED_BY_REVIEWED_FREE_SOURCE,
            },
            evidence.VFVCurrentEvidenceStatus.UNAVAILABLE: {
                evidence.VFVCurrentEvidenceReason.MISSING_REQUIRED_PRIMARY_ARTIFACT,
                evidence.VFVCurrentEvidenceReason.MUTABLE_PAGE_NOT_CAPTURED,
                evidence.VFVCurrentEvidenceReason.PRICE_UNAVAILABLE,
                evidence.VFVCurrentEvidenceReason.REQUIRED_FIELD_UNAVAILABLE,
                evidence.VFVCurrentEvidenceReason.EXPENSE_PERIOD_AMBIGUOUS,
            },
        }
        for result in (unavailable, unsupported, conflict):
            self.assertTrue(set(result.reasons) <= mappings[result.status])
        self.assertEqual(set(evidence.VFVCurrentEvidenceReason),
                         set().union(*mappings.values()))

    def test_field_specific_provenance_is_closed_unique_and_capture_bound(self):
        result = self.qualify()
        roles = [item.role for item in result.fact_evidence]
        self.assertEqual(len(roles), len(set(roles)))
        required = {
            role for role in evidence.VFVFactRole
            if role is not evidence.VFVFactRole.PERFORMANCE_SERIES_LABEL
        }
        self.assertEqual(set(roles), required | {
            evidence.VFVFactRole.PERFORMANCE_SERIES_LABEL})
        for item in result.fact_evidence:
            self.assertIs(type(item.role), evidence.VFVFactRole)
            self.assertIsNone(item.publication_timestamp)
            self.assertIs(item.publication_semantics, PublicationSemantics.UNKNOWN)
            self.assertIs(item.availability_semantics,
                          AvailabilitySemantics.CAPTURE_BOUND)
            self.assertEqual(item.availability_timestamp, item.retrieved_at)
            self.assertIn(item.artifact_family, set(VanguardVFVArtifactFamily))
            self.assertTrue(item.source_locator.startswith(("/html/", "/pdf/")))

    def test_semantic_identity_survives_recapture_evidence_identity_does_not(self):
        first = self.qualify()
        second = self.qualify(
            root=self.root.parent / "recapture",
            product_time="2026-09-30T19:00:00-04:00",
            document_time="2026-09-30T19:05:00-04:00")
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)
        self.assertNotEqual(first.latest_capture_at, second.latest_capture_at)

    def test_authority_scope_use_metadata_and_limitations_are_exact(self):
        result = self.qualify()
        self.assertIs(result.factual_authority_scope,
                      evidence.VFVFactualAuthorityScope.CURRENT_ONLY)
        self.assertIs(result.license_status, UseStatus.UNKNOWN)
        self.assertIs(result.use_status, UseStatus.REVIEW_REQUIRED)
        self.assertEqual(set(result.limitations), set(evidence.VFVCurrentEvidenceLimitation))
        required = {
            "NO_HISTORICAL_AS_OF_AUTHORITY", "NO_PIT_AUTHORITY",
            "NO_EXECUTABLE_QUOTE_AUTHORITY", "NO_FORWARD_ESTIMATE_AUTHORITY",
            "NO_EXPECTED_RETURN_ANALYTICAL_AUTHORITY", "NO_RECOMMENDATION_OR_ALLOCATION",
            "NO_EXECUTION_OR_PRODUCTION_AUTHORITY", "NO_GENERIC_BENCHMARK_AUTHORITY",
            "NO_COMMERCIAL_INGESTION_OR_REDISTRIBUTION_AUTHORITY",
            "S_AND_P_REUSE_AUTHORITY_NOT_ESTABLISHED",
        }
        self.assertTrue(required <= {item.value for item in result.limitations})

    def test_historical_forward_executable_and_cusip_fields_are_absent(self):
        forbidden = {
            "pb", "roe", "dividend_yield", "historical_5y_earnings_growth",
            "historical_etf_return", "historical_index_return", "cagr",
            "historical_distribution_growth", "cusip", "forward_eps",
            "forward_earnings_growth", "forward_pe", "bid", "ask",
            "broker_executable_price", "expected_return", "current_at",
        }
        records = (
            evidence.VFVFundIdentity, evidence.VFVMarketObservation,
            evidence.VFVExpenseFacts, evidence.VFVDistributionFacts,
            evidence.VFVTrailingValuation, evidence.VFVCurrencyExposureFacts,
            evidence.VFVCurrentEvidenceQualification,
            evidence.VFVCurrentEvidenceRequest,
        )
        for record in records:
            self.assertTrue(forbidden.isdisjoint({field.name.casefold()
                                                  for field in fields(record)}))
        source = inspect.getsource(evidence)
        self.assertNotIn("previousClose", source)
        self.assertNotIn("historical CAGR", source)

    def test_request_has_only_receipt_and_expected_identity_fields(self):
        self.assertEqual([field.name for field in fields(evidence.VFVCurrentEvidenceRequest)], [
            "product_page_receipt_id", "expected_product_semantic_id",
            "expected_product_evidence_id", "etf_facts_receipt_id",
            "expected_etf_facts_semantic_id", "expected_etf_facts_evidence_id",
            "factsheet_receipt_id", "expected_factsheet_semantic_id",
            "expected_factsheet_evidence_id",
        ])
        with self.assertRaises(FrozenInstanceError):
            request_for(self.archive, self.product, self.etf, self.factsheet).product_page_receipt_id = "x"

    def test_hash_seed_determinism(self):
        request = request_for(self.archive, self.product, self.etf, self.factsheet)
        script = """
import sys
from economic_facts.vanguard_vfv_archive import VanguardVFVArchive
from economic_facts.vfv_current_evidence import VFVCurrentEvidenceRequest, qualify_vfv_current_evidence
request = VFVCurrentEvidenceRequest(*sys.argv[2:])
result = qualify_vfv_current_evidence(VanguardVFVArchive(sys.argv[1]), request)
print(result.semantic_id)
print(result.evidence_id)
"""
        arguments = [str(self.root)] + [getattr(request, field.name)
                                       for field in fields(request)]
        outputs = []
        for seed in ("1", "777"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            outputs.append(subprocess.check_output(
                [sys.executable, "-B", "-c", script, *arguments],
                text=True, env=environment))
        self.assertEqual(outputs[0], outputs[1])

    def test_archive_corruption_remains_exception_not_economic_status(self):
        path = self.root / "objects" / self.product.content_sha256
        os.chmod(path, 0o600)
        path.write_bytes(b"corrupt")
        with self.assertRaises(evidence.VFVCurrentEvidenceError):
            evidence.qualify_vfv_current_evidence(
                self.archive,
                request_for(self.archive, self.product, self.etf, self.factsheet))


class VFVCurrentEvidenceIsolationTests(unittest.TestCase):
    def test_dependency_direction_and_runtime_isolation(self):
        root = Path(__file__).resolve().parents[1]
        modules = {
            "vanguard_vfv_archive",
            "vanguard_vfv_acquisition",
            "vfv_current_evidence",
        }
        forbidden_imports = {
            "src.expected_return_engine", "src.expected_return_assumptions",
            "src.expected_return_pr5e_adapter", "main", "allocation",
        }
        for name in modules:
            tree = ast.parse((root / "economic_facts" / f"{name}.py").read_text())
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    imported.add(node.module or "")
                elif isinstance(node, ast.Import):
                    imported.update(alias.name for alias in node.names)
            self.assertTrue(forbidden_imports.isdisjoint(imported), name)

        protected = [root / "main.py"]
        for directory in ("src", "pit_comparison"):
            protected.extend((root / directory).rglob("*.py"))
        for path in protected:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(set((node.module or "").split(".")) & modules,
                                     str(path))
                    self.assertFalse({alias.name for alias in node.names} & modules,
                                     str(path))
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(set(alias.name.split(".")) & modules
                                         for alias in node.names), str(path))


if __name__ == "__main__":
    unittest.main()
