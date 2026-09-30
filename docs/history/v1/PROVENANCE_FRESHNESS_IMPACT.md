# Provenance/Freshness Correction - Before/After Impact

## Scope and evidence boundary

Starting point: `main` at `8356d527fc8aa308f15af7ab077a6189cbdc1bf5`,
with `MODEL_RULES_VERSION=2026-07-05-continuous-magnitude-scoring-v2`.

The initial fixture validation checkout intentionally did not contain ignored operational files:
`data/portfolio.csv`, `data/proxy_calibration.csv`, generated manual inputs, cached
market data, or reports. No live portfolio/research data was modified or inferred.
The before/after run therefore used the same deterministic 14-ticker fixture against
an archived starting `main` tree and the corrected tree. It exercised the complete
position-analysis path through thesis, liquidation, cash-flow quality, durability,
capital-allocation score, and final action. Results below are fixture measurements,
not current live portfolio recommendations.

The closure validation below subsequently used read-only copies of the real mounted
operational inputs and a single frozen cache snapshot in isolated temporary trees.

## Reproduced root cause

The suspected path was exact:

1. `balance_sheet_strong_true` was Category A in `sync_manual_inputs_command()`.
2. Category A ignored source age; an observation dated `2025-01-01` was still written.
3. The generated file retained values but no field-level origin or source date.
4. `load_friendly_manual_inputs()` added every populated field to
   `manual_override_fields`.
5. `merge_automated_with_manual_overrides()` replaced fresher automated/official
   evidence and removed its automatic/official source labels.
6. Thesis, liquidation, and durability confirmation helpers treated membership in
   `manual_override_fields` as confirmation.
7. A VRT-like stale calibration `balance_sheet_strong=FALSE` therefore produced
   `THESIS=WEAKENING` with reason `Bilan financier affaibli confirmé.`

## VRT-like contradiction

| Field | Before | After |
|---|---|---|
| `balance_sheet_strong` | `FALSE` | `TRUE` from current stable fixture data |
| Old calibration FALSE retained | Value only, origin erased | Yes, as contextual evidence |
| Calibration provenance | Misclassified as manual | `PROXY_CALIBRATION_SYNC` |
| Calibration date/freshness | Lost / effectively timeless | `2025-01-01` / `STALE` for balance sheet |
| Human-confirmed | Yes | No |
| Currently authoritative | Yes | No |
| Evidence conflict | Hidden | Visible on `balance_sheet_strong` |
| Thesis | `WEAKENING` | `INTACT` |
| Thesis reason | Confirmed weakened balance sheet | No major fundamental break; conflict monitored separately |
| Monitoring | `WATCH` | `MANUAL_REVIEW` |
| Liquidation | `YELLOW` | `GREEN` |
| Confirmed fundamental sell evidence | None | None |
| Cash-flow quality | `EXCELLENT_CASH_COMPOUNDER` / 96 | Unchanged |
| Net debt / FCF | `-2.0x` | Unchanged |
| FCF margin / growth | 18% / 66% | Unchanged |
| Cycle risk | `MEDIUM` | Unchanged |
| Valuation watch | `NORMAL` | Unchanged |
| Allocation decision | `DO_NOT_ADD` | `NO_NEW_ALLOCATION` |
| Final action | `WATCH` | `NO_NEW_ALLOCATION` |
| Capital-allocation score | 0 | 86.12 |
| Conviction / fundamental score | 90 / 8.1 | Unchanged |

The fixture does not force this final action. It demonstrates that corrected
provenance removes the false fundamental break while preserving a manual-review
conflict. Live valuation/cycle/portfolio inputs can still independently produce
`WATCH`, `DO_NOT_ADD`, or another existing outcome.

## Model-wide fixture impact

"Material" means an absolute change of at least 1.0 point for the 0-100 capital
or conviction score. It is an impact-measurement threshold only, not an investment
rule.

- Tickers evaluated: 14
- Tickers with provenance-only changes: 5
- Changed thesis status: 9
- Changed monitoring status: 9
- Changed liquidation status: 9
- Changed allocation decision: 9
- Changed final position action: 9
- Materially changed capital-allocation score: 9
- Materially changed conviction score: 0
- Materially changed fundamental `score_total`: 1 (`OLD_MOAT`)
- Unexpected changes: 0

