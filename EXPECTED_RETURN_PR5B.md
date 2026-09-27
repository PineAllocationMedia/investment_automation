# PR5B — Narrow CURRENT security and EPS qualification

> PR5B qualifies one closed CURRENT SEC/Nasdaq ordinary-common route. It is
> not final economic admission, historical-as-of authority, comparable share-
> basis authority, accounting-subject authority, quote authority, price, or an
> Expected Return input.

## Approved base and scope

After `git fetch origin`, the approved integration ref
`origin/model-v2/expected-return-challenger` was exactly:

| Item | Verified value |
| --- | --- |
| Base commit | `7e0b7a492337414e07087ed025d0e9217d50f53d` |
| Base tree | `5abc8ef57a3cf59006677dbefb7b0aac3268111a` |
| Implementation branch | `codex/v2-pr5b-current-security-eps-qualification` |

The worktree and index were clean before the branch was created from that exact
remote commit. Divergent local refs were preserved.

This PR adds one deterministic, read-only downstream qualifier:

- `economic_facts/sec_current_security_eps_qualification.py`;
- `tests/sec_current_security_eps_qualification_fixtures.py`;
- `tests/test_sec_current_security_eps_qualification.py`;
- this contract.

Existing tests receive only narrow dependency-boundary allowlist entries for
the new downstream consumer. No upstream production module, source acquisition
contract, model rule, Expected Return calculation, runtime path, V1 behavior,
roadmap, decision log, dependency, deployment, or production configuration is
changed.

## One exact capability

PR5B answers one bounded question:

> Under one freshly replayed CURRENT boundary T, does the controlled SEC and
> Nasdaq evidence positively establish one route-local issuer, one selected
> direct Nasdaq ordinary-common security, affirmative relevant-common-class
> coverage, and applicability of every retained C3 diluted-EPS filing version
> to that supported route?

The positive result closes Property 4A through 4E for this exact route only.
For Property 4H it establishes only filing-local source correspondence over the
selected observations. It does not establish durable legal/economic continuity
or absence of corporate actions.

```text
CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED
!= FINAL_ECONOMIC_ADMISSION
!= comparable share basis
!= one accounting reporting subject
!= quote currency or per-share unit
!= observed price
!= complete listing inventory
!= HISTORICAL_AS_OF authority
```

## Public API

```python
qualify_sec_current_security_eps(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentSecurityEPSQualificationRequest,
) -> SecCurrentSecurityEPSQualification
```

The frozen/slotted request contains exactly one field:

- `temporal_source_series_request: SecTemporalCommonStockSourceSeriesRequest`.

It contains no caller CIK, ticker, exchange, class ID, security ID, issuer ID,
qualification boolean, completeness assertion, prebuilt upstream assessment,
economic-admission assertion, bytes, URL, callback, clock, or model input.

All six public arguments require their exact declared types. Caller-provided
subclasses or structurally similar objects do not extend the authority surface.

## Mandatory fresh replay

The qualifier freshly replays the approved source graph. A normal supported
call invokes D4D3B, which in turn freshly replays D4C2 and every selected D4D3A
observation and their D1-D4 dependencies. No prebuilt result can bypass that
path.

A narrow D4C2 preflight exists only so an actually captured but unsupported
D3A/D3B taxonomy profile can return the frozen typed
`UNSUPPORTED_QUALIFICATION_PROFILE` result instead of escaping as an untyped
downstream construction error. It does not select a winner or supply a positive
qualification. Supported calls still require the complete fresh D4D3B replay.

There is one exact boundary:

```text
T = fresh D4D3B.current_authority_boundary
```

Every retained source capture used by the qualification must be controlled on
or before T. Later evidence cannot repair the decision at T. Receipt capture
time, SEC acceptance time, fiscal-period dates, caller order, and wall-clock
time are never substituted for T.

## Closed final statuses

The frozen status vocabulary is:

