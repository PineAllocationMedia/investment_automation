import copy
import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pit_comparison.bundle import BundleError, loads, canonical
from pit_comparison.runner import ComparisonError, run_comparison, verify_pair, validate_result
from tests.pit_fixtures import fixture_data, fixture_export, write_bundle
from pit_comparison.source_export import V1_SHA, V2_SHA, V1_RULES, export_revision, git
from pit_comparison.boundary import clean_environment


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
                    lineage = result["model_provenance"]["model_lineage"]
                    self.assertEqual(result["model_provenance"]["model_rules_version"], V1_RULES)
                    expected_schema = {"V1": "2026-08-23-validation-architecture-v3", "V2": "2026-09-06-validation-identity-v4"}[lineage]
                    self.assertEqual(result["model_provenance"]["validation_schema_version"], expected_schema)
                    self.assertEqual(manifest["specification"]["models"][lineage]["validation_schema_version"], expected_schema)
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

    def test_distinct_v2_rules_from_exact_synthetic_commit_publish_with_fixed_v1(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            repo = root/"synthetic-source"
            original = fixture_export(None, V2_SHA, repo, lineage="V2")
            (repo/"source_manifest.json").unlink()
            new_rules = "2099-01-01-synthetic-v2-rules-v8"
            (repo/"src/model_version.py").write_text(f'MODEL_RULES_VERSION = "{new_rules}"\n')
            env = clean_environment(root/"git-env")
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="PIT synthetic source", GIT_AUTHOR_EMAIL="pit@example.invalid",
                       GIT_COMMITTER_NAME="PIT synthetic source", GIT_COMMITTER_EMAIL="pit@example.invalid")
            for command in (("init", "-q"), ("add", "."), ("commit", "-qm", "Synthetic rules identity only")):
                subprocess.run(["git", "-C", str(repo), *command], env=env, check=True, capture_output=True)
            revision = git(repo, "rev-parse", "HEAD").decode().strip()
            def prepare(selected_repo, selected_revision, destination, *, lineage):
                if lineage == "V1":
                    return fixture_export(None, selected_revision, destination, lineage=lineage)
                return export_revision(selected_repo, selected_revision, destination, lineage=lineage)
            bundle = root/"bundle"
            expected = write_bundle(bundle, fixture_data(scenario="empty_history"))
            pair = run_comparison(repo=repo, bundle_root=bundle, expected_bundle_hash=expected,
                store=root/"comparison_store", v2_revision=revision, source_preparer=prepare)
            manifest = verify_pair(pair)
            models = manifest["specification"]["models"]
            self.assertEqual(models["V1"]["git_commit_sha"], V1_SHA)
            self.assertEqual(models["V1"]["model_rules_version"], V1_RULES)
            self.assertEqual(models["V2"]["git_commit_sha"], revision)
            self.assertEqual(models["V2"]["model_rules_version"], new_rules)
            original_main = next(r for r in original["files"] if r["path"] == "main.py")
            self.assertEqual(next(r for r in models["V2"]["files"] if r["path"] == "main.py"), original_main)
            self.assertEqual(manifest["validation_authority"], "NONE")
            for lineage, link in manifest["executions"].items():
                result = loads((pair/link["path"]).read_bytes())
                self.assertEqual(result["model_provenance"]["model_rules_version"], models[lineage]["model_rules_version"])
                self.assertEqual(result["validation_authority"], "NONE")
                self.assertFalse(result["strategy_validation_authority"])
                request = {"comparison_id": manifest["comparison_id"], "execution_id": link["execution_id"],
                    "expected_bundle_hash": expected, "input_identity": manifest["input_identity"],
                    "source_provenance": models[lineage], "harness_hash": manifest["specification"]["harness_hash"]}
                result["model_provenance"]["model_rules_version"] = "forged-user-override"
                with self.assertRaises(ComparisonError): validate_result(result, request)
            print("PIT_DISTINCT_RULES", V1_RULES, new_rules, "AUTHORITY NONE", flush=True)
