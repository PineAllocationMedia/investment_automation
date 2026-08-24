# Validation architecture hardening - technical report

## A. Branch

- `codex/fix-validation-architecture-hardening`

## B. PR

- PR #16: https://github.com/PineAllocationMedia/investment_automation/pull/16
- Status: open for external review; unmerged and undeployed.

## C. Starting state

- Starting main SHA: `b9d2cba56c782c271641393827c677a275eac8f9`.
- Starting and ending `MODEL_RULES_VERSION`: `2026-08-23-research-freshness-authority-v5`.
- The investment-rule version did not change because this chantier changes validation authority, history metadata and audit interpretation only.
- Current validation schema after the final authority correction: `2026-08-23-validation-architecture-v3`.
- P0-B predecessor: PR #14 / merge `61a961f`; PR #15 was also present at the starting HEAD.

## D. Root causes

- P0-A: current-score historical simulations were scored positively by `full_audit_engine` and used by the anti-overfitting/tuning path, despite look-ahead/current-information contamination.
- P0-C: `build_walk_forward_inventory` selected the immediate next snapshot date before checking the minimum interval. Diagnostic runs could therefore replace the next real decision and remove a valid period.
- P1-A: `model_audit_engine` aggregated all observed `model_rules_version` values into the primary turnover/stability metrics.
- Residual P1-A correction: after version isolation, `model_audit_engine` still admitted every current-version run purpose and discarded purpose identity before daily collapse. Diagnostics could inflate primary history and a later same-day diagnostic could replace a genuine decision.
- Residual walk-forward authority correction: `UNKNOWN_LEGACY` snapshots accepted by the causal spacing fallback could simulate as `POINT_IN_TIME_WALK_FORWARD` and inflate strategy confidence, full-audit OOS maturity and anti-overfitting `genuine_oos_periods` despite their unknown original purpose.
- P1-B: model-history, source freshness and strategy-validation maturity used overlapping generic confidence labels.
- Safe tuning: `apply-safe-tuning` could write behavioral parameters when a YAML flag and several gates passed; the gates included theoretical backtest results and did not require homogeneous current-version OOS evidence.
- P0-B verification: the predecessor provenance/freshness architecture already satisfies the requested contract. No competing taxonomy or implementation was added.

## E. Architecture before

- The theoretical backtest was described as theoretical but still supplied positive audit score and tuning authority.
- Walk-forward paired every daily snapshot with the immediate next date, without run purpose.
- Stability metrics mixed rule versions; transitions could look like ordinary instability.
- On PR #16 head `8dc34874cf44b6ad0db484f2ed88440780d8b731`, a current-version sequence of scheduled, diagnostic, zero-capital, development-test and scheduled snapshots produced 5 primary observations although only 2 were comparable decisions. A 09:00 scheduled `MSFT` decision followed by an 18:00 `AAPL` diagnostic on the same date retained `AAPL` as the primary sample.
- On PR #16 head `e0944a9b23a8eb3a39514a71f29b4af156d48b40`, seven causally spaced legacy snapshots produced six simulated periods classified `POINT_IN_TIME_WALK_FORWARD`; summary/full-audit confidence became `DEVELOPING`, and anti-overfitting reported six `genuine_oos_periods` with `PASS` status. Period rows omitted the inventory's purpose status and eligibility basis.
- Generic confidence could make fresh data resemble validated strategy evidence.
- Auto-apply remained technically available.

## F. Architecture after

