# MARKET ATLAS V1 — Daily world-market map, fixed PAM format

**Purpose:** A recognizable, repeatable daily finance graphic for Blossom `@therealpam`. **Technical template:** `M1`. The CEO's Prompt 2 **Subject: Market Atlas** (case-insensitive, including surrounding words) is an **explicit production request** for the M1 world-market movement graphic; do not substitute a market scan, text-only commentary, alternative layout or more fashionable topic.

**Status:** proposed in the associated CEO-reviewed PR until merged into `model-v2/expected-return-challenger`. This file changes neither source truths nor CEO approval authority.

## Immutable recurring visual contract

Every normal Market Atlas issue uses **the existing deterministic `render_global_index_map.py` layout**, not newly conceived art. Format version `MARKET_ATLAS_V1` remains fixed across Monday–Friday requests until a separately approved design change.

- **Canvas:** exactly 1080×1350 (4:5) native PNG and SVG; 390px wide mobile companion.
- **Brand:** same CEO-approved forest-green pine/cone master on ivory circular seal; same PAM typography, colors and safe margins. Never replace the actual logo with a reconstructed approximation.
- **Title:** fixed **PAM / MARKET ATLAS**; default headline fixed `The world in one U.S. session`, so a different daily hook does **not** move or reflow the map. Date comparison text changes, not its placement. Hooks belong in the external English caption.
- **Geography:** fixed **Natural Earth 1:50m Admin 0 Countries v5.1.1** world geometry, immutable SHA-pinned local master, identical country polygon paths for colored and neutral areas, and unchanged map viewport/country lookup. 50m geometry preserves Canada's Arctic archipelago and multi-island countries (e.g. Indonesia and Japan) rather than the distorted low-detail 110m simplification. Singapore locator remains source-independent and only appears when qualified. Ocean and unplotted slate land consistently styled. Do not invent a separate color-overlay polygon, simplify highlighted countries differently, or alter borders to fit an ETF narrative.
- **Performance:** exact one completed U.S. ETF market-price return in USD per eligible country, including FX/after-home-close repricing, never mixed with local home-exchange indices. A separately requested domestic-index M1 run retains its distinct subtitle/price basis, but uses the same Market Atlas visual skeleton.
- **Color:** session-adaptive continuous symmetric green/red diverging scale with numeric endpoint labels derived from that same mapping function; 0.00% is covered warm neutral, missing is dark NOT PLOTTED. Scaling *method* remains the same every day, while numeric bounds change with actual volatility.
- **League table:** **fixed** side-by-side **TOP 3 FRONTRUNNERS** and **BOTTOM 3 LAGGARDS** panels with precisely three stationary row slots each. Actual signed returns determine their order; ties resolve using ISO country code. An observation cannot appear in both panels. If exceptionally fewer than six observations qualify, preserve all six physical row slots; leave excess as an em dash rather than inventing data, reshuffling the design or refusing to render.
- **Public-image chrome:** keep the exact covered-session comparison date near the title (the deck). **Never display the private GM-YYYYMMDD-NN issue ID in the top-right header**, and **never display an AS OF ... UTC audit/render timestamp in the lower-left footer**. Retain the issue ID and cutoff_utc unmodified in JSON, filenames/manifest and independent audit records. Preserve the existing material source/geography footnote and bottom-right NOT INVESTMENT ADVICE disclosure. No visible DRAFT, NOT FOR PUBLICATION, AUDIT ONLY or REVIEW VERSION banner on genuine Market Atlas artwork; those states belong outside the artwork.
- **Editorial caption:** natural confident horse-race framing based only on actual leader, laggard, point spread, positive/negative/flat breadth, exact session and US-listed-ETF/FX caveat. The specific sentences can change; voice, factual vocabulary and semantic structure should feel consistently PAM, not seven unrelated brand personalities.

**Permitted daily variation:** valid returns, color fills, numerical legend endpoints, session comparison near the title, private audit cutoff metadata, qualifying country count, country ranks, measured performance values and narrative wording. **Not permitted:** arbitrary replacement of the world map, shifted modules, altered fonts or branding, new cards, changing ranked-slot count, hidden missingness, unapproved chart type or visual watermarks on genuine first-output artwork.

