# M1 — Global country ETF map (USD-price proxy alternative)

**Branch/authority:** PR #202, open and unmerged until the CEO decides. **Design/validation prototype only. No real ETF return series or public use clearance is supplied.** This mode is an explicit alternative to the domestic index map, not a new claim of full national stock-market returns.

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

## 30-country CEO list → 25 named U.S. ETF candidates

These are **research targets, not a claim of 25 available real-time quotes or 25 publication-licensed feeds**. The actual fund/underlying country focus, existence and trading status must be checked for the intended day. Proxy purity is approximate; do not substitute a broader regional/emerging-markets ETF for one country.

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

**Primary issuer/entity references:** [iShares U.S. ETF directory](https://www.ishares.com/us/products/etf-investments), [Vanguard VOO](https://investor.vanguard.com/investment-products/etfs/profile/voo), [VanEck VNM](https://www.vaneck.com/us/en/investments/vietnam-etf-vnm/). [SEC EGPT liquidation supplement (March 2024)](https://www.sec.gov/Archives/edgar/data/1137360/000113736024000170/vvtegpt2024liquidationsupp.htm), [VanEck RSX/RSXJ liquidation notice](https://www.vaneck.com/us/en/blogs/emerging-markets-equity/shareholder-notice-rsx-and-rsxj-liquidation/).

Registry source URLs identify the issuer; they **do not provide approved reuse rights or current-day closing prices**. Only an exact, active U.S.-listed, unhedged single-country fund may qualify. The lack of a candidate for five countries is a working state, not a permanent assertion that no comparable U.S. fund could ever exist.

## What the employee must actually do

1. **Initialize 30-row ETF research** on the authorized PR #202 branch, with **zero** inherited market prices or completed status:

   ```bash
   cd docs/marketing/visual_kit
   python m1_scan_handoff.py init --mode usd-etf \
       --cutoff-utc 2026-10-20T23:00:00Z \
       --out /private/m1_20261020_us_etf_research.json
   ```

2. Independently investigate **all 30** selected countries. Verify exact ETF identity, listing, unhedged single-country holdings and **last two completed regular U.S. exchange prices** (split or ex-distribution events must be reviewed). Quote prices must be USD secondary-market **close**, not ETF NAV or distributions-reinvested performance. Check fund history/splits and whether U.S. markets were actually open.
3. Preserve original issuer/exchange quote captures and applicable data-rights evidence in authorized **private** storage; record the two exact source SHA-256 hashes, exact recorded exchange sessions with U.S. time zone offsets, source/rights audit references, facts review and calculation. **Never create fake captures, source links, reviewer identities or permissions** to satisfy the input schema.
4. Qualified quote fields follow [the research handoff contract](m1_scan_handoff.py). In USD ETF mode use `benchmark_variant=ETF_EXCHANGE_PRICE`, `return_currency=USD`, `currency=USD`, exact ticker + full fund name from [registry](m1_country_etf_mode.py), `etf_price_basis=UNADJUSTED_US_EXCHANGE_CLOSE`, `corporate_action_review=NO_MATERIAL_SPLIT_OR_EX_DISTRIBUTION`, `proxy_scope=SINGLE_COUNTRY_UNHEDGED`, `rights_scope=PUBLIC_BLOSSOM_ETF_USD_GRAPHIC`.
5. Run `assess` with `--evidence-root /private/... `, the complete packet and an external review. A candidate M1 real-issue JSON can be created **only** if 30 decisions are complete, at least four genuinely approved ETF series are present, separate source/rights/fact reviewers are identified and every original/rights capture's bytes match its SHA. All displayed observations must share one completed U.S. session date and U.S. close.
6. Run the M1 deterministic renderer to create an **unpublished DRAFT** image and real-data caption, inspect 1080x1350 and 390px, and send the exact asset/source/rights packet for a separate factual, visual and Commercial & Compliance review. **CEO approval of the exact asset remains mandatory**.

**Cannot be bypassed:** Data-use licensing/permissions and independent factual verification are unresolved. A ticker list and a pricing endpoint do not establish rights to branded redistribution. A free endpoint, synthetic screenshot or arbitrary `VERIFIED` JSON field cannot create publication authority.

## Test / proof

- [Separate synthetic input](examples/m1_us_etf_synthetic.json) intentionally contains 25 **fictional** USD ETF close pairs and five ordinary-land exclusions: EGY, DZA, RUS, KAZ, IRN.
- [ETF validator/registry](m1_country_etf_mode.py) and [existing M1 renderer](render_global_index_map.py) use mutually exclusive return bases.
- [USD ETF renderer tests](tests/test_m1_us_etf_mode.py) and [research-handoff tests](tests/test_m1_etf_research_intake.py) cover mismatched tickers, exchange hours, currencies, portfolio proxy restrictions, eliminated ETFs, incomplete closes, NAV/total-return substitution and rights-capture integrity.
- GitHub CI creates distinct **1080x1350 PNG, SVG and 390px PNG** synthetic previews in `m1-us-country-etf-synthetic-previews`. No live screenshot, licensed quote, complete employee scan or real post is implied.

**Acceptance:** The CEO must separately approve the new ETF semantic/design before publication. PR #202 is OPEN/UNMERGED; completing implementation tests is not a merge authorization.
