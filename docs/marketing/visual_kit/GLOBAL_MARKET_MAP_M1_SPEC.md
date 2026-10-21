# M1 — Global Equity Market Map: CEO-Selected 30-Market Prototype

**Status:** DRAFT / SYNTHETIC / UNMERGED / NOT PUBLICATION-READY. CEO scope update dated 2026-10-20. This specification supersedes the earlier proposed “20 largest economies by nominal GDP” M1 coverage rule. Country-selection order is **not** a GDP ranking, market-cap ranking or any other statistical ranking.

**Alternative:** The CEO additionally requested [an explicit U.S.-listed USD country-ETF proxy mode](M1_US_COUNTRY_ETF_MODE.md) to improve the number of markets potentially shown. Its USD ETF market-price changes are **not national domestic-index returns**. The same Natural Earth layout and CEO 30-country universe are reused, but data contracts and visible labels are mutually exclusive. Neither mode constitutes a live automatic quote feed or data-rights entitlement.

## Purpose and exact country coverage

The CEO instructed an index-first world map for these **30 country/market labels, in this order**:

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
| 21 | **Saudi Arabia** | SAU | Tadawul All Share Index (TASI), source and exact price variant unverified |
| 22 | **Egypt** | EGY | EGX 30 price-index candidate, source/variant unverified |
| 23 | **Algeria** | DZA | **MISSING** — no qualified comparable domestic price-index series |
| 24 | Indonesia | IDN | IDX Composite price index |
| 25 | Vietnam | VNM | VN-Index price candidate |
| 26 | Russia | RUS | MOEX Russia Index — **MISSING**, source/rights/session unresolved |
| 27 | Kazakhstan | KAZ | KASE Index — **MISSING**, price variant/source unresolved |
| 28 | Iran | IRN | TEDPIX — **INCOMPARABLE**, return basis and rights unresolved |
| 29 | Poland | POL | WIG20 price index |
| 30 | Sweden | SWE | OMX Stockholm 30 price index |

There are **30 decisions**, not 30 guaranteed daily returns or confirmed live feeds. The index names above are **research candidates**, not checked symbol/variant assignments or licensed-data entitlements. A market index is an equity benchmark proxy and is **not** the performance of a country's GDP or the total national economy. The countries/markets are chosen editorially; this representation does not assert a position on recognition, territorial sovereignty or contested borders. Taiwan and other potentially sensitive geographic representation require independent editorial/legal review before a public release.

The CEO subsequently restored **Saudi Arabia** and added **Egypt and Algeria**, immediately after Turkey; 27 + 3 = **30 candidate markets**. Algeria remains unqualified until a comparable original price-index source, calendar and rights are independently proven. **Unqualified countries are omitted from market overlays entirely**, not highlighted as missing. There is no GDP-ranking fallback.

## Omission-only visual policy (CEO direction, 2026-10-20)

**Scan all thirty; only draw the qualifying subset.** Missing, stale, holiday, closed, unlicensed or incomparable cases remain in the source register with their reasons and null numeric returns. On the map their Natural Earth polygons receive the same `LAND` fill as non-selected countries, **never a special gray**. Do not list excluded countries in leader/laggard rows or a gray legend; no missing-denominator annotation. The selection can vary by date, so the graphic reports only the number actually shown, without asserting that all 30 moved or were observed.

The Singapore point/`SG` marker and `SG POINT` footer appear **only** when a qualifying Singapore series exists. If not qualified, neither is drawn. Preserve the public-facing context that these are *selected index observations*, not exhaustive global equity-market coverage. An internal audit record must keep the full 30-country scan history so omission is not concealed from reviewers. An immutable issue change, eligibility change or caption change invalidates earlier release approval.

## Geometry and Singapore

