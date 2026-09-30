# PR4C4 — Synthetic security identity qualification

PR4C4 binds a resolved fictional PR4C3 issuer EPS series to one explicitly
evidenced fictional ordinary-common-share security and one direct U.S. listing.
It establishes contract mechanics only. It establishes no real security identity,
share basis, economic comparability, publication/availability, historical PIT,
or Expected Return admission.

## Verified starting state

After `git fetch origin`, authoritative V2 was
`65b9b1f2d48436e1e58f20dc77db724ce9a831ff`, tree
`8b6da80f88e1979309e4a056adc2ef087c100dc4`. V1 `origin/main` remained
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`.

The clean local checkout was `codex/v2-sec-eps-series-resolver` at
`6733cb591d02b5061e3a6120a08c3518806ac583`, with the exact authoritative V2 tree.
The implementation branch `codex/v2-security-identity-contract` was created
directly from the verified remote V2 commit. Local `main` at
`abc37bd52c24b2d68adf8138e57625327a3251b7` and local integration at
`c5fc27c82c29c2a6027eccee245098c4a072fdf1` were left untouched.
The PR base is `model-v2/expected-return-challenger`; no merge is authorized.

## Scope and public API

```text
qualify_security_identity(
    series: ResolvedAnnualDilutedEPSSeries,
    request: SecurityIdentityRequest,
    evidence: SyntheticIdentityEvidenceBundle,
) -> SecurityIdentityQualification
```

The module uses standard library and upstream PR4C3 types/version constants only.
It performs no I/O, acquisition, environment/clock reads, or model computation.
Original PR4C4 added four files: this document,
`economic_facts/security_identity.py`, `tests/security_identity_fixtures.py`,
and `tests/test_security_identity.py`. The PR4C4.1 correction described below
modifies only those four files.

Version identities:

| Constant | Value |
| --- | --- |
| `IDENTITY_CONTRACT_VERSION` | `2026-09-12-security-identity-contract-v1` |
| `IDENTITY_QUALIFIER_VERSION` | `2026-09-12-single-common-class-identity-qualifier-v2` |
| `SYNTHETIC_EVIDENCE_VERSION` | `2026-09-12-synthetic-security-identity-evidence-v1` |
| `EXTRACTION_VERSION` | `2026-09-12-synthetic-identity-claims-v1` |

## Closed synthetic evidence and trust boundary

All input/result records are frozen/slotted dataclasses with immutable tuples.
The qualifier recursively checks exact types, including nested upstream records;
subclasses, mutable containers, string substitutes for enums, and bool substitutes
for scalars cannot enter through the typed boundary. Malformed inputs raise
`IdentityContractError`. Missing or unsupported economic identity evidence returns
a closed unsuccessful qualification rather than a confidence score.

Each `SyntheticSourceEvidence` contains source reference/version/kind, locator,
extraction version, publication/availability/capture assertions, exact bytes,
SHA-256, and a typed `IdentitySnapshot`. The bytes must decode to exactly:

```text
{
  "schema_version": SYNTHETIC_EVIDENCE_VERSION,
  "claims": <exact projection of the typed IdentitySnapshot>
}
```

The sole locator is `/claims`. The qualifier verifies SHA-256 and exact decoded
claim correspondence, rejecting unknown fields, duplicate JSON keys, nonfinite
JSON and mismatched locators. JSON whitespace/key order may vary; exact source
byte identity then changes. No free-form claim dictionary, caller validity
boolean, alternate extraction version or real authority value is accepted.

Unordered applicability ID sets and inventory members are normalized only for
comparison/deduplication. Repeated security claims with the exact same economic
core can add secondary identifiers without changing identity. Exact input bytes
and the original typed claims remain unchanged and bound in source evidence.

Source references use `synthetic:document:<key>`. Stable issuer/security/listing
anchors have separate `synthetic:issuer:`, `synthetic:security:` and
`synthetic:listing:` namespaces. The complete relationships must appear in the
checked source payload. Selection targets in the request are not proof.

This is not source authentication: callers supply fictional bytes and fictional
chronology. Hashes prove consistency with those bytes, not external truth. The
input PR4C3 object is an upstream result, not a cryptographically unforgeable
capability. PR4C4 checks its version, resolved/current status, supported semantics,
five-period and filing/observation inventories, required blockers, authority
consistency, and exact request/hash linkage. It does not reread the SEC archive or
recompute PR4C3's evidence hash from extraction/decisions unavailable in the series
object. The full supplied series is additionally bound into PR4C4 evidence identity.

There is exactly one authority: `SYNTHETIC_TEST_ONLY`. Every returned result,
including historical/other failures, carries `SYNTHETIC_EVIDENCE_ONLY`. There is
no real-admission enum, caller authority switch, adapter, or production consumer.

## Complete snapshots and qualification time

Every document is a mandatory complete snapshot for the same requested scope.
Every snapshot must independently pass every gate. Multiple incomplete snapshots
cannot be stitched into a passing one, and later evidence never wins over a
conflict. Unknown/unrelated claim fields are not silently excluded. All supplied
source identities enter evidence lineage; exact duplicate records are deduplicated.

For `CURRENT_SNAPSHOT`:

```text
qualification_as_of = max(
    PR4C3.authority_as_of,
    captured_at of every mandatory source snapshot,
)
```

This uses parsed chronological UTC values, not lexicographic timestamp ordering.
Timestamps must already be canonical UTC `Z` strings, with either no fractional
seconds or six fractional digits when present. The explicit source chronology
must satisfy `published_at <= available_at <= captured_at`. This validates
fictional chronology shape/order; it does not qualify real publication or PIT
availability. A request has no `as_of` field. No evidence is backdated.

Every mandatory snapshot must establish the selected current state on the UTC
date of the derived boundary. A later mandatory capture can invalidate an expired
state. It cannot preserve the earlier eligibility result. No ignored later
document is used to advance time. An empty bundle is unavailable.

Effective intervals contain canonical ISO dates, inclusive at both ends. They
retain date precision and are never converted into invented effective timestamps.
Issuer, security, common-class inventory and listing inventory cover the entire
interval from the earliest EPS period start through the derived boundary date.
The selected listing itself must be active at that boundary. Its listing history
is covered by the explicit inventory; a first listing need not predate every EPS
period. Expiry, future-only listing states and gaps in required continuity fail.

`HISTORICAL_AS_OF` deterministically returns `HISTORICAL_IDENTITY_UNSUPPORTED`
after request/upstream shape validation, without inspecting the evidence bundle,
returning identities, or producing a qualification boundary. Describing prior
effective intervals from a current synthetic source is not historical knowledge.

## Identity levels and class inventory

`IssuerIdentity` contains an explicit issuer anchor, exact CIK matching PR4C3,
effective interval and source lineage. Descriptive names are retained, but never
matched or used in semantic issuer/security identity.

`SecurityIdentity` contains a stable security anchor, issuer anchor,
`ORDINARY_COMMON_EQUITY`, exact legal/economic common-class designation,
participation state, effective interval, optional secondary identifiers and
source lineage. V1 requires one unchanged security state spanning the five EPS
periods through the current boundary. Security changes and conflicting states
cannot be bridged. Reorganization/successor claims explicitly return unsupported.

`CommonClassInventory` explicitly enumerates classes, issuer, interval and
`COMPLETE_WITHIN_INTERVAL` coverage. A lone ticker/security does not imply a
complete inventory. Missing/incomplete inventories fail. Multiple distinct common
classes, including A/B/C with equivalent-looking economics, are unsupported.
Unresolved or different participation rights block the positive profile.
Identical duplicate class records do not manufacture a second economic class;
contradictory records with the same class key remain conflicting evidence.

Only direct ordinary common equity is supported. Preferred equity, funds,
partnership units, warrants, options, convertibles, depositary receipts, ADSs,
ADRs, CDRs, composite and unknown instruments cannot be coerced into common equity.
All depositary structures are unsupported, including a descriptive 1:1 assertion.
There is no ratio field, ratio calculation or share-basis processing.

## Listing identity, migration and rename

`ListingIdentity` contains a stable listing anchor, security anchor, explicit
venue, symbol, USD quote currency, `MAJOR_CURRENCY_UNIT`, effective interval and
source lineage. The closed first venue allowlist is `MIC:XNYS` and `MIC:XNAS`.
This is a synthetic scope rule, not a live venue/security validation service.
Missing venue/currency/unit information blocks. Explicit out-of-profile venues,
non-USD currencies and minor quote units return unsupported profile reasons.

An explicit complete `ListingInventory` must enumerate every listing anchor in
the source snapshot. Simultaneous distinct listing relationships are
`DUAL_LISTING_UNSUPPORTED`; the requested preferred listing cannot hide another.
Sequential distinct listing/venue relationships are
`LISTING_MIGRATION_UNSUPPORTED`, even when the requested listing is current.
V1 conservatively rejects these relationships anywhere in the supplied inventory.

A symbol rename is supported only on the same security/listing/venue, with
nonoverlapping adjacent date intervals and an exact `SymbolContinuity` record for
every transition. Missing/extra continuity assertions, overlap or gaps fail.
The current symbol is selected by effective dates, never evidence order. A rename
does not alter security semantic identity; it changes the listing-state semantic
identity. Same symbol with a different security anchor/class cannot preserve
economic security identity.

Legacy aliases, suffix inference, company-name matching, discovery deduplication,
portfolio representation, quote providers and FX logic are not imported or read.
They were inspected before implementation and are unchanged.

## Complete EPS applicability

Each complete snapshot must contain one resolved applicability claim per required
PR4C3 period. It binds exact series semantic/evidence hashes, period boundaries,
security/class, the entire comparable filing-version ID set and every annual
supporting observation ID. `EPSApplicabilityClaim.version_ids` binds the full
PR4C3 `version_ids`; `observation_ids` binds exactly PR4C3's annual
`supporting_observation_ids`. No representative-only citation or one-year
shortcut qualifies, and the two fields have not changed meaning.

PR4C3 can retain an agreeing 8-K, 10-Q or 10-Q/A version for the exact annual
period without making its observation an annual candidate. Consequently, annual
support is a subset of the complete filing-version observation union, and that
subset may be strict. Within the current SEC profile, support must equal all
observations belonging to `10-K`/`10-K/A` versions with `reported_fp=FY`. It must
be nonempty, unique, and contain the representative observation. Version IDs must
match the complete unique version-record inventory. Every version must contain
observations, each observation must have exactly one version/period owner, and
version/observation identities must be canonical SHA-256 strings. None of these
checks selects, trims or promotes cross-form observations.

The complete supplied PR4C3 series, including every version's observations,
remains bound into identity evidence. Downstream evidence qualification can
inspect that full lineage while applicability decisions retain their separate
full-version and annual-support fields. SEC forms, CIK, US-GAAP and supported
venues remain source/profile-specific; these are not universal V2 concepts.

Missing, extra, contradictory, wrong-class, wrong-series or incomplete version/
observation coverage fails. Exactly identical claim duplicates do not create a
conflict. The successful result contains exactly five immutable
`EPSClassApplicabilityDecision` records, each with full source/version lineage.
No EPS value, unit, period, observation, decision, hash or blocker is modified.

## Outcomes, reasons and identities

Outcomes are `IDENTITY_ESTABLISHED_WITHIN_SYNTHETIC_SCOPE`,
`IDENTITY_UNAVAILABLE` and `IDENTITY_UNSUPPORTED`. Reasons are closed enums,
sorted/deduplicated deterministically. Unsupported reasons determine the overall
unsupported outcome while all other detected reasons remain visible. Every
unsuccessful result has no issuer/security/listing identity and no successful
applicability decisions. Corrupt contracts raise a fixed-category contract error.

Issuer semantic identity excludes descriptive names. Security semantic identity
binds issuer/security anchors, instrument, full common-class state and effective
interval. Secondary identifiers are retained as evidence attributes, never
selected as an anchor. Listing semantic identity binds its complete current state.
Qualification semantic identity binds PR4C3 semantic identity, mode, targets,
outcome/reasons, successful identity semantics and five period/class bindings.
Contract and qualifier versions domain-separate every hash.

Evidence identity additionally binds the exact request, full immutable PR4C3
series, all source evidence identities, derived boundary, applicability decisions,
reasons, blockers and synthetic limitation. Each source identity binds exact byte
hash/length, source reference/locator/version, extracted claims and chronology.
Thus conflicts and every considered source remain bound even on failure. There
is no silently excluded source category in this complete-snapshot contract.

Equivalent evidence ordering has the same semantic result. Reordered exact bytes
or recapture changes evidence identity while preserving economics when the current
state remains valid. The qualifier performs no numeric EPS operation; upstream
Decimals are encoded exactly for its lineage without binary64 conversion or
context-sensitive rounding. No runtime paths, locale, random IDs or implicit
clock values enter these identities.

## Unchanged downstream boundary

All upstream admission blockers are preserved, including:

- `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED`
- `SPLIT_BASIS_NOT_ESTABLISHED`
- `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`
- `PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED`
- `SNAPSHOT_COVERAGE_ONLY`
- `UPSTREAM_EVIDENCE_ONLY`
- `OFFLINE_CAPTURE_NOT_AUTHENTICATED` when present upstream.

Synthetic identity success discharges none of these real-admission blockers.
No `ShareBasis`, PR4B1 `Identity`, `ReportedDilutedEPS`, `QualifiedFacts`, real
adapter, price or dividend is constructed. Microsoft is not used or revisited.
PR4C1/C2/C3, PR4B1, PIT and V1 behavior remain unchanged.

## Validation

Use Python 3.12 and unchanged `requirements.lock`, through the disposable
code-only runner. It strips credentials and denies socket connections. The local
Python 3.12.14 environment matched every pinned dependency; `.python-version`
remains 3.12.13, matching the existing CI configuration.

```sh
.venv/bin/python -B scripts/run_isolated_tests.py --pattern 'test_security_identity.py'
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
Unchanged `MODEL_RULES_VERSION`: `2026-08-23-allocation-room-integrity-v7`.
These are mechanical synthetic tests, not real investment evidence or tuning.

