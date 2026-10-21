# Market Atlas (M1) — Normal daily research → final-looking graphic workflow

**Full authoritative product-format specification:** [MARKET_ATLAS_STANDARD.md](MARKET_ATLAS_STANDARD.md). This daily runbook uses the implemented M1 USD country ETF proxy renderer. It does not authorize publication. PRs #202–#207 are merged, including standardized Market Atlas V1, Natural Earth 1:50m geometry, and public-image header/footer corrections.

## One sentence

**Prompt 2 / Subject: Market Atlas → search for actual same-session USD U.S. ETF closing prices → render the STANDARD approved PAM world map without visible draft/audit warnings → deliver the exact source/caption/SHA package → Prompt 3 checks these unchanged files → CEO separately approves posting.**

No additional prompt or alternative topic-selection workflow is needed when Market Atlas is explicitly requested. The same standardized 1080×1350 composition, 390px mobile companion, branding, zero-centered performance colors, fixed legend placement and side-by-side **TOP 3 FRONTRUNNERS / BOTTOM 3 LAGGARDS** panels must recur every day. Only dated evidence, returns, scale values, leaders/laggards and caption wording change.

## Prompt 2 / research and render — obligatory behavior

1. Choose the latest **fully completed** 16:00 America/New_York U.S. session and actual preceding completed U.S. session. If today is intraday, use the last closed session and label it correctly. Watch holidays and early closes.
2. Initialize the **30-row registry** via `m1_etf_daily.py init`. It currently maps 25 U.S.-listed USD single-country ETF tickers; five no-eligible-ETF countries remain neutral. These are distinct from "quotes that should have been found". Do not claim all thirty countries have U.S. ETF substitutes.
3. **Research both actual market closes for every established candidate.** Search ticker/date pairs, not just ETF issuer directories. Try dated issuer or exchange price records; on initial failures retry credible historical quote/finance sites and inspect original price/date basis. Discrepancies require a second check and relevant corporate-action inspection. If a source cannot be used under actual access terms, choose a legitimate alternative. Do not treat an ordinary failed first query as `insufficient credible information`, and do not submit a names-only "research in progress" response as the final result.
4. Record exact USD **unadjusted regular-session ETF exchange** close pairs, source URLs/titles and split/ex-distribution review notes. Avoid NAV, total return, FX-neutral home indices, intraday prices or fabricated sources. Keep genuinely unavailable individual rows blank while continuing retrieval for all other tickers. The `NO_KNOWN_EVENT` and `REVIEW_PENDING` research statuses require Prompt 3 verification; they should not stop the first creative.
5. **Render the first normal image in final appearance, without a visible DRAFT / AUDIT / NOT FOR PUBLICATION overlay.** Use the CEO-approved pine-logo PNG, permanent Market Atlas layout, exact SVG, 1080×1350 PNG, 390px PNG, English race-style candidate caption, issue JSON, source CSV and SHA-256 asset manifest. Never create a different AI-generated map composition in place of the registered renderer.

**Coverage is a research-performance objective, not a hardcoded renderer quota.** Try to recover authentic pairs for the full established 25-ticker candidate set. The old 4- and 6-country blocking thresholds are gone. An exceptional one-country fact pattern can still render in the SAME three-row-per-panel visual layout, with honest empty slots and no invented ranking entries. A zero-real-return issue cannot truthfully show any performance; diagnose the retrieval problem instead of producing fake percentages.

## One fixed image, updated data only

The CEO-supplied October 20, 2026 Market Atlas image is the **visual master**. Each Market Atlas request immediately uses that composition in the existing M1 renderer. Keep the dark background, approved pine seal, masthead, headline, fixed map, horizontal green/red scale, three frontrunners, three laggards, market-breadth/spread band and source/footer exactly where they are. Update only completed-session dates, properly sourced ETF prices/returns, map fills, ranks, scale values, observed market count, data-driven summary, sources and English caption. Use the same existing renderer and country geometry; **no bootstrap, new infrastructure, template selection or pre-render administrative procedure**.

An internal image can be produced before independent publication review. Verification of material facts and CEO sign-off remain necessary **before posting**, not as reasons to withhold the first image.

## Normal CLI example (paths/date are examples only, NOT actual closing-price evidence)

```bash
cd docs/marketing/visual_kit
python m1_etf_daily.py init --out ./market_atlas_quotes.csv
# Researcher/agent supplies authentic prices, both dates and exact URLs in the CSV.
python m1_etf_daily.py build ./market_atlas_quotes.csv \
  --session-date 2026-10-20 --prior-date 2026-10-19 \
  --cutoff-utc 2026-10-20T21:00:00Z \
  --issue-id GM-20261020-05 \
  --brand-logo /path/to/CEO_APPROVED_PAM_MASTER.png \
  --out-issue ./market_atlas_issue.json \
  --svg ./market_atlas.svg --png ./market_atlas.png \
  --mobile-png ./market_atlas_390.png \
  --asset-manifest ./market_atlas_asset_manifest.json
```

