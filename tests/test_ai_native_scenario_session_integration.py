"""Synthetic integration: original PI displayed weights -> R1 scenario -> CC reports."""
from copy import deepcopy
import unittest

from ai_native.session_bridge import complete_manual_session
from scripts.r1_manual_session_cli import evaluate
from tests.test_ai_native_session_bridge import SessionBridgeTests
from tests.test_ai_native_portfolio_observation import ObservationTests


class ScenarioSessionIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.fx = SessionBridgeTests()
        self.obs = ObservationTests()

    def case(self, *, research=False, weight="100.00", shock="-30"):
        observed = self.obs.kwargs(analysis_id="CASE-A", observed_on="2026-10-28",
                                  analysis_as_of="2026-10-28")
        observed["positions"][0]["displayed_weight_pct"] = weight
        observed["positions"][0]["displayed_weight_visibility"] = "VERIFIED_VISIBLE"
        raw = {
            "analysis_id": "CASE-A", "analysis_as_of": "2026-10-28",
            "strategy_id": "balanced",
            "denominator_evidence": "DISPLAYED_VIEW_DENOMINATOR_CALLER_ATTESTED",
            "positions": [
                {"p_id": "P-1", "weight_pct": weight, "function": "GROWTH"},
            ],
            "scenarios": [{
                "scenario_id": "SYN_STOCK_DOWN", "as_of": "2026-10-28",
                "assumption_source_ref": "SYNTHETIC_REFERENCE_DO_NOT_CERTIFY",
                "shocks_pct_by_p_id": {"P-1": shock},
            }],
        }
        req = self.fx.request(strategy_id="balanced", research_needed=research,
                              portfolio_needed=True)
        payload = {"request": req, "pi_delta": self.fx.pi(strategy_id="balanced"),
                   "observation_inputs": observed, "scenario_weight_inputs": raw}
        if research:
            ir = self.fx.ir(strategy_id="balanced")
            payload["ir_capsule"] = ir
            payload["pi_delta"]["forwarded_ir"] = deepcopy(ir)
        return payload

    def test_pi_only_final_report_includes_sensitivity_not_account_truth(self):
        original = self.case()
        prior = deepcopy(original)
        out = complete_manual_session(**original)
        self.assertEqual(prior, original)
        self.assertEqual(out["status"], "PI_ONLY_CONDITIONAL_REPORT_ASSEMBLED")
        self.assertEqual(out["scenario_weight_sensitivity_private"]["policy_authority"], "NONE")
        self.assertIn("variation hypothétique de la vue -30.00%",
                      out["final_report_private"])
        self.assertIn("variation hypothétique de la vue -30.00%",
                      out["executive_report_private"])
        for secret in ("SYN_STOCK_DOWN", "P-1", "SYNTHETIC_REFERENCE_DO_NOT_CERTIFY", "SCOPE-A"):
            self.assertNotIn(secret, out["final_report_private"])
        self.assertEqual(out["storage"], "NONE")

    def test_ir_pi_route_integration_and_institutional_memory_exclusion(self):
        payload = self.case(research=True)
        out = complete_manual_session(**payload)
        self.assertEqual(out["status"], "M7A_COMPONENT_ASSEMBLED_NOT_END_TO_END_ACCEPTANCE")
        self.assertIn("variation hypothétique de la vue -30.00%", out["final_report_private"])
        self.assertIn("variation hypothétique de la vue -30.00%", out["executive_report_private"])
        self.assertEqual(out["integrated_private"]["scenario_weight_sensitivity_private"],
                         out["scenario_weight_sensitivity_private"])
        self.assertNotIn("SYN_STOCK_DOWN",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))
        self.assertEqual(out["readiness"], "NOT_EVALUATED")

    def test_cli_true_manual_json_path(self):
        out = evaluate(self.case())
        self.assertEqual(out["scenario_weight_sensitivity_private"]["scenarios"][0]
                         ["scoped_displayed_hypothetical_return_pct"], "-30.00")

    def test_missing_pi_or_observation_or_unrequested_route_fails(self):
        for variant, regex in (
            ("pi", "COMPLETED_PI_ROUTE"),
            ("observation", "PRIVATE_PI_OBSERVATION"),
            ("route", "COMPLETED_PI_ROUTE"),
        ):
            p = self.case()
            if variant == "pi":
                p.pop("pi_delta")
            elif variant == "observation":
                p.pop("observation_inputs")
            else:
                p["request"]["portfolio_needed"] = False
                p.pop("pi_delta")
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, regex):
                complete_manual_session(**p)

    def test_retyped_weights_and_ids_fail(self):
        for variant in ("weight", "id", "date", "mode", "source"):
            p = self.case()
            if variant == "weight":
                p["scenario_weight_inputs"]["positions"][0]["weight_pct"] = "99.00"
            elif variant == "id":
                p["scenario_weight_inputs"]["positions"][0]["p_id"] = "OTHER"
            elif variant == "date":
                p["scenario_weight_inputs"]["analysis_as_of"] = "2026-10-27"
            elif variant == "mode":
                p["scenario_weight_inputs"]["strategy_id"] = "high-cagr"
            else:
                p["observation_inputs"]["source_type"] = "PUBLIC_BLOSSOM_REFERENCE"
                p["observation_inputs"]["private_scope"] = False
            with self.subTest(variant=variant), self.assertRaises(ValueError):
                complete_manual_session(**p)

    def test_malformed_scenario_fields_fail_with_value_errors(self):
        for variant in ("nonstring_mode", "nonstring_weight"):
            payload = self.case()
            if variant == "nonstring_mode":
                payload["scenario_weight_inputs"]["strategy_id"] = None
            else:
                payload["scenario_weight_inputs"]["positions"][0]["weight_pct"] = 100
            with self.subTest(variant=variant), self.assertRaisesRegex(
                    ValueError, "SCENARIO_REVIEW_"):
                complete_manual_session(**payload)

    def test_official_macro_context_does_not_certify_caller_shocks(self):
        payload = self.case(research=True)
        payload["scenario_weight_inputs"]["historical_regime_id"] = "CA_2022_INFLATION"
        original = deepcopy(payload)
        out = complete_manual_session(**payload)
        self.assertEqual(payload, original)
        review = out["scenario_weight_sensitivity_private"]
        context = review["historical_regime_context_private"]
        self.assertEqual(context["asset_returns"], "NOT_SUPPLIED")
        self.assertEqual(context["shocks_derived"], "NO")
        self.assertEqual(review["scenarios"][0]["scoped_displayed_hypothetical_return_pct"],
                         "-30.00")
        self.assertIn("Statistique Canada", out["final_report_private"])
        self.assertIn("Statistics Canada", out["final_report_private"])
        self.assertIn("AUCUN rendement", out["final_report_private"])
        self.assertNotIn("SYN_STOCK_DOWN", out["final_report_private"])
        self.assertNotIn("CA_2022_INFLATION",
                         str(out["integrated_private"]["memory_proposal_nonprivate"]))

    def test_unknown_historical_regime_fails_closed(self):
        payload = self.case()
        payload["scenario_weight_inputs"]["historical_regime_id"] = "BOGUS"
        with self.assertRaisesRegex(ValueError, "REGIME_CONTEXT_UNKNOWN"):
            complete_manual_session(**payload)
        payload["scenario_weight_inputs"]["historical_regime_id"] = None
        with self.assertRaisesRegex(ValueError, "REGIME_CONTEXT_UNKNOWN"):
            complete_manual_session(**payload)
        payload["scenario_weight_inputs"].pop("historical_regime_id")
        payload["scenario_weight_inputs"]["unexpected"] = "YES"
        with self.assertRaisesRegex(ValueError, "SCENARIO_REVIEW_EXACT_SCHEMA"):
            complete_manual_session(**payload)

    def test_100_point_2_is_unavailable_in_actual_report(self):
        payload = self.case(weight="100.00")
        payload["observation_inputs"]["positions"][0]["displayed_weight_pct"] = "100.00"
        # Two rows with weights whose raw sum exceeds 100% (not silently fixed).
        second = deepcopy(payload["observation_inputs"]["positions"][0])
        second["p_id"] = "P-2"
        second["security_id"] = "DEF:TSX"
        second["market_value_base"] = "200.00"
        second["displayed_weight_pct"] = "0.20"
        payload["observation_inputs"]["positions"].append(second)
        payload["scenario_weight_inputs"]["positions"].append(
            {"p_id": "P-2", "weight_pct": "0.20", "function": "DEFLATION_DURATION"})
        payload["scenario_weight_inputs"]["scenarios"][0]["shocks_pct_by_p_id"]["P-2"] = "5"
        out = complete_manual_session(**payload)
        self.assertIn("UNAVAILABLE_WEIGHTS_EXCEED_100_NO_NORMALIZATION",
                      out["final_report_private"])
        self.assertNotIn("variation hypothétique de la vue", out["final_report_private"])


if __name__ == "__main__":
    unittest.main()
