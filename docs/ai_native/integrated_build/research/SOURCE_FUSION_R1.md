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
