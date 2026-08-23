# Provenance/Freshness Correction - Before/After Impact

## Scope and evidence boundary

Starting point: `main` at `8356d527fc8aa308f15af7ab077a6189cbdc1bf5`,
with `MODEL_RULES_VERSION=2026-07-05-continuous-magnitude-scoring-v2`.

This validation checkout intentionally does not contain ignored operational files:
`data/portfolio.csv`, `data/proxy_calibration.csv`, generated manual inputs, cached
market data, or reports. No live portfolio/research data was modified or inferred.
The before/after run therefore used the same deterministic 14-ticker fixture against
an archived starting `main` tree and the corrected tree. It exercised the complete
position-analysis path through thesis, liquidation, cash-flow quality, durability,
capital-allocation score, and final action. Results below are fixture measurements,
not current live portfolio recommendations.

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

- Focused provenance/freshness and adjacent engine tests: 63 passed.
- Complete suite in an isolated Python 3.12 environment: 718 passed, 0 failed,
  0 skipped, 22.03 seconds.
- `python main.py validate-inputs` passed in an isolated copy populated only with
  the repository portfolio template; the working checkout itself correctly reports
  its intentionally absent ignored `data/portfolio.csv`.
- `git diff --check`: passed.
- No production data, systemd unit/timer, Drive path, Telegram configuration,
  operational history, portfolio holding, research PDF, or Chromebook deployment
  was modified.

Ending model version:
`2026-08-23-provenance-freshness-confirmation-v3`.