The date/cutoff example is usable only when the actual exchange sessions are completed and authenticated. `--headline` is accepted for old CLI compatibility but the normal Market Atlas artwork has a deliberately fixed headline; a custom daily hook belongs **in the English caption**, not as a redesign of the map.

Required columns:
`country,ticker,prior_close,close,source_url,prior_source_url,source_name,corporate_action_status,source_use_status,notes`.

An included row needs genuine HTTPS quotation URLs, positive comparable USD closing prices and an actual corporate action/source-use observation. No blanket per-ETF fictitious licence-letter or exhaustive legal rights archive is needed merely to generate an original internal graphic from publicly reported factual close prices. Source-specific binding restrictions remain material and will be checked in Prompt 3.

The renderer **does not fetch remote quotes**: an employee with web capabilities must actively complete the source-linked CSV. Once genuine prices exist it assembles the image deterministically. Rendering is not proof that external quote facts were verified by an independent person.

## Fixed image and caption

See [MARKET_ATLAS_STANDARD.md](MARKET_ATLAS_STANDARD.md) for invariant coordinates, regularized PAM identity, palette, left/right ranking positions and product version. Fixed 3+3 headers and row positions **do not change** when the displayed price data change, even during unusual coverage. Empty rows use a dash, never fabricated country names or performance. The adaptive map shades and actual legend endpoint values still respond to that session's real moves.

The English caption is engaging, natural, grounded in the actual strongest/weakest qualifying ETF returns, signed % values, percentage-point spread, observed breadth, dates, source attribution and USD ETF/FX caveat. No invented price catalyst, fake quotation, inaccurate domestic-index claim, mandatory engagement bait or investment recommendation.

**A clean image is only publication-ready in appearance**, not permission to post. Approval-state text is stored in the manifest/issue/QA packet, never on the public image. **Market Atlas geographic/chrome correction merged in PR #207:** both colored countries and ordinary unplotted land now use the pinned 1:50m Natural Earth polygons (including detailed Canadian Arctic and Indonesian/Japanese islands). The public image header does **not** show `GM-YYYYMMDD-NN` and the footer does **not** show the redundant `AS OF ... UTC` line; the true US-session comparison remains in the prominent deck. Exact issue ID and UTC cutoff remain in the JSON/source/asset SHA audit trail, and the bottom-right NOT INVESTMENT ADVICE disclosure remains on the image. These rules are canonical on `model-v2/expected-return-challenger`; actual 1080×1350 and 390px geographic visual validation is still required for each release.

## Prompt 3 / independent review — no re-render

- Inspect the **exact** source data, market/date/session semantics, splits and ex-distributions when material, arithmetic, 25-candidate retrieval attempts, selected/unplotted land, dynamic legend and top/bottom-three actual ranks.
- Open the **actual** 1080×1350 and 390px pictures. Check clarity, logo hash, country/ETF labels, fixed format and caption; compare original PNG/SVG/mobile/caption SHA-256 hashes with the Prompt 2 `M1_EXACT_ASSET_HANDOFF_V1` manifest. Do **not** re-render after reviewing.
- An actual discrepancy means correction/rebuild and re-audit **new hashes**. This does not require inserting a DRAFT watermark on any generated genuine-data graphic.
- Independently return PASS or a precise finding. **Do not invent** an external auditor record, source-use permission or CEO consent. The CEO authorizes the final exact unchanged image/caption separately.

Example QA fields (replace placeholders with actual checked hashes and real reviewer references):

```json
{
  "issue_sha256": "<actual issue SHA256>",
  "svg_sha256": "<actual SVG SHA256>",
  "png_sha256": "<actual 1080px PNG SHA256>",
  "mobile_png_sha256": "<actual mobile PNG SHA256>",
  "caption_sha256": "<actual caption SHA256>",
  "fact_verdict": "PASS",
  "corporate_actions_verdict": "PASS",
  "source_use_verdict": "NO_KNOWN_RESTRICTION",
  "visual_verdict": "PASS",
  "auditor_reference": "<actual factual audit record>",
  "source_use_review_reference": "<actual source-use review record>"
}
```

`python m1_etf_daily.py review ./market_atlas_issue.json --asset-manifest ./market_atlas_asset_manifest.json --qa ./market_atlas_qa.json --out-issue ./market_atlas_reviewed.json` validates declared auditor findings against the **same original byte hashes**, without re-rendering or publishing.

## Hard limits retained

No fabricated market returns, no invented price sources, no silent switch from USD ETF prices to local-currency national indices, no noncompleted U.S. session falsely treated as final, no bogus historical approved logo, no known-source contractual use violation, no automatic Blossom post. **Prompt 2 should not stop merely because fewer than an arbitrary number of data points were retrieved; it must search seriously first.**

`--draft-only` is reserved for deliberate developer diagnostics, **not** the default CEO-requested Market Atlas path. Genuine-data image exports contain no publication-warning watermark even in that internal mode; only deliberately SYNTHETIC demo fixtures retain a visible synthetic/draft identifier.
