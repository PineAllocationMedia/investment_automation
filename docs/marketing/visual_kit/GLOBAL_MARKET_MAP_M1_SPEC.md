# M1 — Global Equity Market Map: CEO-Selected 27-Market Prototype

**Status:** DRAFT / SYNTHETIC / UNMERGED / NOT PUBLICATION-READY. CEO scope update dated 2026-10-20. This specification supersedes the earlier proposed “20 largest economies by nominal GDP” M1 coverage rule. Country-selection order is **not** a GDP ranking, market-cap ranking or any other statistical ranking.

## Purpose and exact country coverage

The CEO instructed an index-first world map for these **27 country/market labels, in this order**:

| Order | Market | Geometry ID | Domestic equity-index candidate (not verified) |
|---:|---|---|---|
| 1 | United States | USA | S&P 500 price index |
| 2 | Japan | JPN | TOPIX price index |
| 3 | China | CHN | CSI 300 price index |
| 4 | India | IND | NIFTY 50 price index |
| 5 | Germany | DEU | DAX **Kursindex / price**, not headline performance DAX |
| 6 | United Kingdom | GBR | FTSE 100 price index |
| 7 | Canada | CAN | S&P/TSX Composite price index |
| 8 | Australia | AUS | S&P/ASX 200 price index |
| 9 | Taiwan | TWN | Taiwan Weighted Index / TAIEX candidate |
| 10 | South Korea | KOR | KOSPI price index |
| 11 | Brazil | BRA | Ibovespa — **INCOMPARABLE** pending return-basis review |
| 12 | France | FRA | CAC 40 price index |
| 13 | Switzerland | CHE | Swiss Market Index / SMI price candidate |
| 14 | Mexico | MEX | S&P/BMV IPC price index |
| 15 | Spain | ESP | IBEX 35 price index |
| 16 | Italy | ITA | FTSE MIB price index |
| 17 | Netherlands | NLD | AEX price index |
| 18 | Singapore | SGP_POINT | Straits Times Index / STI price candidate |
| 19 | South Africa | ZAF | FTSE/JSE All Share price candidate |
| 20 | Turkey | TUR | BIST 100 price index |
| 21 | Indonesia | IDN | IDX Composite price index |
| 22 | Vietnam | VNM | VN-Index price candidate |
| 23 | Russia | RUS | MOEX Russia Index — **MISSING**, source/rights/session unresolved |
| 24 | Kazakhstan | KAZ | KASE Index — **MISSING**, price variant/source unresolved |
| 25 | Iran | IRN | TEDPIX — **INCOMPARABLE**, return basis and rights unresolved |
| 26 | Poland | POL | WIG20 price index |
| 27 | Sweden | SWE | OMX Stockholm 30 price index |

There are **27 decisions**, not 27 guaranteed daily returns or confirmed live feeds. The index names above are **research candidates**, not checked symbol/variant assignments or licensed-data entitlements. A market index is an equity benchmark proxy and is **not** the performance of a country's GDP or the total national economy. The countries/markets are chosen editorially; this representation does not assert a position on recognition, territorial sovereignty or contested borders. Taiwan and other potentially sensitive geographic representation require independent editorial/legal review before a public release.

The previous fixture's **Saudi Arabia** entry is removed, as it is not in the CEO's list. There is no GDP-ranking fallback; do not silently substitute a 20-economy GDP universe.

## Geometry and Singapore

- Immutable public-domain **Natural Earth 1:110m Admin-0 v5.1.1**, 177 features; [upstream Natural Earth GitHub source](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_110m_admin_0_countries.geojson), upstream blob SHA 1e6ab74c7042f97013be69ceec798be8e1aff27d; normalized local Git blob SHA 8300299de7b831db1b50d0501924cad1f5b067e1. Public-domain terms: https://www.naturalearthdata.com/about/terms-of-use/.
- **26 selected geographic IDs have real Natural Earth polygons. Singapore is absent at this map scale.** Draw a small explicitly labeled SG **geographic point locator**, at approximate 103.8198°E, 1.3521°N, over the real basemap; identify “SG POINT” in the footer. This is not a sovereign boundary or a replacement licensed polygon; independently validate the point and cartographic presentation before release.
- Preserve actual countries' polygons. Never freehand or image-generate geographic outlines. Examine small Taiwan/European/Southeast Asian shapes at 390px and use an approved inset/secondary information graphic if legibility is inadequate. The public-domain basemap does not grant stock-index quotation rights.

