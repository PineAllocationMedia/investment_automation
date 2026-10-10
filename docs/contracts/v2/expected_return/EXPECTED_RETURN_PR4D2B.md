# PR4D2B — Controlled SEC Submissions capture and referenced-history replay

## Status and exact base

Implementation for review; not a merge, deployment, authority promotion or real
issuer qualification. Branch: `codex/v2-sec-submissions-capture`.

After fetching origin, the verified integration base is
`model-v2/expected-return-challenger` at
`23651b9738996257ffa57ac49249470904b51dc9` (merged PR #44 / PR4D2A), tree
`9a3e8994ecfeca2b3af752ac2ec080b1993d3151`. The clean worktree began on the prior
D2A branch at `5d0f4b865d7a62ec508d11c3309f45129fe3125c`, with that same tree.
The implementation branch was created directly from the verified remote integration
ref. Existing divergent local refs were preserved.

Frozen remote V1 `main` is `c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`. No V1, runtime, Chromebook,
production configuration, investment rules or dependencies are changed.

## Scope and exact files

Added:

- `economic_facts/sec_submissions_archive.py`
- `economic_facts/sec_submissions_acquisition.py`
- `economic_facts/sec_submissions_inventory.py`
- `tests/sec_submissions_fixtures.py`
- `tests/test_sec_submissions_archive.py`
- `tests/test_sec_submissions_acquisition.py`
- `tests/test_sec_submissions_inventory.py`
- `EXPECTED_RETURN_PR4D2B.md`

Modified:

- `tests/test_sec_acquisition.py`: permit only the new acquisition module's
  intentional dependency on the existing shared SEC helpers.
- `PAM_ROADMAP.md`: correct B — stale state reporting to verified post-D2A,
  pre-D2B status, record the current inventory prerequisite and unresolved
  qualifications. No D2B merge or future merge SHA is claimed.

Out of scope: Companyfacts/D2A production changes, C3/C4–C6, D1, registry changes,
Expected Return, PIT, runtime, dependencies, CLI, orchestration, filing downloads,
identity/property-4 verification, economic admission and investment-rule changes.
The constitution is untouched.

## APIs and dependency direction

```python
acquire_sec_submissions(*, cik: str, archive_root: str | Path)
    -> SecSubmissionsAcquisitionResult

acquire_sec_submissions_history(*, archive_root: str | Path,
                               parent_receipt_id: str, history_filename: str)
    -> SecSubmissionsAcquisitionResult

replay_sec_submissions_inventory(archive: SecSubmissionsArchive,
                                request: SecSubmissionsInventoryRequest)
    -> SecSubmissionsInventoryAssessment
```

The frozen request has only `parent_receipt_id` and a tuple of explicit
`child_receipt_ids`. It has no latest selection, as-of boundary or caller authority.
Acquisition exposes no bytes, URL, timestamp, clock, transport, retry/rate policy,
User-Agent override, publication/availability value or completeness flag.
`SecSubmissionsArchive` has only `read_receipt` and `read_object` as public methods.
The private `_capture_live` is reserved for reviewed acquisition and fictional
mechanical tests; it is not an independent source of factual authority.

Acquisition depends on unchanged `sec_acquisition` transport helpers and the new
dedicated archive. Replay depends only on that archive and the standard library.
The bounded private source parser lives in the archive module so capture and
replay apply one contract. There are no reverse consumers in model, runtime, PIT,
C3, C4–C6, D1 or Expected Return.

## Resource selectors and controlled transport

Root: `https://data.sec.gov/submissions/CIK##########.json`, with exactly ten ASCII
CIK digits including leading zeros. CIK is only a source selector.

History: `https://data.sec.gov/submissions/{history_filename}`. Before any request,
acquisition reads the exact stored ROOT receipt and hash-verified bytes, parses
`filings.files` and checks membership. The accepted basename is
`CIK{same ten-digit CIK}-submissions-{one or more ASCII digits}.json`, at most 128
characters. The digits have no fixed pagination width. Absolute URLs, paths,
slashes, backslashes, dots outside the closed suffix, escaping, whitespace,
controls, Unicode digits, query strings and fragments do not match. No resource
name is accepted independently of that exact parent.

One request uses the shared C2 per-user, cross-process rate gate, held through
publication. Companyfacts, D2A and D2B share the same lock/budget. Existing C2
behavior supplies declared administrative User-Agent validation, 0.25-second
spacing, verified TLS, disabled environment proxies, redirect rejection, 15-second
socket timeout, 60-second response deadline and no retry. Relevant HTTP framing
headers use duplicate-safe parsing. Only `application/json` with optional UTF-8
charset is accepted; absent/identity encoding only. Streaming reads are at most
64 KiB and the exact body is capped at 32 MiB. No unbounded read or decompression.
Administrative contact and source/path details are absent from translated errors.

HTTP Date/Last-Modified/ETag metadata is not interpreted or used for chronology.
Acquisition returns separate controlled request-start, response-completion and
receipt capture times. Clock regression and capture before the selected parent's
capture fail closed. Source dates are retained separately and verbatim.

## Dedicated receipt and archive contract

Frozen, slotted `SubmissionsReceipt` has exactly these fields:

| Field | Contract |
| --- | --- |
| `schema_version` | `2026-09-21-sec-submissions-receipt-v1` |
| `source_kind` | `SEC_SUBMISSIONS_JSON` |
| `cik` | Canonical ten ASCII digits |
| `resource_kind` | `ROOT` or `HISTORY` |
| `history_filename` | Null for ROOT; validated referenced filename for HISTORY |
| `parent_receipt_id` | Null for ROOT; exact ROOT receipt ID for HISTORY |
| `endpoint` | Internally derived canonical endpoint |
| `content_sha256` | SHA-256 of exact source bytes |
| `byte_length` | Integer 1 through 32 MiB; booleans rejected |
| `captured_at` | Internally obtained explicit-offset UTC-canonical timestamp |
| `acquisition_contract_version` | `2026-09-21-sec-live-submissions-v1` |

Serialized receipts add only `receipt_id`, verified on read. Identity is SHA-256
of `pam:sec-submissions-receipt:v1\0` plus canonical sorted ASCII JSON of the
fields. Unknown keys/versions, duplicate keys, nonfinite JSON and mismatched
selectors/IDs fail closed. Receipts contain no completeness or identity claims.

Objects deduplicate by exact bytes; receipts bind the exact capture and parent.
The same history bytes associated with two parent captures produce different
receipts. Changed recaptures preserve both originals. A HISTORY parent must be a
stored ROOT with the same CIK and an actual matching reference, and must not be
captured later than the child. Chaining HISTORY receipts as parents is rejected.

The archive uses descriptor-relative traversal with no symlink following,
regular-file/single-link checks, bounded reads, exact receipt membership, length
and hash verification. Publication writes a private temporary file, flushes/fsyncs,
sets read-only permissions, links atomically with no clobber, removes the temporary
link and fsyncs the directory. Failures do not report success. Publication can leave
an unreferenced object if receipt publication fails; retry verifies rather than
overwrites it. Existing semantically identical receipt serialization is accepted
without rewriting it. Read paths create no files/directories. Symlinks, extra
hardlinks, FIFOs and directory-as-file entries are rejected.

This is a local integrity model, not protection from an actor controlling all
archive bytes, application code and trust anchors. A self-consistent caller receipt
without stored membership is rejected; hashes are not authority credentials.

## Source structure and mechanical limits

The parser requires UTF-8 JSON objects, rejects duplicate keys/nonfinite values,
and scans nesting before decoding. Root source CIK accepts an integer or 1–10
ASCII digits matching the selector. `filings` must have exactly `recent` and
`files`. HISTORY is the columnar filing object directly, without entity metadata.

Required core filing columns:
`accessionNumber`, `filingDate`, `reportDate`, `acceptanceDateTime`, `form`,
`primaryDocument`. Every column is an array with the same row count. Accessions
have canonical `##########-##-######` structure; their prefix need not equal the
registrant CIK. Filing dates are valid ISO dates; report dates may also be empty.
Acceptance strings must be valid UTC `YYYY-MM-DDTHH:MM:SS[.fraction]Z` with 1–6
fractional digits when present. Form is a nonempty string of at most 128
characters. Primary document is a retained string, never an endpoint to follow.

Every compatible extra column is retained in sorted field tuples for each row.
Accepted scalars are strings, nulls, booleans and signed 64-bit integers. Floats,
arrays/objects inside cells, invalid keys and incompatible structures are
unsupported. Existing noncore scalar columns are uninterpreted source metadata.
No form allowlist or EPS-only filter exists: amendments, registrations,
deregistrations, proxies, ownership filings and unfamiliar forms remain visible.
No rows are silently truncated or deduplicated.

Root entity metadata is retained as canonical JSON. Unknown scalar metadata is
accepted. Reviewed nested shapes are string arrays `tickers`/`exchanges`, an
`addresses` object with mailing/business string-or-null fields, and `formerNames`
entries containing exactly string `name`, `from`, `to`. The optional exact field
`addresses.{mailing,business}.isForeignLocation` additionally accepts an exact JSON
integer (`type(value) is int`) satisfying `abs(value) <= 2**63 - 1`; booleans and
floats remain rejected. No `{0,1}` enumeration is imposed. Accepted integers remain
opaque source metadata, preserved without coercion or interpretation. All other
address-field type rules remain unchanged. Other nested extensions
require future review; retained names/tickers/exchanges convey no identity proof.

Each history reference retains its parent receipt ID, original position and all
accepted fields. `name` is mandatory and unique within the parent. Optional
`filingCount` is a nonnegative signed-64-bit integer. Optional `filingFrom` and
`filingTo` are valid dates in nonreversed order. Compatible additional scalar
reference fields are retained. Missing assertions are not invented.

| PAM safety limit | Value |
| --- | ---: |
| Exact body / receipt | 32 MiB / 4 KiB |
| JSON nesting | 8 containers |
| Filing rows per resource | 100,000 |
| Filing cells per resource | 500,000 |
| Columns / general object keys | 64 |
| Column/key identifier | ASCII letter, then letters/digits/underscore; ≤64 characters |
| Scalar string | 16,384 Unicode code points; lone surrogates rejected |
| Metadata list items | 1,000 |
| Parent history references / explicit children | 1,000 |
| History filename / form string | 128 characters each |
| Aggregate replay bytes / rows / cells | 128 MiB / 200,000 / 1,000,000 |

These are PAM implementation limits, not SEC source guarantees. Excess structures
are unsupported rather than truncated. Raw-body bounds apply before decoding;
row/cell limits apply before constructing occurrence records. Replay verifies its
one parent once rather than decoding it for every child; private member-object
reads still verify each child's receipt, byte length and content hash after replay
has checked the exact parent, reference and chronology relationship.

## Reviewed source assertions

The official [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes current metadata, recent columnar filings, additional history files with
date ranges, and dissemination-driven updates. It does not provide a completeness
watermark, atomic snapshot guarantee, fixed pagination width or a formal
`filingCount` reconciliation definition.

Replay checks each child's filing dates for containment in any declared parent
range, because the documented range describes filings contained in that file.
It does not require exact minimum/maximum equality. Out-of-range rows remain
visible and produce `INVENTORY_CONFLICT`. An empty child does not manufacture a
range observation. Declared `filingCount` stays visibly in reference fields;
`observed_history_row_counts` reports actual replayed row counts separately.
No equality rule is invented for the undocumented count semantics.

## Replay and identity semantics

A replay returns the verified parent and explicitly supplied children (including
all capture times), retained root metadata, all references, every filing
occurrence, missing filenames, conflicting accessions, range conflicts and
observed history row counts. Each occurrence has its receipt ID, source endpoint,
section (`filings.recent` or `history`), original row position and exact decoded
scalar fields. Identical duplicate rows keep distinct occurrence provenance.

Statuses:

- `CAPTURED_REFERENCE_CLOSURE_COMPLETE`: every history resource referenced by this
  exact captured parent has one supplied, verified, successfully replayed and
  reconciled child under this contract. Zero references can close an empty set.
- `CAPTURED_REFERENCE_CLOSURE_INCOMPLETE`: valid selections omit one or more parent
  references. This is ordinary incomplete evidence, not corruption.
- `INVENTORY_CONFLICT`: any same-accession row fields differ, or a child's filing
  date falls outside a declared range. All occurrences are retained. Missing
  filenames remain visible even when conflict takes status precedence.

Conflict comparison is deliberately conservative over all retained scalar fields,
including unfamiliar columns; there is no majority vote, latest win or normalized
EPS logic. Duplicate child receipts or multiple captures for one filename are
ambiguous requests and rejected. Old parents never select newer parents' children.
There is no directory scan, network, write, implicit clock or latest selection.

Separate domain hashes cover filing-row semantics, occurrence provenance,
assessment semantics and assessment evidence, using
`pam:sec-submissions:{domain}:v1\0`; assessment contract version is
`2026-09-21-sec-submissions-inventory-v1`. Semantic identity includes the sorted
multiset of row semantic IDs (duplicate multiplicity retained), sorted reference
fields, metadata, conflicts, missing files and observed counts. Row/reference
order permutations do not change semantics. Evidence identity additionally binds
exact receipts and original occurrence/reference positions. Request child order
does not change either identity. Paths, environment, randomness and implicit time
never enter these identities. Explicit capture times enter through receipts.

## Error model

- Acquisition: `SecSubmissionsAcquisitionError` with closed reason and optional
  numeric HTTP status. Shared transport reasons are translated without private
  content. Additional reasons: `INVALID_REQUEST`, `UNSUPPORTED_STRUCTURE`,
  `ARCHIVE_INTEGRITY_ERROR`. Invalid root configuration/selectors use
  `CONFIGURATION_ERROR`. Parent membership/selector checks precede networking.
- Replay invalid caller selection: `InventoryRequestError` (malformed IDs, foreign
  or unreferenced child, nonroot parent, duplicates/ambiguity, wrong typed request).
- Stored evidence integrity: `SubmissionsArchiveError` (missing explicitly selected
  receipt/object, corruption, bad relationship chronology, unsafe paths/links).
- Unsupported source shape/resource limits: `UnsupportedSubmissionsStructure`.
- Normal omitted child: incomplete assessment, not an exception.
- Source contradictions: conflict assessment retaining evidence.
- Unexpected programming exceptions propagate; no broad catch disguises them as
  ordinary missing data.

## Non-atomicity and authority boundary

Parent and children are separate requests. Children may be captured later, may
change between captures, and cannot backdate themselves to parent capture. Each
receipt/time survives replay; there is no manufactured common snapshot timestamp.
Source filing dates, report dates, acceptance strings and declared history bounds
remain distinct from request/completion/capture times. None becomes `published_at`,
`available_at`, a historical cutoff, event-free interval or coverage watermark.

> Reference closure is not filing-history completeness, economic-event completeness, or coverage through the D1 CURRENT boundary.

An event can occur before SEC disclosure. Fetching every parent reference, observing
no later filings, or capturing near D1's boundary cannot establish coverage through
that boundary. This PR does not compare inventory coverage to D1 `T`.

**Property 4 remains wholly unresolved:** no 4A issuer, 4B security, 4C class, 4D
common-class inventory, 4E EPS applicability, 4F listing, 4G listing inventory or
4H continuity is established, even partially. Obligations 5–7 also remain
unresolved. There is no D1 authority upgrade, provider-wide SEC trust, historical
as-of authority, C3 blocker discharge, C4 synthetic object construction, economic
admission, ER adaptation or V2 promotion. The rail supplies reproducible filing
inventory evidence only; D2A remains the separate complete-filing capture route.

## Licensing and use posture

This route accesses public SEC data subject to applicable SEC fair-access and
programmatic-use requirements. See [Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
and [SEC Privacy and Security Policy](https://www.sec.gov/about/privacy-information).
These source policies are not a new legal opinion or factual authority grant.
D1 use-status semantics and authority registries are unchanged. Validation uses
fictional JSON and patched transport; no live SEC data acquisition is performed.
Official SEC documentation was consulted separately for the source contract.

## Validation and handoff

The 101 new tests pass: 32 archive, 41 acquisition and 28 inventory/dependency
tests. They cover exact-byte/provenance replay, recaptures, filesystem attacks,
publication/fsync failure, detached/corrupt evidence, bounded source shapes,
transport/headers/deadlines, shared cross-process contention, all-form retention,
parent-linked children, conflicting duplicates, deterministic identities and
offline/no-write/no-latest/authority isolation.

Completed focused selections:

| Selection | Tests | Result |
| --- | ---: | --- |
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

All **925** tests across the focused selections pass. The dedicated 40-test PIT
selection passed in **963.122 seconds**. The full isolated suite passed **1834
tests in 1079.103 seconds**, with no failures or skips reported. Both runs reproduced
the protected PIT and determinism fingerprints below. All eight added/modified
Python files remain byte-identical to the successful full-suite code snapshot;
only documentation was completed afterward.

Validation also includes `git diff --check`, `git diff --cached --check` and
post-commit `git show --format= --check HEAD`. A fresh fetch before publication
confirmed the same integration SHA/tree and frozen V1 SHA/tree. The final scope
contains exactly the ten files listed above. No existing production source changed.

Environment: existing `.venv` Python **3.12.14**, while `.python-version` remains
**3.12.13**. All **33** locked distributions match `requirements.lock` exactly;
no missing packages or version drift. No environment/dependency changes made.

Verified unchanged protected identities:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

Next recommended chantier: a separately reviewed evidence/temporal-coverage and
real-qualification contract, including independent listing evidence where needed.
This capture rail does not solve disclosure lag or establish through-T economic
coverage. Do not infer admission from successful replay. Owner review decides the
next contract and any merge; no merge, deployment or Chromebook change is part
of this implementation.
