"""Connected M1→M3→M4 portfolio exposure reporting, synthetic input only.

Tests exercise real M3 ledger/exposure computations and both real CC
report routes, not mocked reports or live Blossom/Projects. Never certify
an account, source or investment decision.
"""
from __future__ import annotations

from copy import deepcopy
import unittest

from ai_native.portfolio_observation import prepare_observation_ledger
from ai_native.portfolio_exposure import aggregate_portfolio_exposures
from ai_native.reporting import render_report
from ai_native.session_bridge import complete_manual_session
from tests.test_ai_native_construction_contracts import R1ConstructionContracts
from tests.test_ai_native_r1_integrated_smoke import RealManualConstructionSmoke
from tests.test_ai_native_reporting import ReportingTests


class R1ExposureReportTests(unittest.TestCase):
    def setUp(self):
        self.fx = R1ConstructionContracts()

    def self_contained_observation(self):
        obs = prepare_observation_ledger(**self.fx.observation())
        exposure = aggregate_portfolio_exposures(
            obs, classifications_by_p_id=self.fx.classes())
        return obs, exposure

    def pi(self):
        return {
            "analysis_id":"SYN-X", "portfolio_as_of":"2026-10-28",
            "room_status":"ROOM_UNAVAILABLE",
            "summary":"Synthetic private portfolio, no broker verification",
            "limitations":"Some ETF constituent coverage missing",
            "next_action":"Confirm original dated portfolio evidence",
        }

    def test_pi_only_report_shows_scoped_components_not_holdings(self):
        observation = self.fx.observation()
        classes = self.fx.classes()
        original = deepcopy((observation, classes))
        result = complete_manual_session(
            self.fx.request(False, True), pi_delta=self.pi(),
            observation_inputs=observation, exposure_classifications=classes)
        self.assertEqual((observation, classes), original)
        self.assertEqual(result["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        report = result["final_report_private"]
        self.assertIn("Scoped portfolio exposures — caller-reported", report)
        self.assertIn("45.00% known classified exposure", report)
        self.assertIn("45.00% unknown/unclassified", report)
        self.assertIn("10.00% cash", report)
        self.assertNotIn("600.00", report)
        self.assertNotIn("ABC:TSX", report)
        self.assertNotIn("FUND:TSX", report)
        self.assertNotIn("S2", report)
        self.assertEqual(result["storage"], "NONE")
        self.assertEqual(result["project_invocation"], "NONE")

    def test_integrated_ir_pi_report_carries_real_current_exposures(self):
        case = RealManualConstructionSmoke().case()
        out = complete_manual_session(**case)
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        report = out["final_report_private"]
        self.assertIn("45.00% known classified exposure", report)
        self.assertIn("45.00% unknown/unclassified", report)
        self.assertIn("10.00% cash", report)
        self.assertNotIn("S2", report)
        self.assertNotIn("600.00", report)
        self.assertNotIn("portfolio_exposures_private",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(out["readiness"], "NOT_EVALUATED")

    def test_integrated_historical_fund_is_unknown_not_known(self):
        case = RealManualConstructionSmoke().case()
        case["exposure_classifications"]["P2"]["as_of"] = "2026-10-27"
        out = complete_manual_session(**case)
        report = out["final_report_private"]
        self.assertIn("30.00% known classified exposure", report)
        self.assertIn("60.00% unknown/unclassified", report)
        self.assertIn("10.00% cash", report)
        self.assertIn("Older ETF/fund constituents are excluded", report)
        self.assertNotIn("S2", report)
        self.assertNotIn("600.00", report)
        self.assertNotIn("historical_fund_scenario_private", report)

    def test_incomplete_scope_never_displays_exposure_numbers(self):
        result = complete_manual_session(
            self.fx.request(False, True), pi_delta=self.pi(),
            observation_inputs=self.fx.observation(complete=False),
            exposure_classifications=self.fx.classes())
        report = result["final_report_private"]
        self.assertIn("Scoped portfolio exposures — unavailable", report)
        self.assertNotIn("% known classified exposure", report)
        self.assertNotIn("% unknown/unclassified", report)
        self.assertEqual(result["portfolio_exposures_private"]["status"],
                         "UNAVAILABLE_INCOMPLETE_P_LEDGER")

    def test_report_refuses_forged_percentage_status_date_or_authority(self):
        obs, exposures = self.self_contained_observation()
        packet = ReportingTests().packet(
            analysis_id="SYN-X", as_of="2026-10-28",
            portfolio_observation_private=obs,
            portfolio_exposures_private=exposures)
        for patch in (
            {"known_exposure_pct":"95.00"},
            {"known_exposure_pct":"NaN"},
            {"unknown_exposure_pct":"0.00","unclassified_or_unknown_fund_pct":"0.00"},
            {"status":"CALLER_REPORTED_SCOPED_EXPOSURES"},
            {"analysis_id":"DIFFERENT"},
            {"observation_as_of":"2026-10-29"},
            {"trading_authority":"ALLOW_TRADES"},
            {"source_authentication":"INDEPENDENTLY_VERIFIED"},
            {"fund_composition_date_alignment":"PRIOR_DATED_FUND_SNAPSHOTS"},
        ):
            forged = deepcopy(packet)
            forged["portfolio_exposures_private"] = {**exposures, **patch}
            with self.subTest(patch=patch), self.assertRaisesRegex(
                ValueError, "REPORT_EXPOSURE"):
                render_report(forged)

    def test_report_rejects_unrelated_observation_and_no_position_retyping(self):
        obs, exposures = self.self_contained_observation()
        pkt = ReportingTests().packet(
            analysis_id="SYN-X", as_of="2026-10-28",
            portfolio_observation_private=obs,
            portfolio_exposures_private=exposures)
        pkt["portfolio_observation_private"] = {**obs,"observed_on":"2026-10-27"}
        with self.assertRaisesRegex(ValueError, "REPORT_EXPOSURE_OBSERVATION_MISMATCH"):
            render_report(pkt)
        pkt["portfolio_observation_private"] = None
        with self.assertRaisesRegex(ValueError, "REPORT_EXPOSURE_OBSERVATION_MISMATCH"):
            render_report(pkt)


if __name__ == "__main__":
    unittest.main()
