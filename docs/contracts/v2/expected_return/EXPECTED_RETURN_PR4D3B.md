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

The current SEC [EDGAR XBRL Guide, August 2026, sections 3.2.3 and
8.6](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-08-14.pdf)
states that `dei:EntityCommonStockSharesOutstanding` uses an instant context;
its permitted cases distinguish an undimensioned assertion from multiple
class-member contexts. The same guide states that facts applying to all classes
omit `us-gaap:StatementClassOfStockAxis`, while facts specific to distinct stock
classes use explicit members on that axis. It also illustrates custom members.
These are source-context semantics only; they do not establish PAM economic
classification, class rights, inventory completeness, or EPS entitlement.

Section 8.6 (EFM 6.5.17, “Decimals Not Precision”) rejects a numeric fact with
`precision`. The supported SEC profile therefore requires exactly one valid
`decimals` attribute and rejects missing `decimals`, `precision`, and facts that
carry both. This is a source-representation constraint, not numeric conversion.

The guide identifies `us-gaap:EarningsPerShareDiluted` as the diluted-EPS
concept. The [XBRL Open Information Model XML
mapping](https://www.xbrl.org/Specification/xbrl-xml/CR-2021-02-16/xbrl-xml-CR-2021-02-16.html)
confirms that each explicit member in a fact's context supplies a taxonomy-defined
dimension and that QName prefixes resolve through in-scope namespace bindings.
Accordingly, this extractor preserves expanded axis/member QNames and never
classifies a custom member from its name.

The SEC [Operating Companies standard-taxonomy
registry](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies)
and historical registry identify the exact accepted entry points. PR4D3C audits
those releases, their EDGAR-acceptance intervals, compatibility rules, and the
availability and semantics of every D3B target QName. The implementation uses
that literal finite matrix and does not recognize taxonomy years generically.

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

The exact finite profile table is canonical in `EXPECTED_RETURN_PR4D3C.md`. It
contains the reviewed 2019/2020 legacy pairs and explicit cross-pairs,
2021/2021Q4, 2022/2022Q4, and annual 2023 through 2026 pairs. The exact
`http://fasb.org/us-gaap-sup/2022q3` namespace is accepted only as an overlay with
a reviewed 2022 core pair; it does not supply target fact or axis QNames.

Unlisted cross-pairs, multiple generations, unknown past/future generations,
generic date lookalikes, and supplement substitutions fail closed.
Namespace-expanded QNames, not lexical prefixes, determine identity. Taxonomy
namespaces remain part of source semantics; no cross-profile normalization or
cross-year join exists.

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
exactly one retained `decimals` assertion, no `precision`, no numeric descendants,
and an exact XML-Schema-decimal lexical value. Under the normative [XBRL 2.1
unit-reference rule](https://www.xbrl.org/Specification/xbrl-2.1/rec-2003-12-31/xbrl-2.1-rec-2003-12-31%2Bcorrected-errata-2013-02-20.html),
the exact `unitRef` must resolve unambiguously to an `xbrli:unit` in the same
`ix:resources`. The extractor checks only this referential integrity; it does not
interpret, normalize, or qualify the unit's economics. It preserves the lexical
value, unit reference, decimals assertion, source fact ID,
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
| `test_sec_class_eps_claims.py` | 39 | PASS / 0.403 |
| `test_sec_registered_securities.py` | 68 | PASS / 1.267 |
| `test_sec_*.py` | 474 | PASS / 8.378 |
| `test_security_identity.py` | 84 | PASS / 0.656 |
| `test_current_authority.py` | 17 | PASS / 0.009 |
| `test_source_authority.py` | 11 | PASS / 0.001 |
| `test_expected_return*.py` | 144 | PASS / 1.114 |
| Complete isolated suite | **2,030** | **PASS / 737.286** |

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
