# Investment Automation — Decisions Log

## 🎯 Purpose

This file tracks all major design and investment decisions made in the system.

Each decision must include:
- what was changed
- why it was changed
- expected impact

This ensures long-term consistency and prevents model drift.

---

# 📌 Decisions

## 2026-06-24 — Adopt long-term DCA as core strategy

### Decision
The system uses Dollar Cost Averaging (DCA) as the baseline investment strategy.

### Reason
- Reduces timing risk
- Improves behavioral discipline
- More robust than market timing

### Expected impact
More stable long-term returns with lower variance.

---

## 2026-06-24 — Avoid market timing strategies

### Decision
No strategy based on short-term market prediction is allowed.

### Reason
- Market timing is not statistically reliable
- High risk of overfitting in backtests

### Expected impact
Improved robustness and reduced model fragility.

---

## 2026-06-24 — Introduce Canadian tax-aware logic

### Decision
All investment evaluation must consider Canadian tax structure (TFSA, RRSP, taxable accounts).

### Reason
- Real investor is based in Canada (Quebec)
- After-tax return is more important than gross return

### Expected impact
More realistic portfolio optimization aligned with real-world returns.

---

## 2026-06-25 — Add moderate high-cagr allocation stability

### Decision
The `high-cagr` mode now uses `stability_strength_adjustment: 0.01` in `config/model_tuning.yaml`.

### Reason
- Reduce allocation churn when two eligible candidates are very close.
- Preserve responsiveness when a position deteriorates or a new candidate has a clear edge.
- Keep the high-CAGR profile focused on long-term compounding instead of short-term score noise.

### Expected impact
Slightly smoother monthly recommendations without making the mode materially more conservative.

---

## 2026-06-25 — Add soft single-name concentration throttle for high-cagr

### Decision
The `high-cagr` allocation engine now applies a soft single-name concentration throttle before the existing 30 % / 40 % drift limits.

### Reason
- Reduce repeated monthly additions to a position that is already large.
- Preserve the ability to let exceptional compounders keep growing without forced selling.
- Improve execution discipline when two high-quality candidates are close but one is materially less concentrated.

### Expected impact
More balanced contribution sizing inside the high-CAGR mandate, with lower single-name execution risk and no hard cap on existing winners.

---

## 2026-06-25 — Add durable proxy calibration evidence history

### Decision
The proxy calibration workflow now writes usable true-value/proxy comparisons to `data/proxy_calibration_history.csv` and mirrors the latest view to `reports/latest_proxy_calibration_history.csv`.

### Reason
- Preserve calibration evidence even after the user clears the working calibration CSV.
- Avoid learning from duplicate repeated analyses of the same true value/source.
- Prepare a safer future proxy bias engine without changing proxy formulas yet.

### Expected impact
Improved long-term proxy auditability with no immediate change to allocation recommendations.

---

## 2026-06-25 — Add guarded proxy bias detection

### Decision
Add `src/proxy_bias_engine.py` and export `reports/latest_proxy_bias_report.csv` after each analysis.

### Reason
- Detect possible systematic proxy bias from the durable calibration history.
- Require multiple independent, coherent examples before flagging a bias signal.
- Avoid overcorrection by not applying any formula change automatically.

### Expected impact
Better evidence for future proxy recalibration while preserving current allocation behavior and avoiding noisy self-correction.

---

## 2026-06-25 — Add supervised proxy correction layer

### Decision
Add `config/proxy_corrections.yaml` and `src/proxy_correction_engine.py` so validated multiplicative proxy correction factors can be applied before scoring.

### Reason
- Keep proxy formulas stable while allowing supervised correction factors.
- Avoid overcorrection by requiring explicit activation, numeric fields only, evidence thresholds and a ±25 % maximum factor change.
- Preserve traceability by showing active corrections in `latest_scores.csv`.

### Expected impact
No default change to recommendations because the correction file starts disabled. Future validated corrections can improve proxy accuracy without rewriting formulas directly.

---

## 2026-06-25 — Add proxy correction safety governor

### Decision
Integrate proxy corrections into `improvement-audit` and `apply-safe-tuning` with a dedicated history file at `data/proxy_correction_history.csv`.

