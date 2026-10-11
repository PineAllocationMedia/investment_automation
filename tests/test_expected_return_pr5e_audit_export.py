"""Synthetic native fixtures prove export mechanics, not real-source admission."""
from dataclasses import replace
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from src import expected_return_pr5e_adapter as native
from src import expected_return_pr5d_bundle as upstream
from src import expected_return_pr5e_audit_export as audit
from tests.test_expected_return_pr5e_adapter import PR5EFixtureMixin


class AuditExportTests(PR5EFixtureMixin, unittest.TestCase):
    def export(self, result=None):
        raw = audit.export_pr5e_audit(self.call() if result is None else result)
        return raw, hashlib.sha256(raw).hexdigest()

    def altered(self, raw, change):
        value = json.loads(raw)
        change(value)
        value["manifest"]["payload_sha256"] = audit._digest(audit._canonical(value["payload"]))
        return audit._canonical(value)

    def rejects(self, raw, digest=None):
        with self.assertRaises(audit.AuditExportError):
            audit.verify_pr5e_audit(raw, audit._digest(raw) if digest is None else digest)

    def test_native_admitted_deterministic_projection_and_no_mutation(self):
        result = self.call()
        before = copy.deepcopy(result)
        fixture = self.built["fixture"]
        source_roots = [Path(archive.root) for archive in (
            fixture.current_archive, fixture.submissions_archive, fixture.filing_archive,
            fixture.sec_archive, fixture.nasdaq_archive, self.builder.quote_archive,
            self.builder.split_archive)]
        def snapshot():
            return {str(p): p.read_bytes() for root in source_roots
                    for p in root.rglob("*") if p.is_file()}
        source_before = snapshot()
        first, digest = self.export(result)
        self.assertEqual(first, self.export(result)[0])
        self.assertEqual(audit.verify_pr5e_audit(first, digest), digest)
        p = json.loads(first)["payload"]
        for name in ("pr5d2_semantic_id", "pr5d2_evidence_id", "admission_semantic_id",
                     "admission_evidence_id", "admitted_share_basis_identity", "analytical_as_of"):
            self.assertEqual(p[name], getattr(result, name))
        self.assertTrue(p["evidence_references"])
        self.assertEqual(before, result)
        self.assertEqual(source_before, snapshot())
        self.assertNotIn("construction", p)
        self.assertNotIn("qualified_facts", p)
        self.assertEqual(json.loads(first)["manifest"]["boundaries"], list(audit.BOUNDARIES))

    def test_independent_process_export_and_stdlib_only_verification(self):
        code = """from tests.test_expected_return_pr5e_audit_export import AuditExportTests
import hashlib
AuditExportTests.setUpClass()
try:
    raw = AuditExportTests('runTest').export()[0]
    print(hashlib.sha256(raw).hexdigest())
finally:
    AuditExportTests.tearDownClass()
"""
        raw, digest = self.export()
        for seed in ("7", "101"):
            import os
            run = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONHASHSEED": seed},
                                 check=True, capture_output=True, text=True)
            self.assertEqual(run.stdout.strip(), digest)
        with tempfile.TemporaryDirectory() as directory:
            module = Path(directory) / "verifier.py"
            module.write_bytes(Path(audit.__file__).read_bytes())
            artifact = Path(directory) / "artifact.json"
            artifact.write_bytes(raw)
            run = subprocess.run([sys.executable, "-I", "-c",
                "import runpy,sys,socket; socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network')); "
                "m=runpy.run_path(sys.argv[1]); print(m['verify_pr5e_audit'](open(sys.argv[2],'rb').read(),sys.argv[3]))",
                str(module), str(artifact), digest], check=True, capture_output=True, text=True)
            self.assertEqual(run.stdout.strip(), digest)

    def test_native_nonavailable_states_and_evidence_separation(self):
        for state in (upstream.PR5D2BundleStatus.PR5D_ROOTS_UNAVAILABLE,
                      upstream.PR5D2BundleStatus.PR5D_ROOTS_UNSUPPORTED,
                      upstream.PR5D2BundleStatus.SOURCE_CONFLICT):
            roots = replace(self.built["result"], status=state)
            with patch.object(native, "assemble_expected_return_pr5d_bundle", return_value=roots):
                result = self.call(self.request_for(roots))
            raw, digest = self.export(result)
            self.assertEqual(audit.verify_pr5e_audit(raw, digest), digest)
            p = json.loads(raw)["payload"]
            self.assertEqual(p["status"], result.status.value)
            self.assertIsNone(p["analytical_as_of"])
            changed = replace(roots, upstream_evidence_ids=("a" * 64, *roots.upstream_evidence_ids[1:]))
            with patch.object(native, "assemble_expected_return_pr5d_bundle", return_value=changed):
                variant = self.call(self.request_for(changed))
            self.assertEqual(result.admission_semantic_id, variant.admission_semantic_id)
            self.assertNotEqual(result.admission_evidence_id, variant.admission_evidence_id)
            other, other_digest = self.export(variant)
            self.assertNotEqual(digest, other_digest)
            self.rejects(other, digest)  # internally valid wholesale substitution

    def test_payload_manifest_tampering_missing_and_external_anchor(self):
        raw, digest = self.export()
        value = json.loads(raw)
        value["payload"]["admission_evidence_id"] = "b" * 64
        self.rejects(audit._canonical(value))
        for invalid_hash in ("", "A" * 64, "0" * 63, None):
            value = json.loads(raw)
            value["manifest"]["payload_sha256"] = invalid_hash
            self.rejects(audit._canonical(value))
        mutations = [
            lambda a: a.pop("payload"),
            lambda a: a["manifest"].update(schema_version="future"),
            lambda a: a["manifest"].update(coverage="FULL_RESULT"),
            lambda a: a["manifest"].update(boundaries=[]),
            lambda a: a["payload"].pop("limitations"),
            lambda a: a["payload"].update(contract_version="future"),
            lambda a: a["payload"].update(adapter_version="future"),
            lambda a: a["payload"]["upstream"].update(contract_version="future"),
            lambda a: a["payload"]["upstream"].update(assembler_version="future"),
            lambda a: a["payload"].update(pr5d2_semantic_id="c" * 64),
            lambda a: a["payload"].update(admission_evidence_id="INVALID"),
            lambda a: a["payload"].update(status=True),
            lambda a: a["payload"].update(reasons=["UNKNOWN"]),
            lambda a: a["payload"].update(status="UNSUPPORTED", reasons=["PR5D2_SOURCE_CONFLICT"]),
            lambda a: a["payload"].update(analytical_as_of="invalid"),
            lambda a: a["payload"].update(admitted_share_basis_identity=None),
            lambda a: a["payload"].update(evidence_references=[{"path": "bad", "value": "x"}]),
            lambda a: a["payload"]["evidence_references"].append(a["payload"]["evidence_references"][0]),
            lambda a: a["payload"].update(extra="field"),
        ]
        for change in mutations:
            a = json.loads(raw)
            change(a)
            if "payload" in a:
                a["manifest"]["payload_sha256"] = audit._digest(audit._canonical(a["payload"]))
            self.rejects(audit._canonical(a))
        self.rejects(raw, "0" * 64)
        for invalid in (None, "", "A" * 64, 3):
            self.rejects(raw, invalid if invalid is not None else "")

    def test_malformed_json_duplicate_keys_and_unsupported_values(self):
        raw, digest = self.export()
        for bad in (b"", b"null\n", b"[]\n", b"{}\n", b"{", b"\xff",
                    b'{"a":1,"a":2}\n', b'{"a":NaN}\n', b'{"a":1e999}\n',
                    b'{"a":1}\n', raw + b" ", raw.replace(b'"status":', b'"status":null,"status":', 1),
                    b"[" * 1500 + b"]" * 1500, b" " * (audit.MAX_BYTES + 1)):
            self.rejects(bad, digest)
        for value in (True, {}, [], 1, 1.5):
            bad = self.altered(raw, lambda a: a["payload"].update(admission_semantic_id=value))
            self.rejects(bad)

    def test_exact_native_input_and_inconsistent_native_rejected(self):
        result = self.call()
        for invalid in (None, {}, replace(result, admission_evidence_id="0" * 64),
                        replace(result, contract_version="future"), replace(result, status="UNAVAILABLE")):
            with self.assertRaises(audit.AuditExportError):
                audit.export_pr5e_audit(invalid)

    def test_export_and_verify_without_network(self):
        with patch("socket.socket", side_effect=AssertionError("No network")), \
             patch("socket.getaddrinfo", side_effect=AssertionError("No network")):
            raw, digest = self.export()
            self.assertEqual(audit.verify_pr5e_audit(raw, digest), digest)
