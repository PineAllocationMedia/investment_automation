import copy
import unittest
from ai_native.fundamental_dossier import prepare_fundamental_dossier


class FundamentalDossierTests(unittest.TestCase):
    def facts(self):
        obs=[]
        values={"REVENUE":("100","120"), "OPERATING_INCOME":("10","18"),
                "CFO":("20","25"), "CASH_CAPEX":("5","8"),
                "DILUTED_AVG_SHARES":("100","110")}
        for metric, pair in values.items():
            for i, value in enumerate(pair):
                y=2024+i
                obs.append(dict(observation_id=f"{metric}-{i}",fact_id=f"F-{metric}-{i}",
                    source_id=f"S-{metric}-{i}", economic_issuer="SYN-COMPANY", instrument="SYN:TSX",
                    metric=metric,period_start=f"{y}-01-01",period_end=f"{y}-12-31",
                    currency="CAD" if metric!="DILUTED_AVG_SHARES" else "N/A",
                    unit="M_CAD" if metric!="DILUTED_AVG_SHARES" else "M_SHARES",
                    definition_basis="IFRS",consolidation="GROUP",value=value,
                    source_kind="ISSUER_OR_REGULATOR",classification="SOURCE_FACT",
                    rights_status="PERMITTED",claim_use_status="CALLER_REPORTED_ONLY"))
        return obs
    def inputs(self):
        rows=self.facts(); ids=[r["fact_id"] for r in rows]
        return dict(analysis_id="SYN-01",analysis_as_of="2026-10-28",economic_issuer="SYN-COMPANY",
          instrument="SYN:TSX",source_annex={"analysis_id":"SYN-01","analysis_as_of":"2026-10-28",
                                            "observations_private":rows},
          period_pairs={metric:[f"{metric}-0",f"{metric}-1"] for metric in
                        ("REVENUE","OPERATING_INCOME","CFO","CASH_CAPEX","DILUTED_AVG_SHARES")},
          annual_periods_comparable_reported=True,
          qualitative_axes={name:dict(status="SPECIALIST_REPORTED",rationale="Synthetic observation",
                                      countercase="Might not persist",ir_fact_ids=[ids[0]]) for name in
                            ("COMPETITIVE_POSITION","REINVESTMENT","PERMANENT_LOSS")},
          original_ir_fact_ids=ids)
    def run_case(self,**changes):
        inputs=self.inputs();inputs.update(changes);return prepare_fundamental_dossier(**inputs)
    def test_descriptive_numbers_and_clear_non_owner_label(self):
        x=self.run_case();m=x["descriptive_metrics_private"]
        self.assertEqual(m["reported_revenue_change_pct"],"20.00")
        self.assertEqual(m["reported_operating_margin_pct"],["10.00","15.00"])
        self.assertEqual(m["cfo_less_cash_capex_descriptive"],["15","17"])
        self.assertEqual(m["diluted_share_count_change_pct"],"10.00")
        self.assertEqual(x["normalized_owner_earnings_status"],"NOT_ESTABLISHED")
    def test_organic_growth_not_inferred(self):
        x=self.run_case();self.assertIn("UNKNOWN",x["organic_growth_status"])
        self.assertEqual(x["expected_return_or_trade"],"NOT_ESTABLISHED")
    def test_source_only_caller_reported(self):
        x=self.run_case();self.assertIn("NOT_ORIGINAL_AUTHENTICATED",x["evidence_authority"])
        self.assertEqual(x["writes"],"NONE")
    def test_unknown_rights_block_derived_revenue_growth(self):
        i=self.inputs();i["source_annex"]["observations_private"][0]["rights_status"]="UNCERTAIN"
        x=prepare_fundamental_dossier(**i)
        self.assertNotIn("reported_revenue_change_pct",x["descriptive_metrics_private"])
        self.assertIn("SOURCE_NOT_USABLE",str(x["limitations"]))
    def test_secondary_source_cannot_corroborate_primary(self):
        i=self.inputs();i["source_annex"]["observations_private"][0]["source_kind"]="SECONDARY"
        x=prepare_fundamental_dossier(**i)
        self.assertNotIn("reported_revenue_change_pct",x["descriptive_metrics_private"])
    def test_annex_wrong_analysis_id_rejected(self):
        i=self.inputs();i["source_annex"]["analysis_id"]="DIFFERENT"
        with self.assertRaisesRegex(ValueError,"SOURCE_ANNEX_ID"):prepare_fundamental_dossier(**i)
    def test_cross_issuer_rejected(self):
        i=self.inputs();i["source_annex"]["observations_private"][1]["economic_issuer"]="OTHER"
        with self.assertRaisesRegex(ValueError,"IDENTITY_MISMATCH"):prepare_fundamental_dossier(**i)
    def test_pairing_unknown_source_rejected(self):
        i=self.inputs();i["period_pairs"]["REVENUE"]=["REVENUE-0","NOT-THERE"]
        with self.assertRaisesRegex(ValueError,"UNKNOWN_SOURCE_OBSERVATION_ID"):prepare_fundamental_dossier(**i)
    def test_source_fact_must_be_original_ir_id(self):
        i=self.inputs();i["original_ir_fact_ids"].remove("F-CFO-0")
        with self.assertRaisesRegex(ValueError,"SOURCE_FACT_NOT_IN_ORIGINAL_IR"):prepare_fundamental_dossier(**i)
    def test_mismatched_period_alignment_suppresses_margin(self):
        i=self.inputs();r=next(r for r in i["source_annex"]["observations_private"] if r["observation_id"]=="OPERATING_INCOME-1")
        r["period_end"]="2026-01-01"
        x=prepare_fundamental_dossier(**i)
        self.assertNotIn("reported_operating_margin_pct",x["descriptive_metrics_private"])
    def test_different_currency_suppresses_operating_margin(self):
        i=self.inputs()
        for r in i["source_annex"]["observations_private"]:
            if r["metric"]=="OPERATING_INCOME":r["currency"]="USD"
        self.assertNotIn("reported_operating_margin_pct",prepare_fundamental_dossier(**i)["descriptive_metrics_private"])
    def test_adjusted_basis_mismatch_blocks_growth(self):
        i=self.inputs();i["source_annex"]["observations_private"][1]["definition_basis"]="ADJUSTED"
        self.assertNotIn("reported_revenue_change_pct",prepare_fundamental_dossier(**i)["descriptive_metrics_private"])
    def test_unknown_period_comparability_blocks_all_quantification(self):
        x=self.run_case(annual_periods_comparable_reported=False)
        self.assertFalse(x["descriptive_metrics_private"])
    def test_negative_capex_sign_is_not_interpreted(self):
        i=self.inputs();r=next(r for r in i["source_annex"]["observations_private"] if r["observation_id"]=="CASH_CAPEX-0")
        r["value"]="-5"
        self.assertNotIn("cfo_less_cash_capex_descriptive",prepare_fundamental_dossier(**i)["descriptive_metrics_private"])
    def test_zero_revenue_denominator_blocks_margin_and_growth(self):
        i=self.inputs();r=next(r for r in i["source_annex"]["observations_private"] if r["observation_id"]=="REVENUE-0")
        r["value"]="0"
        x=prepare_fundamental_dossier(**i)
        self.assertNotIn("reported_revenue_change_pct",x["descriptive_metrics_private"])
        self.assertNotIn("reported_operating_margin_pct",x["descriptive_metrics_private"])
    def test_fiscal_period_length_guard(self):
        i=self.inputs();i["source_annex"]["observations_private"][0]["period_start"]="2024-05-01"
        x=prepare_fundamental_dossier(**i)
        self.assertNotIn("reported_revenue_change_pct",x["descriptive_metrics_private"])
    def test_no_data_mutation(self):
        i=self.inputs();before=copy.deepcopy(i);prepare_fundamental_dossier(**i)
        self.assertEqual(i,before)
    def test_missing_qualitative_axis_rejected(self):
        i=self.inputs();del i["qualitative_axes"]["PERMANENT_LOSS"]
        with self.assertRaisesRegex(ValueError,"EXACT_THREE"):prepare_fundamental_dossier(**i)
    def test_unknown_qualitative_axis_retained_as_gap(self):
        i=self.inputs();i["qualitative_axes"]["REINVESTMENT"]["status"]="UNKNOWN"
        x=prepare_fundamental_dossier(**i)
        self.assertIn("REINVESTMENT_NOT_EVIDENCED",x["limitations"])
    def test_evidence_false_verification_rejected(self):
        i=self.inputs();i["qualitative_axes"]["REINVESTMENT"]["status"]="BROKER_VERIFIED"
        with self.assertRaisesRegex(ValueError,"NO_AUTOMATIC"):prepare_fundamental_dossier(**i)


    def test_real_m2_fundamentals_feed_m4_report_without_quality_promotion(self):
        from ai_native.reporting import render_report
        d = prepare_fundamental_dossier(**self.inputs())
        packet = {
            "kind":"DECISION","analysis_id":"SYN-01","as_of":"2026-10-28",
            "strategy":"HIGH_CAGR_EXPLORATORY","method_version":"M2_SYN",
            "status":"CONDITIONAL","objective":"Synthetic issuer review",
            "decision_line":"Research incomplete", "summary":["No decision-grade recommendation"],
            "facts":[],"countercase":"Durability uncertain","limitations":"Original sources not independently authenticated",
            "next_action":"Verify sources","fundamental_dossier_private":d,
        }
        report = render_report(packet)
        self.assertIn("20.00%", report)
        self.assertIn("10.00% → 15.00%", report)
        self.assertIn("15 → 17 M_CAD (CAD)", report)
        self.assertIn("NOT ESTABLISHED", report)
        self.assertNotIn("normalized owner earnings: established", report)


    def test_post_ir_cc_metric_suppresses_retroactive_descriptive_arithmetic(self):
        data = self.inputs()
        for row in data["source_annex"]["observations_private"]:
            row["observed_at"] = "2026-10-27"
        data["source_annex"]["observations_private"][1]["observed_at"] = "2026-10-28"
        data["ir_research_as_of"] = "2026-10-27"
        before = copy.deepcopy(data)
        out = prepare_fundamental_dossier(**data)
        pair = out["metric_pairs_private"]["REVENUE"]
        self.assertEqual(pair["status"], "UNAVAILABLE")
        self.assertIn("SOURCE_OBSERVED_AFTER_ORIGINAL_IR", pair["reason_codes"])
        self.assertNotIn("reported_revenue_change_pct", out["descriptive_metrics_private"])
        self.assertNotIn("reported_operating_margin_pct", out["descriptive_metrics_private"])
        self.assertEqual(out["descriptive_metrics_private"]["diluted_share_count_change_pct"], "10.00")
        self.assertEqual(data, before)

    def test_same_day_original_ir_source_keeps_descriptive_arithmetic_only(self):
        data = self.inputs()
        for row in data["source_annex"]["observations_private"]:
            row["observed_at"] = "2026-10-27"
        out = prepare_fundamental_dossier(**dict(data, ir_research_as_of="2026-10-27"))
        self.assertEqual(out["descriptive_metrics_private"]["reported_revenue_change_pct"], "20.00")
        self.assertEqual(out["expected_return_or_trade"], "NOT_ESTABLISHED")

    def test_invalid_or_future_ir_cutoff_refused(self):
        for cutoff in ("2026-10-29", "2026-1-1", "BAD"):
            with self.subTest(cutoff=cutoff), self.assertRaisesRegex(
                ValueError, "FUNDAMENTAL_IR_CUTOFF_INVALID"):
                prepare_fundamental_dossier(**dict(self.inputs(), ir_research_as_of=cutoff))

    def test_missing_or_after_analysis_observation_refused_for_pair(self):
        for observed in (None, "2026-10-29"):
            data = self.inputs()
            for row in data["source_annex"]["observations_private"]:
                row["observed_at"] = "2026-10-27"
            data["source_annex"]["observations_private"][0]["observed_at"] = observed
            with self.subTest(observed=observed), self.assertRaisesRegex(
                ValueError, "FUNDAMENTAL_SOURCE_OBSERVATION_DATE_INVALID"):
                prepare_fundamental_dossier(**dict(data, ir_research_as_of="2026-10-27"))

if __name__ == '__main__': unittest.main()
