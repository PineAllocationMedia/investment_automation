# PR5D0B — Controlled SEC verified-nonpayer source qualification

> Source evidence only. This contract establishes one narrow issuer-level
> Companyfacts nonpayer proposition. It does not create a PR4B1
> `VerifiedNonpayer`, selected-class authority, final economic admission, or a
> dividend-paying-company route.

## Verified base and scope

After `git fetch origin`, the approved integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `fed2ffbbb580faf1e474ca801405ad304eefec31` |
| Tree | `b7b1ce297b1ba6aee6a13fd3496c3b0190ae2827` |
| Implementation branch | `codex/v2-pr5d0b-sec-verified-nonpayer` |

The starting worktree and index were clean. The previous local PR5D0A branch was
preserved. This PR adds:

- `economic_facts/sec_common_stock_dividends.py`;
- `economic_facts/sec_verified_nonpayer.py`;
- focused fictional fixtures and tests;
- this contract; and
- one minimal roadmap update.

It does not modify PR4B1, Expected Return mathematics, source-authority grants,
model rules, V1, runtime, production, deployment, or any provider acquisition
route.

## Source-semantics checkpoint

The checkpoint succeeds for this deliberately narrow source proposition.

The official SEC [EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
states that Companyfacts aggregates standard-taxonomy facts from filings, and
that the aggregated facts apply to the entire filing entity. It also confirms
that the Companyfacts endpoint returns all company-concept data for one CIK in
one JSON response. The existing C1/C2 archive and acquisition contracts already
preserve those exact response bytes and their controlled capture provenance.

The reviewed US-GAAP taxonomy concepts are exactly:

```text
us-gaap:CommonStockDividendsPerShareDeclared
us-gaap:CommonStockDividendsPerShareCashPaid
```

Their taxonomy meanings are respectively aggregate common-stock dividends per
share declared during the period and aggregate common-stock dividends per share
cash-paid during the period. The FASB's current
[US GAAP Taxonomy FAQ](https://xbrl.fasb.org/resources/taxonomyfaq.pdf) also
distinguishes the declared-period amount regardless of whether it has already
been paid.

These semantics permit the following positive source proposition only:

> For the exact requested annual period, the controlled Companyfacts source
> contains supported annual facts stating both common-stock dividends per share
> declared and common-stock dividends per share cash paid as exactly zero, with
> no contradictory retained evidence for that period.

Because Companyfacts is issuer-level and does not itself establish the selected
PR5B security/class, the result retains
`NO_SELECTED_SECURITY_CLASS_JOIN`. No missing fact, empty array, absent positive
value, business description, yield, or market convention can establish zero.

## Architecture

```text
one exact SecArchive Companyfacts receipt
  -> extract_common_stock_dividends(exact bytes, receipt)
     -> every row for exactly two reviewed standard concepts
  -> resolve_sec_verified_nonpayer(archive, closed request)
     -> exact annual-period and retained-version resolution
     -> shorter-period contradiction inspection
     -> positive issuer-level source condition or explicit failure
```

`sec_common_stock_dividends.py` is lossless extraction only. It performs no
qualification. `sec_verified_nonpayer.py` is one strict resolver, not a generic
dividend engine. Neither module calls acquisition, network, filesystem writes,
clock, configuration, model code, or runtime code.

The resolver reads one exact receipt. It never selects archive latest, combines
receipts, calls Companyfacts independently, or creates another downloader or
archive.

## Extraction API

```python
extract_common_stock_dividends(
    raw: bytes,
    receipt: CaptureReceipt,
) -> CommonStockDividendExtraction
```

Extraction version:

`2026-09-28-sec-common-stock-dividends-extraction-v1`

Only `facts["us-gaap"]` and the two exact reviewed concept names are consumed.
No extension concept, fuzzy tag, generic dividend, total cash-dividend,
payment-of-dividends, preferred-stock, or partnership-distribution concept is a
substitute.

Every retained observation contains:

- observation and semantic IDs;
- CIK, namespace, exact concept, and exact unit;
- exact `Decimal` value;
- start, end, FY, FP, form, filed date, accession, and frame;
- source-object hash, receipt ID, and capture time;
- extraction version;
- exact RFC-6901-style JSON pointer;
- stable semantic locator;
- canonical raw row, including unknown fields; and
- explicit metadata limitations.

The semantic ID binds issuer, namespace, concept, unit, and the complete raw row.
It is stable under mapping and row reordering and equivalent decimal spellings.
The observation ID additionally binds exact source object, receipt, pointer, and
extraction version. No binary float conversion occurs.

Missing concepts or empty arrays produce explicit concept-unavailable issues.
They never produce zero. Malformed JSON, duplicate keys, invalid CIK identity,
or malformed structures fail closed.

## Resolver API and request closure

```python
resolve_sec_verified_nonpayer(
    archive: SecArchive,
    request: VerifiedNonpayerRequest,
) -> VerifiedNonpayerSourceResult
```

Contract and resolver versions:

```text
2026-09-28-sec-verified-nonpayer-source-v1
2026-09-28-exact-two-concept-zero-consensus-v1
```

The frozen/slotted request contains exactly:

- contract version;
- exact Companyfacts receipt ID;
- exact ten-digit CIK;
- exact `latest_required_fiscal_end`;
- exact expected unit; and
- typed period policy.

The first route supports only `USD/shares` and the same fixed-month-end 365/366-
day calendar policy used by C3. The request contains no ticker, security ID,
share class, caller observations, source bytes, provider URL, as-of override,
`nonpayer=True`, `qualified=True`, or authority override.

Only a LIVE C2 receipt can establish the positive source route. An OFFLINE C1
fixture remains inspectable but returns `OFFLINE_CAPTURE_ONLY`.

## Exact annual-period contract

The requested period is the supported twelve-calendar-month interval ending on
the exact requested month end, with an inclusive duration of 365 or 366 days.
Annual evidence must have:

```text
form in {10-K, 10-K/A}
fp == FY
unit == USD/shares
exact requested start and end
valid accession and filing chronology
known supported row context
```

No quarter summation, TTM substitution, FY-label date inference, older-period
fallback, 52/53-week acceptance, or annualization occurs. Missing latest evidence
returns unavailable. A later apparent complete annual period in the same source
snapshot returns `LATER_ANNUAL_PERIOD_PRESENT`; the caller cannot window-shop an
older year and call it latest.

## Exact-zero and retained-version rules

Positive qualification requires, simultaneously:

```text
declared annual value == Decimal(0)
paid annual value     == Decimal(0)
```

There is no epsilon, rounding, tolerance, or float comparison. `0` and `0.0`
canonicalize to the same exact economic zero. Any positive decimal, however
small, is nonzero payer evidence. A negative value is unsupported/conflicting
source evidence.

For each concept and exact annual period, every comparable filing version is
retained. Every version must agree on zero. An original and amendment do not
vote, supersede, or win by filing date, accession, order, or majority. Equivalent
duplicates are allowed but do not increase authority. A semantic ID may choose a
deterministic citation only after economic agreement exists.

Valid positive annual evidence is not a parser failure. It returns nonpayer
unavailable with `NONZERO_DECLARED_DIVIDEND` or
`NONZERO_PAID_DIVIDEND`. Differing retained values return
`SOURCE_CONFLICT` and `UNRESOLVED_VALUE_CONFLICT`.

## Intra-period and later-period semantics

The resolver also inspects valid shorter or overlapping observations for the two
reviewed concepts. A positive observation whose economic interval intersects the
requested annual interval produces
`INTRA_PERIOD_POSITIVE_DIVIDEND_EVIDENCE`. It is contradiction evidence only;
the resolver never sums it into an annual value.

Malformed or unresolved overlapping contexts fail closed. A valid positive fact
whose economic period begins after the requested annual period does not
retroactively invalidate that historical annual conclusion. A later complete
annual period still triggers the separate anti-window-shopping rule above.

## Status, reasons, identity, and limitations

Closed result statuses are:

- `VERIFIED_NONPAYER_SOURCE_ESTABLISHED`;
- `UNAVAILABLE`;
- `SOURCE_CONFLICT`; and
- `UNSUPPORTED_SOURCE_PROFILE`.

Closed reasons distinguish missing declared/paid concepts, missing required
annual evidence, declared/paid positive values, intra-period positive evidence,
value conflict, negative values, unit/CIK mismatch, unsupported calendar,
invalid chronology/filing identity/context, malformed source, later annual
evidence, and offline-only capture.

Semantic identity binds the exact economic request, period, concepts, status,
reasons, and stable retained semantic observations. Evidence identity additionally
binds the receipt/capture provenance, exact object, extraction occurrences,
pointers, and decisions. Therefore row/mapping order and recapture do not change
economic semantics; exact transport or capture provenance changes evidence
identity.

Every result explicitly retains:

```text
CURRENT_SNAPSHOT_ONLY
NO_SELECTED_SECURITY_CLASS_JOIN
NO_SHARE_BASIS_QUALIFICATION
NO_REPORTING_SUBJECT_QUALIFICATION
NO_FINAL_ECONOMIC_ADMISSION
NO_PR4B1_VERIFIED_NONPAYER_ROOT
PAYER_ROUTE_NOT_SUPPORTED
UPSTREAM_SOURCE_EVIDENCE_ONLY
```

PR5B must be freshly replayed by a later join to establish the selected supported
ordinary common route. PR5C remains source-blocked and neither share-basis nor
reporting-subject authority is implied by zero per-share values.

## PR4B1 and payer boundaries

This PR does not import or construct
`src.expected_return_assumptions.VerifiedNonpayer`, modify
`expected_return_assumptions.py`, or add an Expected Return consumer. A future
PR5E adapter may map this source result only after every required PR5B/PR5C/PR5D
join succeeds.

Dividend-paying-company support is explicitly deferred. Companyfacts' aggregate
standard tags do not alone establish PR4B1's ordinary annual dividend with
special distributions explicitly excluded. This PR implements no ordinary-
dividend qualification, special-dividend exclusion, dividend aggregation,
payout ratio, sustainability, forecast, or payer policy selection.

## Explicit answers

```text
Does missing dividend data prove nonpayer status? NO.

Are both zero declared and zero paid facts required? YES.

Does PR5D0B establish the selected PR5B share class? NO.

Does PR5D0B establish share-basis comparability? NO.

Does PR5D0B produce a PR4B1 real VerifiedNonpayer root? NO.

Does PR5D0B support dividend-paying companies? NO.

Does PR5D0B change Expected Return mathematics? NO.

Does PR5D0B change V1 or production behavior? NO.
```

## Validation expectations

Focused tests cover positive zero agreement; every missing-evidence case; payer
evidence; original/amendment and cross-concept contradictions; intra-period and
later-period semantics; exact Decimal behavior; negative values; calendar,
metadata, CIK, unit, chronology, and source failures; deterministic semantic and
evidence identities; immutable closed requests/results; replay purity; and the
absence of Expected Return/runtime/V1 consumers.

Adjacent SEC archive, acquisition, extraction, C3, PR5B, source/current-authority,
and isolation tests remain required. Python compilation and Git whitespace checks
must pass before publication. GitHub CI runs the complete suite.

Protected identities remain unchanged:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`; and
- frozen V1 commit/tree: `c5fc27c82c29c2a6027eccee245098c4a072fdf1` /
  `26a69bb0b2185ab141af0763da2d965602c8346b`.

## Completed local validation

Validation used Python 3.12.14 and the repository's disposable isolated runner.
No live SEC request, real issuer analysis, positive-capital analysis, or full
local suite was run; GitHub CI owns the complete-suite duplication.

| Scope | Tests | Result |
| --- | ---: | --- |
| Dividend extraction focused | 9 | PASS |
| Verified-nonpayer resolver focused | 28 | PASS |
| All SEC tests, including archive/acquisition/C3/PR5B | 884 | PASS |
| Current authority | 17 | PASS |
| Source authority | 11 | PASS |
| Expected Return | 156 | PASS |
| Runtime isolation | 29 | PASS |
| Validation identity isolation | 19 | PASS |
| PR2 investment equivalence | 1 | PASS |
| PIT source export | 6 | PASS |
| PIT Expected Return diagnostics | 19 | PASS |

Changed/relevant Python compilation and working-tree whitespace validation also
passed. Staged and committed-tree whitespace checks are performed during
publication. No protected expectation was regenerated.
