# PR4C5 — Synthetic split-only share-basis qualification

The invariant is that every retained EPS observation already uses one explicitly
evidenced target common-share denomination. The qualifier preserves the original
upstream `Decimal` object in each period decision. It never changes EPS.

## Verified starting state and investigation

`git fetch origin` completed before implementation. Remote state exactly matched:

| Ref | Commit | Tree |
| --- | --- | --- |
| `origin/model-v2/expected-return-challenger` | `1e4307d42aeceb7d3d35942fabffd3b34af7a633` | `d2eac9dda3bc88861afca66ab50687dcdaf3c6d5` |
| `origin/main` | `c5fc27c82c29c2a6027eccee245098c4a072fdf1` | `26a69bb0b2185ab141af0763da2d965602c8346b` |

The initial working tree and index were clean. The local branch was
`codex/v2-security-identity-cross-form-compat`, HEAD
`aa452e28f5cef50886b95c049b9fdf2c2ba2a57a`, with the same tree as authoritative V2.
The implementation branch `codex/v2-share-basis-synthetic` starts at the exact
remote V2 commit. Existing local references were left untouched.

Before implementation, the current implementations, fixtures and tests for
`sec_eps_series` and `security_identity`, plus `EXPECTED_RETURN_PR4C3.md` and
`EXPECTED_RETURN_PR4C4.md`, were inspected. They match Option C's prerequisites.
No integration change is required. Exactly four files are added:

- `economic_facts/share_basis.py`
- `tests/share_basis_fixtures.py`
- `tests/test_share_basis.py`
- `EXPECTED_RETURN_PR4C5.md`

PR4C4.1's distinction is preserved: `supporting_observation_ids` contains annual
support only, while `filing_versions` contains complete comparable lineage.
An agreeing 8-K, 10-Q or 10-Q/A observation can be outside annual support and still
requires explicit share-basis evidence. Nothing trims or promotes that lineage.

## API and version identities

```python
qualify_share_basis(
    series: ResolvedAnnualDilutedEPSSeries,
    identity: SecurityIdentityQualification,
    request: ShareBasisRequest,
    evidence: SyntheticShareBasisEvidenceBundle,
) -> ShareBasisQualification
```

| Constant | Value |
| --- | --- |
| `SHARE_BASIS_CONTRACT_VERSION` | `2026-09-13-share-basis-contract-v1` |
| `SHARE_BASIS_QUALIFIER_VERSION` | `2026-09-13-synthetic-split-only-qualifier-v1` |
| `SYNTHETIC_EVIDENCE_VERSION` | `2026-09-13-synthetic-share-basis-evidence-v1` |
| `EXTRACTION_VERSION` | `2026-09-13-synthetic-share-basis-claims-v1` |

The request binds both upstream semantic/evidence identity pairs and a closed
current/historical mode. `TransformationMode` has exactly `NONE`. No adjusted
value field, adjustment factor, callback, price or caller boundary exists.
Unexpected constructor fields fail at the closed Python signature; malformed
qualifier inputs raise `ShareBasisContractError`.

## Exact upstream witness and trust limit

`IdentityQualificationWitness` stores the original immutable PR4C4 request and
fictional evidence bundle. The existing `qualify_security_identity` is called and
its complete serialized result must exactly equal the supplied qualification.
Changing a nested name, lineage, boundary, hash, blocker or EPS value without the
matching original replay fails as a contract error. Only an exact successful
PR4C4 result can qualify share basis.

The source-profile helper also recomputes PR4C3's semantic projection using its
existing pinned exact encoder. A forged series semantic hash is rejected even
when supplied through newly constructed fictional identity evidence. PR4C3's
full evidence hash cannot be independently reconstructed without its original
archive, extraction and resolution decisions, which are not retained in the
series. This module does not claim to authenticate that evidence hash. It requires
exact linkage and binds the complete supplied series through PR4C4 replay and
PR4C5 evidence identity. Fictional callers can construct self-consistent fictional
inputs; hashes and replay are consistency checks, not external authentication.

All records are frozen and slotted. Exact recursive types reject subclasses,
mutable containers, strings in place of enums and bools in place of integers.
Upstream records, values, IDs, blockers and semantics remain unchanged.

## Sources, coverage and time

Every source contains one mandatory complete `ShareBasisSnapshot`: upstream
identity links, an explicit baseline, corporate-action coverage, complete notice
inventory, and exact reported-basis disclosures. No source is optional and partial
snapshots cannot be stitched together. Complete snapshots must agree.

