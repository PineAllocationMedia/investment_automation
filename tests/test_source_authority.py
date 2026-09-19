"""Closed route powers and independent use-review metadata; no source requests."""
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import unittest

from economic_facts import source_authority as s


class SourceAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.route = s.get_source_route(s.SEC_COMPANYFACTS_LIVE_CURRENT_V1)

    def test_exact_registered_route_and_pins(self):
        self.assertEqual(self.route.provider, "SEC")
        self.assertEqual(self.route.required_acquisition_contract, "2026-09-11-sec-live-companyfacts-v1")
        self.assertEqual(self.route.required_resolution_contract, "2026-09-11-sec-annual-diluted-eps-series-v1")
        self.assertEqual(self.route.required_extraction_contract, "2026-09-10-sec-diluted-eps-extraction-v1")
        self.assertTrue(self.route.immutable_capture_required)
        self.assertIs(self.route.pit_capability, s.PITCapability.UNSUPPORTED)
        self.assertIs(self.route.failure_policy, s.FailurePolicy.FAIL_CLOSED)

    def test_unknown_route_and_provider_name_fail_closed(self):
        for value in ("SEC", "REAL", "unknown", "SEC_COMPANYFACTS_LIVE_CURRENT_V2",
                      s.SEC_COMPANYFACTS_LIVE_CURRENT_V1 + " "):
            with self.subTest(value=value), self.assertRaises(s.SourceAuthorityError) as caught:
                s.get_source_route(value)
            self.assertIs(caught.exception.reason, s.SourceAuthorityReason.UNKNOWN_ROUTE)

    def test_caller_profile_mapping_and_enum_cannot_select_route(self):
        for value in (self.route, {"route_id": self.route.route_id}, True, s.ClaimRole.PRIMARY):
            with self.subTest(kind=type(value)), self.assertRaises(s.SourceAuthorityError):
                s.get_source_route(value)
        self.assertEqual(tuple(inspect.signature(s.get_source_route).parameters), ("route_id",))

    def test_only_three_claims_permitted(self):
        expected = {s.AuthorityProperty.SOURCE_ACQUISITION_PROVENANCE,
                    s.AuthorityProperty.CURRENT_OBSERVED_AVAILABILITY,
                    s.AuthorityProperty.CURRENT_SNAPSHOT_SCOPE}
        self.assertEqual({g.property for g in self.route.permitted_claims}, expected)
        for prop in s.AuthorityProperty:
            if prop in expected:
                grant = s.permitted_claim(self.route.route_id, prop)
                self.assertIs(grant.authority, s.ClaimAuthority.TRUSTED_LOCAL_PROCESS)
                self.assertIs(grant.role, s.ClaimRole.PRIMARY)
            else:
                with self.assertRaises(s.SourceAuthorityError) as caught:
                    s.permitted_claim(self.route.route_id, prop)
                self.assertIs(caught.exception.reason, s.SourceAuthorityReason.CLAIM_NOT_PERMITTED)

    def test_string_claims_are_not_typed_authority(self):
        with self.assertRaises(s.SourceAuthorityError):
            s.permitted_claim(self.route.route_id, "SOURCE_ACQUISITION_PROVENANCE")

    def test_registry_and_records_immutable(self):
        self.assertIsInstance(s._ROUTES, tuple)
        with self.assertRaises(FrozenInstanceError):
            self.route.provider = "Changed"
        with self.assertRaises(FrozenInstanceError):
            self.route.permitted_claims[0].role = "REAL"
        self.assertIs(s.get_source_route(self.route.route_id), self.route)

    def test_usage_and_factual_authority_are_independent(self):
        self.assertIs(self.route.license_status, s.UseStatus.UNKNOWN)
        self.assertIs(self.route.use_status, s.UseStatus.REVIEW_REQUIRED)
        changed = replace(self.route, use_status=s.UseStatus.UNKNOWN)
        self.assertEqual(changed.factual_hash, self.route.factual_hash)
        self.assertNotEqual(changed.profile_hash, self.route.profile_hash)
        self.assertEqual(changed.permitted_claims, self.route.permitted_claims)
        self.assertEqual(set(s.UseStatus), {s.UseStatus.UNKNOWN, s.UseStatus.REVIEW_REQUIRED})

    def test_powers_change_factual_identity(self):
        changed = replace(self.route, permitted_claims=self.route.permitted_claims[:-1])
        self.assertNotEqual(changed.factual_hash, self.route.factual_hash)
        self.assertNotEqual(changed.profile_hash, self.route.profile_hash)

    def test_unordered_profile_inventories_canonical(self):
        changed = replace(self.route, permitted_claims=tuple(reversed(self.route.permitted_claims)))
        self.assertEqual(changed.profile_hash, self.route.profile_hash)

    def test_core_types_have_no_universal_issuer_or_listing_fields(self):
        forbidden = {"cik", "accession", "ticker", "form", "venue", "sec_receipt_id", "accounting_basis"}
        for record in (s.SourceRouteProfile, s.ClaimGrant):
            self.assertFalse(forbidden & {f.name for f in fields(record)})

    def test_registered_profile_cannot_be_replaced_through_api(self):
        fake = replace(self.route, required_acquisition_contract="supplied-by-caller")
        with self.assertRaises(TypeError):
            s.get_source_route(self.route.route_id, profile=fake)
        self.assertIs(s.get_source_route(self.route.route_id), self.route)


if __name__ == "__main__":
    unittest.main()
