# PR4C3 — Single-snapshot annual diluted-EPS series resolution

PR4C3 proves:

> One explicit preserved SEC companyfacts snapshot can be deterministically reduced to five consecutive issuer-level annual diluted-EPS values when all admissible comparable reporting versions agree exactly.

PR4C3 does NOT prove:

> Those values are already economically comparable for a specific security, split-adjusted, historically PIT-valid, or eligible for PR4B1.

## Verified starting state

After fetch, authoritative V2 was `10dfafdbe9c595f6bbdb734dd7b10f01d9f76781`,
tree `8a61feabcecd0c9daae662034662c4af3479a881`. Remote V1 remained
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`. The clean initial checkout was
`codex/v2-sec-live-companyfacts-acquisition` at
`5efba0b9c46b17ec0047ab046dd5fa4bc835efb0`.

Implementation branch `codex/v2-sec-eps-series-resolver` starts directly at the
verified V2 revision. Local `main` (`abc37bd52c24b2d68adf8138e57625327a3251b7`)
and local integration (`c5fc27c82c29c2a6027eccee245098c4a072fdf1`) remain untouched.
The PR base is `model-v2/expected-return-challenger`; merging is not authorized.

## Scope and API

```text
resolve_annual_diluted_eps(archive: SecArchive, request: SeriesResolutionRequest)
    -> SeriesResolutionResult
