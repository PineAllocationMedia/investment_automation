# PR4D2A — Controlled SEC filing capture for real qualification evidence

## Approved base and scope

After `git fetch origin`, V2 integration
`origin/model-v2/expected-return-challenger` was exactly
`a5dd90690a73417bbf1da059263f83e0df575077`, tree
`3839898dc7c906705e9fdf5172312df84114ba85`.
Frozen `origin/main` remained `c5fc27c82c29c2a6027eccee245098c4a072fdf1`.
The clean initial checkout was `codex/v2-lifecycle-roadmap-memory` at
`f0ad32b09bd6a5e595dd8b1230d2746a9aecd6f8`, with the same V2 tree.
`codex/v2-sec-filing-capture` starts at the exact verified integration commit;
existing divergent local refs are preserved.

The constitution, AGENTS, roadmap, D1 contract, approved real-admission audit,
SEC archive/acquisition/extraction/resolution, synthetic C4–C6, SEC fixtures/tests,
runtime isolation and validation identity were investigated before implementation.
This implements only the audit's acquisition prerequisite: one exact complete
submission for future reviewed real qualifiers. Separate real qualifiers and a
source-neutral admission join remain later work.

Exactly six files are added:

- `economic_facts/sec_filing_archive.py`
- `economic_facts/sec_filing_acquisition.py`
- `tests/sec_original_filing_fixtures.py`
- `tests/test_sec_filing_archive.py`
- `tests/test_sec_filing_acquisition.py`
- `EXPECTED_RETURN_PR4D2A.md`

The only existing-file modification is one test-only import allowlist entry in
`tests/test_sec_acquisition.py`, permitting the new acquisition module to reuse
C2 helpers. No existing production source changes. No CLI, framework, discovery,
roadmap update, dependency change, model-rule change or deployment is included.

## Public acquisition and replay

```python
acquire_sec_filing(*, cik: str, accession: str,
                   archive_root: str | Path) -> SecFilingAcquisitionResult
```

The result contains a frozen `FilingReceipt`, frozen `FilingEnvelope` selector
verification metadata (`cik`, `accession`, `form`, `document_count`), and internal
`request_started_at` / `response_completed_at`. Capture time lives in the receipt.
No caller URL, bytes, form assertion, timestamp, clock, transport, retry/rate
policy, contact override, profile, qualification or authority is accepted.

`SecFilingArchive(root).read_receipt(receipt_id)` and `read_object(receipt)` are
read-only replay APIs. The latter verifies stored receipt membership and exact
object length/hash. The archive has no public capture, offline capture, latest
selection, capture-history view, discovery or admission API. The private
`_capture_live` helper is reserved for reviewed acquisition and fictional tests.
An uploaded archive or caller-authored receipt cannot enter this trust domain
merely by claiming LIVE or reproducing a URL/hash. A detached receipt fails
membership. Whole-archive forgery by privileged code is outside local trust.

## Canonical route and shared transport

The selected resource is the modern accession-directory complete-submission text:

```text
https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_without_dashes}/{accession}.txt
```

Both selectors are exact ASCII strings: ten digits for CIK and
`##########-##-######` for accession. No whitespace normalization, Unicode digits,
URL fragments, separators, query strings or percent encoding are accepted.
The accession prefix is never compared to the registrant CIK: it may identify
an external filing agent. Retrieved envelope linkage supplies the association.
The SEC documents this path and caveat in
[Accessing EDGAR Data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data).

The dependency is one-way into unchanged `sec_acquisition` helpers:
`_user_agent`, `_rate_gate`, `_timestamp`, `_open_response`, `_check_status`,
`_single_header`, plus the existing deadline constant and typed errors.
No new lock, rate budget or transport opener exists. C2's single per-user lock
coordinates Companyfacts and filing captures across archives and processes,
waiting 0.25 seconds before every attempt and holding through response,
preflight and archive publication. Contention fails without requesting/retrying.

The unchanged transport requires the existing declared administrative User-Agent,
disables environment proxies, uses default verified TLS hostname/certificate
checks, rejects redirects, and uses a 15-second socket timeout. The 60-second
response deadline is checked before and after each bounded read; an in-flight
socket read can finish after the deadline, but no such response is published.
There is exactly one GET, no conditional requests, retries, decompression,
fallback endpoint or incorporated-document fetch.

