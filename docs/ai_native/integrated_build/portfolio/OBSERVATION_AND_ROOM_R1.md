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
