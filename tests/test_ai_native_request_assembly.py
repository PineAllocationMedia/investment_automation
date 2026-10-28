import copy
import json
import unittest
from ai_native.request_assembly import prepare_manual_handoffs


class RequestAssemblyTests(unittest.TestCase):
    def request(self, **changes):
        req = dict(ceo_initiated=True, analysis_id="SYN-01", as_of="2026-10-28", kind="DECISION",
                   objective="Study a synthetic business", research_needed=True, portfolio_needed=False)
        req.update(changes)
        return req

    def capsule(self, **changes):
        packet = {"analysis_id": "SYN-01", "research_as_of": "2026-10-27", "facts": [
            {"id": "F1", "status": "INDICATIVE", "source_url": "https://example.test/filing", "claim": "Not verified"}],
            "evidence_annex": {"S": ["S1"], "K": [], "V": []}}
        packet.update(changes)
        return packet

    def test_ir_route_and_no_assumed_policy_or_benchmark(self):
        out = prepare_manual_handoffs(self.request())
        self.assertEqual(out["route"], "CC_IR_CC")
        self.assertEqual(out["ir_request_private"]["strategy_id"], "EXPLORATORY")
        self.assertEqual(out["ir_request_private"]["benchmark"], "UNKNOWN")
        self.assertEqual(out["ir_request_private"]["method_version"], "UNKNOWN_NOT_LOADED")
        self.assertIsNone(out["pi_request_private"])
        self.assertEqual(out["project_invocation"], "NONE")

    def test_direct_route_has_no_duplicated_specialist_work(self):
        o = prepare_manual_handoffs(self.request(research_needed=False, portfolio_needed=False))
        self.assertEqual(o["route"], "CC_DIRECT")
        self.assertEqual(o["copy_ready_private"], {})

    def test_portfolio_only_route_keeps_unknown_holdings(self):
        o = prepare_manual_handoffs(self.request(research_needed=False, portfolio_needed=True))
        self.assertEqual(o["route"], "CC_PI_CC")
        self.assertEqual(o["pi_request_private"]["portfolio_context_private"]["status"], "NOT_SUPPLIED")
        self.assertIsNone(o["pi_request_private"]["FORWARD_UNCHANGED"])

    def test_both_routes_wait_for_ir_before_pi(self):
        o = prepare_manual_handoffs(self.request(portfolio_needed=True))
        self.assertEqual(o["route"], "CC_IR_PI_CC")
        self.assertIsNone(o["pi_request_private"])
        self.assertIn("PI_REQUEST_AWAITING_ORIGINAL_IR_CAPSULE", o["pending_manual_steps"])

    def test_entire_capsule_transferred_unchanged_once(self):
        inp = self.capsule()
        o = prepare_manual_handoffs(self.request(portfolio_needed=True), ir_capsule=inp)
        pi = o["pi_request_private"]
        self.assertEqual(pi["FORWARD_UNCHANGED"], inp)
        self.assertEqual(pi["FORWARD_UNCHANGED"]["facts"][0]["status"], "INDICATIVE")
        self.assertEqual(json.loads(o["copy_ready_private"]["PI_REQUEST"])["FORWARD_UNCHANGED"], inp)
        self.assertEqual(o["pending_manual_steps"], [])
        self.assertEqual(o["ir_request_private"]["analysis_id"], pi["analysis_id"])
        self.assertNotIn("IR_CAPSULE", pi)

    def test_input_deepcopy_protects_original(self):
        req = self.request(portfolio_needed=True, account_context={"private": ["hidden"]})
        capsule = self.capsule()
        portfolio = {"observed_at": "2026-10-28", "holdings": ["PRIVATE"]}
        before = copy.deepcopy((req, capsule, portfolio))
        out = prepare_manual_handoffs(req, ir_capsule=capsule, portfolio_context=portfolio)
        out["pi_request_private"]["FORWARD_UNCHANGED"]["facts"][0]["status"] = "VERIFIED"
        self.assertEqual((req, capsule, portfolio), before)

    def test_missing_ceo_initiation_refused(self):
        with self.assertRaisesRegex(ValueError, "CEO_INITIATION_REQUIRED"):
            prepare_manual_handoffs(self.request(ceo_initiated=False))

    def test_non_boolean_route_flag_refused(self):
        with self.assertRaisesRegex(ValueError, "explicit boolean"):
            prepare_manual_handoffs(self.request(research_needed="true"))

    def test_bad_date_refused(self):
        with self.assertRaisesRegex(ValueError, "invalid|ISO"):
            prepare_manual_handoffs(self.request(as_of="2026-02-30"))

    def test_bad_ir_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "IR_ANALYSIS_ID_MISMATCH"):
            prepare_manual_handoffs(self.request(portfolio_needed=True), ir_capsule=self.capsule(analysis_id="OTHER"))

    def test_future_ir_refused(self):
        with self.assertRaisesRegex(ValueError, "IR_RESEARCH_NEWER_THAN_CUTOFF"):
            prepare_manual_handoffs(self.request(portfolio_needed=True), ir_capsule=self.capsule(research_as_of="2026-11-01"))

    def test_future_portfolio_date_refused(self):
        with self.assertRaisesRegex(ValueError, "PORTFOLIO_OBSERVATION_NEWER_THAN_CUTOFF"):
            prepare_manual_handoffs(self.request(research_needed=False, portfolio_needed=True), portfolio_context={"observed_at": "2026-10-29"})

    def test_unrequested_ir_packet_refused(self):
        with self.assertRaisesRegex(ValueError, "IR_CAPSULE_UNREQUESTED"):
            prepare_manual_handoffs(self.request(research_needed=False), ir_capsule=self.capsule())

    def test_unrequested_private_context_refused(self):
        with self.assertRaisesRegex(ValueError, "PORTFOLIO_CONTEXT_UNREQUESTED"):
            prepare_manual_handoffs(self.request(portfolio_needed=False), portfolio_context={"observed_at":"UNKNOWN"})

    def test_nonportable_packet_refused(self):
        with self.assertRaisesRegex(ValueError, "portable JSON"):
            prepare_manual_handoffs(self.request(portfolio_needed=True), ir_capsule=self.capsule(facts={1, 2}))

    def test_tuple_packet_not_coerced_to_list(self):
        with self.assertRaisesRegex(ValueError, "non-JSON types"):
            prepare_manual_handoffs(self.request(portfolio_needed=True), ir_capsule=self.capsule(facts=("F1",)))

    def test_no_auto_authentication_of_method_or_holdings(self):
        o = prepare_manual_handoffs(self.request(research_needed=False, portfolio_needed=True,
                         pi_method_version="R1", strategy_id="high-cagr"),
                         portfolio_context={"observed_at": "2026-10-28", "holdings": {"A": "50"}})
        pi = o["pi_request_private"]
        self.assertEqual(pi["strategy_authority"], "CALLER_SUPPLIED_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(o["method_load_verification"], "NOT_PERFORMED")
        self.assertEqual(pi["portfolio_context_private"]["observation_authentication"], "USER_SUPPLIED_NOT_VERIFIED_BY_ASSEMBLER")
        self.assertEqual(o["storage"], "NONE")


if __name__ == "__main__":
    unittest.main()
