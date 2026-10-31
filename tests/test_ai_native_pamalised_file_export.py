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

    def _manual_step(self, case, *, output):
        from io import StringIO
        from scripts.r1_manual_session_cli import main
        out, err = StringIO(), StringIO()
        code = main(["--output", output],
                    instream=StringIO(json.dumps(case)),
                    outstream=out, errstream=err)
        self.assertEqual((code, err.getvalue()), (0, ""))
        return json.loads(out.getvalue())

    def _last_pi_continuation(self, *, original_ir=True):
        """Manual CC→IR→PI without rebuilding the original request."""
        first = self._manual_step(
            {"request": self.fixture.request(portfolio_needed=True)},
            output="operator-packet")
        ir = self.fixture.ir()
        after_ir = self._manual_step(
            {"continuation_private": first["continuation_private"],
             "specialist_result": {"IR_CAPSULE": ir}},
            output="resume-operator")
        self.assertEqual(after_ir["session"]["status"],
                         "AWAITING_MANUAL_PI_DELTA")
        return {
            "continuation_private": after_ir["continuation_private"],
            "specialist_result": {
                "PI_DELTA": self.fixture.pi(),
                "FORWARD_UNCHANGED": (
                    copy.deepcopy(ir) if original_ir else
                    {"analysis_id": "FORGED", "facts": []}),
            },
        }

    def test_completed_final_pi_continuation_exports_pdf_without_case_retyping(self):
        previous = self._last_pi_continuation()
        original = copy.deepcopy(previous)
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "completed.pdf"
            status = export_private_pdf(
                case_json=json.dumps(previous), destination=destination,
                authorized=True)
            self.assertEqual(status, "PDF_CREATED_LOCALLY_NOT_DELIVERED_TO_CC_WORK")
            data = destination.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertTrue(data.rstrip().endswith(b"%%EOF"))
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertEqual(previous, original)

    def test_modified_forwarded_ir_or_incomplete_continuation_never_writes(self):
        forged = self._last_pi_continuation(original_ir=False)
        original = self._last_pi_continuation()
        pending = {
            "continuation_private": original["continuation_private"],
            "specialist_result": {"PI_DELTA": self.fixture.pi()},
        }
        wrong_kind = {
            **original,
            "extra_private_payload": "UNAUTHORIZED_DATA",
        }
        for item in (forged, pending, wrong_kind):
            with self.subTest(keys=list(item)):
                with tempfile.TemporaryDirectory() as folder:
                    destination = Path(folder) / "forbidden.pdf"
                    with self.assertRaisesRegex(
                            ValueError, "PDF_EXPORT_SOURCE_NOT_READY"):
                        export_private_pdf(
                            case_json=json.dumps(item),
                            destination=destination, authorized=True)
                    self.assertFalse(destination.exists())

    def test_last_ir_only_continuation_exports_without_retyped_ir(self):
        first = self._manual_step(
            {"request": self.fixture.request(portfolio_needed=False)},
            output="operator-packet")
        final = {
            "continuation_private": first["continuation_private"],
            "specialist_result": {"IR_CAPSULE": self.fixture.ir()},
        }
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "research.pdf"
            status = export_private_pdf(
                case_json=json.dumps(final), destination=destination,
                authorized=True)
            self.assertEqual(status, "PDF_CREATED_LOCALLY_NOT_DELIVERED_TO_CC_WORK")
            self.assertTrue(destination.read_bytes().startswith(b"%PDF-"))

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
