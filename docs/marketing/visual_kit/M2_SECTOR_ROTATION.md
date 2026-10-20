# M2 — Sector Rotation research plate v0.1 (IMPLEMENTATION PILOT)

**Scope:** Blossom \`@therealpam\` editorial template for an intelligible, **comparable U.S. equity-sector performance cross section**. Source-bound deterministic SVG/PNG only; no market-data feed, share-price forecasting, buy/sell signal, official S&P/GICS affiliation, real-index membership validation or publication authority.

**Actual implementation:** \`render_sector_rotation.py\` with \`template: "M2"\`. This code is on a separate CEO-review PR; **NOT canonical until that PR is CEO-merged**. Other proposed formats M1/E1 remain NOT IMPLEMENTED. Do not call every one-day comparison “sector rotation”—a rank alone does not prove a durable factor/sector shift.

## Distinct information architecture

One 1080×1350 source-bound research plate:

- Top: headline, explanatory deck, labeled 20-session **index price-return** lens, publisher/quote currency/session date.
- Middle: ranked **eleven** fixed U.S. large-cap sector categories. All sectors share **one documented provider/index-family, denomination, return basis and completed close clock**. A **zero-centered horizontal bar** shows the signed 20-session price return, with its exact numeric percent. Adjacent **1D %** is a distinct price-change column. Teal/amber bars distinguish signs with numeric +/− labels; no buy/sell color cues or comparisons of incomparable units.
- Bottom: **20-session breadth** (\`N/11 positive\`) and **leader–laggard spread in percentage points**, both computed by renderer from the underlying observations. A short **READING** and falsifiable **WATCH**, then source-register pointer, exact as-of timestamp and advice line.
- Branding: existing pale-ivory/forest-pine identity. Only an authorized matching-hash reconstructed pine-cone logo may be used for RELEASE. Unbranded synthetic preview deliberately uses a provisional \`P\` seal.

## Scope, taxonomy and comparability

Pilot covers a **complete eleven-sector U.S. large-cap universe**, not a cherry-picked basket or all global sectors. Exact canonical labels required:

Communication Services; Consumer Discretionary; Consumer Staples; Energy; Financials; Health Care; Industrials; Information Technology; Materials; Real Estate; Utilities.

Calling this set "GICS" in an actual issue requires the auditor to verify the source's classification/version and lawful use of that taxonomy. The renderer **does not itself validate** membership, index methodologies, licensing, constituent drift, sector reclassifications or source-publisher endorsement. The future evidence sheet must document the actual universe identifier and all eleven mapping definitions before a real publication.

Accept only **homogeneous local-currency sector INDEX PRICE series** for the pilot—not mixtures of sector ETFs, FX-converted fund prices, price indices, total-return series and adjusted NAVs. Individual series must share the declared \`index_family\` and \`currency\`; heterogeneous subscriptions/license rights are not silently resolved by the code.

**20S** means twenty **eligible completed index trading sessions**, not calendar days, one calendar month or twenty-one-day intraday data. The 20-session claim needs a human-reviewed trading calendar, provider schedule and true prior/lookback daily observations. Code checks only order, plausible calendar spacing and metadata; it cannot independently prove the provider's number of eligible sessions. Require same \`observed_at\`, \`prior_observed_at\`, \`lookback_observed_at\` across the eleven selected series, with explicit UTC offsets, and row-specific \`retrieved_at\` before issue cutoff. Different markets/sessions → HOLD, not a misleading heatmap.

## Frozen JSON contract

Top-level \`schema_version=1.0 | template=M2 | account=@therealpam | issue_id=SR-YYYYMMDD-NN | issue_at (offset-aware) | headline | deck | interpretation | watch | caption | universe=US_LARGE_CAP_11_SECTORS | basis=LOCAL_CURRENCY_INDEX_PRICE_RETURN | lookback_sessions=20 | index_family | source_title | currency | rights_note | evidence[11]\`. Optional \`brand_logo_sha256\` becomes mandatory when using approved logo or releasing.

For each of the **eleven** evidence objects: \`claim_id | sector | index_id | index_family | currency | close | prior_close | lookback_close | observed_at | prior_observed_at | lookback_observed_at | retrieved_at | session_status=COMPLETED | source_url (original HTTPS) | classification=FACT | verification=VERIFIED | verification_note\`.

From those *three original source levels*, the renderer recomputes:
- \`1D price return % = 100 × (close / prior_close − 1)\`.
- \`20S price return % = 100 × (close / lookback_close − 1)\`.
- \`breadth = count(sector 20S return > 0)\`.
- \`leader–laggard spread in percentage points = max(20S returns) − min(20S returns)\`.

All observations must be positive finite numbers. Missing sectors, duplicate sector labels or claim IDs, inconsistent provider/currency, mixed session times, unverified sources, missing/holiday closes, stale (>96h) observation, wrong or impossible values cause **HOLD**. Do not infer missing values as zero or extrapolate charts. Fixed ordering by computed 20S return, with sector-label tie break, prevents editorial rank manipulation.

Bars share **one symmetric, zero-anchored linear return scale** chosen deterministically for the entire issue; every row shows an explicit signed numeric value to avoid color-only or scale-only communication. Local color and rank meaning must be clear. The rank does not establish statistical significance or a recommendation.

## Strict rights, evidence and release boundaries

Sector index data and classification schemas can be copyrighted/licensed; public availability is not redistribution permission. Specific source permission, fair use/quotation context, visual display rights and attribution should be resolved with Commercial & Compliance before using live values in public copy. \`rights_note=REVIEWED_FOR_EXACT_USE\` is *an assertion*, not proof of legal clearance. No paying for a data service or adding an API under this implementation.

A real post must have an **independently inspected original evidence packet**: eleven eligible current/prior/lookback closes, source URLs and retrieval times, index family/provider, local session clock, classification mapping, methodology, currency, recalculated exact returns, data rights, claim-level verification, correct caption and potential alternative explanation. The source register is retained outside the image.

Renderer uses unchanged \`release_allowed()\` **exact input+caption SHA manifest**, separate recorded independent audit PASS and explicit CEO post approval, **exact approved pine logo bytes**, and the data-rights note; the tool does not authenticate human approvals and never auto-publishes. Production release should fail closed absent any gate.

## Synthetic preview and visual hold

\`\`\`bash
cd docs/marketing/visual_kit
python render_sector_rotation.py examples/m2_synthetic.json \
  --output /tmp/m2_demo.svg --png /tmp/m2_demo.png
\`\`\`

\`m2_synthetic.json\` uses eleven **fictional** source-free sector close triplets and \`example.org\`. Its figures, dates, returns and interpretations **do not represent actual markets**. It is visibly watermarked \`DRAFT · SYNTHETIC TEST\` and automatically ineligible for publication.

Check native and **390px mobile PNG**, bar alignment and zero-axis symmetry, axis scale, row label legibility, signed positive/negative/zero and neutral distinctions, sector completeness, header/source/as-of/warning, single readable thesis, and absence of collision between ranking, interpretation and footer. The **six-part institutional design gate** is a human review, not a CI result. A proposed visual is **VISUAL HOLD** until the CEO accepts its exact look; any real market post needs fresh independent factual and visual review and a *separate* per-post CEO approval.

**Resource controls:** REUSE standard-library SVG + existing deterministic primitives/logo validator/source/approval SHA, pinned PyMuPDF for optional PNG. BUILD only narrow M2 sector data-binding, arithmetic and bar geometry. No new package, external cost, privileged tool, new data-right grant, V1/model change, automated activity or CEO-protected governance amendment. Check PyMuPDF licensing before distributing the rendering software itself.
