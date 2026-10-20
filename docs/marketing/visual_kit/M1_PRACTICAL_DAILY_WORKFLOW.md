# M1 — Practical daily world-map workflow (CEO direction, October 20, 2026)

**Status:** PRs #202–#204 are merged. PR #205 proposes the next CEO-directed M1 refinement: two 3-row leaderboards and exact final-looking image delivery in Prompt 2. This document does not authorize publication. Specialized domestic-index and strict legacy intake remain available.

## The short version

When the CEO says “World map scan of today's market moves”:

**Find latest completed U.S. ETF closes → compute arithmetic → render the final-looking 1080×1350 M1 image and 390px companion (NO visible DRAFT overlay) → Prompt 3 checks the exact bytes and caption → CEO approves that same exact image and caption.** A clean image is an *approval-pending artifact*, not permission to post.

Do not stop after researching the ETF names. Do not claim a 3:45 PM ET snapshot is a completed 4:00 PM closing map. If markets are still open, complete the prior finished U.S. session as a clearly titled alternative, or hold a requested same-day-only product. ETF % moves include FX and U.S. trading repricing; they are not a country's GDP or home-exchange benchmark move.

## Prompt 2 / editor: produce an exact final-looking candidate

1. Use the existing 30-country universe with 25 ETF **starting candidates**; check actual fund identity/activity as warranted by current evidence and investigate whether the five gaps have changed. Do not repeat an intensive original-listing audit 30 times every day when current fund identity is not reasonably in doubt.
2. Identify the **latest fully completed** regular 16:00 America/New_York U.S. trading session and its actual prior completed session; check holidays and early closes separately. No intraday or mixed-date closes.
3. Research U.S.-listed, unhedged country ETF **exchange closing prices in USD** (NOT ETF NAV, home exchange level or adjusted total return). Prefer original fund issuers/exchanges where available; an openly accessible reputable historical source may be used for factual closing-price observations with attribution and, where material, cross-check. **Never claim every website grants automated scraping or redistribution.** Follow actual source access conditions; if terms prohibit the intended retrieval/use, select another legitimate source. Do not copy a vendor's chart, database or proprietary presentation.
4. Make a quick **30-row price sheet** with exact ETF price pairs, source URLs/names, simple split/ex-distribution finding, and an honest source-use note. Leave unsupported countries blank. For known restrictions, exclude the observation; do not invent substitutes or permissions. A research preview may show as few as four observations, but the final-looking M1 artifact requires **at least six distinct qualified markets**, enough for three frontrunners and three separate laggards.
5. **Render the exact intended public appearance BEFORE Prompt 3.** The ordinary `build` command now requires the exact approved pine logo, native PNG, 390px PNG and `--asset-manifest`. It creates a clean, unwatermarked image and caption, **but explicitly labels the handoff metadata `PENDING_INDEPENDENT_AUDIT_AND_CEO_APPROVAL`.** Give Prompt 3 the original PNG/SVG/mobile bytes, 30-row CSV, full issue JSON, caption and SHA-256 manifest. If a required asset or 6-market coverage is absent, use `--draft-only` for a clearly watermarked exploratory preview. NEVER describe an unreviewed artifact as authorized to publish.

### CLI (no paid API or scraper)

```bash
cd docs/marketing/visual_kit
python m1_etf_daily.py init --out /private/m1_etf_prices.csv
# Researcher fills in prices/sources in the CSV. Unsupported rows stay blank.
python m1_etf_daily.py build /private/m1_etf_prices.csv \
  --session-date 2026-10-20 --prior-date 2026-10-19 \
  --cutoff-utc 2026-10-20T21:00:00Z \
  --issue-id GM-20261020-05 \
  --headline "The world in one U.S. session" \
  --brand-logo /private/PAM_Macro_Lens_logo_RECONSTRUCTED_v0.1_APPROVED_2048.png \
  --out-issue /private/m1_issue_final_looking.json \
  --svg /private/m1_final_looking.svg --png /private/m1_final_looking.png \
  --mobile-png /private/m1_mobile.png \
  --asset-manifest /private/m1_exact_asset_manifest.json
```

The example command uses a **post-close** UTC cutoff on October 20; do not run it earlier or substitute fictional closes. The CSV retains all 30 decisions with up to 25 eligible ETF candidates. The exact-final-looking output requires **6+ genuinely sourced returns**; an explicit `--draft-only` can produce a watermarked diagnostic with 4–5. The CLI checks session, math, ETF/country mapping, data-source URLs, supported/unplotted countries and mobile raster; it also outputs an exact SHA-256 ledger binding the **issue payload, source CSV, SVG, native PNG, mobile PNG, caption and approved logo.** The deterministic builder is not a licensed live quote feed.

Required columns: `country,ticker,prior_close,close,source_url,prior_source_url,source_name,corporate_action_status,source_use_status,notes`. For included countries:
- `corporate_action_status=CHECKED_CLEAR` or `NO_KNOWN_EVENT` (the latter is preliminary; Prompt 3 must verify before publication). If a material action is suspected, **do not include** the unadjusted move until checked.
- `source_use_status=NO_KNOWN_RESTRICTION` or `REVIEW_PENDING` (research preview only). A known restriction is excluded; do not assume free availability grants contractual redistribution.
- Both close prices from comparable regular-session USD ETF market-price observations, with individual source URLs where different.

**No blanket per-fund data-license permission letter or archived rights-document SHA is required merely to prepare this original source-attributed research map.** Market price facts are not the same as distributing an entire vendor quote feed. Review actual material restrictions proportionately, not hypothetically.

## Adaptive M1 color scale and race-style editorial caption (PR #204)

