# M2 R1 — Source-linked fundamental economics dossier

**Status:** `DESCRIPTIVE_INDICATIVE / ORIGINAL_SOURCE_CHECK_NOT_PERFORMED_BY_CODE / NOT_DECISION_GRADE`  
**Primary role:** Investment Research, specialist review pending.

## Real economic question

Before using any bear/base/bull terminal price, determine **what actually drives the business economics**. The optional `ai_native.fundamental_dossier.prepare_fundamental_dossier` turns an **existing M2 source-fusion annex** into a compact private issuer dossier, retaining original `S/F` observations, definitions and dates. It is not a new source fetcher, normalized owner-earnings engine, artificial moat score, V2 policy replacement or global company ranking.

The caller supplies exactly one `analysis_id/as_of`, `economic_issuer` and `instrument`, the existing source annex, the **original** IR capsule's fact-ID list, selected previous/current observation-ID pairs and three qualitative analyses.

### Supported descriptive numbers

| Exact original metric pair | Output if compatible | What it does **not** establish |
| --- | --- | --- |
| `REVENUE` | Reported change between two annual periods | Organic growth, acquisitive vs FX-neutral demand or CAGR |
| `OPERATING_INCOME` + `REVENUE` | Prior/current reported operating margin | Adjusted normalization, segment-return quality or peer comparability |
| `CFO` + `CASH_CAPEX` | Descriptive CFO minus positive cash investment outflow | Maintenance capex, stock compensation, leases, sustainable owner cash or valuation base |
| `DILUTED_AVG_SHARES` | Change in comparable diluted weighted-average share count | Complete future economic dilution or buyback quality |

- Every pair uses unique existing `observation_id`, original matching `fact_id`, **one** issuer/instrument/metric and sequential comparable full annual periods. Caller explicitly asserts period comparability; code also guards annual length, accounting basis, consolidation, units and currency. Results are withheld for incomplete/conflicted/restricted/post-cutoff observations, secondary source claims and misleading cash-investment sign conventions.
- The source annex may label a primary filing as `CALLER_REPORTED_ONLY`. Even a numerical calculation grounded in that record is **INDICATIVE**, not independently authenticated or qualifying PIT evidence. A missing publication date, changed accounting basis, unit, source right or original check **blocks the particular derived calculation**, not all valid information about the issuer.
- If revenue is zero/non-positive or operating income periods are incompatible, do not produce the corresponding growth/margin. CFO minus cash capex retains the permanent `NOT_NORMALIZED_OWNER_EARNINGS` warning. For noncorporate business models (banks, insurers, investment vehicles) use specialist-appropriate original facts rather than forcing this industrial model.

### Qualitative economics belong to an analyst

Require three linked counter-thesis records: `COMPETITIVE_POSITION`, `REINVESTMENT`, `PERMANENT_LOSS`. Each has `status=SPECIALIST_REPORTED | UNKNOWN`, a reasoned thesis, explicit countercase and `ir_fact_ids` existing in the original IR capsule. The helper preserves uncertainty and stops a false `BROKER_VERIFIED` or self-awarded authority claim. **No automated QUALITY, DURABILITY, CONFIDENCE or Expected Return verdict** follows. Original issuer facts alone do not prove a moat; organic growth and acquisition mix remain `UNKNOWN` until actually analyzed.

### Private R1 M7a integration

An IR-including manual route may provide both `source_evidence_inputs` and `fundamental_inputs` to `complete_manual_session`. M7a first runs the **existing** `assemble_source_fusion`, verifies IDs belong to the original IR capsule, and then builds `fundamental_dossier_private` using the source annex. `fundamental_inputs` has exactly five fields: `economic_issuer`, `instrument`, `period_pairs`, `annual_periods_comparable_reported`, `qualitative_axes`. It does **not** accept free-form research conclusions as verified figures. Without the source annex, the fundamental dossier is refused.

The report becomes `CONDITIONAL` and refers to the private annex without exposing account context or manufactured investment superiority. No account access, financial data expense, automated Project invocation, source persistence or trading. Full integrated real-M7a regression and original source checks remain for proportional technical review and the later comprehensive 36-decision acceptance.

**Validation boundary:** 20 local synthetic tests PASS, compile PASS, GitHub blob identity checked. No actual issuer financial records, full current-repo regression, Work browser session, Portfolio Room or authentic decision-grade company evidence tested.
