# PR4C6 — Synthetic reporting-subject continuity qualification

## Starting state and investigation

Before modification, `git fetch origin` completed and authoritative refs matched:

| Ref | Commit | Tree |
| --- | --- | --- |
| `origin/model-v2/expected-return-challenger` | `0bebc7f38d2df3f4b0e54a025ca2dc8ed4c9effe` | `d9eb87e030d470a484cc54179158ae5208221284` |
| `origin/main` | `c5fc27c82c29c2a6027eccee245098c4a072fdf1` | `26a69bb0b2185ab141af0763da2d965602c8346b` |

The initial index/worktree were clean, on `codex/v2-share-basis-synthetic` at
`e121e7e31704f2007c7854f9dbb38658b1dc2618`, whose tree matched authoritative V2.
`codex/v2-reporting-subject-synthetic` starts directly at the authoritative V2
commit. Existing divergent local refs remain untouched.

The extractor, C3 resolver, C4 identity, C5 share basis, corresponding tests and
fixtures, PR4C3–5 documents, and PR4B1 assumptions were inspected before edits.
The approved premise fits: the fixed Companyfacts source semantics and exact
concept, C3 numerical/period resolution, C4 security/class qualification and C5
share denomination leave one new evidentiary property: accounting reporting-subject
continuity. C4's `UNCHANGED_SECURITY` does not itself identify the accounting
subject or require an accounting predecessor/successor presentation assessment.
No upstream change or PR4B1 integration is necessary.

Exactly four files are added:

- `economic_facts/reporting_subject.py`
- `tests/reporting_subject_fixtures.py`
- `tests/test_reporting_subject.py`
- `EXPECTED_RETURN_PR4C6.md`

## Scope and public API

```python
qualify_reporting_subject(
    series: ResolvedAnnualDilutedEPSSeries,
    identity: SecurityIdentityQualification,
    share_basis: ShareBasisQualification,
    request: ReportingSubjectRequest,
    evidence: SyntheticReportingSubjectEvidenceBundle,
) -> EconomicComparabilityQualification
```

This pure function asks whether every retained EPS observation and the current
qualified issuer/security belong to one continuous accounting reporting subject
from the oldest required period start through the derived boundary. It performs
no filesystem, network, clock, environment, model, or portfolio operation.

There is no assessment of acquisition intensity, business perimeter, organic
growth, earnings quality, management, durability, exceptional charges, taxes,
margins, cyclicality, repeatability or investment merit. Ordinary acquisitions,
divestitures, restructuring and normal accounting changes do not create subject
identities. Evidence anchors identify formal accounting subjects, not transaction
categories or accounting-policy epochs. No transaction ontology is introduced.

## Closed contracts and fixed profiles

| Constant | Value |
| --- | --- |
| `REPORTING_SUBJECT_CONTRACT_VERSION` | `2026-09-13-reporting-subject-contract-v1` |
| `REPORTING_SUBJECT_QUALIFIER_VERSION` | `2026-09-13-synthetic-reporting-subject-qualifier-v1` |
| `SYNTHETIC_EVIDENCE_VERSION` | `2026-09-13-synthetic-reporting-subject-evidence-v1` |
| `EXTRACTION_VERSION` | `2026-09-13-synthetic-reporting-subject-claims-v1` |
| `SOURCE_PROFILE` | `2026-09-13-sec-companyfacts-total-diluted-eps-v1` |
| `MEASUREMENT_PROFILE` | `2026-09-13-reported-total-entity-diluted-eps-us-gaap-v1` |

The source profile is the supported current SEC Companyfacts route, exact
`us-gaap:EarningsPerShareDiluted`, `USD/shares`, and candidate `US_GAAP` accounting
profile. Its economic meaning is reported total-entity diluted EPS attributable
to the qualified common equity. The request has no profile, numerator, caller
as-of, comparability boolean, adjustment factor, value replacement or callback.

The SEC's standard-taxonomy and entire-filing-entity API restrictions, together
with the selected concept, supply source-level measurement meaning. C6 does not
reconstruct that meaning from filings or substitute continuing-operations EPS.
Source semantics remain separate from authentication and issuer tagging quality.
The qualifier detects neither all issuer mistakes nor economic sustainability.

The nine frozen/slotted record types are:

