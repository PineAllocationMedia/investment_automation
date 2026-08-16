import unittest
from unittest.mock import patch

from src.report_formatters import (
    build_compact_data_reliability_section,
    build_compact_decision_section,
    build_compact_external_monitoring_section,
    build_compact_model_health_section,
    build_compact_portfolio_section,
    build_decision_quality_compact_lines,
    build_ranking_section,
    build_triage_header,
)


class ReportFormattersTest(unittest.TestCase):
    def test_decision_quality_capital_zero_shows_not_applicable_line(self):
        lines = build_decision_quality_compact_lines(
            {
                "decision_quality_level": "HIGH",
                "decision_quality_score": 100,
                "data_quality_status": "NOT_APPLICABLE",
                "risk_status": "ACCEPTABLE",
                "stability_status": "NOT_APPLICABLE",
                "sensitivity_status": "NOT_APPLICABLE",
            }
        )

        self.assertEqual(lines, ["  → Analyse sans capital — score de robustesse non applicable."])

    def test_decision_quality_medium_shows_mixed_status_breakdown(self):
        lines = build_decision_quality_compact_lines(
            {
                "decision_quality_level": "MEDIUM",
                "decision_quality_score": 72,
                "data_quality_status": "WATCH",
                "risk_status": "ELEVATED",
                "stability_status": "RESPONSIVE",
                "sensitivity_status": "MODERATELY_SENSITIVE",
                "why_not_high": [
                    "La recommandation reste utile, mais certaines données et certains risques demandent une validation manuelle avant grosse allocation."
                ],
            }
        )

        self.assertEqual(len(lines), 2)
        self.assertIn("données: ⚠ données", lines[0])
        self.assertIn("risque: ✗ risque", lines[0])
        self.assertIn("stabilité: ~ stabilité", lines[0])
        self.assertIn("sensibilité: MODERATELY_", lines[0])
        self.assertLessEqual(len(lines[1].replace("  → ", "", 1)), 120)

    def test_decision_quality_high_shows_robust_line_only(self):
        lines = build_decision_quality_compact_lines(
            {
                "decision_quality_level": "HIGH",
                "decision_quality_score": 91,
                "data_quality_status": "ROBUST",
                "risk_status": "ACCEPTABLE",
                "stability_status": "STABLE",
                "sensitivity_status": "ROBUST",
            }
        )

        self.assertEqual(lines, ["  → Recommandation robuste — tous les indicateurs au vert."])

    def test_decision_quality_missing_is_safe(self):
        lines = build_decision_quality_compact_lines(None)

        self.assertEqual(lines, ["  → Données de qualité insuffisantes pour évaluation."])

    def test_triage_header_separates_system_actions_when_needed(self):
        markdown = build_triage_header(
            mode="high-cagr",
            allocation_result={"allocations": [{"ticker": "MSFT", "amount": 100}]},
            sell_rows=[],
            validation_priority_rows=[],
            anomaly_rows=[],
            analyses={"MSFT": {}},
            watchlist_analyses={},
            market_analyses={},
            discovery_analyses={},
            score_stability={"status": "WATCH", "message": "⚠️ Scores à surveiller."},
            walk_forward_status={"status": "WALK_FORWARD_DORMANT", "message": "Walk-forward absent."},
        )

        self.assertIn("DÉCISION : +100$ MSFT", markdown)
        self.assertIn("─── ACTIONS SYSTÈME REQUISES ───", markdown)
        self.assertIn("python3 main.py walk-forward-backtest --mode high-cagr", markdown)
        self.assertIn("Scores à surveiller", markdown)

    @patch(
        "src.report_formatters._triage_proxy_calibration_maintenance_state",
        return_value=("🟢 Calibration des proxys : à jour.", []),
    )
    def test_triage_header_hides_system_block_when_no_system_action(self, _proxy_state):
        markdown = build_triage_header(
            mode="high-cagr",
            allocation_result={"allocations": []},
            sell_rows=[],
            validation_priority_rows=[],
            anomaly_rows=[],
            analyses={},
            watchlist_analyses={},
            market_analyses={},
            discovery_analyses={},
            score_stability={"status": "STABLE", "message": "Stable."},
            walk_forward_status={"status": "WALK_FORWARD_HEALTHY", "message": "OK."},
        )

        self.assertIn("Aucune contribution ce mois-ci", markdown)
        self.assertNotIn("ACTIONS SYSTÈME", markdown)

    @patch(
        "src.report_formatters._triage_research_report_maintenance_state",
        return_value=(
            "🟡 Rapports BNCD/Morningstar : mise à jour périodique recommandée.",
            [
                "⚠ RAPPORTS BNCD/MORNINGSTAR — RAFRAÎCHISSEMENT RECOMMANDÉ",
                "2 titre(s) figurent dans la file de recherche (1 priorité haute).",
                "Action: lancer python3 main.py research-needed --limit 30",
            ],
        ),
    )
    def test_triage_header_replaces_raw_validation_count_with_research_action(self, _research_state):
        with patch(
            "src.report_formatters._triage_proxy_calibration_maintenance_state",
            return_value=("🟢 Calibration des proxys : à jour.", []),
        ):
            markdown = build_triage_header(
                mode="high-cagr",
                allocation_result={"allocations": []},
                sell_rows=[],
                validation_priority_rows=[
                    {"priority": "HAUTE"},
                    {"priority": "TRES_HAUTE"},
                    {"priority": "MOYENNE"},
                ],
                anomaly_rows=[],
                analyses={},
                watchlist_analyses={},
                market_analyses={},
                discovery_analyses={},
                research_needed_rows=[
                    {"ticker": "MSFT", "priority": "HIGH"},
                    {"ticker": "MSFT", "priority": "HIGH"},
                    {"ticker": "NVDA", "priority": "MEDIUM"},
                ],
            )

        self.assertNotIn("donnée(s) prioritaire(s) à valider", markdown)
        self.assertIn("RAPPORTS BNCD/MORNINGSTAR", markdown)
        self.assertIn("2 titre(s) figurent dans la file de recherche (1 priorité haute)", markdown)
        self.assertIn("python3 main.py research-needed --limit 30", markdown)
        self.assertIn("Calibration des proxys : à jour", markdown)

    def test_compact_decision_section_builds_allocation_and_position_profile(self):
        markdown = build_compact_decision_section(
            allocation_result={
                "allocations": [
                    {
                        "ticker": "MSFT",
                        "amount": 120,
                        "percentage": 0.4,
                        "reason": "Meilleur compromis actuel entre qualité, croissance et risque.",
                        "confidence": "HIGH",
                    }
                ],
                "decision_quality": {},
            },
            allocation_change_rows=[{"ticker": "MSFT", "change_amount": 20, "change_status": "INCREASED"}],
            analyses={"MSFT": {"company_name": "Microsoft"}},
            watchlist_analyses={},
            market_analyses={},
            discovery_analyses={},
            instrument_profiles=[
                {
                    "ticker": "MSFT",
                    "name": "Microsoft",
                    "instrument_type": "STOCK",
                    "sector_or_category": "Technology",
                    "industry": "Software",
                    "business_description": "développer des logiciels et services cloud",
                    "revenue_model_or_activity": "Revenus récurrents logiciels, cloud et productivité",
                    "portfolio_role": "compounder de qualité",
                    "key_watch_items": "valorisation et croissance cloud",
                }
            ],
            decision_quality={
                "decision_quality_level": "HIGH",
                "decision_quality_score": 92,
                "data_quality_status": "ROBUST",
                "risk_status": "ACCEPTABLE",
                "stability_status": "STABLE",
                "sensitivity_status": "ROBUST",
            },
        )

        self.assertIn("Allocation recommandée", markdown)
        self.assertIn("MSFT 120$ (40%)", markdown)
        self.assertIn("Confiance   : HIGH (92/100)", markdown)
        self.assertIn("#### Microsoft (MSFT)", markdown)
        self.assertIn("Microsoft est une entreprise classée dans Technology / Software.", markdown)
        self.assertIn("Activité principale : développer des logiciels et services cloud.", markdown)
        self.assertNotIn("Microsoft est une entreprise Technology / Software dont l'activité principale est", markdown)
        self.assertIn("Son rôle dans ce portefeuille : compounder de qualité.", markdown)
        self.assertIn("Vs dernier run      : +20$ (INCREASED)", markdown)

    def test_compact_decision_section_handles_no_active_allocation(self):
        markdown = build_compact_decision_section(
            allocation_result={"allocations": []},
            allocation_change_rows=[],
            analyses={},
            watchlist_analyses={},
            market_analyses={},
            discovery_analyses={},
            instrument_profiles=None,
            decision_quality=None,
        )

        self.assertIn("Aucune contribution ce run — portefeuille en surveillance.", markdown)

    def test_compact_model_health_section_summarizes_signals_and_fragile_core_data(self):
        markdown = build_compact_model_health_section(
            score_stability={"status": "STABLE", "message": "✅ SCORE_STABILITY_STABLE — OK"},
            walk_forward_status={"status": "WALK_FORWARD_DORMANT", "message": "⚠️ WALK_FORWARD_DORMANT — relancer"},
            full_audit_status={"status": "FULL_AUDIT_HEALTHY", "message": "Audit récent."},
            model_audit_status={"status": "MODEL_AUDIT_HEALTHY", "message": "Audit stabilité récent."},
            decision_quality={
                "decision_quality_level": "HIGH",
                "decision_quality_score": 95,
                "data_quality_status": "ROBUST",
            },
            allocation_result={"allocations": []},
            data_freshness_rows=[
                {
                    "ticker": "MSFT",
                    "universe": "CORE_PORTFOLIO",
                    "overall_data_freshness_level": "WATCH_FRESHNESS",
                    "market_data_warning_flags": "CIRCUIT_OPEN",
                    "data_freshness_action": "Relancer les données avant grosse allocation.",
                }
            ],
        )

        self.assertIn("### Santé du modèle", markdown)
        self.assertIn("Score Stability", markdown)
        self.assertIn("Walk-Forward", markdown)
        self.assertIn("Robustesse : N/A", markdown)
        self.assertIn("MSFT — CIRCUIT_OPEN", markdown)

    def test_compact_model_health_section_uses_nested_decision_quality_sensitivity_status(self):
        markdown = build_compact_model_health_section(
            score_stability={"status": "STABLE", "message": "✅ SCORE_STABILITY_STABLE — OK"},
            walk_forward_status={"status": "WALK_FORWARD_HEALTHY", "message": "OK."},
            full_audit_status={"status": "FULL_AUDIT_HEALTHY", "message": "Audit récent."},
            model_audit_status={"status": "MODEL_AUDIT_HEALTHY", "message": "Audit stabilité récent."},
            decision_quality={
                "decision_quality_level": "MEDIUM",
                "decision_quality_score": 70,
                "data_quality_status": "ROBUST",
                "risk_status": "WATCH",
                "stability_status": "RESPONSIVE",
                "sensitivity_status": "ROBUST",
            },
            allocation_result={
                "allocations": [{"ticker": "CLS.TO", "amount": 63}],
                "decision_quality": {"sensitivity_status": "ROBUST"},
            },
            data_freshness_rows=[],
        )

        self.assertIn("Robustesse : ROBUST", markdown)
        self.assertNotIn("Robustesse : N/D", markdown)

    def test_compact_portfolio_risks_use_aggregate_cluster_exposures(self):
        markdown = build_compact_portfolio_section(
            risk_rows=[
                {
                    "risk_type": "cluster_caché",
                    "risk_level": "HIGH",
                    "description": "RATES_SENSITIVE_GROWTH: cluster caché extrême",
                    "impact": "Poids concerné: 68.5 %",
                },
                {
                    "risk_type": "cluster_caché",
                    "risk_level": "HIGH",
                    "description": "MEGA_CAP_TECH_PLATFORMS: cluster caché extrême",
                    "impact": "Poids concerné: 60.8 %",
                },
                {
                    "risk_type": "devise",
                    "risk_level": "MEDIUM",
                    "description": "USD: forte exposition USD",
                    "impact": "Poids concerné: 81.0 %",
                },
            ],
            hidden_cluster_rows=[
                {
                    "ticker": "MSFT",
                    "niveau": "EXTREME",
                    "exposition_cluster": 0.685,
                    "clusters": (
                        "AI_SEMI_CLOUD_INFRA, INDUSTRIAL_ELECTRIFICATION_AUTOMATION, "
                        "MEGA_CAP_TECH_PLATFORMS, RATES_SENSITIVE_GROWTH"
                    ),
                }
            ],
        )

        self.assertIn("| risque | niveau | exposition | lecture |", markdown)
        self.assertIn("Sensibilité aux taux", markdown)
        self.assertIn("68.5%", markdown)
        self.assertIn("Grandes plateformes technologiques", markdown)
        self.assertIn("60.8%", markdown)
        self.assertIn("Devise USD", markdown)
        self.assertIn("81%", markdown)
        self.assertIn("⚠️ Élevé", markdown)
        self.assertIn("★ Sensibilité aux taux", markdown)
        self.assertIn("★ Risque prioritaire à considérer", markdown)
        self.assertNotIn("thème IA / semi-conducteurs", markdown)
        self.assertNotIn("électrification industrielle", markdown)

    def test_compact_portfolio_risks_show_secondary_clusters_without_priority_star(self):
        markdown = build_compact_portfolio_section(
            risk_rows=[
                {
                    "risk_type": "cluster_caché",
                    "risk_level": "SECONDARY",
                    "description": "AI_SEMI_CLOUD_INFRA: exposition agrégée",
                    "impact": "Poids concerné: 39.7 %",
                },
                {
                    "risk_type": "cluster_caché",
                    "risk_level": "SECONDARY",
                    "description": "INDUSTRIAL_ELECTRIFICATION_AUTOMATION: exposition agrégée",
                    "impact": "Poids concerné: 36.2 %",
                },
            ],
        )

        self.assertIn("IA / semi-conducteurs / cloud", markdown)
        self.assertIn("39.7%", markdown)
        self.assertIn("Électrification et automatisation", markdown)
        self.assertIn("36.2%", markdown)
        self.assertNotIn("★ IA / semi-conducteurs / cloud", markdown)
        self.assertNotIn("★ Électrification et automatisation", markdown)

    def test_compact_data_reliability_section_flags_conflicts_and_sources(self):
        markdown = build_compact_data_reliability_section(
            analyses={
                "MSFT": {"data_reliability_level": "STRONG"},
                "APP": {"data_reliability_level": "WATCH"},
            },
            source_health_rows=[
                {"source": "Yahoo/yfinance market data", "status": "OK"},
                {"source": "Disabled source", "status": "DISABLED"},
            ],
            source_conflict_rows=[
                {
                    "ticker": "APP",
                    "severity": "HIGH_REVIEW",
                    "conflict_count": "4",
                    "conflict_profile": "MATERIAL_REVIEW",
                    "recommended_action": "Valider avant grosse allocation.",
                }
            ],
            data_freshness_rows=[
                {
                    "ticker": "MSFT",
                    "universe": "CORE_PORTFOLIO",
                    "overall_data_freshness_level": "WATCH_FRESHNESS",
                    "market_data_warning_flags": "CIRCUIT_OPEN",
                }
            ],
            validation_priority_rows=[],
        )

        self.assertIn("Confiance dans les données", markdown)
        self.assertIn("UTILISABLE POUR LE SUIVI HABITUEL", markdown)
        self.assertIn("50% des 2 entreprises détenues ont des données solides", markdown)
        self.assertIn("| APP | 4 écart(s) entre sources | Seulement avant un achat important |", markdown)
        self.assertIn("aucune validation technique champ par champ", markdown)
        self.assertIn("Action commune", markdown)
        self.assertIn("Sources : Yahoo/yfinance market data", markdown)

    def test_compact_data_reliability_excludes_etfs_from_fundamental_coverage(self):
        markdown = build_compact_data_reliability_section(
            analyses={
                "MSFT": {"data_reliability_level": "HIGH"},
                "APP": {"data_reliability_level": "STRONG"},
                "VFV.TO": {"data_reliability_level": "BENCHMARK"},
                "TEC.TO": {"data_reliability_level": "ETF"},
            },
            source_health_rows=[],
            source_conflict_rows=[],
            data_freshness_rows=[],
            validation_priority_rows=[],
        )

        self.assertIn("100% des 2 entreprises détenues ont des données solides", markdown)
        self.assertIn("2 ETF/indice(s) exclus", markdown)
        self.assertNotIn("fragile", markdown)
        self.assertIn("<summary>Détails techniques des sources</summary>", markdown)

    def test_compact_external_monitoring_prioritizes_user_action(self):
        markdown = build_compact_external_monitoring_section(
            mode="high-cagr",
            allocation_result={"allocations": []},
            core_analyses={"MSFT": {}},
            market_analyses={"AMAT": {}, "ADI": {}},
            external_candidate_rows=[
                {
                    "source": "MARKET_UNIVERSE",
                    "ticker": "AMAT",
                    "status": "PROMISING_BUT_INCOMPLETE",
                    "score": 9.76,
                    "raison": "Préfiltre de qualité respecté.",
                },
                {
                    "source": "MARKET_UNIVERSE",
                    "ticker": "ADI",
                    "status": "PROMISING_BUT_INCOMPLETE",
                    "score": 8.58,
                    "raison": "Préfiltre de qualité respecté.",
                },
            ],
            blocked_validation_rows=[{"ticker": "AUCUN_CANDIDAT_BLOQUE"}],
            promotion_rows=[],
            external_etf_rows=[],
            policy_note="Politique externe détaillée.",
        )

        self.assertIn("## 6. Radar externe", markdown)
        self.assertIn("Aucun titre externe financé", markdown)
        self.assertIn("AMAT, ADI", markdown)
        self.assertIn("pas des achats à exécuter", markdown)
        self.assertIn("**Action pour toi :** aucune", markdown)
        self.assertIn("| AMAT | Market | Prometteur, mais pas encore retenu |", markdown)
        self.assertIn("<summary>Comprendre le radar et voir les détails techniques</summary>", markdown)

    def test_compact_external_monitoring_identifies_active_external_allocation(self):
        markdown = build_compact_external_monitoring_section(
            mode="high-cagr",
            allocation_result={"allocations": [{"destination": "AMAT", "montant": 125.0}]},
            core_analyses={"MSFT": {}},
            market_analyses={"AMAT": {}},
            external_candidate_rows=[],
            blocked_validation_rows=[],
            promotion_rows=[],
            external_etf_rows=[],
        )

        self.assertIn("Allocation externe active :** AMAT 125$", markdown)
        self.assertIn("aucune promotion manuelle", markdown)
        self.assertIn("exécuter uniquement les montants déjà indiqués dans la section 1", markdown)

    def test_ranking_section_shows_drawdown_and_non_allocated_watchlist(self):
        markdown = build_ranking_section(
            analyses={
                "MSFT": {
                    "ticker": "MSFT",
                    "capital_allocation_score": 88,
                    "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
                    "quality_drawdown_reason": "Baisse importante avec thèse intacte.",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "news_context_status": "SECTOR_OR_MACRO_PRESSURE",
                },
                "RHM.NE": {
                    "ticker": "RHM.NE",
                    "capital_allocation_score": 84,
                    "expected_cagr_quality": "HIGH",
                    "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "allocation_decision": "BUY / ADD",
                    "final_position_action": "ADD_WITH_MONITORING",
                }
            },
            watchlist_analyses={
                "COST": {
                    "ticker": "COST",
                    "capital_allocation_score": 82,
                    "blocking_reason_category": "DATA_INSUFFICIENT",
                    "expected_cagr_quality": "HIGH",
                    "opportunity_cost_status": "CLEARLY_BETTER_THAN_VFV",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "allocation_decision": "ELIGIBLE_BUT_NOT_SELECTED",
                }
            },
            market_analyses={
                "LOW": {
                    "ticker": "LOW",
                    "capital_allocation_score": 84,
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "promotion_proximity_score": "8/15",
                }
            },
            discovery_analyses={
                "DISC": {
                    "ticker": "DISC",
                    "capital_allocation_score": 90,
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "local_report_available": False,
                }
            },
        )

        self.assertIn("Opportunités — drawdown avec thèse intacte", markdown)
        self.assertIn("signal de prix intéressant", markdown)
        self.assertIn("Baisse importante avec thèse intacte", markdown)
        self.assertIn("SECTOR_OR_MACRO_PRESSURE", markdown)
        self.assertIn("MSFT", markdown)
        self.assertIn("Meilleurs titres surveillés", markdown)
        self.assertIn("classement général", markdown)
        self.assertIn("Données insuffisantes", markdown)
        self.assertIn("Un même titre peut apparaître dans les deux listes", markdown)
        self.assertIn("COST", markdown)
        self.assertNotIn("RHM.NE", markdown)
        self.assertNotIn("| LOW |", markdown)
        self.assertNotIn("| DISC |", markdown)


if __name__ == "__main__":
    unittest.main()
