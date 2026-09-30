# PR4C2 — Trusted SEC companyfacts acquisition

PR4C2 proves:

> Reviewed code can acquire the canonical SEC companyfacts endpoint, enforce a
> declared/fair-access network contract, mint capture time internally, validate
> the response and publish exact received source bytes into the PR4C1 archive
> under a distinct LIVE acquisition identity.

PR4C2 does NOT prove:

> The archived SEC observations are already qualified PR4B1 Expected Return facts.

This is a capability implementation. Validation uses fictional CIK `0000000000`,
synthetic bodies and a patched private transport, with socket access forbidden
by the existing isolated runner. No companyfacts endpoint was requested, no real
issuer response was downloaded, and the CLI was not run against SEC. Official
SEC policy pages alone were read to revalidate the access requirements.

## Verified base and branch scope

After fetch, authoritative `origin/model-v2/expected-return-challenger` was
`948bc2c45ba3d9f12192100976df45b9d7ae6d8e`, tree
`4493e689fb7560c27cdc587093c0d7941644b941`. `origin/main` remained
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`. The clean initial checkout was
`codex/v2-sec-diluted-eps-archive` at
`1e3315761c9ed37236acf29d5e049c9fb2356d10`.

The local `main` ref was `abc37bd52c24b2d68adf8138e57625327a3251b7` and local
`model-v2/expected-return-challenger` was
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`. Work stopped on that discrepancy.
The user explicitly authorized proceeding from the verified remote V2 commit
while leaving both local refs untouched. Branch
`codex/v2-sec-live-companyfacts-acquisition` was created from the exact required
commit, and its HEAD/tree were immediately verified against the values above.
The sole PR base is `model-v2/expected-return-challenger`; no merge is authorized.

## SEC policy checked September 11, 2026

Official sources:

