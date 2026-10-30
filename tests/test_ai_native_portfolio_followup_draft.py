"""R1 synthetic sealed M3 record -> new CEO-requested PI follow-up.

All original prior holdings stay in private CC-only input; no source
authentication, automatic Project execution, archive storage or trades.
"""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.portfolio_snapshot_transfer import (
    seal_private_portfolio_snapshot, verify_private_portfolio_snapshot,
)
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests


class PortfolioFollowupDraftTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def cli(self, packet, mode="portfolio-followup-draft"):
        stdin = StringIO(json.dumps(packet, ensure_ascii=False))
        stdout, stderr = StringIO(), StringIO()
        code = main(["--output", mode], instream=stdin,
                    outstream=stdout, errstream=stderr)
        return code, stdout.getvalue(), stderr.getvalue()

    def old(self):
        values = self.obs.kwargs(
            analysis_id="HIST-PI-CASE",
            analysis_as_of="2026-10-28",
            observed_on="2026-10-28",
            captured_at="2026-10-28T09:30:00-04:00",
        )
        values["positions"][0]["security_id"] = "HISTORICAL-ONLY-SECRET:TSX"
        return seal_private_portfolio_snapshot(values)

    def current(self):
        return self.obs.kwargs(
            analysis_id="FRESH-PI-CASE",
            analysis_as_of="2026-10-29",
            observed_on="2026-10-29",
            captured_at="2026-10-29T10:30:00-04:00",
        )

    def prepared(self):
        old = self.old()
        rc, body, err = self.cli({
            "private_portfolio_snapshot_envelope": old})
        self.assertEqual((rc, err), (0, ""))
        return old, json.loads(body)

    def authorized_session(self, draft):
        source = deepcopy(draft["input_template"])
        source["request"].update({
            "ceo_initiated": True,
            "analysis_id": "FRESH-PI-CASE",
            "as_of": "2026-10-29",
            "objective": "Describe changed scope weights from two dated views",
            "horizon": "multi-year",
            "risk_constraints": ["No inference of trades or returns"],
            "account_context": {
                "type": "PERSONAL", "broker": "UNKNOWN",
                "tax": "UNKNOWN", "commission": "UNKNOWN",
                "fx_cost": "UNKNOWN",
            },
        })
        source["observation_inputs"] = self.current()
        return source

    def test_inert_snapshot_followup_draft_does_not_copy_stale_holdings_to_request(self):
        old = self.old()
        preserved = deepcopy(old)
        rc, body, err = self.cli({
            "private_portfolio_snapshot_envelope": old})
        self.assertEqual((rc, err), (0, ""))
        draft = json.loads(body)
        self.assertEqual(draft["status"],
                         "PRIVATE_PORTFOLIO_FOLLOWUP_DRAFT_REQUIRES_CEO_INITIATION")
        req = draft["input_template"]["request"]
        self.assertIs(req["ceo_initiated"], False)
        self.assertIsNone(req["analysis_id"])
        self.assertIsNone(req["as_of"])
        self.assertIsNone(req["objective"])
        self.assertEqual(req["kind"], "FOLLOWUP")
        self.assertIs(req["research_needed"], False)
        self.assertIs(req["portfolio_needed"], True)
        self.assertEqual(req["prior_analysis_id"], "HIST-PI-CASE")
        self.assertEqual(req["strategy_id"], "EXPLORATORY")
        self.assertEqual(req["pi_method_version"], "UNKNOWN_NOT_LOADED")
        self.assertNotIn("HISTORICAL-ONLY-SECRET", json.dumps(req))
        self.assertNotIn("SCOPE-A", json.dumps(req))
        self.assertNotIn("positions", json.dumps(req))
        self.assertNotIn("observed_on", json.dumps(req))
        self.assertEqual(draft["input_template"][
            "prior_private_portfolio_envelope"], old)
        self.assertEqual(draft["prior_observation_reference_private"][
            "observed_on"], "2026-10-28")
        self.assertEqual(draft["previous_record_authenticity"],
                         "NOT_ESTABLISHED_UNKEYED_CHECKSUM")
        self.assertEqual(draft["current_portfolio_observation"],
                         "NOT_SUPPLIED")
        self.assertEqual(draft["project_invocation"], "NONE")
        self.assertEqual(draft["storage"], "NONE")
        self.assertEqual(draft["trading_authority"], "NONE")
        self.assertEqual(old, preserved)
        self.assertEqual(verify_private_portfolio_snapshot(old)[
            "analysis_id"], "HIST-PI-CASE")
        rc, output, err = self.cli(draft["input_template"], "guided-portfolio-closeout")
        self.assertEqual((rc, output), (2, ""))
        self.assertIn("CEO_INITIATION_REQUIRED", err)

    def test_new_explicit_pi_followup_reuses_guided_pi_and_seals_only_current(self):
        previous, draft = self.prepared()
        session = self.authorized_session(draft)
        unchanged = deepcopy(session)
        rc, body, err = self.cli(session, "guided-portfolio-closeout")
        self.assertEqual((rc, err), (0, ""))
        first = json.loads(body)
        self.assertEqual(
            first["status"], "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_PENDING_MANUAL_PI")
        operator = first["guided_operator_private"]
        self.assertEqual(operator["specialist_step"], "PI_REQUEST")
        prompt = operator["specialist_prompt_private"]
        self.assertIn("Recipient: Portfolio Intelligence (PI)", prompt)
        self.assertIn("METHOD_PATH:", prompt)
        self.assertNotIn("HISTORICAL-ONLY-SECRET", prompt)
        self.assertNotIn("prior_private_portfolio_envelope", prompt)
        self.assertNotIn('"resume_input"', prompt)
        continuation = operator["operator_packet_private"]["continuation_private"]
        self.assertEqual(continuation["resume_input"][
            "prior_private_portfolio_envelope"], previous)
        self.assertNotIn(
            "HISTORICAL-ONLY-SECRET",
            json.dumps(continuation["next_handoff"]["PI_REQUEST"]))
        self.assertEqual(session, unchanged)
        rc, body, err = self.cli({
            "continuation_private": continuation,
            "specialist_result": {
                "PI_DELTA": self.fx.pi(
                    analysis_id="FRESH-PI-CASE",
                    portfolio_as_of="2026-10-29"),
            },
        }, "guided-portfolio-closeout")
        self.assertEqual((rc, err), (0, ""))
        completed = json.loads(body)
        self.assertEqual(completed["status"],
                         "PRIVATE_GUIDED_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        final = completed["private_portfolio_closeout"]
        self.assertEqual(final["status"], "PRIVATE_PORTFOLIO_CLOSEOUT_COPY_NOT_STORED")
        fresh = verify_private_portfolio_snapshot(
            final["private_portfolio_snapshot_envelope"])
        self.assertEqual(fresh, session["observation_inputs"])
        self.assertNotIn("HISTORICAL-ONLY-SECRET", json.dumps(fresh))
        self.assertEqual(final["operator_packet_private"]["session"][
            "route"], "CC_PI_CC")
        self.assertIsInstance(final["operator_packet_private"][
            "report_private"], str)
        self.assertEqual(final["storage"], "NONE")
        self.assertEqual(final["trading_authority"], "NONE")
        self.assertNotIn("private_case_envelope", body)

    def test_changed_original_envelope_or_wrong_id_fails_closed_without_private_echo(self):
        old = self.old()
        bad = deepcopy(old)
        bad["private_snapshot"]["original_observation_inputs"][
            "positions"][0]["security_id"] = "LEAKED_SECRET_TAMPERED"
        code, output, err = self.cli({
            "private_portfolio_snapshot_envelope": bad})
        self.assertEqual((code, output), (2, ""))
        self.assertIn("PRIVATE_PORTFOLIO_SHA256_MISMATCH", err)
        self.assertNotIn("LEAKED_SECRET_TAMPERED", err)

        _, draft = self.prepared()
        wrong = self.authorized_session(draft)
        wrong["request"]["prior_analysis_id"] = "UNRELATED-OLD-CASE"
        code, output, err = self.cli(wrong, "guided-portfolio-closeout")
        self.assertEqual((code, output), (2, ""))
        self.assertIn("PRIVATE_PORTFOLIO_BASELINE_ID_MISMATCH", err)
        self.assertNotIn("HISTORICAL-ONLY-SECRET", err)

    def test_new_observation_required_and_old_date_not_a_current_view(self):
        _, draft = self.prepared()
        missing = self.authorized_session(draft)
        missing.pop("observation_inputs")
        code, output, err = self.cli(missing, "guided-portfolio-closeout")
        self.assertEqual((code, output), (2, ""))
        self.assertNotIn("HISTORICAL-ONLY-SECRET", err)

        same_date = self.authorized_session(draft)
        same_date["observation_inputs"]["observed_on"] = "2026-10-28"
        same_date["observation_inputs"]["captured_at"] = (
            "2026-10-28T10:30:00-04:00")
        code, output, err = self.cli(same_date, "guided-portfolio-closeout")
        self.assertEqual((code, output), (2, ""))
        self.assertNotIn("HISTORICAL-ONLY-SECRET", err)


if __name__ == "__main__":
    unittest.main()
