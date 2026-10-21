# Market Atlas (M1) — USD U.S.-listed country ETF price return map

**Status:** The dual-mode M1 map, practical ETF price assembler, adaptive legend and exact-asset handoff are merged in PRs #202–#205. The standardized daily product is now named **Market Atlas** in the new CEO-directed proposal. Read [MARKET_ATLAS_STANDARD.md](MARKET_ATLAS_STANDARD.md) for fixed recurring format, source-search escalation and clean first-image rule. No automatic quote feed is provided; actual source-linked ETF closing-price research and separate Prompt 3/CEO approval remain necessary. Plain `Subject: Market Atlas` selects this USD ETF M1 map by default, unless the CEO explicitly requests domestic-index mode.

## Why a separate mode

The CEO identified a simpler and potentially much broader route to a useful world map: U.S.-listed country equity ETFs such as **VOO, EWJ, MCHI, INDA, EWG and EWU**.

A daily percent return on a U.S.-traded ETF **is not the domestic stock-index return in that country**. It can reflect:
- movement in the underlying country equity exposures, based on fund holdings rather than the whole country's market;
- foreign-currency translation into **USD**, including changes after the underlying exchange has closed;
- U.S. trading-hours repricing, U.S. news and ETF secondary-market supply/demand/premiums;
- fund fees, tracking differences, corporate actions, stock splits and distributions.

The M1 map's public label must therefore identify **“US-LISTED COUNTRY ETFs / USD PRICE MOVES”**, and the legend **“ONE COMPLETED U.S. SESSION / FX INCLUDED”**. Do not call these direct national exchange returns, synchronized local-market sessions or currency-neutral performance. The exact rendering uses a single cutoff, consistent **U.S. 16:00 ET closing market prices**, not NAV or dividend-adjusted total-return indexes. The caption should explain the proxy and its limitations.

**US ETF mode:** `return_basis=US_LISTED_COUNTRY_ETF_USD_MARKET_PRICE_RETURN`, `comparison_basis=ONE_COMPLETED_US_ETF_SESSION`, `etf_price_basis=UNADJUSTED_US_EXCHANGE_CLOSE`, `fund_currency=USD`.

**Domestic index mode (unchanged):** `return_basis=DOMESTIC_INDEX_LOCAL_PRICE_RETURN`, `comparison_basis=LATEST_COMPLETED_SESSIONS`. No mixing between modes.

## Subject routing and mandatory all-country ETF discovery

**Default:** literal **“Market Atlas”**, plus “world map scan of today's market moves,” “global country map,” and analogous world-map subjects route to **US-listed single-country ETFs in USD** using the FIXED Market Atlas visual product, not a new freeform map or the local-index mode. This applies even if the CEO says “national economy”: the graphic must truthfully describe **country equity ETF proxies**, not country GDP, whole national economies or official local-stock-index performance.

**Explicit opt-in:** “domestic national equity indices,” “local currency country index map,” or `--mode index` selects the older local-index method. The generic `SCAN CURRENT MARKETS` command alone does not obligate the employee to make a map; topic-first editorial selection still applies.

`m1_scan_handoff.py init` now defaults to USD ETFs; `--mode usd-etf` is equivalent, `--mode index` explicitly opts into domestic indices, and `--subject "World map scan of today's market moves"` records the automatic ETF route.

**Each time the employee receives a world-map assignment:** Before doing exhaustive new-fund research, use the [practical daily price-to-map flow](M1_PRACTICAL_DAILY_WORKFLOW.md). The existing 25 ticker names are starting leads; prioritize **two actual closing prices and the map preview**. Check issuer identity when conflicting, stale or newly changed, and revisit absent-fund cases proportionately. The 30-country CSV already records the absent five. **No minimum of four or six source-linked observations blocks the clean Market Atlas image.** Keep searching all 25 approved registry tickers thoroughly, then render the real-data source-linked returns that were actually validated, with no fake values, no changing the map layout and no visual review-state watermark.