## Data contract (M1 v0.2)

The input requires: schema_version=1.0, template=M1, account=@therealpam, issue_id, cutoff_utc, headline/deck/interpretation/caption, universe_version, **selection_basis=CEO_SELECTED_27_COUNTRIES**, geometry_version, geometry_source_github_blob_sha, return_basis=DOMESTIC_INDEX_LOCAL_PRICE_RETURN, comparison_basis=LATEST_COMPLETED_SESSIONS, method_version, rights_note, universe_review, benchmark_registry_status and an evidence array of **exactly 27 records**.

Each record has a unique integer selection_order 1–27, matching the exact market/ISO code above. Selection order has **no economic ranking meaning**. The obsolete rank, rank_nominal_gdp_usd, gdp_observation_year, ranking_year, gdp_source_url, and gdp_vintage fields are not required by M1 v0.2 and must not be used as a basis for a numerical coverage claim. Singapore uses geometry_id=SGP_POINT; other rows require the exact pinned Natural Earth geometry join.

Each country has a candidate instrument name, provider/variant, benchmark definition, exchange/local quote currency, exposure note, original data source URL, verification and rights notes, plus an **explicit eligibility decision**. Eligible price-index rows must have completed session/prior-session observed timestamps with offsets, observed and retrieved clocks before the UTC cutoff, exact prior/current numeric closes and signed percent return recomputed from those closes. If the price vs total-return basis, permission, integrity, completed session or comparability is not resolved, no numeric return may be supplied: mark MISSING, HOLIDAY, CLOSED, STALE or INCOMPARABLE rather than 0.00%.

A single symmetric red-to-green percentage color scale is used for local price-index returns only. **Actual zero return** has its own neutral swatch **EXACT 0.00%**; **NO VALID CLOSE** has a different gray key. Map headline must say latest completed sessions and **not synchronized** when markets have different local closes. The plate shows eligible count out of 27 and the names of two eligible leaders/two laggards. Full all-27 price evidence remains in the source packet; tiny on-map ticker labels for every country are not required or advisable.

## Prototype proof vs real data

The fixture is a **synthetic visual exercise** with invented prices and percentage returns and explicit example.org placeholders. In this demo, 23/27 returns are eligible **only for layout testing**, and Brazil, Russia, Kazakhstan and Iran are neutral missing/incomparable. Neither the 23/27 number nor any percentage is an observed October 2026 market result. All candidate data, provider claims, timestamp conventions and sources still need independent validation.

Before any authentic M1 issue: independently qualify every relevant benchmark's **exact price variant, official close, session/calendar, exchange currency, quote source, data-rights/redistribution permission and indexing license**; review source URLs and original observation captures; review the 27-country joins, Singapore dot and disputed-boundary presentation; replay authentic calculations and inspect 1080×1350 and 390px PNGs. If coverage/rights/comparability do not support a coherent world map, **HOLD or SKIP**, do not fill gaps.

Production still requires the exact CEO-approved SHA-bound reconstructed pine master, immutable issue/caption hash, independent factual/visual audit and **separate explicit CEO approval of the exact image and caption**. Visual Kit CI tests structurally deterministic code and rendering, not the authenticity, legal redistribution or public readiness of the data. No auto-publishing, fee-bearing feed, new external service, portfolio or investment decision authority is introduced.

## Intended regression gates

Reject omitted/duplicated/substituted countries, Saudi Arabia creep, invalid Singapore polygon joins, GDP-rank masquerading, invalid Natural Earth SHA/ISO joins, unqualified ETF or total-return substitution, unsigned/mismatched arithmetic, fake zeros for missingness, nonfinite/zero closes, impossible clocks, stale observations, logo mismatch, synthetic release and caption-hash drift. Check explicit SG locator and separate exact-zero/no-close legend, plus 390px text bounds and polar geometry crop.
