# Deep Drawdown Allocation Safeguard - Engineering Impact Report

## Starting state

- Git SHA: `932f8b32661c7c6e5ea20af6dbf559a2a523102c`
- Branch: `codex/fix-deep-drawdown-allocation-safeguard`
- Starting `MODEL_RULES_VERSION`: `2026-08-23-research-freshness-authority-v5`
- Ending `MODEL_RULES_VERSION`: `2026-08-23-deep-drawdown-allocation-safeguard-v6`
- `VALIDATION_SCHEMA_VERSION`: unchanged at `2026-08-23-validation-architecture-v3`
- Provenance/freshness predecessor: present and preserved.
- Validation-authority/history predecessor: present and preserved.

## Existing architecture found

`load_portfolio()` retains account lots. `resolve_portfolio_lot_rows()` canonicalizes
each lot for account reporting, while `resolve_portfolio_rows()` aggregates the same
canonical ticker across all accounts. The aggregate sums shares and compatible
acquisition cost, marks mixed cost currencies unusable, and is then passed through
`enrich_portfolio_with_market_data()`, which converts both market value and cost to
CAD. `add_position_weights()` and `compute_portfolio_risk()` therefore operate on one
economic Portfolio 1 + Portfolio 2 representation for ticker, sector, region,
currency, factor, cluster, and total concentration.

The allocation path already contained `_quality_drawdown_allocation_exception()`,
`_marginal_monthly_score()`, `_available_monthly_room()`, the high-CAGR overflow
path, reliability metadata from `compute_data_reliability()`, canonical conflict
profiles from `source_conflict_engine`, and the existing account SVG renderer in
`account_charts.py`. Those components were reused; no new allocation, reliability,
risk, chart, transaction-memory, or concentration subsystem was created.

## Cost-basis validation

The safeguard uses only normalized `current_value_cad` and
`acquisition_value_cad`. The latter is the current position acquisition value
derived from shares and average cost, or an explicit cost basis, and is aggregated
only while account rows use a compatible cost currency. The loader already handles
partial-position state through the current shares/average-cost representation; it
does not reconstruct transaction history for this calculation.

The combined return is:

`combined_position_return = current_value_cad / acquisition_value_cad - 1`

It is valid only for an owned position with non-negative CAD current value and a
positive CAD acquisition value. Missing, malformed, non-positive, mixed-currency,
or unconverted cost is `UNKNOWN`. A current value produced by the existing
`acquisition_value_fallback` is also `UNKNOWN`, because using cost as both numerator
and denominator would fabricate a zero return. No synthetic return is created.

## Drawdown logic before

- The quality-drawdown exception checked quality, mode, expected CAGR,
  opportunity cost, news, valuation, quality-drawdown score, conviction, business
  quality, and durability.
- It did not require canonical `HIGH` evidence reliability or reject material
  unresolved evidence conflicts.
- Positive drawdown inputs could raise the capital-allocation score, marginal
  score, and candidate ordering for an owned position without that stronger
  evidence gate.
- Allocation room had no combined cost-basis `-20%` evidence safeguard.

## Drawdown logic after

- One explicit policy constant is used:
  `DEEP_AVERAGING_DOWN_THRESHOLD = -0.20`.
- Existing quality requirements are preserved.
- The quality-drawdown exception now additionally requires canonical
  `data_reliability_level == HIGH`, no existing
  `requires_manual_validation_for_large_allocation`, and no material unresolved
  conflict.
- Existing positive drawdown rewards are retained only when that strengthened
  exception passes. Negative quality-drawdown adjustments remain intact.
- At a valid combined return `<= -20%`, failed evidence quality sets normal and
  high-CAGR overflow allocation room to zero for the current analysis.
- At a valid combined return `<= -20%`, strong clean evidence removes only this
  special block; every normal concentration, sizing, capital, drift, opportunity,
  and risk limit remains authoritative.
- The rule is stateless. Evidence recovery automatically restores normal behavior
  on the next analysis.
- New candidates are not subject to an averaging-down cost-basis rule.
- Missing cost basis remains `UNKNOWN` and does not activate the special hard block.

## Reliability and conflict gating

The implementation reuses these existing statuses and fields:

