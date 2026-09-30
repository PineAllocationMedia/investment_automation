# PR4D4C1 — Controlled SEC CIK/ticker/exchange association snapshot

> SEC association source claim != economic issuer identity != security or
> share-class identity != qualified listing != historical continuity != final
> admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`7cba3ccc14c99e6cf24f08b1a87623884017e1d3`, tree
`95be78496fbb4f55a6381855cb377ced4fb4451f` (post-merged PR #55 / PR4D4B).
The worktree and index were clean. Branch
`codex/v2-sec-ticker-exchange-association-snapshot` was created directly from
that verified remote commit; the prior branch and all divergent/stale refs were
preserved.

This PR adds only a controlled exact-byte capture rail, dedicated immutable
archive, and deterministic offline replay for the fixed SEC association file.
It does not join or modify D4B, D4A, D3A, D3B, D2B, D2C, Companyfacts,
`security_identity.py`, price providers, Expected Return, model/runtime/V1, or
any production path. `source_authority.py` and every `AuthorityProperty` remain
unchanged.

Added:

- `economic_facts/sec_ticker_exchange_archive.py`
- `economic_facts/sec_ticker_exchange_acquisition.py`
- `economic_facts/sec_ticker_exchange_snapshot.py`
- `tests/sec_ticker_exchange_fixtures.py`
- `tests/test_sec_ticker_exchange_archive.py`
- `tests/test_sec_ticker_exchange_acquisition.py`
- `tests/test_sec_ticker_exchange_snapshot.py`
- `EXPECTED_RETURN_PR4D4C1.md`

The only existing-file change is the narrow dependency-test allowlist update in
`tests/test_sec_acquisition.py`, permitting this reviewed acquisition adapter to
reuse the shared SEC transport. No model rule changes.

## Official source, purpose, and limitation

The only endpoint is:

`https://www.sec.gov/files/company_tickers_exchange.json`

The legacy `/data/` redirect location, alternate paths, mirrors, discovery,
fallback providers, and HTML search scraping are unsupported. Redirects are
rejected.

The file supplies a useful SEC source claim connecting a CIK, EDGAR-conformed
company name, ticker text, and exchange text. The official
[SEC EDGAR data-access documentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
describes these files as periodically updated for EDGAR search functionality and
warns that it does not guarantee their accuracy or scope. PAM preserves that
limitation:

- presence is not independently sufficient economic identity qualification;
- absence is not proof that no security or listing exists;
- ticker/name/exchange text is not durable identity, a fuzzy-match key, a MIC,
  quote currency, wrapper classification, or admission.

## Acquisition contract

```python
acquire_sec_ticker_exchange_associations(
    *, archive_root: str | Path,
) -> SecTickerExchangeAcquisitionResult
```

The public caller supplies only an archive root. There is no URL, source bytes,
capture/publication time, clock, transport, retry policy, User-Agent override,
CIK/ticker filter, authority, completeness, or qualification input.

The adapter reuses the reviewed shared SEC administrative User-Agent validator,
per-user/cross-process rate gate, verified TLS transport, disabled environment
proxies, redirect rejection, duplicate-safe response headers, 15-second socket
timeout, 60-second response deadline, bounded streaming reads, and one-request/
no-retry behavior. It sends `Accept: application/json` and
`Accept-Encoding: identity`; only JSON with optional UTF-8 charset and absent or
identity content encoding is accepted. The exact body is bounded at 32 MiB,
structurally preflighted, then archived without reserialization.

The controlled local chronology is nondecreasing:

```text
request_started_at <= response_completed_at <= receipt.captured_at
```

HTTP `Date`, `Last-Modified`, and `ETag` cannot manufacture source publication,
availability, effective-listing, or historical semantics. No retry, response
cache, conditional request, alternate endpoint, or provider fallback exists.

## Dedicated immutable archive

`SecTickerExchangeReceipt` is frozen/slotted and binds exactly:

| Field | Meaning |
| --- | --- |
| `schema_version` | `2026-09-26-sec-ticker-exchange-receipt-v1` |
| `source_kind` | `SEC_COMPANY_TICKERS_EXCHANGE_JSON` |
| `resource_kind` | `SEC_TICKER_EXCHANGE_ASSOCIATIONS` |
| `endpoint` | exact fixed HTTPS endpoint |
| `content_sha256` | SHA-256 of exact response bytes |
| `byte_length` | exact positive length, at most 32 MiB |
| `captured_at` | internally sampled, explicit-offset UTC-canonical local capture time |
| `acquisition_contract_version` | `2026-09-26-sec-ticker-exchange-acquisition-v1` |

Receipt identity is domain-separated SHA-256 over canonical closed JSON.
Objects are content-addressed. Identical bytes recaptured at another time reuse
the object but create a distinct receipt; changed captures preserve both.
Publication uses private temporary files, flush/fsync, read-only permissions and
an atomic no-clobber link. Existing evidence is verified and never overwritten.

Descriptor-relative traversal rejects symlinks, extra hardlinks, FIFOs,
directories-as-files, unsafe parent components, missing membership and corrupt
length/hash/receipt identity. Reads are bounded and create no directories or
files. The archive exposes only explicit `read_receipt` and `read_object`; it has
no directory discovery or “latest receipt” API. This is a trusted-local-code and
storage integrity model, not an SEC signature or protection against an actor who
controls the archive, application code, and trust anchors.

## Exact source structure and safety bounds

Only this JSON shape is supported:

```json
{
  "fields": ["cik", "name", "ticker", "exchange"],
  "data": [[1234567, "FICTIONAL CORP", "FICT", "Nasdaq"]]
}
```

The top-level object must have exactly `fields` and `data`; the field vector is
exactly the four values above and every data row is a JSON array of exactly four
cells. Duplicate JSON keys, NaN/Infinity, malformed UTF-8/JSON, excessive
nesting, and unreviewed extensions fail closed.

CIK must be an integer source value (booleans and coercions rejected) from 1
through 9,999,999,999. Each source string is retained exactly, nonempty and
bounded; lone Unicode surrogates are rejected. Ticker additionally must remain
one whitespace/control-free source token. Company-name and exchange whitespace,
including an escaped source line break, is retained rather than normalized.
PAM limits are 100,000 rows,
4,096 code points for name, 128 for ticker, 512 for exchange, four JSON container
levels, and 32 MiB exact source bytes. These are implementation safety limits,
not SEC completeness guarantees. No malformed value is coerced or truncated.

## Replay and source-row semantics

```python
replay_sec_ticker_exchange_snapshot(
    archive: SecTickerExchangeArchive,
    request: SecTickerExchangeSnapshotRequest,
) -> SecTickerExchangeSnapshotAssessment
```

The frozen/slotted request contains exactly `receipt_id`. Replay reads and
verifies that explicit receipt and complete snapshot. It performs no network,
write, clock read, directory scan, implicit selection, filter, or acquisition.

Every frozen/slotted row retains exact receipt, zero-based source row position,
source CIK integer, source company name, source ticker and source exchange. It
also exposes a ten-digit zero-padded SEC CIK representation; this is only a
deterministic SEC adapter normalization and is never a PAM entity ID.

All source rows survive. One CIK may have multiple tickers and exchanges. No
one-to-one issuer/security assumption, primary-listing choice, winner, latest,
first, majority vote, alphabetical selection, silent deduplication, fuzzy name
normalization, ADR inference, exchange-to-MIC mapping, or currency inference is
performed.

Exact duplicate rows remain distinct occurrences and are reported under
`SOURCE_AMBIGUITY`; increasing duplicate multiplicity does not strengthen the
association semantic identity. A ticker text associated with multiple CIKs is
also diagnostic `SOURCE_AMBIGUITY`, not an economic conflict or cross-row join.
Multiple different ticker/exchange rows for one CIK remain ordinary preserved
source associations. The source documentation reviewed here establishes no
stronger uniqueness invariant, so `SOURCE_CONFLICT` is deliberately absent.
Otherwise status is `CAPTURED_SEC_TICKER_EXCHANGE_SNAPSHOT`.

## Time and deterministic identity

`receipt.captured_at` means only when PAM controlled-captured the exact bytes. It
is not source publication time, first public availability, effective listing
date, listing start, historical knowledge, continuous validity, or evidence that
no event occurred before/after capture. No midnight or HTTP-derived timestamp is
invented, and no `HISTORICAL_AS_OF` authority exists.

Domain-separated SHA-256 identities use
`pam:sec-ticker-exchange:{domain}:v1`. Row semantic identity binds the exact four
source values. Occurrence identity additionally binds receipt and source row
position. Snapshot semantic identity binds contract, unique association
semantics and narrow diagnostic state, without path/environment/capture time or
duplicate multiplicity strengthening. Evidence identity additionally binds the
exact receipt ID, object digest, capture time, and every occurrence identity.
Thus identical-byte recapture preserves semantics and changes evidence.

## Authority boundary

There is no D2C, D4B, D4A, D3A, D3B, D2B, Companyfacts, price-provider, or
synthetic-identity join in this PR. No ticker equality or company-name similarity
qualifies anything. CIK remains an SEC adapter identifier and does not enter a
source-neutral global economic identity contract.

| Property | State after PR4D4C1 |
| --- | --- |
| 4A | Unresolved — CIK/name association is not issuer economic identity. |
| 4B | Unresolved — ticker association is not economic security identity. |
| 4C | Unresolved — no legal/economic class identity or rights. |
| 4D | Unresolved — no complete relevant class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement. |
| 4F | Unresolved — exchange text is not a qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — snapshot scope is not a complete/scoped listing inventory. |
| 4H | Unresolved — capture is not historical security/listing continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission. No
source route, provider-wide trust, authority property, ER fact, score, allocation,
runtime consumer, V1 change, deployment, Chromebook action, or V2 promotion is
introduced.

## Validation and next handoff

Tests use fictional deterministic JSON and patched transport; no live SEC source
is captured and no positive-capital analysis is run. Validation covers fixed
endpoint/headers, reviewed SEC User-Agent, verified TLS/no proxies, redirect and
non-200 rejection, timeouts/deadline, no retry, MIME/encoding/framing/size bounds,
exact bytes, immutable publication, corrupt evidence, explicit replay, structural
and value rejection, multiple associations, diagnostic ambiguity, deterministic
identities, offline/no-write/no-clock/no-discovery behavior, and one-way dependency/
authority isolation.

The 50 new focused tests pass. Adjacent selections covering shared SEC transport,
Nasdaq Listed, SEC Submissions, filing capture, D3A/D3B, D4A/D4B, authority,
CURRENT evidence, Expected Return, runtime isolation, validation isolation and
investment equivalence also pass; the focused and adjacent selections total 810
passing tests. The complete isolated suite passes **2,148 tests in 732.805
seconds**, with no failures or skips.

The full suite exercised all 64 protected PIT equivalence scenarios and
reproduced, without regenerating expectations:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

The existing environment uses Python 3.12.14 against the unchanged repository
pin 3.12.13. No dependency, lockfile, runtime, protected expectation or model
version is changed. Final whitespace, staged-diff, committed-HEAD, remote-base
and clean-worktree checks are completed during publication.

The likely next frontier is a separately reviewed PR4D4C2 CURRENT real
issuer/security/listing evidence bridge comparing independently replayed evidence.
That future contract must define which agreements establish which narrow claims;
ticker equality and company-name similarity remain insufficient. This PR neither
pre-authorizes that bridge nor decides its qualification rules, merge, deployment,
or authority.