**Optional deeper discovery protocol (only when actual ETF identity uncertainty warrants it):**
1. Perform a **fresh, dated fund-discovery check for every one of the 30 countries**, even if the registry already contains a ticker. First check fund issuer/official product pages, exchange listing/activity and SEC filings as relevant. The 25-ticker registry is a starting list, **not a license to skip searching**. Investigate the other five countries for newly launched suitable funds; check whether a previously listed ETF has liquidated or changed exposure.
2. For each market, complete the `etf_discovery` ledger: `state`, `checked_at_utc`, `source_urls` (at least one real, inspectable HTTPS publisher/listing reference) and specific `notes`. Only `CANDIDATE_VERIFIED`, `NO_ELIGIBLE_ETF_FOUND` or `NEW_ETF_REVIEW_REQUIRED` may resolve a row. A `NOT_SEARCHED` row must remain `UNRESEARCHED` and forces assessment HOLD. No generic unexamined “none exists” conclusion.
3. If a previously unlisted ETF is found, record `NEW_ETF_REVIEW_REQUIRED`; the ETF cannot be plotted until a separate identity/activity/exposure/rights review authorizes a **registry change** and the changed code is independently tested. If no equivalent qualifies, explain why and omit that country visually.
4. Verify genuine U.S. fund activity and original USD market-close evidence, split/distribution events, local-currency exposure, reuse permissions and independent checks before `QUALIFIED`. A fund's existence is **not a qualified return observation**.

**No dishonest fallback:** Never silently mix in local indexes, regional ETFs, ADRs or incompatible series. A weak initial search requires alternate genuine quotation sources and ticker/date retries across the 25 candidate ETFs, not an automatic HOLD. The renderer must not invent a return; an exceptional zero-valid-return or impossible-session case remains a factual blocker. Any honestly absent ETF quote does not trigger a *global* 4/6-country veto.

## Market Atlas adaptive daily colors and source-grounded caption (merged PR #204)

Use the approved world-map layout with an adaptive continuous percent-return scale from the actual plotted daily ETF observations. The map and legend share the same zero-centered symmetric rounded endpoints (minimum ±1%, then ±2/5/10/20 as warranted), so pale green/red and distinct exact-zero fill never merge with dark slate NOT PLOTTED land. An outlined plotted country remains identifiable at 390px. The legend must disclose the real session-dependent endpoints and background meaning. Fixed ±2% buckets are no longer adequate on a volatile day. The intensity is only comparable **within a session**, because endpoints change with its observed range.

For the usual `m1_etf_daily.py build`, the source-derived caption starts as a lively horse-race-style market scoreboard: top ETF return, laggard, percentage-point gap, count of rising/falling ETFs, real completed US session and USD/FX caveats, with price-source attribution. Prompt 2 should polish the copy naturally, without changing figures or attributing invented causes; Prompt 3 confirms every quoted number and caption against the issue record and image. Preserve CEO approval of exact final post. The deterministic color fix applies to **both M1 ETF and opt-in domestic-index modes**, whereas the racing recap generator applies only to the USD ETF daily CLI.


## Market Atlas ETF country registry: 28 candidates, 5 exclusions

These are **research starting points, not live-price records or publication-licensed feeds**. The original 30-country/25-ETF research schema remains accepted for historical inputs, and the expanded daily ETF CSV has 33 rows (28 registered tickers plus five no-proxy cases). Each must be rechecked on the intended market date; newly discovered funds require separate qualified registry review. The actual fund/underlying country focus, existence and trading status must be checked for the intended day. Proxy purity is approximate; do not substitute a broader regional/emerging-markets ETF for one country.