| Record | Purpose |
| --- | --- |
| `ShareBasisQualificationWitness` | Original C5 request and C5 evidence, including its original nested C4 witness |
| `ReportingSubjectRequest` | Version, closed current/historical mode, exact C3/C4/C5 semantic/evidence hash pairs |
| `ReportingSubjectSpan` | Subject anchor, issuer anchor, inclusive date interval, exact opaque observation references |
| `ReportingSubjectSnapshot` | Exact series hash pair, explicit completeness, subject spans |
| `SyntheticReportingSubjectEvidence` | Typed claims, bytes/digest, reference/locator/versions, publication/availability/capture timestamps |
| `SyntheticReportingSubjectEvidenceBundle` | Version, one C5 witness, mandatory documents |
| `PeriodReportingSubjectDecision` | Original period/value and full lineage, assigned subjects, qualified subject or null, outcome/reasons |
| `EconomicComparabilityQualification` | Profiles, upstream identities, boundary, qualified anchors/basis identity or null, five decisions, authority/blockers, semantic/evidence IDs |

All collections are immutable tuples. Exact recursive types reject subclasses,
mutable collections, unknown enum substitutes and malformed optional records.
Invalid structure, foreign references, invalid issuer links, stale versions,
source corruption and forged replay results raise `ReportingSubjectContractError`.

## Upstream replay and trust boundary

`_replay_sec_profile` calls the unchanged `qualify_share_basis` and requires exact
canonical serialized equality with the supplied C5 qualification. C5 uses its
existing `IdentityQualificationWitness` to replay unchanged C4, which validates
C3 structure and the fixed SEC profile. C5 also checks C3's exact semantic hash.
No independent C4 witness or parallel copy of those qualification algorithms exists.
The small profile helper additionally recognizes the existing live/offline
Companyfacts acquisition contract identifiers and preserves the offline blocker.

Success requires exact successful C4 and C5 results, C5 `TransformationMode.NONE`
and a non-null qualified target basis. Valid upstream unavailability produces
`UPSTREAM_NOT_QUALIFIED`; malformed or unsupported C3 series are rejected by the
existing replay contract, not rescued. An unavailable/forged result cannot acquire
a successful state merely by relabeling its outcome.

Replay is internal consistency only. It does not authenticate external documents,
the truth of subject anchors or a fictional assertion of complete coverage. Full
C3 evidence authentication still needs the original archive/extraction chain;
C6 does not reconstruct its evidence hash from the smaller series projection.

## Subject coverage and chronology

A span contains a stable `synthetic:subject:...` anchor separate from its
`synthetic:issuer:...` link. References reuse the jurisdiction-neutral C5
`ObservationReference`: period start/end and opaque version/observation IDs.
Core subject records contain no CIK, form, accession, exchange or ticker semantics.
Future jurisdictions can prove the same subject property through other adapters.

The required interval is the oldest C3 period start through the C6 boundary date.
Spans assert inclusive whole dates; capture boundaries retain full UTC timestamp
precision. A span covering the boundary date explicitly covers that whole date;
no intraday transition ordering is inferred from a date. Source timestamps must
be canonical UTC instants, including six-digit fractional precision where present;
a date-only source value is rejected rather than promoted to an invented instant.

Each mandatory snapshot must independently:

- Declare complete coverage.
- Cover the entire required interval without gaps.
- Assign every retained period/version/observation reference, including all
  agreeing 8-K, 10-Q and 10-Q/A observations outside annual support.
- Link every span to the exact qualified issuer when an issuer is available.
- Cover the full period of every observation assigned to a span.
- Establish a single accounting subject over the required interval.

One span can enumerate the complete inventory. No per-observation accounting
document is required. Identical duplicates do not create extra evidence meaning.
Adjacent or overlapping spans for the same subject are canonically merged for
comparison. Actual chronology stays date-ordered, including on failed results.
Multiple snapshots cannot fill each other's omissions; complete snapshots must
agree on canonical required chronology and observation assignments.

A formal predecessor/successor, reverse-acquisition reporting reset, or
carve-out/combined-subject replacement within the required interval is unsupported.
This is evidenced by distinct accounting-subject anchors, not inferred from a
transaction label, CIK or security ticker. Different numbers are not necessary:
identical EPS assigned to different subjects still fail.

| Transition location | Treatment |
| --- | --- |
| Entirely before the required interval | May qualify when one successor covers all required history and the boundary |
| Within the five-year history | Discontinuity rejection |
| After latest EPS, through the boundary date | Discontinuity rejection |
| Strictly after the boundary date | Outside the requested scope; evidence remains bound in evidence identity |

## Outcomes, boundaries and auditability

Modes are `CURRENT_SNAPSHOT` and recognized-but-unsupported `HISTORICAL_AS_OF`.
Historical requests still validate typed inputs/replay and source integrity, then
return `HISTORICAL_COMPARABILITY_UNSUPPORTED`. The reported boundary remains a
current evidence boundary; it never represents historical availability.

