"""Adversarial tests for source-neutral CURRENT executable-entry evidence."""
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import ast
import inspect
import json
from pathlib import Path
import unittest

from economic_facts import executable_entry_evidence as entry
from economic_facts.source_authority import (
    AvailabilitySemantics,
    PublicationSemantics,
    UseStatus,
)
from economic_facts.yahoo_current_quote import QualifiedCurrentQuote


CONTEXT_ID = "execctx:" + "a" * 64
INSTRUMENT_ID = "instrument:" + "b" * 64


def provenance(seed="1", **changes):
    values = {
        "schema_version": entry.EXECUTABLE_ENTRY_EVIDENCE_SCHEMA_VERSION,
        "source_owner": f"Synthetic Source Owner {seed}",
        "source_descriptor": f"authenticated synthetic evidence {seed}",
        "source_locator": f"fixture:entry:{seed}",
        "receipt_id": seed * 64,
        "content_sha256": chr(ord(seed) + 1) * 64,
        "capture_sha256": chr(ord(seed) + 2) * 64,
        "retrieved_at": "2026-10-03T10:00:00-04:00",
        "publication_timestamp": None,
        "publication_semantics": PublicationSemantics.UNKNOWN,
        "availability_semantics": AvailabilitySemantics.CAPTURE_BOUND,
        "license_status": UseStatus.UNKNOWN,
        "use_status": UseStatus.REVIEW_REQUIRED,
        "freshness": entry.CurrentEvidenceFreshness.CURRENT_SAME_RUN_CAPTURE,
    }
    values.update(changes)
    return entry.EvidenceProvenance(**values)


def eligibility(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "state": entry.EligibilityState.ELIGIBLE,
        "transaction_currency": "EUR",
        "provenance": provenance("1"),
    }
    values.update(changes)
    return entry.EligibilityEvidence(**values)


def funding(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "state": entry.FundingAvailabilityState.SETTLED_AND_AVAILABLE,
        "funding_currency": "EUR",
        "provenance": provenance("4"),
    }
    values.update(changes)
    return entry.FundingEvidence(**values)


def commission(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "amount": Decimal("1.2500"),
        "currency": "EUR",
        "semantics": entry.CommissionSemantics.FLAT_PER_ORDER_TRANSACTION_CURRENCY,
        "provenance": provenance("7"),
    }
    values.update(changes)
    return entry.CommissionEvidence(**values)


def settlement(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "semantics": entry.SettlementSemantics.POST_TRADE_REGULAR_WAY,
        "cycle": entry.SettlementCycle.T_PLUS_1,
        "provenance": provenance("a"),
    }
    values.update(changes)
    return entry.SettlementEvidence(**values)


def executable_quote(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "bid": Decimal("99.1250"),
        "ask": Decimal("99.3750"),
        "currency": "EUR",
        "market_timestamp": "2026-10-03T13:59:59Z",
        "authority": entry.ExecutableQuoteAuthority.EXECUTABLE_BID_ASK,
        "execution_source_descriptor": "synthetic executable venue",
        "provenance": provenance("d"),
    }
    values.update(changes)
    return entry.ExecutableQuoteEvidence(**values)


def request(**changes):
    values = {
        "execution_context_id": CONTEXT_ID,
        "target_instrument_id": INSTRUMENT_ID,
        "eligibility": eligibility(),
        "funding": funding(),
        "commission": commission(),
        "settlement": settlement(),
        "executable_quote": executable_quote(),
    }
    values.update(changes)
    return entry.ExecutableEntryEvidenceRequest(**values)


def qualify(**changes):
    return entry.qualify_executable_entry_evidence(request(**changes))


