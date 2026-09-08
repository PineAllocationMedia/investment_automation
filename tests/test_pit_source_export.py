"""Exact source identity and allowlist fail-closed checks, without model imports."""
from pathlib import Path
import tempfile
import unittest

from pit_comparison.bundle import BundleError
from pit_comparison.source_export import V1_SHA, V2_SHA, V1_TREE, V2_TREE, verify_export, allowed_source
from tests.pit_fixtures import fixture_export


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
