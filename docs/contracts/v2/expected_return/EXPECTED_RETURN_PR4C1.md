# PR4C1 — Offline SEC filing-vintage diluted-EPS archive

PR4C1 proves:

> Exact SEC-style source snapshots can be archived immutably and filing-specific
> diluted-EPS observations can be preserved and inspected without flattening away
> their vintage/context semantics.

PR4C1 does NOT prove:

> Those observations are already qualified real PR4B1 roots.

The input object is a **companyfacts-style JSON snapshot**, not an immutable
10-K filing document. Filing accessions and row metadata are preserved as source
claims. This slice does not retrieve or authenticate their original documents.
Only fictional source bytes are used in tests. No provider/network implementation
is present, and no operational caches or private inputs are read.

## Starting state

After `git fetch origin`, authoritative V2 was
`897335d9b1cff00c381640ae87536cc3be4c28bf`, tree
`e153a99a4ff09153068070771d6b004d4ba8f7a3`. V1 remained
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`. The clean local checkout was
`codex/v2-expected-return-pit-diagnostics` at
`0648ba61a4484d37477360a0eb65afe906d376f8`, with the same V2 tree.
`codex/v2-sec-diluted-eps-archive` was created directly from authoritative V2.
The PR base is `model-v2/expected-return-challenger`, never `main`.

## Architecture and public APIs

```text
caller-supplied exact bytes and capture metadata
  -> economic_facts.sec_archive.SecArchive.capture
     -> exact-byte source object + immutable semantic capture receipt
  -> SecArchive.captures_as_of(cik, cutoff)
     -> every eligible receipt, plus latest captured-view receipt IDs
  -> economic_facts.sec_diluted_eps.extract_diluted_eps
     -> all rows of us-gaap:EarningsPerShareDiluted, including unusable rows
  -> assess_candidate / inspect_archive
     -> annual/period/value limitations and unresolved competing evidence
