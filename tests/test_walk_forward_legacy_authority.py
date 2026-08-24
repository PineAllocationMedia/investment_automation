import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from src.anti_overfitting_gate_engine import build_anti_overfitting_context
from src.full_audit_engine import build_full_audit_metrics
from src.model_audit_engine import build_model_audit
from src.utils import save_json
from src.validation_evidence import (
    AUTO_TUNING_POLICY,
    EXPLICIT_DECISION_ELIGIBILITY_BASIS,
    LEGACY_PARTIALLY_RECOVERABLE_BASIS,
    EvidenceClass,
    RunPurpose,
)
from src.walk_forward_backtest_engine import (
    WalkForwardInventoryConfig,
    build_walk_forward_coverage,
    build_walk_forward_inventory,
    build_walk_forward_simulation_summary,
    simulate_walk_forward_periods,
)


class WalkForwardLegacyAuthorityTest(unittest.TestCase):
    def test_scheduled_decision_period_is_point_in_time_walk_forward(self):
        _, periods, summary = self._simulate_timeline(
            [RunPurpose.SCHEDULED_DECISION.value, RunPurpose.SCHEDULED_DECISION.value]
        )

        self.assertEqual(periods[0]["evidence_class"], EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value)
        self.assertTrue(periods[0]["strategy_validation_authority"])
        self.assertEqual(summary["genuine_oos_periods"], 1)

    def test_manual_decision_period_is_point_in_time_walk_forward(self):
        _, periods, summary = self._simulate_timeline(
            [RunPurpose.MANUAL_DECISION.value, RunPurpose.MANUAL_DECISION.value]
        )

        self.assertEqual(periods[0]["evidence_class"], EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value)
        self.assertTrue(periods[0]["strategy_validation_authority"])
        self.assertEqual(summary["genuine_oos_periods"], 1)

    def test_unknown_legacy_spacing_fallback_remains_simulatable_and_auditable(self):
        inventory, periods, summary = self._simulate_timeline([None, None])

        self.assertEqual(inventory[0]["run_purpose"], RunPurpose.UNKNOWN_LEGACY.value)
        self.assertEqual(inventory[0]["run_purpose_status"], "LEGACY_UNCERTAINTY")
        self.assertTrue(inventory[0]["usable_for_walk_forward"])
        self.assertEqual(periods[0]["evaluation_status"], "SIMULATED")
        self.assertEqual(summary["simulated_periods"], 1)

    def test_legacy_period_preserves_eligibility_provenance_and_lower_class(self):
        _, periods, _ = self._simulate_timeline([None, None])
        period = periods[0]

        self.assertEqual(period["run_purpose"], RunPurpose.UNKNOWN_LEGACY.value)
        self.assertEqual(period["run_purpose_status"], "LEGACY_UNCERTAINTY")
        self.assertEqual(period["eligibility_basis"], LEGACY_PARTIALLY_RECOVERABLE_BASIS)
        self.assertEqual(period["evidence_class"], EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value)
        self.assertFalse(period["strategy_validation_authority"])

    def test_legacy_period_does_not_count_as_genuine_oos(self):
        _, _, summary = self._simulate_timeline([None, None])

        self.assertEqual(summary["simulated_periods"], 1)
        self.assertEqual(summary["genuine_oos_periods"], 0)
        self.assertEqual(summary["explicit_decision_simulated_periods"], 0)
        self.assertEqual(summary["legacy_partially_recoverable_simulated_periods"], 1)

    def test_many_legacy_periods_do_not_raise_strategy_validation_confidence(self):
        _, _, summary = self._simulate_timeline([None] * 7)

        self.assertEqual(summary["simulated_periods"], 6)
        self.assertEqual(summary["strategy_validation_confidence"], "INSUFFICIENT")
        self.assertEqual(summary["evidence_maturity"], "INSUFFICIENT")
        self.assertEqual(summary["strategy_validation_status"], "NO_USABLE_PERIODS")

    def test_many_legacy_periods_do_not_raise_primary_walk_forward_confidence(self):
        _, _, summary = self._simulate_timeline([None] * 7)

        self.assertEqual(summary["walk_forward_confidence"], "INSUFFICIENT")
        self.assertEqual(summary["evidence_class"], EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value)

    def test_full_audit_excludes_legacy_from_current_version_oos_maturity(self):
        _, periods, summary = self._simulate_timeline([None] * 7)
        metrics = self._full_audit(periods, summary)

        self.assertEqual(metrics["walk_forward_current_version_total_simulated_period_count"], 6)
        self.assertEqual(metrics["walk_forward_current_version_period_count"], 0)
        self.assertEqual(metrics["walk_forward_current_version_legacy_period_count"], 6)
        self.assertEqual(metrics["walk_forward_period_count"], 0)
        self.assertEqual(metrics["walk_forward_evidence_class"], EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value)
        self.assertEqual(metrics["walk_forward_confidence"], "INSUFFICIENT")
        self.assertEqual(metrics["strategy_validation_confidence"], "INSUFFICIENT")

    def test_anti_overfitting_excludes_legacy_from_genuine_oos(self):
        _, periods, summary = self._simulate_timeline([None] * 7)
        context = build_anti_overfitting_context(
            model_metrics=self._model_metrics(),
            walk_forward_summary_rows=[summary],
            walk_forward_period_rows=periods,
        )

        self.assertEqual(context["walk_forward_simulated_periods"], 6)
        self.assertEqual(context["walk_forward_current_version_total_simulated_period_count"], 6)
        self.assertEqual(context["walk_forward_current_version_legacy_period_count"], 6)
        self.assertEqual(context["genuine_oos_periods"], 0)
        self.assertEqual(context["evidence_class"], EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value)
        self.assertEqual(context["evidence_maturity"], "INSUFFICIENT")
        self.assertEqual(context["walk_forward_status"], "LIMITED")

    def test_mixed_twelve_periods_uses_only_two_explicit_for_maturity(self):
        legacy = [self._period_row(authoritative=False) for _ in range(10)]
        explicit = [self._period_row(authoritative=True) for _ in range(2)]
        summary = build_walk_forward_simulation_summary(
            [*legacy, *explicit],
            {"usable_walk_forward_periods": 12},
            WalkForwardInventoryConfig(mode="high-cagr", recommended_min_periods=6),
            "TEST",
        )

        self.assertEqual(summary["simulated_periods"], 12)
        self.assertEqual(summary["genuine_oos_periods"], 2)
        self.assertEqual(summary["explicit_decision_simulated_periods"], 2)
        self.assertEqual(summary["legacy_partially_recoverable_simulated_periods"], 10)
        self.assertEqual(summary["strategy_validation_confidence"], "INSUFFICIENT")
        self.assertEqual(summary["evidence_class"], EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value)

    def test_legacy_periods_remain_visible_in_diagnostic_counts(self):
        _, _, summary = self._simulate_timeline([None] * 5)

        self.assertEqual(summary["simulated_periods"], 4)
        self.assertEqual(summary["legacy_partially_recoverable_simulated_periods"], 4)
        self.assertEqual(summary["non_authoritative_simulated_periods"], 4)
        self.assertEqual(summary["other_non_authoritative_simulated_periods"], 0)

    def test_pre_schema_legacy_period_remains_backward_compatible_and_fail_closed(self):
        period = self._period_row(authoritative=False)
        for field in [
            "run_purpose_status",
            "eligibility_basis",
            "evidence_class",
            "strategy_validation_authority",
        ]:
            period.pop(field)
        summary = build_walk_forward_simulation_summary(
            [period],
            {"usable_walk_forward_periods": 1},
            WalkForwardInventoryConfig(mode="high-cagr"),
            "TEST",
        )
        full = self._full_audit([period], summary)

        self.assertEqual(summary["genuine_oos_periods"], 0)
        self.assertEqual(summary["legacy_partially_recoverable_simulated_periods"], 1)
        self.assertEqual(full["walk_forward_current_version_period_count"], 0)
        self.assertEqual(full["walk_forward_current_version_legacy_period_count"], 1)

    def test_diagnostic_fragmentation_behavior_remains_unchanged(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            days = ["2026-01-01", "2026-01-05", "2026-01-20"]
            purposes = [
                RunPurpose.SCHEDULED_DECISION.value,
                RunPurpose.DIAGNOSTIC.value,
                RunPurpose.SCHEDULED_DECISION.value,
            ]
            for day, purpose in zip(days, purposes):
                self._write_pair(reports, day, purpose)
            rows = build_walk_forward_inventory(
                reports,
                WalkForwardInventoryConfig(mode="high-cagr", min_days_between_points=14),
            )

        by_date = {row["analysis_date"]: row for row in rows}
        self.assertEqual(by_date["2026-01-01"]["next_analysis_date"], "2026-01-20")
        self.assertTrue(by_date["2026-01-01"]["usable_for_walk_forward"])
        self.assertFalse(by_date["2026-01-05"]["primary_timeline_eligible"])

    def test_current_version_model_audit_purpose_isolation_remains_unchanged(self):
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            self._write_pair(reports, "2026-01-01", RunPurpose.SCHEDULED_DECISION.value)
            self._write_pair(reports, "2026-01-05", RunPurpose.DIAGNOSTIC.value)
            self._write_pair(reports, "2026-01-20", RunPurpose.MANUAL_DECISION.value)
            metrics = build_model_audit(
                reports,
                period="all",
                mode="high-cagr",
                current_model_rules_version="v-current",
            )["metrics"]

        self.assertEqual(metrics["current_version_total_observation_count"], 3)
        self.assertEqual(metrics["current_version_decision_observation_count"], 2)
        self.assertEqual(metrics["current_version_non_decision_observation_count"], 1)

    def test_cross_version_full_audit_scope_remains_unchanged(self):
        current = self._period_row(authoritative=True, version="v-current")
        old = self._period_row(authoritative=True, version="v-old")
        summary = build_walk_forward_simulation_summary(
            [current, old],
            {"usable_walk_forward_periods": 2},
            WalkForwardInventoryConfig(mode="high-cagr"),
            "TEST",
        )
        metrics = self._full_audit([current, old], summary)

        self.assertEqual(metrics["walk_forward_current_version_period_count"], 1)
        self.assertEqual(metrics["walk_forward_cross_version_period_count"], 1)

    def test_proposal_only_tuning_policy_remains_unchanged(self):
        self.assertEqual(AUTO_TUNING_POLICY, "PROPOSAL_ONLY")

    @classmethod
    def _simulate_timeline(
        cls,
        purposes: list[str | None],
    ) -> tuple[list[dict], list[dict], dict]:
        with TemporaryDirectory() as folder:
            reports = Path(folder)
            days = [(date(2026, 1, 1) + timedelta(days=20 * index)).isoformat() for index in range(len(purposes))]
            for day, purpose in zip(days, purposes):
                cls._write_pair(reports, day, purpose)
            config = WalkForwardInventoryConfig(
                mode="high-cagr",
                min_days_between_points=14,
                recommended_min_periods=6,
            )
            inventory = build_walk_forward_inventory(reports, config)
            coverage = build_walk_forward_coverage(inventory, config)
            prices = pd.DataFrame(
                {
                    "MSFT": [100.0 + 2.0 * index for index in range(len(days))],
                    "VFV.TO": [100.0 + index for index in range(len(days))],
                },
                index=pd.to_datetime(days),
            )
            simulation = simulate_walk_forward_periods(
                [row for row in inventory if row["usable_for_walk_forward"]],
                prices,
                config,
            )
            periods = simulation["period_rows"]
            summary = build_walk_forward_simulation_summary(periods, coverage, config, "TEST")
            return inventory, periods, summary

    @staticmethod
    def _write_pair(reports: Path, day: str, purpose: str | None) -> None:
        history = reports / "history"
        history.mkdir(parents=True, exist_ok=True)
        stamp = day.replace("-", "")
        common = {
            "analysis_date": day,
            "created_at": f"{day}T09:00:00",
            "analysis_mode": "high-cagr",
            "model_rules_version": "v-current",
        }
        if purpose is not None:
            common["run_purpose"] = purpose
        save_json(
            history / f"analysis_high-cagr_{stamp}_090000.json",
            {**common, "analyses": [{"ticker": "MSFT", "universe": "CORE_PORTFOLIO"}]},
        )
        save_json(
            history / f"allocation_high-cagr_{stamp}_090100.json",
            {
                **common,
                "created_at": f"{day}T09:01:00",
                "allocations": [{"ticker": "MSFT", "amount": 500, "percentage": 1.0}],
            },
        )

    @staticmethod
    def _period_row(*, authoritative: bool, version: str = "v-current") -> dict:
        if authoritative:
            purpose = RunPurpose.SCHEDULED_DECISION.value
            basis = EXPLICIT_DECISION_ELIGIBILITY_BASIS
            evidence_class = EvidenceClass.POINT_IN_TIME_WALK_FORWARD.value
        else:
            purpose = RunPurpose.UNKNOWN_LEGACY.value
            basis = LEGACY_PARTIALLY_RECOVERABLE_BASIS
            evidence_class = EvidenceClass.HISTORICAL_STRESS_SENSITIVITY.value
        return {
            "model_rules_version": version,
            "run_purpose": purpose,
            "run_purpose_status": "EXPLICIT" if authoritative else "LEGACY_UNCERTAINTY",
            "eligibility_basis": basis,
            "evidence_class": evidence_class,
            "strategy_validation_authority": authoritative,
            "evaluation_status": "SIMULATED",
            "strategy_period_return": 0.02,
            "vfv_period_return": 0.01,
            "excess_return_vs_vfv": 0.01,
            "days_held": 20,
            "market_regime": "VFV_POSITIVE",
        }

    @classmethod
    def _full_audit(cls, periods: list[dict], summary: dict) -> dict:
        return build_full_audit_metrics(
            model_audit={"metrics": cls._model_metrics()},
            backtest_result={"summaries": []},
            backtest_error="",
            walk_forward_result={"summary": summary, "period_rows": periods},
            walk_forward_error="",
            account_performance_rows=[],
            contribution_estimate={"confidence": "LOW", "monthly_capital": 500},
            selected_monthly_capital=500,
            period="all",
            years=[5],
            mode="high-cagr",
        )

    @staticmethod
    def _model_metrics() -> dict:
        return {
            "health_status": "DATA_TOO_SHORT",
            "health_score": 40,
            "confidence": "VERY_LIMITED",
            "sample_count": 1,
            "allocation_sample_count": 1,
            "span_days": 0,
            "current_model_rules_version": "v-current",
            "current_version_decision_observation_count": 1,
        }


if __name__ == "__main__":
    unittest.main()
