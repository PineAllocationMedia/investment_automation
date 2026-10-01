"""Bounded, dated VFV FX/hedge evidence qualification tests."""
from dataclasses import FrozenInstanceError, fields, replace
from decimal import Decimal
import json
from pathlib import Path
import unittest

from economic_facts import source_authority
from economic_facts import vfv_fx_hedge_evidence as evidence


def standard_record(**changes):
    values = {
        "source_role": (
            evidence.VFVFXHedgeSourceRole.
            NET_CURRENCY_EXPOSURE_AFTER_CURRENCY_CONTRACTS),
        "source_owner": "Vanguard Investments Canada Inc.",
        "source_document_id": "VFV_REVIEWED_CURRENCY_EXPOSURE_2026_06_30",
        "source_reference": "fixture:reviewed-vfv-currency-exposure",
        "content_sha256": "1" * 64,
        "source_locator": (
            "currency-exposure-table:USD:after-currency-contracts"),
        "capture_id": "2" * 64,
        "captured_at": "2026-09-30T18:05:00-04:00",
        "reviewed_at": "2026-10-01T09:00:00-04:00",
        "publication_semantics": source_authority.PublicationSemantics.UNKNOWN,
        "availability_semantics": (
            source_authority.AvailabilitySemantics.CAPTURE_BOUND),
        "instrument_ticker": "VFV",
        "instrument_isin": "CA92205Y1051",
        "listed_currency": "CAD",
        "base_currency": "CAD",
        "economic_exposure_currency": "USD",
        "material_hedge_state": (
            evidence.VFVMaterialHedgeState.
            MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE),
        "measurement_date": "2026-06-30",
        "net_usd_exposure_percent_of_nav": Decimal("100.0"),
        "exposure_unit": (
            evidence.VFVFXExposureUnit.
            PERCENT_OF_NAV_AFTER_CURRENCY_CONTRACTS),
    }
    values.update(changes)
    return evidence.VFVFXHedgeEvidenceRecord(**values)


def standard_qualification(**changes):
    return evidence.qualify_vfv_fx_hedge_evidence(
        (standard_record(**changes),))


