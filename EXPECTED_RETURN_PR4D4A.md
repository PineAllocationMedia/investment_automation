# PR4D4A — Real SEC Property-4 temporal evidence dossier

> Evidence organization only. A temporal source-evidence dossier is not economic
> identity, historical continuity, CURRENT authority, or final admission.

## Approved base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`7c7ab13d99cd98d448ddd3ea103594085efdc80d`, tree
`c4c642fbf2e095d79ed93a237d4a72684ed8ad4d` (post-merged PR #52 / PR4D3C).
The worktree and index were clean. Branch
`codex/v2-sec-property4-temporal-dossier` was created directly from that remote
commit; divergent local refs were preserved.

This PR adds one deterministic, offline SEC-adapter dossier connecting exact D2B
inventory evidence, D2A complete-submission captures, D3A registered-security
source claims, and D3B class/EPS source claims. It changes no upstream extraction
semantics or identity, source-authority power, D1 assessment, D2C evidence, C4–C6,
Expected Return, model rule, runtime, V1, deployment, or Chromebook path.

Added:

- `economic_facts/sec_property4_temporal_dossier.py`
- `tests/sec_property4_temporal_fixtures.py`
- `tests/test_sec_property4_temporal_dossier.py`
- `EXPECTED_RETURN_PR4D4A.md`

The only existing-file changes are narrow dependency-boundary test allowlist
updates permitting the new downstream dossier to import D2B, D2A, D3A, and D3B.
No existing production module is modified.

## Public API and request closure

```python
build_sec_property4_temporal_dossier(
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    request: SecProperty4TemporalDossierRequest,
) -> SecProperty4TemporalDossier
```

The frozen/slotted request has exactly:

- `parent_submissions_receipt_id`;
- tuple `child_submissions_receipt_ids`;
- tuple `filing_receipt_ids`.

Every selector must be an exact lowercase 64-hex receipt ID. Tuples are bounded;
duplicates are rejected. Caller order is sorted before replay. There is no caller
CIK, ticker, issuer/security/class/listing identity, exchange, MIC, currency,
time boundary, completeness, continuity, qualification, admission, URL, source
bytes, callback, policy, clock, or authority flag. The source CIK comes only from
the verified D2B parent receipt.

Exact typed archive and request instances are required. The replay performs no
network, acquisition, writes, clock reads, directory discovery, mutation, or
latest selection. Missing/corrupt selected archive evidence propagates its upstream
integrity exception. Unexpected programming failures propagate.

## D2B replay and relevant filing universe

The dossier internally constructs the exact D2B request and calls
`replay_sec_submissions_inventory`; it never accepts a caller-built inventory
assessment. The only relevant forms are:

- `10-K`;
- `10-K/A`;
- `10-Q`;
- `10-Q/A`.

There is no form-family inference. `8-K`, `20-F`, foreign forms, and unrelated
forms do not enter the relevant universe. If an accession has at least one relevant
occurrence, every D2B occurrence for that exact accession is retained so a
conflicting variant cannot disappear. Standalone unrelated accessions remain in
the bound typed D2B inventory but do not become temporal filing entries.

Every retained occurrence preserves its D2B occurrence ID, semantic row ID,
source receipt, endpoint, section, position, accession, filing date, report date,
acceptance timestamp, form, primary document, and every additional retained D2B
field. Identical duplicates retain distinct occurrences. Different semantic rows
for one relevant accession produce a source conflict; no row wins. D2B range
conflicts propagate. D2B reference-closure incompleteness remains explicit.

## D2B ↔ D2A join and multiple captures

A selected D2A receipt joins only when its verified receipt CIK exactly equals
the D2B parent CIK and its exact accession occurs in the D2B inventory's relevant
universe. A missing accession, CIK mismatch, or selection outside that universe is
rejected. There is no join by accession prefix, primary filename, ticker, name,
date proximity, filing order, or report date. An accession prefix may identify a
filing agent rather than the registrant.

Each selected D2A receipt is membership-, length-, and hash-verified. All captures
for one accession are preserved:

- same accession and exact bytes at different `captured_at` values retain both
  receipts, keep semantic dossier identity stable, and change evidence identity;
- same accession and differing exact bytes retain every capture and produce
  `DIFFERING_D2A_CAPTURE_BYTES` / `SOURCE_CONFLICT`;
- there is no latest, first, majority, or capture-time winner.

After successful D3 replay, each D2B form and `primaryDocument` assertion is
compared with the verified D2A primary form and filename. Any disagreement is a
source conflict, is not silently corrected, and is not reinterpreted as a
different filing. Filename metadata never establishes identity.

## D3A and D3B replay, gaps, and conflicts

For every exact D2A receipt, the dossier independently calls D3A and D3B with a
new exact receipt-ID request. Typed upstream assessments are retained directly,
including their contract version, status, semantic/evidence identities, primary
document, contexts, claims, occurrences, and source-local relationships.

Only the reviewed upstream unsupported-source exceptions are converted to stable
gap categories `D3A_UNSUPPORTED_SOURCE` or `D3B_UNSUPPORTED_SOURCE`. Exception
text does not enter semantics. One rail can remain inspectable when the other is
unsupported. Archive corruption, invalid stored evidence, malformed dossier
selection, and programming errors are not downgraded to gaps.

Upstream statuses map without reinterpretation:

- D3A/D3B `SOURCE_CONFLICT` produces dossier source conflict;
- incomplete and no-supported-claims statuses produce explicit incompleteness;
- captured statuses retain the complete typed source-claim assessment but grant
  no economic authority.

The dossier never fabricates partial D3 claims. Historical taxonomy profiles from
PR4D3C flow through unchanged; D3A/D3B published identities are not changed.

## Accession aggregation, amendments, and chronology

Aggregation occurs only by exact accession after preserving every source
occurrence. `10-K/A` and `10-Q/A` remain independent accessions; an amendment
never replaces its original and there is no latest-amendment rule.

Occurrences are ordered deterministically by parsed source `acceptanceDateTime`,
then source `filingDate`, exact accession, and occurrence identity. Accession
entries are ordered by their full ordered occurrence chronology and accession.
This ordering is for inspection only and is not evidence authority or a winner.

The clocks remain separate:

| Field | Meaning retained by this dossier |
| --- | --- |
| D2B `filingDate` | SEC source filing-date assertion |
| D2B `reportDate` | SEC source report/period-date assertion |
| D2B `acceptanceDateTime` | SEC source acceptance timestamp |
| D2A `captured_at` | upper bound by which PAM observed the captured exact bytes |

Explicitly:

```text
acceptanceDateTime != published_at
acceptanceDateTime != available_at
filingDate != available_at
captured_at != publication time
```

Official SEC semantics distinguish EDGAR acceptance from first public website
availability; these inputs contain no exact first-availability timestamp. The
dossier exposes no `published_at`, `available_at`, `historically_known_by`,
event-free interval, or D1 authority boundary.

## Statuses and issue precedence

Closed non-authority statuses are:

- `SOURCE_CONFLICT` when relevant D2B assertions conflict, a D2B range conflicts,
  selected bytes differ for one accession, D2B/D2A metadata disagrees, or either
  D3 rail reports source conflict;
- `INCOMPLETE_TEMPORAL_EVIDENCE_DOSSIER` when no source conflict exists but D2B
  reference closure is incomplete, a relevant occurrence lacks D2A capture, a D3
  rail is unsupported, or D3 reports incomplete/no-supported claims;
- `CAPTURED_TEMPORAL_EVIDENCE_DOSSIER` only when relevant filings in the explicitly
  replayed D2B reference set have nonconflicting selected capture/extraction evidence;
- `NO_RELEVANT_PERIODIC_FILINGS` only when the closed replay contains no relevant
  occurrence and no conflict/incompleteness prevents that narrow observation.

Conflict has precedence over incompleteness, while every issue remains visible.
`CAPTURED` is not complete filing history, economic-event history, security/class/
listing history, continuous identity, or coverage through D1 T.

## Reference closure is not historical completeness

`CAPTURED_REFERENCE_CLOSURE_COMPLETE` means only that every history filename listed
by the exact selected D2B parent was explicitly supplied and replayed. It does not
prove that the SEC inventory is complete, that all economic events or identity
changes were disclosed, that no event occurred after the newest filing, or that
evidence covers the D1 CURRENT boundary. **Reference closure is not historical completeness.**

The dossier is not continuity. It organizes source evidence needed by a later
qualifier without claiming event-free intervals or cross-filing economic joins.

## Semantic and evidence identity

New domain-separated SHA-256 identities use
`pam:sec-property4-temporal-dossier:{domain}:v1`.

Semantic identity binds the dossier contract, D2B inventory semantic identity,
source CIK, every retained relevant D2B semantic assertion including duplicate
multiplicity, accession grouping, distinct upstream D3A/D3B semantic identities,
stable gap/issue categories, and status. Request order and capture time alone do
not change semantics. Equal-byte recaptures collapse only in the semantic capture
set; every selected receipt remains present in the typed dossier.

Evidence identity additionally binds the D2B inventory evidence identity, exact
D2B occurrence IDs, every exact D2A receipt/content hash/capture time, D3A/D3B
evidence identity, and occurrence provenance. Paths, environment, randomness,
object identity, and implicit time enter neither identity.

## No cross-filing economic identity inference

Equal or different ticker/title/exchange/member/share/EPS assertions are displayed
only as repeated source claims. The dossier does not decide that two filings refer
to the same or different economic issuer, security, class, or listing. In
particular:

- same ticker is not durable security identity;
- changed ticker is not broken continuity or a new economic security;
- same source class member is not durable class identity;
- different class member is not proof of a different economic class;
- D3A `source_security_scope_id` and D3B `source_class_scope_id` remain source-local
  relationships and never become cross-filing PAM IDs.

CIK and accession remain SEC-adapter provenance/selectors. They do not enter a
universal economic identity model. A future source-neutral qualifier may consume
analogous dossiers from other jurisdictions, but this PR does not implement that
framework.

## Authority limitations and exact remaining blockers

This PR grants zero new `AuthorityProperty` power and modifies no source-authority
registry or CURRENT assessment.

| Property | State after PR4D4A |
| --- | --- |
| 4A | Unresolved — filing CIK is not issuer economic identity. |
| 4B | Unresolved — repeated source claims are not durable economic security identity. |
| 4C | Unresolved — source class members/text are not legal/economic class identity or rights. |
| 4D | Unresolved — observed filing claims do not establish complete relevant class inventory. |
| 4E | Unresolved — EPS contexts do not establish applicability or entitlement. |
| 4F | Unresolved — SEC title/symbol/exchange claims do not qualify listing, quote currency, or unit. |
| 4G | Unresolved — repeated claims do not establish complete/scoped listing inventory. |
| 4H | Unresolved — dossier chronology is not continuity through the interval or D1 T. |

**Obligations 5–7 remain unresolved**: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

D1 CURRENT authority is explicitly deferred: no D2B acceptance or D2A capture
time is compared with D1 T. D2C Nasdaq Listed is explicitly deferred: it has no
CIK, durable identity, historical continuity, or quote-currency authority. There
is no market price, company-tickers, OpenFIGI, GLEIF, MIC, currency, C4 object,
PR4B1/Expected Return input, score, allocation, or admission token.

## Validation

Validation uses the unchanged isolated runner with fictional offline evidence,
disposable code/state/HOME, stripped credentials, and denied network. No live SEC
request or positive-capital analysis is performed.

Final executable-source results:

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_property4_temporal_dossier.py` | 30 | PASS / 0.406 |
| `test_sec_submissions_inventory.py` | 28 | PASS / 0.915 |
| `test_sec_filing_*.py` | 74 | PASS / 1.012 |
| `test_sec_registered_securities.py` | 73 | PASS / 0.770 |
| `test_sec_class_eps_claims.py` | 44 | PASS / 0.439 |
| `test_sec_*.py` | 514 | PASS / 5.254 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.412 |
| `test_security_identity.py` | 84 | PASS / 0.513 |
| `test_*authority.py` | 44 | PASS / 0.143 |
| `test_expected_return*.py` | 144 | PASS / 0.591 |
| `test_runtime_isolation.py` | 29 | PASS / 27.965 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.279 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.083 |
| `test_pit*.py` | 40 | PASS / 389.747 |
| Complete isolated suite | **2,070** | **PASS / 456.343** |

The complete suite reported no failures or skips, exercised all 64 PIT
equivalence scenarios, and reproduced both protected fingerprints without
regenerating expectations. Python was 3.12.14 against the unchanged repository
pin 3.12.13. Dependencies and lockfiles were not changed.

Protected expected identities must remain unchanged without regeneration:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

Published D3A identity checks:

- primary: `ae3b0d9d0a721374b7d3f355b8d6ad826987deffc44a362aec624cd6a5065177`
- semantic: `84e9c6921b10377369f079f4fd7fab6e8822543f3310b4a341da2d857705b069`
- evidence: `d10207c2a5d4677cd5acc8e1dc0ca15e7255b9a9a390511c6d84cddf72dd70c5`

Representative D3B checks remain the documented 2025/2026 semantic/evidence
identities in `EXPECTED_RETURN_PR4D3C.md`.

The 73-test D3A and 44-test D3B suites protect those published identities and
passed unchanged. `MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. Final whitespace, staged-diff,
committed-HEAD, remote-base, and clean-tree checks are completed during
publication; the resulting commit and PR identity belong in the final handoff.

## Next handoff

A future **separately reviewed** Real Fact Admission contract may consume this D4A
dossier together with the D1 CURRENT boundary, independent identity evidence,
D2C or other reviewed listing evidence, and explicit temporal-coverage rules to
evaluate actual Property-4 obligations. A possible next frontier is PR4D4B temporal
coverage / security-listing continuity qualification, but this PR does not
pre-authorize its contract, implementation, authority, merge, or deployment.