## Prompt 2: search thoroughly, output the clean final-looking asset first

For a plain `Subject: Market Atlas`, bypass generic topic-selection/scanning questions and immediately initiate M1 on the latest fully completed U.S. exchange session and its true predecessor. **Never use intraday values as completed closes.** On holidays and before U.S. close, use the latest completed regular session, with dates explicitly identified.

The 30-country CEO universe contains **25 established U.S. ETF candidate ticker mappings** and **five current no-qualified-ETF placeholders**. These five are not failures to find a price for an existing ticker. They must be honestly re-investigated when evidence of a new eligible listing emerges; never misrepresent 30 country proxies as already existing.

A failure to retrieve initial quotes is a **search-retry trigger**, *not* permission to stop at a directory of fund names or issue a boilerplate `insufficient credible information` rejection. For each candidate:
1. Search exact **ticker + both actual U.S. session dates + historical daily closing prices**. An issuer landing page alone does **not** provide a dated close pair.
2. Try issuer/exchange listings and accessible dated price histories; if they lack one of the dates or are blocked, search other reputable financial quote/history publishers. Verify whether data represent **unadjusted U.S. exchange close in USD**, not NAV, adjusted return or an intraday price.
3. Where material discrepancies occur, compare an independent accessible history and check split/ex-dividend dates; select the supported basis or exclude only the specific unresolved row. Use another compliant source if an actual publisher restriction applies.
4. Keep searching other qualified tickers after an individual source fails. Capture actual URLs, prices, same-session dates and a clear reason for any genuinely unresolved row. **Attempt all 25 registry candidates** before treating a low-coverage result as finished. Do not claim the 25 prices were collected if they were not.

This is a **vigorous search obligation**, not permission to fabricate values or imply that proprietary website reuse rights exist. A competent agent with browsing/source access should ordinarily recover historical ETF close pairs; the repository's offline assembler **does not retrieve them on its own** and cannot guarantee remote availability.

The renderer has **no arbitrary minimum of four or six markets**: one genuinely qualified close pair is enough to generate the standard clean map. A shortfall of plotted markets is recorded in the audit/evidence packet; it is not a layout-switch command or an automatic blocker. The only genuine blockers to the exact branded graphic are **zero real qualified returns**, a contradictory/noncompleted session, incompatible/false quotation, absent or corrupt approved master logo, or an actual technical render failure. Do not bypass these by inventing data or impersonating an auditor.

Ordinary `m1_etf_daily.py build` outputs:
- first visually final, watermark-free native **Market Atlas** PNG + SVG and companion mobile PNG,
- true-source quote CSV + issue JSON, natural English candidate caption,
- SHA-256 file manifest binding image bytes, input CSV, issue payload, caption and approved logo.

**No on-image publication-status warnings.** Internally the metadata continues to say `PENDING_INDEPENDENT_AUDIT_AND_CEO_APPROVAL`; that does not affect the picture. The user gets a finished *design*, not automatic permission to post it.

## Prompt 3: audit the exact completed creative, without recreating it

Review actual close pairs, same completed session, percentage math, FX proxy basis, adaptive legend, precise ranks, missingness, caption and exact 1080/390px visual. Compare original file hashes from Prompt 2; never replace the image after a PASS. If a fact is wrong, return a specific correction, regenerate the original creative once and re-audit its new hashes. No source terms assumption or invented external approval.

**Only separate explicit CEO approval authorizes actual posting to Blossom.** This remains true even though the artwork contains no review-state watermark. No automatic posting, new data rights, or different regulatory status is granted.

## Stability tests and operational limits

Regression suites must cover coverage counts **1 through 25** where inputs are valid, honest blank rank slots with no duplicated countries, no first-image real-data warnings, unchanged row/header coordinates over different daily data, actual 1080×1350/390px output, approved-logo hash and immutable Prompt 3 manifest. Synthetic prices used in tests never establish a real daily market fact.

Keep `Market Atlas` on the same visual template version for a week of sessions. Only a separately CEO-approved renderer revision may change that version. GitHub Actions CI status must be stated truthfully: exhausted free runner minutes can stop tests from executing but do not count as a successful test run.