```

The only application dependencies are `sec_archive` and `sec_diluted_eps`.
The resolver does not import acquisition, `src`, PIT, providers, configuration,
or model code. It reads one explicit receipt and its verified object, invokes the
existing extractor, and returns immutable evidence. It never selects archive
latest, combines receipts, writes files, reads environment/time, or uses network.

Only four new files are needed: the resolver, fictional fixture helpers,
resolver tests, and this document. Legacy archive/extraction/acquisition code,
IDs, receipt schema, inspection output, and qualification blockers are unchanged.
Legacy `official_data_fetcher._annual_series` is not imported or reused.

## Versioned closed contracts

| Identity | Value |
| --- | --- |
| Series contract | `2026-09-11-sec-annual-diluted-eps-series-v1` |
| Resolver | `2026-09-11-sec-current-reported-consensus-v1` |
| Period policy | `2026-09-11-fixed-month-end-365-366-v1` |

All records use frozen, slotted dataclasses and immutable tuple collections.
The public boundary requires exact `SecArchive` and `SeriesResolutionRequest`
types, rejects subclasses/mappings, validates scalar types, and checks exact
enum/version identities. Output construction is internal to the resolver;
dataclasses are not an unforgeable authentication capability.

`SeriesResolutionRequest` fields are exactly `contract_version`, `mode`,
`receipt_id`, `cik`, `latest_required_fiscal_end`, `expected_unit`, and
`period_policy`. No caller observation tuple, economic as-of, transport, clock,
authority assertion, policy callback, or winner preference is accepted.

`CaptureAuthorityAssessment` binds receipt/object identity, acquisition contract,
capture timestamp, LIVE/OFFLINE authority, and downstream limitations.

`ResolvedAnnualDilutedEPS` binds start/end, inclusive days, exact Decimal value,
representative observation, all supporting annual observation IDs, all comparable
semantic version IDs, filing metadata/occurrence inventories, selection reason,
and informational metadata limitations. Reported `fy`, `fp`, and frame remain
source metadata in each `FilingVersionReference`; they never define continuity.

`PeriodResolutionDecision` retains considered/admissible IDs, excluded records
with reason codes, distinct comparable values, support/conflict identities,
status, and blockers. `SeriesResolutionResult` also retains the complete original
`Extraction` and a sorted exclusion inventory for observations outside the five
required intervals or excluded from annual candidacy. No source row is deleted.

`ResolvedAnnualDilutedEPSSeries` binds CIK, exact namespace/concept/unit/basis,
mode, receipt-derived authority time, period policy, required final period,
exactly five ordered annual records, receipt/object/accession lineage, resolution
status, downstream blockers, and semantic/evidence hashes.

On economic resolution failure, status is `UNAVAILABLE`, reasons are sorted
closed enums, and `series=None`; extraction and decisions remain inspectable.
Malformed requests raise `SeriesResolutionError(INVALID_REQUEST)`. Archive
membership/hash/length/schema failures raise `ARCHIVE_INTEGRITY_ERROR`; malformed
source raises `SOURCE_STRUCTURE_ERROR`. No corrupted evidence is silently repaired.

## Time and LIVE/OFFLINE authority

`CURRENT_AS_REPORTED` means mechanically resolvable within this explicit snapshot.
The resolver derives `authority_as_of = receipt.captured_at`. It neither asserts
that the snapshot is currently the newest source nor extends its freshness beyond
capture. Coverage remains snapshot-only.

`HISTORICAL_AS_OF` always returns `HISTORICAL_CUTOFF_UNSUPPORTED`, with no archive
reads, extraction, or authority assessment. It cannot produce a partial historical
answer. A 2026 capture containing a 2022 filing date cannot create 2022 knowledge.

Receipt-aware assessment is additive:

- `2026-09-11-sec-live-companyfacts-v1` -> `LIVE_LOCAL_CAPTURE`.
- `2026-09-10-offline-supplied-companyfacts-v1` -> `OFFLINE_SUPPLIED_CAPTURE`.
- Only OFFLINE carries `OFFLINE_CAPTURE_NOT_AUTHENTICATED` in the new assessment.
- Unknown/corrupt acquisition contracts are rejected by the archive reader.

Legacy PR4C1 inspection still has its original fixed blocker tuple. Its historical
output is not reinterpreted or changed. LIVE remains trusted local-process capture
under PR4C2's threat model, not cryptographic remote or historical attestation.

## Annual scope and anti-window-shopping

Scope is exactly `us-gaap:EarningsPerShareDiluted`, `US_GAAP`, and `USD/shares`.
There is no IFRS/basic/adjusted EPS fallback, FX conversion, or mixed-unit series.
An absent exact concept yields `DILUTED_EPS_UNAVAILABLE` rather than substitution.

The initial period policy requires full twelve-month intervals ending on a fixed
month's last day, with 365/366 inclusive days. Each next start is the prior end
plus one day. February uses actual month ends, including leap days. The required
five intervals are generated backward from the explicit final fiscal end; gaps
cannot be filled with older observations. 364/371-day week calendars, shifted
annual boundaries, stubs, and calendar transitions are not annualized or admitted.

Before value/identity filtering, an apparent-annual envelope inspects USD rows.
When both economic dates are valid, only 364–371 inclusive days enter this
conservative envelope, regardless of form/fp. This includes supported 365/366-day
years and unsupported week/shifted annual intervals. Valid short quarterly,
interim, or stub intervals do not enter merely because form is annual, `fp=FY`,
or form/fp is missing. When either date is unavailable or invalid, annual forms,
`fp=FY`, or missing form/fp still make the row potentially annual and fail closed.
Any later end produces `LATER_ANNUAL_PERIOD_PRESENT`. Unlocatable apparent annual
rows produce `INSUFFICIENT_FILING_IDENTITY`. Missing accession, value, or other
qualification metadata cannot hide a newer period. Zero/negative values are
never filtered. Missing final coverage fails instead of reverting to an older
window. Alternate year-length intervals overlapping the required window fail
calendar qualification even when a clean interval is also present.

Annual filings can contain quarterly comparative rows. Those rows cannot supply
annual values or establish a later annual economic period. Short comparative rows
are preserved as excluded nonannual intervals. A stub replacing a required annual
interval still fails annual coverage; it is not classified as an annual calendar.
This envelope can reject uncertain snapshots;
it does not claim to infer fiscal-year identity from incomplete metadata.

## Candidate identity, contexts, and exact agreement

Annual candidates require `10-K` or `10-K/A`, `fp=FY`, exact required interval,
valid accession `##########-##-######`, and valid filing-date chronology:
`period_end <= filed <= capture UTC date`. Accession prefix need not equal CIK.
Neither accession ordering nor `filed` establishes authority or supersession.
No publication or availability timestamp is fabricated.

Missing `fy` or frame alone is not disqualifying. A misleading `fy` is preserved
without changing interval identity. Malformed supplied metadata is not silently
treated as a missing optional value. Unexplained form/filed/fp or nonmissing-fy
contradictions within one accession/period block filing identity.

Comparable exposed context is deliberately narrow: the row may contain only
`start`, `end`, `val`, `accn`, `fy`, `fp`, `form`, `filed`, and `frame`. Unknown
extensions/dimensions produce `UNRESOLVED_CONTEXT`; they are neither silently
discarded nor used to manufacture a value conflict. Matching this projection
does not prove complete underlying XBRL context or security/split comparability.

