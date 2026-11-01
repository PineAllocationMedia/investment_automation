# PAM Financial Systems — five-prompt manual workflow v1.4 synchronization

**Status:** CANDIDATE MANUAL UX CONTRACT / CEO-REQUESTED PR / NOT INSTALLED / NOT PRODUCTION ACCEPTED  
**Applies to:** the R1 exploratory ChatGPT PI → IR → CC handoffs, not the protected V1 or approved V2 financial policies.  
**Owner:** CEO for investment decisions; PI for portfolio interpretation; IR for issuer discovery/valuation; CC for synthesis.  
**Authority:** `PAM_PROJECT_CONSTITUTION.md`, `governance/PAM_GOVERNANCE.md`, the actually approved mode, current PI/IR/CC project instructions, and existing R1 source, portfolio, comparability and PDF methods. This document is a manual workflow clarification only.  
**Reference:** the CEO's sixth trial of 2026-10-31 (a private PAMalisé report), and the user-facing five-prompt v1.4. No private holdings, profile URL, user identification, reports or screenshots are stored here.

## Scope and main correction

The sixth trial observed 20 visible Blossom rows (the displayed percentages totalled **100.3%**), but treated the entire shared-profile display as unrelated to the client. The CEO reports that their selected Blossom profile represents their portfolio and is connected to brokerage data. That user statement is material context, not independent broker verification.

**Two-layer source interpretation, no schema migration:**

1. **Capture layer stays unchanged.** PI-1 continues to produce `PUBLIC_REFERENCE` / `public_portfolio_reference` for a shared-profile view, `OWN_PRIVATE_AUTHORIZED` / `work_blossom_inputs` only for an actually established owner-private authorized view, and `INACCESSIBLE_OR_AMBIGUOUS` on failure. Do not forge `work_blossom_inputs`, change the official fields, or promote any public reference into a private M3 ledger.
2. **Client-context layer is separate.** When the CEO expressly attests that the selected profile is theirs and reflects broker-linked positions, append a distinct human-readable `OWNER_ATTESTATION=CEO_ATTESTED_LINKED_PROFILE`; record evidence of a visible platform connected/verified badge **per row** if actually observed, else `UNKNOWN`. The attestation permits **qualitative, conditional interpretation** of the visible composition for this client; it does not certify account ownership, the brokerage link's current health, the exclusive CELI scope, freshness, cash, monetary balances, ETF look-through or execution terms.
3. **No duplicate brokerage proof by default.** Do not require a separate broker statement or a fresh private-account login merely to describe visible lines or plausible concentration overlap. Request a decisive account-scoped observation only if necessary for a numeric personalized `PORTFOLIO_ROOM`, per-account denominator, after-contribution weights, or transaction economics. Keep `UNKNOWN` distinct from `0`.
4. **R1 deterministic boundary remains authoritative.** The already existing `ai_native/attested_visible_concentration.py` may calculate *displayed-view-only* top-line/top-five concentration **only** when its original completeness/date/rounding guards all pass; it cannot authenticate accounts or calculate private allocations. For a 20-line display totalling 100.3%, do **not** renormalize or assert a validated whole-view denominator. The genuinely visible raw weights and leading rows can still be described as user-interface observations with the explicit limitation.

## Five-prompt on-demand sequence

One client intake per `ANALYSIS_ID`; one CEO-visible action at a time. Preserve the chosen mode, horizon, account/broker facts and as-of across handoffs. A changed client statement is logged as `CLIENT_PROFILE_REVISION`. No personal values are written to this repository.

| Step | Project / prompt | Required handoff | Decision boundary |
| --- | --- | --- | --- |
| 0 | PI — source capture | `PI_ACQUISITION_RECEIPT`, original source category, `P_OBSERVATION_LEDGER` or qualified public reference, `CLIENT_RESEARCH_CONTEXT` | Capture provenance, not buy/sell or private Room |
| 1 | IR — market discovery | `SCAN_UNIVERSE_LEDGER`, `SCAN_SHORTLIST`, `SCAN_TO_VALUATION_HANDOFF` | Open discovery; not proof of exhaustive market ranking |
| 2 | IR — deep valuation | Original `IR_CAPSULE` + decisive `EVIDENCE_ANNEX` and `ECONOMIC_COMPARABILITY_BRIEF`, plus scan receipt | Issuer/benchmark economics, not private Portfolio Room |
| 3 | PI — final integration (when portfolio relevant) | Separate `PI_DELTA`, and the exact received original IR evidence once under `FORWARD_UNCHANGED` | Conditional room/cost, no second issuer valuation |
| 4 | CC — decision and PAMalisé delivery | Decision-first report and `CC_FINAL_REPORT_RECEIPT` with status of scan, evidence, PDF and archive | CEO decides; no autonomous transaction |