```

`extract_diluted_eps(raw, receipt)` is pure and checks byte/hash consistency.
`inspect_archive(archive, *, cik, cutoff)` is read-only and verifies archive
membership and source integrity before extraction. `SecArchive(root)` itself does
not touch disk. Capture initializes the archive; reading a nonexistent archive
fails without creating directories. No consumer is added to model/PIT code.

All result records are frozen dataclasses containing immutable scalars/tuples.
The implementation uses Python standard library only. It targets the existing
POSIX macOS/Linux environment, using directory descriptors and `O_NOFOLLOW`.

## Exact object and receipt contracts

Source object layout: `objects/<sha256-of-exact-bytes>`.
There is no source-object JSON wrapper or normalization: the stored content is
exactly the supplied bytes. Whitespace or mapping-order changes produce a
different source hash even when extracted semantics are equivalent.

Receipt layout: `receipts/<receipt_id>.json`.
Closed receipt fields are:

| Field | Contract |
| --- | --- |
| `schema_version` | `2026-09-10-sec-capture-receipt-v1` |
| `source_kind` | `SEC_COMPANYFACTS_SNAPSHOT` |
| `cik` | Exactly ten decimal digits; an issuer identifier only |
| `endpoint` | Exact companyfacts endpoint identity matching that CIK |
| `content_sha256` | Lowercase SHA-256 of exact source bytes |
| `byte_length` | Nonnegative integer, excluding booleans |
| `captured_at` | Explicit-offset input, normalized to canonical UTC `Z` |
| `source_locator` | Nonempty metadata string; never a filesystem path |
| `acquisition_contract_version` | `2026-09-10-offline-supplied-companyfacts-v1` |
| `receipt_id` | Computed SHA-256 of canonical semantic fields above, excluding itself |

Canonical receipt JSON uses sorted keys, compact separators, ASCII escapes and
finite JSON values. Unknown fields, duplicate keys, invalid versions and
identity mismatches fail. Receipt serialization key order/whitespace does not
change semantic identity. Different capture times can reference the same object.
Equivalent explicit timezone offsets canonicalize to the same receipt time.
Naive timestamps, invalid offsets and unknown `-00:00` offsets are rejected.

### Capture trust boundary

A receipt is intended to assert only that the exact bytes were present no later
than `captured_at`; it asserts no publication or source-availability timestamp.
**This offline API cannot prove a caller-supplied time or source identity is
truthful.** It validates the assertion's shape, persistence and byte linkage.
An authorized future acquisition process must mint trustworthy capture receipts.
Merely supplying an old timestamp here does not create genuine historical proof.
Hashes detect inconsistent content; they do not authenticate an attacker who can
replace the entire archive and every trust anchor.

## Storage, integrity and failure behavior

Objects and receipts are published only after a complete temporary file is
flushed and fsynced. A same-directory no-clobber hard link atomically exposes the
complete file. Temporary links are removed and the directory is fsynced. Files
are created read-only. There is no overwrite/update/delete API.

Repeated identical capture is idempotent. An existing object under the expected
hash with different bytes causes an error and is never repaired silently.
Semantically equivalent receipt serialization can be referenced idempotently
without rewriting it. Corrupt receipts fail closed. Object-first publication
can leave an unreferenced valid object if receipt publication fails; that object
does not grant any observation or time eligibility without a valid receipt.
Incomplete `.pending-*` files are not evidence and are ignored by inspection.

Root/ancestor/archive-child symlinks are rejected through descriptor-relative
directory traversal; file reads reject symlinks, nonregular files and external
hard links. Only computed hexadecimal hashes become filenames. CIK validation
and metadata-as-data handling prevent source metadata path traversal. Objects
are rehashed and length checked on read; receipt IDs and filenames are checked.
This is an archive-specific design, not a general filesystem framework.

## Extraction contract

Extraction version: `2026-09-10-sec-diluted-eps-extraction-v1`.
Inspection version: `2026-09-10-sec-diluted-eps-inspection-v1`.

Only `facts["us-gaap"]["EarningsPerShareDiluted"]["units"]` is extracted.
No basic EPS, adjusted EPS, estimates, price/P-E, income/share calculation,
IFRS concept, provider fallback or model proxy is used. Absent concepts/empty
unit arrays produce `DILUTED_EPS_UNAVAILABLE`, not a nonreporting assertion.
Malformed JSON/duplicate keys/invalid source structure fail explicitly.
Source CIK mismatch is an error; absent source CIK is retained as a limitation.

Every row retains CIK from its receipt, exact unit key, value, start/end, fy/fp,
form, filed, accession, optional frame, source hash, receipt ID, capture time,
extraction version, exact JSON pointer, semantic locator, and canonical raw row.
The raw row retains unknown extension/context fields as nonauthoritative source
content. Missing fields stay `None`; malformed metadata remains inspectable in
the raw row and yields explicit limitations. Missing frame alone is allowed.
Values use `Decimal` so binary floats cannot lose source decimal precision.
The US-GAAP namespace establishes only `candidate_accounting_basis=US_GAAP`.
Full original XBRL context not exposed by the snapshot cannot be synthesized.

### Locator and identity scheme

`source_locator` is an RFC-6901-style pointer, for example
`/facts/us-gaap/EarningsPerShareDiluted/units/USD~1shares/0`.
It identifies the exact row in the exact immutable source object.

`semantic_id` hashes issuer, namespace, concept, exact unit and the full row,
including unknown context fields. Its JSON representation sorts mapping keys and
uses an exact, canonical decimal encoding. `semantic_locator` replaces the array
index with `sha256:<semantic_id>`. It remains stable under mapping/row reordering.
Identical repeated rows share semantic identity but keep distinct exact pointers.

`observation_id` hashes source-object hash, capture-receipt ID, semantic ID, exact
pointer and extraction version. Thus reserialization changes source/observation
identity while preserving semantic identity. No object IDs, random identifiers,
temporary paths, process IDs or generated clock values enter evidence identity.

## Candidate inspection, not admission

Extraction preserves all diluted-EPS rows. Separate inspection recognizes
`10-K` and `10-K/A` only when `fp == FY`; no empty-fp equivalent is assumed.
Quarterly/nonmatching forms remain extracted but are not annual candidates.
20-F/40-F rows are preserved as nonmatching evidence, without a processing route.

Inclusive duration is `end - start + 1` when both dates parse. Only 365/366 days
satisfy the current period check. A 364-day 52-week year, 371-day 53-week year,
stub or other duration remains visible with
`UNSUPPORTED_BY_CURRENT_PR4B1_PERIOD_CONTRACT`. Calendar changes and missing
boundaries are not filled or bridged. No five-year comparable-series selection
is performed. Negative/zero values remain legitimate source observations with
`NOT_USABLE_BY_CURRENT_POSITIVE_EPS_ROUTE`; no positive replacement is selected.
Invalid dates, reversed periods, period-end-after-filing and filing-date-after-
capture-UTC-date claims are explicitly limited, not used to invent chronology.

Assessments report local annual/period/positive-value checks separately from
global qualification blockers. An `ANNUAL_DILUTED_EPS_CANDIDATE` still carries
those blockers. No `security_id` or `share_class` field is qualified or emitted;
even caller-provided assertions in a raw row remain only raw content.

## Amendments, collisions and as-of rules

Inspection admits only receipts for the requested CIK with `captured_at <= T`.
All admitted captures and their observations remain inspectable. The latest
capture IDs are a convenience view; equal-time captures are all retained rather
than arbitrarily ranked. Coverage is always `ARCHIVE_CAPTURE_VIEW_ONLY`, never
complete SEC coverage. An absent fact is not evidence it was never reported.

Original/amended filings are never overwritten, and no latest/positive winner is
selected. Period groups flag multiple units, filing versions, observations and
competing values. Same claimed source context with inconsistent values is
`SEMANTIC_IDENTITY_COLLISION`. Exact repeated rows or repeated captures of the
same semantic row do not create conflicting values. Missing period boundaries
remain individually limited rather than being guessed into a collision group.

A later filing's comparative FY2023 observation retains its actual later `filed`,
`fy` and `accn` fields. No vintage is inferred from the economic year. A 2022
filing first captured in 2026 is never exposed to a 2022 cutoff.

The regression fixture captures FY2024 EPS 2.00 at T1, then 1.75 with a different
accession at T2. An inspection between T1/T2 is identical before and after T2 is
appended; after T2, both versions and the new capture view are visible. Later
object bytes are not read for an earlier cutoff. Receipt catalog corruption
still fails closed because malformed receipt metadata cannot safely be assigned
to a time/issuer; this is an integrity failure, not a historical revision.

## Isolation and deferred live access

No `src/`, `main.py`, PR4A/PR4B1, PIT, discovery or configuration changes occur.
The only existing-file adjustment adds `economic_facts` to the isolated test
wrapper's code-copy allowlist. Model and transport import-boundary tests confirm
there is no reverse dependency. Dependencies, source-export pins, decision
fingerprint algorithms and model rules are untouched.

Future SEC access requirements supplied for this PR (not live-verified here):
public `data.sec.gov` APIs currently require no API key; automated access must
declare a User-Agent and respect the current 10 requests/second ceiling. Future
acquisition must verify the then-current SEC access policy, use a legitimate
configured contact identity, and implement rate limiting. The legacy placeholder
`local-user@example.com` is not a final acquisition identity. No email, secret,
downloader or live access is added here.

Worldwide capability remains PARTIAL. Non-US authorities and worldwide discovery
remain separate work.

## Remaining qualification blockers

- Live authenticated capture and trusted timestamp provenance.
- Publication/source-availability evidence and complete source coverage.
- Exact security, share-class and listing identity, including depositary receipts.
- Split basis and corporate-action reconciliation.
- Five-year comparable-series and competing-version resolution.
- Dividends/nonpayer, qualified price and objective profile qualification.
- Explicit real-source PR4B1 admission, still absent.
- Real PIT collector and any separately reviewed transport extension.
- Global jurisdictions.

## Validation

Use Python 3.12 and the unchanged `requirements.lock`, through the disposable
code-only runner. That runner strips credentials and forbids socket connections.

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

Preserved aggregate PIT fingerprint:
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
Preserved determinism fingerprint:
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.
Unchanged `MODEL_RULES_VERSION`: `2026-08-23-allocation-room-integrity-v7`.
These fixtures are diagnostic mechanical evidence only, not Baseline, real PIT,
strategy validation, tuning, or investment-decision evidence.

### Completed validation

Local interpreter: Python **3.12.14**. Every installed dependency matched the
unchanged `requirements.lock`. The repository's `.python-version` remains
**3.12.13** for its existing CI configuration; both interpreters are Python 3.12.

| Runner pattern | Result | Test duration |
| --- | --- | --- |
| `test_sec_*.py` | 56 passed | 0.810 s |
| `test_expected_return*.py` | 144 passed | 0.744 s |
| `test_pit*.py` | 40 passed, including the 64-case / 256-worker matrix | 379.606 s |
| `test_runtime_isolation.py` | 29 passed | 36.055 s |
| `test_validation_identity_isolation.py` | 19 passed | 0.421 s |
| `test_pr2_investment_equivalence.py` | 1 passed | 0.134 s |
| Full isolated suite | **1,198 passed** | **441.051 s** |

Both exact PIT fingerprints above were reproduced by the targeted and full
isolated suites. No expected fingerprint was regenerated. Working-tree and
staged whitespace checks passed before commit. Only this validation-result text
was added after the full test run; no tested executable source changed.