Other forms with the exact interval participate in conflict inspection when
their exposed context and filing identity pass. They cannot supply the required
annual candidate. Equal cross-form versions remain in the lineage; different
comparable values block the period. The first contract conservatively requires
valid form/fp/filed identity for cross-form comparisons too: an otherwise matching
8-K row with missing fp blocks with `INSUFFICIENT_FILING_IDENTITY`. This policy is
covered by a fictional test and is not relaxed to make a real issuer pass.

All comparable values must agree exactly as Decimal numbers. There is no tolerance,
averaging, latest-filed/latest-accession precedence, amendment precedence, or
comparative restatement override. Same accession/context with different values
adds `SAME_ACCESSION_VALUE_CONFLICT`; different comparable values add
`UNRESOLVED_VALUE_CONFLICT`. Unknown contexts are excluded from those value sets.

Exact transport duplicates retain distinct observation pointers but one semantic
version. Different filing versions remain separate even if values agree. A
representative annual citation is selected by semantic identity and exact pointer
solely for serialization. It is never an authoritative winner. All supporting
versions and excluded observations remain auditable.

## Values, identities, and downstream boundary

Finite positive, zero, and negative reported values are treated equally. PR4B1's
positive-EPS methodology remains downstream. No growth, normalization, confidence,
price, Expected Return, corporate-action adjustment, or security mapping is computed.

The semantic hash binds the five exact periods/values, issuer, scope, mode, and
contract/resolver/period-policy versions. It is stable under row reordering,
equivalent Decimal spellings, extra irrelevant observations, and recapture of the
same economics. It does not claim evidence authority.

The evidence hash also binds the request, receipt/acquisition authority, exact
object hash, complete extraction, original observation IDs/pointers, decisions,
exclusions, and filing-version inventories. Reordering source bytes or changing
capture time changes evidence identity. The existing exact Decimal encoder is
reused; no float conversion or precision-sensitive Decimal normalization occurs.

Success is only `RESOLVED_ISSUER_EVIDENCE`, and always retains:

- `PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED`
- `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED`
- `SPLIT_BASIS_NOT_ESTABLISHED`
- `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`
- `SNAPSHOT_COVERAGE_ONLY`
- `UPSTREAM_EVIDENCE_ONLY`

No real PR4B1 AdapterIdentity, root, ShareBasis, or temporal admission is created.
Future qualification still needs security/split/comparability evidence, genuine
publication/availability semantics, a reviewed real adapter, dividend/nonpayer,
price and objective profile evidence. VFV forward ER and historical PIT remain
separate work. Repeated observations never increase numerical confidence.

## Failure categories

Closed reasons distinguish insufficient coverage, missing latest/annual periods,
later periods, nonconsecutive periods, unsupported calendars/transitions, unit or
accounting mismatch, unavailable exact concept, unknown context, value conflicts,
missing/invalid accessions, insufficient filing identity, invalid values/filing
chronology, and unsupported historical mode. Per-observation exclusion reasons
also identify nonannual forms/intervals and outside-window evidence. Integrity and
request errors remain exceptions, separate from economic unavailability.

## Retained Microsoft diagnostic

Read-only inspection used the existing archive `/private/tmp/sec-smoke-archive-Al8Ez8vx`,
receipt `2fbff39067e5e1af3a3bd76388bc631bb85ae585d22b92bf6a7f4b4ecbfb30b1`,
object `f8aae2965b20ad0df44bdf7ccbedf797d275b6b8dc030154a7a311361bb7246f`.
No acquisition or source mutation occurred, and tests do not depend on this archive.

The FY2022–FY2026 request returned `UNAVAILABLE` with
`INSUFFICIENT_FILING_IDENTITY`. The 12 annual 10-K candidates agree within their
periods, but the complete 340-row inventory also contains same-interval 8-K rows
for FY2022, FY2023, and FY2024 from accession `0000950170-24-132722`, filed
2024-12-03, with missing fp and fy. Missing fy alone is informational; missing fp
fails this first contract's cross-form identity gate. The earlier annual-only
diagnostic did not establish those additional rows' admissibility. No competing
value or restatement conclusion is inferred from missing metadata.

