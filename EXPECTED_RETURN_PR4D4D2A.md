# PR4D4D2A — Identify direct SEC Section-12 securities-description sources

> Candidate direct source != legal-rights qualification, share-class identity,
> durable security identity, Item 202 completeness, SEC compliance, Property 4C,
> or admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`60385075855b89443181f5fe83412f3bab5994a2`, tree
`d3d697ab377106a99964be0bcb376cdaa7c41303` (post-merged PR #58 / PR4D4D1).
The worktree and index were clean. Branch
`codex/v2-sec-direct-section12-description-source` was created directly from
that verified commit; divergent and stale local refs were preserved.

This PR adds one deterministic, offline, direct-only source-identification layer
over a freshly replayed D4D1 filing-document inventory. It answers only whether
an exact selected annual filing physically contains one or more embedded
documents satisfying PAM's deliberately narrow reviewed source profile.

Added:

- `economic_facts/sec_direct_section12_description_source.py`;
- `tests/sec_direct_section12_description_fixtures.py`;
- `tests/test_sec_direct_section12_description_source.py`;
- `EXPECTED_RETURN_PR4D4D2A.md`.

Existing test files receive only narrow dependency-boundary allowlist changes
needed for the new downstream reader. No D4D1 production code, acquisition,
primary-document, D3A/D3B, D4A/D4B/D4C2, source-authority, Expected Return,
investment rule, runtime, V1, roadmap, decision, dependency, deployment, or
production behavior changes.

## Regulatory motivation, not a compliance engine

The architectural motivation is the SEC's official
[FAST Act adopting release](https://www.sec.gov/files/rules/final/2019/33-10618.pdf),
Release No. 33-10618. The reviewed rule text for Item 601(b)(4)(vi) requires the
Item 202(a)-(d) and (f) information for each class registered under Section 12
when the registrant files the relevant annual report. The release also states
that a registrant may incorporate an unchanged previously filed qualifying
exhibit by reference, and that fiscal-year modifications/amendments should be
reflected in the annual-report disclosure.

Those rule semantics motivate the source profile only. This module does not
determine whether a registrant is in scope, whether an exhibit complies, whether
the description is complete or accurate, whether absence is a violation, or
whether a prior incorporated exhibit satisfies the rule.

## Public API and mandatory fresh replay

```python
identify_sec_direct_section12_description_sources(
    archive: SecFilingArchive,
    request: SecDirectSection12DescriptionRequest,
) -> SecDirectSection12DescriptionAssessment
```

The frozen/slotted request contains exactly `filing_receipt_id`. It accepts no
prebuilt inventory, CIK, accession, form, document selector, metadata, class,
ticker, security identity, rights flag, time, URL, bytes, callback, clock, or
caller qualification assertion. Exact typed arguments are required.

Every call freshly invokes `replay_sec_filing_document_inventory(...)`. A
serialized/prebuilt D4D1 result cannot bypass replay. The selected receipt's
archive membership and complete-submission object are verified under D2A/D4D1.
Archive corruption and upstream unsupported-envelope errors propagate; they are
not converted into ordinary weak-evidence outcomes.

## Supported forms and direct-only scope

Positive identification is supported only for `10-K` and `10-K/A`. The other
D2A/D4D1 forms—`10-Q`, `10-Q/A`, and `8-K`—return
`UNSUPPORTED_FILING_FORM` without inspecting exhibits for this profile.

Only D4D1 payload slices physically embedded in the selected complete-submission
object are inspected. The module does not fetch `FILENAME`, follow hyperlinks,
load external resources, search EDGAR, choose another receipt/accession, scan an
archive, select a latest filing, or resolve prior filings. Filename remains
provenance and is never treated as a path.

## Closed EX-4 source TYPE profile

The exact structural grammar is:

```text
EX-4
EX-4.<component>(-<component>){0,3}
component := 1–16 ASCII letters or digits
```

Therefore `EX-4`, `EX-4.1`, `EX-4.B`, `EX-4.H`, and bounded forms such as
`EX-4.A-1` are structurally eligible. `EX-40`, `EX-4.`, `EX-4..1`, `EX-4.A.B`,
`EX-4_1`, `EX-4/1`, oversized tokens, non-ASCII tokens, and `EX-10` are not.
Structural eligibility never makes a document positive.

## Supported representations and visible text

The initial profile supports only strict UTF-8 (with ASCII as its subset):

- balanced full HTML documents with one explicit `html` root and `body`;
- the same strict profile with the exact XHTML namespace on `html`;
- plain text containing no markup delimiter.

An optional exact HTML doctype or narrow UTF-8 XML declaration is accepted.
The parser is not a browser and performs no repair. Unbalanced/misnested markup,
wrong roots, duplicate attributes, foreign tag prefixes, ambiguous text/markup,
or unsupported declarations produce `SOURCE_AMBIGUITY`. PDF, ZIP/Office, OLE,
RTF, non-UTF-8, NUL/control-laden, and other binary/container representations
produce `UNSUPPORTED_DOCUMENT_REPRESENTATION`. No PDF/OCR, Word parser,
JavaScript, stylesheet, image, external resource, DTD, entity loader, or network
operation exists.

Visible text is collected only from the explicit body. `head`, `script`, `style`,
`noscript`, `template`, `svg`, `math`, and `canvas` subtrees cannot supply an
anchor. Normal HTML character references are decoded. Reviewed layout elements
contribute a space boundary; inline descendant text remains in source order. The
exact extracted visible-text SHA-256 and normalized matching-text SHA-256 are
retained as derived inspection provenance. D4D1's raw payload SHA-256 remains the
authoritative source-byte identity.

## Exact matching normalization and anchors

Matching performs only:

1. consecutive Unicode whitespace collapse to one ASCII space;
2. leading/trailing whitespace removal; and
3. ASCII `a`–`z` conversion to uppercase.

It performs no Unicode normalization, punctuation stripping, token reordering,
stemming, edit distance, fuzzy similarity, synonym inference, translation, or
markup repair.

At least one exact heading anchor and at least one exact Section-12 anchor must
both occur in visible text with ASCII-alphanumeric phrase boundaries.

Exact heading set:

```text
DESCRIPTION OF REGISTRANT'S SECURITIES
DESCRIPTION OF THE REGISTRANT'S SECURITIES
DESCRIPTION OF REGISTRANT’S SECURITIES
DESCRIPTION OF THE REGISTRANT’S SECURITIES
```

Exact Section-12 set:

```text
REGISTERED PURSUANT TO SECTION 12 OF THE SECURITIES EXCHANGE ACT OF 1934
REGISTERED PURSUANT TO SECTION 12(B) OF THE SECURITIES EXCHANGE ACT OF 1934
```

The two curly-apostrophe headings are explicit finite variants, not the result of
Unicode normalization. They were observed in official SEC-hosted annual-report
exhibits, including an
[EX-4.B example](https://www.sec.gov/Archives/edgar/data/822416/000082241626000007/exhibit4b-descriptionofreg.htm)
and an
[EX-4.3 example](https://www.sec.gov/Archives/edgar/data/1662774/000166277425000027/qncx2024123110k.pdf).
The explicit `(B)` Section-12 form is the only reviewed parenthetical variant. A
comma, other punctuation change, misspelling, synonym, incomplete phrase, or
isolated words such as “Section 12,” “Exchange Act,” “securities,” or
“description” do not match.

## DESCRIPTION, filename, and ordering

D4D1 `DESCRIPTION` is retained unchanged as provenance but is neither required
nor sufficient. It cannot override missing visible-content anchors. `FILENAME`,
extension, sequence, ordinal, and document order likewise cannot qualify a
source. Extension is not used even for representation detection.

Every positive document is preserved in D4D1 physical order. Multiple positives
are not a conflict and there is no first, lowest/highest sequence, filename,
TYPE, phrase, or presumed-class winner. Multiple documents are not inferred to
represent multiple economic classes.

## Status precedence and no-candidate semantics

Assessment precedence is:

1. `UNSUPPORTED_FILING_FORM`;
2. `SOURCE_AMBIGUITY` if any structurally eligible document is malformed or
   ambiguous under the strict textual profile;
3. `UNSUPPORTED_DOCUMENT_REPRESENTATION` if any structurally eligible document
   cannot be inspected under the representation profile;
4. `CAPTURED_DIRECT_SECTION12_DESCRIPTION_SOURCES` when at least one positive
   exists and all eligible documents were deterministically inspectable; otherwise
5. `NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE`.

Positive candidates remain visible when another eligible document makes the
overall assessment fail closed, but the overall status is not `CAPTURED`.

`NO_DIRECT_SUPPORTED_DESCRIPTION_SOURCE` means only that no physically embedded
document in this exact selected `10-K`/`10-K/A` satisfied PAM's D4D2A profile. It
does not mean that no registered securities, legal rights, relevant disclosure,
prior exhibit, or incorporation-by-reference case exists, and does not assert
noncompliance.

## Incorporation-by-reference limitation

The reviewed rule permits incorporation by reference under relevant conditions.
D4D2A does not resolve it. Hyperlinks and reference language are inert visible
source content: no target accession is inferred, no prior filing is looked up,
and no target is fetched. This version intentionally adds no speculative
incorporation-reference diagnostic.

## Output, identities, and time

Frozen/slotted candidate records retain filing and D4D1 document identities,
physical ordinal and metadata, exact payload offset/length/SHA-256, representation
profile, derived visible/normalized text hashes, every exact matched anchor ID,
source-identification status, and issues. They expose no issuer/security/class/
listing ID, rights, registered-class assertion, qualification, or admission.

Domain-separated SHA-256 uses:

```text
pam:sec-direct-section12-description:{domain}:v1
```

Candidate semantic identity binds the contract/profile, filing CIK/accession/form,
D4D1 document semantic identity, representation, exact matched anchors, source
status, and issues. Evidence identity additionally binds the D4D1 document
evidence identity, receipt, exact payload slice/digest, and derived text hashes.
Assessment semantic identity binds contract, filing form, D4D1 inventory
semantics, ordered candidate semantics, status, and issues. Assessment evidence
identity additionally binds inventory and candidate evidence identities.

Identical recapture preserves semantics and can change evidence through the
upstream receipt. Changed raw payload changes D4D1 document semantics. Filesystem
path, environment, object identity, current clock, and randomness enter neither
identity.

The only controlled time remains D2A `receipt.captured_at`. No publication,
availability, effective-rights, `known_by`, HISTORICAL_AS_OF, D1 boundary, or
wall-clock field is created.

## Authority and exact nonclaims

No `AuthorityProperty`, source route, provider-wide trust, D4C2 join, D3A title/
ticker/exchange comparison, identity consumer, Expected Return input, model score,
runtime consumer, V1 behavior, deployment, or production authority is added.

### No legal-rights extraction

Even a positive source yields no class designation, par value, authorized shares,
voting, dividend, liquidation, conversion, redemption, sinking-fund, preemption,
transfer, anti-takeover, agent, ticker, exchange, jurisdiction, common/preferred,
or other legal/economic claim. D4D2B requires separate review.

| Property | State after PR4D4D2A |
| --- | --- |
| 4A | Unresolved — filing CIK remains source provenance, not issuer identity. |
| 4B | Unresolved — a source document is not durable security identity. |
| 4C | Unresolved — no legal/economic class identity or rights are extracted. |
| 4D | Unresolved — direct documents are not complete relevant class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — one annual filing is not historical continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

## Validation

Validation uses invented offline evidence through the unchanged isolated runner.
No live SEC capture, positive-capital analysis, protected-expectation regeneration,
model-rule change, deployment, merge, or production operation is performed.

Python was 3.12.14 against the unchanged repository pin 3.12.13. All 33 locked
distributions match unchanged `requirements.lock`; the only textual freeze/lock
comparison difference is pip's case-normalized `pymupdf` display and lock comments.

Completed isolated selections:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_direct_section12_description_source.py` | 32 | PASS / 0.232 |
| `test_sec_*.py` | 679 | PASS / 7.114 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.442 |
| `test_*authority.py` | 44 | PASS / 0.144 |
| `test_security_identity.py` | 84 | PASS / 0.531 |
| `test_expected_return*.py` | 144 | PASS / 0.608 |
| `test_runtime_isolation.py` | 29 | PASS / 28.363 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.280 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.086 |
| Complete isolated suite | **2,235** | **PASS / 445.582** |

The complete suite reported no failures or skips. It includes D4D1, D2A
acquisition/archive, primary-document replay, D3A/D3B, D4A/D4B, D4C1/D4C2,
source/CURRENT authority, synthetic security identity, Expected Return, runtime
isolation, validation identity, investment equivalence, and all 40 PIT tests.
It reproduced all 64 PIT equivalence scenarios and the protected identities
without regenerating expectations:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`.

Final working/staged whitespace, committed-HEAD, remote-base, and clean-worktree
checks are completed during publication. No executable code or test changed after
the completed full suite; only this validation record was finalized.

## Next handoff

The possible next separately reviewed chantier is PR4D4D2B, structured Section-12
rights source claims. It may consume only positively identified D4D2A sources and
must independently define its exact extraction vocabulary, section/class scoping,
missing/contradictory claims, multi-class handling, and relationship to D3A/D4C2.
Extracted claims would still not automatically resolve Property 4C. This PR does
not pre-authorize D4D2B, merge, deployment, authority, or promotion.