- [EDGAR Application Programming Interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
  states that public `data.sec.gov` APIs require no authentication/API key and
  documents the ten-digit companyfacts endpoint. Page last reviewed April 8, 2025.
- [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
  requires a declared User-Agent, illustrates organization/contact identification,
  and gives the current 10 requests/second maximum.
- [Developer Resources](https://www.sec.gov/about/developer-resources)
  specifies at most 10 requests/second per user across machines. Page last
  reviewed March 10, 2025.

No material difference from the supplied policy was found. PR4C2 uses at most
four requests/second per shared local acquisition gate, below the requested
five/second internal ceiling and the SEC maximum. This does not coordinate V1,
other applications, other operating-system users or other machines.

## Architecture and authority boundary

```text
acquire_companyfacts(cik=..., archive_root=...)
  -> existing exact ten-digit CIK validator / canonical endpoint constructor
  -> required environment User-Agent validation
  -> per-user nonblocking flock + full 250 ms pre-request wait
  -> one direct verified HTTPS GET (no proxy, redirect, retry or cache)
  -> HTTP 200 / endpoint / media type / encoding / bounded-body checks
  -> internally observed UTC response completion
  -> strict companyfacts structural preflight on a parsed copy
  -> internally observed UTC capture time
  -> SecArchive._capture_live -> original object-first immutable publication
  -> frozen SecAcquisitionResult
```

The only application dependency from `sec_acquisition` is `sec_archive`.
HTTP concerns are isolated in the new module. No model, PR4B1, PIT, portfolio,
scanner, allocation, scoring or report consumer imports acquisition. The package
initializer has no imports or side effects. The existing diluted-EPS extractor,
V1 `src/official_data_fetcher.py`, V1 caches and all investment logic are unchanged.

The request URL is constructed only as
`https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` from an exact
ten-digit ASCII CIK. No caller URL, hostname, query, SSL context, transport,
timestamp or rate override is exposed. `urllib.request` gets a fresh private
opener with `ProxyHandler({})`, suppressing environment/system proxy discovery;
no global opener is used. `ssl.create_default_context()` preserves the normal
trust store, required certificate verification and hostname verification.
Redirects fail closed, including redirects back to the canonical resource;
the final response URL must also match. No alternate endpoint or provider exists.

## Runtime User-Agent

`INVESTMENT_AUTOMATION_SEC_USER_AGENT` is mandatory. Configure it privately at
runtime with an organization/application identity followed by an administrative
email contact. The syntax check does not verify ownership or deliverability.
Accepted values are 1–256 printable ASCII characters without surrounding
whitespace. Empty values, controls (including CR/LF, tab and DEL), non-ASCII,
the legacy placeholder, browser-style defaults, missing contact, and contact-only
values fail before network access. No real contact identity is committed.

Request headers are `User-Agent`, `Accept: application/json` and
`Accept-Encoding: identity`; the HTTP library supplies normal protocol headers.
No browser impersonation, authorization key or conditional request is used.
The result records only `declared_user_agent_used=True`. Exceptions expose a
fixed category and optional numeric status, suppressing underlying exception
text; CLI output never includes the contact or response body. Selected response
metadata also omits values reflecting the configured identity/contact.

## Fair-access gate

The stable lock is `~/.investment_automation/sec_acquisition/gate.lock`, shared
by invocations using the same local home, regardless of archive root. The final
state directory and lock reject symlinks, foreign ownership and group/world
write access; the lock must be a regular file with one link. The lock inode is
never replaced, removed, or written with acquisition data. Keep the home/state
location consistent across processes and do not remove the lock during use.

An exclusive nonblocking POSIX `flock` covers the full wait, request, validation
and publication. A competing caller receives `RATE_LIMITED` without a request
or retry. Every successful lock acquisition waits a full 250 ms before its
request, using a monotonic deadline and rechecking early wakeups. There are no
saved tokens or burst credit. Even after failure, process exit or a crash, the
next holder waits a fresh interval. Thus local request starts are at least
250 ms apart without persisted wall-clock state. Throughput is generally slower
because requests are serialized. Tests replace private sleep/monotonic functions
and verify actual interprocess flock exclusion without production sleeps.

## Response bounds and exact-byte transport contract

- Socket-operation timeout: **15 seconds**, passed to the private opener.
- Response deadline: **60 seconds** from request start, checked before/after
  each bounded read. This is not a hard process deadline: an in-progress socket
  operation may last until its socket timeout; OS DNS resolution, headers and
  HTTP framing are handled by the standard library. No bounded-completion claim
  is made for the operating-system resolver or filesystem operations.
- Body limit: **32 MiB (33,554,432 bytes)**. This is a deliberate tens-of-MiB
  per-issuer ceiling, leaving space for a broad multi-concept companyfacts
  snapshot while bounding acquisition memory and archive growth per call. It is
  not a measured promise that every real issuer fits; a larger response fails
  and requires separate review rather than automatically increasing the limit.
- Reads use `read1` in at most **64 KiB** chunks, requesting at most the remaining
  limit plus one byte. No unbounded `.read()` occurs in acquisition code.
- A present Content-Length must be one decimal value (at most 20 digits), fit the
  ceiling, and equal the final body length. Missing length is allowed; actual
  reads still enforce the ceiling. Duplicate framing/media headers, unsupported
  transfer encodings and simultaneous chunked/Content-Length framing fail.

Archived bytes are the exact response entity/body bytes delivered by the HTTP
client after HTTP transfer framing (including chunk framing) is removed. They
are **not raw wire/TLS bytes**. `Content-Encoding` must be absent or `identity`;
compressed responses are rejected, never decompressed. The original received
bytes are hashed and published without stripping, reordering, pretty-printing
or reserialization. Parsing is only preflight. Numeric parsing cannot alter the
object bytes or the later PR4C1 Decimal extraction.

## HTTP failures and structural preflight

Only HTTP 200 is eligible. All 3xx are `REDIRECT_REJECTED`; 429 is explicitly
`RATE_LIMITED`; 403, 404, 5xx and other non-200 statuses are `HTTP_ERROR` with
the numeric status. There are **no automatic retries**, including on 429 or a
Retry-After header. Error response bodies never become archive objects.
Timeouts are `TIMEOUT`; TLS, connection and HTTP transport failures are
`NETWORK_ERROR`. Other categories are `CONFIGURATION_ERROR`,
`RESPONSE_TOO_LARGE`, `INVALID_CONTENT_TYPE`, `INVALID_RESPONSE`, and
`ARCHIVE_ERROR`. A failure is never interpreted as issuer nonreporting.

Before publication the response must have `application/json`, optionally with
an explicit UTF-8 charset parameter (case insensitive, optionally quoted).
Unknown charset/parameters and non-JSON media types fail closed. The body must
decode as strict UTF-8 and parse as one JSON object with no trailing nonwhitespace,
duplicate keys or nonfinite numbers. Floating numeric overflow also fails
conservatively. Excessive nesting/parser failures fail before publication.
`cik` must be an integer in the existing source-CIK range or 1–10 ASCII digits,
excluding booleans, and normalize to the requested ten-digit CIK. `facts` must
be an object. EPS, positive values and five-year coverage are not required.
HTML/access-denied content and wrong-issuer JSON fail even with status 200.

Configuration, lock, TLS, timeout, redirect, HTTP, size, media, structure and CIK
failures all precede the first archive publication. Tests assert that no archive
root, object or LIVE receipt exists after these failures. PR4C1's object-first
behavior is preserved: a later receipt-publication failure may leave a valid
unreferenced object; it grants no capture identity by itself.

## Time, receipt and acquisition result

Private `_utc_now()` reads the process clock. Request start, completed response
and post-preflight archive capture are separately observed and normalized to
explicit UTC `Z`. Backwards ordering or a naive clock value fails closed.
`captured_at` is the post-preflight process time supplied internally to archive
publication. It is never a filing date, HTTP Date, Last-Modified, fiscal period,
caller argument or metadata claim. Tests patch only the private clock.

The reviewed acquisition code, when executed normally, mints its timestamp after
the canonical SEC request. This is misuse resistance and auditability under
trusted local code, **not cryptographic remote attestation**, a hardware-backed
timestamp authority, or protection from an actor with arbitrary local code,
clock or filesystem control. Python private methods are a convention, not an
unforgeable security boundary.

Supported acquisition identities are explicitly allowlisted:

- Offline, unchanged: `2026-09-10-offline-supplied-companyfacts-v1`.
- LIVE: `2026-09-11-sec-live-companyfacts-v1`.

Receipt schema remains `2026-09-10-sec-capture-receipt-v1`. Public
`SecArchive.capture()` always uses the old identity and accepts no version/LIVE
override. The narrow private `_capture_live()` fixes the new identity and
canonical source locator. Both routes share the existing atomic no-clobber
publication. Old receipts retain their identities and deserialize unchanged;
unknown versions/keys and corrupt hashes remain rejected.

The frozen, slotted `SecAcquisitionResult` contains exactly:

`endpoint`, `cik`, `status`, `content_sha256`, `byte_length`,
`request_started_at`, `response_completed_at`, `captured_at`,
`archive_receipt_id`, `acquisition_contract_version`,
`declared_user_agent_used`, `safe_response_metadata`.

Metadata is an immutable tuple of string pairs, selected in fixed order from
Content-Type, Date, ETag and Last-Modified. Only printable ASCII values up to
1,024 characters are retained. These are transport/source claims, **not**
economic publication, filing dissemination or Expected Return availability
authority; no PR4B1 chronology is populated. No additional sidecar is persisted.
Result/receipt linkage is exact. Identical bytes acquired at different capture
times share an object hash while retaining distinct inspectable receipts.

The existing EPS inspector is deliberately unchanged. Its historical
`OFFLINE_CAPTURE_NOT_AUTHENTICATED` qualification blocker is not reinterpreted
or removed in this slice; consumers must inspect the receipt's explicit
acquisition identity. A LIVE receipt alone does not qualify any observation.

## Explicit manual CLI (not executed against SEC)

After privately configuring the required runtime User-Agent:

```sh
.venv/bin/python scripts/capture_sec_companyfacts.py \
  --cik TEN_DIGITS --archive-root /explicit/archive/root
```

Replace `TEN_DIGITS` with one exact ten-digit CIK only in a separately reviewed
post-merge acquisition. There is no default archive location, ticker, URL,
timestamp, contact command-line option, universe, batch, loop or scheduler.
Success output contains only `success`, `cik`, `content_sha256`, `receipt_id`,
and `captured_at`. Failure emits the safe reason/status on stderr and returns 1.
Argument errors return 2. This CLI does not compute Expected Return.

## Preserved identities and remaining blockers

`MODEL_RULES_VERSION` remains `2026-08-23-allocation-room-integrity-v7`.
PR4A, PR4B1, PR4B2 and V2 decision identities are unchanged. No real-source
PR4B1 AdapterIdentity or real root admission exists.

Expected PIT aggregate:
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
Expected PIT determinism:
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.
Expected values are never regenerated to accommodate this change.

Deferred prerequisites remain:

- Actual first reviewed real acquisition.
- Publication/availability semantics beyond capture.
- Exact security/listing/share-class identity.
- ADR/local listing relationships.
- Split/corporate-action basis.
- Comparable five-year EPS-series resolution.
- Dividend/nonpayer evidence.
- Qualified market price.
- Objective business-profile qualification.
- Real-source PR4B1 admission.
- Real PIT collector.
- VFV forward Expected Return.
- Global jurisdictions.
- Worldwide discovery.
- Allocation authority.

No portfolio/private data, Drive, Chromebook, deployment, operational scheduler,
real Expected Return, Baseline evidence, tuning, backtest, walk-forward or
investment decision change is part of PR4C2.

## Validation

Python 3.12 and the unchanged `requirements.lock` are required. The existing
isolated runner copies code only, strips credentials, uses temporary home/state,
and denies socket connections. All 33 installed dependency versions were
verified against the lock; no dependency or runner change is needed.

```sh
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_sec_*.py'
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_expected_return*.py'
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_pit*.py'
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_runtime_isolation.py'
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_validation_identity_isolation.py'
.venv/bin/python scripts/run_isolated_tests.py --pattern 'test_pr2_investment_equivalence.py'
.venv/bin/python scripts/run_isolated_tests.py
git diff --check
git diff --cached --check
git show --format= --check HEAD
```

Tests cover configuration, authority boundaries, TLS/proxy/redirect behavior,
HTTP failures, bounded reads, structure, internal chronology, receipt versions,
exact bytes, idempotence, corruption, publication failures, fake-clock spacing,
real cross-process lock exclusion and static model isolation. Existing PR4C1
archive/extraction regressions remain intact; its static offline import check
is scoped to the unchanged offline modules, while PR4C2 checks the live module
separately. Completed counts and fingerprints are recorded after validation.

### Completed focused validation

Interpreter: **Python 3.12.14**. All **33** installed dependency versions match
the unchanged lock. The existing CI Python pin remains **3.12.13**.

| Runner pattern | Passed | Test duration |
| --- | ---: | ---: |
| `test_sec_*.py` | 99 (28 archive, 28 EPS, 43 acquisition) | 2.302 s |
| `test_expected_return*.py` | 144 | 0.842 s |
| `test_pit*.py` | 40 | 375.003 s |
| `test_runtime_isolation.py` | 29 | 36.886 s |
| `test_validation_identity_isolation.py` | 19 | 0.441 s |
| `test_pr2_investment_equivalence.py` | 1 | 0.142 s |

Both exact PIT fingerprints above were reproduced. The 64-case / 256-worker
equivalence matrix passed without changing expected values. An initial test-only
fixture error (NUL cannot be assigned to a real OS environment variable) was
corrected by testing the validator with a plain environment mapping; the complete
SEC-focused rerun passed. No production transport was invoked.

### Completed full validation

The complete isolated suite passed **1,241 tests in 428.094 seconds**, with exit
status 0 on Python **3.12.14**. It reproduced both exact PIT fingerprints above.
Only validation documentation was updated after the run; tested executable code
did not change. Working-tree and staged whitespace checks passed. The required
commit whitespace check is performed again on the implementation commit before
push. These results are synthetic mechanical evidence only, not Baseline, real
PIT, tuning, strategy validation or investment-decision evidence.