- Strong reliability: `data_reliability_level == HIGH` and no active
  `requires_manual_validation_for_large_allocation`.
- Material unresolved source profiles: `DIRECTIONAL_REVIEW` and
  `MATERIAL_REVIEW`.
- Current provenance conflict: `fundamental_evidence_conflict == True`.
- Non-blocking minor profile: `TECHNICAL_OR_PERIOD_DIFFERENCE`.

Unknown reliability is not `HIGH` and therefore cannot create a positive
averaging-down exception. `UNPARSED_REVIEW` is not silently relabeled material;
the existing classifier must first identify a material or directional conflict.

## Auditable output

The analysis and quality-drawdown CSV structures now expose the combined return,
threshold status, reliability, conflict profile, exception result, block flag, and
reason. A blocked ticker receives an allocation log and allocation-decision reason
equivalent to:

`DEEP AVERAGING DOWN BLOCKED: combined position return <= -20%; evidence quality is insufficient or materially unresolved.`

The sell decision is read from the unchanged liquidation/sell architecture.

## Controlled before/after fixture impact

The comparison used identical deterministic fixtures, CAD values, a $10,000
portfolio, and a $1,000 high-CAGR contribution. The pre-change path was reproduced
with the prior quality exception and no deep-room block; the post-change path used
the implemented policy.

| Ticker | Combined return | Reliability | Conflict | Exception before -> after | Drawdown adjustment before -> after | Room before -> after | Allocation before -> after | Final action before -> after | Amount before -> after | Sell before -> after | Classification |
| --- | ---: | --- | --- | --- | ---: | ---: | --- | --- | ---: | --- | --- |
| `WEAK_DEEP` | -25% | MEDIUM | none | pass -> fail | +5 -> 0 | $400 -> $0 | BUY / ADD -> DO_NOT_ADD | BUY / ADD -> DO_NOT_ADD | $400 -> $0 | HOLD -> HOLD | `EXPECTED_RELIABILITY_GATING` |
| `CONFLICT_DEEP` | -25% | HIGH | MATERIAL_REVIEW | pass -> fail | +5 -> 0 | $700 -> $0 | BUY / ADD -> DO_NOT_ADD | BUY / ADD -> DO_NOT_ADD | $700 -> $0 | HOLD -> HOLD | `EXPECTED_CONFLICT_GATING` |
| `WEAK_MINUS_15` | -15% | MEDIUM | none | pass -> fail | +5 -> 0 | $400 -> $400 | BUY / ADD -> BUY / ADD | BUY / ADD -> BUY / ADD | $400 -> $400 | HOLD -> HOLD | `EXPECTED_RELIABILITY_GATING` |

Unchanged controls:

- `STRONG_DEEP` at -25% retained the exception, $700 normal room/allocation, and
  `HOLD` sell decision.
- `MISSING_COST` remained outside the special `-20%` classification and retained
  normal existing behavior.
- `NEW_CANDIDATE` remained outside the averaging-down rule.
- No `UNEXPECTED` change was observed.

### Fixture blast radius

- Owned tickers evaluated: 5
- Valid combined returns at or below -20%: 3
- At or below -20% with strong clean evidence: 1
- Blocked due to reliability: 1
- Blocked due to material conflict: 1
- Allocation amounts changed: 2
- Sell actions changed: 0

Current operational `data/portfolio.csv`, manual inputs, calibration inputs, and
generated reports are not present in this local checkout. No current holding impact
was fabricated, and no operational file was modified.

## Combined portfolio chart

`build_account_allocation_chart_rows()` still renders every account-specific SVG
with the existing size, typography, colors, legend, labels, small-position grouping,
and output directory. It now adds `charts/account_ALL_ACCOUNTS.svg` last in the
report. The same canonical lot rows are summed by ticker for the combined slice, so
a cross-account duplicate appears once.

The smoke fixture produced:

- TFSA1 chart: generated.
- TFSA2 chart: generated.
- ALL_ACCOUNTS chart: generated and referenced by report markdown.
- MSFT: $400 / 40%, one slice.
- AAPL: $200 / 20%.
- VFV.TO: $400 / 40%.
- Total: $1,000 / 100%.

The rendered SVG was visually inspected with no clipping, overlap, broken labels,
or style regression.

