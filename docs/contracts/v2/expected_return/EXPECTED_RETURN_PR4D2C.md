# PR4D2C — Controlled Nasdaq Listed directory capture and replay

> A captured Nasdaq Listed snapshot is evidence of what Nasdaq's directory recorded in that captured/generated snapshot. It is not historical listing continuity, global listing completeness, or economic identity qualification.

## Verified base and scope

After `git fetch origin`, the approved V2 integration branch
`origin/model-v2/expected-return-challenger` was exactly
`af299692f5cea0f7fdfc4e2dbac967f8618cc108`, tree
`36e124a484c8383604fb835493e0a67cd2197b33` (post-PR #46).
Frozen `origin/main` remained `c5fc27c82c29c2a6027eccee245098c4a072fdf1`.
The initial checkout/index was clean on `codex/v2-roadmap-etf-lookthrough`.
`codex/v2-nasdaq-listed-capture` starts directly from the verified integration
commit. Existing local refs, including stale/divergent integration and main refs,
were preserved without resets, rebases or force updates.

Exactly eight files are added:

- `economic_facts/nasdaq_listed_archive.py`
- `economic_facts/nasdaq_listed_acquisition.py`
- `economic_facts/nasdaq_listed_snapshot.py`
- `tests/nasdaq_listed_fixtures.py`
- `tests/test_nasdaq_listed_archive.py`
- `tests/test_nasdaq_listed_acquisition.py`
- `tests/test_nasdaq_listed_snapshot.py`
- `EXPECTED_RETURN_PR4D2C.md`

No existing file is modified. In particular D1/D2A/D2B, C3/C4–C6, Expected
Return, PIT, V1, runtime, dependencies, model rules, authority registries and
`PAM_ROADMAP.md` remain unchanged. There is no shared provider framework,
SEC-helper dependency, CLI, scheduler, model integration or admission join.

## Source investigation and use basis

Reviewed on 2026-09-21:

- [Nasdaq directory definitions](https://www.nasdaqtrader.com/Trader.aspx?id=SymbolDirDefs)
- [Official Nasdaq Listed resource](https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt)
- [Nasdaq Symbol Lookup notice](https://www.nasdaqtrader.com/Trader.aspx?id=symbollookup)

The definitions describe periodic directory updates, source codes and a final
generation-time record. Their prose describes compact `mmddyyyyhhmm`, while
their example and the inspected resource use `mmddyyyyhh:mm`. This contract
supports the latter exact colon-separated, minute-precision form only. No
timezone is stated in the reviewed Nasdaq Listed definition; none is supplied
by PAM. A future format change requires deliberate review.

A separate, bounded HTTPS format inspection returned `text/plain`, 349,031
bytes, ASCII-only text, 5,625 CRLF-terminated lines (5,623 ordinary rows), the
eight-column header below, and a longest field of 245 characters. The observed
footer was `File Creation Time: 0921202614:01|||||||`. These are inspection
observations, not promised future sizes, a stored LIVE receipt or qualification
evidence. No real directory payload is committed. All tests use fictional rows
and patched transport with network disabled by the isolated runner.

The Symbol Lookup notice expressly includes Nasdaq Listed in Nasdaq Events Data
and permits use of the data as held in Nasdaq's records without further licensing
requirements. That route-specific notice is the current use basis. It grants no
factual authority. This contract does not extend it to Other Listed, Nasdaq Fund
Network, Daily List, CUSIP or every Nasdaq dataset; D1 use-status semantics remain
unchanged. Daily List integration or purchase is a separate sourcing/budget
decision, not a way to infer history from this free snapshot.

## APIs and dependency direction

```python
acquire_nasdaq_listed(*, archive_root: str | Path) -> NasdaqListedAcquisitionResult

replay_nasdaq_listed_snapshot(
    archive: NasdaqListedArchive,
    request: NasdaqListedSnapshotRequest,
) -> NasdaqListedSnapshotAssessment
```

The frozen request contains exactly one `receipt_id`, with no default. Acquisition
accepts only an archive root. Neither API accepts URL/host/path overrides, bytes,
clocks, capture/source times, policies, completeness, authority, `as_of`, CIK,
ticker mapping, issuer/security/class identities, intervals or coverage bounds.
The acquisition result contains a verified published receipt and controlled
`request_started_at` / `response_completed_at` execution metadata.

`NasdaqListedArchive` exposes only `read_receipt` and `read_object` as public
methods. Its private `_capture_live` is an implementation capability for reviewed
acquisition and fictional tests, not a public raw-byte LIVE API.

```text
acquisition -> snapshot parser -> dedicated archive types/encoding
            -> dedicated archive publication
offline replay -> dedicated archive reads + same snapshot parser
```

The three modules otherwise import only the standard library. No existing
production module imports them. Dependency tests cover root entry points,
`src`, scripts, PIT and economic-fact modules. Negative tests reject Nasdaq
objects at SEC Companyfacts, D1 and C4 synthetic qualification boundaries.

## Fixed transport and provider gate

The single route is HTTPS GET to
`https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt`.
It has no query, caller selector, arbitrary path, mirror, FTP fallback, redirect
following or retry. One invocation makes at most one request. The request uses
fixed `User-Agent: PAM-NasdaqListedCapture/1.0`, `Accept: text/plain` and
`Accept-Encoding: identity`; there is no SEC administrative contact requirement.

Default verified TLS checks certificates and hostnames. Environment proxies and
the global urllib opener are bypassed. The socket timeout is 15 seconds; a
60-second monotonic response deadline is checked before and after each bounded
`read1`, including opening/receiving time. A receive already in progress remains
subject to the socket timeout; no response completed after the deadline can be
accepted. Reads are at most 64 KiB, bounded by remaining body capacity plus one
byte for overflow detection. No transparent content decompression occurs.

Only `text/plain`, optionally with UTF-8 or US-ASCII charset (case-insensitive,
optionally quoted), is accepted. A declared US-ASCII body must actually be ASCII;
all bodies must also pass strict UTF-8 structural preflight. Absent/identity
Content-Encoding only. Content-Type, Content-Encoding, Content-Length and
Transfer-Encoding reject duplicate headers. Length must be bounded ASCII decimal
and match received bytes. Transfer-Encoding is absent or a single `chunked`
value without Content-Length; chunk framing is decoded by the HTTP library.
HTTP Date, Last-Modified and ETag are not chronology or authority inputs.

The independent per-user gate is
`~/.investment_automation/nasdaq_trader_acquisition/gate.lock`.
It is unrelated to the SEC gate and independent of archive root and XDG settings.
The application/provider directories are walked without symlink following and
checked for local-user ownership and absence of group/other write permissions;
the lock also requires a regular single-link file. Contention fails immediately.
Each holder waits a full second before requesting, including after idle time or
process restart; there is no burst credit, retry loop or wall-clock rate state.
The lock is retained through receive, preflight and archive publication and
released on failure. The stable lock inode must not be removed during use.
This one-request-per-second ceiling is a conservative PAM limit, not a claimed
Nasdaq fair-access policy or guaranteed allowance.

## Receipt and immutable storage

Frozen, slotted `NasdaqListedReceipt` has exactly these fields:

| Field | Contract |
| --- | --- |
| `schema_version` | `2026-09-21-nasdaq-listed-receipt-v1` |
| `source_kind` | `NASDAQ_TRADER` |
| `resource_kind` | `NASDAQ_LISTED_DIRECTORY` |
| `endpoint` | The exact fixed HTTPS route |
| `content_sha256` | SHA-256 of the exact received body bytes |
| `byte_length` | Integer 1 through 16 MiB, excluding bool |
| `captured_at` | Controlled, explicit-offset, canonically UTC PAM time |
| `acquisition_contract_version` | `2026-09-21-nasdaq-listed-acquisition-v1` |

Serialized receipts add only `receipt_id`. Identity is SHA-256 of
`pam:nasdaq-listed-receipt:v1\0` plus sorted, compact ASCII JSON of the fields.
Unknown versions/keys, duplicate JSON keys, nonfinite constants and inconsistent
identities fail closed. Source creation metadata is deliberately parsed from the
source bytes in replay, never independently authored into receipts.

Objects use exact SHA-256 names. Receipts bind a particular controlled capture;
identical bytes recaptured at a different time share one object but have separate
receipts. Changed bytes preserve both objects. Publication cannot overwrite
existing evidence. Equivalent JSON receipt serialization is verified without
rewriting it.

Descriptor-relative traversal rejects symlinks in the root, ancestors and archive
subdirectories. Parent traversal components are rejected. Files must be regular
and single-link; FIFOs, directories and extra hardlinks fail. Reads are bounded
and verify stored receipt membership, receipt identity, object length and hash.
Read paths create nothing. Temporary publication files use exclusive creation,
flush/fsync and read-only permissions before atomic no-clobber linking; the
temporary link is removed and the containing directory fsynced. Newly created
directory entries are also fsynced. Temporary-name attempts are bounded at 1,000.

Publication failure never reports success. A later-stage failure can leave an
unreferenced object or an already-linked file; later publication verifies existing
content rather than overwriting it. Cleanup failures also surface as errors.

This is the existing trusted-local-code/storage model, not a Nasdaq signature,
secure timestamp service or protection against a privileged actor replacing the
entire archive and code. Detached/self-authored receipts fail membership checks.
Uploaded archives do not gain trust merely by reproducing these hashes. Frozen
reports and success labels are inspectable outputs, not authority credentials.

## Structural contract and source fields

The current header observed was:

```text
Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
```

Exactly one header is required, containing at least the first six named fields.
Column names are unique ASCII identifiers beginning with a letter, followed by
letters/digits/spaces/underscore/hyphen, at most 64 characters and without outer
whitespace. Columns can appear in a different order. Each data row must have
exactly the header's field count. All accepted values, names, symbols, ordering,
extra columns and whitespace are retained without normalization.

- `Symbol`: bounded structural token `[A-Za-z0-9][A-Za-z0-9.$^_/-]{0,31}`.
  This permits extended suffix/test shapes and makes no common-stock-only or
  economic-identity claim. The size is a PAM safety bound.
- `Security Name`: nonempty after checking whitespace, retained verbatim. No
  instrument or issuer inference from text.
- `Market Category`: reviewed `Q`, `G`, `S` codes only.
- `Test Issue`: reviewed `Y` or `N`; test issues are retained as source rows.
- `Financial Status`: reviewed `D`, `E`, `Q`, `N`, `G`, `H`, `J`, `K` only.
- `Round Lot Size`: positive ASCII integer text, one to nine digits; exact text
  (including any leading zeroes) retained. The digit bound is PAM's, not an
  assertion about all Nasdaq products.

Code validation checks reviewed source vocabulary only; there is no investment
recommendation or class qualification. Unknown core codes fail closed. Additional
compatible columns, including `ETF` and `NextShares`, remain uninterpreted
strings; the reviewed Nasdaq Listed definition did not justify making those
extra fields mandatory or importing Other Listed semantics. Empty extra values
are preserved. Unsupported economic instrument types are not parser failures:
common stock, share classes, ADR/ADS, warrants, units, rights, ETFs, preferred
structures and test rows all remain visible when structurally valid.

Uniform LF or CRLF is supported with optional final newline/empty terminal lines.
Mixed endings, bare CR, internal empty records, invalid UTF-8, BOM, Unicode control/
format/surrogate characters and Unicode line/paragraph separators are unsupported.
Names may otherwise contain safe UTF-8, including combining marks, without lossy
replacement or Unicode normalization.

Exactly one final nonempty footer is required: `File Creation Time: mmddyyyyhh:mm`
followed by enough empty pipe fields to match the header width. Dates and clock
components are validated. Missing, multiple, malformed or nonfinal footers, data
after the footer, extra footer values and unexplained records fail closed.
Header plus footer with zero rows is structurally valid and reports zero rows;
it does not assert that Nasdaq has no listed securities.

| PAM safety bound | Value |
| --- | ---: |
| Body / receipt bytes | 16 MiB / 4 KiB |
| Data rows | 100,000 |
| Columns | 64 |
| Field length | 4,096 Unicode code points |
| Data cells | 1,000,000 |

Bounds are checked before building occurrence records; exceeding a bound is an
unsupported source variant, never silently truncated data or a completeness claim.

## Replay, chronology and conflict semantics

Replay requires one explicit typed archive/request and verifies the selected
receipt and object. It performs no network operation, directory scan, latest
selection, write, implicit clock read or automatic recapture. The assessment
retains the receipt, header, exact footer, minute-precision source creation text
and components, all rows, row count, conflicts and structural contract
`2026-09-21-nasdaq-listed-snapshot-v1`.

Each row binds receipt ID, exact endpoint, zero-based data position, one-based
source line and all header/value pairs. Duplicate symbols retain every occurrence,
including byte-identical repetitions, and return `SOURCE_CONFLICT` with a sorted
symbol inventory. There is no first/latest winner, vote or silent deduplication.
Otherwise the status is `CAPTURED_NASDAQ_LISTED_SNAPSHOT`.

Separate SHA-256 domains encode rows, occurrences, snapshot semantics and evidence
under `pam:nasdaq-listed:{domain}:v1\0`. Semantics include contract, status,
ordered header/rows, exact field values, footer/creation metadata and conflicts.
Reordering source rows changes this ordered snapshot identity. LF versus CRLF or
terminal newline changes affect only evidence. Evidence additionally binds the
receipt and occurrence provenance. Identical-source recapture changes evidence
identity, not semantics; paths and ambient environment never enter either hash.

Controlled local chronology must be nondecreasing:
`request_started_at <= response_completed_at <= receipt.captured_at`.
Capture is sampled after response completion and successful structural preflight,
before publication. Source generation time remains a separate text/component
record with **no timezone or invented seconds**. It is not converted to UTC,
compared to local capture or D1 `T`, or promoted to publication, observed
availability, completeness watermark, event-free interval or validity-through-T.

Invalid caller selections raise `SnapshotRequestError`; unsafe/missing/corrupt
stored evidence raises `NasdaqListedArchiveError`; unsupported source structures
raise `UnsupportedNasdaqListedStructure`. Acquisition translates failures to
closed `NasdaqListedAcquisitionReason` categories plus optional numeric HTTP
status, suppressing underlying bodies, messages and paths. Programming defects
propagate rather than becoming normal unavailability or successful partial replay.

## Explicit nonclaims and next handoff

Property 4 remains unresolved in every part: 4A issuer, 4B security, 4C share
class, 4D complete common-class inventory, 4E EPS applicability, 4F source-neutral
security/listing binding, 4G listing inventory and 4H continuity. No CIK mapping,
name/ticker reconciliation, SEC filing join, quote-currency/major-unit inference,
economic admission, historical authority, C3 blocker removal or C4 success object
is produced. Nasdaq-listed does not become USD-quoted under this contract.

A capture/generation time cannot prove the absence of an intervening event,
uninterrupted validity, economic-event completeness or coverage through an
arbitrary later D1 boundary. No real qualifier or authority-registry route is
added. Obligations 5–7 remain unresolved as well. `otherlisted.txt`, other
exchanges, Daily List and historical corporate-action ingestion are excluded.

The next chantier needs a separately reviewed real-evidence qualification and
temporal-coverage contract. Future comparisons with D2A cover disclosures and
D2B filing inventory must retain their distinct scopes and clocks; this PR builds
only the Nasdaq evidence input. Merge remains the owner's decision. No merge,
deployment, positive-capital analysis, Chromebook action or V2 promotion occurs.

## Validation record

Environment: unchanged existing `.venv`, Python **3.12.14** versus repository pin
**3.12.13**. All **33** locked distributions match unchanged `requirements.lock`;
no missing packages or version drift. No dependencies/runtime settings changed.
Tests use `scripts/run_isolated_tests.py`, disposable code/state and HOME,
stripped credentials and denied network.

All **89 new tests** pass (28 archive, 36 acquisition, 25 snapshot/dependency).
They cover canonical exact-byte receipts and recaptures, unsafe files/links,
publication/fsync failures, bounded reads, fixed transport, TLS/proxies/redirects,
size/MIME/encoding/framing/deadlines, provider-specific cross-process contention,
gate retention, source structure/limits, field preservation, duplicate conflicts,
source-time precision, deterministic identities and authority isolation.

Completed focused selections:

| Selection | Tests | Result |
| --- | ---: | --- |
| `test_nasdaq_listed_*.py` | 89 | PASS |
| `test_sec_submissions_*.py` | 101 | PASS |
| `test_sec_filing_*.py` | 74 | PASS |
| `test_sec_acquisition.py` | 43 | PASS |
| `test_sec_fact_archive.py` | 28 | PASS |
| `test_sec_diluted_eps.py` | 28 | PASS |
| `test_sec_eps_series.py` | 52 | PASS |
| `test_sec_current_evidence.py` | 41 | PASS |
| `test_source_authority.py` | 11 | PASS |
| `test_current_authority.py` | 17 | PASS |
| `test_security_identity.py` | 84 | PASS |
| `test_share_basis.py` | 136 | PASS |
| `test_reporting_subject.py` | 77 | PASS |
| `test_expected_return*.py` | 144 | PASS |
| `test_runtime_isolation.py` | 29 | PASS |
| `test_validation_identity_isolation.py` | 19 | PASS |
| `test_pr2_investment_equivalence.py` | 1 | PASS |
| `test_pit*.py` | 40 | PASS |

The focused selections total **1,014 passing tests**. The dedicated PIT selection
passed **40 tests in 1,028.031 seconds**. The complete isolated suite passed
**1,923 tests in 1,160.464 seconds**, without failures or skips. Both runs
reproduced all 64 protected equivalence scenarios and the protected determinism
identity. All seven new Python files are byte-identical to the full-suite code
snapshot; only this validation record was finalized afterward.

Verified unchanged protected identities:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

Whitespace checks pass for the working/index diffs; post-commit validation uses
`git show --format= --check HEAD`. A fresh fetch before publication confirmed the
same approved integration SHA/tree and frozen V1 SHA. Scope verification confirms
exactly the eight additions above and no pre-existing file changes. Commit/push/PR
creation is authorized; merge is not. The final commit SHA and PR URL are reported
with the published handoff.
