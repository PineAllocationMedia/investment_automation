# PR5C0A — Controlled SEC reporting-subject source foundation

> Source evidence only. This contract does not establish accounting reporting-
> subject continuity, infer continuity from silence or a shared CIK, or discharge
> any C3 admission blocker.

## Reviewed base and scope

After `git fetch origin`, the reviewed integration base was exactly
`626ee5baebd8a5a5cf49dfb098fabcbd93d21d0a`, tree
`fc456bc5af2456d8b31e6868d1fc88fbf0e5fae9`, on
`origin/model-v2/expected-return-challenger` (merged PR #64 / PR5B). The clean
implementation branch was created directly from that ref; the prior local PR5B
branch was preserved.

This PR adds one deterministic offline source foundation. It freshly replays one
exact D2B Submissions parent and explicitly selected history children, joins
explicitly selected D2A complete-submission receipts, inventories exact embedded
documents, retains reviewed Form 8-K metadata signals, and extracts a finite set
of explicit source passages. It never returns a continuity decision.

The D2A acquisition and D4D1 document-inventory allowlists add `8-K/A`. This is
required because SEC reverse-acquisition guidance expressly contemplates required
accounting-acquirer financial statements being filed by amendment to Form 8-K.
The extension changes no interpretation, authority, transport, archive, limit, or
envelope rule.

Out of scope: final reporting-subject qualification, PR5C, share-basis and
corporate-action qualification, price, FX, dividends, Expected Return, Quality,
Durability, Confidence, portfolio logic, recommendations, model rules, runtime,
V1, deployment, global entity resolution, and a generalized M&A engine.

## Source-semantics checkpoint

The checkpoint succeeded for a source-only layer.

Official [SEC EDGAR API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
describes recent filing history and
referenced additional history files. D2B already captures and replays that surface
while preserving compatible scalar columns, including `items`, without claiming
an historical-completeness watermark.

SEC [Financial Reporting Manual Topic 12](https://www.sec.gov/about/divisions-offices/division-corporation-finance/financial-reporting-manual/frm-topic-12)
distinguishes the legal registrant from
the accounting acquirer and explains that after a reverse acquisition or reverse
recapitalization the accounting acquirer/legal acquiree may be the continuing
reporting entity and the registrant's predecessor. It also describes the relevant
Form 8-K item pattern and amended-filing route. These are positive source concepts;
absence of the wording is not evidence of continuity.

D2A and D4D1 verify the complete-submission envelope, exact receipt, content hash,
document ordinal/type/filename, byte slice, and document hash. Those controls can
preserve explicit passages and provenance without inventing an accounting result.

```text
captured Submissions parent + selected referenced history
  -> represented filing universe and metadata signals
  -> selected exact complete-submission receipts
  -> exact primary / reviewed embedded document slices
  -> explicit typed source passages
  -> future separately reviewed qualifier
```

This flow never permits `no detected wording -> no transition -> continuity`.

## Public API and request closure

```python
build_sec_reporting_subject_source_foundation(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecReportingSubjectSourceRequest,
) -> SecReportingSubjectSourceAssessment
```

The frozen/slotted request has exactly the parent Submissions receipt ID, a tuple
of child Submissions receipt IDs, and a tuple of filing receipt IDs. Every selector
is exact lowercase 64-hex. There is no caller CIK, filing list, source body, URL,
clock, subject ID, completeness assertion, continuity/no-event boolean,
qualification flag, or authority token.

Replay performs no network request, write, clock read, directory scan, or latest
selection. Foreign CIKs, unrepresented accessions, duplicates, and untyped calls
fail. Archive integrity failures propagate.

## Filing universe and reference closure

The universe derives only from fresh D2B replay. An accession enters when any
retained occurrence has exact form `10-K`, `10-K/A`, `10-Q`, `10-Q/A`, `8-K`, or
`8-K/A`. Every occurrence for that accession remains visible. No suspicion filter
is applied.

`CAPTURED_REFERENCE_CLOSURE_COMPLETE` keeps exactly its D2B meaning: every history
filename referenced by that captured parent was supplied and replayed. It is not
real-world filing completeness, event completeness, coverage through CURRENT T,
or reporting-subject continuity.

Every represented relevant accession needs an exact selected D2A capture for a
complete PR5C0A source set. Equal-byte recaptures enrich evidence without changing
semantics. Differing bytes remain a conflict; no first, latest, amendment, or
majority winner exists.

## Signals and exact claims

Only exact `items` tokens on Forms 8-K and 8-K/A become discovery signals:

| Item | Signal |
| --- | --- |
| 2.01 | `ACQUISITION_DISPOSITION_SIGNAL` |
| 4.01 | `CERTIFYING_ACCOUNTANT_CHANGE_SIGNAL` |
| 5.01 | `CHANGE_IN_CONTROL_SIGNAL` |
| 5.03 | `FISCAL_YEAR_CHANGE_SIGNAL` |
| 5.06 | `SHELL_STATUS_CHANGE_SIGNAL` |
| 9.01 | `FINANCIAL_STATEMENTS_EXHIBITS_SIGNAL` |

An unreviewed token is retained as uninterpreted metadata but does not by itself
make a subject claim or invalidate otherwise reviewed source bytes. Item presence, a name or
fiscal-year change, same CIK, ticker, security, auditor, or filing cadence never
creates a subject transition or identity claim.

The extractor consumes the verified primary and reviewed `EX-99` / `EX-99.n`
documents. Other documents remain in the exact inventory but are uninterpreted.
Eligible bytes must be bounded UTF-8 plain text or balanced HTML/XHTML under a
closed visible-block parser. Unsupported encodings, malformed structure, and
safety-bound excess remain unsupported. There is no LLM, fuzzy classifier,
browser repair, or external-resource resolution.

Reference claims retain reviewed term mentions. The two stronger relational
claims are narrower: they require a finite, reviewed affirmative sentence
grammar. Keyword co-occurrence does not create a transition or reporting-entity
relation. Negative, hypothetical, conditional, and otherwise unreviewed wording
therefore cannot emit `PREDECESSOR_SUCCESSOR_TRANSITION` or
`ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY`.

Closed claim vocabulary:

- `PREDECESSOR_REFERENCE`;
- `SUCCESSOR_REFERENCE`;
- `PREDECESSOR_SUCCESSOR_TRANSITION`;
- `ACCOUNTING_ACQUIRER_REFERENCE`;
- `ACCOUNTING_ACQUIRER_BECOMES_REPORTING_ENTITY`;
- `REVERSE_ACQUISITION_REFERENCE`;
- `REVERSE_RECAPITALIZATION_REFERENCE`;
- `CONTINUING_REPORTING_ENTITY_REFERENCE`;
- `PREDECESSOR_PERIOD_LABEL`;
- `SUCCESSOR_PERIOD_LABEL`;
- `CARVE_OUT_FINANCIAL_STATEMENTS_REFERENCE`;
- `COMBINED_FINANCIAL_STATEMENTS_REFERENCE`;
- `UNINTERPRETED_RESTRUCTURING_LANGUAGE`.

Every claim retains exact passage text and hash, filing receipt/capture time,
document semantic/evidence identity, document byte slice, and visible-block
locator. When reviewed grammar explicitly names a subject, the exact source label
is preserved. Its deterministic identity is filing/document/claim-local, not a
universal economic entity ID. Matching strings across filings are not unified.

Auditor/accountant predecessor wording is excluded from reporting-subject
predecessor claims. Unknown restructuring wording remains uninterpreted and makes
the source profile unsupported, rather than being classified optimistically.

There is no negative claim equivalent to `NO_PREDECESSOR`, `NO_SUCCESSOR`,
`NO_REVERSE_ACQUISITION`, `NO_SUBJECT_CHANGE`, or `CONTINUITY_ESTABLISHED`.

## Status, conflicts, and identities

Closed statuses are:

- `CAPTURED_REPORTING_SUBJECT_SOURCE_SET`;
- `INCOMPLETE_REPORTING_SUBJECT_SOURCE_SET`;
- `SOURCE_CONFLICT`;
- `UNSUPPORTED_SOURCE_PROFILE`.

Conflict has precedence. Conflicts retain all D2B variants, differing D2A bytes,
D2B/D2A form disagreement, and incompatible explicitly named subject labels within
one accession-local source scope. Accessions are separate source events by default:
form plus report date does not link filings, and an `8-K/A` is not inferred to amend
a same-date `8-K` without an explicit captured source relationship. No latest or
amendment winner exists. Unsupported status covers unsupported or malformed
eligible documents, bounds, and uninterpreted language. Unreviewed 8-K item
metadata remains an issue occurrence but does not invalidate an otherwise reviewed
captured source set. Incomplete status covers omitted D2B history or missing
relevant filing captures.

A captured status means only that the selected captured source surface replayed
under this profile. It does not mean no transition occurred.

Domain-separated identities use
`pam:sec-reporting-subject-source:{domain}:v1`. Semantic identity binds source
meaning, D2B semantics, document content semantics, signals, claims, labels,
stable issues, status, and limitations. Equal-byte recaptures and caller order do
not strengthen semantics. Evidence identity additionally binds exact D2B
occurrences, D2A receipts/times, document evidence, passage occurrences, and issue
occurrences. Paths, wall clock, randomness, and object identity enter neither.

## Authority boundary and future qualifier

PR5C0A discharges zero C3 blockers. `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED` and
`SPLIT_BASIS_NOT_ESTABLISHED` remain. PR5B is unchanged. No `AdmissionBlocker`
success tuple, `AuthorityProperty`, source-authority grant, model/runtime/V1
consumer, or Expected Return input is added. PR4C6 remains synthetic-only and is
not imported as authority.

A future PR5C qualifier must separately prove one accounting reporting subject
from the oldest required C3 EPS period through CURRENT T, assign every retained
version, and reject every unresolved transition, gap, ambiguity, or conflict.
SEC-only evidence may still be insufficient for a filer. This foundation does not
disguise that limitation.

Explicit answers:

- Does PR5C0A establish reporting-subject continuity? **NO.**
- Does it discharge `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`? **NO.**
- Does absence of a transition claim count as continuity evidence? **NO.**
- Does same CIK count as accounting-subject identity? **NO.**

## Validation result

Validation used Python 3.12.14 and the unchanged locked environment. No live SEC
request or positive-capital analysis was performed.

| Isolated selection | Tests | Result |
| --- | ---: | --- |
| PR5C0A focused | 27 | PASS |
| SEC Submissions | 101 | PASS |
| SEC filing acquisition/archive/document inventory | 99 | PASS |
| D4A/D4B temporal | 58 | PASS |
| PR5B | 31 | PASS |
| all SEC tests | 820 | PASS |
| source/current authority | 44 | PASS |
| security identity | 84 | PASS |
| Expected Return | 144 | PASS |
| runtime isolation | 29 | PASS |
| validation identity isolation | 19 | PASS |
| protected PIT | 40 | PASS |
| complete isolated suite | **2,376** | **PASS** |

The protected PIT aggregate remains
`f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
the determinism fingerprint remains
`f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
and `MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. Frozen V1 remains commit
`c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`.