## Files and functions changed

- `src/allocation_engine.py`: policy constant, combined return, strengthened
  exception, positive-reward gating, room/overflow block, audit annotations/log.
  Functions: `apply_deep_averaging_down_context()`, `allocate_capital()`,
  `_candidate_sort_key()`, `_available_monthly_room()`,
  `_marginal_monthly_score()`, `_high_cagr_overflow_eligible()`,
  `_high_cagr_overflow_room()`, `_quality_drawdown_allocation_exception()`, and
  narrowly scoped safeguard helpers.
- `src/sizing_engine.py`: suppresses only positive drawdown score/adjustment inputs
  for owned positions when the strengthened exception fails; scoring weights are
  unchanged.
- `main.py`: applies safeguard context before allocation scoring and exposes the
  block as `DO_NOT_ADD`; sell combination logic is unchanged.
- `src/quality_drawdown_engine.py` and `src/report_generator.py`: audit fields in
  existing CSV/report structures.
- `src/account_charts.py`: adds the all-accounts bucket and combined SVG while
  preserving the existing renderer.
- `src/model_version.py`: advances the behavior version.
- `DECISIONS.md`: records problem, risk, policy, aggregation, chart, non-goals, and
  versioning.
- Tests: focused safeguard, aggregation, chart, report-reference, threshold,
  recovery, missing-cost, new-candidate, and sell-side regressions.

## Tests

- Focused and relevant allocation/report suite: 138 passed, 0 failed, 0 skipped.
- Final complete suite: 803 passed, 0 failed, 0 skipped in 21.813 seconds
  (22.54 seconds wall time).

No failing test was removed, no assertion was weakened to conceal behavior, and no
operational fixture was updated.

## Chromebook compatibility

The scheduled analysis command, `--refresh-market-data`, Google Drive sync,
`portfolio.csv`, proxy calibration, manual-input sync, BNCD/Morningstar ingestion,
Telegram capital confirmation, report and compact-report generation, history
persistence, chart directories, and maintenance workflows retain their interfaces.
No systemd unit, timer, Drive path, report path, history path, Telegram setting, or
schedule changed. The added SVG uses the existing report chart directory and naming
convention.

Nothing was deployed or pulled onto the Chromebook. After external review and a
separate approved merge, the eventual Chromebook action is the normal reviewed-code
update followed by the usual fixture/report smoke check; no systemd change is
required.

## Remaining limitations

- A mixed, missing, malformed, or unconverted acquisition cost cannot support the
  special return calculation and remains explicitly `UNKNOWN`.
- The calculation uses the current position cost basis supplied by `portfolio.csv`;
  it does not reconstruct historical tax lots or transaction memory.
- Operational portfolio impact could not be measured because ignored operational
  inputs are absent locally.
- The -20% threshold is an explicit pre-validation safety policy. It was not tuned,
  swept, or evaluated as an alpha claim.

## Final self-review

- Canonical Portfolio 1 + Portfolio 2 aggregation preserved: YES.
- Combined normalized cost basis used where valid: YES.
- Invalid cost fabricated: NO.
- Exactly one explicit deep threshold: YES, -20% inclusive.
- Historically optimized: NO.
- Strong clean evidence restores normal logic: YES.
- Weak/materially conflicted deep evidence gets zero room: YES.
- Automatic sell introduced: NO.
- Persistent block/cooldown introduced: NO.
- New candidates blocked: NO.
- Concentration thresholds or scoring weights changed: NO.
- Drawdown-specific rewards gated without removing unrelated scoring: YES.
- Block reason auditable: YES.
- New reliability, risk, chart, or Portfolio 2 engine created: NO.
- Duplicate cross-account ticker rendered once in combined chart: YES.
- Operational data modified: NO.
- Deployment performed: NO.

## Risk and recommendation

Deployment risk: **LOW**. The change is narrow, fail-closed for additional capital,
stateless, fully separated from sell logic, and covered by focused and complete
regression tests. The principal limitation is unavailable local operational data,
which prevents a real-holdings impact count before external review.

Merge recommendation: **READY_FOR_EXTERNAL_REVIEW** after the final complete suite
and unmerged PR checks pass.
