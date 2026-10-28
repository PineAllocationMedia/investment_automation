# M2 R1 — Fact-first, multisource, international research workflow
**Status:** candidate operational method; not a live data-collection program and not a source license.  
**Owner:** Investment Research (subject review pending). **Authority:** CEO build-first 36-decision scope, especially #06, #07, #19, #20, #23.  
**Inputs:** `IR_REQUEST` from the [integration operating contract](../OPERATING_CONTRACT.md).

## 1. Begin with the economic question, not the data vendor
For a specified strategy/horizon, choose the **minimum decisive facts** needed; source choice is per fact, not per company or entire universe. Use a dated fact-request table:

| Fact | First evidence to seek | Alternative / challenge | Typical failure |
|---|---|---|---|
| Economic issuer / security | Issuer and exchange identifiers, regulator filings, ISIN/CIK/LEI | Other exchange/ADR notice, share-class note | Duplicate dual listing, incorrect ADS ratio |
| Revenue and *organic* growth | Two aligned issuer original periods and reported revenue definition | Filing taxonomy, auditor note; secondary lead | Acquisition, 52/53-week, subsidy, fiscal-year mismatch |
| Operating economics | Original operating income/segment statements and invested capital | Comparable original peer or financial note | GAAP vs adjusted; banks compared with manufacturers |
| Owner cash | Original CFO + capital expenditures, leases, acquisitions and share-based compensation | Financial-statement notes; provider quick ratio for lead | CFO−PPE labeled normalized owner earnings |
| Funding/dilution | Debt maturity, cash availability, weighted-average diluted shares | Debt prospectus, financing filing | Point-in-time shares treated as diluted EPS |
| Price/security valuation | Dated exact exchange/share class/currency quotation | Independent dated public source; original corporate actions | GBX/GBP, ADR, stale quote or impossible FX |
| Durability | Original retention/organic demand drivers, customer/product mix, competitor/regulation | Independent industry/primary sector sources | High margin assumed to prove a moat |
| Expectations | Company guidance, separate consensus context, separately labeled PAM scenarios | Original presentation and material revisions | Adjusted EPS presented as GAAP, old forecasts |
| Benchmark / costs | Vanguard VFV source, user-known account/broker/FX fees | Public official rates when permitted | Invented VFV forward return, unspecified account economics |

T13 illustrates fact fusion across SEC/issuer/Stock Analysis/Google and sector sources, but its published secondary quotes remain indicative and not executable.

## 2. Broad discovery without pretending to cover the world
For a broad mandate, retain a **funnel ledger** with region, date, source/search, reachable candidates, companies de-duplicated, financial data coverage, reasons for shortlisting and non-shortlisting, missing/geography bias. Use prior T09 152 SEC company profiles, T12 2,865 ESEF LEIs and T13 30 cases as separate historical evidence universes only when actually accessible. ESEF LEIs are not automatically investable equities. Avoid forcing an exhaustive full-repo scan or one-provider full dataset.

- Discover via lawful, publicly accessible screeners, index/provider company pages and official reports; record vendor filter settings as **vendor constraints**, not PAM investment policy.
- Verify company vs listed instrument vs reporting group; Canada, USA and Europe are not exhaustive geography. Use legal source access, no scraper bypass, proxy cycling or suppression of HTTP 429.
- Stage 1: descriptive cross-sector triage on economically sensible factors and unknowns. Stage 2: challenge a justified shortlist with primary issuer sources, corporate actions, pricing, moat and cash. The priority order is research triage, not a global expected-return rank.
- A missing fact triggers a secondary legal source or one targeted follow-up when material, never a fabricated value or automatic rejection of company quality. Stop only the unsupported conclusion.

## 3. Reconcile every material fact
Use the contract's structured fact record and S/F/K/V identifiers. Each observation carries original economic identity, instrument, reporting/conversion currency, period/end-date, source publication/capture date, original URL or filing locator, accounting concept, reported/adjusted/estimate basis, numeric unit, permissions, and confidence. `VERIFIED` requires a named and traceable actual original-source check; visibility on a secondary site is `INDICATIVE`. Differences are resolved only when accounting basis, timing, securities basis and corporate actions are understood.

- `SOURCE_FACT`: directly attributable original issuer/regulator statement, with stated verification stage.
- `THIRD_PARTY_ESTIMATE`: analyst consensus, provider forward number, vendor price without original attestation.
- `PAM_ASSUMPTION`: explicitly chosen scenario input, never disguised as historical evidence.
- `CONFLICTED` or `MISSING`: retained rather than averaged or silently replaced.
- `CURRENT`: as currently observed; historical PIT is not inferred from dates alone.