| Country | Proposed ETF | Issuer |
|---|---|---|
| USA | **VOO** — S&P 500 ETF | Vanguard |
| Japan | **EWJ** — MSCI Japan | iShares |
| China | **MCHI** — MSCI China | iShares |
| India | **INDA** — MSCI India | iShares |
| Germany | **EWG** — MSCI Germany | iShares |
| United Kingdom | **EWU** — MSCI United Kingdom | iShares |
| Canada | **EWC** — MSCI Canada | iShares |
| Australia | **EWA** — MSCI Australia | iShares |
| Taiwan | **EWT** — MSCI Taiwan | iShares |
| South Korea | **EWY** — MSCI South Korea | iShares |
| Brazil | **EWZ** — MSCI Brazil | iShares |
| France | **EWQ** — MSCI France | iShares |
| Switzerland | **EWL** — MSCI Switzerland | iShares |
| Mexico | **EWW** — MSCI Mexico | iShares |
| Spain | **EWP** — MSCI Spain | iShares |
| Italy | **EWI** — MSCI Italy | iShares |
| Netherlands | **EWN** — MSCI Netherlands | iShares |
| Singapore | **EWS** — MSCI Singapore | iShares |
| South Africa | **EZA** — MSCI South Africa | iShares |
| Turkey | **TUR** — MSCI Turkey | iShares |
| Saudi Arabia | **KSA** — MSCI Saudi Arabia | iShares |
| **Egypt** | **NO QUALIFIED U.S. SINGLE-COUNTRY ETF** | VanEck EGPT terminated in 2024; **never quote** |
| **Algeria** | **NO QUALIFIED U.S. SINGLE-COUNTRY ETF** | No active verified equivalent established |
| Indonesia | **EIDO** — MSCI Indonesia | iShares |
| Vietnam | **VNM** — Vietnam ETF | VanEck |
| **Russia** | **NO QUALIFIED U.S. SINGLE-COUNTRY ETF** | VanEck RSX/RSXJ in liquidation; **never quote** |
| **Kazakhstan** | **NO QUALIFIED U.S. SINGLE-COUNTRY ETF** | No active verified equivalent established |
| **Iran** | **NO QUALIFIED U.S. SINGLE-COUNTRY ETF** | No active verified equivalent established |
| Poland | **EPOL** — MSCI Poland | iShares |
| Sweden | **EWD** — MSCI Sweden | iShares |
| **Argentina** | **ARGT** — MSCI Argentina | [Global X](https://www.globalxetfs.com/funds/ARGT) |
| **Chile** | **ECH** — MSCI Chile | [iShares](https://www.ishares.com/us/products/239618/ishares-msci-chile-etf) |
| **Thailand** | **THD** — MSCI Thailand | [iShares](https://www.ishares.com/us/products/239688/ishares-msci-thailand-capped-etf) |

**Exposure caveat:** ARGT tracks the MSCI All Argentina 25/50 equity-exposure basket and includes internationally listed/ADR companies; it is **not** an index of only shares trading in Buenos Aires. ECH and THD provide Chile- and Thailand-focused equities, but ETF USD market-close returns still incorporate trading/FX effects. Vietnam was already covered by VanEck **VNM**, France by **EWQ**. **EGPT (Egypt) was liquidated in March 2024** and no current eligible U.S.-listed country ETF for Algeria was verified; do not substitute a regional ETF.

**Primary issuer/entity references:** [iShares U.S. ETF directory](https://www.ishares.com/us/products/etf-investments), [Vanguard VOO](https://investor.vanguard.com/investment-products/etfs/profile/voo), [VanEck VNM](https://www.vaneck.com/us/en/investments/vietnam-etf-vnm/). [SEC EGPT liquidation supplement (March 2024)](https://www.sec.gov/Archives/edgar/data/1137360/000113736024000170/vvtegpt2024liquidationsupp.htm), [VanEck RSX/RSXJ liquidation notice](https://www.vaneck.com/us/en/blogs/emerging-markets-equity/shareholder-notice-rsx-and-rsxj-liquidation/).

Registry source URLs identify the issuer; they **do not provide approved reuse rights or current-day closing prices**. Only an exact, active U.S.-listed, unhedged single-country fund may qualify. The lack of a candidate for five countries is a working state, not a permanent assertion that no comparable U.S. fund could ever exist.

## Legacy full research-intake path (optional for ordinary USD ETF maps)

1. **Initialize 30-row ETF research** on the authorized PR #202 branch, with **zero** inherited market prices or completed status. This is the DEFAULT `init` mode, so `--mode usd-etf` is optional:

   ```bash
   cd docs/marketing/visual_kit
   python m1_scan_handoff.py init --mode usd-etf \
       --cutoff-utc 2026-10-20T23:00:00Z \
       --out /private/m1_20261020_us_etf_research.json
   ```

2. Independently investigate **all 30** selected countries and fill the dated `etf_discovery` record with inspected issuer/exchange/regulatory sources for each, including no-current-ETF cases. Verify exact ETF identity, listing, unhedged single-country holdings and **last two completed regular U.S. exchange prices** (split or ex-distribution events must be reviewed). Quote prices must be USD secondary-market **close**, not ETF NAV or distributions-reinvested performance. Check fund history/splits and whether U.S. markets were actually open.
3. Preserve original issuer/exchange quote captures and applicable data-rights evidence in authorized **private** storage; record the two exact source SHA-256 hashes, exact recorded exchange sessions with U.S. time zone offsets, source/rights audit references, facts review and calculation. **Never create fake captures, source links, reviewer identities or permissions** to satisfy the input schema.
4. Qualified quote fields follow [the research handoff contract](m1_scan_handoff.py). In USD ETF mode use `benchmark_variant=ETF_EXCHANGE_PRICE`, `return_currency=USD`, `currency=USD`, exact ticker + full fund name from [registry](m1_country_etf_mode.py), `etf_price_basis=UNADJUSTED_US_EXCHANGE_CLOSE`, `corporate_action_review=NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION`, `proxy_scope=SINGLE_COUNTRY_UNHEDGED`, `rights_scope=PUBLIC_BLOSSOM_ETF_USD_GRAPHIC`.
5. Run `assess` with `--evidence-root /private/... `, the complete packet and an external review. A candidate M1 real-issue JSON can be created **only** if 30 decisions are complete, at least four genuinely approved ETF series are present, separate source/rights/fact reviewers are identified and every original/rights capture's bytes match its SHA. All displayed observations must share one completed U.S. session date and U.S. close.
6. Render the exact first clean Market Atlas graphic, source-linked English caption, native 1080×1350/390px files and SHA manifest via the practical `m1_etf_daily.py build` route, with no DRAFT/AUDIT warning overlay on the original real-data image. Prompt 3 independently verifies the exact same files and actual source-use situation; the CEO separately approves the exact post. A clean image is not an autonomous publication permit.

**Normal daily mode:** Public ETF closing-price facts with attribution can be used in an original internal map preview; no per-ticker copyright licence is presumed necessary merely to record a fact. Before posting, Prompt 3 must review actual source-access/reuse conditions, calculation integrity, corporate actions, sessions, image and caption; a known contractual restriction remains a real issue. The separate approved pine-logo gate, human independent audit and exact CEO post approval remain binding. A fake reviewer identity or synthetic screenshot cannot establish release authority.

## Test / proof

- [Separate synthetic input](examples/m1_us_etf_synthetic.json) intentionally contains 25 **fictional** USD ETF close pairs and five ordinary-land exclusions: EGY, DZA, RUS, KAZ, IRN.
- [ETF validator/registry](m1_country_etf_mode.py) and [existing M1 renderer](render_global_index_map.py) use mutually exclusive return bases.
- [USD ETF renderer tests](tests/test_m1_us_etf_mode.py) and [research-handoff tests](tests/test_m1_etf_research_intake.py) cover mismatched tickers, exchange hours, currencies, portfolio proxy restrictions, eliminated ETFs, incomplete closes, NAV/total-return substitution and rights-capture integrity.
- GitHub CI creates distinct **1080x1350 PNG, SVG and 390px PNG** synthetic previews in `m1-us-country-etf-synthetic-previews`. No live screenshot, licensed quote, complete employee scan or real post is implied.

**Acceptance:** The CEO must separately approve the new ETF semantic/design before publication. PR #202 is OPEN/UNMERGED; completing implementation tests is not a merge authorization.
