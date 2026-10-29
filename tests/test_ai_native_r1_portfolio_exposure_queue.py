"""Current-exposure evidence follow-up for real R1 private manual sessions.

Synthetic only. The queue remains a human instruction list, never a generated
fund source, account verification, readiness gate or automatic Project call.
"""
from __future__ import annotations

from copy import deepcopy
import json
import unittest

from ai_native.manual_review_queue import prepare_manual_review_queue
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_construction_contracts import R1ConstructionContracts
from tests.test_ai_native_r1_integrated_smoke import RealManualConstructionSmoke


class R1PortfolioExposureQueueTests(unittest.TestCase):
    def setUp(self):
        self.fx = R1ConstructionContracts()

    def pi(self):
        return {"analysis_id":"SYN-X", "portfolio_as_of":"2026-10-28",
                "room_status":"ROOM_UNAVAILABLE", "summary":"Unverified synthetic",
                "limitations":"Private scope incomplete", "next_action":"Check original"}

    def case(self, classifications=None, complete=True):
        return complete_manual_session(
            self.fx.request(False, True), pi_delta=self.pi(),
            observation_inputs=self.fx.observation(complete=complete),
            exposure_classifications=(
                self.fx.classes() if classifications is None else classifications))

    @staticmethod
    def codes(session):
        output = prepare_manual_review_queue(session)
        assert output["item_count"] <= 13
        return output, [row["code"] for row in output["items"]]

    def test_same_day_partial_fund_requests_specific_coverage_not_buying(self):
        case = self.case()
        out, codes = self.codes(case)
        self.assertIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)
        self.assertNotIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("CHECK_PORTFOLIO_ORIGINAL", codes)
        self.assertEqual(out["trading_authority"], "NONE")
        self.assertEqual(out["project_invocation"], "NONE")
        self.assertEqual(out["readiness"], "NOT_EVALUATED")
        self.assertEqual(out["storage"], "NONE")

    def test_historical_fund_prioritizes_refresh_over_generic_source_task(self):
        classes = self.fx.classes()
        classes["P2"]["as_of"] = "2026-10-27"
        saved = deepcopy(classes)
        case = self.case(classifications=classes)
        out, codes = self.codes(case)
        self.assertEqual(classes, saved)
        self.assertIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)
        self.assertNotIn("CHECK_PORTFOLIO_ORIGINAL", codes)
        self.assertIn("REVIEW_CONDITIONAL_REPORT", codes)
        self.assertNotIn("ABC:TSX", json.dumps(out))
        self.assertNotIn("FUND:TSX", json.dumps(out))
        self.assertNotIn("S2", json.dumps(out))
        self.assertNotIn("600.00", json.dumps(out))

    def test_current_complete_report_keeps_independent_original_check(self):
        classes = self.fx.classes()
        classes["P2"]["constituents"][0]["fund_weight_pct"] = "100"
        classes["P2"]["composition_complete_reported"] = True
        case = self.case(classifications=classes)
        _, codes = self.codes(case)
        self.assertIn("CHECK_PORTFOLIO_ORIGINAL", codes)
        self.assertNotIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)

    def test_missing_or_rights_uncertain_classification_is_an_evidence_task(self):
        for case_classes in ({}, self.fx.classes("UNCERTAIN")):
            with self.subTest(classifications=case_classes):
                _, codes = self.codes(self.case(classifications=case_classes))
                self.assertIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)
                self.assertNotIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)

    def test_incomplete_scope_requires_scope_not_invented_fund_review(self):
        case = self.case(complete=False)
        _, codes = self.codes(case)
        self.assertIn("RECONCILE_PORTFOLIO_SCOPE", codes)
        self.assertNotIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)

    def test_real_complete_ir_pi_report_queue_uses_same_exposure_priority(self):
        c = RealManualConstructionSmoke().case()
        c["exposure_classifications"]["P2"]["as_of"] = "2026-10-27"
        result = complete_manual_session(**c)
        _, codes = self.codes(result)
        self.assertIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("CHECK_PORTFOLIO_ORIGINAL", codes)
        self.assertEqual(result["project_invocation"], "NONE")

    def test_pending_pi_does_not_create_unrequested_evidence_tasks(self):
        pending = complete_manual_session(
            self.fx.request(False, True),
            observation_inputs=self.fx.observation(),
            exposure_classifications=self.fx.classes())
        _, codes = self.codes(pending)
        self.assertIn("TRANSFER_PI_DELTA", codes)
        self.assertNotIn("REFRESH_DATED_FUND_LOOKTHROUGH", codes)
        self.assertNotIn("RESOLVE_CURRENT_EXPOSURE_COVERAGE", codes)

    def test_exposure_scope_or_authority_forgery_rejected_privately(self):
        complete = self.case()
        for patch in ({"source_authentication":"BROKER_VERIFIED"},
                      {"account_scope_private":"OTHER_ACCOUNT"},
                      {"analysis_id":"WRONG_ID"},
                      {"observation_as_of":"2026-10-27"},
                      {"known_exposure_pct":"NaN"},
                      {"known_exposure_pct":"99.00"},
                      {"fund_composition_date_alignment":"PRIOR_DATED_FUND_SNAPSHOTS"},
                      {"status":"CALLER_REPORTED_SCOPED_EXPOSURES"}):
            with self.subTest(patch=patch):
                bad = deepcopy(complete)
                bad["portfolio_exposures_private"].update(patch)
                with self.assertRaisesRegex(ValueError, "REVIEW_QUEUE_EXPOSURE"):
                    prepare_manual_review_queue(bad)

    def test_private_inputs_and_queue_bounds_unchanged(self):
        case = self.case()
        before = deepcopy(case)
        queue = prepare_manual_review_queue(case)
        self.assertEqual(case, before)
        self.assertEqual(queue["item_count"], len(queue["items"]))
        self.assertLessEqual(queue["item_count"], 13)
        self.assertEqual(len({v["code"] for v in queue["items"]}),queue["item_count"])


if __name__ == "__main__":
    unittest.main()
