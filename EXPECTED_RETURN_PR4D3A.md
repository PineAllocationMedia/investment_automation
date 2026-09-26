# PR4D3A — Offline SEC registered-security claim extraction

Implementation for review only. SOURCE CLAIM != ECONOMIC IDENTITY.

## Verified base and scope

After fetching origin, the integration branch `model-v2/expected-return-challenger`
was exactly `3ad055a1070337178d97bb1c0fbb7c4289808d4f` (merged PR #48), tree
`407f7bc3ed71706990d89cb655cd28f0e406ff83`. The initial worktree/index was clean
on `codex/v2-roadmap-architecture-refresh`. All existing local refs, including
stale main/integration refs, were preserved. The dedicated branch is
`codex/v2-sec-registered-security-claims`, created directly from that verified base.

Added files:

- `economic_facts/sec_registered_securities.py`
- `tests/sec_registered_security_fixtures.py`
- `tests/test_sec_registered_securities.py`
- `EXPECTED_RETURN_PR4D3A.md`

Modified: `tests/test_sec_filing_acquisition.py`, solely to permit the new
extractor's archive import in the existing dependency-direction test. Acquisition
imports remain forbidden there. The new extractor has its own exact dependency
allowlist and no-reverse-consumer regression.

All existing production code, D2A acquisition/archive, D2B, D2C, C3/C4–C6, D1,
source-authority powers, Expected Return, PIT, V1, model rules, dependencies,
runtime, roadmap and decisions are out of scope and unchanged.

## API and integrity

```python
extract_sec_registered_security_claims(
    archive: SecFilingArchive,
    request: SecRegisteredSecurityExtractionRequest,
) -> SecRegisteredSecurityExtractionAssessment
```

The exact frozen/slotted request contains only `filing_receipt_id`. No raw bytes,
CIK assertion, ticker, exchange, class, URL, time, as-of, callback, policy or
authority flag is accepted. Exact typed archive/request instances are required.
There is no latest selection, directory scan, acquisition, network, write or
clock read. D2A verifies receipt membership and exact object byte length/hash.
Missing/corrupt/unsafe storage propagates `FilingArchiveError`; malformed request
raises `RegisteredSecurityRequestError`. These are never ordinary weak evidence.

The pure source-local envelope reader identifies the first primary DOCUMENT,
checks accession/CIK/form linkage and document counts/boundaries, and slices exact
TEXT payload bytes without reserialization. Other exhibits remain opaque, including
binary bytes. They cannot supply a fallback primary or additional facts. D2A's
trusted local archive/acquisition model remains unchanged: these hashes are
integrity records, not external authentication or proof of issuer truth.

## Reviewed source profile

Forms: **10-K, 10-K/A, 10-Q, 10-Q/A** only. No 8-K extraction.

The source profile is UTF-8, well-formed namespace-aware XHTML, Inline XBRL 1.1
(`http://www.xbrl.org/2013/inlineXBRL`), with the four DEI concepts below in one
of the exact historical core namespace pairs audited by PR4D3C. The canonical
finite matrix, EDGAR-acceptance intervals, concept/axis availability, quarterly
variants, exact 2022Q3 overlay, and rejected candidates are recorded in
`EXPECTED_RETURN_PR4D3C.md`. It includes the reviewed 2019/2020 legacy pairs and
cross-pairs, 2021/2021Q4, 2022/2022Q4, and annual 2023 through 2026 pairs.

- `Security12bTitle`
- `TradingSymbol`
- `NoTradingSymbolFlag`
- `SecurityExchangeName`

Namespace-expanded QNames determine concept identity; lexical prefixes alone
do not. `TAXONOMY_PROFILES` is a literal finite allowlist, with no generic year
matching or taxonomy downloads/resolution. All DEI/US-GAAP family namespace
declarations in the primary document, including nested and unused declarations,
must fit one exact reviewed pair. The two pre-2021 cross-year pairs are explicit
entries rather than a generic compatibility rule. Any 2021-or-later cross-year
pair, multiple generations, unknown years, and lookalike concepts are unsupported.
The exact `http://fasb.org/us-gaap-sup/2022q3` namespace is accepted only as an
overlay with a reviewed 2022 core pair; it is never a replacement fact namespace.
An unused companion namespace need not be declared; any declared companion must
fit the resolved profile. Namespace-family prefix checks only identify
declarations to validate; they never admit a release.
Only untransformed, non-nil `ix:nonNumeric` facts are supported. `escape` may be
absent/false/0. Plain XHTML descendants contribute their exact decoded text.
Whitespace, Unicode, punctuation and descriptive title/exchange strings are
preserved; XML's specified decoding/end-of-line rules apply, while exact raw
bytes remain bound independently. A literal no-symbol assertion must be `true`
or `1`; its exact source string survives. No implicit false/absent equivalence.

Contexts must have the SEC CIK scheme and ten-digit identifier, date-only duration
period, and optionally explicit segment dimensions on:

- `us-gaap:StatementClassOfStockAxis`, in that pair's US-GAAP namespace;
- `dei:EntityListingsExchangeAxis`, in that pair's DEI namespace.

Member QNames, including custom members, are retained as source assertions.
No taxonomy download, member classification or dimensional taxonomy validation
is implied. The extractor does not validate the entire SEC/XBRL filing.

The reviewed source basis is the SEC [EDGAR XBRL Guide, February 2026,
sections 3.2.4.1–4](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-02-17.pdf):
registered securities use class contexts; exchange dimensions distinguish multiple
listings; title/exchange facts pair in the same context; symbol and no-symbol
assertions are alternatives. Source names may use transformation rules, which
this initial profile rejects rather than implementing implicitly. The
[Inline XBRL 1.1 specification](https://www.xbrl.org/specification/inlinexbrl-part1/rec-2013-11-18/inlinexbrl-part1-rec-2013-11-18.html)
and [XBRL text extraction guidance](https://xbrl.org/WGN/html-for-ixbrl-wgn/WGN-2022-12-07/html-for-ixbrl-wgn-2022-12-07.html)
were consulted for nonNumeric text, continuations, exclusions and escape semantics.
No real filing was acquired or included in tests.

## Pairing, provenance and output

Facts pair only by exactly equal supported context aspects: entity scheme/value,
period and expanded dimension/member pairs. Equivalent context IDs can share an
aspect group; all source context IDs and individual occurrences survive. There
is no pairing by HTML proximity, array positions, symbol, company name or another
provider. No dimension is discarded for pairing.

Each group retains tuples of all distinct titles, symbols, no-symbol flags and
exchange names. Identical duplicate facts add occurrences, not extra claim groups.
Conflicting values have no winner. Multiple securities remain distinct through
their source class dimensions. Multiple exchange contexts remain separate groups;
only their explicit exchange dimension is omitted in a separate **source context
scope hash** to expose the source relationship. That hash is never a PAM economic
security identity. Differing titles across those related contexts are conflicting;
different exchange-specific symbols are retained without merging them.

Mixing dimensioned and undimensioned class or exchange scopes is explicitly
ambiguous. Entity identifier disagreement with the filing envelope is a conflict,
with both assertions retained. Missing title, symbol assertion or exchange creates
incomplete evidence. No context or later duplicate supplies a heuristic fallback.

Statuses, in precedence order:

1. `SOURCE_CONFLICT`: a contradiction or ambiguous scope exists.
2. `INCOMPLETE_REGISTERED_SECURITY_CLAIMS`: supported facts lack a required pairing.
3. `CAPTURED_REGISTERED_SECURITY_CLAIMS`: all extracted groups have the supported
   source pairing; no completeness or economic identity is established.
4. `NO_SUPPORTED_REGISTERED_SECURITY_CLAIMS`: no reviewed facts found in a supported
   Inline document; this does not assert absence of registered securities.

Every successful parse retains the exact verified receipt; primary CIK/accession/
form/endpoint, zero-based DOCUMENT ordinal, sequence, filename, payload byte offset,
length and SHA-256; referenced contexts and their source order; and every fact's
expanded and lexical name, contextRef, source id, exact decoded value, language,
zero-based XML-element preorder ordinal and one-based source line. Occurrence
identity binds the primary-document evidence identity, which in turn binds the
receipt and exact document slice. Exact bytes, not a DOM serialization, prove
primary byte identity. Filename metadata is never interpreted as a filesystem path.

## Explicit unsupported cases and safety

`UnsupportedRegisteredSecuritySource` rejects malformed/ambiguous envelopes or
primary XML, non-Inline HTML/table-only filings, other forms, other DEI/axis
versions, unbound QNames, duplicate XML/context IDs, missing contextRefs, non-SEC
identifier schemes, instant/forever/timezone periods, scenario/typed/unknown
dimensions, duplicate dimensions, transformed/nil/continued/escaped/tuple facts,
nested Inline/exclusion/foreign markup within values, nondefault targets, and
empty/oversized values. No partial-success assessment masks those variants;
original evidence remains in the archive for future inspection.

In particular `ixt-sec:exchnameen`, transformed checkbox booleans, `ix:continuation`,
`ix:exclude`, namespace combinations outside the audited finite matrix and IFRS class axes
need separate review.
Rejecting these variants is an explicit initial limitation, not a claim that they
are invalid SEC filings. No HTML parser repair, provider framework, fallback
document, extension taxonomy resolution or external incorporation is attempted.

`lxml` uses strict XML mode with recovery, DTD loading, entity expansion, network
and huge-tree mode disabled, plus a denying external-resource resolver. DTD/entity
declarations are rejected before parsing. Script/style contents cannot supply
reviewed facts; other script/URL/schema/image/XInclude references are inert and
never loaded or executed. No browser, schema validator or XInclude processor runs.

PAM safety bounds: existing D2A 32 MiB source/256 KiB header/1,000 documents;
250,000 XML elements, 20,000 context definitions, 10,000 reviewed fact occurrences,
16,384 Unicode code points per value. Excess inputs raise unsupported errors;
no truncated positive result. The locked `lxml` dependency is reused unchanged.

## Deterministic identities

Frozen/slotted records contain immutable tuples. Canonical sorted ASCII JSON and
SHA-256 use distinct `pam:sec-registered-securities:{domain}:v1` domains and a
contract version. Semantics bind filing CIK/accession/form, exact extracted values,
language, expanded names, context aspects, relationships, issues and status.
They exclude context-label spelling, prefix spelling, source occurrence order,
identical duplicate multiplicity, capture time and formatting outside fact values.
Claim groups sort by their context semantic hash; occurrence order remains source
order. Source strings are not economically normalized.

The taxonomy corrections preserve this encoding and contract version. Expanded
QName namespaces deliberately remain part of source semantics: assertions across
admitted profiles can have the same retained values, exact-context pairing,
conflict behavior and source relationships, but different fact namespace
identities and assessment semantic hashes. There is no cross-profile QName
normalization or join. Existing supported 2025 and 2026 inputs retain their
original identities.

Evidence identity additionally binds the verified receipt, exact primary bytes,
offset/length/metadata, source context spellings/order, every original occurrence
and group occurrence links. Recapturing identical bytes can change evidence alone.
Formatting or prefix/order changes may change evidence alone; whitespace changes
inside a retained source value change semantics too. Paths, environment, object
addresses, randomness and implicit time enter neither identity.

## Authority limitations and exact remaining blockers

All parts of Property 4 remain **unresolved**, on every output:

| Property | Still requires independent real evidence/qualification |
| --- | --- |
| 4A | Issuer economic identity; filing CIK is only source provenance. |
| 4B | Economic security identity and durable security anchor. |
| 4C | Economic/legal share-class identity and rights. |
| 4D | Complete relevant common-class inventory. |
| 4E | Applicability/entitlement of every required EPS observation to that class. |
| 4F | Qualified listing identity, quote currency and unit. |
| 4G | Complete/scoped listing inventory, including relevant other listings. |
| 4H | Continuity throughout the required five-year interval and through D1 T. |

Obligations 5–7 remain unresolved: share-basis comparability, accounting/reporting-
subject comparability, and final economic admission. No C3/D1 blocker changes,
no synthetic C4 objects, authority-registry extension or real ER adapter exists.
No current listing, freshness, historical-as-of, publication, complete inventory,
event-free interval or economic truth follows from a filing source claim.

D2B metadata and D2C directory evidence remain separate and unqualified. No Nasdaq
imports, ticker/name joins, CIK↔ticker bridge, company_tickers resources, external
identifier providers, quote currency inference or inferred instrument type exists.
Titles saying common/preferred/ADR/fund/warrant remain text. Exchange values are
not mapped to PAM venues or MICs. No model rule changes, production deployment,
positive-capital analysis, Chromebook operation or V2 promotion is included.

## Original implementation validation and handoff

The existing environment has Python 3.12.14; the unchanged repository pin is
3.12.13. All 33 distributions match unchanged `requirements.lock`. The unchanged
isolated runner strips credentials, denies network, and uses disposable code,
state and HOME. No dependency/runtime configuration is changed.

All **61 new tests pass**, including explicit receipt selection, archive corruption,
four forms, multiple securities/exchanges, literal no-symbol assertions, duplicate
and conflicting facts, missing/mismatched contexts, malformed/non-Inline sources,
namespace/dimension attacks, duplicate context IDs, hostile references, exact
Unicode/whitespace, deterministic ordering, recaptures and non-authority boundaries.
Replay tests deny network, writes, directory scans and clocks. Actual extracted
assessments are rejected by D1, C4, the assumption constructor and ER engine.

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_*.py` (final code; includes all 61 new tests and D2A/D2B/D1/C3) | 428 | PASS / 11.046 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 2.054 |
| `test_security_identity.py` | 84 | PASS / 0.651 |
| `test_current_authority.py` | 17 | PASS / 0.006 |
| `test_source_authority.py` | 11 | PASS / 0.001 |
| `test_expected_return*.py` | 144 | PASS / 0.819 |
| `test_runtime_isolation.py` | 29 | PASS / 61.525 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.456 |
| `test_pr2_investment_equivalence.py` | 1 | PASS |
| `test_pit*.py` | 40 | PASS / 1059.493 |
| Complete isolated suite | **1,984** | **PASS / 1145.847** |

The focused selections total **862 passing tests**. The complete suite also covers
share-basis/reporting-subject regressions; no failures or skips were reported.
Both PIT and complete runs reproduced all 64 equivalence scenarios and these
protected identities, without regenerating expectations:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

During review, a regression first reproduced ignored text following an XML comment
inside a context leaf. Reading all XML-decoded text fixes that defect without
normalizing source strings. The earlier full run was stopped; the completed full
suite above ran after that correction and the 61st test. No executable code or
tests changed afterward; only this validation record was finalized. Logs are in
`/private/tmp/pr4d3a-sec-final.log`, `/private/tmp/pr4d3a-adjacent.log` and
`/private/tmp/pr4d3a-full-final.log`.

A fresh fetch before publication confirmed the same approved V2 SHA/tree and
unchanged frozen V1 at `c5fc27c82c29c2a6027eccee245098c4a072fdf1`, tree
`26a69bb0b2185ab141af0763da2d965602c8346b`. The final scope is exactly the five
files listed above. Working and staged whitespace checks pass; the committed HEAD
is checked with `git show --format= --check HEAD` before push. Commit/PR identity
is recorded in the published handoff and Git history. No merge is authorized.

Next recommended chantier: independent review of this source profile, then a
separately approved real Property-4 qualifier and temporal-coverage contract.
Extraction alone cannot close the remaining blockers. Merge and any promotion
remain owner decisions. The original implementation opened PR #49 against V2
integration; the following correction updates that same PR without merging it.

## PR #49 correction — explicit 2026 taxonomy compatibility

Before editing, `git fetch origin`, the remote branch and GitHub PR #49 all
confirmed the prior HEAD `0bd6ebaae58689323d02000c25e2e69ed3666922`, tree
`65e6db01761816e38c8e655b04825c9e54c2a80c`. PR #49 was OPEN against the same V2
integration branch; the worktree/index was clean. This is defect A: the reviewed
CURRENT US extraction profile omitted the explicitly approved 2026 pair.

Correction scope is exactly three existing files: `economic_facts/sec_registered_securities.py`,
`tests/test_sec_registered_securities.py` and this contract. No fixture helper,
existing authority-boundary test, dependency, runtime, model rule, D1, C4–C6,
D2A/B/C, Expected Return, roadmap or unrelated file changes. No additional PR,
merge, deployment or new authority is authorized.

At that correction, the extractor recognized fact/axis QNames derived only from
the two literal pairs. A document-wide namespace check rejected mixed generations before extracting
claims. Pairing, source text, provenance, conflict rules and evidence hashing are
unchanged. Seven added regression methods cover literal profile closure, equivalent
2025/2026 assertions (including multiple securities/exchanges, no-symbol, duplicate,
conflict and incomplete cases), both mixed pairs, nested mixed declarations,
unknown future/past years and namespace-prefix aliases. All pre-existing tests,
including authority-boundary tests, remain unchanged.

Completed correction validation through the unchanged isolated runner:

| Selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_registered_securities.py` | 68 | PASS / 0.558 |
| `test_sec_*.py` (includes the 68 extractor tests) | 435 | PASS / 5.231 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.291 |
| `test_security_identity.py` | 84 | PASS / 0.425 |
| `test_current_authority.py` | 17 | PASS / 0.003 |
| `test_source_authority.py` | 11 | PASS / 0.001 |
| `test_expected_return*.py` | 144 | PASS / 0.568 |
| `test_runtime_isolation.py` | 29 | PASS / 35.802 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.458 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.093 |
| Complete isolated suite | **1,991** | **PASS / 461.055** |

The adjacent selections total **829 passing tests**, including the focused 68.
All seven new regression methods pass. The full suite includes the 40 PIT tests,
all 64 equivalence scenarios, determinism, share-basis and reporting-subject
regressions, with no failures or skips. It reproduced the unchanged identities:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

No expected fingerprint was regenerated. All 33 locked distributions still match;
the existing Python 3.12.14 versus repository pin 3.12.13 difference is unchanged.
Both changed executable files were byte-compared with the active full-suite
snapshot and their saved hashes verified again before publication. No code/tests
changed after validation; only this validation record was completed afterward.
All pre-existing test methods, including authority boundaries, were independently
verified unchanged by AST comparison with the prior HEAD.

Logs: `/private/tmp/pr4d3a-2026-focused.log`,
`/private/tmp/pr4d3a-2026-adjacent.log`, `/private/tmp/pr4d3a-2026-full.log`.
A fresh fetch and GitHub check before publication again confirmed PR #49 OPEN
at the expected prior HEAD. Working/staged whitespace checks and the committed
HEAD check are required before push. This correction is a follow-up commit on
the existing PR branch, preserving the original commit and local refs.
Property 4A–4H and obligations 5–7 remain unresolved. No merge or new PR.
