# M2 R1 — Adaptive valuation and Expected Return method
**Status:** CANDIDATE / RESEARCH METHOD / NO NEW MODEL ADMISSION AUTHORITY. **Owner:** Investment Research.  
**Applies:** when investor mandate, source reliability and security identity support a valuation; otherwise emit conditional output or `UNAVAILABLE`.

## 1. First establish a valuation-worthy earnings/cash base
Require: economic entity and exact instrument/class; dated original-currency price; equity value and enterprise value when relevant; current shares and diluted shares (including conversion/stock comp); net debt, obligations and cash availability; latest filed year plus recent interim; organic and per-share economics; business type and cyclicality; dividends/buybacks/financing. Store source URLs, financial concept, period, audited/unaudited, GAAP/IFRS/adjusted and rights. No unsupported FX conversion, fabricated split/ADR correction, or future-payout assumption.

**Normalization bridge** (record every sign, amount and evidence):
```text
Reported earnings or CFO (basis, period)
  +/- documented unusual items, economic taxes, working capital effects
  - maintenance reinvestment (estimate labeled if not disclosed)
  - relevant lease / intangible / software cash needs
  - stock-based compensation and financing dilution economic impact
  - other necessary recurring reinvestments and financing effects
  = *conditional* normalized owner economics / per diluted share
```
This is a **method checklist**, not a mathematically universal equation for all companies. Do not double-subtract costs already included in the starting measure. CFO minus property purchases, EBITDA-capex or adjusted EPS does not automatically equal owner earnings.

## 2. Pick model by the business, not by an opaque universal score
| Economic model | Useful methods (conditional) | Material weaknesses |
|---|---|---|
| Recurring asset-light software/consumer | Normalized FCF per share, sustainable pricing/retention/reinvestment, earnings multiple | SBC, acquisitions, churn, non-GAAP addbacks |
| Asset-heavy/industrial growth | ROIC vs WACC qualitative capital logic, incremental capex return, EV/EBIT/owner cash | Incomplete capex, order/capacity cyclicality, dilution |
| Deep cyclicals/materials | Mid-cycle normalized earnings and stress balance sheet; scenario EV multiples | Peak margins, inventory and commodity spot prices |
| Biotech/pharma | Product-level cash runway, patent/competition and finite-life scenarios | Missing launch/payer/patent probabilities, false steady-state P/E |
| Banks/insurers/real estate | Sector-relevant capital or asset-value methods | Ordinary operating margins/FCF not comparable |
No mandatory method takes priority without facts and user strategy.

## 3. Transparent scenarios, not promised statistical Expected Return
For each bear/base/bull `s` and horizon `n` years, when valid, state:
- `E0`: original/corrected normalized per-share economic base and exact as-of.
- `g_s`: assumed economically possible growth, including dilution/reinvestment and specific catalysts/risks.
- `M_s`: justified terminal multiple, or other terminal valuation basis; never auto-use V2's narrowly applicable US-GAAP ordinary anchors.
- `D_s,t`: after-source-consistent per-share distributions if supported (else `UNKNOWN`, not zero).
- `P0`: verified comparable security-class quote with currency and corporate-action basis.

Illustrative **conditional** ending value (simple, valid where normalized per-share earnings and P/E are economically appropriate):
```text
E_s,n = E0 * (1 + g_s)^n
terminal_price_s = E_s,n * M_s
If cash distributions are known and their timing/reinvestment specified:
    derive total-return cash flows / IRR explicitly with a deterministic checker.
If no distributions and the instrument matches P0:
    price_CAGR_s = (terminal_price_s / P0)^(1/n) - 1
```
If distributions may matter but are unknown, a price CAGR does **not** imply a total-return CAGR. If a denominator is negative/not normalized or no valid terminal basis exists, do not force this equation. Use scenario input ranges and sensitivity; identify the source and rationale of **every** growth/multiple assumption. `BASE` is a named scenario, not a probability-weighted mean or validated Expected Return. Never fabricate probabilities.

**Mathematical cross-check:** show intermediate growth factor, terminal valuation, horizon, currency/units, dilution, total cash-flow timing and checker/tool used. If no deterministic tool ran, mark `CALCULATION_NOT_VERIFIED`. No false precision or fabricated backtested success.

## 4. VFV opportunity cost / cross-market comparison
VFV is benchmark for the canonical Canadian High-CAGR strategy. A comparison requires **comparable forward horizon, as-of basis, currency, distributions, fees, FX/corporate actions and actual defensible VFV Expected Return**. An observed ETF market quote or its historical performance does not create forward Expected Return; show `VFV_ER_UNAVAILABLE` when absent. The V2 [comparator contract](../../../../docs/contracts/v2/expected_return/COMPANY_VFV_EXPECTED_RETURN_COMPARATOR.md) has restrictive qualifying evidence/basis and is **not** automatically satisfied by ChatGPT web observations. Never claim alpha from company scenario minus fabricated benchmark return.

## 4A. IR post-test-5 comparative decision discipline (ChatGPT candidate R1.2)

For an approved High-CAGR mandate with VFV as the actual benchmark, distinguish two **independent economic outputs**. **Lane A** is conditional valuation arithmetic: security/quote date/class and native currency, model horizon, per-share normalized base and reinvestment, exit assumptions, dilution, year-by-year payout timing (UNKNOWN is not zero), `PRICE_CAGR_ONLY` versus `TOTAL_CASHFLOW_IRR_CONDITIONAL`, K/V references, calculation tool and precision. Even correctly recalculated bear/base/bull arithmetic is NOT a probability-weighted Expected Return. Never claim a ten-year scenario answers a twenty-year investor horizon without additional defensible assumptions.

