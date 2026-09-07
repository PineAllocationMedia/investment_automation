"""PR2 authority regressions. All records and capital are synthetic test fixtures."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src import model_identity
from src.baseline_identity import (baseline_forward_authority, baseline_observation_metadata,
    combined_baseline_snapshot_authority, load_baseline_identity)
from src.decision_manifest_engine import build_decision_manifest, write_failed_run_audit
from src.dependency_reproducibility import dependency_environment
from src.history_engine import save_current_snapshot
from src.allocation_change_engine import save_allocation_snapshot
from src.audit_snapshot_engine import _build_current_run_snapshot
from src.run_logging_engine import write_universe_snapshot, build_analysis_run_log, extend_report_run_log
from src.model_audit_engine import build_model_audit
from src.anti_overfitting_gate_engine import build_anti_overfitting_context
from src.full_audit_engine import build_full_audit_metrics
from src.validation_evidence import VALIDATION_SCHEMA_VERSION, walk_forward_period_has_strategy_validation_authority as authority
from src.walk_forward_backtest_engine import (WalkForwardInventoryConfig, build_walk_forward_inventory,
    build_walk_forward_coverage, build_walk_forward_simulation_summary, simulate_walk_forward_periods,
    _period_authority_metadata, WALK_FORWARD_PERIOD_COLUMNS)
from src.transaction_friction_engine import build_walk_forward_friction_rows, add_friction_fields_to_walk_forward_periods
from tests.identity_fixtures import production_identity, production_observation


def csv_roundtrip(row):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(row))
    writer.writeheader()
    writer.writerow(row)
    stream.seek(0)
    return next(csv.DictReader(stream))


class ValidationIdentityIsolationTest(unittest.TestCase):
    def test_native_v2_identity_does_not_depend_on_runtime_or_baseline_config(self):
        with patch.dict('os.environ', {'INVESTMENT_AUTOMATION_RUNTIME_PROFILE': 'v1',
                                      'INVESTMENT_AUTOMATION_BASELINE_STARTED_AT': '2026-01-01'}):
            identity = load_baseline_identity('/missing/irrelevant/baseline.yaml')
        self.assertEqual(model_identity.MODEL_LINEAGE, 'V2')
        self.assertEqual(identity['model_lineage'], 'V2')
        self.assertEqual(identity['validation_authority'], 'NONE')
        self.assertEqual(identity['baseline_id'], '')
        self.assertEqual(identity['baseline_status'], 'NOT_ESTABLISHED')
        metadata = baseline_observation_metadata(run_timestamp='2026-09-01', run_purpose='MANUAL_DECISION', capital=1000)
        self.assertFalse(metadata['baseline_forward_eligible'])
        self.assertFalse(metadata['strategy_validation_authority'])

    def test_baseline_identity_and_operating_condition_matrix(self):
        good = production_observation()
        self.assertTrue(baseline_forward_authority(good)['baseline_forward_eligible'])
        changes = {'model_lineage': 'V2', 'validation_authority': 'SHADOW_ONLY',
            'baseline_id': 'wrong', 'model_rules_version': 'other-rules',
            'validation_schema_version': 'old-schema', 'run_purpose': 'DIAGNOSTIC', 'capital': 0,
            'run_succeeded': False, 'critical_input_passed': False, 'approved_config_active': False,
            'dependency_status': 'DRIFT', 'git_tracked_worktree_clean': False,
            'baseline_forward_eligible': False, 'baseline_status': 'PENDING_APPROVED_DEPLOYMENT',
            'baseline_started_at': '2027-01-01', 'run_timestamp': 'invalid',
            'eligibility_basis': 'LEGACY_PARTIALLY_RECOVERABLE', 'strategy_validation_authority': False}
        for field, changed in changes.items():
            for value in (changed, None, ''):
                with self.subTest(field=field, value=value):
                    self.assertFalse(baseline_forward_authority({**good, field:value}, require_declared_eligibility=True)['baseline_forward_eligible'])
            missing = {k:v for k,v in good.items() if k != field}
            if field != 'strategy_validation_authority':
                with self.subTest(field=field, missing=True):
                    self.assertFalse(baseline_forward_authority(missing, require_declared_eligibility=True)['baseline_forward_eligible'])
        for bad_capital in (-1, float('nan'), float('inf')):
            self.assertFalse(baseline_forward_authority({**good, 'capital':bad_capital})['baseline_forward_eligible'])
        # Explicit prior denial is sticky even at the direct/default entry point.
        self.assertFalse(baseline_forward_authority({**good, 'baseline_forward_eligible':False})['baseline_forward_eligible'])
        self.assertIn('MODEL_LINEAGE_MISSING', baseline_forward_authority({**good, 'model_lineage':''})['baseline_authority_reasons'])

    def test_generic_authority_matrix_and_csv(self):
        good = production_observation()
        self.assertTrue(authority(good))
        self.assertTrue(authority(csv_roundtrip(good)))
        for field in ('model_lineage', 'model_rules_version', 'validation_authority', 'validation_schema_version',
                      'strategy_validation_authority', 'run_purpose', 'eligibility_basis', 'evidence_class'):
            for value in (None, '', False, 'unknown'):
                with self.subTest(field=field, value=value):
                    row = {**good, field:value}
                    self.assertFalse(authority(row))
                    self.assertFalse(authority(csv_roundtrip(row)))
            self.assertFalse(authority({k:v for k,v in good.items() if k != field}))
        for lineage, scope in [('V2','PRODUCTION'), ('V1','NONE'), ('V1','SHADOW_ONLY'), ('V2','NONE')]:
            self.assertFalse(authority({**good, 'model_lineage':lineage, 'validation_authority':scope}))

    def test_denial_survives_period_conversion_and_csv(self):
        for changes in ({'strategy_validation_authority':False}, {'validation_authority':'NONE'},
                        {'validation_authority':'SHADOW_ONLY'}, {'model_lineage':'V2'}):
            row = production_observation(**changes)
            for input_row in (row, csv_roundtrip(row)):
                converted = _period_authority_metadata(input_row)
                self.assertFalse(converted['strategy_validation_authority'])
                self.assertFalse(authority(csv_roundtrip(converted)))
                for key in model_identity.IDENTITY_FIELDS:
                    self.assertEqual(converted[key], input_row[key])
        row = _period_authority_metadata(production_observation(baseline_forward_eligible=False))
        self.assertFalse(row['baseline_forward_eligible'])

    def test_paired_identity_and_denial_matrix(self):
        good = production_observation()
        self.assertTrue(combined_baseline_snapshot_authority([good, good], run_purpose='MANUAL_DECISION')['baseline_forward_eligible'])
        for field in (*model_identity.IDENTITY_FIELDS, 'baseline_id', 'manifest_fingerprint', 'run_id',
                      'analysis_mode', 'run_purpose', 'baseline_started_at'):
            for value in ('different', ''):
                with self.subTest(field=field, value=value):
                    result = combined_baseline_snapshot_authority([good, {**good, field:value}], run_purpose='MANUAL_DECISION')
                    self.assertFalse(result['baseline_forward_eligible'])
                    self.assertFalse(result['strategy_validation_authority'])
        for changes in ({'strategy_validation_authority':False}, {'baseline_forward_eligible':False},
                        {'validation_authority':'NONE'}, {'validation_authority':'SHADOW_ONLY'}):
            denied = {**good, **changes}
            result = combined_baseline_snapshot_authority([good, denied], run_purpose='MANUAL_DECISION')
            self.assertFalse(result['baseline_forward_eligible'])
            if 'baseline_forward_eligible' not in changes:
                self.assertFalse(result['strategy_validation_authority'])

    @staticmethod
    def write_pair(reports, day, lineage='V1', *, clock='12', **changes):
        common = production_observation(model_lineage=lineage, analysis_date=day,
            created_at=f'{day}T{clock}:00:00', run_timestamp=f'{day}T{clock}:00:00',
            run_id=f'{lineage}-{day}-{clock}', manifest_fingerprint=f'{lineage}-{day}-{clock}', **changes)
        if lineage == 'V2':
            common.update(validation_authority='NONE', baseline_id='', baseline_status='NOT_ESTABLISHED',
                          baseline_forward_eligible=False, strategy_validation_authority=False)
        history = reports / 'history'
        history.mkdir(exist_ok=True)
        for kind in ('analysis', 'allocation'):
            content = {'analyses':[{'ticker':'MSFT','universe':'CORE_PORTFOLIO','score_total':9}]} if kind=='analysis' else {'allocations':[{'ticker':'MSFT','amount':1000,'percentage':1}]}
            (history / f'{kind}_{lineage}_{day}_{clock}.json').write_text(json.dumps({**common, **content}))

    def test_partition_before_dedup_pairing_and_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder)
            for day in ('2026-06-01','2026-07-01','2026-08-01'):
                self.write_pair(reports, day)
            config=WalkForwardInventoryConfig(model_lineage='V1')
            before=build_walk_forward_inventory(reports, config)
            baseline_metrics=build_model_audit(reports, period='all', mode='high-cagr', current_model_lineage='V1')['metrics']
            # Later same-day V2 and extra V2 dates must not change V1 endpoints.
            for day in ('2026-06-01','2026-06-15','2026-07-01','2026-08-01'):
                self.write_pair(reports, day, 'V2', clock='18')
            after=build_walk_forward_inventory(reports, config)
            self.assertEqual(before, [r for r in after if r['model_lineage']=='V1'])
            v2_rows=[r for r in after if r['model_lineage']=='V2']
            self.assertEqual(len(v2_rows),4)
            self.assertTrue(all('V2' in r['run_id'] for r in v2_rows))
            metrics=build_model_audit(reports, period='all', mode='high-cagr', current_model_lineage='V1')['metrics']
            for key in ('current_version_observation_count','baseline_forward_observation_count','baseline_evidence_maturity'):
                self.assertEqual(metrics[key], baseline_metrics[key])
            v2=build_model_audit(reports, period='all', mode='high-cagr')['metrics']
            self.assertEqual(v2['current_version_total_observation_count'],4)
            self.assertEqual(v2['current_version_observation_count'],0)
            self.assertEqual(v2['baseline_forward_observation_count'],0)
            self.assertEqual(build_walk_forward_coverage(after,config)['baseline_forward_eligible_snapshots'],3)
            # Reverse the time ordering as well: later V1 records cannot displace V2.
            for day in ('2026-06-01','2026-07-01','2026-08-01'):
                self.write_pair(reports, day, 'V1', clock='23')
            reverse=build_walk_forward_inventory(reports, config)
            self.assertEqual(v2_rows, [r for r in reverse if r['model_lineage']=='V2'])

    def test_cross_lineage_records_do_not_form_a_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder)
            self.write_pair(reports,'2026-06-01')
            self.write_pair(reports,'2026-06-01','V2')
            (reports/'history'/'allocation_V1_2026-06-01_12.json').unlink()
            (reports/'history'/'analysis_V2_2026-06-01_12.json').unlink()
            rows=build_walk_forward_inventory(reports)
            self.assertEqual(len(rows),2)
            self.assertTrue(all(not r['baseline_forward_eligible'] and not r['strategy_validation_authority'] for r in rows))

    def test_legacy_read_does_not_rewrite_or_infer_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder); self.write_pair(reports,'2026-06-01'); self.write_pair(reports,'2026-07-01')
            for path in (reports/'history').glob('*.json'):
                row=json.loads(path.read_text()); row.pop('model_lineage'); row.pop('validation_authority')
                row['validation_schema_version']='2026-08-23-validation-architecture-v3'
                path.write_text(json.dumps(row))
            before={str(p):p.read_bytes() for p in (reports/'history').glob('*.json')}
            rows=build_walk_forward_inventory(reports)
            self.assertEqual(len(rows),2)
            self.assertTrue(all(not r['strategy_validation_authority'] and not r['baseline_forward_eligible'] for r in rows))
            self.assertEqual(build_model_audit(reports,period='all')['metrics']['current_version_observation_count'],0)
            self.assertEqual(before,{str(p):p.read_bytes() for p in (reports/'history').glob('*.json')})

    def test_derived_periods_keep_denial_and_persist_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder)
            for day in ('2026-06-01','2026-07-01'):
                self.write_pair(reports,day,strategy_validation_authority=False,baseline_forward_eligible=False)
            rows=build_walk_forward_inventory(reports,WalkForwardInventoryConfig(model_lineage='V1'))
            prices=pd.DataFrame({'MSFT':[100,110],'VFV.TO':[100,105]},index=pd.to_datetime(['2026-06-01','2026-07-01']))
            periods=simulate_walk_forward_periods([r for r in rows if r['usable_for_walk_forward']],prices)['period_rows']
            self.assertEqual(len(periods),1)
            self.assertFalse(authority(periods[0]))
            self.assertFalse(periods[0]['baseline_forward_eligible'])
            for field in (*model_identity.IDENTITY_FIELDS,'run_id','manifest_fingerprint','strategy_validation_authority'):
                self.assertIn(field,WALK_FORWARD_PERIOD_COLUMNS)
                self.assertIn(field,periods[0])

    def test_full_audit_and_gate_scope_lineage_and_explicit_authority(self):
        good=production_observation(evaluation_status='SIMULATED',strategy_period_return=.02,vfv_period_return=.01,excess_return_vs_vfv=.01,days_held=30)
        bad=[{**good,'model_lineage':'V2'}, {**good,'validation_authority':'SHADOW_ONLY'},
             {**good,'validation_authority':'NONE'}, {**good,'strategy_validation_authority':False}]
        for lineage, expected in [('V1',1),('V2',0)]:
            metrics={**production_identity(),'current_model_lineage':lineage,'current_model_rules_version':good['model_rules_version'],'current_version_decision_observation_count':0}
            gate=build_anti_overfitting_context(model_metrics=metrics,walk_forward_period_rows=[good,*bad])
            self.assertEqual(gate['genuine_oos_periods'],expected)
            full=build_full_audit_metrics(model_audit={'metrics':metrics},backtest_result={},backtest_error='',
                walk_forward_result={'period_rows':[good,*bad]},account_performance_rows=[],contribution_estimate={},
                selected_monthly_capital=0,period='all',years=[],mode='high-cagr')
            self.assertEqual(full['walk_forward_period_count'],expected)
            self.assertEqual(full['strategy_validation_confidence'],'INSUFFICIENT')
            summary=build_walk_forward_simulation_summary([good,*bad],{},WalkForwardInventoryConfig(model_lineage=lineage),'TEST')
            self.assertEqual(summary['genuine_oos_periods'],expected)

    def test_manifest_identity_is_canonical_and_fingerprinted(self):
        common=dict(project_root=Path.cwd(),run_id='fixture',run_timestamp='2026-09-01',run_purpose='DIAGNOSTIC',
            mode='high-cagr',capital=0,analyses_by_universe={},allocation_result={},research_inputs={},market_data={},benchmark_data={},
            git_sha='a'*40,dependency_payload={'dependency_fingerprint':'d','dependency_lock_fingerprint':'l'},
            git_state_payload={'git_tracked_worktree_clean':True,'git_tracked_diff_fingerprint':'clean'})
        first=build_decision_manifest(**common,baseline_metadata=production_observation())
        self.assertEqual(first['model_lineage'],'V2')
        self.assertEqual(first['validation_authority'],'NONE')
        self.assertEqual(first['baseline']['baseline_id'],'')
        second=build_decision_manifest(**{**common,'run_id':'later','run_timestamp':'2026-09-02'})
        self.assertEqual(first['manifest_fingerprint'],second['manifest_fingerprint'])
        for field,value in [('model_lineage','V1'),('validation_authority','SHADOW_ONLY'),('validation_schema_version','different')]:
            identity={**model_identity.current_model_identity(),field:value}
            with patch('src.baseline_identity.current_model_identity',return_value=identity):
                changed=build_decision_manifest(**common)
            self.assertNotEqual(first['manifest_fingerprint'],changed['manifest_fingerprint'])
            self.assertEqual(first['decision_output_fingerprint'],changed['decision_output_fingerprint'])

    def test_native_persistence_cannot_emit_supplied_v1_authority(self):
        forged=production_observation()
        with tempfile.TemporaryDirectory() as folder:
            reports=Path(folder)
            analyses={'MSFT':{'ticker':'MSFT','score_total':9,'universe':'CORE_PORTFOLIO'}}
            common=dict(run_purpose='MANUAL_DECISION',baseline_metadata=forged,manifest_reference='fixture.json',manifest_fingerprint='fixture',run_id='fixture')
            save_current_snapshot(reports,'high-cagr',analyses,**common)
            save_allocation_snapshot(reports,{'allocations':[{'destination':'MSFT','montant':1000}]},analysis_mode='high-cagr',**common)
            write_universe_snapshot(analyses,mode='high-cagr',model_rules_version=forged['model_rules_version'],reports_dir=reports,**common)
            payloads=[json.loads((reports/path).read_text()) for path in ('latest_analysis_snapshot.json','latest_allocation_snapshot.json','universe_snapshots/fixture.json')]
            log=build_analysis_run_log(run_id='fixture',mode='high-cagr',capital=0,refresh_market_data=False,baseline_metadata=forged)
            payloads.extend(log)
            audit=_build_current_run_snapshot(reports_dir=reports,analysis_mode='high-cagr',allocation_result={'baseline_identity':forged},anomaly_rows=[],validation_priority_rows=[],run_log_rows=log)
            payloads.append(audit['meta'])
            for row in payloads:
                self.assertEqual(row['model_lineage'],'V2')
                self.assertEqual(row['validation_authority'],'NONE')
                self.assertEqual(row['baseline_id'],'')
                self.assertFalse(row['baseline_forward_eligible'])
                self.assertFalse(row['strategy_validation_authority'])
                self.assertEqual(row['validation_schema_version'],VALIDATION_SCHEMA_VERSION)
                self.assertTrue(row['run_id'])

    def test_friction_join_cannot_mix_same_date_evidence(self):
        period=production_observation(mode='high-cagr',analysis_date='2026-06-01',next_analysis_date='2026-07-01',evaluation_status='SIMULATED',strategy_period_return=.05)
        v2={**period,'model_lineage':'V2','validation_authority':'NONE','run_id':'v2'}
        first={**period,'ticker':'MSFT','allocation_weight':1,'trade_value_cad':1000}
        other={**v2,'ticker':'AAPL','allocation_weight':1,'trade_value_cad':99999}
        single=build_walk_forward_friction_rows({},[period],[first])
        mixed=build_walk_forward_friction_rows({},[period,v2],[first,other])
        self.assertEqual(single[0],mixed[0])
        a=add_friction_fields_to_walk_forward_periods([period],single)[0]
        b=add_friction_fields_to_walk_forward_periods([period,v2],mixed)[0]
        self.assertEqual(a,b)


    def test_locked_dependencies_match(self):
        environment = dependency_environment(Path.cwd() / 'requirements.lock')
        self.assertEqual(environment['dependency_status'], 'MATCH', environment)

    def test_aggregate_legacy_counts_cannot_raise_maturity(self):
        metrics = {'current_model_rules_version': 'v-current', 'current_model_lineage': 'V1',
                   'current_version_decision_observation_count': 99, 'allocation_sample_count': 99}
        gate = build_anti_overfitting_context(model_metrics=metrics)
        self.assertEqual(gate['current_version_observations'], 0)
        self.assertEqual(gate['sample_count'], 0)
        full = build_full_audit_metrics(model_audit={'metrics': metrics}, backtest_result={}, backtest_error='',
            account_performance_rows=[], contribution_estimate={}, selected_monthly_capital=0,
            period='all', years=[], mode='high-cagr')
        self.assertEqual(full['current_version_observation_count'], 0)

    def test_rules_schema_and_scope_partition_before_selection(self):
        with tempfile.TemporaryDirectory() as folder:
            reports = Path(folder)
            for day in ('2026-06-01', '2026-07-01'):
                self.write_pair(reports, day)
            initial = build_walk_forward_inventory(reports)
            mutations = ({'model_rules_version': 'other'}, {'validation_schema_version': 'old'},
                         {'validation_authority': 'SHADOW_ONLY'}, {'validation_authority': 'NONE'})
            for index, changes in enumerate(mutations):
                self.write_pair(reports, '2026-06-01', clock=str(15 + index), **changes)
                self.write_pair(reports, '2026-06-15', clock=str(15 + index), **changes)
            after = build_walk_forward_inventory(reports)
            target = model_identity.evidence_cohort(initial[0])
            self.assertEqual(initial, [r for r in after if model_identity.evidence_cohort(r) == target])

    def test_writers_preserve_explicit_denial_even_in_v1_fixture(self):
        from src.baseline_identity import producer_baseline_metadata
        with patch('src.model_identity.MODEL_LINEAGE', 'V1'):
            for scope in ('NONE', 'SHADOW_ONLY'):
                row = producer_baseline_metadata(production_observation(validation_authority=scope))
                self.assertEqual(row['validation_authority'], scope)
                self.assertFalse(row['strategy_validation_authority'])
                self.assertFalse(row['baseline_forward_eligible'])

    def test_failed_run_audit_is_native_v2_and_non_authoritative(self):
        with tempfile.TemporaryDirectory() as folder:
            result = write_failed_run_audit(reports_dir=folder, project_root=Path.cwd(), run_id='failed-fixture',
                run_timestamp='2026-09-01', run_purpose='DIAGNOSTIC', mode='high-cagr', capital=0, input_audit={})
            self.assertEqual(result['model_lineage'], 'V2')
            self.assertEqual(result['validation_authority'], 'NONE')
            self.assertEqual(result['baseline']['baseline_id'], '')
            self.assertFalse(result['baseline']['baseline_forward_eligible'])
            self.assertFalse(result['baseline']['strategy_validation_authority'])


    def test_coverage_rechecks_authority_before_baseline_maturity(self):
        good = production_observation(primary_timeline_eligible=True, usable_for_walk_forward=True,
                                      analysis_snapshot_path='a', allocation_snapshot_path='b')
        rows = [dict(good, validation_authority='NONE') for _ in range(12)]
        coverage = build_walk_forward_coverage(rows, WalkForwardInventoryConfig(model_lineage='V1'))
        self.assertEqual(coverage['baseline_forward_usable_periods'], 0)
        self.assertEqual(coverage['baseline_evidence_maturity'], 'INSUFFICIENT')
        self.assertEqual(coverage['genuine_decision_usable_periods'], 0)
