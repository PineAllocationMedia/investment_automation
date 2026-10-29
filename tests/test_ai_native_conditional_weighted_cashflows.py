"""Synthetic conditional cash-flow sensitivity tests, never real valuation acceptance."""
from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
import unittest

from ai_native.conditional_weighted_cashflows import calculate_weighted_cashflows
from ai_native.valuation_scenarios import evaluate_valuation_scenarios
from ai_native.valuation_quote_trace import trace_valuation_quote
from ai_native.source_fusion import assemble_source_fusion
from ai_native.integrated_flow import assemble_manual_run
from ai_native.manual_review_queue import prepare_manual_review_queue
from ai_native.session_bridge import complete_manual_session
from ai_native.reporting import render_report
from scripts.r1_manual_session_cli import main
from tests.test_ai_native_valuation_scenarios import ScenarioTests


class ConditionalWeightedCashflowsTests(unittest.TestCase):
    def setUp(self):
        self.fx = ScenarioTests()

    @staticmethod
    def weights(**changes):
        w = {"BEAR":"25", "BASE":"50", "BULL":"25"}
        w.update(changes)
        return {
            "analysis_id":"SYN-01", "analysis_as_of":"2026-10-28",
            "security_id":"ABC:TSX", "probability_basis":"PAM_ASSUMPTION",
            "probability_rationale_ref":"SYN-ANALYST-JUDGMENT",
            "probabilities_pct":w,
        }

    @staticmethod
    def source():
        return dict(
            observation_id="QUOTE-O1", fact_id="QUOTE-F1",
            source_id="QUOTE-S1", economic_issuer="SYN",
            instrument="ABC:TSX", metric="MARKET_PRICE_PER_SHARE",
            period_start="2026-10-28", period_end="2026-10-28",
            currency="CAD", unit="PER_SHARE",
            definition_basis="EXCHANGE_LAST_REPORTED",
            consolidation="SECURITY_CLASS", value="100",
            observed_at="2026-10-28", published_at="2026-10-28",
            original_checked_at="2026-10-28", source_kind="SECONDARY",
            classification="SOURCE_FACT",
            source_locator="https://example.org/syn-source",
            rights_status="PERMITTED", verification_status="INDICATIVE")

    def inputs(self):
        return self.fx.setup_case(analysis_id="SYN-01",
                                  quote_source_ref="QUOTE-O1")

    def checked(self, inputs=None, *, source=True, **probability_changes):
        inputs = self.inputs() if inputs is None else inputs
        scenarios = evaluate_valuation_scenarios(**inputs)
        annex = (assemble_source_fusion(
            analysis_id="SYN-01", analysis_as_of="2026-10-28",
            observations=[self.source()]) if source else None)
        quote = trace_valuation_quote(
            valuation=scenarios, source_annex=annex,
            ir_research_as_of="2026-10-28")
        return calculate_weighted_cashflows(
            valuation_inputs=inputs,
            valuation_scenarios=scenarios,
            quote_trace=quote,
            probability_inputs=self.weights(**probability_changes))

    def request(self, *, pi=False):
        return {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "ceo_initiated":True, "research_needed":True,
            "portfolio_needed":pi, "kind":"DECISION",
            "objective":"Synthetic valuation proof",
            "strategy_id":"high-cagr",
            "ir_method_version":"SYNTHETIC",
        }

    def ir(self, *, source=True):
        result={
            "analysis_id":"SYN-01", "research_as_of":"2026-10-28",
            "summary":["Synthetic accounting and valuation assumptions."],
            "facts":[{"id":"QUOTE-F1","status":"INDICATIVE",
                      "claim":"Synthetic quote to be independently checked."}],
            "limitations":"Original quote not authenticated.",
            "countercase":"Estimates and distributions may be wrong.",
            "decision_line":"No investment authorization.",
            "next_action":"Review original quote and distributions.",
        }
        if source:
            result["EVIDENCE_ANNEX"]={
                "analysis_id":"SYN-01", "analysis_as_of":"2026-10-28",
                "observations":[self.source()]}
        return result

    def test_weighted_terminal_cagr_is_not_average_of_individual_cagrs(self):
        result=self.checked()
        self.assertEqual(result["status"],"CONDITIONAL_CASHFLOW_MODEL_NOT_CERTIFIED")
        self.assertEqual(result["measure"],"WEIGHTED_TERMINAL_PRICE_ONLY_CAGR_DISTRIBUTIONS_UNKNOWN")
        self.assertEqual(result["conditional_annualized_pct"],"8.05")
        self.assertEqual(result["probability_calibration"],"NOT_PERFORMED")
        self.assertEqual(result["model_expected_return_authority"],"NOT_CERTIFIED")
        self.assertEqual(result["vfv_alpha"],"NOT_ESTABLISHED")
        self.assertEqual(result["trading_authority"],"NONE")

    def test_total_cashflows_zero_dividends_uses_weighted_cashflow_irr(self):
        inputs=self.inputs()
        for row in inputs["scenarios"].values():
            row["annual_distributions_per_share"]=[
                {"amount_per_share":"0","source_ref":"SYN-ZERO"}]*2
        result=self.checked(inputs)
        self.assertEqual(result["conditional_annualized_pct"],"8.05")
        self.assertEqual(result["measure"],"IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR")

    def test_positive_dividends_change_weighted_irr(self):
        inputs=self.inputs()
        for row in inputs["scenarios"].values():
            row["annual_distributions_per_share"]=[
                {"amount_per_share":"5","source_ref":"SYN-1"},
                {"amount_per_share":"5","source_ref":"SYN-2"}]
        result=self.checked(inputs)
        self.assertEqual(result["measure"],"IRR_ON_WEIGHTED_YEAR_END_CASHFLOWS_NOT_MEAN_IRR")
        self.assertGreater(float(result["conditional_annualized_pct"]),8.05)

    def test_all_zero_terminals_and_zero_distributions_minus_100(self):
        inputs=self.inputs()
        for row in inputs["scenarios"].values():
            row["terminal_price_per_share"]="0"
            row["annual_distributions_per_share"]=[
                {"amount_per_share":"0","source_ref":"SYN-ZERO"}]*2
        self.assertEqual(self.checked(inputs)["conditional_annualized_pct"],"-100.00")

    def test_unknown_distributions_cannot_be_implicitly_zero(self):
        inputs=self.inputs()
        inputs["scenarios"]["BEAR"]["annual_distributions_per_share"]=[
            {"amount_per_share":"0","source_ref":"SYN-ZERO"}]*2
        result=self.checked(inputs)
        self.assertEqual(result["measure"],"UNAVAILABLE")
        self.assertIsNone(result["conditional_annualized_pct"])
        self.assertIn("MIXED_DISTRIBUTION_KNOWLEDGE",result["reason_codes"])

    def test_unlinked_quote_never_approves_weighted_return(self):
        result=self.checked(source=False)
        self.assertEqual(result["measure"],"UNAVAILABLE")
        self.assertIn("ORIGINAL_QUOTE_EVIDENCE_UNRESOLVED",result["reason_codes"])

    def test_uncertain_security_currency_basis_never_approves_weighted_return(self):
        inputs=self.inputs()
        inputs["currency_basis_confirmed_by_caller"]=False
        result=self.checked(inputs)
        self.assertEqual(result["measure"],"UNAVAILABLE")
        self.assertIn("SCENARIO_SECURITY_OR_CURRENCY_BASIS_UNCONFIRMED",result["reason_codes"])

    def test_invalid_missing_unbounded_probabilities_rejected(self):
        for bad in [
            {"BEAR":"10","BASE":"50","BULL":"25"},
            {"BEAR":"-1","BASE":"76","BULL":"25"},
            {"BEAR":"NaN","BASE":"50","BULL":"25"},
            {"BEAR":25,"BASE":"50","BULL":"25"},
            {"BEAR":"0.0000001","BASE":"99.9999999","BULL":"0"},
            {"BEAR":"125","BASE":"-50","BULL":"25"},
            {"BEAR":"25","BASE":"50"},
            {"BEAR":"0","BASE":"0","BULL":"0"},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                args=self.weights()
                args["probabilities_pct"]=bad
                inputs=self.inputs()
                valuation=evaluate_valuation_scenarios(**inputs)
                quote=trace_valuation_quote(
                    valuation=valuation, source_annex=None,
                    ir_research_as_of="2026-10-28")
                calculate_weighted_cashflows(
                    valuation_inputs=inputs,
                    valuation_scenarios=valuation,
                    quote_trace=quote, probability_inputs=args)

    def test_probability_context_and_price_tampering_rejected(self):
        inputs=self.inputs()
        valuation=evaluate_valuation_scenarios(**inputs)
        quote=trace_valuation_quote(valuation=valuation, source_annex=None,
                                    ir_research_as_of="2026-10-28")
        for name,val in [
            ("security_id","WRONG"), ("analysis_id","WRONG"),
            ("analysis_as_of","2026-10-29"),
            ("probability_basis","CERTIFIED_PROBABILITY"),
        ]:
            with self.subTest(field=name), self.assertRaises(ValueError):
                p=self.weights()
                p[name]=val
                calculate_weighted_cashflows(
                    valuation_inputs=inputs, valuation_scenarios=valuation,
                    quote_trace=quote, probability_inputs=p)
        altered=deepcopy(valuation)
        altered["scenarios_private"]["BASE"]["terminal_price_per_share"]="122"
        with self.assertRaisesRegex(ValueError,"TERMINAL_MISMATCH"):
            calculate_weighted_cashflows(
                valuation_inputs=inputs,valuation_scenarios=altered,
                quote_trace=quote,probability_inputs=self.weights())

    def test_quote_authority_upgrade_rejected(self):
        inputs=self.inputs()
        valuation=evaluate_valuation_scenarios(**inputs)
        quote=trace_valuation_quote(valuation=valuation, source_annex=None,
                                    ir_research_as_of="2026-10-28")
        quote["original_market_price_verification"]="INDEPENDENTLY_VERIFIED"
        with self.assertRaisesRegex(ValueError,"QUOTE_TRACE_AUTHORITY_INVALID"):
            calculate_weighted_cashflows(
                valuation_inputs=inputs,valuation_scenarios=valuation,
                quote_trace=quote,probability_inputs=self.weights())

    def test_optional_model_preserves_existing_scenarios_when_absent(self):
        req = {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "objective":"Synthetic standalone", "strategy_id":"high-cagr",
            "kind":"DECISION","method_version":"SYNTHETIC"}
        out=assemble_manual_run(req,self.ir(),valuation_inputs=self.inputs())
        self.assertIsNone(out["weighted_cashflow_model_private"])
        self.assertNotIn("Analyst-supplied probability sensitivity",out["markdown"])

    def test_ir_report_available_only_as_conditional_and_private(self):
        req = {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "objective":"Synthetic standalone", "strategy_id":"high-cagr",
            "kind":"DECISION","method_version":"SYNTHETIC"}
        inputs, prob = self.inputs(), self.weights()
        saved=deepcopy((req,inputs,prob))
        out=assemble_manual_run(req,self.ir(),valuation_inputs=inputs,
                                probability_inputs=prob)
        self.assertEqual((req,inputs,prob),saved)
        self.assertEqual(out["weighted_cashflow_model_private"]["conditional_annualized_pct"],"8.05")
        self.assertIn("Conditional weighted cash-flow sensitivity: 8.05%",out["markdown"])
        self.assertIn("NOT certified Expected Return",out["markdown"])
        self.assertIn("distributions UNKNOWN",out["markdown"])
        self.assertNotIn("SYN-ANALYST-JUDGMENT",out["markdown"])
        self.assertNotIn("https://example.org/syn-source",out["markdown"])
        self.assertNotIn("8.05",str(out["memory_proposal_nonprivate"]))

    def test_missing_quote_evidence_stays_unavailable_in_report(self):
        req = {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "objective":"Synthetic standalone", "strategy_id":"high-cagr",
            "kind":"DECISION","method_version":"SYNTHETIC"}
        out=assemble_manual_run(req,self.ir(source=False),
                                valuation_inputs=self.inputs(),
                                probability_inputs=self.weights())
        self.assertIn("weighted cash-flow sensitivity: UNAVAILABLE",out["markdown"])
        self.assertNotIn("weighted cash-flow sensitivity: 8.05%",out["markdown"])

    def test_manual_cli_and_operator_queue_have_no_private_source_ids(self):
        payload={"request":self.request(),"ir_capsule":self.ir(),
                 "valuation_inputs":self.inputs(),"probability_inputs":self.weights()}
        stdin=StringIO(json.dumps(payload))
        stdout,stderr=StringIO(),StringIO()
        status=main(["--output","report"],instream=stdin,
                    outstream=stdout,errstream=stderr)
        self.assertEqual((status,stderr.getvalue()),(0,""))
        self.assertIn("8.05%",stdout.getvalue())
        self.assertNotIn("SYN-ANALYST-JUDGMENT",stdout.getvalue())
        session=complete_manual_session(
            payload["request"],ir_capsule=payload["ir_capsule"],
            valuation_inputs=payload["valuation_inputs"],
            probability_inputs=payload["probability_inputs"])
        queue=prepare_manual_review_queue(session)
        self.assertIn("CHECK_SCENARIO_PROBABILITIES",
                      [row["code"] for row in queue["items"]])
        self.assertNotIn("QUOTE-O1",json.dumps(queue))
        self.assertEqual(queue["readiness"],"NOT_EVALUATED")

    def test_pi_only_path_rejects_probability_specification(self):
        with self.assertRaisesRegex(ValueError,"PROBABILITY_CASHFLOWS_REQUIRE_IR_VALUATION"):
            complete_manual_session({
                "analysis_id":"SYN-01","as_of":"2026-10-28",
                "ceo_initiated":True,"portfolio_needed":True,"research_needed":False,
                "objective":"PI only","kind":"DECISION"},
                probability_inputs=self.weights(), valuation_inputs=self.inputs())

    def test_report_rejects_tampered_probability_authority_and_return(self):
        req = {
            "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "objective":"Synthetic standalone", "strategy_id":"high-cagr",
            "kind":"DECISION","method_version":"SYNTHETIC"}
        assembled=assemble_manual_run(req,self.ir(),valuation_inputs=self.inputs(),
                                      probability_inputs=self.weights())
        # The renderer is fed only a locally assembled PRIVATE packet, never a
        # caller-proclaimed change to model authority.
        packet={
            "kind":"DECISION", "analysis_id":"SYN-01", "as_of":"2026-10-28",
            "strategy":"high-cagr", "method_version":"SYNTHETIC",
            "status":"CONDITIONAL", "objective":"Synthetic standalone",
            "decision_line":"No authority", "summary":["Synthetic"],
            "facts":self.ir()["facts"], "countercase":"Assumptions",
            "limitations":"Unverified", "next_action":"Review",
            "valuation_scenarios_private":assembled["valuation_scenarios_private"],
            "valuation_quote_trace_private":assembled["valuation_quote_trace_private"],
            "weighted_cashflow_model_private":assembled["weighted_cashflow_model_private"],
        }
        for key, val in [
            ("probability_calibration","CERTIFIED"),
            ("model_expected_return_authority","ADMITTED"),
            ("vfv_alpha","POSITIVE_VERIFIED"),
            ("conditional_annualized_pct","NaN"),
            ("conditional_annualized_pct","999999999999999999"),
        ]:
            with self.subTest(field=key), self.assertRaises(ValueError):
                copy=deepcopy(packet)
                copy["weighted_cashflow_model_private"][key]=val
                render_report(copy)


if __name__ == "__main__":
    unittest.main()