The blocker is reported rather than weakening policy. Any future relaxation needs
an explicit general context/identity contract and fictional adversarial tests.

## Validation and preserved identities

Use Python 3.12 with unchanged locked dependencies. Tests use fictional sources,
including synthetic LIVE publication without acquisition. The existing isolated
runner uses disposable code/state, strips credentials, and forbids network.

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_sec_eps_series.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_sec_*.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_expected_return*.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pit*.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_runtime_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_validation_identity_isolation.py'
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_pr2_investment_equivalence.py'
.venv/bin/python -B scripts/run_isolated_tests.py
git diff --check
git diff --cached --check
git show --format= --check HEAD
```

Preserved aggregate PIT fingerprint:
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
Preserved determinism fingerprint:
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.
`MODEL_RULES_VERSION` remains `2026-08-23-allocation-room-integrity-v7`.
PR4A/B1/B2 identities, PIT pins/fixtures, legacy SEC identities, dependencies,
configuration, and investment semantics remain unchanged. Expected fingerprints
are never regenerated. Validation results are recorded after execution.

### Completed validation

Python **3.12.14**; installed locked dependency versions matched the unchanged
`requirements.lock`. All commands below used the disposable isolated runner.

| Scope | Passed | Test duration |
| --- | ---: | ---: |
| New resolver | 46 | 0.701 s |
| All SEC | 145 | 1.828 s |
| Expected Return | 144 | 0.516 s |
| PIT | 40 | 519.961 s |
| Runtime isolation | 29 | 39.782 s |
| Validation identity | 19 | 0.292 s |
| PR2 equivalence | 1 | 0.100 s |
| Full isolated suite | **1,287** | **614.504 s** |

The PIT and full runs both reproduced the exact aggregate and determinism
fingerprints above. An initial test-only AST guard incorrectly classified
`re.compile` as dynamic Python compilation; the guard was corrected, and all
final focused/full runs passed. No expected fingerprint was regenerated.
Working-tree and staged whitespace checks passed. Only this completed-validation
record was added after the final suite; executable source and tests did not change.
The implementation commit also receives the required commit whitespace check.

These runs are fictional mechanical regression evidence. No operational
Expected Return, real PR4B1 admission, SEC request, or investment decision ran.

### PR #36 annual-envelope correction

Before changing implementation, a fictional 2025-01-01 through 2025-03-31 8-K
row with missing fp reproduced the defect: the requested 2024-12-31 latest annual
window incorrectly returned `LATER_ANNUAL_PERIOD_PRESENT`. The resolver suite
then had 47 tests, with exactly this new regression failing.

The implementation change is confined to `_apparent_annual()`: valid economic
dates now take precedence over filing-form/missing-metadata heuristics, as
specified above. Six new test methods cover short later 8-K/annual-form/missing-form
rows, later 365/366-day rows missing fp, 364/371-day week years, and unlocatable
potential annual rows with incomplete metadata. Existing zero/negative/missing-value
later-year and same-interval cross-form identity tests remain unchanged. The stub
coverage test now expects a missing annual period rather than treating a known
short interval as an unsupported annual calendar.

The retained Microsoft receipt was rerun offline and still returned only
`INSUFFICIENT_FILING_IDENTITY` with `UNAVAILABLE` status and 340 observations.
Archive file hashes, sizes, modification times, and modes remained unchanged.
No SEC request was made. Filing-version agreement, LIVE/OFFLINE authority,
PR4C1 identities, PR4B1 admission, and model/allocation rules are unchanged.

Correction validation on Python 3.12.14, using the isolated runner:

| Scope | Passed | Test duration |
| --- | ---: | ---: |
| Resolver | 52 | 0.580 s |
| All SEC | 151 | 3.430 s |
| Expected Return | 144 | 0.580 s |
| PIT | 40 | 535.013 s |
| Runtime isolation | 29 | 41.410 s |
| Validation identity | 19 | 0.467 s |
| PR2 equivalence | 1 | 0.103 s |
| Full isolated suite | **1,293** | **588.618 s** |

Both PIT and full runs reproduced the exact aggregate and determinism fingerprints
recorded above. Expected fingerprints and `MODEL_RULES_VERSION` were unchanged.
Only documentation was updated after these runs; executable code and tests were
unchanged. Correction logs are retained at `/private/tmp/pr36-envelope-*.log`.
