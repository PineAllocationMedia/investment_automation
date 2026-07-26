from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.report_formatters import build_score_stability_signal_lines
from src.score_stability_engine import compute_score_stability
from src.utils import today_iso


class ScoreStabilityEngineTests(unittest.TestCase):
    def test_baseline_when_no_same_day_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            signal = compute_score_stability(tmp, "high-cagr", {"MSFT": _analysis("MSFT")})

        self.assertEqual(signal["status"], "SCORE_STABILITY_BASELINE")
        self.assertEqual(signal["ticker_rows"], [])

    def test_baseline_when_only_current_snapshot_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(reports, "2026-07-03T09:00:00", [_analysis("MSFT")])

            signal = compute_score_stability(reports, "high-cagr", {"MSFT": _analysis("MSFT")})

        self.assertEqual(signal["status"], "SCORE_STABILITY_BASELINE")

    def test_detects_watch_and_unstable_score_moves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(
                reports,
                "2026-07-03T09:00:00",
                [
                    _analysis("MSFT", score_total=8.0, conviction_score=80, capital_allocation_score=75),
                    _analysis("GOOGL", score_total=8.0, conviction_score=80, capital_allocation_score=75),
                ],
            )
            _write_snapshot(
                reports,
                "2026-07-03T10:00:00",
                [
                    _analysis("MSFT", score_total=8.0, conviction_score=80, capital_allocation_score=75),
                    _analysis("GOOGL", score_total=8.0, conviction_score=80, capital_allocation_score=75),
                ],
            )

            signal = compute_score_stability(
                reports,
                "high-cagr",
                {
                    "MSFT": _analysis("MSFT", score_total=10.0, conviction_score=80, capital_allocation_score=75),
                    "GOOGL": _analysis("GOOGL", score_total=8.0, conviction_score=84, capital_allocation_score=75),
                },
            )

        self.assertEqual(signal["status"], "UNSTABLE")
        rows = {row["ticker"]: row for row in signal["ticker_rows"]}
        self.assertEqual(rows["GOOGL"]["stability_flag"], "UNSTABLE")
        self.assertEqual(rows["MSFT"]["stability_flag"], "WATCH")

    def test_data_reliability_delta_alone_does_not_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(
                reports,
                "2026-07-03T09:00:00",
                [_analysis("MSFT", score_total=8.0, conviction_score=80, capital_allocation_score=75, data_reliability_score=90.0)],
            )
            _write_snapshot(
                reports,
                "2026-07-03T10:00:00",
                [_analysis("MSFT", score_total=8.0, conviction_score=80, capital_allocation_score=75, data_reliability_score=90.0)],
            )

            signal = compute_score_stability(
                reports,
                "high-cagr",
                {
                    "MSFT": _analysis(
                        "MSFT",
                        score_total=8.0,
                        conviction_score=80,
                        capital_allocation_score=75,
                        data_reliability_score=95.0,
                    )
                },
            )

        self.assertEqual(signal["status"], "STABLE")
        rows = {row["ticker"]: row for row in signal["ticker_rows"]}
        self.assertEqual(rows["MSFT"]["stability_flag"], "STABLE")
        self.assertEqual(rows["MSFT"]["data_reliability_score_delta"], 5.0)

    def test_market_freshness_gate_only_blocks_non_comparable_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(
                reports,
                "2026-07-03T09:00:00",
                [
                    _analysis("MSFT", market_data_freshness_level="STALE_CACHE"),
                    _analysis("GOOGL", market_data_freshness_level="STALE_CACHE"),
                ],
            )
            _write_snapshot(
                reports,
                "2026-07-03T10:00:00",
                [
                    _analysis("MSFT", market_data_freshness_level="FRESH"),
                    _analysis("GOOGL", market_data_freshness_level="FRESH"),
                ],
            )

            signal = compute_score_stability(
                reports,
                "high-cagr",
                {
                    "MSFT": _analysis("MSFT", score_total=4.0, market_data_freshness_level="FRESH"),
                    "GOOGL": _analysis("GOOGL", score_total=4.0, market_data_freshness_level="FRESH"),
                },
            )

        self.assertEqual(signal["status"], "SCORE_STABILITY_BASELINE")
        self.assertEqual(signal["ticker_rows"], [])
        self.assertEqual(signal["market_data_comparability"]["n_intersection"], 2)
        self.assertEqual(signal["market_data_comparability"]["n_mismatch"], 2)
        self.assertEqual(signal["market_data_comparability"]["fraction"], 1.0)

        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(
                reports,
                "2026-07-03T09:00:00",
                [_analysis("MSFT", score_total=8.0, market_data_freshness_level="FRESH")],
            )
            _write_snapshot(
                reports,
                "2026-07-03T10:00:00",
                [_analysis("MSFT", score_total=8.0, market_data_freshness_level="FRESH")],
            )

            signal = compute_score_stability(
                reports,
                "high-cagr",
                {"MSFT": _analysis("MSFT", score_total=4.0, market_data_freshness_level="FRESH")},
            )

        self.assertEqual(signal["status"], "UNSTABLE")
        self.assertEqual(signal["market_data_comparability"]["n_mismatch"], 0)

    def test_ignores_vfv_and_etfs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            _write_snapshot(
                reports,
                "2026-07-03T09:00:00",
                [
                    _analysis("VFV.TO", score_total=8.0, asset_type="ETF"),
                    _analysis("QQQ", score_total=8.0, asset_type="ETF"),
                    _analysis("MSFT", score_total=8.0),
                ],
            )
            _write_snapshot(
                reports,
                "2026-07-03T10:00:00",
                [
                    _analysis("VFV.TO", score_total=8.0, asset_type="ETF"),
                    _analysis("QQQ", score_total=8.0, asset_type="ETF"),
                    _analysis("MSFT", score_total=8.0),
                ],
            )

            signal = compute_score_stability(
                reports,
                "high-cagr",
                {
                    "VFV.TO": _analysis("VFV.TO", score_total=2.0, asset_type="ETF"),
                    "QQQ": _analysis("QQQ", score_total=2.0, asset_type="ETF"),
                    "MSFT": _analysis("MSFT", score_total=8.0),
                },
            )

        self.assertEqual(signal["status"], "STABLE")
        self.assertEqual([row["ticker"] for row in signal["ticker_rows"]], ["MSFT"])

    def test_compact_signal_is_one_line_when_stable(self) -> None:
        lines = build_score_stability_signal_lines(
            {"status": "STABLE", "message": "✅ SCORE_STABILITY_STABLE — Tous les scores sont identiques."}
        )

        self.assertEqual(lines, ["✅ SCORE_STABILITY_STABLE — Tous les scores sont identiques.", ""])


def _analysis(
    ticker: str,
    *,
    score_total: float = 8.0,
    conviction_score: float = 80.0,
    capital_allocation_score: float = 75.0,
    data_reliability_score: float = 90.0,
    asset_type: str = "",
    market_data_freshness_level: str = "FRESH",
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "score_total": score_total,
        "conviction_score": conviction_score,
        "capital_allocation_score": capital_allocation_score,
        "data_reliability_score": data_reliability_score,
        "asset_type": asset_type,
        "market_data_freshness_level": market_data_freshness_level,
    }


def _write_snapshot(reports_dir: Path, created_at: str, analyses: list[dict[str, object]]) -> None:
    history_dir = reports_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": created_at,
        "analysis_date": today_iso(),
        "analysis_mode": "high-cagr",
        "analyses": analyses,
    }
    suffix = created_at.replace(":", "").replace("-", "").replace("T", "_")
    (history_dir / f"analysis_high-cagr_{suffix}.json").write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
