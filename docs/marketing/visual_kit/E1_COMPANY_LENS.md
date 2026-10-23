# E1 — Company Lens research plate v0.1 (CEO-approved working visual direction)

**Editorial use:** an evidence-based note about a single U.S. SEC-reporting public company's reported fiscal period. **Channel:** Blossom \`@therealpam\`. **Code:** \`render_company_lens.py\` accepts only \`template="E1"\`; no live SEC/financial feed, prediction, personalized advice, security rating, issuer affiliation, or publication. The bounded E1 renderer **was merged in PR #201**; this records implementation availability, not data-source authentication or automatic publication.

## CEO visual-direction freeze — 2026-10-21

**Decision:** CEO reviewed the real-data Microsoft FY2026 Company Lens **working image** (native and mobile previews) and selected **FREEZE AS-IS / NO MICRO-IMPROVEMENTS**. The visual composition is satisfactory as a reusable editorial design. Do not initiate cosmetic rework or increase information density without new CEO direction; proceed to other templates such as M4.

**Approved working reference** (generated in the October 2026 CEO conversation, not embedded or separately versioned as a GitHub asset):
- `PAM_E1_Company_Lens_MSFT_FY2026_WORKING_1080.png` — 1080 x 1350; SHA-256 `3c4e09d9d946f21e06de59cbe4f0d16d11e4a5bda2723f34af68ddcaafb52214`.
- `PAM_E1_Company_Lens_MSFT_FY2026_WORKING_390.png` — 390 x 488; SHA-256 `fbb54c9b5c1fd7dcec49cdcec6151201a390ea9da6ace22b0db03e859ed1b058`.
- `PAM_E1_Company_Lens_MSFT_FY2026_WORKING.svg` — SHA-256 `203cd37e23b335791c8fb83d17db7f27f6621f39b114a13761682c15b3931611`.

**Retain the accepted visual grammar:** deep pine background; approved ivory botanical seal; PAM / COMPANY LENS masthead; issuer name and ticker; compact two-line analytical thesis and deck; one documented fiscal-period/source line; exactly three clearly ruled financial evidence rows with right-aligned levels and distinct editorial interpretations; sober counter-case and what-to-watch; concise original-source/disclaimer footer; legibility at mobile scale. No decorative dashboards or added metrics as filler.

**Scope / exactness:** the working Microsoft preview was composed **locally from the E1 design**, *not* exported by executing the canonical `render_company_lens.py`. This freeze records CEO approval of that **working visual direction**, **not** proof of pixel-identical canonical-renderer output, a passed independent data/rights audit, or approval to publish that Microsoft issue. The GitHub renderer remains unchanged. Before the first production post, compare its actual native/mobile output to the accepted reference during the ordinary exact-artifact audit; correct an actual material mismatch if observed rather than reopening cosmetic template redesign. Preserve the existing independent sourcing, logo-hash and exact-post CEO publication gates.

## Why this is not T1, M4 or M2

E1 is a **company filing + investment thesis architecture**: *the question / trigger → three reported figures → what the analyst infers → counter-case → observable next check*. All facts come from an identifiable original filing and its exact fiscal period. E1 is intentionally not a macro mechanism diagram (T1), not an asynchronous cross-asset market tape (M4), and not an industry sector ranking (M2).

The 1080×1350 graphic has one concise company identifier and event, a real thesis headline, **three ruled filing evidence rows** with clearly differentiated reported values and issuer/accounting provenance, then a visible skeptical **COUNTER-CASE** and **WHAT TO MONITOR**. Interpretations are labeled as *editorial reading*; they are not quotes or mathematical deductions from the issuer. No decorative pseudo-chart or comparison bar mixes heterogenous units.

## Bounded v0.1 evidence contract

