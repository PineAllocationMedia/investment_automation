# PR4D3B — Offline SEC common-class / diluted-EPS source claims

> Extraction only. A source class member is not economic identity, and an EPS
> context is not proof of applicability or entitlement.

## Verified base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`95698ceab38296c135639dc1f8294fdcb7aca55c`, tree
`16f45ce07835e0e287ab31b95bd1f407349d3c33` (post-PR #50). The initial
worktree/index was clean on `codex/v2-roadmap-feature-complete-global-shadow` at
`8f7cc1fcdc8d1d19df19b218d7707dce5d12e11f`, with the same tree. The dedicated
branch `codex/v2-sec-class-eps-source-claims` starts directly from the approved
integration commit; existing local refs were preserved.

Added:

- `economic_facts/sec_primary_document.py`
- `economic_facts/sec_class_eps_claims.py`
- `tests/sec_class_eps_fixtures.py`
- `tests/test_sec_class_eps_claims.py`
- `EXPECTED_RETURN_PR4D3B.md`

Modified only for the bounded shared-reader dependency boundary:

- `economic_facts/sec_registered_securities.py`
- `tests/test_sec_registered_securities.py`
- `tests/test_sec_filing_acquisition.py`

No D2A archive/acquisition behavior, D3A public API/output semantics, source
authority, D1, C4–C6, PR4B1, Expected Return, PIT, V1, runtime, dependency,
configuration, roadmap, model rule, deployment, or Chromebook file is changed.

## Official source semantics reviewed

The current SEC [EDGAR XBRL Guide, April 2026, sections 3.2.3 and
6.4](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-04-21.pdf)
states that `dei:EntityCommonStockSharesOutstanding` uses an instant context;
its permitted cases distinguish an undimensioned assertion from multiple
class-member contexts. The same guide states that facts applying to all classes
omit `us-gaap:StatementClassOfStockAxis`, while facts specific to distinct stock
classes use explicit members on that axis. It also illustrates custom members.
These are source-context semantics only; they do not establish PAM economic
classification, class rights, inventory completeness, or EPS entitlement.

The guide identifies `us-gaap:EarningsPerShareDiluted` as the diluted-EPS
concept. The [XBRL Open Information Model XML
mapping](https://www.xbrl.org/Specification/xbrl-xml/CR-2021-02-16/xbrl-xml-CR-2021-02-16.html)
confirms that each explicit member in a fact's context supplies a taxonomy-defined
dimension and that QName prefixes resolve through in-scope namespace bindings.
Accordingly, this extractor preserves expanded axis/member QNames and never
classifies a custom member from its name.

The SEC [Operating Companies standard-taxonomy
registry](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies)
lists the exact 2025 and 2026 DEI and US-GAAP entry points. The SEC's
[2026 taxonomy update](https://www.sec.gov/newsroom/whats-new/2603-2026-xbrl-taxonomies-update)
states that 2026 taxonomies are compatible only with other 2026 taxonomies.
The implementation therefore uses a literal two-pair allowlist and does not
recognize taxonomy years generically.

## API and dependency direction

```python
extract_sec_class_eps_claims(
    archive: SecFilingArchive,
    request: SecClassEPSExtractionRequest,
) -> SecClassEPSExtractionAssessment
```

The frozen/slotted request contains exactly one `filing_receipt_id`. It accepts
no bytes, CIK assertion, ticker, security/class/listing identifier, time, authority,
completeness, applicability, policy, callback, or network option. Replay verifies
one explicit D2A receipt and exact object membership/hash. There is no latest
selection, directory scan, acquisition, network, write, clock, or model call.
Archive corruption propagates as `FilingArchiveError`; malformed selections raise
`SecClassEPSRequestError`; unsupported source representations raise
`UnsupportedSecClassEPSSource`. None becomes partial success.

The shared `sec_primary_document` module is the minimum bounded extraction of
D3A's prior D2A envelope/primary-document reader. It preserves the exact
`PrimaryDocumentProvenance` fields and published D3A primary-document hash domain.
D3A re-exports the same record and translates the shared closed error into its
unchanged public exception. Its public API, source semantics, records, statuses,
and semantic/evidence identities remain unchanged for identical fixtures. The
shared reader grants no XBRL or economic authority and is not a general filing or
XBRL framework.

## Supported source profile

Forms are exactly `10-K`, `10-K/A`, `10-Q`, and `10-Q/A`. `8-K`, foreign forms,
and international axes remain unsupported.

| Profile | DEI namespace | US-GAAP namespace |
| --- | --- | --- |
| 2025 | `http://xbrl.sec.gov/dei/2025` | `http://fasb.org/us-gaap/2025` |
| 2026 | `http://xbrl.sec.gov/dei/2026` | `http://fasb.org/us-gaap/2026` |

Mixed pairs, multiple generations, and unknown past/future generations fail
closed. Namespace-expanded QNames, not lexical prefixes, determine identity.
Taxonomy namespaces remain part of source semantics; no 2025/2026 normalization
or cross-year join exists.

Target facts are only:

- `dei:EntityCommonStockSharesOutstanding` in an instant context;
- `us-gaap:EarningsPerShareDiluted` in a duration context.

Target contexts require the SEC CIK identifier scheme and ten-digit identifier,
date-only instant/duration periods, and either no taxonomy-defined dimension or
one explicit `us-gaap:StatementClassOfStockAxis` member in the selected profile.
The exact expanded and lexical axis/member QNames survive. Scenario, typed,
duplicate, unknown, exchange, IFRS `ClassesOfShareCapitalAxis`, and other
dimensions affecting a target fact are unsupported rather than discarded.

An undimensioned diluted-EPS fact remains undimensioned. It is never copied or
assigned to extracted class members. A class-dimensioned fact retains the exact
member. Dimensioned and undimensioned diluted-EPS assertions for the same entity
and source period remain separate and produce `SOURCE_CONFLICT`; no winner or
economic interpretation is selected.

`source_class_scope_id` is deterministic only for the filing's exact CIK,
accession, form, and expanded class-axis/member relationship. It exposes a
source-local relationship between targeted facts in that filing. It is explicitly
not a `pam_security_id`, economic security/class identity, listing identity, or
cross-filing class identity.

## Numeric representation boundary

Supported facts are direct, untransformed, non-nil `ix:nonFraction` elements with
an exact `unitRef`, at most one retained `decimals` or `precision` assertion, no
numeric descendants, and an exact XML-Schema-decimal lexical value. The extractor
preserves the lexical value, unit reference, accuracy attribute, source fact ID,
lexical/expanded concept name, source line, element order, context reference, and
primary-document identity. It does not resolve unit semantics or create an
investment-ready number.

`format`, `scale`, `sign`, `continuedAt`, nil, nested numeric tagging, tuples,
non-Inline target facts, grouping separators, surrounding lexical whitespace, or
other representations fail closed. No transformation, continuation resolution,
scale/sign application, Decimal/float conversion, whitespace normalization, unit
inference, or nil substitution occurs.

The strict XML parser disables recovery, DTD loading, entity expansion, network,
and huge-tree mode and installs a denying external resolver. DTD/entity declarations
are rejected. Safety limits remain 250,000 elements, 20,000 contexts, 10,000
target facts, and 16,384 code points per lexical value.

## Conflicts, provenance, and identities

Every exact duplicate remains an occurrence. Different values or retained
representations in one exact concept/context claim produce an explicit conflict
while preserving all assertions. Multiple members, periods, amendments, and
dimensioned/undimensioned facts remain distinct. No vote, latest win, numeric
comparison, proximity pairing, title/ticker join, count join, or cross-filing
member join exists. Missing either target fact family is explicit incomplete
evidence; missing both is `NO_SUPPORTED_CLASS_EPS_SOURCE_CLAIMS`, never proof of
absence.

Canonical, domain-separated SHA-256 identities use
`pam:sec-class-eps-claims:{domain}:v1`. Semantic identity binds the exact profile,
CIK/accession/form, target concept/context/class relationships, exact lexical and
representation assertions, issues, and status. Exact duplicate multiplicity,
context-label spelling, source order, capture time, and path do not change
semantics. Evidence identity additionally binds the verified D2A receipt, exact
primary bytes/provenance, context IDs/order, every original occurrence/order, and
claim links. Recapture can change evidence without changing semantics. Paths,
environment, object identity, randomness, and implicit time enter neither identity.

## Authority limitations and remaining blockers

D3B records source assertions only and establishes **zero** Property-4 properties:

| Property | Still unresolved |
| --- | --- |
| 4A | Issuer economic identity; filing CIK is provenance only. |
| 4B | Economic security identity and durable security anchor. |
| 4C | Legal/economic share-class identity, status, and rights. |
| 4D | Complete relevant common-class inventory. Outstanding-share facts do not prove completeness. |
| 4E | EPS applicability/entitlement to the selected economic class. Context scope alone is not entitlement. |
| 4F | Qualified listing, quote currency, and quote unit. |
| 4G | Complete/scoped listing inventory. |
| 4H | Historical continuity through the required interval and D1 boundary T. |

Obligations 5–7 remain unresolved: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

No D1 blocker is removed. No C4 synthetic success object, real identity
qualification, source-authority power, PR4B1 input, Expected Return fact, score,
allocation, or production token is constructed. D2B, D2C, market data,
`company_tickers`, OpenFIGI, GLEIF, ticker/name/exchange/MIC/currency inference,
and other cross-source joins remain absent. No V1, model, runtime, deployment,
Chromebook, positive-capital, or promotion operation occurs.

## Validation and handoff

Validation uses the unchanged isolated runner with fictional offline fixtures,
disposable code/state/HOME, stripped credentials, and denied network. Final test
results on the final executable source are:

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_class_eps_claims.py` | 36 | PASS / 0.389 |
| `test_sec_registered_securities.py` | 68 | PASS / 0.812 |
| `test_sec_*.py` | 471 | PASS / 7.743 |
| `test_sec_filing_*.py` | 74 | PASS / 1.871 |
| `test_nasdaq_listed_*.py` | 89 | PASS / 1.965 |
| `test_security_identity.py` | 84 | PASS / 1.006 |
| `test_current_authority.py` | 17 | PASS / 0.014 |
| `test_source_authority.py` | 11 | PASS / 0.002 |
| `test_expected_return*.py` | 144 | PASS / 1.144 |
| `test_runtime_isolation.py` | 29 | PASS / 45.273 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.459 |
| Complete isolated suite | **2,027** | **PASS / 756.802** |

The complete suite reported no failures or skips and reproduced all 64 protected
equivalence cases and the unchanged identities below without regenerating an
expectation:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

The unchanged environment is Python 3.12.14 versus repository pin 3.12.13. Final
scope, dependency-lock, whitespace, committed-HEAD, remote-base, clean-tree, and
PR publication checks are completed after this validation record; exact HEAD and
PR URL are reported in the published handoff.

The next handoff is a separately reviewed temporal-evidence / real Property-4
qualification contract that may combine D1, D2A, D2B, D2C, D3A, and D3B while
preserving their distinct scopes and clocks. Successful extraction does not
pre-authorize that qualifier or grant economic authority. Merge, deployment, and
promotion remain owner decisions.