- `CURRENT_SECURITY_EPS_QUALIFICATION_ESTABLISHED`;
- `QUALIFICATION_BLOCKED`;
- `SOURCE_CONFLICT`;
- `UNSUPPORTED_QUALIFICATION_PROFILE`;
- `UPSTREAM_CURRENT_AUTHORITY_UNAVAILABLE`.

Every non-positive result retains typed component states, a sorted issue set,
upstream evidence available at the failure boundary, deterministic identities,
and the same explicit limitations. It emits no route-local issuer or security
key and no qualified blocker.

A positive result alone emits the exact typed tuple:

```text
(AdmissionBlocker.SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED,)
```

This records route-specific qualification evidence for PR5E. It does not mutate
the C3 blocker tuple or perform final admission.

The issue vocabulary distinguishes, among other conditions:

- unavailable CURRENT or C3 authority;
- boundary or CIK disagreement;
- D4C2 ambiguity or unsupported listing route;
- D4D3A/D4D3B source conflict;
- unsupported or ambiguous participation rights;
- missing affirmative relevant-class coverage or a competing common class;
- D3B conflicts, absent EPS correspondence, or dimension ambiguity;
- an uncontrolled, omitted, period-mismatched, or value-mismatched C3 version;
- post-T evidence, unsupported taxonomy, unsupported instrument, and extraneous
  selected evidence.

No latest, earliest, majority, duplicate-count, or caller-order rule resolves a
conflict.

## Route profile

The only positive profile is
`SEC_NASDAQ_CURRENT_ORDINARY_COMMON_EPS_QUALIFICATION_V1`.

It requires:

1. one positive controlled C3 reported diluted-EPS series;
2. one positive D4D3B temporal source series under the same CURRENT boundary;
3. one exact positive D4C2 direct Nasdaq candidate;
4. exact agreement on issuer CIK, source symbol, and all upstream identities;
5. an ordinary residual common participation profile supported in every
   selected filing-local source scope;
6. affirmative route-local relevant-common-class coverage in every selected
   filing;
7. exact source correspondence for every retained C3 filing version; and
8. no contradictory, competing, dimensioned, mixed, post-boundary, unsupported,
   or extraneous selected evidence.

The selected instrument must be direct common stock. ADS/ADR, preferred,
convertible, unit, warrant, fund, partnership, trust, and other profiles remain
unsupported.

## Property 4A — route-local issuer

The positive route requires exact agreement among the C3 Companyfacts issuer,
D4C2 SEC association and filing evidence, D4D3A/D4D3B observations, and every
D3B capture. The resulting issuer key is deterministic and route-local.

It is not a global entity identifier, LEI mapping, cross-market issuer master,
or proof of accounting-subject continuity.

## Property 4B — route-local security and listing

One exact D4C2 candidate must bind the controlled SEC registered-security claim
to one non-test Nasdaq row by CIK, symbol, and the closed `NASDAQ` / `Nasdaq`
exchange profile. The resulting security key is deterministic and route-local.

This proves only the selected direct CURRENT source route. It does not prove a
complete listing inventory, ticker permanence, historical venue continuity,
quote currency, quote unit, or durable global security identity.

## Property 4C — ordinary common participation

PR5B interprets only a finite exact source grammar. After canonical whitespace
and case normalization, every selected filing must contain:

- the approved dividend-distribution sentence, explicitly subject to prior
  preferred-stock rights; and
- the approved liquidation sentence, explicitly after debts, liabilities, and
  preferred-stock preferences, with ratable participation in residual assets.

The exact one-vote-per-share sentence and exact no-redemption/no-conversion/no-
sinking-fund sentence are optional supporting statements. The latter is a
supported negative right, not a negative economic conclusion.

Unknown topic-bearing rights language is not interpreted. Missing required
language is unsupported; additional or conflicting participation language is
ambiguous. Topic anchors, section headings, a `COMMON STOCK` title, or a matched
source scope alone never establish ordinary residual participation.

This is a deliberately narrow source-language profile, not a general legal-
rights interpreter.