The derived boundary is the maximum of C3 authority, C4 qualification, C5
qualification boundary and every mandatory C6 capture timestamp. Any extension
past C5 produces `UPSTREAM_BOUNDARY_NOT_QUALIFIED`, including one microsecond on
the same day. A later successful C6 result needs a newly successful upstream chain.

Outcomes are `COMPARABLE_WITHIN_SYNTHETIC_SCOPE`, `COMPARABILITY_UNAVAILABLE`,
and `COMPARABILITY_UNSUPPORTED`. The reason set distinguishes upstream failure,
upstream-boundary failure, incomplete coverage, evidence conflict, discontinuity
and unsupported historical mode. `SYNTHETIC_EVIDENCE_ONLY` is an unconditional
limitation, never a failure reason by itself.

Every returned result contains five immutable period decisions. Each retains the
original Decimal object, start/end, annual supporting IDs, complete version IDs
and complete version-observation references. No EPS arithmetic, float conversion,
rounding, restatement, alternate selection, logarithms or growth calculation occurs.
Finite positive, negative and zero values have identical subject-qualification
eligibility. PR4B1's later `NONPOSITIVE_REQUIRED_EPS` rule remains separate.

On any overall failure, qualified subject, issuer, security, class and target-basis
identity are all null; every period's qualified subject is null. Assigned subjects
remain diagnostic evidence, with failure outcomes/reasons. The successful target
basis identity uses C5's `qualified_target_basis.semantic_hash`, not its whole
series-specific qualification hash.

## Semantic and evidence identity

SHA-256 hashes use contract/qualifier version and explicit domain separation.
Semantic identity binds all upstream semantic hashes, fixed source/economic
profiles, mode, required interval/boundary, qualified subject, canonical subject
chronology, five period semantic decisions, outcome and reasons. C3's semantic
hash already binds exact numeric meaning, without Decimal context rounding.
Observation IDs and Decimal spelling are retained in evidence, not reinterpreted
as new economic meaning.

Evidence identity additionally binds upstream evidence and complete supplied
results, request, replay witness, every verified source's exact bytes/digest,
metadata/locator/versions/timestamps/claims, full period lineage, blockers and
limitations. Reordered equivalent documents/references preserve semantics;
reformatted bytes or changed provenance can alter evidence identity alone.
Nothing is discarded merely because it lies outside the required subject interval.

## Authority, real admission and preserved behavior

The only C6 authority is `SYNTHETIC_TEST_ONLY`. The union of all applicable upstream
admission blockers survives synthetic success:

- `PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED`
- `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED`
- `SPLIT_BASIS_NOT_ESTABLISHED`
- `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`
- `SNAPSHOT_COVERAGE_ONLY`
- `UPSTREAM_EVIDENCE_ONLY`
- `OFFLINE_CAPTURE_NOT_AUTHENTICATED`, where applicable

Offline Companyfacts-shaped bytes exercise mechanics only. A test fixture carrying
live-capture metadata also leaves C6 synthetic; it invokes no provider acquisition.
The future real route separately needs acceptable acquisition, identity, basis,
subject and availability authorities. C6 does not discharge any real blocker or
construct PR4B1 roots. No PR4B1, model, policy, allocation or V1 file changes.

Protected validation identities:

- Aggregate PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- `MODEL_RULES_VERSION`: `2026-08-23-allocation-room-integrity-v7`

## Validation

Python 3.12.14 and all 33 unchanged `requirements.lock` pins were verified.
Every test command uses the unchanged `scripts/run_isolated_tests.py`, with a
disposable code checkout, temporary HOME, credentials removed and network disabled.
Focused tests cover successful/full cross-form histories, signs/precision,
ordinary business/accounting changes, before/inside/after interval transitions,
missing/conflicting/stitchable coverage, exact replay attacks, source metadata and
byte tampering, boundary precision, immutable contracts and explicit non-features.

| Isolated test selection | Tests | Result |
| --- | ---: | --- |
| PR4C6 reporting subject | 77 | PASS |
| PR4C5 share basis | 136 | PASS |
| PR4C4 security identity | 84 | PASS |
| PR4C3 EPS series | 52 | PASS |
| All SEC (`test_sec*.py`, including security identity) | 235 | PASS |
| Expected Return | 144 | PASS |
| PIT | 40 | PASS |
| Runtime isolation | 29 | PASS |
| Validation identity | 19 | PASS |
| PR2 investment equivalence | 1 | PASS |
| Complete isolated suite | 1590 | PASS (481.227 s) |

Both the targeted PIT run and complete suite reproduced the protected aggregate
and determinism fingerprints exactly. `git diff --check`,
`git diff --cached --check`, and `git show --format= --check HEAD` passed.
No provider acquisition, real-capital analysis, production run, deployment or
merge was performed. Existing source/model/allocation/portfolio files are unchanged.
