"""Adversarial tests for source-neutral CURRENT cash-like carry."""
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal
import ast
import inspect
import json
from pathlib import Path
import unittest

from economic_facts import cash_like_current_carry as carry
from economic_facts.source_authority import (
    AvailabilitySemantics,
    PublicationSemantics,
    UseStatus,
)


def standard_claim(**changes):
    values = {
        "balance_form": carry.CashLikeBalanceForm.SETTLED_CASH_BALANCE,
        "settlement_state": carry.CashLikeSettlementState.SETTLED_AND_AVAILABLE,
        "native_accrual_currency": "EUR",
        "rate": Decimal("3.1250"),
        "rate_type": carry.CashLikeRateType.NOMINAL_ANNUAL_RATE,
        "rate_unit": carry.CashLikeRateUnit.PERCENTAGE_POINTS_PER_YEAR,
        "accrual_semantics": (
            carry.CashLikeAccrualSemantics.
            DAILY_ON_END_OF_DAY_SETTLED_BALANCE),
        "payment_semantics": carry.CashLikePaymentSemantics.PAID_MONTHLY,
        "compounding_semantics": (
            carry.CashLikeCompoundingSemantics.UNSPECIFIED_BY_SOURCE),
        "day_count_semantics": (
            carry.CashLikeDayCountSemantics.UNSPECIFIED_BY_SOURCE),
        "effective_date": "2026-10-01",
        "effective_semantics": (
            carry.CashLikeEffectiveSemantics.RATE_EFFECTIVE_FROM_DATE),
        "term_semantics": carry.CashLikeTermSemantics.NO_FIXED_TERM,
        "maturity_date": None,
        "recurring_expense_treatment": (
            carry.CashLikeRecurringExpenseTreatment.
            NO_RECURRING_INSTRUMENT_EXPENSE),
    }
    values.update(changes)
    return carry.CashLikeCurrentCarryClaim(**values)


def standard_receipt(*, claim=None, **changes):
    values = {
        "schema_version": carry.CASH_LIKE_CURRENT_CARRY_RECEIPT_VERSION,
        "qualification_input_contract_version": (
            carry.CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION),
        "source_owner": "Synthetic Source Owner",
        "source_descriptor": "authenticated account-state capture",
        "source_locator": "fixture:current-carry:balance-rate",
        "receipt_id": "1" * 64,
        "content_or_account_state_sha256": "2" * 64,
        "capture_sha256": "3" * 64,
        "retrieved_at": "2026-10-01T09:30:00-04:00",
        "publication_timestamp": None,
        "publication_semantics": PublicationSemantics.UNKNOWN,
        "availability_semantics": AvailabilitySemantics.CAPTURE_BOUND,
        "license_status": UseStatus.UNKNOWN,
        "use_status": UseStatus.REVIEW_REQUIRED,
        "freshness": carry.CashLikeCurrentFreshness.CURRENT_SAME_RUN_CAPTURE,
        "claim": claim if claim is not None else standard_claim(),
    }
    values.update(changes)
    return carry.CashLikeCurrentCarryReceipt(**values)


def qualify(*, claim=None, **receipt_changes):
    return carry.qualify_cash_like_current_carry(
        standard_receipt(claim=claim, **receipt_changes))