**Lane B** is forward **economic opportunity-cost comparability**, which requires company and VFV to share a defensible horizon, cutoff, cash-flow return definition and comparable currency/FX basis. Document VFV's independently justified *forward* fundamentals/scenario inputs, cash distributions and known MER; do not turn an ETF's price or historic total return into a forward benchmark. Separate trading/FX costs and dividend withholding by the actual instrument, account type and residence, or label UNKNOWN. When probabilities, business-value assumptions or benchmark inputs are unsupported, emit `ER_UNAVAILABLE`, `VFV_ER_UNAVAILABLE` and/or `NOT_COMPARABLE` with specific source gaps. Do not turn a hypothetical pairwise spread into expected alpha or recommendation.

In the original IR_CAPSULE, add a compact `ECONOMIC_COMPARABILITY_BRIEF` stating both lane statuses, security and ETF, horizon mismatch, exact original S/F/K/V references, missing issuer/benchmark inputs separately, and ONE IR-owned next research question. `PORTFOLIO_ROOM = AWAITING_PI` remains separately PI-owned. Supplying a private account export does NOT cure missing company/VFV Expected Return. Preserve the existing High-CAGR company → VFV → exceptional reserve hierarchy without forcing trades or inventing new admission rules. This is a ChatGPT method refinement, **not** new policy, model certification or a numeric forecast engine.

## 5. Output contract
Produce a concise table by security / scenario: `as_of`, `native_currency`, `reported_vs_normalized_basis`, `price_status`, `E0_source`, `growth_assumption`, `terminal_method`, `distributions_treatment`, `debt/dilution_effect`, `scenario_return_or_UNAVAILABLE`, `confidence`, `principal_failure_mode`. Separate `K` calculation IDs and `V` scenario IDs. Do not report precise allocation or trade economics without PI and account context.

## R1 M2 construction — supplied-input per-share scenario arithmetic

`ai_native.valuation_scenarios.evaluate_valuation_scenarios` now implements the **deterministic checker** for a complete *bear/base/bull* set of terminal **per-share** valuations. The caller supplies: ANALYSIS_ID, request and quote cutoff, exact tradable security ID, native currency and price (with `quote_source_ref`), explicit positive integer horizon (1–30 years), Boolean same-security/corporate-action and same-currency basis confirmation, and three named scenario records. **Terminal prices must already be justified externally**; the code does not infer normalized owner earnings, growth, a target multiple, company quality or market timing.

For each scenario require `terminal_price_per_share` (nonnegative), `terminal_value_ref`, `rationale_ref`, `valuation_method` (`NORMALIZED_MULTIPLE | OWNER_CASH | MID_CYCLE | PRODUCT_RUNWAY | SECTOR_NAV | OTHER_EXPLICIT`), and `assumption_basis` (`SOURCE_FACT | THIRD_PARTY_ESTIMATE | PAM_ASSUMPTION`). `annual_distributions_per_share = null` means **UNKNOWN**, not zero; it yields a *price-only annualized CAGR*, **not total return**. To compute year-end annual cash-flow IRR, the caller must instead supply **exactly one nonnegative payment and reference for each year**, even explicit `0`. The annual IRR uses the initial price, year-end distributions and terminal price in the final year. Payment timing other than year-end, reinvestment assumptions, fees/taxes and FX require separate source-backed modeling. Known price-only/full-return scenarios are still conditional, **not expected-value forecasts**.

The helper rejects nonfinite/out-of-bounds decimals, invalid dates/horizon, missing references and unsupported security/currency basis. All three scenario outputs record `assumption_validation=NOT_PERFORMED`, provenance references and either a conditional annualized return or `UNAVAILABLE`. `expected_return_status` stays `NOT_ESTABLISHED_NO_PROBABILITIES_OR_ASSUMPTION_CERTIFICATION`; `VFV_ER_UNAVAILABLE` is preserved, never fabricated. No probability weighting, return superiority claim, ranking, account/trade cost netting, automatic policy, brokerage order or source authentication is implemented.

**M7a:** optional `valuation_inputs` on an IR-containing route, checked against the original ANALYSIS_ID and `as_of`, is retained only as `valuation_scenarios_private`. It adds a `CONDITIONAL` report caveat; calculated scenario figures do not appear as independently verified facts in the public/memory report. The helper is an arithmetic component supporting decision #21; it **does not complete normalized Expected Return**, and the 36-decision global acceptance remains deferred.

## Guarded multiple-candidate comparison

The separate `candidate_comparison.compare_candidates` helper reuses this **exact** per-security scenario evaluator for two to six candidates and performs limited pairwise BEAR/BASE/BULL **scenario-to-scenario** comparisons only under common security/currency/quote-date/horizon/cash-flow-measure basis. Mismatched scenarios are `NOT_COMPARABLE`, not a forced ordering. Even a numerical spread is not probability-weighted Expected Return, VFV forward alpha, market timing or account-specific net superiority. See `CANDIDATE_COMPARISON_R1.md`; original valuations and assumptions remain caller-reported, not authenticated.