A single **10-K, 10-Q or 8-K** fiscal-period original source, with precise source sections. Company scope is an SEC filer rather than claiming global company coverage. The primary original source for a real E1 must be a \`www.sec.gov/Archives/edgar/data/...\` HTTPS document. A syntactically permitted filing URL **does not prove** the source exists or contains these numbers: the human auditor must access, preserve and validate the actual filing and all three locators.

Top-level required JSON keys:

\`schema_version="1.0" | template="E1" | account="@therealpam" | issue_id="CL-YYYYMMDD-NN" | issue_at | company_name | ticker | cik | event | headline | deck | countercase | watch | caption | fiscal_period | reporting_currency | document_type | figure_policy="EXACT_REPORTED_HISTORICAL" | primary_filing_url | filed_at | rights_note | evidence\`.

Three **and only three** evidence objects:

\`claim_id | metric | display | numeric_value | unit | basis | fact_kind="REPORTED_HISTORICAL" | fiscal_period | meaning | source_section | verification_note | source_url | classification="FACT" | verification="VERIFIED" | retrieved_at\`.

- \`numeric_value\` must be finite, and its \`display\` must match within the displayed decimal precision. **No invented annualization, aggregation, margin, trailing-series or implied valuation.**
- Every record must share the issuer fiscal period and exact primary filing URL. The issuer reporting currency is shown prominently; the **unit on each figure** distinguishes revenue USD millions, GAAP percentages, operating ratios and other measures. This pilot only admits \`GAAP / NON_GAAP / OPERATING\` explicitly annotated bases.
- The \`meaning\` attached to a fact is editorial interpretation, **not SEC-verified source language**. The separate counter-case and monitor field require consideration of uncertainty. Avoid advice-like price targets or disguised forward forecasts.
- Source chronology must satisfy \`filed_at <= retrieved_at <= issue_at\`. The renderer cannot authenticate the filer, CIK/ticker, actual data, accounting basis or time relevance: independent review must.
- No forecast/guidance number inside the **historical evidence** rail. Real management outlook, pro forma figures, trailing-twelve-month adjustments or historical series crossings require a future explicit E1 variation and separate validation.
- Each record contains a section locator; the source register must preserve full filing URL, filing accession, filing date, fiscal period, original table/footnote text, GAAP/non-GAAP reconciliation or operating definition, exchange/ticker/CIK and independent comparison to the rendered level. \`basis="NON_GAAP"\` is a disclosure signal, **not an automatic acceptable data-definition validation**.
- \`rights_note=REVIEWED_FOR_EXACT_USE\` is a manual assertion that source presentation rights were reviewed and does not itself grant data rights. No paid source or membership feed is added.

## Private issuer IDs, no public code

`CL-YYYYMMDD-NN` identifies the E1 issue in structured research, filenames, manifests and audit communications only. The top-right internal tracking code is no longer part of the public-facing E1 masthead. Keep the company, fiscal period, reported-vs-inferred distinctions and source references readable; do not replace that code with another arbitrary build/revision string. Apply the same principle to one-off E1 compositions.

## Clean genuine-filing previews (including custom compositions)

Real-filing E1 preview artwork must have **no internal DRAFT / NOT AUDITED badge or production-status footer**, even while the working package remains internally `DRAFT_NOT_AUDITED_NOT_APPROVED`. The CEO-supplied Meta Q3 2026 working package used **custom SVG composition**, not the canonical E1 renderer: its upper-right `DRAFT / NOT AUDITED` badge and lower-left `DRAFT NOT AUDITED` footer are the exact recurring defect to prevent. Place review and approval notes in the **external asset manifest and response**, not on the image. Synthetic fixture images must still visibly identify themselves as `DRAFT · SYNTHETIC TEST`. A visually clean image is **not** permission to publish.

For bespoke SVG, run `python artwork_status_guard.py <candidate.svg>`, then inspect exported native and 390px PNGs; the SVG check does not inspect words in embedded/raster image content. This new hygiene rule leaves every original source/rights, brand hash, independent-review and CEO exact-post release gate intact.

## Release and brand gates

The same \`release_allowed()\` exact JSON **including caption** SHA manifest, independent reviewer reference, explicit CEO approval of exact asset, and matching CEO-approved reconstructed pine-logo master SHA are required for any release. Direct RELEASE renderer calls also enforce the exact logo hash. The renderer cannot verify audit identity or actual CEO intent and never sends anything to Blossom. **A PR merge is not a post approval**.

The only fixture \`examples/e1_synthetic.json\` is for mock/layout tests, has a **fictional company, invented financials and invalid fictitious SEC filing**, uses \`example.org\`, \`rights_note=SYNTHETIC_LAYOUT_ONLY\` and a provisional \`P\` seal; cannot be released. A real event/report must not be silently simulated from fixture numbers.

\`\`\`bash
cd docs/marketing/visual_kit
python render_company_lens.py examples/e1_synthetic.json \
  --output /tmp/e1_demo.svg --png /tmp/e1_demo.png
\`\`\`

CI exports 1080px and 390px proofs and checks XML, actual glyph bounds, counter-case/watch separation, source/period/GAAP gate behavior, release fail-closed and negative tests. **CEO visual direction approval comes after visually inspecting actual native and 390px outputs**; source and copyright audits for the first real post remain independent. If any gate fails, **HOLD**.

**REUSE:** same approved PAM palette, deterministic SVG primitives, SHA/logo and release envelope, optional existing pinned PyMuPDF. **BUILD:** narrow E1 filing fact schema, focused research narrative layout and regression tests. **NO** source purchase, external market calls, autonomous workflow or changes to CEO-protected files.