## Property 4D — affirmative relevant-class coverage

Coverage is positive evidence, not silence about a second class. For every
selected filing, PR5B requires:

- exactly one relevant D3A common-stock relationship matching the D4C2
  candidate and the filing-local D4D3A source scope;
- inspection of all captured D3A registered-security claims in that selected
  filing;
- no competing observed common class, ambiguous common relationship, or
  contradictory symbol/exchange relationship;
- a successful D3B extraction under the supported taxonomy profile;
- an affirmative undimensioned/all-class common-shares-outstanding source
  claim; and
- no dimensioned or mixed dimensioned/undimensioned EPS evidence.

A dimensioned shares fact is not affirmative all-class coverage. A filing that
contains another observed relevant common class blocks the route even if the
selected class otherwise matches. Duplicate equivalent captures enrich evidence
but do not vote away a conflict.

This coverage conclusion is filing-local and route-local. It is not a complete
issuer-wide, U.S.-wide, global, or historical class inventory.

## Property 4E — retained-version EPS applicability

Every retained C3 filing version must be accounted for individually. For each
version PR5B requires:

- exact accession, form, and filed-date correspondence to controlled D2B/D4B
  evidence;
- a controlled D3B capture on or before T;
- exact issuer CIK agreement;
- exact fiscal duration start and end dates;
- exact Decimal-equivalent diluted-EPS value agreement;
- undimensioned supported diluted-EPS semantics; and
- successful 4C and 4D qualification for the selected route.

The output retains the C3 version semantic identity, every C3 observation ID,
D3B claim and assessment semantic/evidence identities, and every matching source
occurrence ID. An agreeing 10-K/A is not collapsed into the original 10-K.
Omitting one retained version blocks qualification.

Class-specific or mixed dimensioned/undimensioned EPS is ambiguous under this
profile and blocks. PR5B does not normalize EPS, reinterpret numerator
entitlement, transform share basis, or choose among competing values.

## Property 4H — bounded source correspondence only

The positive result can state that the selected filing-local source
correspondence covers the retained observations under T. It cannot state:

- uninterrupted legal or economic class continuity;
- ticker permanence;
- absence of splits, stock dividends, conversions, mergers, reorganizations,
  recapitalizations, or other corporate actions;
- common share-denomination continuity;
- rights effectiveness throughout the interval; or
- one accounting reporting subject.

Those limitations are explicit in every result. PR5C remains responsible for
positive no-transformation share-basis and reporting-subject qualification.

## Deterministic identity and provenance

The qualifier uses domain-separated canonical projections for deterministic
semantic and evidence identities.

Semantic identity contains the decision-relevant source meaning, statuses,
issues, route-local keys, participation conclusion, coverage conclusion, and
per-version applicability decisions. It excludes evidence-only receipt,
occurrence, and assessment-evidence identities.

Evidence identity additionally commits to the complete retained evidence
projection. Therefore:

- caller permutation does not change either identity;
- an equivalent recapture preserves semantic identity;
- that recapture changes evidence identity; and
- conflicting recaptures remain visible and cannot create a positive majority.

The deterministic route-local keys are meaningful only within this contract and
profile. They are not promoted to a universal security master.

## Exact discharged blocker and retained blockers

A positive PR5B result discharges only the C3 blocker:

- `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED`

and only for the exact C3 series, selected CURRENT evidence graph, and route
represented by the result. It does not mutate C3 or remove that blocker globally.

The following remain for later reviewed chantiers:

- PR5C: `SPLIT_BASIS_NOT_ESTABLISHED` and
  `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED` through positive no-transformation
  share-basis and reporting-subject qualification;
- PR5D: controlled observed price, quote currency/per-share unit, dividend or
  nonpayer state, supported ordinary-compounder profile, and governed real-root
  policies;
- PR5E: exact snapshot-coverage closure, upstream-evidence closure, final
  economic admission, and adaptation into the existing Expected Return path.