`SyntheticSourceEvidence.source_bytes` decodes to the exact projection of every
source field except `source_bytes` and `content_sha256`. The envelope therefore
binds authority, reference, schema/extraction versions, `/claims` locator,
publication/availability/capture chronology, and all typed claims. SHA-256 is
verified first; unknown fields, duplicate JSON keys, floating-point numbers,
nonfinite numbers and detached metadata/claim edits are rejected. Whitespace and
key order can differ without changing economic meaning; exact evidence hash then
changes. This is a fictional extraction contract, not a real document parser.

The deterministic qualification boundary is the maximum of PR4C3 authority time,
PR4C4 qualification time and every mandatory share-basis capture time. Timestamps
must be canonical UTC, and publication <= availability <= capture. An extension
past PR4C4's boundary yields `IDENTITY_BOUNDARY_NOT_QUALIFIED`, including a later
instant on the same day. To qualify at a later boundary, supply a newly successful
PR4C4 result and its exact original witness covering that boundary. PR4C5 neither
recaptures identity evidence nor silently extends it.

Let S be the oldest selected period start, A the explicit baseline anchor and B
the derived boundary. A must be at or before S. Each source independently covers
A through B, all closed action categories (including unsupported and other
basis-affecting actions), no gaps, the exact event inventory, and the same
security/class. Date-based coverage is an explicit inclusive whole-day assertion;
it is not an invented event timestamp. An empty event list is insufficient without
complete coverage. Coverage includes the interval after the latest fiscal end.

Date-only effective events on the boundary day cannot be ordered against its
intraday timestamp. Such evidence fails closed. Two events on one date require
explicit distinct effective instants; equal instants and mixed date/timestamp
precision on one day return `EVENT_ORDER_UNRESOLVED`. Parsed chronological
comparison also preserves ordering within one second. Hash order chooses only a
citation among economically identical notices, never event chronology.

## Events and denomination epochs

Split ratios are exact positive integer `new_units` / `old_units` terms with
explicit orientation. Forward 2/1 and 3/2, reverse 1/5, and large integer ratios
are supported when all remaining evidence agrees. Zero, negatives, bools and
floats are malformed. Unknown orientation, missing terms, direction mismatch,
unresolved structure, or equal units fail qualification. Canonical ratios use
integer GCD reduction solely for semantic identity; original terms remain in
source bytes and considered evidence. There is no cumulative ratio.

Each notice has a lifecycle (`ANNOUNCED`, `APPROVED`, `EFFECTIVE`, `CANCELLED`)
and separate explicit `AMENDS` / `SUPERSEDES` relationships. Notices are complete
claims, not patches. Relationships require an existing notice for the same event,
strictly earlier recording chronology and an acyclic graph. Multiple unresolved
terminal meanings conflict; later recording time alone never chooses a winner.
Explicit corrections replace a prior notice's claims while retaining its bytes
and exclusion identity. A cancellation cannot erase confirmed implementation
anywhere in the supplied event history. Announced/approved events and a passed
scheduled date cannot create an epoch.

An effective pure split requires explicit implementation, known effective
chronology, same-security/class continuation, pure structure and no fractional
cash settlement. An unresolved relevant proposal blocks. A future proposal can
be informational under complete coverage, as can an explicitly never-implemented
cancelled event. Neither can be claimed incorporated into reported EPS. A claimed
implementation in the future conflicts. Explicitly known events before the
baseline remain retained and are represented by that anchor; an event on the
baseline date with unresolved ordering blocks.

Epochs preserve baseline -> effective split -> successor, in evidenced order.
A forward split followed by its numerical inverse still creates two distinct
successors; a reused basis anchor is a conflict. A split changes denomination
without asserting a new legal security. There is no lifetime corporate-action
graph or generalized restructuring engine.

## Filing-specific basis and five period decisions

Each `ObservationReference` binds exact period start/end, version ID and
observation ID. Every observation in every retained filing version must appear in
each mandatory complete snapshot. Disclosures can enumerate multiple references,
but there is no representative-only, annual-only or later-filing inheritance.
References outside the exact upstream lineage raise a contract error.

A `ReportedEPSBasisEvidence` separately identifies its security/class, reported
basis and per-event `INCORPORATED`, `NOT_INCORPORATED` or `UNRESOLVED` treatment.
Missing treatment is never treated as not incorporated. All material effective
events require treatment on every observation, consistent with the ordered epoch
prefix. Explicit basis and treatment contradictions fail. Known earlier epochs
produce `BASIS_NORMALIZATION_REQUIRED`; unknown basis produces
`REPORTED_BASIS_UNRESOLVED`. Mixed known bases remain visible. A post-fiscal-year
split is part of the target, and earlier observations must explicitly already use
that target denomination. The qualifier never divides their values itself.