class VFVFXHedgeEvidenceTests(unittest.TestCase):
    def test_exact_positive_supported_vfv_fixture(self):
        result = standard_qualification()
        self.assertIs(
            result.status, evidence.VFVFXHedgeEvidenceStatus.AVAILABLE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.instrument_ticker, "VFV")
        self.assertEqual(result.instrument_isin, "CA92205Y1051")
        self.assertEqual(
            result.net_usd_exposure_percent_of_nav, Decimal("100.0"))
        self.assertIs(
            result.exposure_unit,
            evidence.VFVFXExposureUnit.
            PERCENT_OF_NAV_AFTER_CURRENCY_CONTRACTS,
        )
        self.assertIs(
            result.confidence, evidence.VFVFXHedgeConfidenceLevel.LOW)
        json.dumps(result.to_dict(), allow_nan=False)
        with self.assertRaises(FrozenInstanceError):
            result.status = evidence.VFVFXHedgeEvidenceStatus.UNAVAILABLE

    def test_usd_economic_exposure_is_distinct_from_cad_listing_and_base(self):
        result = standard_qualification()
        self.assertEqual(result.listed_currency, "CAD")
        self.assertEqual(result.base_currency, "CAD")
        self.assertEqual(result.economic_exposure_currency, "USD")

    def test_measurement_date_and_capture_review_provenance_are_retained(self):
        result = standard_qualification()
        self.assertEqual(result.measurement_date, "2026-06-30")
        self.assertEqual(result.capture_ids, ("2" * 64,))
        self.assertEqual(
            result.latest_captured_at, "2026-09-30T22:05:00+00:00")
        self.assertEqual(
            result.latest_reviewed_at, "2026-10-01T13:00:00+00:00")
        self.assertEqual(result.source_records, (standard_record(),))

    def test_materially_unhedged_classification_is_explicitly_date_bound(self):
        result = standard_qualification()
        self.assertIs(
            result.material_hedge_state,
            evidence.VFVMaterialHedgeState.
            MATERIALLY_UNHEDGED_USD_EXPOSURE_TO_CAD_AT_DISCLOSURE_DATE,
        )
        limitations = {item.value for item in result.limitations}
        self.assertIn("DATE_BOUND_DISCLOSURE_STATE_ONLY", limitations)
        self.assertIn(
            "NO_HEDGE_RATIO_AFTER_2026_06_30_AUTHORITY", limitations)

    def test_zero_contract_and_permanent_no_hedging_claims_are_not_implied(self):
        names = {field.name for field in fields(
            evidence.VFVFXHedgeEvidenceQualification)}
        self.assertFalse({
            "permanent_no_hedging_mandate", "zero_currency_contracts",
            "current_hedge_ratio", "historical_hedge_state",
        } & names)
        limitations = {item.value for item in
                       standard_qualification().limitations}
        self.assertIn(
            "NO_PERMANENT_NO_HEDGING_MANDATE_AUTHORITY", limitations)
        self.assertIn("NO_ZERO_CURRENCY_CONTRACTS_CLAIM", limitations)

    def test_semantic_and_evidence_identities_are_deterministic(self):
        first = standard_qualification()
        second = standard_qualification()
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertEqual(first.evidence_id, second.evidence_id)
        self.assertEqual(
            first.semantic_id,
            "1b16a3cab764f39fc3e74911dd813664616cedd984f55868729d45ae02724482",
        )
        self.assertEqual(
            first.evidence_id,
            "5d3badf3f403e96ca71904aa7ff23e4aa8a5790be742cabae7c8c951a65c280b",
        )
        self.assertRegex(first.semantic_id, r"^[0-9a-f]{64}$")
        self.assertRegex(first.evidence_id, r"^[0-9a-f]{64}$")

    def test_provenance_only_recapture_changes_evidence_not_semantics(self):
        first = standard_qualification()
        second = standard_qualification(
            content_sha256="3" * 64,
            capture_id="4" * 64,
            captured_at="2026-10-01T10:00:00-04:00",
            reviewed_at="2026-10-01T11:00:00-04:00",
        )
        self.assertEqual(first.semantic_id, second.semantic_id)
        self.assertNotEqual(first.evidence_id, second.evidence_id)

    def test_missing_evidence_fails_closed(self):
        result = evidence.qualify_vfv_fx_hedge_evidence(())
        self.assertIs(
            result.status, evidence.VFVFXHedgeEvidenceStatus.UNAVAILABLE)
        self.assertEqual(
            result.reasons,
            (evidence.VFVFXHedgeEvidenceReason.REQUIRED_EVIDENCE_MISSING,),
        )
        self.assertIsNone(result.net_usd_exposure_percent_of_nav)

    def test_unsupported_and_contradictory_evidence_fail_closed(self):
        unsupported = standard_qualification(
            material_hedge_state=(
                evidence.VFVMaterialHedgeState.
                MATERIALLY_HEDGED_TO_CAD_AT_DISCLOSURE_DATE))
        self.assertIs(
            unsupported.status,
            evidence.VFVFXHedgeEvidenceStatus.UNSUPPORTED,
        )
        conflict = evidence.qualify_vfv_fx_hedge_evidence((
            standard_record(),
            standard_record(
                content_sha256="3" * 64,
                capture_id="4" * 64,
                material_hedge_state=(
                    evidence.VFVMaterialHedgeState.
                    MATERIALLY_HEDGED_TO_CAD_AT_DISCLOSURE_DATE)),
        ))
        self.assertIs(
            conflict.status,
            evidence.VFVFXHedgeEvidenceStatus.SOURCE_CONFLICT,
        )
        self.assertIn(
            evidence.VFVFXHedgeEvidenceReason.SOURCE_ASSERTIONS_CONFLICT,
            conflict.reasons,
        )

    def test_no_historical_or_pit_authority(self):
        result = standard_qualification()
        limitations = {item.value for item in result.limitations}
        self.assertIn("NO_HISTORICAL_AS_OF_OR_PIT_AUTHORITY", limitations)
        self.assertNotIn("HISTORICAL_AS_OF", result.authority_scope.value)
        self.assertNotIn("PIT", result.authority_scope.value)
        source = Path(evidence.__file__).read_text()
        self.assertNotIn("datetime.now", source)
        self.assertNotIn("date.today", source)


if __name__ == "__main__":
    unittest.main()
