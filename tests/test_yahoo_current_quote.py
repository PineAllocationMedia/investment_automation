import ast
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timezone
from decimal import Decimal
import inspect
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from economic_facts import yahoo_current_quote as quote
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from tests.test_sec_current_security_eps_qualification import (
    CurrentSecurityEPSQualificationTests,
)
from tests.yahoo_quote_fixtures import CAPTURED_AT, MARKET_EPOCH, chart_response


class YahooCurrentQuoteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.quote_archive = YahooQuoteArchive(Path(temporary.name).resolve() / "quotes")
        self.security = CurrentSecurityEPSQualificationTests(methodName="runTest")
        self.security.setUp()
        self.addCleanup(self.security.doCleanups)

    def publish(self, raw=None, *, symbol="FICT", captured_at=CAPTURED_AT):
        return self.quote_archive._capture_live(
            chart_response() if raw is None else raw,
            symbol=symbol,
            captured_at=captured_at,
        )

    def request(self, *, security_request=None, raw=None, symbol="FICT",
                captured_at=CAPTURED_AT, expected_changes=None):
        security_request = (self.security.inputs() if security_request is None
                            else security_request)
        security = self.security.qualify_request(security_request)
        receipt = self.publish(raw, symbol=symbol, captured_at=captured_at)
        extraction = quote.extract_yahoo_current_quote(self.quote_archive, receipt.receipt_id)
        values = {
            "security_request": security_request,
            "expected_security_semantic_id": security.semantic_id,
            "expected_security_evidence_id": security.evidence_id,
            "quote_receipt_id": receipt.receipt_id,
            "expected_quote_semantic_id": extraction.semantic_id,
            "expected_quote_evidence_id": extraction.evidence_id,
        }
        values.update(expected_changes or {})
        return quote.YahooCurrentQuoteQualificationRequest(**values)

    def qualify(self, **changes):
        request = self.request(**changes)
        return quote.qualify_yahoo_current_quote(
            self.quote_archive,
            self.security.current_archive,
            self.security.submissions_archive,
            self.security.filing_archive,
            self.security.sec_archive,
            self.security.nasdaq_archive,
            request,
        )

    def test_positive_exact_pr5b_nasdaq_quote_route(self):
        result = self.qualify()
        self.assertIs(result.status, quote.CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.price, Decimal("123.4500"))
        self.assertEqual(result.quote_extraction.price_source_text, "123.4500")
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.unit, "CURRENCY_PER_SHARE")
        self.assertEqual(result.symbol, "FICT")
        self.assertEqual(result.venue_id, "NASDAQ_GLOBAL_SELECT")
        self.assertEqual(result.instrument_type, "EQUITY")
        self.assertEqual(result.provider_market_epoch, MARKET_EPOCH)
        self.assertEqual(result.provider_market_timestamp, "2026-02-25T11:00:00Z")
        self.assertEqual(result.captured_at, CAPTURED_AT)
        self.assertEqual(result.route_local_security_key,
                         result.upstream_security.route_local_security_key)
        self.assertRegex(result.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(result.evidence_id, r"^[0-9a-f]{64}$")
        self.assertEqual(result.license_status, "UNKNOWN")
        self.assertEqual(result.use_status, "REVIEW_REQUIRED")

    def test_fresh_pr5b_replay_and_closed_request_surface(self):
        request = self.request()
        with patch.object(
            quote, "qualify_sec_current_security_eps",
            wraps=quote.qualify_sec_current_security_eps,
        ) as replay:
            result = quote.qualify_yahoo_current_quote(
                self.quote_archive, self.security.current_archive,
                self.security.submissions_archive, self.security.filing_archive,
                self.security.sec_archive, self.security.nasdaq_archive, request)
        self.assertEqual(replay.call_count, 1)
        self.assertIs(result.status, quote.CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED)
        self.assertEqual(tuple(field.name for field in fields(
            quote.YahooCurrentQuoteQualificationRequest)), (
                "security_request", "expected_security_semantic_id",
                "expected_security_evidence_id", "quote_receipt_id",
                "expected_quote_semantic_id", "expected_quote_evidence_id"))
        for keyword in ("qualified", "price", "currency", "symbol", "authority", "same_basis"):
            with self.subTest(keyword=keyword), self.assertRaises(TypeError):
                quote.YahooCurrentQuoteQualificationRequest(
                    request.security_request,
                    request.expected_security_semantic_id,
                    request.expected_security_evidence_id,
                    request.quote_receipt_id,
                    request.expected_quote_semantic_id,
                    request.expected_quote_evidence_id,
                    **{keyword: True},
                )

    def test_exact_decimal_high_precision_and_no_fallback_price(self):
        raw = chart_response(price_text="123.4500000000000000000000001")
        extraction = quote.extract_yahoo_current_quote(
            self.quote_archive, self.publish(raw).receipt_id)
        self.assertEqual(extraction.price, Decimal("123.4500000000000000000000001"))
        self.assertEqual(extraction.price_source_text, "123.4500000000000000000000001")

        for price_text in ("0", "-1", '"123.45"', "null"):
            with self.subTest(price=price_text):
                raw = chart_response(price_text=price_text)
                extraction = quote.extract_yahoo_current_quote(
                    self.quote_archive, self.publish(raw, captured_at="2026-02-25T12:00:01Z").receipt_id)
                self.assertIs(extraction.status, quote.QuoteExtractionStatus.QUOTE_UNAVAILABLE)
                self.assertIn(quote.CurrentQuoteReason.PRICE_INVALID, extraction.reasons)
        raw = chart_response(omit=("regularMarketPrice",), unknown_meta={"previousClose": 99})
        extraction = quote.extract_yahoo_current_quote(
            self.quote_archive, self.publish(raw, captured_at="2026-02-25T12:00:02Z").receipt_id)
        self.assertIsNone(extraction.price)
        self.assertIn(quote.CurrentQuoteReason.PRICE_INVALID, extraction.reasons)
        nonfinite = chart_response().replace(b"123.4500", b"NaN")
        extraction = quote.extract_yahoo_current_quote(
            self.quote_archive,
            self.publish(nonfinite, captured_at="2026-02-25T12:00:03Z").receipt_id)
        self.assertIs(extraction.status, quote.QuoteExtractionStatus.QUOTE_UNAVAILABLE)

    def test_currency_symbol_venue_and_instrument_fail_closed(self):
        cases = (
            (chart_response(symbol="OTHER"), quote.QuoteExtractionStatus.SOURCE_CONFLICT,
             quote.CurrentQuoteReason.SYMBOL_MISMATCH),
            (chart_response(currency="CAD"), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.CURRENCY_MISMATCH),
            (chart_response(omit=("currency",)), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.CURRENCY_MISMATCH),
            (chart_response(exchange_name="NGM", full_exchange_name="NasdaqGM"),
             quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.VENUE_MISMATCH),
            (chart_response(instrument_type="ETF"), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED),
            (chart_response(instrument_type="MUTUALFUND"), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED),
            (chart_response(instrument_type="INDEX"), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED),
            (chart_response(instrument_type="CRYPTOCURRENCY"), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED),
            (chart_response(omit=("instrumentType",)), quote.QuoteExtractionStatus.QUOTE_UNSUPPORTED,
             quote.CurrentQuoteReason.INSTRUMENT_TYPE_UNSUPPORTED),
        )
        for index, (raw, status, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                receipt = self.publish(raw, captured_at=f"2026-02-25T12:01:{index:02d}Z")
                extraction = quote.extract_yahoo_current_quote(
                    self.quote_archive, receipt.receipt_id)
                self.assertIs(extraction.status, status)
                self.assertIn(reason, extraction.reasons)

    def test_timestamp_contract_and_chronology(self):
        for value in (None, "1772017200", 1772017200.0, True):
            with self.subTest(value=value):
                raw = chart_response(market_time=value)
                extraction = quote.extract_yahoo_current_quote(
                    self.quote_archive,
                    self.publish(raw, captured_at="2026-02-25T12:02:00Z").receipt_id)
                self.assertIn(quote.CurrentQuoteReason.PROVIDER_TIMESTAMP_INVALID,
                              extraction.reasons)
        missing = quote.extract_yahoo_current_quote(
            self.quote_archive,
            self.publish(
                chart_response(omit=("regularMarketTime",)),
                captured_at="2026-02-25T12:02:01Z").receipt_id)
        self.assertIn(quote.CurrentQuoteReason.PROVIDER_TIMESTAMP_INVALID,
                      missing.reasons)
        equal_epoch = int(datetime.fromisoformat(CAPTURED_AT.replace("Z", "+00:00")).timestamp())
        equal = self.qualify(raw=chart_response(market_time=equal_epoch))
        self.assertIs(equal.status, quote.CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED)
        future = self.qualify(raw=chart_response(market_time=equal_epoch + 1))
        self.assertIs(future.status, quote.CurrentQuoteStatus.SOURCE_CONFLICT)
        self.assertIn(quote.CurrentQuoteReason.QUOTE_AFTER_CAPTURE, future.reasons)

    def test_source_structure_provider_error_multiple_results_and_duplicate_keys(self):
        cases = (
            (chart_response(provider_error={"code": "Not Found"}),
             quote.QuoteExtractionStatus.QUOTE_UNAVAILABLE),
            (chart_response(result_count=2), quote.QuoteExtractionStatus.SOURCE_CONFLICT),
            (b'{"chart":{"result":null,"error":null}}',
             quote.QuoteExtractionStatus.QUOTE_UNAVAILABLE),
            (b'{"chart":{"result":[],"result":[],"error":null}}',
             quote.QuoteExtractionStatus.QUOTE_UNAVAILABLE),
        )
        for index, (raw, status) in enumerate(cases):
            with self.subTest(index=index):
                extraction = quote.extract_yahoo_current_quote(
                    self.quote_archive,
                    self.publish(raw, captured_at=f"2026-02-25T12:03:{index:02d}Z").receipt_id)
                self.assertIs(extraction.status, status)

    def test_unknown_fields_do_not_grant_semantics_but_change_evidence(self):
        first = self.publish(chart_response(), captured_at="2026-02-25T12:04:00Z")
        second = self.publish(
            chart_response(unknown_meta={"unreviewedProviderField": "ignored"}),
            captured_at="2026-02-25T12:04:00Z")
        left = quote.extract_yahoo_current_quote(self.quote_archive, first.receipt_id)
        right = quote.extract_yahoo_current_quote(self.quote_archive, second.receipt_id)
        self.assertEqual(left.semantic_id, right.semantic_id)
        self.assertNotEqual(left.evidence_id, right.evidence_id)

        numeric = self.publish(
            chart_response(price_text="123.45"),
            captured_at="2026-02-25T12:04:00Z")
        equivalent = quote.extract_yahoo_current_quote(
            self.quote_archive, numeric.receipt_id)
        self.assertEqual(left.semantic_id, equivalent.semantic_id)
        self.assertNotEqual(left.evidence_id, equivalent.evidence_id)

    def test_pr5b_failure_symbol_join_and_forged_identity_block(self):
        unsupported_request = self.security.inputs(nasdaq=self.security.nasdaq(symbol="OTHER"))
        blocked = self.qualify(security_request=unsupported_request)
        self.assertIsNot(blocked.status, quote.CurrentQuoteStatus.CURRENT_QUOTE_ESTABLISHED)
        self.assertIn(quote.CurrentQuoteReason.PR5B_NOT_ESTABLISHED, blocked.reasons)

        symbol = self.qualify(raw=chart_response(symbol="OTHER"))
        self.assertIs(symbol.status, quote.CurrentQuoteStatus.SOURCE_CONFLICT)
        self.assertIn(quote.CurrentQuoteReason.SYMBOL_MISMATCH, symbol.reasons)

        forged = self.qualify(expected_changes={"expected_security_semantic_id": "0" * 64})
        self.assertIs(forged.status, quote.CurrentQuoteStatus.SOURCE_CONFLICT)
        self.assertIn(quote.CurrentQuoteReason.SOURCE_CONFLICT, forged.reasons)

    def test_capture_replay_does_not_select_newer_receipt(self):
        old_request = self.request(
            raw=chart_response(price_text="100", market_time=MARKET_EPOCH),
            captured_at="2026-02-25T12:05:00Z")
        self.publish(
            chart_response(price_text="200", market_time=MARKET_EPOCH + 60),
            captured_at="2026-02-25T12:06:00Z")
        result = quote.qualify_yahoo_current_quote(
            self.quote_archive, self.security.current_archive,
            self.security.submissions_archive, self.security.filing_archive,
            self.security.sec_archive, self.security.nasdaq_archive, old_request)
        self.assertEqual(result.price, Decimal("100"))
        self.assertEqual(result.quote_extraction.receipt.receipt_id,
                         old_request.quote_receipt_id)

    def test_extraction_identities_are_hash_seed_deterministic(self):
        receipt = self.publish()
        script = """
import sys
from economic_facts.yahoo_quote_archive import YahooQuoteArchive
from economic_facts.yahoo_current_quote import extract_yahoo_current_quote
item = extract_yahoo_current_quote(YahooQuoteArchive(sys.argv[1]), sys.argv[2])
print(item.semantic_id)
print(item.evidence_id)
"""
        outputs = []
        for seed in ("1", "777"):
            environment = dict(os.environ)
            environment["PYTHONHASHSEED"] = seed
            outputs.append(subprocess.check_output(
                [sys.executable, "-B", "-c", script,
                 str(self.quote_archive.root), receipt.receipt_id],
                text=True, env=environment,
            ))
        self.assertEqual(outputs[0], outputs[1])

    def test_explicit_nonclaims_and_immutable_results(self):
        result = self.qualify()
        self.assertIn(
            quote.CurrentQuoteLimitation.QUOTE_TO_PR5C_BASIS_BRIDGE_NOT_ESTABLISHED,
            result.limitations)
        self.assertIn(quote.CurrentQuoteLimitation.NO_PR4B1_OBSERVED_PRICE_ROOT,
                      result.limitations)
        forbidden = {
            "eps_basis_bridge", "same_basis", "split_basis_established",
            "final_admission", "buy", "sell", "hold", "recommendation",
            "allocation", "expected_return", "quality", "durability",
            "confidence_score",
        }
        self.assertTrue(forbidden.isdisjoint({field.name for field in fields(type(result))}))
        self.assertTrue(forbidden.isdisjoint({field.name for field in fields(
            quote.YahooCurrentQuoteQualificationRequest)}))
        with self.assertRaises(FrozenInstanceError):
            result.price = Decimal("1")
        source = inspect.getsource(quote)
        self.assertNotIn("expected_return_assumptions", source)
        self.assertNotIn("previousClose", source)


class YahooQuoteDependencyTests(unittest.TestCase):
    def test_dependency_direction_and_v1_runtime_isolation(self):
        root = Path(__file__).resolve().parents[1]
        modules = {
            "yahoo_quote_archive": set(),
            "yahoo_quote_acquisition": {"yahoo_quote_archive"},
            "yahoo_current_quote": {
                "nasdaq_listed_archive", "sec_archive",
                "sec_current_security_eps_qualification", "sec_filing_archive",
                "sec_submissions_archive", "sec_ticker_exchange_archive",
                "source_authority", "yahoo_quote_archive",
            },
        }
        for name, allowed_relative in modules.items():
            tree = ast.parse((root / "economic_facts" / f"{name}.py").read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertIn(node.module, allowed_relative, (name, node.module))
                    else:
                        self.assertIn(node.module.split(".")[0], sys.stdlib_module_names)
                elif isinstance(node, ast.Import):
                    self.assertTrue(all(
                        alias.name.split(".")[0] in sys.stdlib_module_names
                        for alias in node.names), name)

        protected = [root / "main.py"]
        for directory in ("src", "pit_comparison", "scripts"):
            protected.extend((root / directory).rglob("*.py"))
        names = set(modules)
        for path in protected:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(set((node.module or "").split(".")) & names,
                                     str(path))
                    self.assertFalse({alias.name for alias in node.names} & names,
                                     str(path))
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(
                        set(alias.name.split(".")) & names for alias in node.names),
                        str(path))


if __name__ == "__main__":
    unittest.main()
