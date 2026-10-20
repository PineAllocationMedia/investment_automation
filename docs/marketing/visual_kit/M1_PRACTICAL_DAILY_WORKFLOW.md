# M1 — Practical daily world-map workflow (CEO direction, October 20, 2026)

**Implementation under review:** PR #203 (from canonical V2 after #202 merge). This document does not change CEO publication authority. It replaces the publication-grade **pre-render** burden for ordinary daily USD ETF maps; specialized domestic-index and strict legacy intake remain intact.

## The short version

When the CEO says “World map scan of today's market moves”:

**Find latest completed U.S. ETF closes → compute arithmetic → render real-data DRAFT M1 with approved pine logo → Prompt 3 checks actual figures and source terms → CEO approves the exact final post.**

Do not stop after researching the ETF names. Do not claim a 3:45 PM ET snapshot is a completed 4:00 PM closing map. If markets are still open, complete the prior finished U.S. session as a clearly titled alternative, or hold a requested same-day-only product. ETF % moves include FX and U.S. trading repricing; they are not a country's GDP or home-exchange benchmark move.

## Prompt 2 / editor: work to a real draft

1. Use the existing 30-country universe with 25 ETF **starting candidates**; check actual fund identity/activity as warranted by current evidence and investigate whether the five gaps have changed. Do not repeat an intensive original-listing audit 30 times every day when current fund identity is not reasonably in doubt.
2. Identify the **latest fully completed** regular 16:00 America/New_York U.S. trading session and its actual prior completed session; check holidays and early closes separately. No intraday or mixed-date closes.
3. Research U.S.-listed, unhedged country ETF **exchange closing prices in USD** (NOT ETF NAV, home exchange level or adjusted total return). Prefer original fund issuers/exchanges where available; an openly accessible reputable historical source may be used for factual closing-price observations with attribution and, where material, cross-check. **Never claim every website grants automated scraping or redistribution.** Follow actual source access conditions; if terms prohibit the intended retrieval/use, select another legitimate source. Do not copy a vendor's chart, database or proprietary presentation.
4. Make a quick **30-row price sheet** with exact ETF price pairs, source URLs/names, simple split/ex-distribution finding, and an honest source-use note. Leave unsupported countries blank. For known restrictions, exclude the observation; do not invent substitutes or permissions. You need **four source-linked prices** before M1 graphic has meaningful coverage.
5. **Render the M1 graphic before Prompt 3.** The code labels it `DRAFT · REAL DATA`; a research preview is for the CEO/editor/auditor and is **NOT postable**. Use exactly the approved pine logo if available. Give Prompt 3 the real PNG, 390px preview, issue JSON, 30-row source CSV, caption, as-of and supported/unsupported count.

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
  --out-issue /private/m1_issue_draft.json \
  --svg /private/m1_draft.svg --png /private/m1_draft.png \
  --mobile-png /private/m1_mobile.png
```

The example command uses a **post-close** UTC cutoff on October 20; do not run it earlier that day or substitute fictional daily closes. The 30-row CSV is a human/agent research artifact, not an API output. It accepts **30 decisions with 0–25 genuinely available observations**; at least four source-linked observations are required for a graphic. The script deterministically recomputes price returns, validates the session, USD ticker mapping, sources, omission treatment and mobile raster.

Required columns: `country,ticker,prior_close,close,source_url,prior_source_url,source_name,corporate_action_status,source_use_status,notes`. For included countries:
- `corporate_action_status=CHECKED_CLEAR` or `NO_KNOWN_EVENT` (the latter is preliminary; Prompt 3 must verify before publication). If a material action is suspected, **do not include** the unadjusted move until checked.
- `source_use_status=NO_KNOWN_RESTRICTION` or `REVIEW_PENDING` (research preview only). A known restriction is excluded; do not assume free availability grants contractual redistribution.
- Both close prices from comparable regular-session USD ETF market-price observations, with individual source URLs where different.

**No blanket per-fund data-license permission letter or archived rights-document SHA is required merely to prepare this original source-attributed research map.** Market price facts are not the same as distributing an entire vendor quote feed. Review actual material restrictions proportionately, not hypothetically.

## Prompt 3 / independent auditor: proportional, focused, real checks

1. Reopen and spot-check **every plotted ETF close pair**, ticker-to-country relationship and previous/current completed regular U.S. session dates. Recalculate displayed returns and check leaders/laggards, signs, percentages and source-to-image match. A genuine discrepancy blocks the exact post.
2. Review splits, ex-dividend/distribution effects when relevant (especially outlier returns) and the actual terms/retrieval method if they materially restrict use. Using factual price moves with attribution is different from redistributing licensed datasets. **Do not require individual copyright/market-data licenses by default.** Stop if an actual source constraint is established or a material source-use question remains.
3. Review the **exact 1080×1350 and 390px branded graphic**, sources and plain-English caption. It must say “USD U.S.-listed country ETF price returns” and acknowledge FX/US-hours repricing, not claim domestic national-index returns or market-wide country GDP.
4. The 30-row universe must still include the five no-proxy slots, but **do not HOLD just because a fixed no-proxy country lacks a daily repeated formal issuer search**. Exclusions and last known issuer context must be honest; material new ETF findings require registry review.
5. Return **PASS** only if all material facts and actual source-use circumstances are checked, with an independent reviewer reference and the exact SHA-256 of the issue; otherwise return specific corrections or HOLD. A rendered research draft can exist during HOLD; do not publish it. No source/rights assertions or reviewer personas may be fabricated.

A successful Prompt 3 produces a structured QA declaration, e.g.:

```json
{
  "issue_sha256": "<actual SHA256 of canonical JSON payload>",
  "fact_verdict": "PASS",
  "corporate_actions_verdict": "PASS",
  "source_use_verdict": "NO_KNOWN_RESTRICTION",
  "visual_verdict": "PASS",
  "auditor_reference": "<actual independent factual reviewer record>",
  "source_use_review_reference": "<actual source-use check record>"
}
```

`python m1_etf_daily.py review /private/m1_issue_draft.json --qa /private/m1_prompt3_qa.json --out-issue /private/m1_reviewed.json` produces a **reviewed publication candidate**. The separate M1 renderer **still requires a SHA-bound release manifest, exact original approved logo and CEO approval of the final image/caption** to remove the DRAFT watermark. A QA field is an attestation, not proof that a tool performed external checks.

## Operational limits

- CLI is an **offline deterministic assembler**, not a live market-data retrieval service. Prompt 2 must actually research the CSV using accessible sources. No fictional live data, hidden bot execution or automatic Blossom posting.
- Legacy `m1_scan_handoff.py` remains for heavier index/forensic audits but is **not** the default for a normal daily USD ETF market-map request.
- A daily research map is feasible when factual pairs exist and sources permit research/display, **without treating each public closing-price fact as inherently licensed content**.
- If a source, corporate action, wrong session or actual right-of-use problem affects a return, omit that market or HOLD its release; don't block all research previews unnecessarily.
- Exact chart/logo/release protections and independent CEO authority remain intact.
