"""Synthetic D2 contract tests; no authentic SEC qualification is claimed."""
import ast
from copy import deepcopy
from dataclasses import asdict, FrozenInstanceError, replace
from decimal import Decimal, localcontext, Inexact, Rounded, FloatOperation
import inspect
import json
import pickle
import socket
from unittest.mock import patch

from economic_facts.sec_archive import ArchiveError, SecArchive
from economic_facts.sec_revenue_operating_income import CONCEPTS
from src import d1_two_period_operating_profit_continuity as d1
from src import d2_two_period_reported_trajectory as d2
from tests.sec_d1_two_period_fixtures import D1Fixture, comparative, row, payload, OTHER, a


class D2DiagnosticTests(D1Fixture):
    def analyze(self, source=None, **kwargs):
        return d2.analyze_d2_two_period_reported_trajectory_v1(self.evaluate(source, **kwargs))

    def assert_fraction(self, result, numerator, denominator):
        self.assertEqual((result.numerator, result.denominator), (numerator, denominator))

    def assert_no_trajectory(self, result):
        for key in ('revenue_direction', 'operating_income_direction', 'revenue_relative_change'):
            self.assertIsNone(getattr(result, key))

    def test_all_nine_revenue_and_operating_income_directions(self):
        for r1, rd in ((80, 'DECREASED'), (100, 'UNCHANGED'), (120, 'INCREASED')):
            for o1, od in ((-20, 'DECREASED'), (0, 'UNCHANGED'), (20, 'INCREASED')):
                with self.subTest(r1=r1, o1=o1):
                    result = self.analyze(comparative(100, 0, r1, o1))
                    self.assertIs(result.status, d2.S.AVAILABLE)
                    self.assertEqual(result.reasons, ())
                    self.assertEqual(result.revenue_direction.value, rd)
                    self.assertEqual(result.operating_income_direction.value, od)
                    self.assert_fraction(result.revenue_relative_change, r1 // 20 - 5, 5 if r1 != 100 else 1)

    def test_operating_income_direction_across_positive_zero_negative_and_losses(self):
        for o0, o1, direction in ((-20, -10, 'INCREASED'), (-10, -20, 'DECREASED'),
                (-10, -10, 'UNCHANGED'), (-10, 0, 'INCREASED'), (0, -10, 'DECREASED'),
                (0, 10, 'INCREASED'), (10, 0, 'DECREASED'), (10, -10, 'DECREASED'),
                (-10, 10, 'INCREASED'), (10, 20, 'INCREASED'), (20, 10, 'DECREASED'),
                (10, 10, 'UNCHANGED'), (0, 0, 'UNCHANGED')):
            with self.subTest(o0=o0, o1=o1):
                result = self.analyze(comparative(100, o0, 100, o1))
                self.assertEqual(result.operating_income_direction.value, direction)
                self.assertFalse(hasattr(result, 'operating_income_relative_change'))

    def test_exact_reduced_signed_revenue_changes(self):
        for r0, r1, num, den in ((80, 100, 1, 4), (100, 80, -1, 5), (3, 4, 1, 3),
                                (7, 7, 0, 1), (6, 2, -2, 3)):
            result = self.analyze(comparative(r0, 10, r1, 20))
            self.assert_fraction(result.revenue_relative_change, num, den)

    def test_fractional_decimals_and_hostile_context_without_premature_subtraction(self):
        raw = json.dumps(comparative()).encode()
        for old, new in ((b'"val": 80', b'"val": 0.1250'),
                         (b'"val": 100', b'"val": 0.7501'),
                         (b'"val": 10', b'"val": -0.125'),
                         (b'"val": 20', b'"val": 0.000')):
            raw = raw.replace(old, new)
        normal = self.analyze(raw=raw)
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.Emax = 1
            ctx.Emin = -1
            for signal in (Inexact, Rounded, FloatOperation):
                ctx.traps[signal] = True
            hostile = self.analyze(raw=raw)
            self.assertEqual((normal.semantic_id, normal.evidence_id),
                             (hostile.semantic_id, hostile.evidence_id))
            self.assert_fraction(hostile.revenue_relative_change, 6251, 1250)
            self.assertEqual(hostile.operating_income_direction.value, 'INCREASED')
            self.assertEqual(hostile.prior_revenue.as_tuple(), Decimal('0.1250').as_tuple())

    def test_preserves_four_original_decimals_periods_and_provenance(self):
        qualification = self.evaluate()
        result = d2.analyze_d2_two_period_reported_trajectory_v1(qualification)
        for key in ('prior_revenue', 'prior_operating_income', 'current_revenue',
                    'current_operating_income', 'prior_period_start', 'prior_period_end',
                    'current_period_start', 'current_period_end', 'source_cik'):
            self.assertEqual(getattr(result, key), getattr(qualification, key))
        self.assertEqual(result.upstream_qualification_semantic_id, qualification.semantic_id)
        self.assertEqual(result.upstream_qualification_evidence_id, qualification.evidence_id)
        with self.assertRaises(FrozenInstanceError):
            result.status = d2.S.UNAVAILABLE

    def test_nonpositive_revenues_suppress_all_trajectory_outputs(self):
        for r0 in (0, -100, 100):
            for r1 in (0, -200, 200):
                if r0 > 0 and r1 > 0:
                    continue
                result = self.analyze(comparative(r0, -1, r1, 0))
                self.assertIs(result.status, d2.S.NOT_APPLICABLE)
                self.assert_no_trajectory(result)
                self.assertEqual((result.prior_revenue, result.current_revenue),
                                 (Decimal(r0), Decimal(r1)))
                expected = []
                if r0 <= 0:
                    expected.append(d2.R.PRIOR_REVENUE_ZERO if r0 == 0 else d2.R.PRIOR_REVENUE_NEGATIVE)
                if r1 <= 0:
                    expected.append(d2.R.CURRENT_REVENUE_ZERO if r1 == 0 else d2.R.CURRENT_REVENUE_NEGATIVE)
                self.assertEqual(result.reasons, tuple(sorted(expected, key=lambda r: r.value)))
                self.assertEqual(result.upstream_reasons, ())

    def test_all_nonestablished_statuses_without_partial_facts_or_dates(self):
        conflict = comparative()
        conflict['facts']['us-gaap'][CONCEPTS[0]]['units']['USD'].append(row(999, accn=OTHER))
        for source, status, reason in (
                (payload(), d2.S.UNAVAILABLE, d2.R.UPSTREAM_EVIDENCE_UNAVAILABLE),
                (comparative(fp='Q4'), d2.S.UNSUPPORTED, d2.R.UPSTREAM_EVIDENCE_UNSUPPORTED),
                (conflict, d2.S.SOURCE_CONFLICT, d2.R.UPSTREAM_SOURCE_CONFLICT)):
            qualification = self.evaluate(source)
            result = d2.analyze_d2_two_period_reported_trajectory_v1(qualification)
            self.assertIs(result.status, status)
            self.assertEqual(result.reasons, (reason,))
            self.assertEqual(result.upstream_status, qualification.status)
            self.assertEqual(result.upstream_reasons, qualification.reasons)
            self.assert_no_trajectory(result)
            for key in ('prior_revenue', 'prior_operating_income', 'current_revenue',
                        'current_operating_income', 'prior_period_start', 'prior_period_end',
                        'current_period_start', 'current_period_end'):
                self.assertIsNone(getattr(result, key))

    def test_wrong_foreign_and_detached_public_inputs_rejected(self):
        q = self.evaluate()
        for wrong in ({}, None, True, asdict(q), d1.analyze_d1_two_period_operating_profit_continuity_v1(q)):
            with self.assertRaises(d2.D2DiagnosticError):
                d2.analyze_d2_two_period_reported_trajectory_v1(wrong)
        class Subclass(a.CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1):
            pass
        with self.assertRaises(d2.D2DiagnosticError):
            d2.analyze_d2_two_period_reported_trajectory_v1(object.__new__(Subclass))
        for wrong in (replace(q), deepcopy(q), pickle.loads(pickle.dumps(q))):
            with self.assertRaises(ArchiveError):
                d2.analyze_d2_two_period_reported_trajectory_v1(wrong)

    def test_modified_and_self_consistently_forged_facts_fail_replay(self):
        q = self.evaluate()
        for key, value in (('current_revenue', Decimal(999)),
                           ('prior_operating_income', Decimal(-99)),
                           ('current_period_start', '2024-01-02'),
                           ('source_cik', '0000000001'), ('captured_at', '2025-08-03T00:00:00Z'),
                           ('extraction_inventory_id', '0' * 64)):
            forged = replace(q, **{key: value})
            object.__setattr__(forged, '_archive_replay_binding', q._archive_replay_binding)
            with self.subTest(key=key), self.assertRaises(ArchiveError):
                d2.analyze_d2_two_period_reported_trajectory_v1(forged)

    def test_invalid_contract_version_and_identity_are_integrity_errors(self):
        q = self.evaluate()
        with patch.object(type(q), 'contract_version', 'wrong-version'), self.assertRaises(ArchiveError):
            d2.analyze_d2_two_period_reported_trajectory_v1(q)
        for key in ('semantic_id', 'evidence_id'):
            original = getattr(type(q), key)
            mismatched = property(lambda obj, original=original: '0' * 64
                                  if obj is q else original.fget(obj))
            with patch.object(type(q), key, mismatched), self.assertRaises(ArchiveError):
                d2.analyze_d2_two_period_reported_trajectory_v1(q)

    def test_stale_binding_and_missing_receipt_fail_closed(self):
        q = self.evaluate()
        forged = replace(q)
        object.__setattr__(forged, '_archive_replay_binding',
                           replace(q._archive_replay_binding, receipt_id='0' * 64))
        with self.assertRaises(ArchiveError):
            d2.analyze_d2_two_period_reported_trajectory_v1(forged)
        receipt = self.root / 'receipts' / (q.capture_receipt_id + '.json')
        self.assertTrue(receipt.is_file())
        receipt.unlink()
        with self.assertRaises(ArchiveError):
            d2.analyze_d2_two_period_reported_trajectory_v1(q)

    def test_missing_and_altered_source_objects_fail_before_each_status(self):
        for source in (comparative(), comparative(r0=0), payload(), comparative(fp='Q4'),
                       comparative(filed='2025-09-01')):
            for alteration in ('missing', 'changed'):
                q = self.evaluate(source)
                path = self.root / 'objects' / q.source_object_hash
                if alteration == 'missing':
                    path.unlink()
                else:
                    altered = path.read_bytes() + b' '
                    path.unlink()
                    path.write_bytes(altered)
                    path.chmod(0o400)
                with self.assertRaises(ArchiveError):
                    d2.analyze_d2_two_period_reported_trajectory_v1(q)
                # Restore only synthetic fixture bytes for the next case.
                if path.exists():
                    path.unlink()

    def test_reconstructed_snapshot_is_used_once(self):
        q = self.evaluate()
        with patch.object(a, '_qualify_extraction', wraps=a._qualify_extraction) as replay:
            d2.analyze_d2_two_period_reported_trajectory_v1(q)
        self.assertEqual(replay.call_count, 1)

    def test_semantic_identity_survives_recapture_evidence_identity_changes(self):
        original = self.analyze()
        recaptured = self.analyze(timestamp='2025-08-02T00:00:00Z')
        self.assertEqual(original.semantic_id, recaptured.semantic_id)
        self.assertNotEqual(original.evidence_id, recaptured.evidence_id)
        scaled = self.analyze(comparative(160, 20, 200, 40))
        self.assertEqual(original.revenue_relative_change, scaled.revenue_relative_change)
        self.assertNotEqual(original.semantic_id, scaled.semantic_id)
        income_changed = self.analyze(comparative(o1=21))
        self.assertNotEqual(original.semantic_id, income_changed.semantic_id)

    def test_equivalent_decimal_encoding_and_duplicate_inventory_identity(self):
        original = self.analyze()
        raw = json.dumps(comparative()).encode().replace(b'"val": 80', b'"val": 80.000')
        equivalent = self.analyze(raw=raw)
        self.assertEqual(original.semantic_id, equivalent.semantic_id)
        self.assertNotEqual(original.evidence_id, equivalent.evidence_id)
        source = comparative()
        for concept in CONCEPTS:
            rows = source['facts']['us-gaap'][concept]['units']['USD']
            rows.reverse()
            rows.append(deepcopy(rows[0]))
        duplicate = self.analyze(source)
        self.assertEqual(original.semantic_id, duplicate.semantic_id)
        self.assertNotEqual(original.evidence_id, duplicate.evidence_id)

    def test_d1_and_d2_complement_margin_and_amount_observations(self):
        q = self.evaluate(comparative(100, 20, 200, 30))
        margin = d1.analyze_d1_two_period_operating_profit_continuity_v1(q)
        trajectory = d2.analyze_d2_two_period_reported_trajectory_v1(q)
        self.assertEqual(margin.ratio_direction.value, 'DECREASED')
        self.assertEqual(trajectory.revenue_direction.value, 'INCREASED')
        self.assertEqual(trajectory.operating_income_direction.value, 'INCREASED')
        self.assert_fraction(trajectory.revenue_relative_change, 1, 1)

    def test_supplied_authentic_amounts_are_only_a_synthetic_arithmetic_oracle(self):
        result = self.analyze(comparative(281724000000, 128528000000, 331839000000, 155237000000))
        self.assertEqual(result.revenue_direction.value, 'INCREASED')
        self.assertEqual(result.operating_income_direction.value, 'INCREASED')
        self.assert_fraction(result.revenue_relative_change, 16705, 93908)

    def test_rational_carrier_canonicalization_and_invalid_input(self):
        for num, den, expected in ((2, 4, (1, 2)), (2, -4, (-1, 2)), (0, -3, (0, 1))):
            self.assert_fraction(d2.RevenueRelativeChange(num, den), *expected)
        for num, den in ((True, 2), (1, False), (1.0, 2), (1, 0)):
            with self.assertRaises(d2.D2DiagnosticError):
                d2.RevenueRelativeChange(num, den)

    def test_bounded_authority_and_no_network_capture_clock_or_persistent_mutation(self):
        q = self.evaluate()
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with (patch.object(socket, 'socket', side_effect=AssertionError('network')),
              patch.object(SecArchive, '_capture', side_effect=AssertionError('capture'))):
            result = d2.analyze_d2_two_period_reported_trajectory_v1(q)
        self.assertEqual(before, {str(p.relative_to(self.root)): p.read_bytes()
                                 for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(result.authority, 'DURABILITY_D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_ONLY')
        self.assertEqual(result.temporal_mode, 'CURRENT_CAPTURE_BOUND_ONLY')
        self.assertFalse({'score', 'confidence', 'expected_return', 'recommendation', 'allocation'} & asdict(result).keys())
        self.assertEqual({s.value for s in d2.S}, {'AVAILABLE', 'NOT_APPLICABLE', 'UNAVAILABLE', 'UNSUPPORTED', 'SOURCE_CONFLICT'})
        self.assertEqual(len(inspect.signature(d2.analyze_d2_two_period_reported_trajectory_v1).parameters), 1)
        imports = [n for n in ast.walk(ast.parse(inspect.getsource(d2))) if isinstance(n, (ast.Import, ast.ImportFrom))]
        modules = {n.module if isinstance(n, ast.ImportFrom) else n.names[0].name for n in imports}
        self.assertEqual(modules, {'dataclasses', 'decimal', 'enum', 'fractions', 'sys', 'typing',
            'src.current_annual_operating_income_to_positive_two_point_average_assets'})
