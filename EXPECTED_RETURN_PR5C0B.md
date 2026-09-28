# PR5C0B — Controlled corporate-action/share-basis source foundation

> Source evidence only. This contract does not establish an unchanged share
> basis, infer no action from silence, normalize EPS, or discharge any C3 blocker.

## Reviewed base and exact scope

After `git fetch origin`, the approved integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `639599aa4daa947296ef21bb46ae314702e72500` |
| Tree | `78ee953428255be6424b192b5b6c7284e1b22a9c` |
| Implementation branch | `codex/v2-pr5c0b-share-basis-source-foundation` |

The starting worktree and index were clean. The prior local PR5C0A branch was
preserved. This PR adds one deterministic offline source foundation:

- `economic_facts/sec_share_basis_source_claims.py`;
- `tests/sec_share_basis_source_claims_fixtures.py`;
- `tests/test_sec_share_basis_source_claims.py`;
- this contract; and
- one minimal roadmap update.

It does not modify `share_basis.py`, PR5B, PR5C0A authority, C3 values, Expected
Return, model rules, runtime, V1, production, deployment, or any provider route.

## Source-semantics checkpoint

The checkpoint succeeded for a source-only layer, not for share-basis
qualification.

Official [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes the filer Submissions history, referenced older history files, and
Inline XBRL filing data. The existing D2B rail can replay the captured parent and
explicit children without turning reference closure into historical completeness.
D2A and D4D1 preserve exact complete-submission receipts, embedded-document byte
slices, content hashes, forms, filenames, ordinals, and capture times. PR5C0A's
bounded visible-document profile proves that exact primary and reviewed `EX-99`
documents can be represented without browser repair, generic NLP, or network use.

Official Nasdaq Listing Rule 5250(e)(6) requires notice for dividend actions and
stock distributions, while Rule 5250(e)(7) requires a Company Event Notification
Form for reverse stock splits. Nasdaq's public Listing Center also exposes the
relevant company-event and distribution forms. Those rules establish notification
duties; they do not establish that PAM captured each notification or that an empty
PAM event inventory is complete.

The existing free Nasdaq Listed snapshot remains current directory evidence only.
It is not consumed by this module and cannot prove historical action completeness,
ticker/class continuity, or an unchanged share denomination.

The source flow is therefore honest and bounded:

```text
captured Submissions parent + explicitly selected history children
  -> represented 10-K/10-Q/8-K filing universe and metadata signals
  -> explicitly selected exact complete-submission receipts
  -> exact primary and reviewed EX-99 document slices
  -> finite textual action/basis claims, ratios, dates and class labels
  -> future PR5B + PR5C0A + PR5C0B qualification join
```

Nothing in this flow permits:

```text
no detected wording -> no action -> unchanged share basis
```

## Public API and closed request

```python
build_sec_share_basis_source_foundation(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecShareBasisSourceRequest,
) -> SecShareBasisSourceAssessment
```

The frozen/slotted request contains exactly one parent Submissions receipt ID,
a tuple of explicit child Submissions receipt IDs, and a tuple of explicit filing
receipt IDs. Every selector is exact lowercase 64-hex. It contains no CIK, ticker,
class/security ID, source bytes, URL, clock, qualification flag, completeness
assertion, `same_basis`, `no_split`, `no_corporate_action`, or `basis_complete`.

Replay performs no network request, write, directory scan, implicit clock read,
latest selection, or caller-authored economic join. Foreign CIKs/accessions,
duplicate selections, unrepresented filings, and untyped arguments fail closed.

## Filing universe and document scope

The filing universe is freshly derived from D2B and includes exact forms:

```text
10-K  10-K/A  10-Q  10-Q/A  8-K  8-K/A
```

Every occurrence of a relevant accession remains visible. No suspicion or
keyword filter narrows the universe. Every represented relevant accession needs
an explicitly selected D2A receipt for a complete source set.

The extractor reviews the verified primary document and exact `EX-99` / `EX-99.n`
documents. Other embedded documents remain in the D4D1 inventory but are not
interpreted. Eligible text uses the same bounded UTF-8 plain-text or balanced
HTML/Inline-XBRL-visible-block profile as PR5C0A. Malformed, unsafe, unsupported,
or over-bound documents remain unsupported.

## Finite source vocabulary

Closed action references cover:

- stock split and reverse stock split;
- stock dividend;
- share-class conversion;
- recapitalization;
- merger/security exchange;
- spin-off;
- share redenomination and share consolidation; and
- other explicitly basis-affecting action language.

Separate claim kinds retain explicit split-ratio, action-effective-date,
record-date, retrospective-share-adjustment, retrospective-per-share-adjustment,
historical-EPS-adjustment, common-share-basis, and uninterpreted basis-affecting
references.

Each claim retains the exact passage and hash, accession, exact document semantic
identity and byte provenance, document/block ordinals, source-local action key,
class scope/labels, lifecycle, structured ratio/date when safely parsed, and every
equivalent capture occurrence.

`LEXICAL_OR_PRESENTATION_REFERENCE` remains distinct from an
`AFFIRMATIVE_LIFECYCLE_ACTION_CLAIM`; neither is future economic/basis
qualification.

Keyword presence never creates an implemented event. The closed lifecycle is:

- `ANNOUNCED_OR_PROPOSED_REFERENCE`;
- `APPROVED_REFERENCE`;
- `EFFECTIVE_OR_IMPLEMENTED_REFERENCE`;
- `CANCELLED_OR_NOT_IMPLEMENTED_REFERENCE`; and
- `UNRESOLVED_LIFECYCLE`.

Finite affirmative grammar is evaluated only within one bounded visible block.
Negative, cancelled, proposed, conditional, and approved-but-not-effective
language cannot become an effective action. Unresolved language stays unresolved.

## Ratios, dates and retrospective presentation

Reviewed ratio forms include exact positive integer `new_units` / `old_units`
semantics for `2-for-1`-style phrases and explicit “every old shares became new
shares” wording. Original source terms remain. Binary floating point is never
used. Colon-only ratios, impossible terms, or multiple incompatible ratios in
one source-local action do not receive an inferred orientation.

Filing date, report date, SEC acceptance timestamp, controlled capture time,
record date, and action effective date remain distinct. Only reviewed explicit
calendar-date grammar produces a normalized action date; the exact source text is
retained. An ambiguous or conflicting action date fails closed. No filing clock is
substituted for an action date.

Explicit statements that historical shares, per-share amounts, or EPS were
retroactively adjusted are separate typed claims. Their scope distinguishes all
periods presented, one explicit period reference, and vague/unresolved coverage.
No such statement rewrites C3 values or proves that every retained version is on
one target basis.

## Security/class linkage boundary

Every claim exposes a source-local scope:

- named common class explicit;
- issuer common stock generic;
- multiple classes or ambiguous;
- other security; or
- unresolved.

Exact source labels and a deterministic filing/document/block-local link are
retained so a future qualifier can join them to freshly replayed PR5B evidence.
PR5C0B does not emit a selected PR5B route key, create ticker identity, or infer
that issuer-generic language belongs to the selected class. Preferred stock,
warrants, options, convertibles, ADS/ADR language, and ambiguous multiple-class
scope never become selected ordinary-common evidence.

## Inline XBRL boundary

Visible Inline XBRL filing text participates only through the exact bounded
document-block profile. This PR does not publish a reviewed QName mapping for
stock-split concepts and therefore emits no structured XBRL fact claim. Absence
of a standardized tag is never no-action evidence, and extension concepts are not
silently mapped. A future reviewed QName/context/unit profile may add structured
facts without weakening this textual source contract.

## Status, conflicts and deterministic identity

Closed statuses are:

- `CAPTURED_SHARE_BASIS_SOURCE_SET`;
- `INCOMPLETE_SHARE_BASIS_SOURCE_SET`;
- `SOURCE_CONFLICT`; and
- `UNSUPPORTED_SOURCE_PROFILE`.

Captured means only that the selected captured source surface was represented.
Zero detected actions is valid in that status and proves no negative proposition.
Incomplete covers missing D2B reference closure or missing represented filing
captures. Unsupported covers malformed/unsupported eligible documents, ambiguous
ratio/date semantics, unsafe bounds, and uninterpreted basis-affecting language.
Conflict preserves D2B contradictions, differing bytes for one accession,
D2B/D2A form disagreement, and incompatible ratios/effective dates within one
source-local action. There is no first/latest/amendment/majority winner.

Domain-separated SHA-256 identities use
`pam:sec-share-basis-source:{domain}:v1`. Semantic identity binds source meaning,
filing-universe semantics, claims, class scope, structured terms, stable issues,
status, and limitations. Evidence identity additionally binds exact receipts,
capture times, occurrence positions, document evidence, exact passages, and issue
occurrences. Caller order and equal-byte recapture do not change semantics;
equivalent recapture enriches evidence. Paths, wall clock, randomness, and object
identity enter neither identity.

## Authority and sourcing limitations

PR5C0B discharges zero blockers. In particular:

- `SPLIT_BASIS_NOT_ESTABLISHED` remains unresolved;
- `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED` remains unresolved;
- PR5B and PR5C0A authority remain unchanged;
- synthetic PR4C5 evidence is not imported;
- no `AdmissionBlocker` success tuple is emitted; and
- no Expected Return/model/runtime/V1 consumer exists.

The source-foundation capability succeeds, but the controlled public SEC/free
Nasdaq graph still does not provide positive complete no-transformation coverage
from the oldest retained EPS period through CURRENT T. The public evidence is
useful for explicit action and presentation claims, conflicts, and unsupported
cases; it is not sufficient by silence to discharge the share-basis blocker.

Nasdaq Daily List is a potentially relevant historical corporate-action source,
including stock dividends/splits, but it is not integrated, purchased, scraped,
licensed, or assumed authoritative here. Any paid-source decision requires owner
approval and a separate permitted-use contract. A licensed Daily-List-like or
other complete action source may still be required before PR5C can affirmatively
qualify no transformation.

Explicit answers:

- Does PR5C0B establish an unchanged share basis? **NO.**
- Does it discharge `SPLIT_BASIS_NOT_ESTABLISHED`? **NO.**
- Does an empty detected-event inventory prove no corporate action? **NO.**
- Does stable CIK/ticker/share count prove one denomination epoch? **NO.**
- Was any paid Nasdaq Daily List capability integrated? **NO.**

## Validation

Validation used Python 3.12.14, the unchanged locked environment, fictional
offline filing bytes, disposable state/HOME, and denied network. No protected
expectation was regenerated.

| Isolated selection | Tests | Result |
| --- | ---: | --- |
| PR5C0B focused | 24 | PASS |
| PR5C0A | 27 | PASS |
| SEC Submissions | 101 | PASS |
| SEC filing acquisition/archive/document inventory | 99 | PASS |
| PR5B | 31 | PASS |
| D4A/D4B temporal | 58 | PASS |
| source/current authority | 44 | PASS |
| security identity | 84 | PASS |
| synthetic PR4C5 share basis | 136 | PASS |
| Expected Return | 144 | PASS |
| runtime isolation | 29 | PASS |
| validation identity isolation | 19 | PASS |
| protected PIT/determinism | 40 | PASS |
| complete isolated suite | **2,400** | **PASS** |

Python compilation and working-tree whitespace checks passed. Final staged and
committed-tree whitespace checks are performed during publication.

Protected identities must remain:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- model rules: `2026-08-23-allocation-room-integrity-v7`; and
- frozen V1 commit/tree: `c5fc27c82c29c2a6027eccee245098c4a072fdf1` /
  `26a69bb0b2185ab141af0763da2d965602c8346b`.
