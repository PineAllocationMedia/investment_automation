import copy
import unittest
from ai_native.candidate_comparison import compare_candidates
from ai_native.source_fusion import assemble_source_fusion


class CandidateComparisonTests(unittest.TestCase):
    def item(self, name, security, price="100", values=("81", "121", "144"), currency="CAD"):
        scenarios = {}
        for label, val in zip(("BEAR", "BASE", "BULL"), values):
            scenarios[label] = dict(valuation_method="OTHER_EXPLICIT", assumption_basis="PAM_ASSUMPTION",
                rationale_ref=f"SYN-R-{name}-{label}", terminal_value_ref=f"SYN-T-{name}-{label}",
                terminal_price_per_share=val, annual_distributions_per_share=None)
        return dict(candidate_id=name, role="SECURITY", research_method_version="SYN-M1",
            research_status="SPECIALIST_REPORTED", portfolio_room_status="ROOM_CONDITIONAL",
            principal_failure_ref=f"SYN-FAIL-{name}", valuation_inputs=dict(analysis_id="SYN-C",
            analysis_as_of="2026-10-28", security_id=security, currency=currency, quoted_at="2026-10-27",
            quote_source_ref=f"SYN-Q-{name}", price_per_share=price, horizon_years=2,
            security_basis_confirmed_by_caller=True, currency_basis_confirmed_by_caller=True,
            scenarios=scenarios))

    def data(self):
        return dict(analysis_id="SYN-C",analysis_as_of="2026-10-28",strategy_id="EXPLORATORY",
            account_currency="CAD",candidates=[self.item("A","ABC:TSX"),self.item("B","DEF:TSX",values=("64","100","121"))])

    def run_comparison(self, **patch):
        d=self.data();d.update(patch)
        return compare_candidates(**d)

    def weighted_case(self, *, missing_probability=False, unknown_dividend=False,
                      unlinked_quote=False):
        """Synthetic IR candidates with two distinct quote-linked price traces.

        Even matched quotes are caller-reported, not independent authentication.
        """
        d = self.data()
        observations = []
        for item in d["candidates"]:
            val = item["valuation_inputs"]
            sec = val["security_id"]
            ref = "SYN-QOBS-" + item["candidate_id"]
            val["quote_source_ref"] = ref
            for row in val["scenarios"].values():
                row["annual_distributions_per_share"] = (
                    None if unknown_dividend
                    else [{"amount_per_share": "0", "source_ref": "SYN-ZERO-CASH"}] * 2
                )
            item["probability_inputs"] = {
                "analysis_id": "SYN-C", "analysis_as_of": "2026-10-28",
                "security_id": sec, "probability_basis": "PAM_ASSUMPTION",
                "probability_rationale_ref": "SYN-CALIBRATION-UNVERIFIED",
                "probabilities_pct": {"BEAR": "25", "BASE": "50", "BULL": "25"},
            }
            if not unlinked_quote:
                observations.append({
                    "observation_id": ref, "fact_id": "SYN-F-" + item["candidate_id"],
                    "source_id": "SYN-S-" + item["candidate_id"],
                    "economic_issuer": item["candidate_id"],
                    "instrument": sec, "metric": "MARKET_PRICE_PER_SHARE",
                    "period_start": "2026-10-27", "period_end": "2026-10-27",
                    "currency": val["currency"], "unit": "PER_SHARE",
                    "definition_basis": "EXCHANGE_LAST_REPORTED",
                    "consolidation": "SECURITY_CLASS", "value": "100",
                    "observed_at": "2026-10-28", "published_at": "2026-10-27",
                    "original_checked_at": "2026-10-28",
                    "source_kind": "SECONDARY", "classification": "SOURCE_FACT",
                    "source_locator": "https://example.org/synthetic-source",
                    "rights_status": "PERMITTED",
                    "verification_status": "INDICATIVE",
                })
        if missing_probability:
            del d["candidates"][1]["probability_inputs"]
        source = (assemble_source_fusion(
            analysis_id="SYN-C", analysis_as_of="2026-10-28",
            observations=observations) if observations else None)
        return d, source

    def test_weighted_cashflow_total_irr_spread_is_conditional_and_pre_cost(self):
        d, source = self.weighted_case()
        before = copy.deepcopy(d)
        result = compare_candidates(
            **d, source_annex=source, ir_research_as_of="2026-10-28")
        self.assertEqual(d, before)
        pair = result["pairwise_weighted_cashflow_private"][0]
        self.assertEqual(pair["status"], "CONDITIONAL_TOTAL_CASHFLOW_IRR_SPREAD_ONLY")
        self.assertEqual(pair["reason_codes"], [])
        self.assertEqual(pair["cost_fx_tax"], "NOT_EVALUATED")
        self.assertIsNotNone(pair["first_minus_second_pp"])
        self.assertEqual(result["probability_weighted_expected_return"], "NOT_ESTABLISHED")
        self.assertEqual(result["benchmark_expected_return"], "NOT_ESTABLISHED")
        self.assertEqual(result["forward_alpha_or_superiority"], "NOT_ESTABLISHED")
        self.assertEqual(result["recommendation_or_ranking"], "NOT_AUTHORIZED")
        # Lack of authenticated private account Room is a separate decision
        # dependency, not a blocker to comparison of economic *assumptions*.
        self.assertEqual(result["portfolio_allocation"], "NOT_CALCULATED")
        self.assertEqual(result["trading_authority"], "NONE_CEO_ONLY")
        from ai_native.reporting import render_report
        packet = dict(kind="DECISION", analysis_id="SYN-C", as_of="2026-10-28",
                      strategy="EXPLORATORY", method_version="SYNTHETIC",
                      status="CONDITIONAL", objective="Sourced model comparison",
                      decision_line="No return certification",
                      summary=["Assumptions only"], facts=[],
                      countercase="Probabilities and future returns may differ",
                      limitations="Original source not independently checked",
                      next_action="Verify authentic original sources",
                      candidate_comparison_private=result)
        text = render_report(packet)
        self.assertIn("Sensibilite du rendement total conditionnel", text)
        self.assertIn("IRR conditionnel des flux totaux", text)
        self.assertIn("NON calibr", text)
        self.assertIn("not ranked", text)

    def test_missing_or_unusable_weighted_evidence_stays_not_comparable(self):
        for variant in ("one_missing", "dividends_unknown", "unlinked_quote",
                        "fx_mismatch", "quote_date_mismatch", "unknown_research"):
            with self.subTest(variant=variant):
                d, src = self.weighted_case(
                    missing_probability=(variant == "one_missing"),
                    unknown_dividend=(variant == "dividends_unknown"),
                    unlinked_quote=(variant == "unlinked_quote"))
                if variant == "fx_mismatch":
                    d["candidates"][1]["valuation_inputs"]["currency"] = "USD"
                if variant == "quote_date_mismatch":
                    d["candidates"][1]["valuation_inputs"]["quoted_at"] = "2026-10-26"
                if variant == "unknown_research":
                    d["candidates"][1]["research_status"] = "UNKNOWN"
                # A changed price observation date would also require a changed
                # observation link. The comparator must not silently rewrite it.
                if variant in {"fx_mismatch", "quote_date_mismatch"}:
                    with self.assertRaises(ValueError):
                        compare_candidates(**d, source_annex=src,
                                           ir_research_as_of="2026-10-28")
                    continue
                result = compare_candidates(
                    **d, source_annex=src, ir_research_as_of="2026-10-28")
                pair = result["pairwise_weighted_cashflow_private"][0]
                self.assertEqual(pair["status"], "NOT_COMPARABLE")
                self.assertIsNone(pair["first_minus_second_pp"])
                self.assertTrue(pair["reason_codes"])

    def test_integrated_route_reports_quote_evidence_gap_without_source(self):
        from ai_native.integrated_flow import assemble_manual_run
        data, _source = self.weighted_case()
        request = {
            "analysis_id": "SYN-C", "as_of": "2026-10-28",
            "objective": "Synthetic economic comparison",
            "strategy_id": "EXPLORATORY", "kind": "DECISION",
            "method_version": "SYN-IR",
        }
        ir = {
            "analysis_id": "SYN-C", "research_as_of": "2026-10-28",
            "summary": ["Conditional probabilities and cashflow premises."],
            "facts": [{"id": "SYN-F", "status": "INDICATIVE",
                       "claim": "Synthetic data, no original quote verified."}],
            "limitations": "Source annex for both quotes absent.",
            "countercase": "Missing original quote evidence.",
            "decision_line": "No company preference established.",
            "next_action": "Obtain original date/currency quote sources.",
        }
        out = assemble_manual_run(
            request, ir, candidate_comparison_inputs=data,
        )
        result = out["candidate_comparison_private"]
        pair = result["pairwise_weighted_cashflow_private"][0]
        self.assertEqual(pair["status"], "NOT_COMPARABLE")
        self.assertIsNone(pair["first_minus_second_pp"])
        self.assertIn("WEIGHTED_CASHFLOW_EVIDENCE_UNAVAILABLE",
                      pair["reason_codes"])
        self.assertIn("Sensibilite du rendement total conditionnel",
                      out["markdown"])
        self.assertIn("NOT_COMPARABLE", out["markdown"])
        self.assertNotIn("SYN-CALIBRATION-UNVERIFIED", out["markdown"])

    def test_report_rejects_invented_conditional_alpha(self):
        from ai_native.reporting import render_report
        d, src = self.weighted_case()
        result = compare_candidates(
            **d, source_annex=src, ir_research_as_of="2026-10-28")
        packet = dict(kind="DECISION", analysis_id="SYN-C", as_of="2026-10-28",
                      strategy="EXPLORATORY", method_version="SYNTHETIC",
                      status="CONDITIONAL", objective="Synthetic",
                      decision_line="No investment admission",
                      summary=["Unverified"], facts=[],
                      countercase="No calibration", limitations="Unverified",
                      next_action="Verify", candidate_comparison_private=result)
        broken = copy.deepcopy(packet)
        broken["candidate_comparison_private"]["pairwise_weighted_cashflow_private"][0][
            "first_minus_second_pp"] = "999"
        with self.assertRaisesRegex(ValueError, "COMPARISON_WEIGHTED_SPREAD_MISMATCH"):
            render_report(broken)
        forged = copy.deepcopy(packet)
        forged["candidate_comparison_private"]["pairwise_weighted_cashflow_private"][0][
            "evidence_authority"] = "CERTIFIED_EXPECTED_ALPHA"
        with self.assertRaisesRegex(ValueError, "COMPARISON_WEIGHTED_PAIR_ID_OR_AUTHORITY_INVALID"):
            render_report(forged)

    def test_same_currency_price_scenario_differences(self):
        res=self.run_comparison()
        pair=res["pairwise_scenario_differences_private"][0]["by_scenario"]
        self.assertEqual(pair["BASE"]["delta_first_minus_second_pp"],"10.00")
        self.assertEqual(pair["BEAR"]["delta_first_minus_second_pp"],"10.00")
        self.assertEqual(pair["BASE"]["comparison_status"],"SCENARIO_ARITHMETIC_ONLY")
        self.assertIn("PRICE_ONLY_NOT_TOTAL_RETURN",pair["BASE"]["reason_codes"])

    def test_never_expected_return_alpha_or_ranking(self):
        o=self.run_comparison()
        self.assertEqual(o["forward_alpha_or_superiority"],"NOT_ESTABLISHED")
        self.assertEqual(o["recommendation_or_ranking"],"NOT_AUTHORIZED")
        self.assertEqual(o["portfolio_allocation"],"NOT_CALCULATED")
        self.assertEqual(o["trading_authority"],"NONE_CEO_ONLY")

    def test_foreign_currency_blocks_account_comparison(self):
        d=self.data();d["candidates"][1]["valuation_inputs"]["currency"]="USD"
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertEqual(p["comparison_status"],"NOT_COMPARABLE")
        self.assertIn("ACCOUNT_CURRENCY_FX_MODEL_MISSING",p["reason_codes"])

    def test_both_foreign_currency_still_blocked(self):
        d=self.data()
        for c in d["candidates"]: c["valuation_inputs"]["currency"]="USD"
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIsNone(p["delta_first_minus_second_pp"])

    def test_price_cagr_versus_dividend_irr_not_comparable(self):
        d=self.data()
        for v in d["candidates"][1]["valuation_inputs"]["scenarios"].values():
            v["annual_distributions_per_share"]=[{"amount_per_share":"0","source_ref":"SYN-Z"}]*2
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIn("RETURN_MEASURE_NOT_COMPARABLE",p["reason_codes"])
        self.assertIsNone(p["delta_first_minus_second_pp"])

    def test_two_irr_scenarios_are_arithmetic_only(self):
        d=self.data()
        for c in d["candidates"]:
            for v in c["valuation_inputs"]["scenarios"].values():
                v["annual_distributions_per_share"]=[{"amount_per_share":"0","source_ref":"SYN-Z"}]*2
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIn("YEAR_END_IRR_ASSUMPTIONS_UNVERIFIED",p["reason_codes"])
        self.assertEqual(p["delta_first_minus_second_pp"],"10.00")

    def test_inconsistent_bear_base_bull_blocks_comparison(self):
        d=self.data();d["candidates"][0]["valuation_inputs"]["scenarios"]["BEAR"]["terminal_price_per_share"]="225"
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIn("SCENARIO_ORDER_INCONSISTENT",p["reason_codes"])

    def test_candidate_count_guards(self):
        d=self.data()
        for items in ([],[d["candidates"][0]],d["candidates"]*4):
            with self.subTest(n=len(items)),self.assertRaisesRegex(ValueError,"COUNT_MUST_BE"):
                self.run_comparison(candidates=items)

    def test_duplicate_security_and_candidate_ids(self):
        d=self.data();d["candidates"][1]["candidate_id"]="A"
        with self.assertRaisesRegex(ValueError,"DUPLICATE_CANDIDATE_ID"):compare_candidates(**d)
        d=self.data();d["candidates"][1]["valuation_inputs"]["security_id"]="ABC:TSX"
        with self.assertRaisesRegex(ValueError,"DUPLICATE_SECURITY_ID"):compare_candidates(**d)

    def test_wrong_analysis_id_and_asof_not_silently_mixed(self):
        for key,val in (("analysis_id","OTHER"),("analysis_as_of","2026-10-27")):
            d=self.data();d["candidates"][1]["valuation_inputs"][key]=val
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"ID_OR_DATE_MISMATCH"):
                compare_candidates(**d)

    def test_quote_dates_must_match_for_spread(self):
        d=self.data();d["candidates"][1]["valuation_inputs"]["quoted_at"]="2026-10-26"
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIn("QUOTE_OBSERVATION_DATE_MISMATCH",p["reason_codes"])
        self.assertIsNone(p["delta_first_minus_second_pp"])

    def test_intra_candidate_mixed_measures_block_spreads(self):
        d=self.data()
        row=d["candidates"][1]["valuation_inputs"]["scenarios"]["BEAR"]
        row["annual_distributions_per_share"]=[{"amount_per_share":"0","source_ref":"SYN-Z"}]*2
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertIn("INTRA_CANDIDATE_RETURN_MEASURES_INCONSISTENT",p["reason_codes"])

    def test_different_horizon_rejected(self):
        d=self.data();d["candidates"][1]["valuation_inputs"]["horizon_years"]=3
        with self.assertRaisesRegex(ValueError,"SAME_HORIZON"):compare_candidates(**d)

    def test_incompatible_share_basis_yields_no_spread(self):
        d=self.data();d["candidates"][1]["valuation_inputs"]["security_basis_confirmed_by_caller"]=False
        p=compare_candidates(**d)["pairwise_scenario_differences_private"][0]["by_scenario"]["BASE"]
        self.assertEqual(p["comparison_status"],"NOT_COMPARABLE")

    def test_reference_etf_does_not_acquire_vfv_expected_return(self):
        d=self.data();d["candidates"][1]["role"]="REFERENCE_ETF"
        o=compare_candidates(**d)
        self.assertEqual(o["benchmark_expected_return"],"NOT_ESTABLISHED")
        self.assertEqual(o["candidates_private"][1]["role"],"REFERENCE_ETF")

    def test_unknown_research_and_room_remain_unknown(self):
        d=self.data();d["candidates"][1]["research_status"]="UNKNOWN"
        d["candidates"][1]["portfolio_room_status"]="NOT_EVALUATED"
        x=compare_candidates(**d)["candidates_private"][1]
        self.assertIn("RESEARCH_STATUS_UNKNOWN",x["qualification_codes"])
        self.assertIn("PORTFOLIO_ROOM_UNAVAILABLE_OR_NOT_EVALUATED",x["qualification_codes"])

    def test_cannot_assert_evidence_supported_from_comparator(self):
        d=self.data();d["candidates"][1]["portfolio_room_status"]="ROOM_EVIDENCE_SUPPORTED"
        with self.assertRaisesRegex(ValueError,"MUST_NOT_BE_CERTIFIED"): compare_candidates(**d)

    def test_three_way_pairwise_count_no_implicit_rank(self):
        d=self.data();d["candidates"].append(self.item("C","GHI:TSX",values=("49","81","100")))
        r=compare_candidates(**d)
        self.assertEqual(len(r["pairwise_scenario_differences_private"]),3)
        self.assertEqual(r["recommendation_or_ranking"], "NOT_AUTHORIZED")

    def test_exact_input_unchanged(self):
        d=self.data();before=copy.deepcopy(d)
        compare_candidates(**d)
        self.assertEqual(d,before)

    def test_no_source_fetch_or_writes(self):
        o=self.run_comparison()
        self.assertEqual(o["source_authentication"],"NOT_PERFORMED")
        self.assertEqual(o["writes"],"NONE")


    def test_real_comparator_to_report_is_conditional_not_authorized(self):
        from ai_native.reporting import render_report
        item=self.run_comparison()
        packet={"kind":"DECISION","analysis_id":"SYN-C","as_of":"2026-10-28",
                "strategy":"EXPLORATORY","method_version":"M2_SYN","status":"CONDITIONAL",
                "objective":"Synthetic comparison","decision_line":"No authorized ranking",
                "summary":["Unverified premises"],"facts":[],
                "countercase":"Cashflow assumptions are not certified",
                "limitations":"Original-source checks missing","next_action":"Check sources",
                "candidate_comparison_private":item}
        report=render_report(packet)
        self.assertIn("BASE: 10.00 pp",report)
        self.assertIn("not ranked",report)
        self.assertNotIn("SYN-FAIL",report)
        self.assertNotIn("SYN-R-",report)

if __name__ == "__main__": unittest.main()
