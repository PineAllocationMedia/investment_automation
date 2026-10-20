# M4 — Daily Market Brief / Cross-Asset Pulse v0.1

**Status:** bounded **renderer candidate** in a separate PR; not production-approved or published. **Channel:** Blossom `@therealpam`. **Editorial scope:** a focused, information-rich view of **latest completed regular trading sessions** across major asset classes; no automated live feed. **No affiliation** with any bank, brokerage research desk or financial-data vendor is implied.

## Why M4 exists

The currently implemented Macro Lens T1/T2/T3 layouts are designed to explain particular economic mechanisms and comparisons. M4 has a different information architecture: **a compact editorial market tape and one interpretive conclusion**, useful when an actual market scan reveals a meaningful cross-asset relationship. Do not force it into Macro Lens naming. An M4 visual is worthwhile when the selected market moves **collectively illuminate one defensible thesis**, not because five numbers happen to be available.

## Exact pilot envelope

Four required group observations in order: **EQUITIES → RATES → FX → COMMODITIES**. One optional *second equity index* is placed immediately after EQUITIES. Four/five rows only; if reliable data is unavailable or heterogeneous comparisons would mislead, use another format or a sourced text post. A future six-row/credit/breadth variant needs a separate reviewed schema/layout change.

- **Price/index changes** for equities, FX and commodities: `(current / previous eligible close − 1) × 100`, with a `% ` change label. These refer to prices/spot quotes or price-index levels, **not total-return series** or an investment recommendation.
- **Rate yield changes:** `(current yield % − previous yield %) × 100` **basis points**, with `bp` change label and yield level in `%`. A falling yield is not a negative return on bonds.
- **No invented unified scale:** equity return percent and yield basis points are different quantities. M4 uses a **table of signed numbers**, not a single red/green heat scale, a common bar chart or a fake composite score.
- **Clock:** every row requires a distinct current completed session observation timestamp, prior eligible session timestamp, local `period`/`prior_period`, and acquisition timestamp. `issue_at` is a clear *as-of* cutoff. Rows may have different local close clocks/dates; the visual explicitly says **LATEST COMPLETED SESSIONS** and must never imply synchronized closing prices. Any observation older than **96 hours**, after the issue cutoff or from a provisional/halted session causes HOLD.
- **Coverage:** sources must genuinely represent the named instrument, listing venue, denomination, quote direction, market session and currency. A raw FX move is movement of the **quoted pair** (not automatically currency strength generally). Avoid unadjusted index/ETF substitution, stale delayed quotes passed off as today's close, close versus intraday mixing and inappropriate cross-currency comparisons.
- **Data rights:** individual exchange/index/vendor/ETF feeds may restrict redistribution even when browsable. A source URL is not a license. Research must record source permissions, transformations, rights and full original locators; Commercial & Compliance review if uncertain. No data subscription or feed is introduced by the code.
- **Brand:** approved reconstructed pine-logo master is unchanged and must pass the existing SHA-256 gate for release. No fake `©` next to it. All citations/source labels/observed times remain accountable. No product performance/alpha claims or trade instructions.

## Schema / evidence keys

M4 runs through `docs/marketing/visual_kit/render_market_brief.py` (a **separate** offline SVG/PNG entrypoint, not a `T1` mode).

Top-level JSON: `schema_version="1.0"`, `template="M4"`, `account="@therealpam"`, `issue_id="MB-YYYYMMDD-NN"`, `issue_at` offset-aware ISO-8601, `comparison_basis="LATEST_COMPLETED_REGULAR_SESSIONS"`, `return_policy="PRICE_RETURN_AND_YIELD_BP_DISTINCT"`, `headline`, `deck`, `interpretation`, `watch`, `caption`, `evidence` list of 4–5 rows; optional `brand_logo_sha256` required for any approved branded render. The **exact caption** and layout input are included in `payload_hash` just as they are for T1.

Each source-bound evidence row requires:

`claim_id | asset_group | label | instrument_id | venue | price_currency | period | prior_period | observed_at | prior_observed_at | retrieved_at | session_status="COMPLETED" | display | unit | numeric_value | previous_numeric_value | change_kind | numeric_change | change_display | source_title | source_url | classification="FACT" | verification="VERIFIED" | verification_note`.

`change_kind="YIELD_MOVE_BP"` for rates; `"PRICE_RETURN_PCT"` for others. Numeric values are source-supplied data, while the renderer independently **recomputes** and checks the signed daily change and its display precision. It can check structure/arithmetic/time ordering, **not whether a remote source really contained the observations**; `VERIFIED` remains a human research assertion.

`display` is a bounded numeric **level only**, without a currency symbol (put the unit in `unit`). Example: a government yield level might be `4.32` with `unit="%"` and an eligible source-pair movement `-3.00 bp`. That example is **not a market observation**.

`observed_at` and `prior_observed_at` use the **local session clock with explicit offset** and their calendar dates must match `period` and `prior_period`. Preserve exchange holiday context and local offset/DST in the external evidence sheet. Missing/holiday markets are not 0%; reject and omit/skip rather than carry a fake close. Source register includes full publisher/release title, original URL, retrieved time, local session calendar, venue, quote definition, currency, raw closes, rounding and licensing.

## Visual specification

1080×1350 (4:5) SVG with optional PNG at the same resolution. Distinct `PAM / MARKET BRIEF` masthead, report date, one thesis/headline, a brief context deck, four/five **thinly ruled source-named rows**, value and unit, signed day move with type, one interpretation, an observable WATCH line, as-of and an advice disclaimer. Forest ink / warm ivory / muted pine with no decorative rounded cards or meaningless heatmap. Disclosures and source metadata are inspected at **390px feed width**; no source/small print may depend on zoom to be understandable.

The audience must not interpret a table as an automatically verified real-time terminal. Caption should explain **why these particular observations belong together**, any asynchronous clock limitations, and significant alternative interpretations.

## Usage and review

Synthetic **layout-only fixtures** intentionally use `example.org` and invented numbers:

```bash
cd docs/marketing/visual_kit
python render_market_brief.py examples/m4_synthetic.json \
  --output /tmp/m4_draft.svg --png /tmp/m4_draft.png
```

These examples are always **DRAFT · NOT AUDITED** and ineligible for release. Tests check source/number mismatch, missing or stale sessions, wrong percentage/bp labels, incomplete groups, unverified rows, failed source URLs, and glyph/PNG boundaries where available.

Release uses the unchanged `--brand-logo` / `--release-manifest` interface and **exactly the canonical, CEO-approved pine master** plus independent audit and CEO authorization record, then manual publication under current governance. The renderer does not connect to Blossom, does not acquire quotes or facts, and does not establish distribution rights.

**Separate gates:** (1) software tests and rendered-snapshot/390px inspection, (2) external real-world evidence and data-rights review, (3) independent factual + visual audit of exact final artifact/caption, (4) explicit CEO approval of that post. A merged M4 renderer PR by itself does **not** satisfy (2)–(4).

## REUSE / ADAPT / BUILD

**REUSE:** shared deterministic SVG/text/approved-logo/release SHA primitives and pinned optional PyMuPDF. **ADAPT:** a different four-family, two-measure type editorial table from existing Visual Kit visual grammar. **BUILD:** narrow M4-only validator, calculator, view and tests. No additional paid feeds, external dependencies, geodata, publication permission, altered product code, or CEO-protected governance changes. Prior renderer code/license caveats, including PyMuPDF AGPL/commercial implications if distributing renderer code, remain relevant.
