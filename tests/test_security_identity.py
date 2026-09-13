"""Fictional security identity qualification and adversarial trust boundaries."""
import ast
import builtins
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch

from economic_facts import security_identity as i
from economic_facts.sec_eps_series import AdmissionBlocker, ResolutionReason, ResolutionStatus
from tests.sec_eps_series_fixtures import annual_rows
from tests.security_identity_fixtures import (
    CAPTURED, COMMON, INTERVAL, ISSUER, LISTING, SECURITY, bundle, document,
    rename, request, resolve_series_fixture, series_fixture, snapshot,
)

R = i.IdentityReason
O = i.IdentityOutcome


class SecurityIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = series_fixture(multiple_versions=True)

    def setUp(self):
        self.claims = snapshot(self.series)

    def qualify(self, claims=None, *, sources=None, req=None):
        evidence = bundle(document(self.claims if claims is None else claims)) if sources is None else bundle(*sources)
        return i.qualify_security_identity(self.series, request(self.series) if req is None else req, evidence)

    def blocked(self, claims, *reasons, sources=None, req=None):
        result = self.qualify(claims, sources=sources, req=req)
        self.assertNotEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertTrue(set(reasons) <= set(result.reasons), result.reasons)
        self.assertIsNone(result.issuer)
        self.assertIsNone(result.security)
        self.assertIsNone(result.listing)
        self.assertEqual(result.applicability_decisions, ())
        self.assertEqual(result.authority, i.Authority.SYNTHETIC_TEST_ONLY)
        self.assertEqual(result.limitations, (R.SYNTHETIC_EVIDENCE_ONLY,))
        return result

    def security_change(self, **changes):
        return replace(self.claims, securities=(replace(self.claims.securities[0], **changes),))

    def listing_change(self, **changes):
        return replace(self.claims, listings=(replace(self.claims.listings[0], **changes),))

    def test_single_direct_ordinary_class_synthetic_success(self):
        result = self.qualify()
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.security.anchor, SECURITY)
        self.assertEqual(result.issuer.cik, self.series.cik)
        self.assertEqual(result.listing.anchor, LISTING)
        self.assertEqual(len(result.applicability_decisions), 5)
        self.assertEqual(result.qualification_as_of, CAPTURED)

    def cross_form_resolution(self, form="8-K", *, annual_form="10-K", conflict=False, replace_annual=False):
        rows = annual_rows()
        rows[-1] = dict(rows[-1], form=annual_form)
        other = dict(rows[-1], form=form, fp="Q4", accn="9999999999-25-000002")
        if conflict:
            other["val"] += 1
        return resolve_series_fixture((rows[:-1] if replace_annual else rows) + [other])

    def qualify_series(self, series, claims=None):
        return i.qualify_security_identity(series, request(series),
            bundle(document(snapshot(series) if claims is None else claims)))

    def reject_period(self, period, *, series=None):
        original = self.series if series is None else series
        changed = replace(original, periods=original.periods[:-1] + (period,))
        with self.assertRaises(i.IdentityContractError):
            self.qualify_series(changed)

    def test_agreeing_cross_forms_preserve_annual_support_and_complete_lineage(self):
        for annual_form in ("10-K", "10-K/A"):
            for form in ("8-K", "10-Q", "10-Q/A"):
                with self.subTest(annual_form=annual_form, form=form):
                    upstream = self.cross_form_resolution(form, annual_form=annual_form)
                    self.assertIs(upstream.status, ResolutionStatus.RESOLVED_ISSUER_EVIDENCE)
                    series = upstream.series
                    before = repr(series)
                    period = series.periods[-1]
                    self.assertEqual(len(period.filing_versions), 2)
                    self.assertEqual(len(period.supporting_observation_ids), 1)
                    comparable = {o for v in period.filing_versions for o in v.observation_ids}
                    self.assertGreater(comparable, set(period.supporting_observation_ids))
                    self.assertIn(period.representative_observation_id, period.supporting_observation_ids)
                    result = self.qualify_series(series)
                    self.assertIs(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
                    self.assertEqual(result.applicability_decisions[-1].version_ids, period.version_ids)
                    self.assertEqual(result.applicability_decisions[-1].observation_ids,
                                     period.supporting_observation_ids)
                    self.assertEqual(result.series_evidence_hash, series.evidence_hash)
                    self.assertEqual(set(result.downstream_blockers), set(series.downstream_admission_blockers))
                    self.assertIs(result.authority, i.Authority.SYNTHETIC_TEST_ONLY)
                    self.assertEqual(repr(series), before)

    def test_annual_support_requires_nonempty_unique_inventory_and_representative(self):
        period = self.series.periods[-1]
        for support in ((), period.supporting_observation_ids * 2, ("f" * 64,),
                        period.supporting_observation_ids + ("f" * 64,)):
            with self.subTest(support=support):
                self.reject_period(replace(period, supporting_observation_ids=support))
        self.reject_period(replace(period, representative_observation_id="f" * 64))

    def test_cross_form_observation_cannot_be_annual_support_or_representative(self):
        series = self.cross_form_resolution().series
        period = series.periods[-1]
        cross = next(v for v in period.filing_versions if v.form == "8-K").observation_ids
        for changes in (dict(representative_observation_id=cross[0]),
                        dict(supporting_observation_ids=period.supporting_observation_ids + cross),
                        dict(supporting_observation_ids=cross, representative_observation_id=cross[0])):
            with self.subTest(changes=changes):
                self.reject_period(replace(period, **changes), series=series)

    def test_annual_support_cannot_omit_an_annual_version(self):
        period = self.series.periods[-1]
        self.reject_period(replace(period, supporting_observation_ids=(period.representative_observation_id,)))

    def test_filing_version_ids_must_match_unique_records(self):
        period = self.series.periods[-1]
        for changes in (dict(version_ids=period.version_ids[:-1]),
                        dict(version_ids=period.version_ids + ("f" * 64,)),
                        dict(version_ids=period.version_ids * 2),
                        dict(filing_versions=period.filing_versions * 2)):
            with self.subTest(changes=changes):
                self.reject_period(replace(period, **changes))

    def test_comparable_observations_require_unique_nonempty_version_ownership(self):
        series = self.cross_form_resolution().series
        period = series.periods[-1]
        cross = next(v for v in period.filing_versions if v.form == "8-K")
        for observations in ((), cross.observation_ids * 2, period.supporting_observation_ids,
                             ("malformed",), ("",), (series.periods[0].representative_observation_id,)):
            with self.subTest(observations=observations):
                versions = tuple(replace(v, observation_ids=observations) if v is cross else v
                                 for v in period.filing_versions)
                self.reject_period(replace(period, filing_versions=versions), series=series)

    def test_malformed_linked_annual_observation_and_version_ids_rejected(self):
        series = series_fixture()
        period = series.periods[-1]
        for invalid in ("", "short", "g" * 64):
            with self.subTest(invalid=invalid):
                version = replace(period.filing_versions[0], observation_ids=(invalid,))
                self.reject_period(replace(period, filing_versions=(version,),
                    supporting_observation_ids=(invalid,), representative_observation_id=invalid), series=series)
                version = replace(period.filing_versions[0], semantic_id=invalid)
                self.reject_period(replace(period, filing_versions=(version,), version_ids=(invalid,)), series=series)

    def test_cross_form_applicability_requires_all_versions_but_only_annual_observations(self):
        series = self.cross_form_resolution().series
        claims = snapshot(series)
        application = claims.eps_applicability[-1]
        period = series.periods[-1]
        annual_versions = tuple(v.semantic_id for v in period.filing_versions if v.form == "10-K")
        all_observations = tuple(o for v in period.filing_versions for o in v.observation_ids)
        for changed in (replace(application, version_ids=annual_versions),
                        replace(application, observation_ids=all_observations)):
            with self.subTest(changed=changed):
                result = self.qualify_series(series, replace(claims,
                    eps_applicability=claims.eps_applicability[:-1] + (changed,)))
                self.assertIs(result.outcome, O.IDENTITY_UNAVAILABLE)
                self.assertIn(R.EPS_CLASS_APPLICABILITY_UNRESOLVED, result.reasons)

    def test_cross_form_conflicts_and_missing_annual_candidate_remain_upstream_unavailable(self):
        for form in ("8-K", "10-Q", "10-Q/A"):
            for changes, reason in ((dict(conflict=True), ResolutionReason.UNRESOLVED_VALUE_CONFLICT),
                                    (dict(replace_annual=True), ResolutionReason.MISSING_ANNUAL_PERIOD)):
                with self.subTest(form=form, changes=changes):
                    upstream = self.cross_form_resolution(form, **changes)
                    self.assertIs(upstream.status, ResolutionStatus.UNAVAILABLE)
                    self.assertIsNone(upstream.series)
                    self.assertIn(reason, upstream.reasons)
                    with self.assertRaises(i.IdentityContractError):
                        i.qualify_security_identity(upstream.series, request(self.series),
                                                    bundle(document(self.claims)))

    def test_cik_mismatch(self):
        self.blocked(replace(self.claims, issuer=replace(self.claims.issuer, cik="0000000001")),
                     R.ISSUER_IDENTIFIER_MISMATCH)

    def test_same_name_different_issuer_identifier(self):
        self.blocked(replace(self.claims, issuer=replace(self.claims.issuer, anchor="synthetic:issuer:other")),
                     R.ISSUER_IDENTIFIER_MISMATCH)

    def test_same_symbol_changed_security_anchor(self):
        self.blocked(self.security_change(anchor="synthetic:security:other"), R.SECURITY_IDENTIFIER_UNRESOLVED)

    def test_changed_anchor_changes_identity_even_with_same_symbol(self):
        other = "synthetic:security:other"
        claims = replace(self.security_change(anchor=other),
            listings=(replace(self.claims.listings[0], security_anchor=other),),
            listing_inventory=replace(self.claims.listing_inventory, security_anchor=other),
            eps_applicability=tuple(replace(a, security_anchor=other) for a in self.claims.eps_applicability))
        result = self.qualify(claims, req=request(self.series, security_anchor=other))
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertNotEqual(result.security.semantic_hash, self.qualify().security.semantic_hash)
        self.assertEqual(result.listing.symbol, self.qualify().listing.symbol)

    def test_changed_class_changes_security_semantics(self):
        common = replace(COMMON, class_id="fixture-replacement", legal_designation="Fixture Replacement")
        claims = replace(self.security_change(common_class=common),
            class_inventory=replace(self.claims.class_inventory, classes=(common,)),
            eps_applicability=tuple(replace(a, class_id=common.class_id) for a in self.claims.eps_applicability))
        self.assertNotEqual(self.qualify(claims).security.semantic_hash, self.qualify().security.semantic_hash)

    def test_explicit_symbol_rename_preserves_security_semantics(self):
        result = self.qualify(rename(self.claims))
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertEqual(result.security.semantic_hash, self.qualify().security.semantic_hash)
        self.assertEqual(result.listing.symbol, "FICTIONAL_RENAMED")
        self.assertNotEqual(result.listing.semantic_hash, self.qualify().listing.semantic_hash)

    def test_rename_requires_explicit_continuity(self):
        self.blocked(replace(rename(self.claims), symbol_continuities=()), R.SECURITY_CONTINUITY_UNRESOLVED)

    def test_ticker_only_anchor_rejected(self):
        self.blocked(self.security_change(anchor="FICTIONAL_ONE"), R.TICKER_ONLY_IDENTITY_INSUFFICIENT)

    def test_symbol_must_not_double_as_security_anchor(self):
        self.blocked(self.listing_change(symbol=SECURITY), R.TICKER_ONLY_IDENTITY_INSUFFICIENT)

    def test_missing_security_anchor(self):
        self.blocked(self.security_change(anchor=""), R.SECURITY_IDENTIFIER_UNRESOLVED)

    def test_missing_security_record(self):
        self.blocked(replace(self.claims, securities=()), R.SECURITY_IDENTIFIER_UNRESOLVED)

    def test_missing_common_class_inventory(self):
        self.blocked(replace(self.claims, class_inventory=None), R.COMMON_CLASS_INVENTORY_INCOMPLETE)

    def test_incomplete_common_class_inventory(self):
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory,
                     coverage=i.InventoryCoverage.INCOMPLETE)), R.COMMON_CLASS_INVENTORY_INCOMPLETE)

    def test_empty_common_class_inventory(self):
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory, classes=())),
                     R.SHARE_CLASS_UNRESOLVED)

    def test_two_common_classes_unsupported(self):
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory,
            classes=(COMMON, replace(COMMON, class_id="fixture-second")))), R.MULTIPLE_COMMON_CLASSES_UNSUPPORTED)

    def test_contradictory_claims_for_one_class_id(self):
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory,
            classes=(COMMON, replace(COMMON, legal_designation="Contradictory Fixture Class")))),
            R.IDENTITY_EVIDENCE_CONFLICT)

    def test_three_equivalent_looking_classes_unsupported(self):
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory,
            classes=tuple(replace(COMMON, class_id="fixture-" + letter) for letter in "ABC"))),
            R.MULTIPLE_COMMON_CLASSES_UNSUPPORTED)

    def test_different_participation_rights(self):
        other = replace(COMMON, class_id="fixture-second", participation=i.Participation.DIFFERENT_PARTICIPATION_RIGHTS)
        self.blocked(replace(self.claims, class_inventory=replace(self.claims.class_inventory,
            classes=(COMMON, other))), R.MULTIPLE_COMMON_CLASSES_UNSUPPORTED, R.PARTICIPATION_RIGHTS_UNRESOLVED)

    def test_unknown_participation(self):
        self.blocked(self.security_change(common_class=replace(COMMON, participation=i.Participation.UNRESOLVED)),
                     R.PARTICIPATION_RIGHTS_UNRESOLVED)

    def test_missing_class_designation(self):
        for key in ("class_id", "legal_designation", "economic_designation"):
            with self.subTest(key=key):
                self.blocked(self.security_change(common_class=replace(COMMON, **{key: ""})), R.SHARE_CLASS_UNRESOLVED)

    def test_missing_applicability_each_period(self):
        for n in range(5):
            with self.subTest(period=n):
                self.blocked(replace(self.claims, eps_applicability=self.claims.eps_applicability[:n]
                    + self.claims.eps_applicability[n + 1:]), R.EPS_CLASS_APPLICABILITY_UNRESOLVED)

    def test_missing_supporting_filing_version(self):
        a = self.claims.eps_applicability[-1]
        self.assertEqual(len(a.version_ids), 2)
        self.blocked(replace(self.claims, eps_applicability=self.claims.eps_applicability[:-1]
            + (replace(a, version_ids=a.version_ids[:1]),)), R.EPS_CLASS_APPLICABILITY_UNRESOLVED)

    def test_missing_supporting_observation(self):
        a = self.claims.eps_applicability[0]
        self.assertEqual(len(a.observation_ids), 2)
        self.blocked(replace(self.claims, eps_applicability=(replace(a, observation_ids=a.observation_ids[:1]),)
            + self.claims.eps_applicability[1:]), R.EPS_CLASS_APPLICABILITY_UNRESOLVED)

    def test_conflicting_eps_class_applicability(self):
        self.blocked(replace(self.claims, eps_applicability=self.claims.eps_applicability
            + (replace(self.claims.eps_applicability[0], class_id="fixture-other"),)),
            R.EPS_CLASS_APPLICABILITY_UNRESOLVED, R.IDENTITY_EVIDENCE_CONFLICT)

    def test_every_application_bound_to_exact_series(self):
        for key in ("series_semantic_hash", "series_evidence_hash"):
            self.blocked(replace(self.claims, eps_applicability=(replace(self.claims.eps_applicability[0], **{key: "f" * 64}),)
                + self.claims.eps_applicability[1:]), R.EPS_CLASS_APPLICABILITY_UNRESOLVED)

    def test_all_other_instrument_types_unsupported(self):
        for kind in i.InstrumentType:
            if kind is i.InstrumentType.ORDINARY_COMMON_EQUITY:
                continue
            with self.subTest(kind=kind):
                result = self.blocked(self.security_change(instrument_type=kind), R.INSTRUMENT_TYPE_UNSUPPORTED)
                self.assertEqual(result.outcome, O.IDENTITY_UNSUPPORTED)

    def test_every_depositary_type_unsupported(self):
        for kind in (i.InstrumentType.ADR, i.InstrumentType.ADS, i.InstrumentType.CDR,
                     i.InstrumentType.DEPOSITARY_RECEIPT):
            self.blocked(self.security_change(instrument_type=kind), R.DEPOSITARY_RECEIPT_UNSUPPORTED)

    def test_one_to_one_label_cannot_admit_depositary(self):
        claims = self.security_change(instrument_type=i.InstrumentType.ADR,
                                     secondary_identifiers=("synthetic:description:one_to_one",))
        self.blocked(claims, R.DEPOSITARY_RECEIPT_UNSUPPORTED)

    def test_depositary_listing_cannot_hide_under_common_security(self):
        self.blocked(self.listing_change(kind=i.ListingKind.DEPOSITARY), R.DEPOSITARY_RECEIPT_UNSUPPORTED)

    def test_dual_listing_does_not_select_requested_winner(self):
        other = replace(self.claims.listings[0], anchor="synthetic:listing:second", venue="MIC:XNAS")
        self.blocked(replace(self.claims, listings=self.claims.listings + (other,),
            listing_inventory=replace(self.claims.listing_inventory, listing_anchors=(LISTING, other.anchor))),
            R.DUAL_LISTING_UNSUPPORTED)

    def test_sequential_exchange_migration_unsupported(self):
        claims = rename(self.claims)
        other = replace(claims.listings[0], anchor="synthetic:listing:previous", venue="MIC:XNAS")
        self.blocked(replace(claims, listings=(other, claims.listings[1]), symbol_continuities=(),
            listing_inventory=replace(claims.listing_inventory, listing_anchors=(other.anchor, LISTING))),
            R.LISTING_MIGRATION_UNSUPPORTED)

    def test_missing_listing_inventory(self):
        self.blocked(replace(self.claims, listing_inventory=None), R.LISTING_UNRESOLVED)

    def test_listing_inventory_cannot_omit_second_listing(self):
        other = replace(self.claims.listings[0], anchor="synthetic:listing:second")
        self.blocked(replace(self.claims, listings=self.claims.listings + (other,)),
                     R.LISTING_UNRESOLVED, R.DUAL_LISTING_UNSUPPORTED)

    def test_incomplete_listing_inventory(self):
        self.blocked(replace(self.claims, listing_inventory=replace(self.claims.listing_inventory,
            coverage=i.InventoryCoverage.INCOMPLETE)), R.LISTING_UNRESOLVED)

    def test_missing_or_unlisted_venue(self):
        for venue in ("", "UNKNOWN", "MIC:FICTIONAL"):
            self.blocked(self.listing_change(venue=venue), R.LISTING_UNRESOLVED)

    def test_missing_and_non_usd_currency(self):
        for currency in ("", "CAD", "usd"):
            result = self.blocked(self.listing_change(quote_currency=currency), R.LISTING_CURRENCY_OR_UNIT_UNRESOLVED)
            self.assertEqual(result.outcome, O.IDENTITY_UNSUPPORTED if currency else O.IDENTITY_UNAVAILABLE)

    def test_unknown_and_minor_quote_unit(self):
        for unit in (i.QuoteUnit.UNKNOWN, i.QuoteUnit.MINOR_CURRENCY_UNIT):
            self.blocked(self.listing_change(quote_unit=unit), R.LISTING_CURRENCY_OR_UNIT_UNRESOLVED)

    def test_effective_gap_in_rename(self):
        claims = rename(self.claims)
        late = replace(claims.listings[1], interval=replace(claims.listings[1].interval, start="2026-03-02"))
        self.blocked(replace(claims, listings=(claims.listings[0], late)), R.EFFECTIVE_INTERVAL_UNRESOLVED)

    def test_contradictory_overlapping_listing_states(self):
        self.blocked(replace(self.claims, listings=self.claims.listings +
            (replace(self.claims.listings[0], symbol="FICTIONAL_OTHER"),)), R.IDENTITY_EVIDENCE_CONFLICT)

    def test_contradictory_overlapping_security_states(self):
        self.blocked(replace(self.claims, securities=self.claims.securities +
            (replace(self.claims.securities[0], common_class=replace(COMMON, class_id="fixture-other")),)),
            R.IDENTITY_EVIDENCE_CONFLICT)

    def test_future_listing_does_not_qualify_current(self):
        self.blocked(self.listing_change(interval=i.EffectiveInterval("2026-04-01", "2027-12-31")),
                     R.EFFECTIVE_INTERVAL_UNRESOLVED)

    def test_expired_current_state(self):
        self.blocked(self.listing_change(interval=i.EffectiveInterval("2020-01-01", "2026-03-01")),
                     R.EFFECTIVE_INTERVAL_UNRESOLVED)

    def test_security_must_cover_each_eps_period(self):
        self.blocked(self.security_change(interval=i.EffectiveInterval("2021-01-01", "2027-12-31")),
                     R.SECURITY_CONTINUITY_UNRESOLVED)

    def test_historical_returns_no_partial_answer_or_evidence_boundary(self):
        req = request(self.series, mode=i.IdentityMode.HISTORICAL_AS_OF)
        result = i.qualify_security_identity(self.series, req, object())
        self.assertEqual(result.reasons, (R.HISTORICAL_IDENTITY_UNSUPPORTED,))
        self.assertIsNone(result.qualification_as_of)
        self.assertIsNone(result.security)
        self.assertEqual(result.considered_evidence_ids, ())

    def test_reorganization_and_successor_unsupported(self):
        for kind in (i.Continuity.REORGANIZATION, i.Continuity.SUCCESSOR):
            self.blocked(replace(self.claims, continuity=kind), R.CORPORATE_REORGANIZATION_UNSUPPORTED)

    def test_authority_has_no_upgrade_and_request_has_no_asof(self):
        self.assertEqual(list(i.Authority), [i.Authority.SYNTHETIC_TEST_ONLY])
        self.assertNotIn("as_of", {f.name for f in fields(i.SecurityIdentityRequest)})
        self.assertNotIn("authority", {f.name for f in fields(i.SecurityIdentityRequest)})
        with self.assertRaises(i.IdentityContractError):
            self.qualify(sources=(replace(document(self.claims), source_kind="REAL"),))

    def test_unknown_enums_mutable_inputs_subclasses_and_fields(self):
        with self.assertRaises(TypeError):
            i.SecurityIdentityRequest(**{f.name: getattr(request(self.series), f.name)
                                      for f in fields(i.SecurityIdentityRequest)}, is_valid=True)
        for claims in (self.security_change(instrument_type="ORDINARY_COMMON_EQUITY"),
                       replace(self.claims, securities=list(self.claims.securities)),
                       self.listing_change(quote_unit=True)):
            with self.assertRaises(i.IdentityContractError):
                self.qualify(sources=(replace(document(self.claims), claims=claims),))
        class Subrequest(i.SecurityIdentityRequest):
            pass
        with self.assertRaises(i.IdentityContractError):
            self.qualify(req=Subrequest(*(getattr(request(self.series), f.name) for f in fields(i.SecurityIdentityRequest))))

    def test_hash_mismatch(self):
        with self.assertRaises(i.IdentityContractError):
            self.qualify(sources=(replace(document(self.claims), content_sha256="0" * 64),))

    def test_locator_mismatch(self):
        with self.assertRaises(i.IdentityContractError):
            self.qualify(sources=(replace(document(self.claims), source_locator="/unrelated"),))

    def test_source_claims_cannot_be_detached_from_bytes(self):
        with self.assertRaises(i.IdentityContractError):
            self.qualify(sources=(replace(document(self.claims), claims=self.security_change(anchor="synthetic:security:other")),))

    def test_unknown_source_fields_and_duplicate_json_keys(self):
        source = document(self.claims)
        parsed = json.loads(source.source_bytes)
        parsed["claims"]["single_class"] = True
        bodies = (json.dumps(parsed).encode(), b'{"claims":{},"claims":{}}', b'{"claims":NaN}')
        for raw in bodies:
            with self.assertRaises(i.IdentityContractError):
                self.qualify(sources=(replace(source, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest()),))

    def test_conflicting_complete_sources_never_latest_win(self):
        changed = replace(self.claims, issuer=replace(self.claims.issuer, interval=replace(INTERVAL, end="2028-12-31")))
        self.blocked(None, R.IDENTITY_EVIDENCE_CONFLICT,
            sources=(document(self.claims), document(changed, captured_at="2026-03-03T12:00:00Z")))

    def test_partial_sources_cannot_stitch_missing_periods(self):
        a = replace(self.claims, eps_applicability=self.claims.eps_applicability[:3])
        b = replace(self.claims, eps_applicability=self.claims.eps_applicability[3:])
        self.blocked(None, R.EPS_CLASS_APPLICABILITY_UNRESOLVED, sources=(document(a), document(b)))

    def test_document_and_claim_reordering(self):
        sources = (document(self.claims), document(self.claims, captured_at="2026-03-03T12:00:00Z"))
        self.assertEqual(self.qualify(sources=sources), self.qualify(sources=sources[::-1]))
        claims = replace(self.claims, eps_applicability=tuple(replace(a, version_ids=a.version_ids[::-1],
            observation_ids=a.observation_ids[::-1]) for a in self.claims.eps_applicability[::-1]))
        self.assertEqual(self.qualify(claims).semantic_hash, self.qualify().semantic_hash)

    def test_rename_order_does_not_select_current_symbol(self):
        claims = rename(self.claims)
        result = self.qualify(replace(claims, listings=claims.listings[::-1]))
        self.assertEqual(result.semantic_hash, self.qualify(claims).semantic_hash)
        self.assertEqual(result.listing.symbol, "FICTIONAL_RENAMED")

    def test_all_considered_sources_bind_failure_evidence_hash(self):
        a = self.security_change(anchor="")
        b = replace(a, issuer=replace(a.issuer, descriptive_name="Another Fictional Name"))
        first, second = self.qualify(a), self.qualify(b)
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)

    def test_forged_extra_applicability_and_observation_ids(self):
        a = self.claims.eps_applicability[0]
        for changed in (replace(a, observation_ids=a.observation_ids + ("f" * 64,)),
                        replace(a, version_ids=a.version_ids + ("f" * 64,)),
                        replace(a, period=i.EffectiveInterval("2019-01-01", "2019-12-31"))):
            self.blocked(replace(self.claims, eps_applicability=(changed,) + self.claims.eps_applicability[1:]),
                         R.EPS_CLASS_APPLICABILITY_UNRESOLVED)

    def test_duplicate_identical_sources_do_not_multiply_evidence(self):
        source = document(self.claims)
        self.assertEqual(self.qualify(sources=(source, source)), self.qualify(sources=(source,)))

    def test_equivalent_duplicate_applicability_id_order(self):
        a = self.claims.eps_applicability[-1]
        duplicate = replace(a, version_ids=a.version_ids[::-1], observation_ids=a.observation_ids[::-1])
        result = self.qualify(replace(self.claims, eps_applicability=self.claims.eps_applicability + (duplicate,)))
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertEqual(result.semantic_hash, self.qualify().semantic_hash)

    def test_secondary_identifiers_in_repeated_security_claims(self):
        extra = replace(self.claims.securities[0], secondary_identifiers=("synthetic:secondary:extra",))
        result = self.qualify(replace(self.claims, securities=self.claims.securities + (extra,)))
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.assertEqual(result.security.semantic_hash, self.qualify().security.semantic_hash)
        self.assertEqual(result.security.secondary_identifiers, extra.secondary_identifiers)

    def test_reordered_json_bytes_preserve_semantics_change_evidence(self):
        source = document(self.claims)
        raw = json.dumps(json.loads(source.source_bytes), indent=2).encode()
        other = replace(source, source_bytes=raw, content_sha256=hashlib.sha256(raw).hexdigest())
        first, second = self.qualify(sources=(source,)), self.qualify(sources=(other,))
        self.assertEqual(first.semantic_hash, second.semantic_hash)
        self.assertNotEqual(first.evidence_hash, second.evidence_hash)

    def test_later_required_capture_cannot_keep_expired_listing(self):
        claims = self.listing_change(interval=i.EffectiveInterval("2020-01-01", "2026-03-02"))
        self.assertEqual(self.qualify(claims).outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)
        self.blocked(None, R.EFFECTIVE_INTERVAL_UNRESOLVED,
            sources=(document(claims), document(claims, captured_at="2026-03-03T12:00:00Z")))

    def test_recapture_changes_evidence_only(self):
        a = self.qualify()
        b = self.qualify(sources=(document(self.claims, captured_at="2026-03-03T12:00:00Z"),))
        self.assertEqual(a.security.semantic_hash, b.security.semantic_hash)
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)
        self.assertEqual(b.qualification_as_of, "2026-03-03T12:00:00Z")

    def test_secondary_identifier_addition_is_not_anchor_selection(self):
        a = self.qualify()
        b = self.qualify(self.security_change(secondary_identifiers=("synthetic:secondary:aaa",)))
        self.assertEqual(a.security.semantic_hash, b.security.semantic_hash)
        self.assertEqual(a.semantic_hash, b.semantic_hash)
        self.assertNotEqual(a.evidence_hash, b.evidence_hash)

    def test_name_changes_are_descriptive_only(self):
        other = replace(self.claims, issuer=replace(self.claims.issuer, descriptive_name="Entirely Different Fictional Name"))
        self.assertEqual(self.qualify(other).semantic_hash, self.qualify().semantic_hash)

    def test_no_series_mutation_and_all_blockers_retained(self):
        before = repr(self.series)
        result = self.qualify()
        self.assertEqual(repr(self.series), before)
        self.assertEqual(result.series_semantic_hash, self.series.semantic_hash)
        self.assertEqual(result.series_evidence_hash, self.series.evidence_hash)
        self.assertEqual(set(result.downstream_blockers), set(self.series.downstream_admission_blockers))
        for blocker in (AdmissionBlocker.SPLIT_BASIS_NOT_ESTABLISHED,
                        AdmissionBlocker.ECONOMIC_COMPARABILITY_NOT_ESTABLISHED,
                        AdmissionBlocker.PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED,
                        AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED):
            self.assertIn(blocker, result.downstream_blockers)

    def test_empty_bundle_still_retains_blockers(self):
        result = self.blocked(None, R.SECURITY_IDENTIFIER_UNRESOLVED, sources=())
        self.assertEqual(set(result.downstream_blockers), set(self.series.downstream_admission_blockers))

    def test_result_and_claims_immutable(self):
        for value, field in ((self.qualify(), "authority"), (self.claims, "continuity")):
            with self.assertRaises(FrozenInstanceError):
                setattr(value, field, None)
            self.assertFalse(hasattr(value, "__dict__"))

    def test_series_binding_and_missing_blockers_fail(self):
        with self.assertRaises(i.IdentityContractError):
            self.qualify(req=request(self.series, series_evidence_hash="0" * 64))
        with self.assertRaises(i.IdentityContractError):
            i.qualify_security_identity(replace(self.series, downstream_admission_blockers=()),
                                        request(self.series), bundle(document(self.claims)))

    def test_bad_dates_and_chronology(self):
        for interval in (i.EffectiveInterval("2020-1-01", "2027-12-31"),
                         i.EffectiveInterval("2027-12-31", "2020-01-01")):
            with self.assertRaises(i.IdentityContractError):
                self.qualify(self.security_change(interval=interval))
        for change in (dict(captured_at="2026-03-02"), dict(captured_at="2026-03-02T09:00:00Z"),
                       dict(available_at="2026-03-04T00:00:00Z"), dict(captured_at="2026-03-02T12:00:00-00:00")):
            with self.assertRaises(i.IdentityContractError):
                self.qualify(sources=(document(self.claims, **change),))

    def test_series_authority_is_boundary_floor(self):
        source = document(self.claims, published_at="2026-02-28T00:00:00Z",
                          available_at="2026-02-28T01:00:00Z", captured_at="2026-02-28T02:00:00Z")
        self.assertEqual(self.qualify(sources=(source,)).qualification_as_of, self.series.authority_as_of)

    def test_no_network_writes_environment_or_clock_calls(self):
        source = document(self.claims)
        with patch.object(socket, "socket", side_effect=AssertionError), \
             patch.object(builtins, "open", side_effect=AssertionError), \
             patch.object(Path, "write_text", side_effect=AssertionError), \
             patch.object(Path, "write_bytes", side_effect=AssertionError), \
             patch.object(os, "getenv", side_effect=AssertionError), \
             patch.object(subprocess, "run", side_effect=AssertionError):
            result = self.qualify(sources=(source,))
        self.assertEqual(result.outcome, O.IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE)

    def test_exact_static_dependency_boundary_and_alias_isolation(self):
        tree = ast.parse(inspect.getsource(i))
        allowed = {"dataclasses", "datetime", "decimal", "enum", "hashlib", "json", "re", "types", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(a.name in allowed for a in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertTrue(node.module in allowed or (node.level == 1 and node.module == "sec_eps_series"))
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                self.assertNotIn(name, {"open", "write", "write_text", "write_bytes", "now", "today", "getenv",
                    "system", "run", "exec", "eval", "__import__", "resolve_ticker", "company_names_match", "infer_quote_currency"})
        text = inspect.getsource(i)
        for forbidden in ("ticker_aliases", "src.", "yfinance", "portfolio", "acquisition", "expected_return"):
            self.assertNotIn(forbidden, text)

    def test_hash_seed_process_determinism_without_model_import(self):
        script = """from tests.security_identity_fixtures import *
from economic_facts.security_identity import qualify_security_identity
import sys
s = series_fixture(True)
r = qualify_security_identity(s, request(s), bundle(document(snapshot(s))))
assert not any(n.startswith(('src.', 'economic_facts.sec_acquisition')) for n in sys.modules)
print(r.semantic_hash, r.evidence_hash)
"""
        outputs = []
        for seed in ("1", "83"):
            outputs.append(subprocess.check_output([sys.executable, "-B", "-c", script],
                env={**os.environ, "PYTHONHASHSEED": seed, "LC_ALL": "C"}, text=True))
        self.assertEqual(outputs[0], outputs[1])
