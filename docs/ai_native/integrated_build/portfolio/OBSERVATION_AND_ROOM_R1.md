# PI R1 — Portfolio observation, exposure and room
**Owner:** Portfolio Intelligence (review pending). **Status:** candidate operational method, no verified live Blossom read. **Contract:** Project PI v0.2 and R1, integrated Operating Contract.

## Observation ledger P
An authorized actual Blossom view may be used *only after it is positively tested*, otherwise use a **dated user-provided screenshot, export or transcribed table**. Public Blossom portfolios are research context only, not the CEO's holdings.

For every material P row preserve:
- ANALYSIS_ID, P_ID and source type (tested authorized read-only view / screenshot / export / transcription).
- Captured_at with timezone (or UNKNOWN); private account and actual *observed scope*, not an implied all-account view.
- Issuer and exact tradable security ID (exchange, class, wrapper/ADR as evidence supports), account currency and market-value currency.
- Visible quantity, price/market value, weight, cash and denominator evidence **per field**; no fabricated value for cropped or unobserved components.
- Field status VERIFIED_VISIBLE / UNCERTAIN / NOT_VISIBLE. VERIFIED_VISIBLE means transcribed from the provided view only; never broker-confirmed account truth.
- Provenance, crop/missing fields, stale quote/corporate-action/FX identity flags. Record when another currency conversion was actually done, its verified rate and date.

A picture showing several positions does not prove cash=0 or all accounts included. Report UNKNOWN unless explicitly visible or user-verified.

## Exposure and portfolio-room procedure
1. Reconcile security identity and economic issuer; multiple listings/ADRs may represent one economic company. ETF holdings, regions and look-through are included **only if independent actual composition evidence is accessible and dated**.
2. Compute position/issuer/sector and currency exposures **only within an explicitly complete scoped denominator**, consistent date and verified common currency. Otherwise provide qualitative overlap or CONDITIONAL/UNAVAILABLE; do not guess market weights.
3. Preserve Quality/Durability/Expected Return/Confidence from Research with actual IR source and method versions; do not promote SPECIALIST_REPORTED to VERIFIED. PI owns Portfolio Room, not a re-written issuer thesis.
4. Determine whether additional new capital fits approved strategy, company evidence, existing concentration, correlated drivers, cash/benchmark options, and account restrictions. A position above a conceptual target through appreciation is not automatically sold.
5. Status: ROOM_EVIDENCE_SUPPORTED / ROOM_CONDITIONAL / ROOM_UNAVAILABLE; list decisive missing P/IR records, not fake optimal weights.

The actual V2 High-CAGR strategy has approximate conceptual diversification/concentration guidelines in the Constitution. They require correct context and no silent numeric override. PI R1 does **not** inherit the detailed V1/V2 allocation engine thresholds or return a mechanical score.

## Privacy and scope
Keep **private account/screenshot/value/lot details outside public repo**, including PR summaries, fixture data, logs and institutional memory. Only synthetic data may occur in source-controlled tests. Never claim a live account link or actual cost basis from an image. No trades or portfolio-sync service.

## M3 construction continuation — private, structured P ledger helper

`ai_native.portfolio_observation.prepare_observation_ledger` accepts **structured, user-supplied transcriptions** of dated screenshots, exports, tables or a caller-confirmed authorized read-only Blossom view. It **does not perform OCR, inspect images or authenticate the Blossom connection**. The caller supplies `analysis_id`, ISO `observed_on`, `analysis_as_of`, an offset-aware `captured_at` timestamp (or `UNKNOWN`), `source_type`, explicit private/public scope, `account_scope`, account-base `currency`, completeness, explicit cash amount/status, common currency-basis assertion and P records. The helper never invents a missing holding or account.

Each P row supplies `p_id`, `security_id`, account scope, currency, nonnegative `market_value_base` decimal if visible and field-status mapping `security_id`, `market_value_base`, `currency`, `account_scope` using `VERIFIED_VISIBLE | UNCERTAIN | NOT_VISIBLE`. These are **caller-reported visibility states**, not a new broker/source certification. Absence of status is `NOT_VISIBLE`. Duplicated/reserved P IDs, invalid money, source/scope conflicts or future observation dates are rejected. Public Blossom references **cannot** be treated as private holdings.