- `src/validation_evidence.py` owns one canonical evidence hierarchy, maturity vocabulary, run-purpose taxonomy, confidence builder, validation schema version and `PROPOSAL_ONLY` tuning policy.
- The theoretical backtest is `MECHANICAL_DIAGNOSTIC`: positive results are neutral for validation, while catastrophic results retain asymmetric warning authority.
- Walk-forward first classifies run purpose, builds a causal eligible-decision timeline, and then constructs non-overlapping periods. Diagnostics remain auditable but cannot fragment the timeline.
- Legacy snapshots remain `UNKNOWN_LEGACY`; deterministic spacing can mark them `LEGACY_PARTIALLY_RECOVERABLE` without manufacturing their original purpose.
- Legacy partially recoverable periods remain simulatable and auditable, but are classified `HISTORICAL_STRESS_SENSITIVITY` with no positive strategy-validation authority.
- Period rows propagate `run_purpose`, `run_purpose_status`, `eligibility_basis`, `evidence_class` and `strategy_validation_authority`.
- Walk-forward summaries separate total simulated, genuine explicit-decision, legacy partially recoverable and other non-authoritative periods. Evidence maturity and strategy/walk-forward confidence use genuine explicit decisions only.
- Primary stability is `CURRENT_VERSION_AUDIT` over current-version `SCHEDULED_DECISION` and `MANUAL_DECISION` observations only; preserved older and non-decision history is diagnostic context.
- Model-audit daily selection preserves `(date, model_rules_version, run_purpose)` identity and applies the deterministic latest-observation rule only within that identity. A later diagnostic cannot replace a same-day genuine decision.
- Additive counts distinguish total history, all current-version observations, current-version decisions, explicit non-decisions, unknown-purpose observations and cross-version decisions.
- `CROSS_VERSION_DIAGNOSTIC` transition counts use comparable decisions only; diagnostic runs can reveal version context but cannot fabricate investment instability.
- Confidence is split into execution, data-integrity, source, strategy-validation and walk-forward dimensions.
- Tuning remains proposal-only at code level; a YAML flag cannot bypass it.

## G. Files changed

- `src/validation_evidence.py`: canonical validation contracts.
- `src/backtest_engine.py`: explicit mechanical classification and asymmetric interpretation.
- `src/walk_forward_backtest_engine.py`: run-purpose filtering, preserved causal legacy fallback, non-fragmenting periods, per-period authority metadata and separated total/genuine/legacy summary counts.
- `src/model_audit_engine.py`: current-version genuine-decision primary metrics, purpose-safe daily collapse, additive context counts and decision-only cross-version transitions.
- `src/full_audit_engine.py`: removes positive mechanical/legacy authority, scopes positive walk-forward evidence to current explicit decisions and exposes legacy diagnostic counts.
- `src/anti_overfitting_gate_engine.py`: current-version explicit-decision OOS provenance and proposal-only fail-closed gate.
- `src/model_improvement_engine.py`: proposal-only summaries and code-level refusal to auto-apply.
- `src/history_engine.py`, `src/allocation_change_engine.py`, `src/run_logging_engine.py`, `src/audit_snapshot_engine.py`: additive run-purpose/validation metadata.
- `main.py`, `scripts/run_investment_analysis.sh`: explicit CLI run purpose and trusted scheduled-decision tag.
- `README.md`, `AUDIT_GUIDE.md`, `DECISIONS.md`: operator and architecture documentation.
- Tests: focused regressions for evidence authority, walk-forward causality, version scope, confidence and tuning safety; obsolete auto-apply expectations were replaced with the corrected contract.

## H. Evidence classification

1. `LIVE_FORWARD_EVIDENCE` - strongest strategy-validation authority.
2. `POINT_IN_TIME_WALK_FORWARD` - strong only when genuinely point-in-time and comparable.
3. `HISTORICAL_STRESS_SENSITIVITY` - robustness context, not direct alpha proof.
4. `MECHANICAL_DIAGNOSTIC` - neutral mechanics plus asymmetric negative warnings.
5. `HEURISTIC_QUALITATIVE` - weakest quantitative validation authority.

## I. Backtest authority

- Backtest report: explicit class, role and `positive_validation_authority=False`.
- Full audit: good mechanical returns no longer increase strategy-validation confidence or the evidence score. Mechanical pathology can reduce the audit through a warning penalty.
- Anti-overfitting/model improvement: mechanical results cannot satisfy the genuine OOS or current-version requirements.
- Tuning: code-level `PROPOSAL_ONLY` prevents any auto-application regardless of mechanical performance.

## J. Walk-forward