class ExecutableEntryEvidenceTests(unittest.TestCase):
    def test_synthetic_source_neutral_same_currency_route_is_available(self):
        result = qualify()
        self.assertIs(result.status, entry.ExecutableEntryStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.facts.commission.amount, Decimal("1.2500"))
        self.assertEqual(result.facts.executable_quote.bid, Decimal("99.1250"))
        self.assertEqual(result.facts.executable_quote.ask, Decimal("99.3750"))
        self.assertIs(
            result.facts.currency_path.state,
            entry.CurrencyPathState.FX_NOT_REQUIRED_SAME_CURRENCY,
        )
        self.assertIs(
            result.authority_scope,
            entry.ExecutableEntryAuthorityScope.CURRENT_CAPTURE_BOUND_EVIDENCE_ONLY,
        )
        json.dumps(result.to_dict(), allow_nan=False)

    def test_exact_decimal_is_preserved_and_binary_float_is_rejected(self):
        exact = Decimal("99.123456789012345678901")
        result = qualify(executable_quote=executable_quote(bid=exact))
        self.assertEqual(result.facts.executable_quote.bid, exact)
        self.assertIs(type(result.facts.executable_quote.bid), Decimal)
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            commission(amount=0.0)
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            executable_quote(bid=99.125)

    def test_positively_evidenced_zero_commission_is_valid(self):
        result = qualify(commission=commission(amount=Decimal("0.000")))
        self.assertIs(result.status, entry.ExecutableEntryStatus.AVAILABLE)
        self.assertEqual(result.facts.commission.amount, Decimal("0.000"))
        self.assertNotIn(entry.ExecutableEntryReason.COMMISSION_UNAVAILABLE, result.reasons)

    def test_missing_commission_is_unavailable_and_never_zero(self):
        result = qualify(commission=None)
        self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertIn(entry.ExecutableEntryReason.COMMISSION_UNAVAILABLE, result.reasons)
        self.assertIn(entry.ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING, result.reasons)
        self.assertIsNone(result.facts.commission)

    def test_unsupported_or_currency_conflicted_commission_fails_closed(self):
        unsupported = qualify(
            commission=commission(semantics=entry.CommissionSemantics.OTHER)
        )
        conflicted = qualify(commission=commission(currency="GBP"))
        self.assertIs(unsupported.status, entry.ExecutableEntryStatus.UNSUPPORTED)
        self.assertEqual(
            unsupported.reasons,
            (entry.ExecutableEntryReason.COMMISSION_SEMANTICS_UNSUPPORTED,),
        )
        self.assertIs(conflicted.status, entry.ExecutableEntryStatus.SOURCE_CONFLICT)
        self.assertEqual(
            conflicted.reasons,
            (entry.ExecutableEntryReason.COMMISSION_CURRENCY_CONFLICT,),
        )
        self.assertIsNone(conflicted.facts.commission)

    def test_missing_and_unsupported_settlement_fail_closed(self):
        missing = qualify(settlement=settlement(semantics=None))
        unsupported_cycle = qualify(
            settlement=settlement(cycle=entry.SettlementCycle.OTHER)
        )
        unsupported_semantics = qualify(
            settlement=settlement(semantics=entry.SettlementSemantics.OTHER)
        )
        self.assertIs(missing.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertIn(
            entry.ExecutableEntryReason.SETTLEMENT_SEMANTICS_UNAVAILABLE,
            missing.reasons,
        )
        self.assertIs(unsupported_cycle.status, entry.ExecutableEntryStatus.UNSUPPORTED)
        self.assertEqual(
            unsupported_cycle.reasons,
            (entry.ExecutableEntryReason.SETTLEMENT_CYCLE_UNSUPPORTED,),
        )
        self.assertIs(unsupported_semantics.status, entry.ExecutableEntryStatus.UNSUPPORTED)

    def test_eligibility_unavailable_and_explicit_negative_states_are_distinct(self):
        not_established = qualify(
            eligibility=eligibility(state=entry.EligibilityState.NOT_ESTABLISHED)
        )
        not_eligible = qualify(
            eligibility=eligibility(state=entry.EligibilityState.NOT_ELIGIBLE)
        )
        unsupported = qualify(
            eligibility=eligibility(
                state=entry.EligibilityState.UNSUPPORTED_INSTRUMENT
            )
        )
        self.assertIs(not_established.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertIn(
            entry.ExecutableEntryReason.ACCOUNT_INSTRUMENT_ELIGIBILITY_NOT_ESTABLISHED,
            not_established.reasons,
        )
        self.assertIs(not_eligible.status, entry.ExecutableEntryStatus.UNSUPPORTED)
        self.assertEqual(
            not_eligible.reasons,
            (entry.ExecutableEntryReason.INSTRUMENT_NOT_ELIGIBLE,),
        )
        self.assertIs(unsupported.status, entry.ExecutableEntryStatus.UNSUPPORTED)
        self.assertEqual(
            unsupported.reasons,
            (entry.ExecutableEntryReason.INSTRUMENT_ROUTE_UNSUPPORTED,),
        )

    def test_unsettled_or_unestablished_funding_fails_closed(self):
        for state in (
            entry.FundingAvailabilityState.UNSETTLED,
            entry.FundingAvailabilityState.AVAILABILITY_NOT_ESTABLISHED,
        ):
            with self.subTest(state=state):
                result = qualify(funding=funding(state=state))
                self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
                self.assertIn(
                    entry.ExecutableEntryReason.SETTLED_AVAILABLE_FUNDING_NOT_ESTABLISHED,
                    result.reasons,
                )
                self.assertIsNone(result.facts.funding_availability)

    def test_missing_funding_or_transaction_currency_fails_closed(self):
        missing_funding = qualify(funding=funding(funding_currency=None))
        missing_transaction = qualify(
            eligibility=eligibility(transaction_currency=None)
        )
        self.assertIn(
            entry.ExecutableEntryReason.EXACT_FUNDING_CURRENCY_UNAVAILABLE,
            missing_funding.reasons,
        )
        self.assertIn(
            entry.ExecutableEntryReason.EXACT_TRANSACTION_CURRENCY_UNAVAILABLE,
            missing_transaction.reasons,
        )
        self.assertIsNone(missing_funding.facts.currency_path)
        self.assertIsNone(missing_transaction.facts.currency_path)

    def test_same_currency_explicitly_establishes_fx_not_required(self):
        fact = qualify().facts.currency_path
        self.assertEqual(fact.funding_currency, "EUR")
        self.assertEqual(fact.transaction_currency, "EUR")
        self.assertIs(
            fact.state, entry.CurrencyPathState.FX_NOT_REQUIRED_SAME_CURRENCY
        )

    def test_cross_currency_without_exact_fx_cost_is_unavailable(self):
        result = qualify(funding=funding(funding_currency="GBP"))
        self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons,
            (entry.ExecutableEntryReason.FX_EXECUTION_COST_EVIDENCE_UNAVAILABLE,),
        )
        self.assertIs(
            result.facts.currency_path.state,
            entry.CurrencyPathState.FX_REQUIRED_EXECUTION_COST_UNAVAILABLE,
        )

    def test_missing_quote_is_unavailable_while_independent_facts_remain(self):
        result = qualify(executable_quote=None)
        self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons,
            (
                entry.ExecutableEntryReason.EXECUTABLE_QUOTE_UNAVAILABLE,
                entry.ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,
            ),
        )
        self.assertIsNotNone(result.facts.eligibility)
        self.assertIsNotNone(result.facts.funding_availability)
        self.assertIsNotNone(result.facts.commission)
        self.assertIsNotNone(result.facts.settlement)
        self.assertIsNotNone(result.facts.currency_path)
        self.assertIsNone(result.facts.executable_quote)

    def test_informational_or_indicative_quote_cannot_be_executable(self):
        for authority in (
            entry.ExecutableQuoteAuthority.INFORMATIONAL_OR_DISPLAY_ONLY,
            entry.ExecutableQuoteAuthority.INDICATIVE_ONLY,
            entry.ExecutableQuoteAuthority.OTHER,
            None,
        ):
            with self.subTest(authority=authority):
                result = qualify(
                    executable_quote=executable_quote(authority=authority)
                )
                self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
                self.assertIn(
                    entry.ExecutableEntryReason.EXECUTABLE_QUOTE_UNAVAILABLE,
                    result.reasons,
                )
                self.assertIn(
                    entry.ExecutableEntryReason.EXECUTABLE_QUOTE_AUTHORITY_INSUFFICIENT,
                    result.reasons,
                )
                self.assertIsNone(result.facts.executable_quote)

    def test_yahoo_current_quote_type_cannot_be_silently_upgraded(self):
        observed_only_quote = object.__new__(QualifiedCurrentQuote)
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            request(executable_quote=observed_only_quote)
        source = Path(entry.__file__).read_text().lower()
        self.assertNotIn("yahoo_current_quote", source)
        self.assertNotIn("qualifiedcurrentquote", source)

    def test_quote_bid_ask_positivity_and_ordering_are_enforced(self):
        for bid, ask in (
            (Decimal("0"), Decimal("1")),
            (Decimal("1"), Decimal("0")),
            (Decimal("2"), Decimal("1")),
            (Decimal("-1"), Decimal("1")),
        ):
            with self.subTest(bid=bid, ask=ask):
                result = qualify(executable_quote=executable_quote(bid=bid, ask=ask))
                self.assertIs(
                    result.status, entry.ExecutableEntryStatus.SOURCE_CONFLICT
                )
                self.assertEqual(
                    result.reasons,
                    (entry.ExecutableEntryReason.QUOTE_BID_ASK_CONFLICT,),
                )

    def test_quote_currency_mismatch_is_source_conflict(self):
        result = qualify(executable_quote=executable_quote(currency="GBP"))
        self.assertIs(result.status, entry.ExecutableEntryStatus.SOURCE_CONFLICT)
        self.assertEqual(
            result.reasons,
            (entry.ExecutableEntryReason.QUOTE_CURRENCY_CONFLICT,),
        )
        self.assertIsNone(result.facts.executable_quote)

    def test_quote_and_provenance_chronology_conflicts_are_distinct(self):
        quote_conflict = qualify(
            executable_quote=executable_quote(
                market_timestamp="2026-10-03T14:00:01Z"
            )
        )
        provenance_conflict = qualify(
            commission=commission(
                provenance=provenance(
                    "7", publication_timestamp="2026-10-03T14:00:01Z"
                )
            )
        )
        self.assertEqual(
            quote_conflict.reasons,
            (entry.ExecutableEntryReason.QUOTE_CHRONOLOGY_CONFLICT,),
        )
        self.assertEqual(
            provenance_conflict.reasons,
            (entry.ExecutableEntryReason.PROVENANCE_CHRONOLOGY_CONFLICT,),
        )

    def test_scope_identity_conflict_fails_closed(self):
        other_context = "execctx:" + "f" * 64
        result = qualify(
            commission=commission(execution_context_id=other_context)
        )
        self.assertIs(result.status, entry.ExecutableEntryStatus.SOURCE_CONFLICT)
        self.assertEqual(
            result.reasons,
            (entry.ExecutableEntryReason.SCOPE_IDENTITY_CONFLICT,),
        )

    def test_stale_or_unestablished_freshness_fails_closed(self):
        for freshness in (
            entry.CurrentEvidenceFreshness.STALE,
            entry.CurrentEvidenceFreshness.NOT_ESTABLISHED,
        ):
            with self.subTest(freshness=freshness):
                result = qualify(
                    settlement=settlement(
                        provenance=provenance("a", freshness=freshness)
                    )
                )
                self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
                self.assertEqual(
                    result.reasons,
                    (entry.ExecutableEntryReason.CURRENT_FRESHNESS_NOT_ESTABLISHED,),
                )
                self.assertIsNone(result.facts.settlement)

    def test_publication_unknown_and_capture_bound_availability_are_preserved(self):
        result = qualify()
        dimensions = (
            result.evidence.eligibility,
            result.evidence.funding,
            result.evidence.commission,
            result.evidence.settlement,
            result.evidence.executable_quote,
        )
        self.assertEqual(len({item.provenance.source_owner for item in dimensions}), 5)
        for item in dimensions:
            self.assertIs(
                item.provenance.publication_semantics, PublicationSemantics.UNKNOWN
            )
            self.assertIsNone(item.provenance.publication_timestamp)
            self.assertIs(
                item.provenance.availability_semantics,
                AvailabilitySemantics.CAPTURE_BOUND,
            )
            self.assertRegex(item.claim_id, r"^[0-9a-f]{64}$")

    def test_closed_precedence_is_conflict_then_unsupported_then_unavailable(self):
        conflict = qualify(
            executable_quote=executable_quote(currency="GBP"),
            settlement=settlement(cycle=entry.SettlementCycle.OTHER),
            commission=None,
        )
        unsupported = qualify(
            settlement=settlement(cycle=entry.SettlementCycle.OTHER),
            commission=None,
        )
        unavailable = qualify(commission=None)
        self.assertIs(conflict.status, entry.ExecutableEntryStatus.SOURCE_CONFLICT)
        self.assertEqual(
            conflict.reasons,
            (entry.ExecutableEntryReason.QUOTE_CURRENCY_CONFLICT,),
        )
        self.assertIs(unsupported.status, entry.ExecutableEntryStatus.UNSUPPORTED)
        self.assertEqual(
            unsupported.reasons,
            (entry.ExecutableEntryReason.SETTLEMENT_CYCLE_UNSUPPORTED,),
        )
        self.assertIs(unavailable.status, entry.ExecutableEntryStatus.UNAVAILABLE)

    def test_equivalent_recapture_preserves_semantics_and_changes_evidence(self):
        first = qualify()
        recaptured = qualify(
            commission=commission(
                provenance=provenance(
                    "7",
                    receipt_id="e" * 64,
                    content_sha256="f" * 64,
                    capture_sha256="0" * 64,
                    retrieved_at="2026-10-03T10:05:00-04:00",
                )
            )
        )
        self.assertEqual(first.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(first.evidence_id, recaptured.evidence_id)

    def test_material_execution_fact_changes_change_semantic_identity(self):
        baseline = qualify().semantic_id
        variants = (
            {"commission": commission(amount=Decimal("1.26"))},
            {"funding": funding(funding_currency="GBP")},
            {"settlement": settlement(cycle=entry.SettlementCycle.OTHER)},
            {"eligibility": eligibility(state=entry.EligibilityState.NOT_ELIGIBLE)},
            {"executable_quote": executable_quote(ask=Decimal("99.50"))},
        )
        for changes in variants:
            with self.subTest(changes=changes):
                self.assertNotEqual(baseline, qualify(**changes).semantic_id)

    def test_decimal_scale_and_provenance_only_changes_do_not_change_semantics(self):
        first = qualify()
        scaled = qualify(
            commission=commission(amount=Decimal("1.250000")),
            executable_quote=executable_quote(
                bid=Decimal("99.125000"), ask=Decimal("99.375000")
            ),
        )
        provenance_only = qualify(
            settlement=settlement(
                provenance=provenance(
                    "a",
                    source_owner="Different Synthetic Owner",
                    source_descriptor="different authenticated capture",
                    source_locator="fixture:different",
                )
            )
        )
        self.assertEqual(first.semantic_id, scaled.semantic_id)
        self.assertEqual(first.semantic_id, provenance_only.semantic_id)
        self.assertNotEqual(first.evidence_id, provenance_only.evidence_id)

    def test_positive_synthetic_identity_fixture_is_pinned(self):
        result = qualify()
        self.assertEqual(
            result.semantic_id,
            "e07995eef7c7a2478390601a9e2e4d73cc4f8d5ca91d0829333b2a559dca70b7",
        )
        self.assertEqual(
            result.evidence_id,
            "d51c432c2d515fcdad772aed77b743d499a482b7f137be6dc4cd1d0fe35c34dc",
        )

    def test_missing_request_is_availability_not_programming_failure(self):
        result = entry.qualify_executable_entry_evidence(None)
        self.assertIs(result.status, entry.ExecutableEntryStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons,
            (entry.ExecutableEntryReason.REQUIRED_EVIDENCE_MISSING,),
        )
        self.assertEqual(result.facts, entry.ExecutableEntryFacts(None, None, None, None, None, None))
        self.assertIsNone(result.evidence)
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            entry.qualify_executable_entry_evidence("not a request")

    def test_public_dataclasses_are_frozen(self):
        result = qualify()
        values_and_attributes = (
            (provenance(), "source_owner"),
            (eligibility(), "state"),
            (funding(), "state"),
            (commission(), "amount"),
            (settlement(), "cycle"),
            (executable_quote(), "bid"),
            (request(), "eligibility"),
            (result.facts.eligibility, "state"),
            (result.facts.funding_availability, "state"),
            (result.facts.commission, "amount"),
            (result.facts.settlement, "cycle"),
            (result.facts.currency_path, "state"),
            (result.facts.executable_quote, "bid"),
            (result.facts, "commission"),
            (result.evidence.commission, "claim_id"),
            (result.evidence, "commission"),
            (result, "status"),
        )
        for value, attribute in values_and_attributes:
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(value, attribute, None)

    def test_module_is_pure_source_neutral_and_has_no_private_identifier_fields(self):
        source = Path(entry.__file__).read_text()
        source_lower = source.lower()
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        self.assertTrue({"requests", "urllib", "httpx", "socket"}.isdisjoint(imports))
        self.assertNotIn("urlopen", source_lower)
        self.assertNotIn("wealthsimple", source_lower)
        self.assertNotIn("yahoo", source_lower)
        self.assertNotIn("cad", source_lower)
        public_dataclasses = (
            entry.EvidenceProvenance,
            entry.EligibilityEvidence,
            entry.FundingEvidence,
            entry.CommissionEvidence,
            entry.SettlementEvidence,
            entry.ExecutableQuoteEvidence,
            entry.ExecutableEntryEvidenceRequest,
            entry.ExecutableEntryFacts,
            entry.ExecutableEntryEvidenceQualification,
        )
        field_names = {
            field.name for class_ in public_dataclasses for field in fields(class_)
        }
        self.assertTrue(
            {
                "account_number",
                "account_id",
                "owner_name",
                "credential",
                "credentials",
                "token",
                "password",
                "quantity",
                "notional",
                "order_size",
            }.isdisjoint(field_names)
        )

    def test_no_b2_expected_return_or_aggregate_friction_surface_exists(self):
        dataclass_names = {
            field.name
            for class_ in (
                entry.ExecutableEntryFacts,
                entry.ExecutableEntryEvidenceQualification,
            )
            for field in fields(class_)
        }
        self.assertTrue(
            {
                "execution_adjusted_entry_price",
                "commission_adjusted_irr",
                "spread_adjusted_irr",
                "fx_adjusted_irr",
                "executable_net_expected_return",
                "aggregate_friction",
                "midpoint",
                "spread_cost",
                "market_impact",
                "slippage",
            }.isdisjoint(dataclass_names)
        )
        functions = {
            name for name, value in vars(entry).items() if inspect.isfunction(value)
        }
        self.assertTrue(
            {
                "calculate_expected_return",
                "calculate_entry_price",
                "calculate_aggregate_friction",
                "construct_order",
                "submit_order",
            }.isdisjoint(functions)
        )

    def test_every_required_authority_limitation_is_exposed(self):
        self.assertEqual(
            {item.value for item in qualify().limitations},
            {item.value for item in entry.ExecutableEntryLimitation},
        )

    def test_programming_contract_requires_strict_scope_and_exact_types(self):
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            request(execution_context_id="private-account-123")
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            request(target_instrument_id="VFV")
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            provenance(retrieved_at="2026-10-03T10:00:00")
        with self.assertRaises(entry.ExecutableEntryEvidenceError):
            executable_quote(currency="eur")


if __name__ == "__main__":
    unittest.main()