class CashLikeCurrentCarryTests(unittest.TestCase):
    def test_valid_source_neutral_receipt_produces_exact_typed_fact(self):
        result = qualify()
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.fact, carry.CashLikeCurrentCarryFact(
            carry.CashLikeBalanceForm.SETTLED_CASH_BALANCE,
            "EUR",
            Decimal("3.1250"),
            carry.CashLikeRateType.NOMINAL_ANNUAL_RATE,
            carry.CashLikeRateUnit.PERCENTAGE_POINTS_PER_YEAR,
            (carry.CashLikeAccrualSemantics.
             DAILY_ON_END_OF_DAY_SETTLED_BALANCE),
            carry.CashLikePaymentSemantics.PAID_MONTHLY,
            carry.CashLikeCompoundingSemantics.UNSPECIFIED_BY_SOURCE,
            carry.CashLikeDayCountSemantics.UNSPECIFIED_BY_SOURCE,
            "2026-10-01",
            carry.CashLikeEffectiveSemantics.RATE_EFFECTIVE_FROM_DATE,
            carry.CashLikeTermSemantics.NO_FIXED_TERM,
            None,
            (carry.CashLikeRecurringExpenseTreatment.
             NO_RECURRING_INSTRUMENT_EXPENSE),
        ))
        self.assertIs(
            result.authority_scope,
            carry.CashLikeCurrentCarryAuthorityScope.CURRENT_CAPTURE_BOUND_ONLY,
        )
        json.dumps(result.to_dict(), allow_nan=False)

    def test_exact_decimal_is_preserved_and_binary_float_is_rejected(self):
        result = qualify(claim=standard_claim(rate=Decimal("3.12500001")))
        self.assertEqual(result.fact.rate, Decimal("3.12500001"))
        self.assertIs(type(result.fact.rate), Decimal)
        with self.assertRaises(carry.CashLikeCurrentCarryError):
            standard_claim(rate=3.125)

    def test_positively_evidenced_zero_is_available_and_not_missing(self):
        result = qualify(claim=standard_claim(rate=Decimal("0")))
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.AVAILABLE)
        self.assertEqual(result.fact.rate, Decimal("0"))
        self.assertNotIn(carry.CashLikeCurrentCarryReason.RATE_UNAVAILABLE,
                         result.reasons)

    def test_missing_rate_is_unavailable_and_never_zero(self):
        result = qualify(claim=standard_claim(rate=None))
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons, (carry.CashLikeCurrentCarryReason.RATE_UNAVAILABLE,))
        self.assertIsNone(result.fact)

    def test_missing_required_semantics_are_unavailable_not_guessed(self):
        cases = (
            ("balance_form", carry.CashLikeCurrentCarryReason.
             ACCOUNT_BALANCE_FORM_UNAVAILABLE),
            ("rate_type", carry.CashLikeCurrentCarryReason.
             RATE_SEMANTICS_UNAVAILABLE),
            ("accrual_semantics", carry.CashLikeCurrentCarryReason.
             ACCRUAL_SEMANTICS_UNAVAILABLE),
            ("payment_semantics", carry.CashLikeCurrentCarryReason.
             PAYMENT_SEMANTICS_UNAVAILABLE),
            ("compounding_semantics", carry.CashLikeCurrentCarryReason.
             COMPOUNDING_OR_DAY_COUNT_UNAVAILABLE),
            ("day_count_semantics", carry.CashLikeCurrentCarryReason.
             COMPOUNDING_OR_DAY_COUNT_UNAVAILABLE),
            ("effective_semantics", carry.CashLikeCurrentCarryReason.
             EFFECTIVE_AS_OF_SEMANTICS_UNAVAILABLE),
            ("term_semantics", carry.CashLikeCurrentCarryReason.
             TERM_PROFILE_UNAVAILABLE),
            ("recurring_expense_treatment", carry.CashLikeCurrentCarryReason.
             RECURRING_EXPENSE_TREATMENT_UNAVAILABLE),
        )
        for field_name, reason in cases:
            with self.subTest(field_name=field_name):
                result = qualify(claim=standard_claim(**{field_name: None}))
                self.assertIs(
                    result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
                self.assertIn(reason, result.reasons)

    def test_missing_exact_currency_fails_closed(self):
        result = qualify(claim=standard_claim(native_accrual_currency=None))
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
        self.assertIn(
            carry.CashLikeCurrentCarryReason.EXACT_CURRENCY_UNAVAILABLE,
            result.reasons,
        )

    def test_unsupported_balance_or_instrument_form_fails_closed(self):
        result = qualify(claim=standard_claim(
            balance_form=carry.CashLikeBalanceForm.CASH_LIKE_INSTRUMENT))
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.UNSUPPORTED)
        self.assertIn(
            carry.CashLikeCurrentCarryReason.ACCOUNT_BALANCE_FORM_UNSUPPORTED,
            result.reasons,
        )

    def test_unsettled_or_unestablished_applicability_fails_closed(self):
        for state in (
                carry.CashLikeSettlementState.UNSETTLED,
                carry.CashLikeSettlementState.AVAILABILITY_NOT_ESTABLISHED):
            with self.subTest(state=state):
                result = qualify(claim=standard_claim(settlement_state=state))
                self.assertIs(
                    result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
                self.assertIn(
                    carry.CashLikeCurrentCarryReason.
                    SETTLED_AVAILABLE_STATE_NOT_ESTABLISHED,
                    result.reasons,
                )

    def test_stale_or_not_established_current_capture_fails_closed(self):
        for freshness in (
                carry.CashLikeCurrentFreshness.STALE,
                carry.CashLikeCurrentFreshness.NOT_ESTABLISHED):
            with self.subTest(freshness=freshness):
                result = qualify(freshness=freshness)
                self.assertIs(
                    result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
                self.assertIn(
                    carry.CashLikeCurrentCarryReason.
                    CURRENT_FRESHNESS_NOT_ESTABLISHED,
                    result.reasons,
                )

    def test_retrieval_does_not_become_effective_or_publication_time(self):
        result = qualify(claim=standard_claim(effective_date="2026-09-15"))
        self.assertEqual(result.fact.effective_date, "2026-09-15")
        self.assertEqual(result.evidence.retrieved_at,
                         "2026-10-01T09:30:00-04:00")
        self.assertNotEqual(result.fact.effective_date,
                            result.evidence.retrieved_at)
        self.assertIsNone(result.evidence.publication_timestamp)

    def test_unknown_publication_and_capture_bound_availability_are_preserved(self):
        result = qualify()
        self.assertIs(
            result.evidence.publication_semantics,
            PublicationSemantics.UNKNOWN,
        )
        self.assertIsNone(result.evidence.publication_timestamp)
        self.assertIs(
            result.evidence.availability_semantics,
            AvailabilitySemantics.CAPTURE_BOUND,
        )
        self.assertEqual(result.evidence.availability_timestamp,
                         result.evidence.retrieved_at)
        self.assertEqual(
            result.evidence.qualification_input_contract_version,
            carry.CASH_LIKE_CURRENT_CARRY_QUALIFICATION_VERSION,
        )
        self.assertRegex(result.evidence.receipt_claim_id, r"^[0-9a-f]{64}$")

    def test_unspecified_day_count_and_compounding_are_explicit_not_guessed(self):
        result = qualify()
        self.assertIs(
            result.fact.compounding_semantics,
            carry.CashLikeCompoundingSemantics.UNSPECIFIED_BY_SOURCE,
        )
        self.assertIs(
            result.fact.day_count_semantics,
            carry.CashLikeDayCountSemantics.UNSPECIFIED_BY_SOURCE,
        )

    def test_invalid_chronology_is_source_conflict(self):
        result = qualify(claim=standard_claim(effective_date="2026-10-02"))
        self.assertIs(
            result.status, carry.CashLikeCurrentCarryStatus.SOURCE_CONFLICT)
        self.assertEqual(
            result.reasons,
            (carry.CashLikeCurrentCarryReason.CHRONOLOGY_CONFLICT,),
        )
        publication = qualify(
            publication_timestamp="2026-10-01T14:00:00-04:00")
        self.assertIs(
            publication.status,
            carry.CashLikeCurrentCarryStatus.SOURCE_CONFLICT,
        )

    def test_equivalent_recapture_preserves_semantics_and_changes_evidence(self):
        first = qualify()
        second = qualify(
            receipt_id="4" * 64,
            content_or_account_state_sha256="5" * 64,
            capture_sha256="6" * 64,
            retrieved_at="2026-10-01T10:00:00-04:00",
        )
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_changed_rate_currency_or_rate_semantics_changes_semantic_identity(self):
        baseline = qualify().semantic_id
        variants = (
            standard_claim(rate=Decimal("3.126")),
            standard_claim(native_accrual_currency="GBP"),
            standard_claim(
                effective_semantics=(
                    carry.CashLikeEffectiveSemantics.CURRENT_AS_OF_DATE)),
        )
        for claim in variants:
            with self.subTest(claim=claim):
                self.assertNotEqual(baseline, qualify(claim=claim).semantic_id)

    def test_decimal_scale_and_provenance_only_changes_do_not_change_semantics(self):
        first = qualify(claim=standard_claim(rate=Decimal("3.1250")))
        scaled = qualify(claim=standard_claim(rate=Decimal("3.125000")))
        provenance = qualify(
            source_owner="Another Synthetic Owner",
            source_descriptor="another authenticated capture",
            source_locator="fixture:another-location",
            license_status=UseStatus.REVIEW_REQUIRED,
        )
        self.assertEqual(first.semantic_id, scaled.semantic_id)
        self.assertEqual(first.semantic_id, provenance.semantic_id)
        self.assertNotEqual(first.evidence_id, provenance.evidence_id)

    def test_missing_receipt_is_availability_not_programming_failure(self):
        result = carry.qualify_cash_like_current_carry(None)
        self.assertIs(result.status, carry.CashLikeCurrentCarryStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons,
            (carry.CashLikeCurrentCarryReason.REQUIRED_RECEIPT_MISSING,),
        )
        self.assertIsNone(result.fact)
        self.assertIsNone(result.evidence)

    def test_malformed_programming_contract_is_an_exception(self):
        with self.assertRaises(carry.CashLikeCurrentCarryError):
            carry.qualify_cash_like_current_carry("not a receipt")
        with self.assertRaises(carry.CashLikeCurrentCarryError):
            standard_receipt(schema_version="wrong")
        with self.assertRaises(carry.CashLikeCurrentCarryError):
            standard_receipt(retrieved_at="2026-10-01T09:30:00")

    def test_module_has_no_network_or_import_time_external_access(self):
        source = Path(carry.__file__).read_text()
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
        self.assertTrue(
            {"requests", "urllib", "httpx", "socket"}.isdisjoint(imports))
        self.assertNotIn("urlopen", source)
        self.assertNotIn("requests.get", source)

    def test_core_semantics_have_no_provider_or_positive_owner_fact(self):
        source = Path(carry.__file__).read_text().lower()
        self.assertNotIn("wealthsimple", source)
        self.assertNotIn("2.5%", source)
        self.assertNotIn("decimal(\"2.5\")", source)
        self.assertNotIn("cad", source)

    def test_no_expected_return_spread_or_seven_year_cash_er_surface(self):
        names = {field.name for field in fields(
            carry.CashLikeCurrentCarryQualification)}
        names.update(field.name for field in fields(
            carry.CashLikeCurrentCarryFact))
        self.assertTrue({
            "expected_return", "seven_year_cash_return", "company_spread",
            "vfv_spread", "rollover_rate", "reinvestment_rate",
        }.isdisjoint(names))
        functions = {
            name for name, value in vars(carry).items()
            if inspect.isfunction(value)
        }
        self.assertTrue({
            "calculate_expected_return", "compare_company_to_cash",
            "compare_vfv_to_cash",
        }.isdisjoint(functions))

    def test_receipt_claim_fact_evidence_and_result_are_frozen(self):
        result = qualify()
        for value, attribute in (
                (standard_claim(), "rate"),
                (standard_receipt(), "source_owner"),
                (result.fact, "rate"),
                (result.evidence, "source_owner"),
                (result, "status")):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(FrozenInstanceError):
                    setattr(value, attribute, None)

    def test_limitations_expose_every_authority_boundary(self):
        values = {item.value for item in qualify().limitations}
        self.assertEqual(values, {
            "CURRENT_CAPTURE_BOUND_ONLY",
            "NO_PIT_AUTHORITY",
            "NO_HISTORICAL_AS_OF_AUTHORITY",
            "NO_FIRST_PUBLICATION_AUTHORITY",
            "NO_SEVEN_YEAR_CASH_EXPECTED_RETURN",
            "NO_COMPANY_OR_VFV_VS_CASH_COMPARISON",
            "NO_HOLDER_TAX_MODELING",
            "NO_RESERVE_ACTIVATION_OR_RELEASE_POLICY",
            "NO_RECOMMENDATION_OR_ALLOCATION_AUTHORITY",
            "NO_EXECUTION_OR_PRODUCTION_AUTHORITY",
            "NO_GENERIC_CASH_ETF_OR_TBILL_AUTHORITY",
            ("PUBLIC_OBSERVABILITY_DOES_NOT_ESTABLISH_AUTOMATED_OR_"
             "COMMERCIAL_INGESTION"),
        })


if __name__ == "__main__":
    unittest.main()
