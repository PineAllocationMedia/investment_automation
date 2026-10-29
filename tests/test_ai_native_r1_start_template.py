"""Synthetic-only checks for a human-started, inert R1 case template.

Never uses real portfolio details, disk, browser, credentials, or network.
"""
from __future__ import annotations

from io import StringIO
import json
import unittest

from scripts.r1_manual_session_cli import main


class _NoRead(StringIO):
    def read(self, *args, **kwargs):
        raise AssertionError("Template must not consume stdin")


class InertRequestTemplateTests(unittest.TestCase):
    def _invoke(self, *, output, input_text=""):
        stdout, stderr = StringIO(), StringIO()
        code = main(["--output", output], instream=StringIO(input_text),
                    outstream=stdout, errstream=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_request_template_needs_no_input_and_never_asserts_ceo_authority(self):
        out, err = StringIO(), StringIO()
        code = main(["--output", "request-template"], instream=_NoRead(),
                    outstream=out, errstream=err)
        self.assertEqual((code, err.getvalue()), (0, ""))
        root = json.loads(out.getvalue())
        self.assertEqual(set(root), {"request"})
        request = root["request"]
        self.assertIs(request["ceo_initiated"], False)
        self.assertIsNone(request["research_needed"])
        self.assertIsNone(request["portfolio_needed"])
        for field in ("analysis_id", "as_of", "kind", "objective", "strategy_id"):
            self.assertEqual(request[field], "")
        self.assertEqual(request["account_context"]["commission"], "UNKNOWN")
        self.assertEqual(request["account_context"]["fx_cost"], "UNKNOWN")
        self.assertNotIn("ir_capsule", root)
        self.assertNotIn("pi_delta", root)
        self.assertNotIn("work_blossom_inputs", root)

    def test_unedited_template_is_rejected_by_existing_session_gate(self):
        body = self._invoke(output="request-template")[1]
        code, stdout, stderr = self._invoke(output="status", input_text=body)
        self.assertEqual((code, stdout), (2, ""))
        self.assertIn("CEO_INITIATION_REQUIRED", stderr)

    def test_completed_ceo_requested_research_uses_real_manual_ir_route(self):
        payload = json.loads(self._invoke(output="request-template")[1])
        payload["request"].update({
            "ceo_initiated": True,
            "research_needed": True,
            "portfolio_needed": False,
            "analysis_id": "SYN-NEW-01",
            "as_of": "2026-10-29",
            "kind": "DECISION",
            "objective": "Synthetic on-demand research",
            "strategy_id": "EXPLORATORY",
        })
        code, stdout, stderr = self._invoke(
            output="status", input_text=json.dumps(payload))
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["status"], "AWAITING_MANUAL_IR_CAPSULE")
        self.assertNotIn("PRIVATE_ACCOUNT", stdout)

    def test_completed_ceo_requested_portfolio_uses_real_manual_pi_route(self):
        payload = json.loads(self._invoke(output="request-template")[1])
        payload["request"].update({
            "ceo_initiated": True,
            "research_needed": False,
            "portfolio_needed": True,
            "analysis_id": "SYN-NEW-02",
            "as_of": "2026-10-29",
            "kind": "DECISION",
            "objective": "Synthetic portfolio review",
            "strategy_id": "EXPLORATORY",
        })
        code, stdout, stderr = self._invoke(
            output="status", input_text=json.dumps(payload))
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["status"], "AWAITING_MANUAL_PI_DELTA")


if __name__ == "__main__":
    unittest.main()