A source-confirmed, timestamped, complete, cash-inclusive, one-account-currency and fully visible P ledger may return `SCOPED_WEIGHTS_DERIVED_FROM_CALLER_VISIBLE_DATA`: *scoped* market values and display percentages reconcile exactly to 100.00% via deterministic largest remainders. These are not whole-household weights unless scope actually covers it. If cash is hidden, a field uncertain, a different currency unconverted, timestamp unknown or scope incomplete, **no weights or denominator** are calculated; specific gaps remain in `missing_or_qualified`. The helper deliberately always reports `portfolio_room_status=ROOM_UNAVAILABLE`: portfolio positioning and research must still supply a strategy-supported thesis and risk budget.

The entire `p_ledger_private`, `cash_record_private`, derived totals and weights are **private return values**. No GitHub write, media copy, source retrieval, account connection, archival/scheduled operation or trade. Tested only on synthetic transcriptions, not screenshots, Blossom private holdings or actual broker data. This advances decisions #16–18 as partial build work and does not pass any READY gate.

## R1 Work visual source bridge

See [Work-to-Blossom visual packet contract](./WORK_BLOSSOM_HANDOFF_R1.md) for the preferred CEO-authorized read-only Work acquisition path. Work must **actually see** a private account view; a public profile or a declared Work capability is not holdings evidence. The narrow `work_blossom_adapter.prepare_work_blossom_observation` maps a privately copied Work-reported observation (or dated screenshot fallback) into this existing P-ledger and does not browse, authenticate or initiate messages. Fields remain caller-reported and incomplete scopes produce no weights. The web application's support for authenticated private account views remains `NOT_TESTED`.

## M3 economic-exposure construction — direct holdings + supplied fund look-through

`ai_native.portfolio_exposure.aggregate_portfolio_exposures(ledger, classifications_by_p_id=...)` is a pure PRIVATE exposure aggregator that **reuses the existing complete-scope P-ledger denominator**. No holdings, FX, securities classification or ETF constituents are fetched. A classified direct equity contributes its actual scoped gross value to its supplied `economic_issuer_id`, `sector` and `region`. A fund contributes only documented `constituents`, each with a `fund_weight_pct`, `economic_issuer_id`, `sector` and `region`; the ETF's **wrapper/manager is not counted as another look-through issuer**. Repeated underlying issuer IDs across a direct position and a fund aggregate into one known exposure, not twice the held ETF's value.

**Classification contract:** map only actual P_IDs to `security_id`, `kind = DIRECT_EQUITY | FUND`, `source_ref`, ISO `as_of` no later than P observation date, `rights_status = PERMITTED | UNCERTAIN | RESTRICTED` and required economic classifications. Fund records additionally require `composition_complete_reported` and `constituents`. Claiming complete fund coverage requires all supplied fractions to sum exactly 100%; when fewer known fractions exist, the residual is preserved as `unclassified_or_unknown_fund_pct`. Missing P classification, uncertain or restricted source use become UNKNOWN, never zero. The rights and completeness declarations are **caller-reported, not independently licensed or verified**; no stale-source age threshold or source-availability qualification is inferred by code.

**Outputs:** known economic issuer, sector and region percentages **within the exact original account scope**, separate cash, exact known/unknown capital fractions, fund-coverage status, original classification dates/refs/rights and source-confidence limits. Percentages are displayed to two decimals and **can differ from 100.00 by rounding**; underlying arithmetic uses Decimal exact market values and complete scoped denominator. `economic_issuer_rank_coverage_reported_complete` only means no declared composition gaps under supplied classifications, not a proof of full household reach or real diversification. Region classifications are **not** economic revenue geography, currency exposure, FX risk or an audited sector taxonomy. Nothing computes Portfolio Room, buy/sell/trimming, allocation optimization or a policy threshold.

`complete_manual_session(..., observation_inputs=..., exposure_classifications=...)` accepts these only after the private PI observation, returns `portfolio_exposures_private` even while waiting for PI_DELTA, and refuses an incoming `ROOM_EVIDENCE_SUPPORTED` PI assertion when this supplied look-through is partial. An observed or economically classified position does not by itself prove thesis, risk budget or investment admission. No private positions, account values or reference locators may enter GitHub memory or Media.

**Construction checks:** 22 new synthetic exposure tests plus 5 new bridge cases, run together with 44 inherited local P/bridge tests (71 passing). These verify the existing P-helper and a **local prior M1→M7a bridge**, not the entire latest canonical repository; verify current integration separately before any readiness claim. Real Blossom/private evidence and complete 36-decision acceptance remain outside this component's scope.
