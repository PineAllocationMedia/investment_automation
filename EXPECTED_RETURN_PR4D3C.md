# PR4D3C — Historical SEC taxonomy-profile coverage for Property-4 evidence

> Extraction profile coverage only. This contract creates no Property-4
> qualification, temporal dossier, source-authority power, or economic admission.

## Verified base and scope

After `git fetch origin`, the approved integration branch
`origin/model-v2/expected-return-challenger` was exactly
`b96cc7da50b124ec955843580485f1773f0fbd91`, tree
`2e9dddd5d5e82740545394ee30a9c394bd5e1a12` (merged PR #51 / PR4D3B).
The worktree and index were clean. The dedicated branch
`codex/v2-sec-historical-taxonomy-profiles` starts directly from that verified
remote commit; existing local refs were preserved.

This PR extends only D3A and D3B's finite, offline source-profile coverage. It
does not build the PR4D4A temporal dossier or qualifier. It changes no extraction
contract version, output field, source authority, model rule, runtime, dependency,
V1 behavior, production path, or investment behavior.

## What was investigated

The investigation distinguishes five separate questions:

1. **Existence:** did an official taxonomy/schema with this namespace exist?
2. **EDGAR acceptance:** could EDGAR accept it during the target interval beginning
   2021-01-01?
3. **Concept availability:** did that exact schema declare each QName used by D3A
   or D3B?
4. **Semantic compatibility:** did the official documentation preserve the narrow
   source meaning used by the extractor?
5. **PAM support:** is the exact combination in the extractor's finite allowlist?

These are not interchangeable. A published schema is not automatically an EDGAR-
accepted profile, an accepted profile is not automatically semantically reviewed,
and successful extraction remains source claims rather than economic authority.

### Primary authoritative sources

- SEC [Operating Companies standard-taxonomy registry](https://www.sec.gov/data-research/structured-data/taxonomies-schemas/standard-taxonomies/operating-companies)
  and its historical [Standard Taxonomies](https://www.sec.gov/files/info/edgar/edgartaxonomies.shtml)
  tables.
- SEC [2021 taxonomy update](https://www.sec.gov/newsroom/whats-new/osd-announcement-032321-2021-xbrl-taxonomies-update)
  and [EDGAR Release 21.2](https://www.sec.gov/filergroup/announcements-old/edgar-release-212),
  establishing that 2019 US-GAAP and DEI remained accepted during the target
  interval until Release 21.2 removed them on 2021-06-21.
- SEC [2022 taxonomy release notes](https://xbrl.sec.gov/doc/releasenotes-2022.pdf),
  section 1.3: before the 2021 taxonomy versions, independently accepted taxonomy
  years were compatible; beginning with 2021 versions, compatible taxonomies must
  share the release year, with quarterly releases compatible within that year.
- SEC [EDGAR Release 21.4](https://www.sec.gov/filergroup/announcements-old/edgar-release-214)
  for DEI 2021Q4 acceptance and its annual-report transition rule.
- SEC [2022Q4 release notes](https://xbrl.sec.gov/doc/releasenotes-2022q4.pdf)
  for DEI 2022Q4 acceptance and exact namespace form.
- SEC [2022Q3 US-GAAP supplement update](https://www.sec.gov/newsroom/whats-new/osd-announcement-081622-xbrl-taxonomy-update)
  and [EDGAR Release 22.3](https://www.sec.gov/filergroup/announcements-old/edgar-release-223):
  the supplement is used with, and imports, core US-GAAP 2022; it is not a
  replacement namespace for the D3B target concepts.
- SEC annual acceptance announcements for
  [2023](https://www.sec.gov/newsroom/whats-new/2303-2023-xbrl-taxonomies-update),
  [2024](https://www.sec.gov/newsroom/whats-new/2403-2024-xbrl-taxonomies-update),
  [2025](https://www.sec.gov/newsroom/whats-new/2503-2025-xbrl-taxonomies-update),
  and [2026](https://www.sec.gov/newsroom/whats-new/2603-2026-xbrl-taxonomies-update).
- The exact official SEC DEI core schemas and documentation linkbases under
  `https://xbrl.sec.gov/dei/{release}/`, and exact official FASB US-GAAP core
  schemas and documentation linkbases under
  `https://xbrl.fasb.org/us-gaap/{release}/elts/`.
- SEC [EDGAR XBRL Guide, August 2026](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-08-14.pdf)
  for the current cover-page, class-context, and numeric-representation rules.

No third-party filing viewer, blog, inferred namespace, live filing, or runtime
taxonomy resolution supplied profile authority.

## Audited exact profile matrix

Abbreviations below:

- D3A facts: `Security12bTitle`, `TradingSymbol`, `NoTradingSymbolFlag`,
  `SecurityExchangeName`.
- D3A axes: DEI `EntityListingsExchangeAxis` and US-GAAP
  `StatementClassOfStockAxis`.
- D3B facts: DEI `EntityCommonStockSharesOutstanding` and US-GAAP
  `EarningsPerShareDiluted`.
- D3B axis: US-GAAP `StatementClassOfStockAxis`.

For every supported row, the exact official core schemas declare every listed
fact and axis. The documentation labels are materially unchanged across the
rows: the D3A title remains a Section 12(b) registered-security title; symbol
remains the exchange-listed instrument symbol; exchange name remains the exchange
on which the security is registered; the class axis remains information by stock
class; common shares outstanding remains the cover-page outstanding-share
assertion; and diluted EPS remains period net income/loss available per common
share including dilutive potential shares. D3A continues retaining exchange text
without interpreting its EDGAR-code type.

| Release / profile | Exact DEI namespace | Exact US-GAAP namespace | Acceptance / compatibility | D3A availability | D3B availability | Reviewed source semantics | PAM result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Legacy 2019 / 2019 | `http://xbrl.sec.gov/dei/2019-01-31` | `http://fasb.org/us-gaap/2019-01-31` | Accepted through 2021-06-20; pre-2021 compatibility rule | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| Legacy 2019 DEI / 2020 GAAP | `http://xbrl.sec.gov/dei/2019-01-31` | `http://fasb.org/us-gaap/2020-01-31` | Accepted while both releases overlapped; pre-2021 compatibility rule | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| Legacy 2020 DEI / 2019 GAAP | `http://xbrl.sec.gov/dei/2020-01-31` | `http://fasb.org/us-gaap/2019-01-31` | Accepted while both releases overlapped; pre-2021 compatibility rule | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| Legacy 2020 / 2020 | `http://xbrl.sec.gov/dei/2020-01-31` | `http://fasb.org/us-gaap/2020-01-31` | Accepted through 2022-06-20; pre-2021 compatibility rule | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2021 annual | `http://xbrl.sec.gov/dei/2021` | `http://fasb.org/us-gaap/2021-01-31` | Accepted; synchronized 2021 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2021Q4 DEI / 2021 GAAP | `http://xbrl.sec.gov/dei/2021q4` | `http://fasb.org/us-gaap/2021-01-31` | Accepted from 2021-12-20; same-release-year quarterly compatibility | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2022 annual | `http://xbrl.sec.gov/dei/2022` | `http://fasb.org/us-gaap/2022` | Accepted; synchronized 2022 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2022Q4 DEI / 2022 GAAP | `http://xbrl.sec.gov/dei/2022q4` | `http://fasb.org/us-gaap/2022` | Accepted from EDGAR 22.4; same-release-year quarterly compatibility | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2023 annual | `http://xbrl.sec.gov/dei/2023` | `http://fasb.org/us-gaap/2023` | Accepted from 2023-03-20; synchronized 2023 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2024 annual | `http://xbrl.sec.gov/dei/2024` | `http://fasb.org/us-gaap/2024` | Accepted 2024-03-18 through 2026-09-13; synchronized 2024 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2025 annual | `http://xbrl.sec.gov/dei/2025` | `http://fasb.org/us-gaap/2025` | Accepted from 2025-03-17; synchronized 2025 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |
| 2026 annual | `http://xbrl.sec.gov/dei/2026` | `http://fasb.org/us-gaap/2026` | Accepted from EDGAR 26.1; synchronized 2026 release | All 4 facts; both axes | Both facts; class axis | Compatible | `BOTH_SUPPORTED` |

The two legacy cross-year rows are not a generic cross-year rule. They are literal
combinations authorized by the SEC's pre-2021 compatibility rule while the exact
2019 and 2020 versions overlapped in EDGAR. Any 2021-or-later cross-year pair, any
other historical cross-pair, and every unlisted pair fail closed.

### 2022Q3 US-GAAP supplement

The official schema has target namespace
`http://fasb.org/us-gaap-sup/2022q3`, imports
`http://fasb.org/us-gaap/2022`, and does not redeclare
`EarningsPerShareDiluted` or `StatementClassOfStockAxis`. It is therefore an
accepted **overlay**, not a replacement D3A/D3B fact-QName profile. D3A and D3B
support that exact supplement only when the document also resolves to one of the
two reviewed core 2022 pairs:

- DEI 2022 + US-GAAP 2022; or
- DEI 2022Q4 + US-GAAP 2022.

Unknown `us-gaap-sup` releases, supplement-only ambiguity, and a 2022Q3-looking
core `us-gaap` namespace fail closed.

## Investigated and rejected profiles

| Candidate | Result | Exact reason |
| --- | --- | --- |
| DEI 2018 (`http://xbrl.sec.gov/dei/2018-01-31`) | `UNSUPPORTED` | EDGAR Release 20.3 removed it before 2021-01-01. Its official schema also lacks D3A `Security12bTitle`, `NoTradingSymbolFlag`, and `SecurityExchangeName`; constructing those QNames would be false. |
| DEI 2021Q3 or another invented quarterly namespace | `UNSUPPORTED` | No reviewed official accepted DEI release with that exact namespace. |
| DEI 2022Q3 as a core namespace | `UNSUPPORTED` | The actual Q3 release was a FASB US-GAAP/SRT supplement, not DEI. |
| US-GAAP 2022Q3 supplement as the target concept namespace | `UNSUPPORTED` | The supplement imports core US-GAAP 2022 and does not declare the D3B target concepts/axis. It is accepted only as the exact overlay described above. |
| Any 2021-or-later cross-year DEI/US-GAAP pair | `UNSUPPORTED` | SEC synchronization rules make it incompatible; EDGAR suspends the filing. |
| Any undeclared past, date-lookalike, or generic year-shaped namespace | `UNSUPPORTED` | It is not an exact reviewed profile; no regex or year range grants support. |
| 2027 DEI or US-GAAP | `UNSUPPORTED` | Not an accepted, reviewed profile for this PR. Publication or draft availability cannot grant PAM support. |

No historically relevant accepted core pair from 2019/2020 forward remains
unsupported for the D3A/D3B target concepts after this matrix.

## Implementation boundary

Each extractor retains its own literal tuple of exact supported pairs. The tuples
currently agree because the audited concepts and axes exist with compatible source
semantics in every admitted row; this does not create a shared capability contract
or require future D3A/D3B profile sets to remain identical.

There is no regex year matching, numeric year range, same-year inference, future-
year admission, runtime download, network resolution, schema discovery, concept
normalization, or cross-year QName collapse. Prefix spelling remains irrelevant;
expanded namespace identity remains bound into contexts, facts, semantic hashes,
and evidence hashes.

D3A continues to accept only the four verified fact local names under an admitted
DEI namespace and only the two verified axes under the exact compatible pair.
D3B continues to accept only the two verified numeric concepts and the exact class
axis. All D3B representation hardening remains unchanged: direct `ix:nonFraction`,
required `decimals`, rejected `precision`, exact `unitRef` resolution, and no
format, scale, sign, continuation, nil, numeric conversion, or member inference.

The existing extraction contract versions and hash domains are unchanged. The
2025 and 2026 output meanings remain unchanged; profile expansion changes neither
their semantic nor evidence identities for identical source bytes.

Exact implementation scope is limited to:

- `economic_facts/sec_registered_securities.py`
- `economic_facts/sec_class_eps_claims.py`
- `tests/sec_registered_security_fixtures.py`
- `tests/test_sec_registered_securities.py`
- `tests/sec_class_eps_fixtures.py`
- `tests/test_sec_class_eps_claims.py`
- `EXPECTED_RETURN_PR4D3A.md`
- `EXPECTED_RETURN_PR4D3B.md`
- `EXPECTED_RETURN_PR4D3C.md`

## Authority limitations

D3A and D3B still establish **zero** Property-4 properties:

| Property | Still unresolved |
| --- | --- |
| 4A | Issuer economic identity; filing CIK remains source provenance. |
| 4B | Economic security identity and durable security anchor. |
| 4C | Legal/economic class identity, status, and rights. |
| 4D | Complete relevant common-class inventory. |
| 4E | EPS applicability and entitlement to an economic class. |
| 4F | Qualified listing, quote currency, and quote unit. |
| 4G | Complete/scoped listing inventory. |
| 4H | Temporal continuity through the required interval and D1 boundary T. |

Obligations 5–7 remain unresolved: share-basis comparability,
accounting/reporting-subject comparability, and final economic admission.

There is no D1/C3 blocker removal, D2B/D2C join, C4 success object, ticker/MIC/
currency mapping, durable security ID, temporal timeline, admission token, PR4B1
input, Expected Return input, allocation, deployment, or authority promotion.
`MODEL_RULES_VERSION` remains unchanged.

## Validation and handoff

The fictional offline regression matrix covers every exact admitted pair, both
quarterly DEI variants, the 2022Q3 supplement overlay, finite legacy cross-year
compatibility, incompatible pair rejection, unknown/future/lookalike namespaces,
nested conflicts, prefix aliases, unchanged D3A conflict/no-symbol behavior,
unchanged D3B numeric hardening, custom member opacity, multiple classes/exchanges,
and unchanged authority boundaries.

Published D3A fixture identities remain:

- primary document: `ae3b0d9d0a721374b7d3f355b8d6ad826987deffc44a362aec624cd6a5065177`
- semantic: `84e9c6921b10377369f079f4fd7fab6e8822543f3310b4a341da2d857705b069`
- evidence: `d10207c2a5d4677cd5acc8e1dc0ca15e7255b9a9a390511c6d84cddf72dd70c5`

Representative D3B identities protected before modification:

| Profile | Semantic | Evidence |
| --- | --- | --- |
| 2025 | `7db512b6cbeb8287edf05a12dbf52bb69809ef34fb9952dd9683981f5d4ed162` | `4b7398fe87b8bbfeb54efd3b7ab64c326e1431d9e4e5d61da9629001016c601f` |
| 2026 | `3d52c78db301f5ec993b00784400de0a54c0d4c13e12716979ea9a0d95548b82` | `f6707ff858ece6adb1c9c1b9d8bc6447bcf9e6d8088eb0114ea7013ebd025a41` |

Validation used the unchanged isolated runner with disposable code/state/HOME,
stripped credentials, and denied network. Final executable-source results were:

| Isolated selection | Tests | Result / seconds |
| --- | ---: | --- |
| `test_sec_registered_securities.py` | 73 | PASS / 0.665 |
| `test_sec_class_eps_claims.py` | 44 | PASS / 0.377 |
| `test_sec_*.py` | 484 | PASS / 5.028 |
| `test_security_identity.py` | 84 | PASS / 0.488 |
| `test_*authority.py` | 44 | PASS / 0.152 |
| `test_expected_return*.py` | 144 | PASS / 0.548 |
| `test_runtime_isolation.py` | 29 | PASS / 27.737 |
| `test_validation_identity_isolation.py` | 19 | PASS / 0.276 |
| `test_pr2_investment_equivalence.py` | 1 | PASS / 0.086 |
| Complete isolated suite | **2,040** | **PASS / 449.947** |

The complete suite reported no failures or skips, reproduced all 64 protected
equivalence cases, and reproduced without regeneration:

- PIT: `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`
- Determinism: `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`
- Model rules: `2026-08-23-allocation-room-integrity-v7`

The test environment was Python 3.12.14 versus the repository's 3.12.13 pin.
Final whitespace, committed-HEAD, remote-base, and clean-tree checks are performed
after this validation record; exact HEAD and PR URL belong in the published
handoff because a commit cannot embed its own identity.

### PR4D4A readiness

The historical taxonomy-profile prerequisite is now sufficient to begin the
separately contracted PR4D4A real SEC Property-4 temporal evidence dossier: all
exact core DEI/US-GAAP profiles that could legitimately occur in the audited
2021-01-01-through-2026 operating-company interval are covered for the current
narrow D3A/D3B concepts, including the accepted 2022Q3 supplement overlay.

This statement removes only the taxonomy-profile prerequisite. Property 4A–4H,
obligations 5–7, filing-history/temporal completeness, economic identity, listing
qualification, continuity, and final admission all remain unresolved and require
the PR4D4A contract and later qualification work.