- Canonical purposes: `SCHEDULED_DECISION`, `MANUAL_DECISION`, `DIAGNOSTIC`, `DEVELOPMENT_TEST`, `ZERO_CAPITAL_ANALYSIS`, `MAINTENANCE`, `UNKNOWN_LEGACY`.
- Primary explicit purposes: scheduled and manual decisions only.
- Untagged positive-capital CLI analysis becomes `UNKNOWN_LEGACY`; untagged zero-capital analysis becomes `ZERO_CAPITAL_ANALYSIS`.
- The trusted scheduled runner passes `SCHEDULED_DECISION` explicitly, including a zero-new-capital scheduled recommendation.
- Available repository history before/after: 0 total snapshots, 0 eligible decisions, 0 diagnostics, 0 legacy/unknown snapshots and 0 usable periods. No operational history was created or rewritten for this analysis.
- Focused fixtures prove that July 15 scheduled -> July 16/22 diagnostic -> July 30 scheduled yields the July 15 -> July 30 period; diagnostic rows remain present and excluded.
- Explicit scheduled/manual period class: `POINT_IN_TIME_WALK_FORWARD`; positive authority: true.
- Legacy partially recoverable period class: `HISTORICAL_STRESS_SENSITIVITY`; positive authority: false.
- Legacy-only reproduction after correction: 6 total simulated, 0 genuine OOS, 6 legacy diagnostic; summary/full-audit maturity `INSUFFICIENT`; anti-overfitting `genuine_oos_periods=0` and status `LIMITED`.
- Mixed deterministic fixture: 12 total simulated, 2 genuine explicit decisions and 10 legacy diagnostic periods; strategy-validation maturity is calculated from 2, not 12.
- A mixed aggregate summary uses the lower `HISTORICAL_STRESS_SENSITIVITY` class; its two explicit period rows individually retain `POINT_IN_TIME_WALK_FORWARD` authority.

## K. Version and purpose audit

- Available repository history: 0 total observations, 0 current-version and 0 cross-version observations.
- Primary stability sample count after correction: 0; confidence `VERY_LIMITED`; evidence maturity `INSUFFICIENT`; model health `DATA_TOO_SHORT`.
- Version-transition fixtures prove that old-version observations remain visible and do not count as current-version instability.
- Deterministic reproduction before the correction: 5 current-version primary observations versus 2 genuine decisions; the later same-day diagnostic replaced the scheduled decision.
- Deterministic fixtures after the correction preserve all 5 observations as context while the primary decision count is 2. The scheduled same-day decision remains primary and the later diagnostic is counted separately.
- No operational reports or history snapshots are present in this Mac workspace. No operational counts were fabricated and no Chromebook was accessed.

## L. Confidence

- `run_execution_confidence`: whether the validation run completed successfully.
- `data_integrity_confidence`: reliability/health of the input data.
- `source_confidence`: authority and operational health of sources.
- `strategy_validation_confidence`: maturity of genuine forward/current-version OOS periods only.
- `walk_forward_confidence`: maturity of comparable walk-forward periods.
- Both strategy and walk-forward confidence count only explicit scheduled/manual periods with genuine `POINT_IN_TIME_WALK_FORWARD` authority; total legacy simulation count is a separate diagnostic dimension.
- Existing company/security confidence fields remain unchanged and keep their original scoring roles.

## M. Evidence maturity

- `INSUFFICIENT`: fewer than 4 comparable observations.
- `EARLY`: 4-5.
- `DEVELOPING`: 6-11.
- `SUBSTANTIAL`: 12 or more.
- Raw counts are always preserved. These labels describe evidence accumulation, not proven alpha, statistical significance or strategy skill.

## N. Safe tuning

- Policy: `PROPOSAL_ONLY`.
- Suggestions may still be generated for human review with evidence class, maturity, current-version scope and genuine OOS count.
- `apply_safe_tuning` exits before reading applicability or writing files.
- Mixed-version or unversioned walk-forward periods do not count toward the current-version OOS maturity field.
- `UNKNOWN_LEGACY` / `LEGACY_PARTIALLY_RECOVERABLE` periods do not count toward `genuine_oos_periods`, tuning maturity or walk-forward tuning status.
- Residual auto-apply risk in this code path: none while the constant policy remains `PROPOSAL_ONLY`. A future policy change requires a separately reviewed chantier.

## O. Provenance predecessor verification

