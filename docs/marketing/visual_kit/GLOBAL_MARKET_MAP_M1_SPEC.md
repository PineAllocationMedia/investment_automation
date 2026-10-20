# M1 — Global Equity Market Map (PROPOSED, NOT IMPLEMENTED)

**Use case:** an accurate geographic view of country-equity proxy **daily session returns** for the **20 largest national economies by a frozen nominal-GDP ranking**. It is **not** a map of countries' daily GDP/economic performance, and green/red do not imply national prosperity or a trade recommendation. Requires separate CEO approval before implementation and publishing.

## A. Frozen country universe

- **Rank basis:** a named primary statistical provider (e.g. IMF WEO / World Bank) **nominal GDP in current U.S. dollars**, *not* PPP, growth rate or aggregate market capitalization. Record source URL/table, publication vintage, estimate vs realized year, retrieval time, ranking formula and frozen `universe_version`. Do not mix different annual releases to build the ranking.
- Choose the top **20 national economies** with an explicit handling rule for separately reported economies/territories and competing geographic definitions. Aggregate regions (EU, Euro area) are **not individual countries** and must not silently displace their members. Do not hardcode today's 20 as timeless; changes require versioned review.
- Source a geo-join key (ISO 3166-compatible identifier with provenance and exception list). Record splits, missing geometry, contested boundaries and policy for territories. **Geographic polygons must come from reviewed licensed/publicly reusable geospatial data**; do not ask an image model or freehand illustrator to approximate sovereign outlines. No political-border representation is asserted authoritative.

## B. What exactly moves?

One comparable series **per country**, selected through an audited **proxy registry**, not a presumed ETF-for-every-economy shortcut. Proposed hierarchy:

1. **Preferred:** widely followed, representative **domestic equity index** with official historical closes, documented selection/weighting, relevant exchange and **local-currency price return** for a defined completed trading session.
2. **Fallback only with declared different contract:** legally usable exchange-traded fund (ETF) representing national equity exposure; **ETF trading-price return in one common currency** and same exchange/session rules for *all* countries, not a patchwork of local indexes and U.S. ETF quotes.
3. **No comparable eligible proxy:** render **MISSING/NOT COMPARABLE** and explain; do **not** silently proxy via an unrelated instrument or mix ETF/index return types under a single color scale.

Important: `S&P 500` is a large-cap U.S. index, **not literally “the whole U.S. economy”**, and `Nikkei 225` (`N225`) is one Japan-listed equity index, **not a standardized total-country return**. ETF ticker symbols can vary by exchange, currency and domicile; confirm the **actual fund mandate, underlying index, listed currency, share class, price venue, corporate-action adjustments and session**. No blanket “national index ETF” equivalence.

**Return basis must be chosen before rendering:** for local-index mode, `(official_close_t / official_close_previous_eligible_session - 1)*100` as a **local-currency index price return**, unless the selected official provider explicitly supplies a differently defined consistent price series. Do not mix total-return and price-return indices. For a uniform ETF mode, use a consistent venue/common settlement currency, adjusted-close convention and the same eligible local trading session definition for all entries; identify FX impact explicitly. All instrument selections and formulas are **versioned data**, not editorial guesses.

## C. As-of/session and missingness gates

Global exchanges close in different timezones and may be **open, closed, on holiday, halted or stale** when the post is composed. Declare a **single observation cutoff timestamp with timezone** and a precise rule for what constitutes an eligible completed session for every proxy. Record `local_session_date`, `previous_eligible_session_date`, `observation_utc`, `retrieved_utc`, exchange time zone, expected session open/close, corporate actions and freshness limit.

Never present asynchronous observations as though they were synchronized same-day trades. The headline should say e.g. **“Latest completed sessions, as of [timestamp]”** (not unqualified “today”) if local session dates differ. Prefer a **single comparable session cohort** where supported. If comparability is materially compromised, choose a regional summary or **SKIP M1**.