Every structurally valid resolved five-period input returns five immutable
`PeriodShareBasisDecision` records, including on economic/evidence failures.
They retain the original exact Decimal object, exact periods, annual support,
complete version IDs and observation lineage, explicit reported-basis records,
considered event evidence, candidate basis, compatibility and blockers. Blockers
include overall gates conservatively. On any overall failure, qualified target
fields are `None` in both the qualification and all five decisions. Separately
named candidate/epoch fields are diagnostic only.

Overall outcomes are `COMPARABLE_BASIS_ESTABLISHED`, `BASIS_UNAVAILABLE` and
`BASIS_UNSUPPORTED`. Stock dividends, class conversions, recapitalizations,
merger/security exchanges, spin-offs, redenominations, unusual consolidations,
other basis-affecting actions and associated restructurings return unsupported.
Cash settlement of fractional entitlements is also unsupported. Depositary
structures, multiple economic classes, dual listings and sequential exchange
migrations cannot pass the unchanged PR4C4 profile. Historical mode returns
`HISTORICAL_BASIS_UNSUPPORTED` with five decisions and no qualified target.

## Hashes, authority and global design boundary

All SHA-256 identities are domain-separated by contract, qualifier and hash
purpose. Semantic hashes bind upstream economic identity, outcomes, reasons,
baseline and the entire ordered epoch chain, canonical event meaning and reported
basis/treatment meaning. Evidence hashes additionally bind original Decimal
representation, full upstream objects and witness, exact source identities,
chronology, references, coverage, corrections, conflicts and exclusions.
Evidence ordering and exact duplicates do not change semantics. Economic event
ordering remains material. No binary64 or Decimal-context normalization occurs.

The only authority is `SYNTHETIC_TEST_ONLY`. Every returned result carries
`SYNTHETIC_EVIDENCE_ONLY`. Every upstream production blocker is preserved,
including `SPLIT_BASIS_NOT_ESTABLISHED` and
`ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`. Synthetic success establishes no real
security identity, split evidence, filing presentation, publication/availability,
historical PIT, economic comparability or investment admission.

The module's only application dependencies are existing PR4C3 and PR4C4.
Jurisdiction-specific series validation and identity replay live in the explicit
profile helper. Core share-basis records use security/class anchors, observations,
periods, coverage, actions and denominations; they do not encode CIK, SEC forms,
US-GAAP or U.S. venues as universal economic concepts. Future jurisdiction adapters
can produce equivalent concepts. No such adapter is implemented here.

There is no I/O, clock/environment access, provider import, market-data inference,
real SEC acquisition, model input or downstream production consumer. The public
API cannot accept price, share-count, weighted-average-share, alias, ticker-change,
quality, durability, allocation or portfolio inputs.

## Validation

Python 3.12.14 and all 33 unchanged `requirements.lock` pins were verified.
Every test command uses `scripts/run_isolated_tests.py`, which copies code only,
uses disposable state and HOME, strips credentials and denies socket connections.

The focused matrix includes all requested split/lifecycle/coverage cases,
correction cycles, each unsupported action, exact witness and hash tampering,
source bytes/locator/chronology, complete cross-form lineage at every position,
large integer ratios, nonpositive and high-precision Decimals, strict mutable/
subclass boundaries, semantic/evidence stability, and static/runtime capability
guards. Review added regressions for fractional-second ordering and attempts to
incorporate cancelled/future proposals.

| Isolated scope | Passed | Test duration |
| --- | ---: | ---: |
| PR4C5 share basis | 127 | 2.092 s |
| PR4C4 security identity | 84 | 0.876 s |
| All SEC | 151 | 3.555 s |
| Expected Return | 144 | 1.100 s |
| PIT | 40 | 549.933 s |
| Runtime isolation | 29 | 40.683 s |
| Validation identity | 19 | 0.538 s |
| PR2 equivalence | 1 | 0.179 s |
| Complete isolated suite | 1504 | 586.147 s |

Both targeted PIT and full-suite runs reproduced all 64 equivalence cases and
both exact fingerprints below. No expected value was regenerated. All runs
exited successfully. The executable source and tests were checked byte-for-byte
against the full-suite sandbox; only this validation record changed afterward.
Logs are retained at `/private/tmp/pr4c5-*.log`. Working-tree, staged and HEAD
whitespace checks are required before push.

Reproduced unchanged aggregate PIT fingerprint:
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`.
Reproduced unchanged determinism fingerprint:
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`.
`MODEL_RULES_VERSION`: `2026-08-23-allocation-room-integrity-v7`.

No real acquisition/provider request, positive-capital analysis, operational
Expected Return, allocation, portfolio, production, deployment or Chromebook
work occurred. Network use is limited to the requested Git/PR workflow. The PR
base is `model-v2/expected-return-challenger`; merging and deployment are not part
of this change.