**Skip rules:** no relevant portfolio → 1 → 2 → 4; a specified single issuer → 2 → 4; unavailable source → IR may continue, with conditional PI and explicit missing-portfolio status. Do not force all five steps.

## Market-discovery retention (correction 3)

IR's discovery must use the existing fact-first `SOURCE_FUSION_R1` funnel ledger; report **actually accessed** geographic/source coverage, date, unique issuers, exclusion reasons, final shortlist and decisive unknowns. The shortlist is an evidence-scoped triage, never a claim to rank the global market.

The `SCAN_TO_VALUATION_HANDOFF` must identify (at minimum) the `ANALYSIS_ID`, strategy, as-of, distinct candidate security IDs, why each candidate was selected/not selected, comparable fact IDs when available, original source locators and material limitations. IR's valuation result **must carry forward a recoverable scan receipt** (`SCAN_UNIVERSE_LEDGER` and `SCAN_SHORTLIST` directly, or an actual same-session original file accessible to CC). A bare attachment name, inaccessible Project-local link, or summary claiming an unseen original is **not** transport.

CC must report why the final issuer emerged from the observed discovery; if the full initial scan is unavailable, say `SCAN_TRACE_INCOMPLETE` and do **not** claim an exhaustive comparative selection. Do not silently convert a single-name valuation into a global ranking.

The previously defined `FORWARD_UNCHANGED` contract remains exact for the received original `IR_CAPSULE` and decisive `EVIDENCE_ANNEX`. The scan receipt is a **separate identified attachment/section**, never added to or rewritten inside the original capsule. A reader must be able to trace the decisive shortlist without duplicating whole research papers.

## Company vs benchmark (correction 2)

IR uses the existing two-lane `VALUATION_R1` contract for a genuinely applicable benchmark:

- **Lane A:** price-only CAGR or conditional distributions-based total cash-flow IRR for the same security, *without* calling one scenario a probability-weighted expected return.
- **Lane B:** company vs the selected benchmark (VFV for approved applicable High-CAGR scope) only with an independently defensible forward economic basis, aligned horizon, cutoff, currency/FX, total distributions, fees and portfolio account facts *when known*.
- Search proportionately for material normalized owner cash per diluted share, capex, reinvestment, acquisition financing, dilution and benchmark forward assumptions. Distinguish `COMPANY_ER=UNAVAILABLE`, `BENCHMARK_ER=UNAVAILABLE`, `NOT_COMPARABLE`, and valid scenario outputs. A missing input does not become zero.
- Return `ECONOMIC_COMPARABILITY_BRIEF` with both lane statuses, original `S/F/K/V` links, most consequential unresolved economic input and *one targeted IR follow-up*. An account statement cannot repair missing benchmark expected return.

No new hurdle, score, scenario probability, price target, benchmark return, trading instruction or six-mode financial policy is authorized.

## CC report completion (corrections 1–3)

CC reconciles the original IR packet and separate `PI_DELTA`, with clear distinctions between (a) raw visible Blossom percentages, (b) CEO-linked-profile statement, (c) source-scope confidence, and (d) evidence-supported monetary account weights. Show an informative view-level description instead of asserting that the displayed stocks are irrelevant to the client; do **not** claim the portfolio is a confirmed Wealthsimple CELI.

The final PAMalisé report contains the five pillars at supported evidence grades and a trace of: which companies were actually considered, why shortlisted, what economic comparability was established, what the displayed portfolio suggests, and whether a monetary portfolio decision is actually supported. Visual design follows `PAMALISED_REPORT_MASTER_R1.md`, requires the original visual prototype to be truly available for a fidelity PASS, and never substitutes a made-up PDF/download.

After the report, state `ARCHIVE_NOT_SAVED` until a real authorized private destination and successful save exist. A prior client yes to research reuse or archive preparation does not store data or give permission to publish. Manual Project-to-Project transfers remain explicit.

## Targeted synthetic regression / next real run

- With a fictitious 20-line `100.3%` display and an attestation, preserve the raw UI sum, no complete-denominator concentration, no private brokerage assertion, no portfolio weights after contribution, no trading authority.
- With a complete internally consistent fictitious view, conditional *display-only* concentration is allowed, and remains nonprivate.
- With date/coverage unknown, return `DISPLAY_VIEW_DENOMINATOR_UNESTABLISHED`.
- With a case mismatch or attempted authority escalation, fail closed.
- Manual packet review: test that IR's scan receipt survives valuation → CC, original IR S/F/K/V is unchanged through PI, and CC keeps company ER and VFV benchmark ER as separate statuses.
- In one new CEO-run trial, check these three issues separately, record manual hops, method versions and any actual Work access. Do **not** claim a live integrated test merely because this contract or synthetic regression exists.

**Authority/status:** V1 frozen, V2 challenger, R1 methods candidate where so marked, hard $0 external financial data cost. No brokerage login initiated here, no Work invocation, no Project Settings installation, no trade, no automatic archive, and no protected-policy changes.