| Ticker | Classification | Decision impact |
|---|---|---|
| `VRT` | `EXPECTED_FRESHNESS_FIX` | Stale false balance sheet no longer forces confirmed weakening; conflict remains visible. |
| `OLD_BAL` | `EXPECTED_FRESHNESS_FIX` | Same systemic balance-sheet correction as VRT. |
| `FRESH_BAL` | `EXPECTED_PROVENANCE_FIX` | Fresh calibration may replace an automatic proxy but remains unconfirmed and under manual review. |
| `RESEARCH_BAL` | `EXPECTED_CONFLICT_FIX` | Fresh high-confidence research outranks stale calibration; conflict remains visible. |
| `OFFICIAL_BAL` | `EXPECTED_CONFLICT_FIX` | Current official evidence outranks stale calibration; conflict remains visible. |
| `UNDATED_BAL` | `EXPECTED_FRESHNESS_FIX` | Undated calibration remains contextual and cannot force weakening. |
| `OLD_MOAT` | `EXPECTED_FRESHNESS_FIX` | Expired qualitative calibration no longer forces weakening; `score_total` rises 7.1 to 8.1. |
| `HUMAN_NEG` | `EXPECTED_PROVENANCE_FIX` | Provenance metadata added only; genuine negative human confirmation remains weakening. |
| `RESEARCH_NEG` | `EXPECTED_PROVENANCE_FIX` | Metadata-only; qualifying negative research remains weakening. |
| `OFFICIAL_NEG` | `EXPECTED_CROSS_ENGINE_FIX` | Current official negative evidence now confirms real weakening instead of being treated as automatic. |
| `AUTO_NEG` | `EXPECTED_PROVENANCE_FIX` | Metadata-only; automatic negative remains unconfirmed/manual-review evidence. |
| `REAL_CURRENT_NEG` | `EXPECTED_CROSS_ENGINE_FIX` | Real current official deterioration still produces weakening and blocks additions. |
| `VALUATION_ONLY` | `EXPECTED_PROVENANCE_FIX` | Metadata-only; fundamental thesis stays intact while valuation watch remains separate. |
| `CATASTROPHIC` | `EXPECTED_PROVENANCE_FIX` | Metadata-only; catastrophic `BROKEN` protection remains intact. |

## Real operational same-input validation

The complete normal `high-cagr` analysis path ran once at the base commit and once
at the corrected tree with capital `0`. Both isolated trees received byte-identical
copies of the mounted Drive inputs, state backup, 84 BNCD/Morningstar PDFs, prior
report state, and the same 995-file market cache snapshot. The cache byte-manifest
SHA-256 was `9881efd195391296d8e6dc0e9787f79c8a991821e5b2c57b828a8d5f62ef9af6`.
No refresh flag was used: 264 unique evaluated tickers used `FRESH_CACHE`; `FI`
remained identically unavailable in both runs and was not among the changed rows.
The mounted `portfolio.csv`, `proxy_calibration.csv`, and legacy generated friendly
file remained byte-identical to their pre-run copies.

- Evaluated rows: 266 across core, watchlist, market-scanner, and discovery universes.
- Unique evaluated tickers: 265.
- Changed rows across the requested evidence/decision fields: 92 (91 unique tickers;
  `TSLA` appears in two evaluated universes).
- Tickers with an actual thesis, monitoring, liquidation, confirmed-sell,
  allocation, or final-action change: 76.
- Tickers with score-only or reason-only changes: 15 (`ADBE`, `AIR.PA`, `EFX`,
  `FTNT`, `FTS.TO`, `FTV`, `HD`, `KLAC`, `MA`, `MPWR`, `NEE`, `NVDA`, `RTX`,
  `SCHW`, `UDR`).
- Field-difference classifications: 80 `EXPECTED_PROVENANCE_FIX`,
  84 `EXPECTED_FRESHNESS_FIX`, 60 `EXPECTED_CONFLICT_FIX`, and
  671 `EXPECTED_CROSS_ENGINE_FIX`.
- `UNEXPECTED`: 0.