### Reason
- Allow only very strong proxy bias signals to become SAFE auto-applicable correction suggestions.
- Require same-day audit, same mode, source-health gate, anti-overfitting gate and existing safe-tuning governor before activation.
- Record every applied proxy correction for cooldown and auditability.

### Expected impact
The model can self-correct small, repeated proxy biases under strict controls, while reducing the risk of overcorrecting formulas from noisy or stale evidence.

---

## 2026-06-26 — Add proxy correction post-activation audit

### Decision
Add `reports/latest_proxy_correction_audit.csv` and report sections that monitor active proxy corrections after they are applied.

### Reason
- Prevent a validated correction from becoming a stale or excessive source of false precision.
- Flag corrections near the ±25 % cap, old corrections, noisy new evidence or evidence pointing in the opposite direction.
- Keep rollback/review supervised instead of letting the model aggressively disable corrections during normal analysis.

### Expected impact
Active corrections remain useful but transparent. The model gains a controlled anti-overcorrection layer without making monthly allocation logic more conservative.

---

## 2026-06-26 — Add walk-forward backtest inventory foundation

### Decision
Add `src/walk_forward_backtest_engine.py` and the command `python3 main.py walk-forward-backtest --mode high-cagr`.

### Reason
- Prepare a future out-of-sample walk-forward backtest without pretending the model has enough evidence too early.
- Separate snapshots by analysis mode so `high-cagr` is never mixed with `balanced`, `family-office` or `rational-aggressive`.
- Deduplicate multiple analyses from the same day and require a minimum number of days between usable points.

### Expected impact
No change to monthly allocations. The model gains a safer audit foundation for future performance validation and lower overfitting risk.

---

## 2026-06-26 — Add guarded walk-forward period simulation

### Decision
Extend `python3 main.py walk-forward-backtest` so it simulates each usable historical allocation until the next sufficiently spaced analysis date and compares it to `VFV.TO`.

### Reason
- Test actual historical recommendations instead of rebuilding past decisions with today’s scores.
- Reduce look-ahead and survival-bias risk by using saved snapshots from the time of the recommendation.
- Avoid false confidence by excluding short periods and marking periods with excessive missing price data as non-simulated.

### Expected impact
No change to monthly allocation behavior. The model gains a more realistic audit signal, but results remain preliminary until enough spaced periods exist.

---

## 2026-06-26 — Integrate walk-forward evidence into audits and anti-overfitting gate

### Decision
`full-audit` now runs and reports the walk-forward check, and `improvement-audit` now passes walk-forward results into the anti-overfitting gate.

### Reason
- Use real historical recommendations as an out-of-sample evidence layer before applying automatic micro-tuning.
- Keep young or insufficient walk-forward history neutral so the model is not made unnecessarily conservative.
- Block only aggressive/reactive auto-tuning when enough walk-forward evidence clearly fails the do-no-harm test vs `VFV.TO`.

### Expected impact
No change to normal monthly recommendations. Safer `apply-safe-tuning` behavior with lower overfitting risk and clearer full-audit reporting.

---

## 2026-06-26 — Add walk-forward market regime diagnostics

### Decision
Add market-regime classification to walk-forward periods and export `reports/latest_walk_forward_regime_summary.csv`.

### Reason
- Avoid judging the model only from one market environment.
- Identify whether the strategy is weak in a specific regime, such as VFV weakness, flat markets or strong rallies.
- Keep the signal moderate: limited or single-regime history remains informational, not punitive.

### Expected impact
No change to monthly allocation behavior. Audit and safe-tuning decisions gain better context across market regimes without forcing broad conservatism.

---

## 2026-06-26 — Add walk-forward health and logging integration

### Decision
Add walk-forward checks to `health-check` and a dedicated run log for `python3 main.py walk-forward-backtest`.

### Reason
- Make the new walk-forward layer easier to monitor over months and years.
- Detect partial/missing walk-forward outputs without affecting monthly recommendations.
- Keep insufficient walk-forward history informational so it does not create false conservatism or false precision.

### Expected impact
No change to scoring or allocation. Better operational reliability, clearer audit trail and safer interpretation of walk-forward evidence.

---

## 2026-06-26 — Phase 2 engine-level correctness pass

