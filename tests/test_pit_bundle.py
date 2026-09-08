import copy
import os
from pathlib import Path
import tempfile
import unittest

from pit_comparison.bundle import BundleError, canonical, loads, verify_bundle
from tests.pit_fixtures import fixture_data, write_bundle


class PITBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pit-bundle-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "bundle"
        self.expected = write_bundle(self.root)

    def test_complete_and_explicit_absence(self):
        b = verify_bundle(self.root, self.expected, require_complete=True)
        self.assertIn("regime_market", b.manifest["explicit_absences"])
        self.assertEqual(b.get("regime_market"), {})
        with self.assertRaises(BundleError):
            b.get("not-declared")

    def test_byte_manifest_and_expected_digest_mutation(self):
        with self.assertRaises(BundleError):
            verify_bundle(self.root, "0" * 64)
        p = self.root / "inputs/market.json"
        p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaises(BundleError):
            verify_bundle(self.root, self.expected)
        m = self.root / "bundle_manifest.json"
        m.write_bytes(m.read_bytes() + b" ")
        with self.assertRaises(BundleError):
            verify_bundle(self.root, self.expected)

    def test_symlink_hardlink_extra_missing_special(self):
        for kind in ("symlink", "hardlink", "extra", "missing", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as t:
                root = Path(t).resolve() / "bundle"
                expected = write_bundle(root)
                p = root / "inputs/portfolio.json"
                if kind == "symlink":
                    p.unlink(); p.symlink_to(root / "inputs/transactions.json")
                elif kind == "hardlink":
                    os.link(p, root / "linked")
                elif kind == "extra":
                    (root / "extra").write_text("unexpected")
                elif kind == "missing":
                    p.unlink()
                else:
                    os.mkfifo(root / "fifo")
                with self.assertRaises(BundleError):
                    verify_bundle(root, expected)

    def test_duplicate_keys_nonfinite_and_embedded_paths(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(BundleError):
                loads(raw)
        for path in ("/production/portfolio.csv", "../portfolio.csv", "C:\\private\\portfolio.csv"):
            d = fixture_data(); d["manual_inputs"]["MSFT"]["notes"] = path
            self.assert_invalid_data(d)

    def assert_invalid_data(self, data, *, quality="COMPLETE_PIT", complete=False):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve() / "bundle"
            expected = write_bundle(root, data, quality=quality)
            with self.assertRaises(BundleError):
                verify_bundle(root, expected, require_complete=complete)

    def test_chronology_quality_authority_and_missing_state(self):
        mutations = [lambda d: d["provenance"]["market"].update(published_at="2026-01-01T00:00:00+00:00"),
            lambda d: d["provenance"]["market"].update(available_at="2026-01-01T00:00:00+00:00"),
            lambda d: d["provenance"]["market"].pop("availability_evidence"),
            lambda d: d["prior_state"].update(status="MISSING"),
            lambda d: d["market"]["MSFT"].pop("forward_eps"),
            lambda d: d["market"]["MSFT"].update(validation_authority="PRODUCTION"),
            lambda d: d["market"]["MSFT"].update(score_total=10),
            lambda d: d["research_facts"]["MSFT"].update(research_report_dates=["2026-01-01"]),
            lambda d: d["market"]["MSFT"].update(sec_edgar_latest_filing_date="2026-01-01"),
            lambda d: d["market"]["MSFT"].update(news_context_published_at=["2026-01-01T00:00:00+00:00"])]
        for mutate in mutations:
            d = fixture_data(); mutate(d); self.assert_invalid_data(d)
        self.assert_invalid_data(fixture_data(), quality="CONTAMINATED_UNUSABLE")
        self.assert_invalid_data(fixture_data(), quality="PARTIAL_PIT", complete=True)
        with tempfile.TemporaryDirectory() as t:
            root = Path(t).resolve()/"bundle"; d=fixture_data()
            d["provenance"]["market"]["captured_at"] = "2026-01-01T00:00:00+00:00"
            expected=write_bundle(root,d)
            self.assertEqual(verify_bundle(root,expected).manifest["pit_quality"],"COMPLETE_PIT")

    def test_rehashed_invalid_manifests(self):
        from pit_comparison.bundle import fingerprint
        for mutation in (lambda m: m["files"].append(copy.deepcopy(m["files"][0])),
                         lambda m: m["files"][0].update(path="inputs/../context.json"),
                         lambda m: m.update(explicit_absences=[])):
            m=loads((self.root/"bundle_manifest.json").read_bytes()); mutation(m)
            m.pop("bundle_hash"); m.pop("bundle_id")
            expected=fingerprint(m); m.update(bundle_hash=expected,bundle_id="sha256:"+expected)
            (self.root/"bundle_manifest.json").write_bytes(canonical(m))
            with self.assertRaises(BundleError): verify_bundle(self.root,expected)