A market with no valid completed observation is **neutral gray + status `CLOSED/HOLIDAY/STALE/MISSING/INCOMPARABLE`** and receives no invented 0.0% movement. Do not carry forward prices as a live session return. Display coverage: `N/20 observed`; a complete `20 economies` performance claim requires all 20 eligibility decisions and explicit missing-status marks. Distinguish a genuine 0.00% eligible return (neutral near-zero bin) from missing data.

## D. Required map design and legend

- A **geographically accurate map** with consistent projection, source/license and country-id join; never warp country shapes to match data values. Confirm small-island and inset handling, disputed borders, and whether the chosen image is a recognizable map at **390px feed width**.
- **Diverging, symmetric, documented scale** around 0: red losses / green gains, saturation proportional to magnitude, **fixed shared return bins** and clear min/max saturation cap. A candidate, **not approved** scheme is `0–0.5 | 0.5–1.0 | 1.0–2.0 | >2.0 percentage points` with mirrored negative bins. Validate against a real sample before setting thresholds; never choose per-country ranges that exaggerate small moves or conceal outsized ones.
- Zero true eligible movement: muted neutral, **not missing gray**; closed/stale/missing/incomparable: separate neutral gray or hatch with a textual key. Use red/green with colorblind-accessible shapes/legend and **signed numeric returns** in an accompanying table or selectively annotated major movers; color alone must never convey sign.
- A world map at 390px **cannot legibly label twenty tickers/countries plus their changes inside polygons**. Use a map plus short **top movers/laggards table** and a separate full 20-row method/data sheet accessible in the source/evidence packet. Labels/insets must avoid overlaps; if a 4:5 map is unreadable, use a split image or text alternative, not shrink labels.
- Title clearly says `equity-index returns` or `ETF price returns` (as applicable), reference date/cutoff, currency basis, percentage unit, count of valid markets, publisher names, legal rights/disclaimers and coverage limitations. Full original URLs, retrieval timestamps, close prices, provenance and method live in evidence register.

## E. Minimum immutable input contract (proposal; renderer not yet built)

One `map_issue` record: `schema_version | issue_id | account | universe_version | gdp_source_url | gdp_vintage | ranking_year | cutoff_utc | return_basis | geo_dataset_version/license | caption | brand_logo_sha256 | copyright_notice_status | status=DRAFT`.

For **each** of 20 joined economies, require:

`economy_id | rank | rank_nominal_gdp_usd | gdp_observation_year | geometry_id | economy_name | instrument_kind=INDEX|ETF|UNAVAILABLE | instrument_id | instrument_provider | country_exposure_note | benchmark_definition | listed_currency | return_currency | close_session_date | prior_session_date | close_timestamp_utc | close_price | prior_close_price | adjustment_policy | signed_return_pct | original_price_source_url | observed/retrieved timestamps | data_rights_note | verification | missing_status`.

Cross-record `method_version` must be identical. Reject duplicate ranks/IDs, unknown geometries, missing sources, divide-by-zero/NaN, signs inconsistent with computed returns, impossible unreviewed outliers, mismatched basis or stale observations, and unsupported geodata licenses. Store exact dataset checksums and rendering version to reproduce the same map. Data is not “verified” just because the JSON says `VERIFIED`.

## F. Independently audited publication readiness

Before any `M1` renderer implementation, complete a **research/proxy methodology review**, authoritative instrument selection register, source rights/redistribution review and geospatial licensing review with Commercial & Compliance as needed. Audit sample data across at least: positive, negative, zero, closed, missing, stale, FX discrepancy, simultaneous but different exchange dates, absent geometry and boundaries. Test map/swatch contrast and every legend bin.

A new deterministic renderer must pass synthetic and authentic replay checks **without implying the authentic test itself authorizes distribution**. The first real issue requires independent original-source verification of all 20 ranks/proxies/returns, chart/legend tests, 390px inspection, and separate CEO approval of **exact map + caption**. If coverage cannot support the claimed geographic picture, **HOLD/SKIP**.

This is a methodological **proposal only**. No country ranking, real-time return, national ETF ticker list, baseline performance or map artwork is approved in this file.