## 4. Qualitative challenge
For every research-priority business, articulate the **economic engine**, reinvestment opportunities, balance-sheet fragility, pricing and competitive moat, cyclicality, major customers and product lifecycle, regulatory/geo/currency dependencies, a plausible permanent-loss mechanism, strongest counter-thesis and thesis invalidation triggers. Separate evidence strength from confidence in forecasting.

## 5. Output, refusal granularity and portability
Deliver `IR_CAPSULE` plus one `EVIDENCE_ANNEX` (S/F/K/V) and one `COVERAGE_LEDGER` when discovery is broad. Mark `NO_RANK_SUPPORT` when valuation comparability fails but keep validated economic findings. `PORTFOLIO_ROOM = AWAITING_PI` unless PI has actual dated portfolio evidence. Keep full reports/possibly private data out of GitHub; only approved, minimized references or de-identified lessons may enter governed memory. One human-carried transfer; a private Work attachment is not accessible cross-Project by default.

## M2/M5 implementation addition — supplied-source provenance and conflict ledger

`ai_native.source_fusion.assemble_source_fusion(analysis_id=..., analysis_as_of=..., observations=[...])` is a **pure, private in-memory reconciliation component** for source references already gathered by Investment Research. It **does not** navigate to external URLs, authenticate original filings, verify publication timing against a server, choose a preferred vendor, establish historical PIT eligibility or change the truth of a source.

Each observation has unique `observation_id`, existing IR `fact_id`, `source_id`, exact economic issuer/instrument, metric and period boundaries, currency, numeric scale, accounting definition/basis and consolidation, decimal value or `null`, source kind, supplied publication/observation/original-check dates, source locator and rights, classification `SOURCE_FACT | THIRD_PARTY_ESTIMATE | PAM_ASSUMPTION`, and a **caller-reported** verification label. The constructor retains `reported_verification_status` separately from derived `claim_use_status`. Even a correctly documented original-source check yields `CALLER_REPORTED_ONLY`, **not** an independent certification or decision-grade claim.

The helper groups **comparable economic concepts only**, so two different same-period/same-basis values create `SAME_BASIS_VALUE_CONFLICT` and neither wins. Numeric strings `1` and `1.00` compare as equal. Differences in GAAP vs adjusted basis are `noncomparable_basis_groups`, **not** synthetic resolved conflicts or merged EPS. Missing source/primary-check metadata, uncertain rights, non-PIT-known publication dates and missing values remain visible; restricted sources, genuinely after-cutoff evidence and impossible source chronologies are marked `UNAVAILABLE`. Unrecognized fields and raw excerpts are **not** carried into the output. A primary-source check claimed by IR is still not established as a live authorized fetch.

The M7a optional `source_evidence_inputs` path checks exact ANALYSIS_ID/cutoff and that every annex `fact_id` appears in the original IR capsule. It reports **uncovered IR fact IDs** and constrains the report to `CONDITIONAL` when the supplied annex is unresolved, incomplete or noncomparable. `source_evidence_annex_private` stays private; the helper writes nothing to GitHub and makes no automatic changes to the original IR capsule or factual status. This complements, rather than duplicates, the existing `evidence_math.audit_calculation` (which operates on two supplied monetary facts).

**Validation:** 21 synthetic component tests with two-decimal source conflicts, GAAP/adjusted comparisons, rights, dates, missing sources and no data mutation. These tests are construction checks, **not an authentic original-source examination** or the comprehensive end-of-assembly evaluation.

## M2 source-linked fundamental economics dossier

The optional `fundamental_dossier.prepare_fundamental_dossier` consumes **this exact source-fusion annex**, not new untracked financial figures. It returns a private 2-period evidence-linked description of reported revenue, operating margins, CFO less cash capex and diluted shares only where identity, definitions, periods, units, currency, rights and claim usability allow. It pairs this with three analyst-supplied qualitative theses and strongest countercases bound to original IR fact IDs, preserving missing/contradictory source limitations and never presenting an automatically validated moat, quality grade or normalized owner cash.

See `FUNDAMENTAL_ECONOMICS_R1.md` for the precise source and optional M7a contract. Full original-document source verification, business-type selection, acquisition/FX decomposition and normalized per-share economics remain analyst tasks; no synthetic tests count as external evidence.
