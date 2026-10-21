"""Offline contract checks for the exact M1 Git-blob runtime materializer."""
import base64
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m1_runtime_bootstrap as bootstrap


class RuntimeBootstrapTests(unittest.TestCase):
    def test_github_blob_decodes_exact_bytes(self):
        raw = b"geometry-fixture-utf8\n" * 100
        expected = bootstrap.blob_sha(raw)
        payload = {"encoding": "base64", "content": base64.b64encode(raw).decode()}
        with patch.object(bootstrap, "api_get", return_value=payload):
            self.assertEqual(bootstrap.read_blob("test-token", expected), raw)

    def test_mismatched_github_blob_is_rejected(self):
        raw = b"tampered"
        payload = {"encoding": "base64", "content": base64.b64encode(raw).decode()}
        with patch.object(bootstrap, "api_get", return_value=payload):
            with self.assertRaisesRegex(ValueError, "SHA verification failed"):
                bootstrap.read_blob("test-token", "0" * 40)

    def test_all_files_pinned_to_one_commit_and_geometry_sha(self):
        commit = "a" * 40
        raw = b"fixture"
        sha = bootstrap.blob_sha(raw)
        paths = set(bootstrap.FILES)
        seen = []
        def api(path, token):
            seen.append(path)
            if path.startswith("commits/"):
                return {"sha": commit}
            if path.startswith("contents/"):
                self.assertEqual(path.split("?ref=")[-1], commit)
                return {"type": "file", "sha": sha}
            if path == "git/blobs/" + sha:
                return {"encoding": "base64", "content": base64.b64encode(raw).decode()}
            raise AssertionError(path)
        with patch.object(bootstrap, "GEO_BLOB", sha), patch.object(
                bootstrap, "api_get", side_effect=api):
            files, chosen = bootstrap.read_from_github("fake-token", bootstrap.REF)
        self.assertEqual(chosen, commit)
        self.assertEqual(set(files), paths)
        self.assertEqual(files[bootstrap.GEO][0], raw)
        self.assertEqual(len([s for s in seen if s.startswith("contents/")]), len(paths))

    def test_wrong_geometry_version_is_rejected_before_download(self):
        commit = "b" * 40
        def api(path, _token):
            if path.startswith("commits/"):
                return {"sha": commit}
            return {"type": "file", "sha": "f" * 40}
        with patch.object(bootstrap, "api_get", side_effect=api):
            with self.assertRaisesRegex(ValueError, "geography SHA drift"):
                bootstrap.read_from_github("fake-token", bootstrap.REF)


if __name__ == "__main__":
    unittest.main()
