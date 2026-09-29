# PR5D1 — Controlled Free Current Quote Foundation

> One controlled current quote proposition only. PR5D1 does not establish the
> quote-to-PR5C share-basis bridge, construct a PR4B1 `ObservedPrice`, or grant
> final Expected Return admission.

## Verified base and scope

After `git fetch origin`, the approved integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `1c6df94d13c8027cd1032bdae841ee96cc8e3295` |
| Tree | `dee7598cb103b4452ea1bf2763f8f6abaedcd5d2` |
| Implementation branch | `codex/v2-pr5d1-controlled-current-quote` |

The initial worktree and index were clean. The prior local PR5C branch was
preserved. This PR adds only the controlled quote archive/acquisition/replay,
focused tests, the exact route-authority grant, this contract, and minimal
roadmap/decision records.

It does not modify V1, `MarketDataFetcher`, the fund fallback engine, PR4B1,
PR5C, Expected Return policies or mathematics, runtime, production, deployment,
dependencies, or model rules.

## One capability

PR5D1 answers one bounded question:

> At provider timestamp Q, did Yahoo Finance report a positive USD-per-share
> regular market price P for the exact direct Nasdaq symbol established by a
> freshly replayed successful PR5B route, and did PAM capture those exact Chart
> response bytes at C with Q no later than C?

Success is `CURRENT_QUOTE_ESTABLISHED`. It is not final admission and it is not
evidence that the current traded share uses PR5C's historical EPS presentation
basis.

## Exact free route

The only acquisition route is:

```text
GET https://query1.finance.yahoo.com/v8/finance/chart/<SYMBOL>
    ?range=5d
    &interval=1d
    &events=div%2Csplits
    &includePrePost=false
```

The canonical parameter serialization is fixed as:

```text
range=5d&interval=1d&events=div%2Csplits&includePrePost=false
```

Live schema inspection for a direct Nasdaq equity retained the required fields
under `/chart/result/0/meta`, including `symbol`, `currency`,
`regularMarketPrice`, `regularMarketTime`, `instrumentType`, `exchangeName` and
`fullExchangeName`. The one reviewed venue representation is exactly:

```text
exchangeName     = NMS
fullExchangeName = NasdaqGS
venue identity   = NASDAQ_GLOBAL_SELECT
```

Other Yahoo Nasdaq representations remain unsupported in v1. Venue, currency,
instrument type, and per-share meaning are never inferred from ticker syntax,
issuer domicile, or the SEC/Nasdaq source route.

The route requires no paid market-data subscription and preserves PAM's free-core
invariant. Failure returns unavailable/unsupported/conflict; it never triggers a
provider substitution.

## Why V1 Yahoo usage is not authority

V1 `src/data_fetcher.py` and `src/fund_price_fallback_engine.py` are operational
convenience paths. They may use mutable `yfinance` objects, cached data, chart
history, `previousClose`, or alternate fund sources. Those payloads and fallback
semantics are not imported, replayed, or trusted by PR5D1.

PR5D1 uses the Chart endpoint directly, stores exact response bytes, and accepts
only `meta.regularMarketPrice`. It never substitutes previous close, chart close,
adjusted close, bid, ask, pre-market, after-hours, last-known-good cache, manual
rate, fund fallback, or another provider.

## Immutable archive and acquisition API

```python
acquire_yahoo_current_quote(
    *,
    symbol: str,
    archive_root: str | Path,
) -> YahooQuoteAcquisitionResult
```

The public API accepts no raw bytes, price, currency, timestamp, provider result,
capture time, transport, authority, or qualification flag. The reviewed path
uses HTTPS with certificate/hostname verification, the fixed host and endpoint,
redirect rejection, bounded socket/deadline/body/header limits, identity-only
content encoding, JSON content type, disabled ambient proxies, and no retry or
fallback.

The archive preserves:

```text
exact raw response bytes
-> SHA-256 content object
-> immutable no-clobber publication
-> immutable receipt
-> deterministic receipt identity
```

The receipt contains the schema/source/resource identities, requested symbol,
exact endpoint and parameter profile, content hash, byte length, capture time,
and acquisition contract. It does not contain the price. Replay selects one
exact receipt ID; directory scans and latest-wins rules are absent.

## Strict extraction

```python
extract_yahoo_current_quote(
    quote_archive: YahooQuoteArchive,
    receipt_id: str,
) -> YahooCurrentQuoteExtraction
```