- Immutable public-domain **Natural Earth 1:50m Admin-0 v5.1.1**, with the same 177 map country IDs and substantially higher coastal/Arctic/island fidelity; [upstream Natural Earth source](https://github.com/nvkelso/natural-earth-vector/blob/master/geojson/ne_50m_admin_0_countries.geojson), upstream blob SHA `9d99f26dc470fcdbd08b062c813005acbdf73ccb`; normalized local asset `m1_natural_earth_50m_v5_1_1.json` pinned by Git blob SHA `9f298a1bac5923c787a8e2aaf937221da04c4a58`. Public-domain terms: https://www.naturalearthdata.com/about/terms-of-use/. The highlighted country must use the *identical* 50m country geometry/path as neutral background land; Canada has 141 multi-polygon Arctic/island parts, rather than the previous 110m simplification's 30, and regional/coastal shapes must not drift relative to the underlying map.
- **29 selected geographic IDs have real Natural Earth polygons. Singapore is absent at this map scale.** Draw a small explicitly labeled SG **geographic point locator**, at approximate 103.8198°E, 1.3521°N, over the real basemap; identify “SG POINT” in the footer. This is not a sovereign boundary or a replacement licensed polygon; independently validate the point and cartographic presentation before release.
- For the deterministic canonical M1 and **public release**, preserve the actual Natural Earth country polygons; no unreviewed freehand/generated geography is automatically publication-ready. A separate image-tool **working visual only** may be made when Python source is inaccessible, as provided below, but its borders must not be claimed as precise or verified until checked. Examine small Taiwan/European/Southeast Asian shapes at 390px where an actual mobile output exists. The public-domain basemap does not grant stock-index quotation rights.

**Operational distinction (CEO image-first direction):** Natural Earth 1:50m is the *canonical publication* geometry. For a requested Market Atlas visual **working draft**, lack of an executable GitHub Python checkout is not a reason to deliver only a status report when a separate image-capable tool exists. Try the existing deterministic M1 renderer first; otherwise visually reproduce the CEO-approved October 20 layout using available image generation/editing and real prices, with the method and any non-50m geography limitations identified **outside** the artwork. Do not claim such a draft is geometrically exact, SHA-verified or authorized for posting; independent geometry and factual audit precede CEO release approval. Never invent countries, prices or same-date evidence. No new renderer subsystem or test is required.

## Data contract (M1 v0.3)

The input requires: schema_version=1.0, template=M1, account=@therealpam, issue_id, cutoff_utc, headline/deck/interpretation/caption, universe_version, **selection_basis=CEO_SELECTED_30_COUNTRIES**, geometry_version, geometry_source_github_blob_sha, return_basis=DOMESTIC_INDEX_LOCAL_PRICE_RETURN, comparison_basis=LATEST_COMPLETED_SESSIONS, method_version, rights_note, universe_review, benchmark_registry_status, **scan_status**, and an evidence array of **exactly 30 records**.

Each record has a unique integer selection_order 1–30, matching the exact market/ISO code above. Selection order has **no economic ranking meaning**. The obsolete rank, rank_nominal_gdp_usd, gdp_observation_year, ranking_year, gdp_source_url, and gdp_vintage fields are not required by M1 v0.3 and must not be used as a basis for a numerical coverage claim. Singapore uses geometry_id=SGP_POINT; other rows require the exact pinned Natural Earth geometry join.

Each country has a candidate instrument name, provider/variant, benchmark definition, exchange/local quote currency, exposure note, verification and rights notes, plus an **explicit eligibility decision**. An eligible market requires an authentic original-price source URL. For an excluded country with no suitable quotation source, `original_price_source_url=null` is allowed; its unsuccessful source checks and exclusion rationale remain in the separate private scan record. Never invent a quotation URL to complete a failed candidate. Eligible price-index rows must have completed session/prior-session observed timestamps with offsets, observed and retrieved clocks before the UTC cutoff, exact prior/current numeric closes and signed percent return recomputed from those closes. If the price vs total-return basis, permission, integrity, completed session or comparability is not resolved, no numeric return may be supplied: mark MISSING, HOLIDAY, CLOSED, STALE or INCOMPARABLE rather than 0.00%.

Use a single symmetric red-to-green percentage scale for eligible local-index price returns. A **genuine 0.00%** return has its own neutral `EXACT 0.00%` key. **No missing-data color, missing-data legend, country-specific unavailable label or denominator `/30` appears on the plate**. Map headline still identifies the latest completed, **not synchronized** sessions. The on-image summary states only `N MARKETS SHOWN`; leader/laggard index rows draw exclusively from eligible market observations. Full all-30 inclusion/exclusion evidence remains in the internal audit packet, not in the on-image coverage display.

## Prototype proof vs real data

The fixture is a **synthetic visual exercise** with invented prices and returns and example.org placeholders. In this demo, **25 countries show fictional return colors**. The other five candidates (Brazil, Algeria, Russia, Kazakhstan, Iran) are **drawn as ordinary background land**, visually identical to countries never selected. The evidence register still records their exclusion reasons. Nothing in the graphic or synthetic data represents observed October 2026 market results, complete scanning, data-rights clearance or a verified index mapping.

Before any authentic M1 issue: the assigned research employee must **scan and resolve all 30 candidates for the intended as-of market day**, recording per-market examined source(s), actual observation/session, accepted return or reason for exclusion, retrieval/provenance and data-use qualification in a durable internal record. A scan is considered completed only after all 30 have an evidence-backed decision; merely writing `COMPLETE_AUDITED` is not independent proof. The renderer accepts `scan_status=SYNTHETIC_NOT_RUN` only for explicit demo inputs, and requires `scan_status=COMPLETE_AUDITED` plus separately reviewed universe/index/rights statuses for a real input. **PR #202 now provides an offline [30-market scan intake and assessment CLI](M1_DAILY_SCAN_HANDOFF.md) (`m1_scan_handoff.py`), but it does not implement an automatic network scanner, provider licensing, source capture or independent factual auditing**. The CLI starts with zero research and enforces full-universe disposition, original-source links and declared exact-use rights before a draft candidate; see the separate runbook. Independently verify exact price variant, official close, market calendar, exchange currency, quotation/redistribution rights, geographic joins, Singapore point, sensitive boundaries, calculations and native/mobile final asset. If too few valid comparable markets remain to sustain meaningful interpretation, **HOLD/SKIP** instead of making a misleading graphic.

Production still requires the exact CEO-approved SHA-bound reconstructed pine master, immutable issue/caption hash, independent factual/visual audit and **separate explicit CEO approval of the exact image and caption**. Visual Kit CI tests structurally deterministic code and rendering, not the authenticity, legal redistribution or public readiness of the data. No auto-publishing, fee-bearing feed, new external service, portfolio or investment decision authority is introduced.

## Intended regression gates

Reject missing/duplicate internal scan decisions, removal of the Saudi Arabia → Egypt → Algeria block, incorrect Singapore join, GDP-rank masquerading, invalid Natural Earth SHA/ISO join, invalid or unreviewed scan status, mixed return basis, inconsistent close arithmetic, fabricated zeros for missingness, impossible clocks, stale observations, release-logo mismatch, synthetic release or caption-hash drift. **Visual tests must verify noneligible target countries use precisely the same base-land fill as never-selected countries, no missing-data legend/label or `/30` denominator, and no Singapore marker when Singapore is unqualified**. Preserve the true-zero swatch, 390px text bounds and Antarctica crop.
