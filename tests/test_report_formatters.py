import unittest

from src.report_formatters import (
    build_compact_data_reliability_section,
    build_compact_decision_section,
    build_compact_model_health_section,
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

    def test_triage_header_hides_system_block_when_no_system_action(self):
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

        self.assertIn("Fiabilité des données", markdown)
        self.assertIn("UTILISABLE AVEC RÉSERVES", markdown)
        self.assertIn("50% des positions ont des données solides", markdown)
        self.assertIn("APP — 4 conflits", markdown)
        self.assertIn("Sources : Yahoo/yfinance market data", markdown)

    def test_ranking_section_shows_drawdown_and_non_allocated_watchlist(self):
        markdown = build_ranking_section(
            analyses={
                "MSFT": {
                    "ticker": "MSFT",
                    "capital_allocation_score": 88,
                    "quality_drawdown_status": "QUALITY_DRAWDOWN_OPPORTUNITY",
                    "thesis_status": "INTACT",
                    "liquidation_status": "GREEN",
                    "quality_drawdown_label": "Baisse intéressante avec thèse intacte.",
                    "news_context_label": "MACRO_PRESSURE",
                }
            },
            watchlist_analyses={
                "COST": {
                    "ticker": "COST",
                    "capital_allocation_score": 82,
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
        self.assertIn("MSFT", markdown)
        self.assertIn("Meilleurs titres surveillés", markdown)
        self.assertIn("COST", markdown)
        self.assertNotIn("| LOW |", markdown)
        self.assertNotIn("| DISC |", markdown)


if __name__ == "__main__":
    unittest.main()