Replay requires strict UTF-8 JSON with duplicate keys and nonfinite constants
rejected, `chart.error == null`, exactly one `chart.result`, and one mapping at
`/chart/result/0/meta`.

The reviewed fields are:

- exact returned symbol;
- exact Yahoo exchange pair and reviewed venue identity;
- `instrumentType == EQUITY`;
- explicit `currency == USD`;
- positive finite `regularMarketPrice`, parsed directly as exact `Decimal`;
- integer `regularMarketTime`, excluding booleans, floats, and strings;
- canonical deterministic UTC conversion of the original epoch.

The original price token's Decimal representation and original market epoch are
retained. Binary float is never used in `economic_facts`. Unknown fields remain
preserved in the immutable source bytes and affect evidence identity, but grant no
new semantics.

## Qualification API and PR5B join

```python
qualify_yahoo_current_quote(
    quote_archive,
    current_archive,
    submissions_archive,
    filing_archive,
    ticker_exchange_archive,
    nasdaq_listed_archive,
    request,
) -> QualifiedCurrentQuote
```

The request contains the exact PR5B selector request, expected PR5B semantic and
evidence identities, one exact quote receipt ID, and expected quote extraction
semantic and evidence identities. It contains no caller price, currency, symbol
override, authority, or success boolean.

Qualification freshly replays PR5B and the quote receipt. Success requires:

- PR5B status `CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED`;
- quote symbol exactly equal to PR5B's selected direct-listing symbol;
- reviewed `NMS` / `NasdaqGS` venue representation;
- `EQUITY` instrument type;
- explicit USD currency;
- positive finite exact Decimal price;
- valid provider epoch/time; and
- provider market timestamp Q no later than receipt capture C.

The result retains PR5B's route-local issuer/security identities. Ticker-only
qualification, detached results, forged expected identities, and caller-order
selection are rejected.

Closed outcomes are:

- `CURRENT_QUOTE_ESTABLISHED`;
- `QUOTE_UNAVAILABLE`;
- `QUOTE_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

## Time semantics

The provider market timestamp and PAM capture timestamp remain distinct:

```text
Q = Yahoo regularMarketTime, converted from exact integer epoch to UTC
C = reviewed PAM capture time retained in the immutable receipt
Q <= C
```

Q is not called publication time, first availability time, exchange execution
time, or historical PIT authority. Replay uses no system clock and never advances
an old receipt because a newer quote exists.

## Factual authority versus permitted use

The exact registered route is:

`YAHOO_FINANCE_CHART_CURRENT_QUOTE_V1`

It may establish only exact-route acquisition provenance, capture-bound CURRENT
availability/snapshot scope, the observed market price, and quote currency/unit.
It has no `SHARE_BASIS_COMPARABILITY` or `FINAL_ECONOMIC_ADMISSION` power.

```text
license_status = UNKNOWN
use_status     = REVIEW_REQUIRED
```

The route is intended only for PAM's current private/internal research
development. No commercial display or redistribution permission is granted.
Commercial product use requires a separately reviewed provider/use decision.
This legal/use limitation is excluded from factual authority identity and does
not alter a valid extracted market price.

## Mandatory limitation and next step

Every result states:

`QUOTE_TO_PR5C_BASIS_BRIDGE_NOT_ESTABLISHED`

Yahoo's absence of a split event is not a complete no-event inventory. PR5D1
does not inspect or use Chart split events as bridge authority. Therefore:

```text
CURRENT_QUOTE_ESTABLISHED
!= QUOTE_TO_PR5C_BASIS_ESTABLISHED
```

PR5D2 remains mandatory to establish the quote-to-PR5C basis bridge and complete
the remaining non-EPS roots, owner-approved policies, and initial PR5D bundle.
PR5E remains the only final admission and real PR4B1 adapter. PR5D1 constructs no
`ObservedPrice` and changes no investment rule.

## Validation contract

Focused tests cover fixed endpoint/symbol policy, HTTPS/redirect/proxy controls,
bounded responses, content type and provider failures, immutable replay and
corruption, exact Decimal/timestamp parsing, every supported/unsupported quote
field, duplicate JSON keys, PR5B fresh replay and identity join, chronology,
semantic/evidence identity, source-use separation, explicit nonclaims, and V1
isolation.

The complete change is expected to route to `STANDARD`; only the isolated
heavyweight PIT adapter-equivalence module is excluded. Protected PIT,
determinism, model-rule, and frozen V1 identities remain unchanged.
