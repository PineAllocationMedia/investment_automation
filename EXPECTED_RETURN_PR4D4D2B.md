# PR4D4D2B — Extract class-scoped Section-12 rights source claims

> A rights-topic source passage is not an interpreted legal right, durable
> share-class identity, registered-class qualification, D3A class binding,
> Property 4C resolution, or admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`a7b5d905c693777a01c3e9417049f7a93e0609fd`, tree
`f69914f81e25a81b5e03eca84659614109e723db` (post-merged PR #59 / PR4D4D2A).
The worktree and index were clean. Branch
`codex/v2-sec-section12-rights-source-claims` was created directly from that
verified commit; divergent and stale local refs were preserved.

This PR adds one deterministic, read-only source-passage extractor downstream
of D4D2A:

- `economic_facts/sec_section12_rights_source_claims.py`;
- `tests/sec_section12_rights_source_claims_fixtures.py`;
- `tests/test_sec_section12_rights_source_claims.py`;
- `EXPECTED_RETURN_PR4D4D2B.md`.

Existing files receive only narrow dependency-boundary allowlist changes needed
for this downstream reader. There is no D4D2A refactor, D3A/D4C2 join, authority
change, legal-right value interpretation, model/runtime/V1 consumer, dependency
change, deployment, production action, or investment-rule change.

## Regulatory motivation, not a compliance determination

D4D2B uses the SEC FAST Act / Regulation S-K motivation already reviewed in
D4D2A: Item 601(b)(4)(vi) annual-report exhibits can contain Item 202(a)–(d) and
(f) descriptions for relevant Section-12-registered securities and can describe
more than one security or contextual authorized classes. Incorporation by
reference remains possible.

The extractor does not determine SEC compliance, exhibit completeness, whether
a class is registered, whether a passage is legally correct or effective, or
whether an absent topic should have been disclosed. A positive D4D2A document
does not make every heading within it a registered class.

## Public API and mandatory fresh replay

```python
extract_sec_section12_rights_source_claims(
    archive: SecFilingArchive,
    request: SecSection12RightsSourceClaimsRequest,
) -> SecSection12RightsSourceClaimsAssessment
```

The frozen/slotted request contains exactly `filing_receipt_id`. It accepts no
prebuilt D4D2A assessment/candidate, document selector, CIK, accession, form,
class, ticker, exchange, security ID, topic, rights value, time, bytes, URL,
callback, clock, qualification, or admission assertion.

Every call freshly invokes
`identify_sec_direct_section12_description_sources(...)`. Extraction proceeds
only when its overall status is
`CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES`. All other upstream states map
to `UPSTREAM_DIRECT_SOURCE_UNAVAILABLE` with one distinct issue:

- `UPSTREAM_NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE`;
- `UPSTREAM_SOURCE_AMBIGUITY`;
- `UPSTREAM_UNSUPPORTED_DOCUMENT_REPRESENTATION`;
- `UPSTREAM_UNSUPPORTED_FILING_FORM`.

No positive candidate is cherry-picked from a fail-closed upstream assessment.
Archive corruption, upstream contract errors, and programming errors propagate.

## Fresh raw-payload replay and representation profile

For every positive D4D2A candidate, the implementation rereads the exact D2A
object, resolves the D4D1 document by physical ordinal, compares D4D1 and D4D2A
semantic/evidence IDs, byte offset, byte length and payload SHA-256, slices the
raw object, and verifies the slice length/hash before parsing. D4D2A private
parser helpers and derived text hashes are not consumed as extracted text.

Only D4D2A `UTF8_HTML` and `UTF8_XHTML` candidates enter the initial extraction
profile. A valid D4D2A `UTF8_TEXT` source yields
`UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE`; valid claims from other candidates stay
visible, but cannot make the overall assessment positive. PDF, OCR, Word, RTF,
browser rendering, CSS layout, JavaScript, external resources, and network
fetching are absent.

## Deterministic visible-block profile

The independent strict parser requires a balanced full HTML document with one
explicit `html` root and `body`, optionally the exact XHTML namespace, plus only
the same narrow doctype/XML-declaration forms reviewed by D4D2A. It does not
repair HTML. Duplicate attributes, misnesting, foreign tag prefixes, visible
text without a reviewed block owner, ambiguous mixed block ownership, or
incomplete roots fail closed.

The finite block contributors are:

```text
h1 h2 h3 h4 h5 h6 p li td th caption blockquote div section article
```

Nested layout containers do not duplicate descendant blocks. `h1`–`h6`, `p`,
and `caption` cannot contain another reviewed block. A layout container that has
both direct visible text and descendant blocks is ambiguous. `br` and `hr`
contribute an in-block visible space. Source order, zero-based block ordinal,
structural element kind, exact decoded visible text, and its UTF-8 SHA-256 are
preserved. Normal HTML character references are decoded.

At minimum, `head`, `script`, `style`, `noscript`, `template`, `svg`, `math`, and
`canvas` subtrees cannot supply blocks or topics. CSS visibility is not
interpreted. Bounds are 100,000 elements, 25,000 emitted blocks, 16,384 decoded
characters per block, and 2,000,000 total visible decoded characters. A bound
failure is `SOURCE_AMBIGUITY`; no truncated result is emitted.

Detection normalization only collapses consecutive Unicode whitespace to one
ASCII space, trims it, and converts ASCII `a`–`z` to `A`–`Z`. Exact source text
is retained separately. There is no Unicode semantic normalization, punctuation
stripping, stemming, fuzzy match, edit distance, synonym inference, translation,
or token reordering.

## Common-stock source scopes and boundaries

The only positive whole-block normalized heading grammar is:

```text
COMMON STOCK
CLASS <TOKEN> COMMON STOCK
<TOKEN> := exactly one ASCII A–Z letter or 0–9 digit
```

`COMMON SHARES`, `ORDINARY SHARES`, `ORDINARY STOCK`, preferred stock, ADR/ADS,
units, warrants, debt, notes, bonds, and other labels do not become positive
scopes. A block shaped as `CLASS ... COMMON STOCK` but outside the exact token
grammar fails closed as an unsupported class-heading structure instead of being
repaired or guessed.

A positive source scope begins at its exact heading block and ends immediately
before the next exact supported common heading or one of these exact boundary
headings:

```text
PREFERRED STOCK
CLASS <TOKEN> PREFERRED STOCK
DEBT SECURITIES
WARRANTS
DEPOSITARY SHARES
```

A boundary creates no class claim. Multiple and repeated common-stock scopes
remain separate in source order; none is primary and no passages are unioned.
The `source_class_scope_id` equals the class-scope semantic ID and is local to
the candidate document/block profile. It is not a class ID, security ID, D3A
`source_security_scope_id`, or durable identity.

## Closed source-topic taxonomy and lexical table

The topics are source-text labels, not legal-right values:

| Source topic | Exact reviewed matching anchors |
| --- | --- |
| `DIVIDEND` | `DIVIDEND`, `DIVIDENDS` |
| `VOTING` | `VOTING`, `VOTE`, `VOTES` |
| `LIQUIDATION` | `LIQUIDATION`, `DISSOLUTION`, `WINDING UP`, `WINDING-UP` |
| `FURTHER_CALLS_OR_ASSESSMENTS` | `FURTHER CALLS`, `ASSESSMENT`, `ASSESSMENTS`, `NONASSESSABLE`, `NON-ASSESSABLE` |
| `PREEMPTIVE` | `PREEMPTIVE`, `PRE-EMPTIVE` |
| `CONVERSION` | `CONVERSION`, `CONVERT`, `CONVERTIBLE` |
| `REDEMPTION` | `REDEMPTION`, `REDEEM`, `REDEEMABLE` |
| `SINKING_FUND` | `SINKING FUND` |

Every anchor requires ASCII-alphanumeric phrase boundaries after the narrow
matching normalization. These finite forms reflect terminology observed in the
reviewed SEC-hosted D4D2A-style examples. There is no broad stemmer, arbitrary
regular-expression suffix match, synonym model, LLM classification, or inference
from an absent topic.

## Passage unit, provenance, and noninterpretation

One exact visible block inside one supported source scope produces at most one
passage. It carries every matched source topic and exact anchor identifier for
that block. Distant blocks are never concatenated, text outside the scope is
ignored, and preferred/debt boundary text cannot leak into the prior common
scope. The record binds D4D2A document semantics/evidence, source-scope ID and
heading, block ordinal/kind, exact decoded source text and SHA-256, topics,
anchors, and issues.

Thus a passage saying “one vote per share” may be tagged `VOTING`, but the output
does not contain `votes_per_share`. A passage saying “no preemptive ... rights”
may be tagged `PREEMPTIVE`, but no true/false preemptive-right value exists.
There is likewise no dividend rate, priority, liquidation preference, conversion
ratio, redemption term, sinking-fund amount, par value, authorized/outstanding
share count, transfer-restriction qualification, anti-takeover classification,
or beneficial-ownership interpretation. Topics are not legal-right values.

No extracted passage for a topic means only that no reviewed lexical passage was
extracted in the supported scope. It does not prove that a right is absent, that
the exhibit is incomplete, or that the issuer failed a disclosure obligation.
There is no Item-202 completeness, rights-completeness, legal-class-completeness,
or Property-4-completeness flag.

## Status and fail-closed behavior

After the mandatory upstream gate, precedence is:

1. `SOURCE_AMBIGUITY` for any ambiguous candidate or safety-bound failure;
2. `UNSUPPORTED_RIGHTS_EXTRACTION_PROFILE` for any unsupported candidate;
3. `CAPTURED_SECTION12_RIGHTS_SOURCE_CLAIMS` when at least one passage exists and
   every candidate was safely inspected;
4. `NO_SUPPORTED_COMMON_STOCK_SCOPE` when no positive scope exists; otherwise
5. `NO_SUPPORTED_RIGHTS_SOURCE_CLAIMS`.

Valid scopes/passages remain visible when another candidate forces a fail-closed
overall status. Document-local issue occurrences identify the affected candidate.
No nearest-heading, latest-heading, keyword-proximity, majority, company-name,
ticker, or D3A-title heuristic resolves ambiguity.

## Deterministic semantic and evidence identities

Domain-separated SHA-256 uses:

```text
pam:sec-section12-rights-source-claims:{domain}:v1
```

Class-scope semantics bind contract/block/class profiles, D4D2A candidate
semantic ID, exact and normalized heading, heading/body ordinals, ordered block
content hashes, and issues. Passage semantics bind the source-scope semantic ID,
block ordinal/kind, exact source-text hash, topics, exact anchor IDs, and issues.
Assessment semantics bind upstream D4D2A semantics, ordered scope/passage
semantics, document-local issue semantics, status, and issues.

Evidence identities additionally bind D4D2A candidate/document evidence,
filing-receipt evidence and exact payload provenance through upstream identities,
plus exact passage text. Identical-byte recapture preserves semantics and can
change evidence identity. Source passage or class-heading changes change
semantics. Filesystem path, environment, wall clock, randomness, object identity,
and input discovery enter neither identity.

## Time, joins, authority, and exact nonclaims

The only controlled time is D2A `receipt.captured_at` inherited through
D4D1/D4D2A. D4D2B adds no publication, availability, effective-rights,
`known_by`, HISTORICAL_AS_OF, D1 boundary, or wall-clock field.

### No D3A/D4C2 join

The implementation imports neither `sec_registered_securities.py` nor
`sec_current_registered_listing_bridge.py`. It never compares the source class
heading/scope with a D3A title/scope, ticker, or exchange. Similar names do not
establish class identity.

No `AuthorityProperty`, source route, provider-wide trust, Expected Return input,
model score, runtime consumer, V1 behavior, deployment, or production authority
is added. `SEC_COMPANYFACTS_LIVE_CURRENT_V1` remains unchanged.

| Property | State after PR4D4D2B |
| --- | --- |
| 4A | Unresolved — filing/source provenance is not issuer economic identity. |
| 4B | Unresolved — a source document/scope is not durable security identity. |
| 4C | Unresolved — passages/topics are not legal/economic class identity or rights qualification. |
| 4D | Unresolved — extracted scopes are not a complete relevant common-class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — one filing/source scope is not historical continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

## Validation

Validation uses invented offline evidence through the unchanged isolated runner.
No live SEC capture, positive-capital analysis, protected-expectation regeneration,
model-rule change, deployment, merge, or production operation is performed.

Python was 3.12.14 against the unchanged repository pin 3.12.13. All 33 locked
distributions match the unchanged dependency environment. Completed isolated
selections:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_section12_rights_source_claims.py` | 31 | PASS / 0.248 |
| `test_sec_*.py` | 710 | PASS / 7.467 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.444 |
| `test_*authority.py` | 44 | PASS / 0.144 |
| `test_security_identity.py` | 84 | PASS / 0.514 |
| `test_expected_return*.py` | 144 | PASS / 0.583 |
| `test_runtime_isolation.py` | 29 | PASS / 28.113 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.279 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.086 |
| Complete isolated suite | **2,266** | **PASS / 445.861** |

The complete suite reported no failures or skips. It includes D4D2A, D4D1, D2A
archive/acquisition and primary-document regressions; D3A/D3B; D4A/D4B;
D4C1/D4C2; source/CURRENT authority; synthetic security identity; Expected
Return; runtime and validation isolation; investment equivalence; and all 64 PIT
equivalence scenarios. It reproduced the protected identities without
regeneration:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`.

Final working/staged whitespace, committed-HEAD, remote-base, and clean-worktree
checks are completed during publication. No executable code or tests changed
after the completed full suite; only this validation record was finalized.

## Next handoff

D4D2B does not pre-authorize another implementation. A separately reviewed next
contract must decide whether a D4D2B source common-stock scope, D3A
`Security12bTitle`/source-security scope, and D4C2 corroborated CIK/symbol
relationship can be bound to the same source class without fuzzy matching or
ticker-only identity, and what additional durable identifier/evidence is needed.
Name similarity alone must not resolve Property 4C.
