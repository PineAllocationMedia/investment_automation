import unittest

from src.report_generator import (
    account_performance_rows_for_report,
    account_performance_indicator_legend_rows,
    allocation_justification_rows_for_report,
    allocation_recommendation_narrative,
    auto_estimate_rows_for_output,
    _weakest_core_compact_alert_lines,
    promotion_recommendation_rows,
    sell_recommendation_narrative_lines,
    source_rows_for_report,
    true_missing_data_rows,
)


class ReportGeneratorTest(unittest.TestCase):
    def test_account_performance_indicator_legend_explains_key_metrics(self):
        rows = account_performance_indicator_legend_rows()
        indicators = {row["indicateur"] for row in rows}

        self.assertIn("portfolio_twr", indicators)
        self.assertIn("twr_excess_vs_sp500", indicators)
        self.assertIn("preferred_performance_summary", indicators)
        self.assertTrue(all(row["à quoi ça sert"] for row in rows))
        self.assertTrue(all(row["comment l’interpréter"] for row in rows))

    def test_account_performance_hides_simple_return_when_flows_distort_it(self):
        rows = account_performance_rows_for_report(
            [
                {
                    "account_type": "TFSA2",
                    "current_value_cad": 771.37,
                    "acquisition_value_cad": 792.32,
                    "unrealized_gain_percent": -0.026441,
                    "tracking_start_date": "2026-05-15",
                    "portfolio_return_since_tracking": 0.438721,
                    "sp500_return_since_tracking": 0.007254,
                    "excess_return_vs_sp500": 0.431466,
                    "portfolio_twr": -0.025,
                    "sp500_twr": 0.007254,
                    "twr_excess_vs_sp500": -0.032254,
                    "twr_status": "TWR_FLOW_ADJUSTED_BEHIND_SP500",
                    "portfolio_xirr": -0.583552,
                    "sp500_xirr": 0.537148,
                    "xirr_excess_vs_sp500": -1.1207,
                    "xirr_status": "XIRR_AVAILABLE_SHORT_HISTORY",
                    "external_flows_cad": 248.45,
                    "sp500_equivalent_value_cad": 791.19,
                    "value_added_vs_sp500_cad": -19.82,
                    "value_added_vs_sp500_percent": -0.02505,
                    "flow_adjusted_status": "BEHIND_SP500_FLOW_ADJUSTED",
                    "comparison_status": "APPROXIMATE_CONTRIBUTIONS_CHANGED",
                    "simple_return_status": "FLOW_DISTORTED_BY_CONTRIBUTIONS",
                    "preferred_performance_summary": "Lecture recommandée: ajusté des cotisations/retraits.",
                    "interpretation": "Comparaison approximative.",
                }
            ]
        )

        self.assertEqual(rows[0]["portfolio_return_since_tracking"], "N/D (flux détectés)")
        self.assertEqual(rows[0]["excess_return_vs_sp500"], "N/D (flux détectés)")
        self.assertEqual(rows[0]["sp500_return_since_tracking"], "0.7 %")
        self.assertEqual(rows[0]["twr_excess_vs_sp500"], "-3.2 %")
        self.assertEqual(rows[0]["value_added_vs_sp500_percent"], "-2.5 %")

    def test_source_rows_include_yfinance_and_local_files(self):
        analyses = {
            "MSFT": {
                "ticker": "MSFT",
                "ticker_display": "MSFT",
                "source": "yfinance",
                "data_source_notes": ["yfinance history (10y)", "yfinance info"],
            }
        }

        rows = source_rows_for_report(analyses, {}, {})

        sources = [row["source"] for row in rows]
        self.assertIn("Yahoo Finance via yfinance", sources)
        self.assertIn("Fichiers locaux utilisateur", sources)
        self.assertIn("Configuration locale de l’agent", sources)
        self.assertIn("Historique local", sources)
        self.assertIn("MSFT", rows[0]["éléments consultés"])

    def test_data_gaps_are_split_from_auto_estimates(self):
        rows = [
            {"ticker": "MSFT", "data_field": "C4: moat_clear", "importance": "HIGH", "impact": "missing"},
            {"ticker": "MSFT", "data_field": "AUTO_ESTIMATE: fair_value", "importance": "MEDIUM", "impact": "proxy"},
        ]

        true_missing = true_missing_data_rows(rows)
        auto_estimates = auto_estimate_rows_for_output(rows)

        self.assertEqual(len(true_missing), 1)
        self.assertEqual(true_missing[0]["data_field"], "C4: moat_clear")
        self.assertEqual(len(auto_estimates), 1)
        self.assertEqual(auto_estimates[0]["data_field"], "fair_value")

    def test_promotion_recommendations_show_none_when_no_strict_promotion_exists(self):
        rows = [
            {"ticker": "NVDA", "promotion_status": "STRONG_WATCH_ONLY"},
            {"ticker": "ROK", "promotion_status": "WAIT_FOR_BETTER_DATA_OR_PRICE"},
        ]

        result = promotion_recommendation_rows(rows)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["promotion_status"], "AUCUNE_PROMOTION_FONDEE")

    def test_promotion_recommendations_keep_only_real_promotions(self):
        promoted = {"ticker": "NVDA", "promotion_status": "PROMOTE_TO_CORE_REVIEW"}
        rejected = {"ticker": "ROK", "promotion_status": "DO_NOT_PROMOTE"}

        result = promotion_recommendation_rows([rejected, promoted])

        self.assertEqual(result, [promoted])

    def test_compact_weakest_core_alert_only_when_audit_differs(self):
        same = _weakest_core_compact_alert_lines(
            [{"current_weakest_ticker": "AAPL", "candidate_weakest_ticker": "AAPL", "same_result": True}]
        )
        different = _weakest_core_compact_alert_lines(
            [
                {
                    "audit_status": "OBSERVE_ONLY",
                    "current_weakest_ticker": "APP",
                    "candidate_weakest_ticker": "TSLA",
                    "same_result": False,
                    "interpretation": "Comparer avant activation.",
                }
            ]
        )

        self.assertEqual(same, [])
        self.assertEqual(len(different), 1)
        self.assertIn("AUDIT-ONLY — aucune recommandation modifiée", different[0])
        self.assertIn("APP", different[0])
        self.assertIn("TSLA", different[0])

    def test_allocation_justification_explains_selected_ticker_amount_and_history(self):
        rows = allocation_justification_rows_for_report(
            [{"ticker": "MSFT", "amount": 120, "percentage": 0.24, "reason": "Score supérieur.", "allocation_type": "Bloc 1"}],
            {
                "MSFT": {
                    "capital_allocation_score": 88,
                    "expected_cagr_quality": "HIGH",
                    "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "allocation_decision": "BUY_ADD",
                    "add_eligibility_size": "STRONG",
                }
            },
            [
                {
                    "ticker": "MSFT",
                    "previous_amount": 80,
                    "current_amount": 120,
                    "change_amount": 40,
                    "change_status": "INCREASED",
                    "main_explanation": "Score amélioré.",
                }
            ],
            [
                {
                    "date": "2026-06-12",
                    "ticker": "MSFT",
                    "account_type": "TFSA1",
                    "change_type": "ADD",
                    "shares_change": 1,
                    "estimated_change_value_cad": 500,
                }
            ],
            [],
        )

        self.assertEqual(rows[0]["ticker"], "MSFT")
        self.assertIn("120.00 $", rows[0]["montant"])
        self.assertIn("score d’allocation 88.0/100", rows[0]["pourquoi_ce_titre"])
        self.assertIn("Bloc 1", rows[0]["pourquoi_ce_montant"])
        self.assertIn("Avant: 80.00 $", rows[0]["vs_dernière_recommandation"])
        self.assertIn("ADD sur MSFT dans TFSA1", rows[0]["lien_avec_portefeuille"])

    def test_allocation_justification_uses_baseline_when_no_real_change_exists(self):
        rows = allocation_justification_rows_for_report(
            [{"ticker": "GOOGL", "amount": 100, "percentage": 0.2, "reason": "Admissible."}],
            {},
            [],
            [],
            [{"date": "2026-05-12", "ticker": "GOOGL", "account_type": "TFSA2", "change_type": "BASELINE"}],
        )

        self.assertIn("Historique initial seulement", rows[0]["lien_avec_portefeuille"])

    def test_allocation_recommendation_narrative_excludes_vfv_and_explains_selected_core(self):
        text = allocation_recommendation_narrative(
            [
                {"ticker": "VFV.TO", "amount": 50, "percentage": 0.1, "reason": "Filet."},
                {"ticker": "MSFT", "amount": 250, "percentage": 0.5, "reason": "Bloc principal.", "allocation_type": "Bloc 1"},
                {"ticker": "GOOGL", "amount": 200, "percentage": 0.4, "reason": "Bloc 2.", "allocation_type": "Bloc 2"},
            ],
            {
                "MSFT": {
                    "company_name_found": "Microsoft Corporation",
                    "capital_allocation_score": 91,
                    "conviction_score": 88,
                    "expected_cagr_quality": "VERY_HIGH",
                    "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
                    "market_growth_thesis_status": "STRUCTURAL_TAILWIND",
                    "cash_flow_quality_status": "STRONG",
                    "shareholder_discipline_status": "DISCIPLINED",
                    "cycle_bubble_risk_level": "MODERATE",
                    "data_reliability_level": "HIGH",
                    "moat_clear": True,
                },
                "GOOGL": {
                    "company_name_found": "Alphabet Inc.",
                    "capital_allocation_score": 86,
                    "conviction_score": 84,
                    "expected_cagr_quality": "HIGH",
                    "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "long_term_durability_status": "VERY_DURABLE_COMPOUNDER",
                    "market_growth_thesis_status": "STRUCTURAL_TAILWIND",
                    "cash_flow_quality_status": "STRONG",
                    "shareholder_discipline_status": "DISCIPLINED",
                    "cycle_bubble_risk_level": "MODERATE",
                    "data_reliability_level": "HIGH",
                    "moat_clear": True,
                },
            },
            [{"ticker": "MSFT", "previous_amount": 125, "current_amount": 250, "change_status": "INCREASED"}],
        )

        self.assertIn("MSFT (Microsoft Corporation) reçoit 250.00 $", text)
        self.assertIn("GOOGL (Alphabet Inc.) reçoit 200.00 $", text)
        self.assertIn("VFV.TO, la cotisation va vers", text)
        self.assertNotIn("VFV.TO reçoit", text)
        self.assertIn("profil haut CAGR 15-30 ans", text)
        self.assertIn("gestion", text.lower())
        self.assertIn("secteur", text.lower())
        self.assertIn("moat", text.lower())
        self.assertIn("plateforme de recherche", text.lower())

    def test_sell_recommendation_narrative_only_appears_for_real_sell_signals(self):
        no_sell = sell_recommendation_narrative_lines(
            {
                "MSFT": {
                    "ticker": "MSFT",
                    "sell_status": "GREEN",
                    "sell_decision": "HOLD",
                    "recommended_action": "HOLD",
                }
            }
        )
        self.assertEqual(no_sell, [])

        lines = sell_recommendation_narrative_lines(
            {
                "BAM": {
                    "ticker": "BAM",
                    "company_name_found": "Brookfield Asset Management",
                    "sell_status": "ORANGE",
                    "liquidation_status": "ORANGE",
                    "sell_decision": "REVIEW_TRIM_25",
                    "recommended_action": "REVIEW_TRIM_25",
                    "mechanical_sell_signal": "TRIM_25",
                    "thesis_status": "WEAKENING",
                    "confirmed_fundamental_sell_signals": ["Fondamental confirmé: marge sous pression."],
                    "technical_or_valuation_signals": ["Alerte technique: prix sous SMA 200."],
                    "liquidation_reasons": ["Fondamental confirmé: marge sous pression."],
                    "business_profile_label": "Alternative Asset Manager",
                    "management_quality_good": False,
                    "balance_sheet_strong": False,
                    "moat_clear": False,
                    "data_reliability_level": "HIGH",
                }
            }
        )

        text = "\n".join(lines)
        self.assertIn("Justification détaillée des ventes recommandées", text)
        self.assertIn("BAM (Brookfield Asset Management)", text)
        self.assertIn("REVIEW_TRIM_25", text)
        self.assertIn("marge sous pression", text)


if __name__ == "__main__":
    unittest.main()
