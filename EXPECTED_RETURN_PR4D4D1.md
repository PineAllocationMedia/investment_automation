# PR4D4D1 — Replay exact SEC filing embedded-document inventory

> Exact embedded-document provenance only. TYPE and DESCRIPTION metadata do not
> identify a rights exhibit, security, share class, listing, or admission fact.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`3b700193bcbdd74b349eb7a282b39da2c0ae843b`, tree
`62aa054b62e9073b06e92f3c79d9fe31e9c5735e` (post-merged PR #57 / PR4D4C2).
The worktree and index were clean. Branch
`codex/v2-sec-filing-document-inventory` was created directly from that verified
remote commit; divergent and stale local refs were preserved.

This PR adds a deterministic, offline inventory over one explicitly selected D2A
complete-submission filing receipt. It changes no D2A acquisition or archive
contract, existing primary-document replay, D3A/D3B extraction, D4A/D4B/D4C2,
source authority, economic identity, Expected Return, investment rule, runtime,
V1, deployment, or production behavior.

Added:

- `economic_facts/sec_filing_document_inventory.py`;
- `tests/sec_filing_document_inventory_fixtures.py`;
- `tests/test_sec_filing_document_inventory.py`;
- `EXPECTED_RETURN_PR4D4D1.md`.

The only existing-file change is a narrow dependency-test allowlist entry in
`tests/test_sec_filing_acquisition.py`, permitting the new offline reader to
import `sec_filing_archive`.

## Public API and exact request

```python
replay_sec_filing_document_inventory(
    archive: SecFilingArchive,
    request: SecFilingDocumentInventoryRequest,
) -> SecFilingDocumentInventoryAssessment
```

The frozen/slotted request contains exactly `filing_receipt_id`. It accepts no
separate CIK, accession, form, document/exhibit selector, TYPE, SEQUENCE,
FILENAME, DESCRIPTION, rights/security/class/listing identifier, source bytes,
URL, time, callback, clock, authority, qualification, or success assertion.

Replay requires exact typed arguments. It reads the explicit receipt, verifies
archive membership, and verifies the exact archived object length and SHA-256.
It performs no network request, write, clock read, directory scan, latest receipt
selection, alternate accession lookup, or remote document fetch.

## Relationship to D2A and supported envelope

The supported forms are exactly D2A's current set:

- `10-K`;
- `10-K/A`;
- `10-Q`;
- `10-Q/A`;
- `8-K`.

No form support is added to D2A. The inventory independently mirrors the reviewed
D2A modern complete-submission grammar and fails closed on CIK/accession/form
mismatch, unsupported header or filer context, malformed/balanced delimiter
failure, declared document-count mismatch, duplicate/invalid SEQUENCE, duplicate/
unsafe FILENAME, empty payload, reserved delimiter text, a first-document TYPE
different from the filing form, or another document claiming the primary form.

The envelope retains exactly one FILER context and the same bounded 256 KiB
header, 1–1,000 document count, ASCII metadata, positive sequence, safe filename,
and exact source-object constraints. A missing DESCRIPTION is supported. A present
DESCRIPTION is one exact ASCII metadata line bounded to 4,096 bytes. Malformed or
oversized metadata is rejected rather than normalized.

## Document provenance and ordering

Every frozen/slotted `SecFilingDocumentProvenance` retains:

- filing receipt ID;
- CIK;
- accession;
- filing form;
- zero-based source document ordinal;
- exact TYPE;
- exact SEQUENCE;
- exact FILENAME;
- exact DESCRIPTION or `None` when absent;
- exact payload byte start in the archived complete-submission object;
- exact payload byte length;
- SHA-256 of exactly that payload slice.

Documents remain in physical submission order. They are not sorted or selected by
TYPE, filename, sequence, description, or presumed legal meaning. Payloads remain
exact bytes and may contain HTML, XML, text, or binary values. They are never
decoded for classification, executed, reserialized, normalized, or followed.

For the first document, regression tests prove equality with unchanged
`read_primary_document` provenance for receipt, CIK, accession, form, ordinal,
sequence, filename, byte start, byte length, and content SHA-256. The existing
`PrimaryDocumentProvenance` shape and evidence identity are unchanged.

## TYPE and DESCRIPTION semantics

TYPE and DESCRIPTION are opaque SEC submission metadata. Values such as `EX-4`,
`EX-4.1`, `EX-4.B`, `EX-4.H`, and `EX-10` receive no classification or ranking.
DESCRIPTION is preserved exactly, including punctuation and leading/trailing
spaces. It is not lowercased, fuzzy-matched, or searched for “description of
securities.”

In particular:

```text
EX-4.* != Item 601(b)(4)(vi) rights exhibit automatically
DESCRIPTION text != legal classification
source document order != legal meaning
```

## Deterministic identity

Domain-separated SHA-256 identities use:

`pam:sec-filing-document-inventory:{domain}:v1`

Document semantic identity binds CIK, accession, filing form, source ordinal,
TYPE, SEQUENCE, FILENAME, DESCRIPTION, and exact payload SHA-256. It excludes
capture multiplicity, filesystem path, environment, object identity, clock, and
randomness.

Document evidence identity additionally binds the exact filing receipt and exact
payload location/length. Because the receipt identity binds the exact complete-
submission object hash, length, capture time, and D2A receipt contract, it also
binds the exact capture evidence.

Inventory semantic identity binds the contract version, filing selectors, and
ordered document semantic identities. Inventory evidence identity additionally
binds the exact filing receipt and ordered document evidence identities. An
identical-byte recapture preserves document/inventory semantics and changes
evidence identity; changed payload bytes or source metadata change semantics.

## Time and no content interpretation

The only controlled time is the unchanged D2A `receipt.captured_at`, meaning when
PAM controlled-captured the complete-submission bytes. Embedded documents receive
no invented `published_at`, `available_at`, `effective_at`, `rights_effective_at`,
or `known_by`. SEC acceptance remains separate source metadata. There is no
HISTORICAL_AS_OF authority and no D1 boundary is created or extended.

The inventory does not parse payloads for voting, dividend, liquidation,
conversion, redemption, preemption, transfer, par-value, authorized-share,
registered-class, common/preferred, debt, or wrapper claims. It does not identify
Item 202 or Item 601(b)(4)(vi), inspect articles or bylaws, follow hyperlinks,
resolve incorporated-by-reference text, infer another accession, or treat a
missing direct EX-4 payload as a defect.

## Authority and admission boundary

No `AuthorityProperty`, source-authority route, or provider-wide trust is added.
`SEC_COMPANYFACTS_LIVE_CURRENT_V1` is unchanged. The inventory is not consumed by
D4C2, `security_identity.py`, Expected Return, Quality, Durability, Confidence,
Portfolio Room, allocation, runtime, or V1.

| Property | State after PR4D4D1 |
| --- | --- |
| 4A | Unresolved — filing CIK remains source provenance, not issuer economic identity. |
| 4B | Unresolved — embedded documents do not establish durable security identity. |
| 4C | Unresolved — no legal/economic class identity or rights are extracted. |
| 4D | Unresolved — physical document inventory is not complete relevant class inventory. |
| 4E | Unresolved — no EPS applicability or entitlement qualification. |
| 4F | Unresolved — no qualified listing, quote currency, or quote unit. |
| 4G | Unresolved — no complete/scoped listing inventory. |
| 4H | Unresolved — one filing capture is not historical continuity. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

The only new capability is:

> Given one exact controlled D2A complete-submission receipt, PAM can
> deterministically enumerate and cryptographically bind each physically embedded
> document.

## Validation

Validation uses fictional offline evidence through the unchanged isolated runner.
No live SEC request, positive-capital analysis, protected-expectation regeneration,
model-rule change, deployment, or production operation is performed.

Python was 3.12.14 against the unchanged repository pin 3.12.13. Completed
isolated selections:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_filing_document_inventory.py` | 25 | PASS / 0.171 |
| `test_sec_*.py` | 647 | PASS / 7.102 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.386 |
| `test_*authority.py` | 44 | PASS / 0.150 |
| `test_security_identity.py` | 84 | PASS / 0.472 |
| `test_expected_return*.py` | 144 | PASS / 0.560 |
| `test_runtime_isolation.py` | 29 | PASS / 28.772 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.284 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.077 |
| Complete isolated suite | **2,203** | **PASS / 439.651** |

The complete suite reported no failures or skips, exercised all 64 PIT
equivalence scenarios, and reproduced both protected fingerprints without
regenerating expectations. Protected expectations remain unchanged:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- Model rules: `2026-08-23-allocation-room-integrity-v7`.

## Next handoff

A possible next chantier is separately reviewed PR4D4D2, SEC Section-12
registered-security rights source claims. That contract must independently define
how a rights exhibit is identified, direct versus incorporated-reference cases,
supported forms, exact provenance, extractable source claims, unsupported cases,
and any later relationship to D4C2. This PR does not pre-authorize D4D2, legal
interpretation, Property-4 qualification, admission, merge, deployment, or
promotion.
