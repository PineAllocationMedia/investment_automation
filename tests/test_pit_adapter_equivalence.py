import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from pit_comparison.boundary import clean_environment
from pit_comparison.bundle import canonical, fingerprint, loads, verify_bundle
from pit_comparison.runner import snapshot_harness, isolated_python_setup
from pit_comparison.source_export import V1_SHA,V2_SHA
from tests.pit_fixtures import fixture_data,fixture_export,write_bundle


class PITAdapterEquivalenceTests(unittest.TestCase):
    def child(self,base,data,lineage,oracle=False,attack=None):
        base.mkdir()
        source=base/'source'; sha=V1_SHA if lineage=='V1' else V2_SHA
        provenance=fixture_export(None,sha,source,lineage=lineage)
        worker=base/'worker'; worker.mkdir()
        bundle=worker/'runtime'/'bundle'; expected=write_bundle(bundle,data)
        verified=verify_bundle(bundle,expected)
        harness=base/'harness'; harness_hash=snapshot_harness(harness)
        if oracle:
            shutil.copyfile(Path(__file__).with_name('pit_reference.py'),harness/'pit_reference.py')
            if attack:
                with (harness/'pit_reference.py').open('a') as output:
                    output.write("\noriginal_reference=reference\ndef reference(bundle, model):\n    try:\n        " + attack + "\n    except Exception:\n        pass\n    return original_reference(bundle, model)\n")
        request={'source_root':str(source),'worker_root':str(worker),'bundle_root':str(bundle),
            'source_provenance':provenance,'expected_bundle_hash':expected,'input_identity':verified.manifest['input_identity'],
            'harness_root':str(harness),'harness_hash':harness_hash,'forbidden_roots':[str(Path(__file__).resolve().parents[1])],
            'comparison_id':'synthetic-comparison','execution_id':'synthetic-'+lineage}
        path=worker/'request.json';path.write_bytes(canonical(request))
        setup, environment=isolated_python_setup()
        code=setup+"import sys; sys.path.insert(0,sys.argv[1]); from pit_comparison.worker import execute; from pit_comparison.bundle import loads; from pathlib import Path; "
        code += "from pit_reference import reference; " if oracle else "reference=None; "
        code += "raise SystemExit(execute(loads(Path(sys.argv[2]).read_bytes()),evaluator=reference))"
        result=subprocess.run([sys.executable,'-s','-S','-B','-c',code,environment,str(harness),str(path)],
            cwd=worker,env=clean_environment(worker),stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=90)
        output=loads((worker/'runtime'/'result.json').read_bytes()) if (worker/'runtime'/'result.json').exists() else {'error':result.stderr}
        self.assertEqual(result.returncode,2 if attack else 0,str(output))
        if attack:
            self.assertEqual(output['status'],'CONTAINMENT_FAILED')
            self.assertTrue(output['containment']['violations'])
        return output

    def test_comprehensive_original_oracle_and_v1_v2_equivalence(self):
        # Four modes x sixteen fixtures; oracle runs the original decision statements
        # from each exact selected revision in its own fresh guarded process.
        fingerprints = []
        for mode in ('balanced','rational-aggressive','family-office','high-cagr'):
            for scenario in ('mixed','liquidation','winner','tied','drawdown','missing','concentration','empty_history','proxy','regime','latest_history','same_day','validation_notes','dated_research','zero_capital','sizing_boundary'):
                with self.subTest(mode=mode,scenario=scenario), tempfile.TemporaryDirectory(prefix='pit-equivalence-') as t:
                    root=Path(t).resolve(); data=fixture_data(mode,scenario)
                    with ThreadPoolExecutor(max_workers=4) as pool:
                        futures = {(lineage, oracle): pool.submit(self.child,
                            root/(lineage+('-oracle' if oracle else '-actual')), data, lineage, oracle)
                            for lineage in ('V1','V2') for oracle in (False,True)}
                        outputs = {key: future.result() for key, future in futures.items()}
                    results=[]
                    for lineage in ('V1','V2'):
                        actual, expected = outputs[lineage, False], outputs[lineage, True]
                        self.assertEqual(actual['semantic_result'],expected['semantic_result'])
                        self.assertEqual(actual['semantic_fingerprint'],expected['semantic_fingerprint'])
                        results.append(actual['semantic_fingerprint'])
                        self.assertEqual(actual['semantic_result']['analyses']['CORE_PORTFOLIO']['MSFT']['market_data_age_hours'],1.0)
                        if scenario == 'dated_research':
                            fact = actual['semantic_result']['analyses']['CORE_PORTFOLIO']['MSFT']
                            self.assertEqual(fact['research_report_field_freshness']['fair_value']['age_days'],32)
                    self.assertEqual(results[0],results[1])
                    fingerprints.append({'mode':mode,'scenario':scenario,'fingerprint':results[0]})
                    print('PIT_EQUIVALENCE', mode, scenario, results[0], flush=True)
        print('PIT_EQUIVALENCE_CASES', len(fingerprints), 'AGGREGATE', fingerprint(fingerprints), flush=True)

    def test_worker_fails_after_caught_network_and_native_denials(self):
        for lineage, attack in (("V1", "__import__('socket').socket()"),
                                ("V2", "__import__('socket').socket()"),
                                ("V1", "__import__('requests').get('https://example.invalid')"),
                                ("V2", "__import__('src.runtime_context',fromlist=['check_analysis']).check_analysis(capital=1, run_purpose='DIAGNOSTIC')")):
            with self.subTest(lineage=lineage,attack=attack), tempfile.TemporaryDirectory() as t:
                self.child(Path(t).resolve()/"worker-test",fixture_data(),lineage,oracle=True,attack=attack)
