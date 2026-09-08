import copy
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pit_comparison.bundle import BundleError, loads, canonical
from pit_comparison.runner import ComparisonError, run_comparison, verify_pair, validate_result
from tests.pit_fixtures import fixture_data, fixture_export, write_bundle


class PITComparisonTests(unittest.TestCase):
    def run_fixture(self, root, *, data=None, order=("V1", "V2"), seed="0", bundle=None, expected=None):
        if bundle is None:
            bundle=Path(root)/"bundle"; expected=write_bundle(bundle,data)
        return run_comparison(repo=Path(__file__).resolve().parents[1], bundle_root=bundle,
            expected_bundle_hash=expected,store=Path(root)/"comparison_store",source_preparer=fixture_export,
            execution_order=order, hash_seed=seed)

    def test_pair_authority_provenance_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve(); bundle=root/"bundle"; expected=write_bundle(bundle)
            first=self.run_fixture(root,bundle=bundle,expected=expected)
            for file in bundle.rglob("*.json"):
                os.utime(file, (1, 1))  # timestamps are not input semantics
            second=self.run_fixture(root,bundle=bundle,expected=expected,order=("V2","V1"),seed="71")
            a,b=verify_pair(first),verify_pair(second)
            self.assertNotEqual(a["comparison_id"],b["comparison_id"])
            self.assertEqual(a["comparison_spec_hash"],b["comparison_spec_hash"])
            fingerprints=[]
            probes=[]
            processes=[]
            for manifest,path in ((a,first),(b,second)):
                self.assertEqual(manifest["validation_authority"],"NONE")
                self.assertEqual(manifest["containment_level"],"APPLICATION_GUARDED")
                self.assertNotEqual(manifest["executions"]["V1"]["execution_id"],manifest["executions"]["V2"]["execution_id"])
                for link in manifest["executions"].values():
                    result=loads((path/link["path"]).read_bytes())
                    self.assertEqual(result["validation_authority"],"NONE")
                    self.assertFalse(result["strategy_validation_authority"])
                    self.assertFalse(result["baseline_forward_eligible"])
                    self.assertFalse(result["genuine_forward_evidence"])
                    fingerprints.append(result["semantic_fingerprint"])
                    probes.append(result["runtime_diagnostics"]["hash_seed_probe"])
                    processes.append(result["runtime_diagnostics"]["process_id"])
                    request = {"comparison_id": manifest["comparison_id"], "execution_id": link["execution_id"],
                        "expected_bundle_hash": manifest["bundle_hash"], "input_identity": manifest["input_identity"],
                        "source_provenance": manifest["specification"]["models"][result["model_provenance"]["model_lineage"]],
                        "harness_hash": manifest["specification"]["harness_hash"],
                        "decision_context": manifest["specification"]["decision_context"]}
                    for key, value in (("validation_authority", "PRODUCTION"), ("bundle_hash", "0"*64),
                                       ("execution_id", "wrong"), ("effective_pit_at", "future"), ("semantic_fingerprint", "0"*64)):
                        tampered = copy.deepcopy(result); tampered[key] = value
                        with self.assertRaises(ComparisonError): validate_result(tampered, request)
            self.assertEqual(len(set(fingerprints)),1, fingerprints)
            self.assertEqual(len(set(processes)),4)
            self.assertEqual(probes[0], probes[1])
            self.assertEqual(probes[2], probes[3])
            self.assertNotEqual(probes[0], probes[2])
            self.assertFalse((root/"reports").exists())
            def reordered(value):
                if isinstance(value, dict): return {k: reordered(v) for k,v in reversed(list(value.items()))}
                if isinstance(value, list): return [reordered(v) for v in value]
                return value
            alternate = root/"alternate_bundle"
            alternate_hash = write_bundle(alternate, reordered(fixture_data()), pretty=True)
            self.assertNotEqual(alternate_hash, expected)  # different exact bytes
            third = self.run_fixture(root,bundle=alternate,expected=alternate_hash)
            for link in verify_pair(third)["executions"].values():
                self.assertEqual(link["semantic_fingerprint"], fingerprints[0])
            print("PIT_DETERMINISM_FINGERPRINT", fingerprints[0], flush=True)
            target=first/a["executions"]["V1"]["path"]
            target.write_bytes(target.read_bytes()+b" ")
            with self.assertRaises(ComparisonError): verify_pair(first)

    def test_missing_market_fx_discovery_fails_without_pair(self):
        for family in ("market", "fx", "universe"):
            with self.subTest(family=family), tempfile.TemporaryDirectory() as t:
                d=fixture_data()
                if family=="market": d[family].pop("MSFT")
                elif family=="fx": d[family].pop("USD")
                else: d[family].pop("discovery_rows")
                with self.assertRaises((ComparisonError,BundleError)):
                    self.run_fixture(Path(t).resolve(),data=d)
                self.assertFalse((Path(t).resolve()/"comparison_store/comparisons").exists())

    def test_second_worker_failure_never_publishes_first_result(self):
        import subprocess
        original = subprocess.run
        calls = []
        def fail_second(command, **kwargs):
            if "-c" in command:
                calls.append(command)
                if len(calls) == 2:
                    request = loads(Path(command[-1]).read_bytes())
                    Path(kwargs["cwd"], "runtime/result.json").write_bytes(canonical({"status": "FAILED", "error": "synthetic second-worker failure"}))
                    return subprocess.CompletedProcess(command, 2, b"", b"")
            return original(command, **kwargs)
        with tempfile.TemporaryDirectory() as t, patch("pit_comparison.runner.subprocess.run", side_effect=fail_second):
            root = Path(t).resolve()
            with self.assertRaises(ComparisonError): self.run_fixture(root)
            self.assertEqual(len(calls), 2)
            self.assertFalse((root/"comparison_store/comparisons").exists())
            self.assertEqual(len(list((root/"comparison_store/failures").glob("*/failure.json"))), 1)
            self.assertFalse(list((root/"comparison_store").glob(".staging-*")))