No SEC, exchange, provider-price, portfolio, Drive, Chromebook, deployment,
scheduler, real Expected Return, backtest, walk-forward or allocation operation
is part of this change. Network activity is restricted to requested Git/PR work.

### Completed validation

| Isolated runner pattern | Result | Test duration |
| --- | --- | --- |
| `test_security_identity.py` | 75 passed | 0.587 s |
| `test_sec_*.py` | 151 passed | 2.118 s |
| `test_expected_return*.py` | 144 passed | 0.598 s |
| `test_pit*.py` | 40 passed, including 64 equivalence cases | 488.771 s |
| `test_runtime_isolation.py` | 29 passed | 28.180 s |
| `test_validation_identity_isolation.py` | 19 passed | 0.304 s |
| `test_pr2_investment_equivalence.py` | 1 passed | 0.136 s |
| Full isolated suite | **1,368 passed** | **506.958 s** |

Both exact fingerprints above were reproduced in targeted PIT validation and in
the final full suite. Expected values were not regenerated. The focused tests
include byte/locator tampering, closed input types, complete period/version/
observation coverage, class/listing conflicts, stable symbol-renaming identity,
equivalent duplicate-claim ordering, secondary-identifier additions, chronology,
failure-output safety and purity/import boundaries.

The duplicate applicability/secondary-identifier regressions were first observed
failing, then passed after comparison normalization. The earlier full-suite run
was stopped and restarted so the completed full run covered the final executable
source and all 75 focused tests. Only this validation record was added afterward.
Working-tree, staged and HEAD whitespace checks passed. Locked dependencies,
upstream contracts, model rules, fixture pins and existing behavior are unchanged.

