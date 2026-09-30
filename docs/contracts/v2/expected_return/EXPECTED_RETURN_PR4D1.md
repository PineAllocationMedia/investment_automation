# PR4D1 — CURRENT real-authority foundation

> PR4D1 establishes verifiable CURRENT source/evidence authority properties.
> It does not admit an EPS series into the investment model.

## Verified base and permitted scope

After fetch, `origin/model-v2/expected-return-challenger` was exactly
`deb98a3027d3da778cea41d4935c68cfb00c2146`, tree
`791e5e851098694cfedbd96231291bce4f821902`.
`origin/main` remained `c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`.
The initial clean checkout was `codex/pam-memory-architecture-v1` at
`a8140f666bf98e9db1d010bafd99fbd92cc46f88`, with the authoritative V2 tree.
Branch `codex/v2-current-authority-foundation` starts directly at the verified
remote V2 commit. Divergent existing local refs remain untouched.

The constitution, agent instructions, roadmap, C2–C6/B1 contracts, actual
archive/acquisition/extraction/resolution, synthetic qualifiers, Expected Return
boundary, and relevant tests were investigated. No existing source change is
required. Exactly seven files are added: three modules, their three test modules,
and this document. No `current_admission_contract.py` is created.

## Public API and dependency direction

```python
assess_sec_current_evidence(
    archive: SecArchive,
    request: SeriesResolutionRequest,
) -> SecCurrentEvidenceAssessment
```

```text
controlled stored capture
  -> unchanged archive/extractor/C3 resolver
  -> SEC route verifier
  -> SecCurrentEvidenceAssessment
       |-- original request, verified receipt, complete original C3 result
       `-- source-neutral CurrentAuthorityAssessment