Offline acquisition authentication and observed-availability semantics remain
governed by D1. HISTORICAL_AS_OF remains unsupported.

## Explicit limitations and nonclaims

Every result carries these limitations:

- no final admission;
- no share-basis qualification;
- no reporting-subject qualification;
- no quote currency or quote unit;
- no price;
- no Expected Return;
- no durable global ID;
- no complete listing inventory;
- no historical-as-of authority; and
- source correspondence only for Property 4H.

The module is not imported by model, portfolio, runtime, health-check, V1, or
production-authority paths. It performs no network acquisition, persistence,
automatic model change, deployment, promotion, or investment action.

## Supported and unsupported cases

Supported cases are restricted to controlled fictional or real-source-shaped
evidence satisfying every requirement above, including 365/366-day C3 periods,
supported D3 taxonomies, direct Nasdaq ordinary common stock, exact finite rights
language, affirmative all-class coverage, and undimensioned diluted EPS.

Unsupported or blocked cases include, without implying an exhaustive global
taxonomy:

- historical-as-of requests;
- unsupported D3 taxonomy or filing-source profiles;
- ADS/ADR, preferred, convertible, unit, warrant, fund, partnership, trust, and
  indirect listing structures;
- multiple or conflicting direct listings;
- multiple, competing, or incompletely covered common classes;
- class-specific or mixed EPS dimensions;
- missing, omitted, late, extraneous, mismatched, or conflicting retained
  source evidence;
- legal-right language outside the exact reviewed profile;
- ticker/class transitions, reorganizations, and basis/subject events; and
- any route requiring currency, price, corporate-action, reporting-subject, or
  final-admission authority.

Unsupported means that this contract refuses authority. It does not mean the
issuer or instrument is economically unsuitable.

## Regression expectations

The PR5B suite must cover:

- the exact positive five-period route, including an agreeing amendment;
- mandatory fresh replay and request-surface closure;
- exact immutable output records and limitations;
- missing, generic, ambiguous, and optional supported rights language;
- competing common classes and non-affirmative class coverage;
- class-specific and mixed-dimension EPS;
- retained-version omission, period mismatch, value mismatch, and post-T
  evidence;
- unsupported source taxonomy and unsupported instrument profiles;
- boundary, CIK, D4C2, and recapture conflicts;
- duplicate source observations and evidence enrichment;
- caller-permutation and semantic/evidence identity invariants; and
- static dependency boundaries excluding model/runtime/V1 authority.

Adjacent C3/D3/D4, identity, source-authority, runtime-isolation, protected PIT,
protected determinism, and full isolated-suite regressions must remain green.

All fixture issuers, filings, prices, values, and source text are synthetic.
Passing synthetic tests proves contract mechanics only; it is not real-data
authority and does not promote V2.

## Model and production boundary

This PR intentionally leaves `MODEL_RULES_VERSION` unchanged. It changes no
investment rule, threshold, ranking, allocation, portfolio-room logic, V1
behavior, production behavior, deployment state, or owner authority.

Merging, deployment, production promotion, and any investment-philosophy change
remain owner decisions outside this PR.

## Validation results

Validation was run with the repository-pinned Python 3.12.14 environment and
the disposable isolated runner where applicable:

- focused PR5B: 28 tests passed;
- isolated adjacent SEC C3/D3/D4 source chain: 790 tests passed;
- isolated Nasdaq source chain: 89 tests passed;
- identity, source-authority, CURRENT-authority, runtime-isolation, validation-
  identity, investment-equivalence, and health-check boundaries: 170 tests
  passed;
- complete isolated suite: 2,346 tests passed;
- Python compilation and `git diff --check`: passed;
- protected PIT fingerprint:
  `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- protected determinism fingerprint:
  `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- `MODEL_RULES_VERSION` remains
  `2026-08-23-allocation-room-integrity-v7`;
- the frozen V1 source proof remains commit
  `c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
  `26a69bb0b2185ab141af0763da2d965602c8346b`; and
- no V1-sensitive or production-runtime file changed.