The filing reader accepts only `text/plain`, optionally UTF-8 or US-ASCII charset,
and absent/identity Content-Encoding. Transfer-decoded chunked bodies are allowed;
ambiguous framing, duplicate relevant headers, other encodings/MIME types,
malformed or mismatched Content-Length fail closed. Reads are at most 64 KiB,
with a 32 MiB entity limit and at most one excess byte read for size detection.
HTTP response metadata is not retained. Errors contain only closed categories
and numeric status, never response bodies, paths or private contact values.
PAM adds no contact data to source bytes or receipts and emits no logs.

## Narrow initial preflight

This is selector/envelope verification, not economic identity qualification.
Supported forms are exactly `10-K`, `10-K/A`, `10-Q`, `10-Q/A`, `8-K`, covering
annual candidates and the reviewed agreeing retained C3 cross-form cases.

The reviewed envelope requires:

- ASCII modern `<SEC-DOCUMENT>...txt : YYYYMMDD` and
  `<SEC-HEADER>...hdr.sgml : YYYYMMDD` lines matching the requested accession;
- a bounded header (256 KiB), one acceptance field, unique accession/submission
  type/document count, and a closed inventory of top-level metadata labels;
- exactly one top-level `FILER` with one `COMPANY DATA` CIK matching the selector,
  and one `FILING VALUES` form matching the submission type;
- only the reviewed company/filing/business address/mail address/former company
  subsections; no other filing parties or unknown top-level contexts;
- 1–1,000 balanced, line-delimited DOCUMENT/TEXT envelopes, exactly matching the
  declared count, unique positive sequence identifiers and safe filename metadata;
- a first document whose TYPE matches the supported form, with no second document
  claiming that same primary form, and nonempty document payloads.

LF and CRLF, trailing horizontal whitespace, and empty optional header fields
are parsed while original bytes remain unchanged. Modern tab indentation
distinguishes filer sections from fields.
Embedded document payloads are opaque, including non-ASCII/binary exhibit bytes.
They are never decoded as HTML/XBRL, executed, fetched, normalized or treated as
proof of document truth. Filename metadata never becomes a filesystem path.
Reserved delimiter-looking lines inside a payload fail closed. Delimiters are
scanned with bounded counts and without recursive or backtracking SGML parsing.

Unsupported cases include other forms (including `8-K/A`, `20-F`, `6-K`), legacy
or alternate header formats, joint/multi-filer/owner/subject-company contexts,
unknown header sections, duplicated/missing/conflicting fields, malformed/truncated
SGML, oversized responses/headers, excessive documents and ambiguous structures.
A SEC-valid filing outside this deliberately narrow grammar is unsupported.
Primary-document URLs, filing indexes, arbitrary web content, latest/history
requests and resolution of external incorporated references are not implemented.
Capture of a submission containing a textual external reference does not imply
capture, availability or completeness of that external material.

## Dedicated immutable archive and receipt

`SecArchive` remains Companyfacts-specific and unchanged. The independent filing
archive retains its reviewed filesystem mechanics without subclassing, sharing
receipt types or adding a generic evidence-archive framework.

Objects are SHA-256-addressed exact entity bytes. Receipts are closed, frozen,
versioned records with schema/source kind, CIK, accession, canonical endpoint,
content SHA-256, positive bounded byte length, UTC capture timestamp and fixed
LIVE acquisition version. There is no economic identity/admission field.

- Receipt schema: `2026-09-20-sec-filing-receipt-v1`
- Source kind: `SEC_COMPLETE_SUBMISSION_TEXT`
- Acquisition: `2026-09-20-sec-live-filing-v1`
- Receipt hash domain: `pam:sec-complete-submission-receipt:v1\0`

Canonical sorted JSON and canonical UTC timestamps determine receipt identity.
The raw object hash remains ordinary exact-byte SHA-256. Paths, process IDs,
environment, random values and execution timestamps outside the explicit capture
time do not enter receipt identity. Equivalent JSON ordering/offsets replay to
the same receipt. Receipt and object hashes establish integrity, not credentials.

Publication uses descriptor-relative no-follow traversal from `/`, exclusive
pending files, read-only file permissions, file fsync, atomic no-clobber linking,
pending-file unlink and directory fsync. Reads reject symlinks, nonregular files,
extra hardlinks, oversized entries, missing receipts and mismatched hashes/lengths.
Receipt reads are bounded to 4 KiB; object reads to the receipt length plus one.
Existing evidence is never overwritten. Read paths create nothing. A publication
failure can leave an unreferenced exact object; that object confers no membership.
A crash between link/unlink can leave a multiple-link entry, which fails closed.
There is no claim of tamper-proof storage, remote attestation or secure time.