### PR4C4.1 cross-form lineage compatibility

Verified starting V2: `58c8d328d4595126879531d01e23ca1d031df905`, tree
`761eb054a11810dd7aab631980e944a55f21984d`. V1 remained
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`. The clean local branch was
`codex/v2-security-identity-contract` at
`3b8d3d7816b4609450dfb2fd77eba68bae67a7f6`, with the authoritative V2 tree.
Branch `codex/v2-security-identity-cross-form-compat` starts at the exact verified
V2 commit. Divergent local main/integration references are untouched.

Before changing code, fictional companyfacts for each of 8-K, 10-Q and 10-Q/A
reproduced a resolved PR4C3 period with two comparable versions, two observations
in their union, and one annual support observation. PR4C4 rejected each with
`IdentityContractError: Invalid upstream observation inventory` because it
incorrectly required equality of the complete observation union and annual
support. The new focused tests also failed before the correction.

The correction is confined to PR4C4 input validation and its tests/fixtures.
Annual support now remains a properly validated subset of full comparable
lineage. Applicability fields and public record shapes are unchanged. The
qualifier version advances from v1 to v2 because accepted input semantics and
validation guarantees change; contract, source-evidence and extraction versions
are unchanged. Existing hash domain separation includes the qualifier version,
so PR4C4-derived identities intentionally receive the new version domain.
PR4C3 values, hashes, annual candidacy, conflict detection and retained lineage
are unchanged.

Nine new test methods cover both 10-K and 10-K/A annual candidates against every
upstream cross-form case, missing/extra/empty/duplicate annual support,
representative membership, annual-versus-cross-form classification, complete
version IDs, malformed IDs, empty/duplicated observation ownership within or
across versions/periods, exact applicability fields, and upstream conflicts or
missing annual candidates. No share-basis or corporate-action code is added.

Validation uses Python 3.12.14 with all 33 installed locked distributions matching
`requirements.lock`, through the existing disposable runner and temporary HOME.

| Isolated runner pattern | Result | Test duration |
| --- | --- | --- |
| `test_security_identity.py` | 84 passed | 0.391 s |
| `test_sec_eps_series.py` | 52 passed | 0.800 s |
| `test_sec_*.py` | 151 passed | 2.607 s |
| `test_expected_return*.py` | 144 passed | 0.812 s |
| `test_pit*.py` | 40 passed | 555.706 s |
| `test_runtime_isolation.py` | 29 passed | 37.962 s |
| `test_validation_identity_isolation.py` | 19 passed | 0.411 s |
| `test_pr2_investment_equivalence.py` | 1 passed | 0.087 s |
| `Full isolated suite` | 1377 passed | 599.751 s |

Both targeted PIT and full-suite runs reproduced the exact aggregate and
determinism fingerprints recorded above, including all 64 equivalence cases.
Expected fingerprints and `MODEL_RULES_VERSION` remain unchanged. Working-tree,
staged and commit whitespace checks are required before push. Only this completed
validation record changed after the final suite; executable code and tests did
not change. Logs are retained at `/private/tmp/pr4c4-1-*.log`.

All validation used fictional isolated fixtures. No real SEC/provider request,
positive-capital analysis, real Expected Return, portfolio, production, Drive,
Chromebook, deployment or merge operation was performed. This correction does
not begin PR4C5 or add share-basis/corporate-action logic.