- PR #14 remains the single provenance/freshness architecture.
- Regression coverage verifies calibration references do not become human overrides, genuine manual/research/official authority remains intact, stale calibration cannot dominate, `AUTO_ESTIMATED` remains distinct, no VRT exception exists, and history is not rewritten.
- No compatibility defect was found and no provenance code changed.

## P. Investment-behavior regression

- Scoring changed: no.
- Rankings/eligibility changed: no.
- Allocation, VFV, sizing or concentration rules changed: no.
- Sell/thesis rules changed: no.
- `MODEL_RULES_VERSION` changed: no.
- Stable fixture regression after the chantier: 64/64 passed across scoring, allocation, final decisions and provenance/freshness.

## Q. Tests

- New deterministic model-audit purpose regressions: 15 tests added.
- New deterministic legacy-authority regressions: 16 tests added and 16 passed, including pre-v3 period-file read compatibility.
- Prompt 3 architecture: 45 passed, 0 failed, 0 skipped.
- Model audit: 19 passed, 0 failed, 0 skipped.
- Complete walk-forward: 28 passed, 0 failed, 0 skipped.
- Full audit: 5 passed, 0 failed, 0 skipped.
- Model improvement / anti-overfitting: 20 passed, 0 failed, 0 skipped.
- PR #14 / PR #15 predecessor regressions: 89 passed, 0 failed, 0 skipped.
- Investment-behavior regression: 64 passed, 0 failed, 0 skipped.
- Complete suite: 787 passed, 0 failed, 0 skipped in 24.743 seconds (25.085 seconds wall time).
- `py_compile` and `git diff --check`: passed with no output.
- The shell default was Python 3.14 while the isolated dependency cache was compiled for Python 3.12. Tests were therefore run with the configured bundled Python 3.12 runtime plus that isolated cache; no repository or production dependency was changed.

## R. History/schema compatibility

- Additive fields include `run_purpose_status`, `eligibility_basis`, per-period `evidence_class`, `strategy_validation_authority`, `genuine_oos_periods`, explicit/legacy/non-authoritative walk-forward counts, confidence dimensions and model-audit purpose counts.
- Existing JSON and CSV records remain readable. Missing metadata maps to explicit legacy uncertainty.
- No migration or destructive rewrite is required.

## S. Chromebook compatibility

- Scheduled runner: adds `--run-purpose SCHEDULED_DECISION` to the existing `analyze` command.
- CLI: optional backward-compatible `--run-purpose`; omitted metadata fails toward audit transparency and does not change the investment output.
- Drive, portfolio sync, research ingestion, Telegram, compact/full report generation and systemd architecture: unchanged.
- History: future snapshots receive additive purpose metadata.
- Deployment: deferred. After external approval, deploy code using the existing process; no service/timer edit is required.

## T. Remaining risks

- The repository copy contains no operational snapshots, so real-history before/after counts are all zero; production counts must be rechecked after approved deployment against a copied/private history set.
- Legacy purpose cannot be reconstructed perfectly. `PARTIALLY_RECOVERABLE` is deliberately uncertain and causal, not a claim of a real decision.
- `UNKNOWN_LEGACY` remains excluded from primary model-audit decisions even though the independent walk-forward legacy fallback remains unchanged.
- Legacy walk-forward outcomes can still inform historical stress/robustness review, but cannot establish known point-in-time decision authority.
- Even point-in-time walk-forward samples can remain small, regime-concentrated and statistically weak.
- The theoretical backtest remains contaminated and useful only for mechanics/warnings.
- No live forward baseline has yet accumulated enough evidence to validate skill.

## U. Confidence in the fix

- P0-A backtest authority: HIGH.
- P0-C walk-forward fragmentation: HIGH.
- P1-A model-version isolation: HIGH.
- P1-A model-audit purpose isolation and same-day safety: HIGH.
- Legacy walk-forward authority isolation: HIGH.
- P1-B confidence separation: HIGH.
- Safe tuning fail-closed: HIGH.
- P0-B predecessor preservation: HIGH.

## V. Merge recommendation

- `READY_FOR_EXTERNAL_REVIEW` after the PR is opened.
- Do not merge, deploy, pull to Chromebook, begin the concentration/allocation chantier, or declare `VALIDATION_BASELINE_V1` in this PR.