The 19 real tickers carrying metadata-free legacy calibration fields were `AAPL`,
`ANET`, `APH`, `APP`, `ASML`, `AVGO`, `CBOE`, `COST`, `CSU.TO`, `GOOGL`, `INTU`,
`LLY`, `MA`, `META`, `MSFT`, `RHM.NE`, `TOI.V`, `TSLA`, and `VRT`. Their origin,
freshness, confirmation, conflict, reliability, score, and downstream decision
differences follow directly from reclassifying the same legacy values as undated
calibration rather than human confirmation. The other changed rows are the intended
cross-engine consistency effect: 69 carry current official confirmation and 12
carry research evidence that the old engine-local confirmation rules handled
inconsistently; all 72 carry automatic evidence that now uses the central rule.

Actual decision/status/action changes occurred for:

`AAPL`, `ABT`, `AEP`, `AJG`, `AMZN`, `ANET`, `AON`, `APH`, `APP`, `ARAY`, `ASML`,
`AVGO`, `BRK-B`, `C`, `CB`, `CBOE`, `CEG`, `CMG`, `COST`, `CPRT`, `CRWD`, `CSU.TO`,
`ETN`, `GEV`, `GILD`, `GOOGL`, `INTC`, `INTU`, `IQV`, `JNJ`, `LLY`, `MELI`, `META`,
`MFC.TO`, `MSFT`, `MU`, `NEM`, `NOW`, `PG`, `PGR`, `QCOM`, `RHM.NE`, `SBAC`, `SJM`,
`SLB`, `SNOW`, `SNPS`, `SOLV`, `SPG`, `STT`, `SW`, `SWKS`, `T`, `TAP`, `TECH`,
`TGT`, `TOI.V`, `TRMB`, `TSCO`, `TSLA`, `TTD`, `TTWO`, `UAL`, `UBER`, `UHS`, `UPS`,
`VICI`, `VRSK`, `VRT`, `VST`, `VTRS`, `VZ`, `WBD`, `WTW`, `XYZ`, `YUM`.

### Real VRT result

| Field | Base | Corrected |
|---|---|---|
| Thesis | `WEAKENING` — confirmed weakened balance sheet | `INTACT` — no major fundamental break |
| Monitoring | `WATCH` | `MANUAL_REVIEW` for source conflict |
| Liquidation | `YELLOW` | `GREEN` |
| Confirmed fundamental sell signals | None | None |
| `balance_sheet_strong` | `FALSE`, treated as manual/confirmed | `TRUE` from current data; legacy `FALSE` retained as contextual evidence |
| Calibration freshness | Origin/date absent | `UNKNOWN_DATE`, non-authoritative |
| Evidence conflict | Not surfaced | `TRUE`: balance sheet plus six other calibration/current-source differences |
| Data reliability | `HIGH` / 93.88 | `HIGH` / 88.88 |
| Fundamental score | 6.43 | 7.91 |
| Capital-allocation score | 0 | 58.69 |
| Conviction score | 97 | 90 |
| Allocation decision | `DO_NOT_ADD` | `NO_NEW_ALLOCATION` |
| Final action | `WATCH` | `NO_NEW_ALLOCATION` |

The operational legacy friendly file was also exercised separately against the
current operational calibration source in a temporary migration probe. All populated
legacy values were equivalent, so the safeguard allowed metadata generation there;
the real Drive file remained unchanged.

## Freshness and precedence policy

- 90 days: valuation and forward-looking calibration fields.
- 120 days: balance sheet and margin-pressure observations.
- 180 days: margin-direction observations.
- 365 days: sector-growth observations.
- 548 days: historical ROIC and EPS-growth observations.
- 730 days: moat and management-quality observations.
- Missing dates: contextual, non-authoritative.

Precedence is limited to the defect scope: explicit human overrides remain first;
qualifying research and current official evidence outrank calibration; current
calibration can correct an automatic proxy but is not human-confirmed; stale or
undated calibration is preserved but not applied. Conflicting evidence is retained
and surfaced instead of silently deleted.

## Verification

- Focused provenance/freshness tests: 18 passed.
- Focused plus adjacent engine tests: 84 passed.
- Complete suite in an isolated Python 3.12 environment: 722 passed, 0 failed,
  0 skipped, 21.86 seconds.
- `python main.py validate-inputs` passed in an isolated copy populated only with
  the repository portfolio template; the working checkout itself correctly reports
  its intentionally absent ignored `data/portfolio.csv`.
- `git diff --check`: passed.
- No production data, systemd unit/timer, Drive path, Telegram configuration,
  operational history, portfolio holding, research PDF, or Chromebook deployment
  was modified.

Ending model version:
`2026-08-23-provenance-freshness-confirmation-v3`.
