"""Exact source identity and allowlist fail-closed checks, without model imports."""
import copy
from pathlib import Path
import tempfile
import unittest

from pit_comparison.bundle import BundleError, canonical, fingerprint, inventory
from pit_comparison.source_export import V1_SHA, V2_SHA, V1_TREE, V2_TREE, verify_export, allowed_source, export_revision, static_identity, write_export
from tests.pit_fixtures import fixture_export, prove_fixture_bytes, source_git_repo


class PITSourceExportTests(unittest.TestCase):
    def test_exact_pinned_source_manifests_and_mutation(self):
        for lineage, revision, tree in (("V1", V1_SHA, V1_TREE), ("V2", V2_SHA, V2_TREE)):
            with self.subTest(lineage=lineage), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary).resolve()/"source"
                expected = fixture_export(None, revision, source, lineage=lineage)
                self.assertEqual(verify_export(source, expected)["git_tree_sha"], tree)
                self.assertTrue(all(allowed_source(r["path"]) for r in expected["files"]))
                self.assertFalse(any((source/p).exists() for p in ("data", "reports", "config", ".git", "deploy")))
                (source/"src/utils.py").write_bytes(b"# source mutation\n")
                with self.assertRaises(BundleError): verify_export(source, expected)

    def test_operational_files_are_not_source(self):
        for path in ("data/portfolio.csv", "reports/history/snapshot.json", "config/positions.yaml", ".git/config", "deploy/service.py", "src/nested/state.py", "credentials.json"):
            self.assertFalse(allowed_source(path))

    def test_fixture_exports_equal_real_git_exports(self):
        for lineage, revision in (("V1", V1_SHA), ("V2", V2_SHA)):
            with self.subTest(lineage=lineage), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                actual = export_revision(source_git_repo(), revision, root/"git", lineage=lineage)
                fixture = fixture_export(None, revision, root/"fixture", lineage=lineage)
                self.assertEqual(actual, fixture)
                self.assertEqual(inventory(root/"git"), inventory(root/"fixture"))
                print("PIT_SOURCE_GIT_PROOF", lineage, revision, actual["git_tree_sha"], actual["source_export_hash"], flush=True)

    def test_self_consistent_fixture_rewrite_cannot_forge_git_proof(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary).resolve()/"source"
            fixture_export(None, V2_SHA, source, lineage="V2")
            blobs = inventory(source)
            blobs.pop("source_manifest.json")
            blobs["src/model_version.py"] += b"# Internally consistent, but not the pinned Git blob.\n"
            with self.assertRaisesRegex(ValueError, "pinned Git objects"):
                prove_fixture_bytes(blobs, V2_SHA, V2_TREE, lineage="V2")
            with self.assertRaisesRegex(ValueError, "exact pinned"):
                prove_fixture_bytes(blobs, "0"*40, V2_TREE, lineage="V2")

    def test_rules_identity_requires_one_supported_static_string(self):
        for expression in ('""', 'None', '123', '" invalid "', '"x" * 2', '__import__("os").getenv("RULES")'):
            with self.subTest(expression=expression), self.assertRaises(BundleError):
                static_identity("MODEL_RULES_VERSION = " + expression, "MODEL_RULES_VERSION")
        for source in ('MODEL_RULES_VERSION="v7"\nMODEL_RULES_VERSION="v8"', 'if True:\n MODEL_RULES_VERSION="v8"'):
            with self.assertRaises(BundleError): static_identity(source, "MODEL_RULES_VERSION")
        self.assertEqual(static_identity('MODEL_RULES_VERSION: str = "synthetic-v8"', "MODEL_RULES_VERSION"), "synthetic-v8")

    def test_v1_rules_cannot_change_and_v2_manifest_cannot_override_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for lineage, revision, tree in (("V1", V1_SHA, V1_TREE), ("V2", V2_SHA, V2_TREE)):
                source = root/lineage
                manifest = fixture_export(None, revision, source, lineage=lineage)
                if lineage == "V1":
                    blobs = inventory(source); blobs.pop("source_manifest.json")
                    blobs["src/model_version.py"] = b'MODEL_RULES_VERSION = "synthetic-v8"\n'
                    with self.assertRaisesRegex(BundleError, "Preserved V1"):
                        write_export(root/"bad-v1", revision, tree, lineage, blobs)
                else:
                    forged = copy.deepcopy(manifest)
                    forged["model_rules_version"] = "synthetic-v8"
                    forged["source_export_hash"] = fingerprint({k:v for k,v in forged.items() if k != "source_export_hash"})
                    (source/"source_manifest.json").write_bytes(canonical(forged))
                    with self.assertRaisesRegex(BundleError, "Source-derived"):
                        verify_export(source, forged)