### Decision
Apply the Phase 2 engine-level fixes from `PHASE2_CODEX_PROMPT.md` without changing investment thresholds, allocation philosophy, or scoring weights.

### Changes
- `src/sizing_engine.py`: reuse already-enriched cash-flow and shareholder-discipline values when present, instead of recomputing them with a slightly different dictionary.
- `src/sizing_engine.py`: prevent `sector_cagr_estimated` from being counted twice when `market_growth_thesis_score` is unavailable by using a neutral market-growth component.
- `src/conviction_engine.py`: make PEG penalties mutually exclusive so a very high PEG receives the stronger penalty only, not both penalties stacked.
- `src/add_eligibility_engine.py`: propagate a locally upgraded monitoring status through `resolved_monitoring_status` and `monitoring_status`.
- `src/allocation_stability_engine.py`: skip ETF analyses in the action-oriented stability layer.
- `main.py`: remove the first early `refresh_add_and_opportunity_context()` call and keep the final refresh after all context/risk passes.
- `src/thesis_engine.py`: memoize field-source sets inside `compute_thesis_status()` and document the two uncertainty thresholds.
- `src/opportunity_cost_engine.py`, `src/cagr_quality_engine.py`, `src/confidence_range_engine.py`, `src/sizing_engine.py`: add clarifying comments around intentional branching/constants/band differences.

### Verification
- `python3 main.py validate-inputs` passed after each fix group.
- Dead-code/integration checks confirmed:
  - `can_add_by_drift()` is used by `allocation_engine.py`.
  - Proxy bias/correction engines are integrated through `main.py`, `auto_fundamentals.py`, reports, and improvement audit.
  - `company_dossier_engine.py` is used by `report_generator.py`.
  - `sell_validation_checklist_engine.py` is used by `report_generator.py`.
  - `fund_price_fallback_engine.py` is used by `data_fetcher.py`.

### Expected impact
Minimal allocation impact except where prior behavior came from duplicated or stale intermediate calculations. The model should be more internally consistent, easier to audit, and less likely to over-penalize or mis-handle edge cases. No new conservatism was intentionally added.

---

## 2026-06-27 — Phase 3 controlled cleanup and optimization pass

### Decision
Apply the safe parts of `PHASE3_CODEX_PROMPT.md` while preserving all allocation rules, scoring thresholds, report schemas and investment behavior.

### Changes
- `src/sizing_engine.py`: added `_get_cached()` to centralize the cached/fallback read pattern introduced in Phase 2.
- `src/ticker_resolver.py`: added `load_and_resolve_universe()` and replaced repeated universe resolution blocks in `main.py`.
- `main.py`: documented the context enrichment order inside `run_analysis()` to make ordering dependencies explicit.
- `src/allocation_engine.py`: moved the small autonomous `allocation_universe_for_mode()` helper out of `main.py`.
- `src/report_generator.py`: removed confirmed unused imports and extracted pure report text helpers into `src/report_formatters.py`.
- `main.py`: documented the final ETF role guard in the allocation universe.

### Verification and deferrals
- `python3 main.py validate-inputs` passed after each change group.
- Verified that Phase 2 flagged items are active and should not be removed: drift add checks, proxy bias/corrections, company dossiers, sell checklist, fund price fallback and model version.
- `pyflakes` was not installed in the local virtual environment, so import cleanup used a conservative AST scan and removed only confirmed unused imports.
- A full split of `report_generator.py` and `main.py` was intentionally limited to safe extractions. The remaining large split is deferred because report sections, CSV writers and formatting helpers are tightly coupled and should be moved in smaller reviewed batches.
- `data_fetcher.py` was assessed but not split because the main `MarketDataFetcher` class and fallback/source logic are heavily coupled.
- `backtest_engine.py` and `walk_forward_backtest_engine.py` share only generic helper names like `_markdown_table`; their logic is intentionally different.
- `full_audit_engine.py` and `model_improvement_engine.py` share generic formatting/helper names, but no safe shared extraction was obvious without adding coupling.

### Expected impact
No intended change to recommendations. The model is slightly easier to maintain, has less duplicated plumbing, and has clearer guardrails for future refactors without reducing high-CAGR behavior.

---

# 🧠 Rule

No major change can be applied to the system without being documented here.