The SEC can correct/remove post-acceptance content. Accession alone is therefore
not immutable-byte identity. Changed-byte recapture retains a separate object and
receipt; unchanged-byte later capture deduplicates the object with a new receipt.
Old receipt replay never selects the newest capture or rewrites prior evidence.

## Time, failures and authority boundaries

Internal chronology must satisfy `request_started_at <= response_completed_at <=
receipt.captured_at`. Naive clocks/regression fail closed. Capture is an observation
bound generated after receive/preflight and before publication. It is not exact
publication, successful persistence time, first availability or historical cutoff.
Filing date, acceptance datetime, date-as-of-change and HTTP dates never determine
capture time. Source dates remain uninterpreted evidence bytes. No backdating or
HISTORICAL_AS_OF API exists.

Errors distinguish configuration/selector errors; rate/HTTP/network/redirect/
timeout/type/size/framing acquisition failures; unsupported filing envelope or
selector mismatch; and archive/integrity failures. None returns positive partial
admission. Shared transport errors are translated from their closed categories;
unexpected programming exceptions propagate. Replay corruption raises
`FilingArchiveError`, never ordinary weak-evidence unavailability.

PR4D2A establishes **none of D1 obligations 4–7**: security/share-class/listing
identity, share-basis comparability, accounting reporting-subject comparability,
or final economic admission. It creates no `CurrentAuthorityAssessment`, C4/C5/C6
qualification, admitted fact, Expected Return root, Decimal-to-float conversion,
source-authority registration or blocker removal. Synthetic qualification remains
synthetic. The receipt cannot enter the unchanged Companyfacts/D1 route.

One successfully captured resource proves no complete filing/event inventory,
absence of corporate actions, unchanged basis/subject, EPS-class applicability,
truth of issuer assertions, freshness or coverage through any D1 CURRENT boundary.
A later reviewed qualifier/bundle contract must establish those properties.
No licensing/commercial-use permission is inferred from access or capture.

## Validation and handoff

Validation uses unchanged `scripts/run_isolated_tests.py`: disposable code/state,
temporary HOME, stripped credentials and network denial. Only fictional filing
bytes and patched transport are used; no actual SEC/provider acquisition or
positive-capital application analysis is performed.

Environment: existing `.venv` uses Python **3.12.14**; repository `.python-version`
remains **3.12.13**. All **33** installed locked distributions match unchanged
`requirements.lock` exactly. No environment or dependency file was modified.

| Selection | Tests | Result |
| --- | ---: | --- |
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

The final new selection has **74 tests**: 24 archive and 50 acquisition/dependency
checks. Focused selections total **824 passing tests**. The 40-test PIT selection
passed in **986.553 seconds**. The complete isolated suite passed **1,733 tests in
1,061.949 seconds**, with no failures or skips reported. The initial full-suite
attempt was interrupted for a preflight format correction; these results belong
to the subsequent complete run of the final Python files. All six added/modified
Python files were byte-identical to that full-suite sandbox snapshot. Only this
validation record was completed afterward.

Both the PIT selection and complete suite reproduced the protected identities:

- PIT aggregate: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Unchanged model rules: `2026-08-23-allocation-room-integrity-v7`

Checks include `git diff --check`, `git diff --cached --check` and post-commit
`git show --format= --check HEAD`. The source inventory comparison against the
verified base finds only the documented test allowlist modification among existing
tracked files. A second fetch before delivery confirmed the same V2 SHA/tree and
frozen V1 SHA. No existing production source, runtime, PIT, model-rule, C4–C6,
Expected Return, authority registry, roadmap or deployment file changed.

Adversarial coverage includes selector/path attacks; mismatched agent/registrant
prefixes; MIME/framing/size/deadline/redirect failures; shared cross-process rate
contention and lock retention through publication; private contact suppression;
modern header formatting and malformed/multi-party envelopes; immutable replay,
recapture, detached/corrupt receipts, corrupt objects, links/FIFOs and atomic
publication failures; chronology and dependency/authority isolation.

Remaining work: a separately approved real qualifier/evidence-bundle contract
must establish economic identity, share-basis, reporting-subject and coverage
properties before any admission join or real Expected Return adapter. This PR
requires no new investment-philosophy or product decision. It grants no V2
production authority. No merge, deployment or Chromebook action is performed.