The M1 map retains its existing approved design but maps every **eligible real computed return** to a continuous color with an adaptive symmetric daily legend: the smallest clean ±1/±2/±5/±10/±20 percentage-point cap including the largest absolute plotted change, with a minimum ±1%. Positive returns are successively deeper green, negative returns deeper red; exact 0.00% is warm-neutral and **still covered**; no observation means original dark slate land with a separate NOT PLOTTED swatch. The legend's current endpoints and middle ticks are **generated from the same function** as the country fills. Don't compare shade intensity across two different sessions without reading each session's scale. The 390px preview must visibly distinguish faint returns from unplotted land and no exaggerated full-saturation on quiet days.

**Caption for each M1 daily map:** derive actual leading/lagging fund return, country name, ticker, percentage-point spread, count of positive/negative/unchanged plotted ETFs, dates and the precise USD ETF/FX caveat from the same price-pair JSON. A little horse-race scoreboard energy is welcome: who set the pace, who trailed and how large the gap was; it should read like an opinionated investor, not a corporate report or a sports commentator on repeat. The deterministic CLI writes an honest starting draft in `issue.caption` and `build` output `caption_draft`. The editor may improve wording, variety and emphasis **without changing a value, implication or attribution**; after editing, Prompt 3 audits the exact amended input SHA and finished graphic. Never imply all funds rose when every plotted return is negative, or call an ETF move the domestic index or whole economy. Never invent explanations for moves or push a buy/sell CTA.

Prompt 3 must check numbers/legend agreement, selected-versus-unplotted land, and caption leaderboard/spread arithmetic **as well as** prior price/rights/brand gates. PR #204 is merged. PR #205 adds the two-column **TOP 3 FRONTRUNNERS / BOTTOM 3 LAGGARDS** display. The ranking uses computed eligible returns only (stable country-code tie-break), with no duplicate market between columns. Even if every ETF is positive, the bottom three are the relative laggards; do not call their returns negative. If fewer than six countries qualify, HOLD the final-looking issue and use `--draft-only` with accurately reduced counts instead.


## Prompt 3 / independent auditor: proportional, focused, real checks

1. Reopen and spot-check **every plotted ETF close pair**, ticker-to-country relationship and previous/current completed regular U.S. session dates. Recalculate displayed returns and check leaders/laggards, signs, percentages and source-to-image match. A genuine discrepancy blocks the exact post.
2. Review splits, ex-dividend/distribution effects when relevant (especially outlier returns) and the actual terms/retrieval method if they materially restrict use. Using factual price moves with attribution is different from redistributing licensed datasets. **Do not require individual copyright/market-data licenses by default.** Stop if an actual source constraint is established or a material source-use question remains.
3. Review the **exact 1080×1350 and 390px branded graphic** plus issue JSON, source CSV, caption and `asset_manifest` without rerendering. Check SHA-256 of original PNG, SVG, mobile image and caption against the manifest. Recompute the **three positive-rank frontrunners and three worst-rank laggards** by numeric eligible returns; they must be separate markets, in the correct order, even on one-sided sessions. Check the dynamically scaled legend and true `NOT PLOTTED` land. The map must say U.S.-listed country ETF USD price returns with FX/US-hours repricing caveats, not domestic stock-market or GDP returns.
4. The 30-row universe must still include the five no-proxy slots, but **do not HOLD just because a fixed no-proxy country lacks a daily repeated formal issuer search**. Exclusions and last known issuer context must be honest; material new ETF findings require registry review.
5. Return **PASS** only if all material facts and actual source-use circumstances are checked, with independent reviewer references and the SHA-256 of the exact unchanged issue/image/caption. No independent audit or CEO post approval is implied by removing the watermark. On a material correction, rebuild the Prompt 2 candidate and **audit the new SHA values from scratch**. A clean-looking image during HOLD remains private and unpublishable; never fabricate source, auditor or owner approvals.

A successful Prompt 3 produces a structured QA declaration, e.g.:

```json
{
  "issue_sha256": "<actual SHA256 of canonical JSON payload>",
  "svg_sha256": "<actual Prompt 2 SVG SHA256>",
  "png_sha256": "<actual Prompt 2 1080px PNG SHA256>",
  "mobile_png_sha256": "<actual Prompt 2 390px PNG SHA256>",
  "caption_sha256": "<actual final caption UTF-8 SHA256>",
  "fact_verdict": "PASS",
  "corporate_actions_verdict": "PASS",
  "source_use_verdict": "NO_KNOWN_RESTRICTION",
  "visual_verdict": "PASS",
  "auditor_reference": "<actual independent factual reviewer record>",
  "source_use_review_reference": "<actual source-use check record>"
}
```

`python m1_etf_daily.py review /private/m1_issue_final_looking.json --asset-manifest /private/m1_exact_asset_manifest.json --qa /private/m1_prompt3_qa.json --out-issue /private/m1_reviewed.json` validates the factual/visual QA claims **against the original image and caption SHA-256** and writes a reviewed issue record. **It does not re-render or replace the image.** The CEO must separately authorize release of those identical original pixels and caption; no automated Blossom posting or release claim is made by the CLI. QA fields are externally supplied attestations, not proof that code performed independent review.

## Operational limits

- CLI is an **offline deterministic assembler**, not a live market-data retrieval service. Prompt 2 must actually research the CSV using accessible sources. No fictional live data, hidden bot execution or automatic Blossom posting.
- Legacy `m1_scan_handoff.py` remains for heavier index/forensic audits but is **not** the default for a normal daily USD ETF market-map request.
- A daily research map is feasible when factual pairs exist and sources permit research/display, **without treating each public closing-price fact as inherently licensed content**.
- If a source, corporate action, wrong session or actual right-of-use problem affects a return, omit that market or HOLD its release; don't block all research previews unnecessarily.
- Exact chart/logo/release protections and independent CEO authority remain intact.
