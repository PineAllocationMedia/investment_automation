# PR4D4D3A — Bridge CURRENT common-stock class source evidence

> Same-filing common-stock source correspondence is not durable economic class
> identity, legal-right interpretation, historical continuity, complete class
> inventory, Property 4C resolution, or admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`47c28536c45b5faaf5966f9514f01b371239336b`, tree
`b5822b4625679dd1fb7aec90fc0ad566c7316a2d` (post-merged PR #60 / PR4D4D2B).
The worktree and index were clean. Branch
`codex/v2-sec-current-common-stock-class-bridge` was created directly from that
verified remote commit; stale and divergent local refs were preserved.

This PR adds one deterministic, read-only D4D3A adapter:

- `economic_facts/sec_current_common_stock_class_bridge.py`;
- `tests/sec_current_common_stock_class_bridge_fixtures.py`;
- `tests/test_sec_current_common_stock_class_bridge.py`;
- `EXPECTED_RETURN_PR4D4D3A.md`.

Existing tests may receive only narrow dependency-boundary allowlist entries for
this new downstream consumer. D3A, D4C2, D4D1, D4D2A, D4D2B, source authority,
Expected Return, investment rules, runtime, V1, roadmap, decisions, dependencies,
deployment, and production behavior remain unchanged.

## Purpose and exact question

D4D3A combines only three freshly replayed source rails:

1. D4C2 CURRENT SEC/Nasdaq registered-listing corroboration;
2. the D3A title/symbol/exchange/source-scope claim from one exact D4C2-supporting
   filing receipt; and
3. one D4D2B COMMON STOCK source scope from that exact same complete-submission
   receipt.

It answers only whether one eligible filing-local D3A title maps, under a closed
source-title grammar, to exactly one filing-local D4D2B class heading. It does
not determine the durable PAM class, ticker permanence, present legal effect,
cross-filing continuity, complete inventory, or admission.

## Public API and closed request

```python
assess_sec_current_common_stock_class_bridge(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentCommonStockClassBridgeRequest,
) -> SecCurrentCommonStockClassBridgeAssessment
```

The frozen/slotted request contains exactly:

- `registered_listing_bridge_request: SecCurrentRegisteredListingBridgeRequest`;
- `rights_claims_request: SecSection12RightsSourceClaimsRequest`.

It contains no caller CIK, ticker, title, exchange, heading, scope, identity,
candidate, boundary, rights value, qualification/admission flag, bytes, URL,
callback, or clock. Exact typed archives and request are required.

## Mandatory fresh replay

Every invocation freshly executes:

```text
assess_sec_current_registered_listing_bridge(...)
extract_sec_section12_rights_source_claims(...)
extract_sec_registered_security_claims(...rights filing receipt...)
```

No prebuilt D4C2, D4D2B, or D3A object can enter the request. The fresh D3A
assessment must agree semantically and evidentially with the D3A assessment
embedded in D4C2's freshly replayed T-bounded capture for the same receipt.
Disagreement is a source/programming conflict and is never repaired.

Archive corruption, unsupported upstream source structure, and contract or
programming errors propagate. There is no network request, write, directory
discovery, latest-receipt selection, implicit acquisition, or clock read.

## Upstream gates and precedence

D4C2 must have overall status `CURRENT_SOURCE_BRIDGE_ESTABLISHED` and exactly one
successful candidate. D4D2B must have overall status
`CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS`. Successful sub-evidence is never
cherry-picked from a fail-closed upstream assessment.

D4C2 conflict, unavailable, unsupported-profile, and no-candidate states remain
distinct D4D3A issues. D4D2B ambiguity, unsupported representation/profile,
no-scope, no-rights-passage, and upstream-unavailable states likewise remain
distinct. Conflict takes precedence over unsupported profile; unsupported takes
precedence over ordinary upstream unavailability; ordinary incompleteness never
becomes positive evidence.

## Exact CURRENT boundary and filing membership

The only CURRENT boundary is:

```text
T = D4C2.current_authority_boundary
```

D4D3A creates no other time. It does not use a wall clock, rights-receipt capture
as a replacement T, or `max(T, capture)`. A positive result requires:

- rights receipt ID in D4C2 candidate `supporting_filing_receipt_ids`;
- rights accession in D4C2 candidate `supporting_accessions`;
- rights receipt CIK exactly equal to the D4C2 candidate source CIK; and
- fresh D3A receipt/primary-document CIK and accession exactly equal to the
  rights filing receipt.

A later or otherwise nonparticipating recapture cannot repair the earlier T.
The primary Inline XBRL document and rights exhibit may be different embedded
documents; the required shared provenance is the complete-submission receipt,
accession, and CIK.

## Selected D3A claim eligibility

Fresh D3A must be `CAPTURED_REGISTERED_SECURITY_CLAIMS`. An eligible claim has:

- no claim issues;
- exactly one title;
- exactly one trading symbol;
- no `NoTradingSymbolFlag`;
- exactly one exchange;
- a nonempty `source_security_scope_id`; and
- exact exchange text `NASDAQ`.

After semantic deduplication there must be exactly one eligible relationship in
the selected receipt. Multiple incompatible relationships fail closed. The claim
must also agree exactly with the successful D4C2 candidate:

- symbol equals `source_symbol`;
- title occurs in `d3a_titles`; and
- `(accession, source_security_scope_id)` occurs in
  `d3a_filing_source_scopes`.

There is no first/latest/majority winner and no ticker-only class identity.

## Closed D3A common-stock title parser

Matching normalization performs only:

1. Unicode-whitespace collapse to one ASCII space;
2. trim; and
3. ASCII `a`–`z` to `A`–`Z`.

There is no Unicode semantic normalization, punctuation removal, arbitrary
suffix stripping, token reordering, stemming, edit distance, fuzzy matching,
synonym inference, embeddings, LLM classification, or issuer alias list.

The base is exactly:

```text
COMMON STOCK
CLASS <TOKEN> COMMON STOCK
TOKEN := one ASCII A-Z letter or 0-9 digit
```

The only optional opaque source suffixes are:

```text
, $<AMOUNT> PAR VALUE
, $<AMOUNT> PAR VALUE PER SHARE
, PAR VALUE $<AMOUNT>
, PAR VALUE $<AMOUNT> PER SHARE
, NO PAR VALUE

AMOUNT := [0-9]+(?:\.[0-9]{1,10})?
```

The amount remains source-string structure. It is never converted to `float` or
`Decimal`, compared economically, or emitted as a par-value fact. The exact
source suffix is retained opaquely. Unsupported source titles produce
`UNSUPPORTED_D3A_COMMON_STOCK_TITLE_PROFILE`; they are never approximated.

## Canonical label and exact D4D2B match

The parser yields only `COMMON STOCK` or `CLASS <TOKEN> COMMON STOCK`. Every
D4D2B `exact_class_heading` is independently normalized using the same narrow
rules. Match requires exact canonical equality.

- zero matching scopes: `NO_MATCHING_RIGHTS_CLASS_SCOPE`;
- more than one matching scope: `AMBIGUOUS_RIGHTS_CLASS_SCOPE`;
- exactly one matching scope: eligible source correspondence.

Duplicate headings remain distinct. D4D3A never chooses by source order,
filename, exhibit TYPE, heading length, passage count, topic count, proximity,
or lexical similarity.

## Rights passage provenance and noninterpretation

For the unique matched scope, D4D3A retains ordered passage semantic/evidence
IDs, source block ordinals, and the finite D4D2B source-topic set. These values
strengthen traceability only. The rights topics remain uninterpreted.

There is no `has_voting_rights`, `votes_per_share`, dividend entitlement,
preemptive-right boolean, redemption/conversion value, liquidation preference,
par-value economics, authorized/outstanding shares, transfer restriction,
anti-takeover analysis, or rights-completeness flag. An absent topic proves
nothing about an absent legal right or disclosure completeness.

## Output and deterministic identities

Frozen/slotted evidence retains the exact T, source CIK/symbol, selected receipt
and accession, D3A title/canonical label/opaque suffix/source scope and claim
identities, D4C2 candidate identities, D4D2B assessment and scope identities,
and matching passage/topic provenance.

Domain-separated SHA-256 uses:

```text
pam:sec-current-common-stock-class-bridge:{domain}:v1
```

Candidate semantics bind the contract/profile, exact T, CIK/symbol/accession,
D4C2 candidate semantics, selected D3A relationship and exact title, canonical
label and source scope, D4D2B assessment/matching-scope semantics, ordered
passage semantics, source topics, status, and issues. Candidate evidence also
binds the exact selected receipt and all upstream evidence identities.

Assessment semantics bind D4C2, D4D2B, fresh D3A, candidate semantics, status,
and issues. Assessment evidence binds the full upstream/candidate evidence.
Identical-byte recapture preserves applicable semantics while changing receipt-
bound evidence. Paths, environment, wall clock, randomness, and object identity
enter neither identity.

These hashes identify evidence objects only. There is no durable class or security identity,
`class_id`, `security_id`, `economic_class_id`, PAM identity,
or cross-filing continuity anchor.

## Positive meaning and explicit nonclaims

`CURRENT_SOURCE_CLASS_BRIDGE_ESTABLISHED` means only that, by exact D4C2 T, one
D4C2-supported filing receipt contains one eligible D3A Nasdaq title/symbol/scope
relationship whose closed canonical common-stock label equals exactly one D4D2B
COMMON STOCK source scope in the same receipt, with that scope's source passages
retained.

It does not establish issuer identity, durable security/class/listing identity,
ticker permanence, cross-filing class continuity, rights effectiveness,
complete rights or class inventory, Item 202/601 compliance, MIC, quote currency
or unit, listing interval, wrapper/ADR resolution, or admission.

## Authority, Property 4, and remaining obligations

No `AuthorityProperty`, source route, provider-wide trust, Expected Return input,
model score, allocation, portfolio/runtime consumer, V1 behavior, deployment,
production authority, or V2 promotion is added.

| Property | State after PR4D4D3A |
| --- | --- |
| 4A | Unresolved — source CIK remains source provenance, not issuer identity. |
| 4B | Unresolved — source correspondence is not durable security identity. |
| 4C | Unresolved — D4D3A adds CURRENT same-filing common-stock source correspondence evidence only; it does not qualify legal/economic class identity or rights. |
| 4D | Unresolved — matched source scope is not complete relevant class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — one CURRENT filing-local bridge is not historical continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

## Validation

Validation uses invented offline evidence and the unchanged isolated runner. It
covers exact API/request closure, fresh replay, upstream gates, exact T and
same-filing membership, D3A eligibility/agreement, the complete title/suffix
grammar, exact D4D2B matching, zero/multiple-match behavior, passage/topic
provenance, nonclaims, deterministic identities, recapture/path invariance, no
network/writes/clocks/scans, dependency direction, authority isolation, and all
adjacent/full regressions required by the implementation prompt.

Python was 3.12.14 against the unchanged repository pin 3.12.13. The dependency
health suite confirms the unchanged locked environment. Completed selections:

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_current_common_stock_class_bridge.py` | 29 | PASS / 0.879 |
| `test_sec_*.py` | 739 | PASS / 8.463 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.331 |
| `test_*authority.py` | 44 | PASS / 0.140 |
| `test_security_identity.py` | 84 | PASS / 0.396 |
| `test_expected_return*.py` | 144 | PASS / 0.461 |
| `test_runtime_isolation.py` | 29 | PASS / 28.824 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.281 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.076 |
| Complete isolated suite | **2,295** | **PASS / 444.609** |

The complete suite reported no failures or skips. It exercised all 64 protected
PIT equivalence scenarios and reproduced both protected fingerprints without
regenerating expectations. No executable code or tests changed after that full
run; only this validation record was finalized afterward.

No live source, positive-capital analysis, protected-expectation regeneration,
model-rule change, deployment, merge, or production operation is performed.
Protected expectations remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`.

Final HEAD/tree, whitespace checks, and PR URL are recorded in the published
implementation handoff after validation.

## Next handoff

D4D3A does not pre-authorize another implementation. A separate review must
choose which remaining Property 4C gap to examine next:

### A. TEMPORAL CLASS CONTINUITY

Determine whether equivalent source-class evidence can be followed across
multiple controlled filings without assuming ticker or name permanence.

### B. NARROW LEGAL-RIGHTS VALUE INTERPRETATION

Determine whether specific D4D2B passages can support bounded deterministic
legal-source assertions without over-interpreting prose.

Neither path may create durable identity or resolve Property 4C implicitly.
Merge, deployment, authority, promotion, and the next chantier remain owner
decisions.
