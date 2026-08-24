import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.full_audit_engine import (
    build_full_audit_markdown,
    build_full_audit_metrics,
    build_full_audit_rows,
    estimate_monthly_contribution,
    write_full_audit_outputs,
)


class FullAuditEngineTest(unittest.TestCase):
    def test_estimate_monthly_contribution_uses_detected_external_flows(self):
        with TemporaryDirectory() as folder:
            data = Path(folder)
            (data / "portfolio_inferred_transactions.csv").write_text(
                "\n".join(
                    [
                        "date,ticker,account_type,account_tax_category,inferred_transaction_type,shares_change,estimated_price_cad,estimated_value_cad,external_flow_cad,sp500_proxy,sp500_proxy_price_at_flow,confidence,source_change_type,source,notes",
                        "2026-01-10,MSFT,TFSA1,TFSA,BUY,1,500,500,500,VFV.TO,100,HIGH,SHARES_INCREASED,AUTO,test",
                        "2026-02-10,VFV.TO,TFSA1,TFSA,BUY,2,250,500,500,VFV.TO,101,HIGH,SHARES_INCREASED,AUTO,test",
                        "2026-03-10,AAPL,TFSA1,TFSA,INFERRED_COST_UPDATE,0,,0,0,VFV.TO,102,INFO_ONLY,COST_BASIS_UPDATED,AUTO,ignore",
                    ]
                ),
                encoding="utf-8",
            )
            (data / "portfolio_transactions.csv").write_text(
                "date,ticker,account_type,transaction_type,shares,price,price_currency,fees,fees_currency,cash_amount,cash_currency,notes\n",
                encoding="utf-8",
            )

            result = estimate_monthly_contribution(data)

        self.assertEqual(result["source"], "DETECTED_EXTERNAL_FLOWS")
        self.assertEqual(result["monthly_capital"], 500.0)
        self.assertEqual(result["positive_flow_month_count"], 2)
        self.assertEqual(result["total_detected_contributions"], 1000.0)

    def test_estimate_monthly_contribution_falls_back_without_flows(self):
        with TemporaryDirectory() as folder:
            result = estimate_monthly_contribution(Path(folder))

        self.assertEqual(result["source"], "DEFAULT_INSUFFICIENT_HISTORY")
        self.assertEqual(result["monthly_capital"], 500.0)
        self.assertEqual(result["confidence"], "LOW")

    def test_full_audit_metrics_builds_criterion7_status(self):
        metrics = build_full_audit_metrics(
            model_audit={
                "metrics": {
                    "health_status": "STRONG",
                    "health_score": 86,
                    "confidence": "SOLID",
                    "sample_count": 6,
                    "allocation_sample_count": 6,
                    "span_days": 180,
                    "avg_allocation_turnover": 0.12,
                    "avg_vfv": 0.12,
                    "avg_core": 0.88,
                    "avg_max_single": 0.34,
                    "high_cycle_day_rate": 0.10,
                    "low_data_day_rate": 0.0,
                    "current_model_rules_version": "v-current",
                    "current_version_observation_count": 6,
                }
            },
            backtest_result={
                "summaries": [
                    {
                        "period_years": 5,
                        "excess_value_vs_vfv": 1200,
                        "max_drawdown_on_capital_multiple": -0.18,
                        "avg_vfv_allocation": 0.12,
                    }
                ]
            },
            backtest_error="",
            walk_forward_result={
                "summary": {
                    "status": "PRELIMINARY_WALK_FORWARD",
                    "simulated_periods": 3,
                    "usable_walk_forward_periods": 3,
                    "compounded_excess_return_vs_vfv": 0.04,
                    "avg_excess_return_vs_vfv": 0.01,
                    "win_rate_vs_vfv": 0.67,
                },
                "period_rows": [
                    {
                        "model_rules_version": "v-current",
                        "evaluation_status": "SIMULATED",
                        "strategy_period_return": 0.04,
                        "vfv_period_return": 0.02,
                        "excess_return_vs_vfv": 0.02,
                    },
                    {
                        "model_rules_version": "v-current",
                        "evaluation_status": "SIMULATED",
                        "strategy_period_return": 0.03,
                        "vfv_period_return": 0.02,
                        "excess_return_vs_vfv": 0.01,
                    },
                    {
                        "model_rules_version": "v-current",
                        "evaluation_status": "SIMULATED",
                        "strategy_period_return": 0.02,
                        "vfv_period_return": 0.01,
                        "excess_return_vs_vfv": 0.01,
                    },
                ],
            },
            account_performance_rows=[
                {
                    "account_type": "ALL_ACCOUNTS",
                    "comparison_status": "APPROXIMATE_CONTRIBUTIONS_CHANGED",
                    "twr_status": "TWR_FLOW_ADJUSTED_AHEAD_OF_SP500",
                    "twr_excess_vs_sp500": 0.08,
                    "xirr_excess_vs_sp500": -0.20,
                    "benchmark_return_basis": "ADJUSTED_CLOSE_TOTAL_RETURN_PROXY",
                    "preferred_performance_summary": "Lecture recommandée: TWR.",
                }
            ],
            contribution_estimate={
                "monthly_capital": 500,
                "confidence": "SOLID",
                "source": "DETECTED_EXTERNAL_FLOWS",
            },
            selected_monthly_capital=500,
            period="all",
            years=[5],
            mode="high-cagr",
        )

        self.assertIn(metrics["criterion7_status"], {"AUDIT_STRONG", "AUDIT_ACCEPTABLE"})
        self.assertGreater(metrics["criterion7_score"], 70)
        self.assertEqual(metrics["selected_monthly_capital"], 500)
        self.assertEqual(metrics["realized_performance_status"], "TWR_FLOW_ADJUSTED_AHEAD_OF_SP500")
        self.assertEqual(metrics["account_summary"]["twr_excess_vs_sp500"], 0.08)
        self.assertIn("Écart TWR", metrics["account_summary"]["interpretation"])
        self.assertIn("ADJUSTED_CLOSE_TOTAL_RETURN_PROXY", metrics["account_summary"]["interpretation"])
        self.assertIn("ticker_source_quality_status", metrics)
        self.assertIn("walk_forward_status", metrics)
        self.assertGreater(metrics["walk_forward_score"], 60)

    def test_full_audit_outputs_are_written(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            metrics = {
                "date": "2026-05-16",
                "mode": "high-cagr",
                "period": "all",
                "years": [5],
                "selected_monthly_capital": 500,
                "criterion7_status": "AUDIT_ACCEPTABLE",
                "criterion7_score": 72.0,
                "criterion7_interpretation": "Audit acceptable.",
                "model_health_status": "GOOD_BUT_WATCH",
                "model_health_score": 72.0,
                "backtest_status": "THEORETICAL_ACCEPTABLE",
                "backtest_score": 70.0,
                "walk_forward_status": "WALK_FORWARD_NOT_READY",
                "walk_forward_score": 60.0,
                "realized_performance_status": "SIMILAR_TO_SP500",
                "realized_performance_score": 62.0,
                "contribution_estimate": {"monthly_capital": 500, "confidence": "LOW"},
            }
            rows = build_full_audit_rows(
                {
                    **metrics,
                    "model_allocation_sample_count": 2,
                    "model_span_days": 30,
                    "avg_allocation_turnover": 0.1,
                    "avg_vfv": 0.1,
                    "avg_core": 0.9,
                    "avg_max_single": 0.4,
                    "high_cycle_day_rate": 0.1,
                    "evidence_score": 60,
                    "account_summary": {"status": "SIMILAR_TO_SP500", "interpretation": "Début du suivi."},
                    "backtest_summaries": [],
                }
            )
            markdown = build_full_audit_markdown(
                {**metrics, "backtest_summaries": []},
                rows,
                {"metrics": {"threshold_review": {"status": "OK", "interpretation": "OK"}}},
                {"summaries": []},
                {"summary": {"status": "NO_USABLE_PERIODS"}, "period_rows": []},
                [],
                weakest_core_audit_rows=[
                    {
                        "audit_status": "OBSERVE_ONLY",
                        "current_weakest_ticker": "APP",
                        "candidate_weakest_ticker": "TSLA",
                        "same_result": False,
                        "current_reason": "Logique active.",
                        "candidate_reason": "Logique candidate.",
                        "interpretation": "Audit seulement.",
                    }
                ],
                backtest_friction_rows=[
                    {
                        "audit_scope": "THEORETICAL_BACKTEST",
                        "mode": "model-lite high-cagr",
                        "period_years": 5,
                        "gross_return": 0.42,
                        "estimated_transaction_cost_cad": 37.5,
                        "net_return_after_friction": 0.415,
                        "friction_drag": 0.005,
                        "friction_assumption_status": "APPROXIMATE_STANDARD",
                        "interpretation": "Audit-only.",
                    }
                ],
            )
            write_full_audit_outputs(reports, {"markdown": markdown, "rows": rows})

            self.assertTrue((reports / "latest_full_audit.md").exists())
            self.assertTrue((reports / "latest_full_audit.html").exists())
            self.assertTrue((reports / "latest_full_audit_summary.csv").exists())
            self.assertIn("Audit weakest core", markdown)
            self.assertIn("AUDIT-ONLY — aucune recommandation modifiée", markdown)
            self.assertIn("APP", markdown)
            self.assertIn("TSLA", markdown)
            self.assertIn("Frictions de transaction des backtests", markdown)
            self.assertIn("APPROXIMATE_STANDARD", markdown)

    def test_full_audit_rows_include_ticker_source_quality(self):
        rows = build_full_audit_rows(
            {
                "criterion7_status": "AUDIT_ACCEPTABLE",
                "criterion7_score": 72.0,
                "criterion7_interpretation": "Audit acceptable.",
                "model_health_status": "GOOD",
                "model_health_score": 72.0,
                "model_confidence": "SOLID",
                "backtest_status": "OK",
                "backtest_score": 70.0,
                "walk_forward_status": "WALK_FORWARD_NOT_READY",
                "walk_forward_score": 60.0,
                "walk_forward_summary": {"status": "NO_USABLE_PERIODS"},
                "realized_performance_status": "OK",
                "realized_performance_score": 60.0,
                "evidence_score": 65.0,
                "source_health_status": "OK",
                "source_health_score": 90.0,
                "source_health_weakest_source": "Yahoo/yfinance market data",
                "source_health_auto_tuning_gate": "PASS",
                "ticker_source_quality_status": "WATCH",
                "ticker_source_quality_score": 78.0,
                "ticker_source_interpretation": "Ticker à surveiller.",
                "contribution_estimate": {"confidence": "LOW"},
                "underperformance_attribution": {"status": "N/D", "correction_governor": "NORMAL_SAFE_TUNING"},
            }
        )

        self.assertTrue(any(row["metric"] == "Qualité tickers et contradictions" for row in rows))
        self.assertTrue(any(row["metric"] == "Walk-forward hors-échantillon" for row in rows))


if __name__ == "__main__":
    unittest.main()
