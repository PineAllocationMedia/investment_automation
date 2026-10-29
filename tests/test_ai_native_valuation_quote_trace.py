"""Synthetic price-source trace checks for the manual R1 valuation workflow."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.source_fusion import assemble_source_fusion
from ai_native.valuation_quote_trace import trace_valuation_quote
from ai_native.integrated_flow import assemble_manual_run
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_valuation_scenarios import ScenarioTests


class ValuationQuoteTraceTests(unittest.TestCase):
    def setUp(self):
        self.fx = ScenarioTests()

    def source(self, **changes):
        row = dict(
            observation_id="QUOTE-O1", fact_id="QUOTE-F1", source_id="QUOTE-S1",
            economic_issuer="SYNTHETIC-ISSUER", instrument="ABC:TSX",
            metric="MARKET_PRICE_PER_SHARE", period_start="2026-10-28",
            period_end="2026-10-28", currency="CAD", unit="PER_SHARE",
            definition_basis="EXCHANGE_LAST_REPORTED", consolidation="SECURITY_CLASS",
            value="100", observed_at="2026-10-28", published_at="2026-10-28",
            original_checked_at="2026-10-28", source_kind="SECONDARY",
            classification="SOURCE_FACT", source_locator="https://example.org/private-quote",
            rights_status="PERMITTED", verification_status="INDICATIVE",
        )
        row.update(changes)
        return row

    def annex(self, observations=None):
        return assemble_source_fusion(
            analysis_id="SYN-01", analysis_as_of="2026-10-28",
            observations=[self.source()] if observations is None else observations,
        )

    def price(self, **changes):
        inputs = {"quote_source_ref": "QUOTE-O1"}
        inputs.update(changes)
        return self.fx.case(**inputs)

    def trace(self, *, observations=None, research_as_of="2026-10-28", **changes):
        source = self.annex(observations)
        return trace_valuation_quote(
            valuation=self.price(**changes), source_annex=source,
            ir_research_as_of=research_as_of,
        )

    def request(self):
        return {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "objective":"Review synthetic scenario arithmetic",
            "strategy_id":"high-cagr", "method_version":"SYNTHETIC",
            "kind":"DECISION",
        }

    def ir(self):
        return {
            "analysis_id":"SYN-01", "research_as_of":"2026-10-28",
            "summary":["No independently verified price."],
            "facts":[{"id":"QUOTE-F1", "status":"INDICATIVE",
                      "claim":"Private synthetic quote."}],
            "limitations":"Source not certified",
            "countercase":"Price may differ between venues.",
            "decision_line":"No investment recommendation.",
            "next_action":"Verify original dated quote.",
        }

    def valuation_inputs(self):
        return self.fx.setup_case(quote_source_ref="QUOTE-O1")

    def test_price_exact_decimals_are_equal_but_still_not_authenticated(self):
        trace = self.trace()
        self.assertEqual(trace["review_stage"], "HUMAN_QUOTE_REVIEW_ONLY")
        self.assertEqual(trace["reason_codes"], [])
        self.assertEqual(trace["original_market_price_verification"], "NOT_ESTABLISHED")
        self.assertEqual(trace["market_price_or_fx_authority"], "NONE")

    def test_absent_annex_is_not_implicitly_certified(self):
        trace = trace_valuation_quote(
            valuation=self.price(), source_annex=None,
            ir_research_as_of="2026-10-28")
        self.assertEqual(trace["review_stage"], "EVIDENCE_RESOLUTION")
        self.assertEqual(trace["reason_codes"], ["SOURCE_ANNEX_NOT_SUPPLIED"])

    def test_unknown_quote_reference_not_replaced_by_other_price(self):
        trace = self.trace(quote_source_ref="NOT-IN-ANNEX")
        self.assertEqual(trace["matched_observation_id_private"], None)
        self.assertIn("QUOTE_OBSERVATION_NOT_LINKED", trace["reason_codes"])

    def test_wrong_value_class_exchange_currency_date_and_metric_rejected(self):
        variations = [
            (dict(value="101"), "QUOTE_PRICE_DISAGREES"),
            (dict(instrument="OTHER:TSX"), "QUOTE_IDENTITY"),
            (dict(currency="USD"), "QUOTE_IDENTITY"),
            (dict(period_start="2026-10-27"), "QUOTE_IDENTITY"),
            (dict(unit="SHARES"), "QUOTE_IDENTITY"),
            (dict(metric="DILUTED_EPS"), "QUOTE_IDENTITY"),
        ]
        for patch, message in variations:
            with self.subTest(patch=patch), self.assertRaisesRegex(ValueError, message):
                self.trace(observations=[self.source(**patch)])

    def test_conflict_and_uncertain_rights_are_evidence_resolution(self):
        scenarios = [
            [self.source(rights_status="UNCERTAIN")],
            [self.source(rights_status="RESTRICTED")],
            [self.source(source_kind="ASSUMPTION",
                         classification="PAM_ASSUMPTION", source_locator=None)],
            [self.source(value=None, verification_status="MISSING")],
            [self.source(), self.source(observation_id="QUOTE-O2",
                                        source_id="QUOTE-S2", value="101")],
        ]
        for obs in scenarios:
            with self.subTest(obs=obs):
                trace = self.trace(observations=obs)
                self.assertEqual(trace["review_stage"], "EVIDENCE_RESOLUTION")
                self.assertTrue(trace["reason_codes"])

    def test_quote_newer_than_research_cutoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "QUOTE_VALUATION_ID_DATE_OR_BASIS_MISMATCH"):
            self.trace(research_as_of="2026-10-27")

    def test_observation_captured_after_ir_cutoff_rejected_even_if_quote_date_old(self):
        # Citation was dated 2026-10-28 but discovered only 2026-10-29.
        source = assemble_source_fusion(
            analysis_id="SYN-01", analysis_as_of="2026-10-30",
            observations=[self.source(
                observed_at="2026-10-29", original_checked_at="2026-10-29")])
        valuation = self.fx.case(analysis_as_of="2026-10-30",
                                 quote_source_ref="QUOTE-O1")
        with self.assertRaisesRegex(ValueError, "AFTER_IR_RESEARCH"):
            trace_valuation_quote(
                valuation=valuation, source_annex=source,
                ir_research_as_of="2026-10-28")

    def test_source_authentication_spoof_not_accepted(self):
        annex = self.annex()
        annex["source_authentication"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "QUOTE_SOURCE_ANNEX_AUTHORITY"):
            trace_valuation_quote(valuation=self.price(), source_annex=annex,
                                  ir_research_as_of="2026-10-28")

    def test_caller_ir_and_quote_not_mutated_in_integrated_report(self):
        request, ir, valuation = self.request(), self.ir(), self.valuation_inputs()
        ir["EVIDENCE_ANNEX"] = {
            "analysis_id":"SYN-01", "analysis_as_of":"2026-10-28",
            "observations":[self.source()]
        }
        before = deepcopy((request, ir, valuation))
        result = assemble_manual_run(request, ir, valuation_inputs=valuation)
        self.assertEqual((request, ir, valuation), before)
        self.assertEqual(result["valuation_quote_trace_private"]["review_stage"],
                         "HUMAN_QUOTE_REVIEW_ONLY")
        self.assertIn("Quotation provenance", result["markdown"])
        self.assertIn("human authentication still required", result["markdown"])
        self.assertNotIn("https://example.org/private-quote", result["markdown"])
        self.assertNotIn("QUOTE-O1", result["markdown"])
        self.assertNotIn("QUOTE-O1", str(result["memory_proposal_nonprivate"]))
        self.assertIn("CONDITIONAL", result["markdown"])

    def test_unlinked_quote_remains_conditionally_reported(self):
        result = assemble_manual_run(
            self.request(), self.ir(), valuation_inputs=self.valuation_inputs())
        self.assertEqual(result["valuation_quote_trace_private"]["review_stage"],
                         "EVIDENCE_RESOLUTION")
        self.assertIn("evidence resolution required", result["markdown"])
        self.assertIn("not a checked market-price return", result["markdown"])

    def test_ir_pi_bridge_preserves_capsule_and_uses_same_quote_check(self):
        request = dict(self.request(), ceo_initiated=True,
                       research_needed=True, portfolio_needed=True)
        ir = self.ir()
        ir["EVIDENCE_ANNEX"] = {
            "analysis_id":"SYN-01", "analysis_as_of":"2026-10-28",
            "observations":[self.source()]
        }
        pi = {
            "analysis_id":"SYN-01", "portfolio_as_of":"2026-10-28",
            "room_status":"ROOM_UNAVAILABLE", "summary":"Incomplete",
            "limitations":"Missing holdings", "forwarded_ir":deepcopy(ir),
        }
        copy = deepcopy((request, ir, pi))
        out = complete_manual_session(
            request, ir_capsule=ir, pi_delta=pi,
            valuation_inputs=self.valuation_inputs())
        self.assertEqual((request, ir, pi), copy)
        self.assertIn("Quotation provenance", out["final_report_private"])
        self.assertEqual(out["project_invocation"], "NONE")

    def test_cli_private_report_no_quote_locator_leak(self):
        request = dict(self.request(), ceo_initiated=True,
                       research_needed=True, portfolio_needed=False)
        ir = self.ir()
        ir["EVIDENCE_ANNEX"] = {
            "analysis_id":"SYN-01", "analysis_as_of":"2026-10-28",
            "observations":[self.source()]
        }
        payload = {"request":request, "ir_capsule":ir,
                   "valuation_inputs":self.valuation_inputs()}
        stdout, stderr = StringIO(), StringIO()
        code = main(["--output", "report"],
                    instream=StringIO(json.dumps(payload)),
                    outstream=stdout, errstream=stderr)
        self.assertEqual((code, stderr.getvalue()), (0, ""))
        self.assertIn("Quotation provenance", stdout.getvalue())
        self.assertNotIn("https://example.org/private-quote", stdout.getvalue())

    def test_report_rejects_forged_quote_price_certification_or_changed_ref(self):
        request, ir = self.request(), self.ir()
        result = assemble_manual_run(request, ir,
                                     valuation_inputs=self.valuation_inputs())
        base = {
            "kind":"DECISION", "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "strategy":"high-cagr", "method_version":"SYNTHETIC",
            "status":"CONDITIONAL", "objective":"Private test",
            "decision_line":"Not a recommendation",
            "summary":["Incomplete"], "facts":ir["facts"],
            "countercase":"Unverified", "limitations":"Unverified",
            "next_action":"Inspect",
            "valuation_scenarios_private": result["valuation_scenarios_private"],
            "valuation_quote_trace_private": result["valuation_quote_trace_private"],
        }
        for field, value in (
            ("original_market_price_verification", "VERIFIED"),
            ("market_price_or_fx_authority", "EXECUTION"),
            ("quote_reference_private", "OTHER_OBSERVATION"),
        ):
            with self.subTest(field=field):
                packet = deepcopy(base)
                packet["valuation_quote_trace_private"][field] = value
                with self.assertRaisesRegex(ValueError, "VALUATION_QUOTE_TRACE_AUTHORITY"):
                    render_report(packet)


if __name__ == "__main__":
    unittest.main()