```

`source_authority.py` owns the closed route table and neutral property vocabulary.
`current_authority.py` owns the neutral report and private assembly invariants.
`sec_current_evidence.py` alone interprets SEC provenance and C3 results.
None imports acquisition, synthetic qualifiers, `src`, PIT or provider code.
The adapter reads evidence only; it never captures, writes, selects archive
latest, computes EPS, or calls a model.

Public callers provide only an exact `SecArchive` and original exact C3 request.
No series, source bytes, timestamp, authority, profile, callback, URL, transport or
clock is accepted. C3 validates the request and reads/verifies receipt membership,
object length/hash, extraction and resolution. The adapter calls C3 exactly once,
then rereads the stored receipt/object to check exact route and returned linkage.
This repeats integrity reads, not C3's resolution algorithm. Corruption between
reads fails closed. No arbitrary supplied series hash is used to skip replay.

## Registered route, not provider trust

The single registered route is `SEC_COMPANYFACTS_LIVE_CURRENT_V1`. `SEC` alone is
not a route ID and cannot confer any authority. Unknown IDs, profile objects and
caller-injected profiles are rejected. Registry lookup describes powers, not proof
that a specific claim has been established.

`SourceRouteProfile` binds provider, profile version, jurisdiction metadata,
permitted typed claims with authority/role, verifier identity, exact acquisition,
capture-schema, extraction and resolution pins, immutable-capture requirement,
publication/availability semantics, PIT capability, failure policy and use status.
The SEC adapter checks these version pins against existing upstream constants.
An upstream version change requires deliberate review; it is not auto-adopted.
There are no dynamic plugins, files/config loaders, databases or provider scores.

| Identity | Value |
| --- | --- |
| Registry/encoding | `2026-09-19-source-route-authority-v1` |
| Route profile | `2026-09-19-companyfacts-current-route-v1` |
| Neutral report | `2026-09-19-current-authority-assessment-v1` |
| SEC verifier | `2026-09-19-sec-current-evidence-verifier-v1` |

### Factual versus use authority

Factual powers answer which properties this exact route can establish.
`license_status=UNKNOWN` and `use_status=REVIEW_REQUIRED` are independent review
metadata. They confer no storage, analysis, redistribution or commercial-use
permission. No legal research or new legal determination occurred.
The factual profile hash excludes use metadata; the full profile and evidence
hashes include it. A legal-status change cannot increase a claim's authority.
Conversely, verified factual provenance cannot grant commercial rights.

## Trust model

The adapter inherits C2's trusted-local-process model: reviewed code performs a
canonical HTTPS acquisition with certificate/hostname verification, no redirects
or proxies, internal capture time, and exact received-body archive publication.
This is not a remotely signed SEC receipt, secure timestamp service, or proof of
the truth of every issuer assertion. The normal local clock and archive are trust
dependencies. The existing archive is integrity checked, not tamper proof against
an actor capable of replacing it and all of its trust anchors.

The archive argument must refer to storage controlled by PAM and populated through
reviewed code. An uploaded archive or user-authored LIVE receipt is not admitted
to that trust domain. This local API cannot distinguish a completely forged
archive made by arbitrary privileged Python/filesystem operations. It adds no
second attestation layer and makes no stronger claim than C2.

Frozen dataclasses and domain-separated hashes are auditable records, not
unforgeable credentials. Constructing a report or calling a private assembly
helper does not establish external truth. No public API consumes those reports
as proof. A later gate must reconstruct/verify the original evidence through
reviewed route verifiers, not trust serialized success labels.

## Capture-bound CURRENT time

For successful LIVE resolution, exactly:

```text
current_authority_boundary = C3.authority_as_of = verified receipt.captured_at
observed_available_by      = current_authority_boundary
publication               = UNKNOWN
```

The availability value is a conservative upper bound: the response information
was observed no later than that controlled capture. It is not first publication,
an exact filing dissemination timestamp, or a historical cutoff. C2's transient
`response_completed_at` is not persisted in its receipt and is not reconstructed.
`filed` remains a date in original C3 provenance; HTTP Date/Last-Modified never
become publication timestamps. No midnight timestamp is invented from a date.

The adapter accepts no `as_of` and uses no clock. Replaying an old explicit receipt
never advances its boundary because a newer receipt exists. A new capture changes
the authority boundary and assessment identity even if economic EPS is identical.
The assessment does not assert that its snapshot is still newest at consumption.

For the future real qualification chain, every contributing source capture must
be no later than this boundary AND must establish required coverage through it.
Earlier capture alone does not prove later completeness. Later evidence requires
a refreshed and requalified upstream chain; it cannot extend an old assessment.
Future qualification creation time, if retained, is execution metadata separate
from source availability and cannot manufacture historical economic authority.

## Obligation ledger and output states

| Neutral property | Successful LIVE C3 replay |
| --- | --- |
| Source acquisition provenance | Established, under controlled local trust |
| CURRENT observed availability | Established as capture bound |
| CURRENT snapshot scope | Established, with no historical authority |
| Security/share-class/listing identity | Unresolved |
| Share-basis comparability | Unresolved |
| Economic/reporting-subject comparability | Unresolved |
| Final economic admission | Unresolved |

The adapter explicitly supplies only the three properties its code verifies;
the assembly layer also checks each against the registered route's powers.
Registry membership alone never creates the other properties. The output status
is `EVIDENCE_ESTABLISHED` or `UNAVAILABLE`; no status named `ADMITTED` exists.

All reports retain limitations: `EXACT_PUBLICATION_UNKNOWN`,
`NO_HISTORICAL_AS_OF_AUTHORITY`, `NO_ECONOMIC_ADMISSION`,
`CONTROLLED_LOCAL_TRUST_ONLY`, and `NO_FRESHNESS_BEYOND_CAPTURE`.

The upstream result is not mutated. All six LIVE C3 blockers remain exactly as
returned, including publication/availability, snapshot-only coverage and upstream
evidence-only. The offline blocker is already absent from C3's own LIVE result;
PR4D1 does not remove it or reinterpret legacy C1 inspection output.
The neutral blocker inventory preserves upstream enum values and order as strings.
The full typed C3 inventory remains in the SEC wrapper.

For OFFLINE, the original resolved series may remain inspectable, but the real
authority report is `UNAVAILABLE`, has no established claims or authority boundary,
and leaves all seven neutral obligations unresolved. An identical value or
canonical SEC source locator does not upgrade acquisition identity.

For a LIVE capture whose C3 resolution is unavailable, the conservative initial
report also establishes no claims and no authority boundary. The full extraction,
resolution reasons, decisions, capture metadata and exclusions remain inspectable.
Source authenticity is not used to rescue an unresolved EPS series. An offline
resolution failure retains both unavailability categories.

Historical requests retain C3's existing early unsupported behavior, without any
archive read, receipt, extraction, partial series or authority boundary. They do
not claim integrity verification of unread archives. Malformed requests still
fail validation before that branch.

## Exact lineage and identities

`SecCurrentEvidenceAssessment` retains the original C3 `SeriesResolutionResult`
object, not a reduced or reconstructed five-value tuple. Thus exact Decimal EPS,
periods, representative/annual supporting observations, all agreeing comparable
versions (including cross-form observations), accessions, original extraction,
resolution decisions and exclusions remain intact. Zero and negative reported
EPS are not screened out. No new winner, normalization, split adjustment or float
conversion exists.

The neutral report carries contract/route identity, typed established claims,
satisfied/unresolved obligations, boundary, availability bound, limitations,
upstream blockers, source hashes and upstream semantic/evidence hash links.
Source-neutral records require no CIK, SEC accession, form, receipt type, ticker,
U.S. venue or US-GAAP field. Those remain in the SEC wrapper's provenance.

Hashes use SHA-256, version/domain separation and exact Decimal sign/digits/exponent
encoding without context-sensitive arithmetic. Semantic identity binds factual
route powers, authority boundary, obligation decisions, limitations and upstream
economic semantics. Unordered property/source inventories are canonicalized.
Evidence identity additionally binds use metadata, exact source hashes, original
blocker order and the complete replay envelope. Wrapper semantics also distinguish
C3 failure reasons and the requested SEC scope. Reordered/reformatted equivalent
source bytes can change evidence alone. Different EPS changes semantics; recapture
changes authority semantics because this assessment is about a specific boundary.

The replay-envelope hash is explicitly distinct from the original source object
hash. No manifest hash is passed off as an SEC filing document. There are no host
paths, environment values, object addresses, randomness or implicit timestamps
in identities.

## Errors versus unavailability

Unknown routes and unpermitted claims raise `SourceAuthorityError` with closed
reasons. Malformed requests and violated verifier linkage raise
`CurrentAuthorityError`: invalid contract, archive integrity failure, malformed
source structure, route/contract mismatch, or authority-boundary mismatch.
Missing receipts and broken hashes are integrity errors, not normal weak evidence.
Unexpected programming exceptions propagate.

Factual/scope unavailability has three small reasons: unsupported acquisition
authority (offline), C3 resolution unavailable, or unsupported historical mode.
No failure returns a positive economic admission or drops original C3 diagnostics.

## Synthetic isolation and missing next qualifications

C4–C6 remain entirely synthetic. Successful identity, share-basis and comparability
objects cannot enter this API or discharge its unresolved real obligations.
Tests may mint LIVE fixture receipts privately or run C2 code with a patched
fictional transport; these are mechanical validation, not real observations.
No such fixture establishes production authority or upgrades the synthetic chain.

Next work still requires genuine sources for security/class/listing applicability,
complete corporate-action and reported-share-basis evidence, and measurement/
reporting-subject continuity. Only a later gate can join those into admitted EPS.
An independent real model adapter is later still: EPS alone does not supply price,
ordinary dividends/verified nonpayer, qualified company profile or explicit
economic assumption policies. PR4B1's synthetic adapters and required publication
timestamps are unchanged. Decimal conversion belongs only at final model adaptation.

The evidence foundation supports PAM research, comparisons, screeners, monitoring
and portfolio intelligence, independently of any eventual investment-model use.

## Validation and preserved identities

Python 3.12.14; all 33 installed packages match unchanged `requirements.lock`.
The repository pin remains Python 3.12.13. All tests run through the unchanged
`scripts/run_isolated_tests.py`: disposable code/state, temporary HOME, stripped
credentials and network denied. No real provider or application analysis runs.

Protected identities verified unchanged:

- PIT aggregate: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- PIT determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

Focused validation uses `--pattern` with the following exact test selections:

| Selection | Tests | Result |
| --- | ---: | --- |
| `test_source_authority.py` | 11 | PASS |
| `test_current_authority.py` | 17 | PASS |
| `test_sec_current_evidence.py` | 41 | PASS |
| `test_sec_acquisition.py` | 43 | PASS |
| `test_sec_fact_archive.py` | 28 | PASS |
| `test_sec_diluted_eps.py` | 28 | PASS |
| `test_sec_eps_series.py` | 52 | PASS |
| `test_security_identity.py` | 84 | PASS |
| `test_share_basis.py` | 136 | PASS |
| `test_reporting_subject.py` | 77 | PASS |
| `test_expected_return*.py` | 144 | PASS |
| `test_pit*.py` | 40 | PASS |
| `test_runtime_isolation.py` | 29 | PASS |
| `test_validation_identity_isolation.py` | 19 | PASS |
| `test_pr2_investment_equivalence.py` | 1 | PASS |

The 15 focused selections total 750 passing tests, including 69 new PR4D1 tests.
The PIT selection passed in 998.432 seconds and reproduced the protected aggregate
over all 64 equivalence scenarios plus the protected determinism fingerprint.
The complete isolated suite passed: **1,659 tests in 1,086.267 seconds**, with no
failures or skips reported. It independently reproduced both protected fingerprints.
All six new Python files were byte-identical to the full-suite sandbox snapshot;
only this validation record was completed afterward. `MODEL_RULES_VERSION` is
unchanged. The only runtime note is Python 3.12.14 versus the unchanged 3.12.13
repository pin; no dependency or runtime configuration was edited.

Whitespace validation covers `git diff --check`, `git diff --cached --check`, and
post-commit `git show --format= --check HEAD`. The final commit adds only the seven
permitted files; it changes no pre-existing tracked file. There is no scope deviation.

No upstream, ER, PIT, runtime, investment, portfolio, deployment, dependency or
V1 file changes. No merge, deployment, positive-capital analysis, live provider
call, repository-setting change or Chromebook action is authorized by this PR.
