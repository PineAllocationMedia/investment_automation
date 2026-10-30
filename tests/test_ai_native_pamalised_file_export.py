"""Isolated synthetic-only P4 local PDF file-delivery checks, no real accounts."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from scripts.pamalised_private_file_export import export_private_pdf
from tests.test_ai_native_session_bridge import SessionBridgeTests

_HAS_REPORTLAB = importlib.util.find_spec("reportlab") is not None


@unittest.skipUnless(_HAS_REPORTLAB, "ReportLab optional PDF dependency unavailable")
class PamalisedFileExportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = SessionBridgeTests()

    def payload(self):
        request = self.fixture.request(portfolio_needed=True)
        ir = self.fixture.ir()
        ir["facts"][0]["claim"] = "SYNTHETIC_ONLY_P4_EVIDENCE_MARKER"
        pi = self.fixture.pi(forwarded_ir=copy.deepcopy(ir))
        return {"request": request, "ir_capsule": ir, "pi_delta": pi}

    def test_completed_original_ir_pi_creates_one_private_pdf(self):
        payload = self.payload()
        before = copy.deepcopy(payload)
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "PAM_synthetic.pdf"
            status = export_private_pdf(
                case_json=json.dumps(payload), destination=target,
                authorized=True)
            self.assertEqual(status, "PDF_CREATED_LOCALLY_NOT_DELIVERED_TO_CC_WORK")
            data = target.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertTrue(data.rstrip().endswith(b"%%EOF"))
            self.assertEqual(stat.S_IMODE(os.stat(target).st_mode), 0o600)
            self.assertEqual(list(Path(temp).iterdir()), [target])
            self.assertEqual(payload, before)
            # The report is local and complete, but this does not mean that
            # an actual ChatGPT Project or Work session received it.
            self.assertGreater(len(data), 512)

    def test_pending_or_tampered_handoff_never_creates_a_pdf(self):
        payload = self.payload()
        candidates = [
            {"request": payload["request"]},
            {**payload, "pi_delta": {**payload["pi_delta"],
                                    "forwarded_ir": {"wrong": True}}},
        ]
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "case.pdf"
            for candidate in candidates:
                with self.subTest(candidate=bool(candidate.get("pi_delta"))):
                    with self.assertRaisesRegex(ValueError, "PDF_EXPORT_SOURCE_NOT_READY"):
                        export_private_pdf(case_json=json.dumps(candidate),
                                           destination=target, authorized=True)
                    self.assertFalse(target.exists())

    def test_never_overwrite_existing_private_report(self):
        payload = self.payload()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "already.pdf"
            target.write_bytes(b"EXISTING_PRIVATE_REPORT")
            with self.assertRaisesRegex(ValueError, "PDF_EXPORT_PRIVATE_DESTINATION_UNAVAILABLE"):
                export_private_pdf(case_json=json.dumps(payload),
                                   destination=target, authorized=True)
            self.assertEqual(target.read_bytes(), b"EXISTING_PRIVATE_REPORT")

    def test_explicit_authorization_required_before_rendering(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "out.pdf"
            with self.assertRaisesRegex(ValueError, "EXPLICIT_AUTHORIZATION"):
                export_private_pdf(case_json="{}", destination=target,
                                   authorized=False)
            self.assertFalse(target.exists())

    def test_bad_destination_or_invalid_case_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "not-a-pdf.txt"
            with self.assertRaisesRegex(ValueError, "DESTINATION_MUST_BE_PDF"):
                export_private_pdf(case_json=json.dumps(self.payload()),
                                   destination=target, authorized=True)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
