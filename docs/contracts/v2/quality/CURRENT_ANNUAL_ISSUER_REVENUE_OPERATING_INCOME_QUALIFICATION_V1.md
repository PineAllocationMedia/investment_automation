# CURRENT annual issuer Revenue / Operating Income qualification — proposed v1

**PROPOSED / NOT_IMPLEMENTED / NO_RUNTIME_AUTHORITY**

Work Order: `WO-STAGE-C-ISSUER-LEVEL-REPORTED-PROFITABILITY-NATIVE-PATH-V1`.
Phase 1 is contract preparation only. Every SHALL below is a proposed future
requirement, pending independent Architecture & Audit review and CEO approval;
none is a claim of implemented behavior or ratified methodology.

## 1. Identity, scope and decision gate

| Field | Proposed value |
| --- | --- |
| Contract identity / evidence kind | `CURRENT_ANNUAL_ISSUER_REVENUE_OPERATING_INCOME_QUALIFICATION_V1` |
| Contract version | `2026-10-12-current-annual-issuer-revenue-operating-income-qualification-v1` |
| Qualification policy version | `2026-10-12-issuer-apparent-annual-endpoint-common-filing-v1` |
| Identity version | `2026-10-12-issuer-reported-profitability-evidence-identities-v1` |
| Result type | `CurrentAnnualIssuerRevenueOperatingIncomeQualificationV1` |
| Proposed module | `economic_facts.sec_current_annual_issuer_revenue_operating_income` |
| Proposed factory | `qualify_sec_current_annual_issuer_revenue_operating_income_v1(archive, receipt_id)` |
| Authority, if subsequently implemented and approved | `CURRENT_ISSUER_REPORTED_PROFITABILITY_EVIDENCE_ONLY` |
| Source / temporal mode | `SEC_COMPANYFACTS_SNAPSHOT` / `CURRENT_CAPTURE_BOUND_ONLY` |

The economic question is whether one specified authentic CURRENT capture supports
one exact, source-reported issuer annual Revenue / Operating Income pair. This is
independent of PR5C and Ordinary Compounder eligibility. CIK is an SEC adapter
issuer identifier, not a core economic security identifier. Establishment means
source-presented issuer scope within a common filing presentation; it establishes
neither security-class eligibility nor cross-period legal-entity/accounting-subject
continuity. Companyfacts accession metadata is not an independently captured 10-K.

This proposal supplies evidence only to the separately versioned
[issuer diagnostic route](CURRENT_ANNUAL_ISSUER_OPERATING_INCOME_TO_POSITIVE_REVENUE_DIAGNOSTIC_V1.md).
It does not replace or revise the
[existing v1 foundation](CURRENT_ANNUAL_REVENUE_OPERATING_INCOME_QUALIFICATION.md).

The supplied Architecture & Audit handoff
`WO-STAGE-C-QUALITY-QUALIFICATION-DECOUPLING-DESIGN-AUDIT` is `CONDITIONAL`,
as reported by the assigning Work Order. That is design-analysis context only;
no further audit findings or implementation approval are inferred. The repository
state says no next implementation is selected; this later CEO dispatch authorizes
only these two draft documents, not Phase 2 or a governance-state update.

The October 11 [Option A decision](../../../../DECISIONS.md) and
[PR #135](https://github.com/PineAllocationMedia/investment_automation/pull/135)
remain unchanged. A future positive result on this new foundation SHALL NOT count
toward Stage-C completion without an explicit CEO-approved Option A supplement
admitting this route to the exit criterion. Contract approval, implementation
release, authentic-positive validation, any supplement, Stage-C closure and
Stage-D transition are distinct gates. None follows automatically from a PR merge.

## 2. Exact input and authenticated source replay

The public factory SHALL accept only an exact `SecArchive` and an exact string
containing one lowercase 64-hex receipt selector. No subclass, mapping, detached
receipt, financial amount, caller CIK, period, preferred accession, qualification
flag, source claim, research candidate or Ordinary Compounder profile is accepted.

It SHALL read the selected stored receipt and exact object, verifying:

1. Archive membership, safe native archive reads, exact selector/receipt identity,
   closed receipt schema and `SEC_COMPANYFACTS_SNAPSHOT` source kind.
2. Receipt schema `2026-09-10-sec-capture-receipt-v1` and LIVE acquisition contract
   `2026-09-11-sec-live-companyfacts-v1`; OFFLINE receipts are rejected.
3. Exact byte length and SHA-256, without rewriting or normalizing source bytes.
4. Canonical endpoint and source locator equal to `endpoint_for(receipt.cik)`;
   exact ten-digit receipt CIK equals the normalized, present source CIK.
5. Canonical UTC capture timestamp and all native receipt integrity requirements.

Use [SecArchive](../../../../economic_facts/sec_archive.py), its
[archive contract](../expected_return/EXPECTED_RETURN_PR4C1.md) and
[LIVE acquisition contract](../expected_return/EXPECTED_RETURN_PR4C2.md).
No acquisition, network, current clock, archive mutation, receipt catalog search,
implicit latest receipt or historical cutoff selection occurs. CURRENT means
capture-bound evidence, not a freshness guarantee.

Missing/corrupt receipt or bytes, hash/length/CIK mismatch, absent source CIK,
unsupported acquisition contract, malformed structural JSON, duplicate keys and
invalid public inputs are contract/integrity errors in the native `ArchiveError`
family. They SHALL NOT become economic unavailability or a `SOURCE_CONFLICT`
result. This deliberately follows the research capture boundary, not the legacy
profile-based foundation's replay-conflict projection. Error messages SHALL NOT
expose private archive paths, contact values or full source payloads.

LIVE provenance is trusted-local-process acquisition provenance, not remote SEC
cryptographic attestation. Hashes do not protect against replacement of the entire
archive and trust anchors or arbitrary hostile execution in the Python process.

## 3. Extraction and exact reported meaning

Reuse [the existing extractor](../../../../economic_facts/sec_revenue_operating_income.py),
version `2026-10-07-sec-revenue-operating-income-extraction-v1`, for exactly:

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`;
- `us-gaap:OperatingIncomeLoss`.

Positive qualification requires exact `USD` and source-presented `US_GAAP`.
Preserve each original finite `Decimal`, including zero and negative amounts,
and its raw row, namespace/concept/unit, dates, FY/FP, form, filed date, accession,
optional frame, row pointer, semantic locator and observation identities. Do not
convert via binary float, round, normalize, annualize, reconstruct, convert currency
or substitute aliases, other revenue concepts, issuer extensions or EBIT/EBITDA.
Equivalent Decimal encodings have equal economic meaning; original row evidence
remains available. If equal values have different Decimal encodings, retain every
original observation; a scalar representative may be selected deterministically
by the smallest selected observation ID only after exact numerical consensus.

The full extraction inventory includes both concepts in all units and contexts.
Malformed structures are errors; missing/invalid row values remain inspectable
limitations. Unknown material row extensions or unresolved XBRL context are not
silently accepted. Missing evidence is never zero or a negative Quality conclusion.
The reviewed revenue concept does not prove universal total-revenue completeness.

## 4. Annual surveillance before admissibility filtering

Adapt the bounded selection logic and corrected regressions from
[PR #143](https://github.com/PineAllocationMedia/investment_automation/pull/143),
[its implementation](../../../../economic_facts/sec_current_annual_reported_fact_research_candidate.py)
and [research contract](../research/CURRENT_ANNUAL_REPORTED_FACT_RESEARCH_CANDIDATE.md).
This is reuse of source-selection mechanics, not conversion of
`CANDIDATE_COHERENT` into native authority.

Inspect every extracted row before filtering by USD, valid value, form or context.
An observation is apparently annual if any of the following holds:

- Explicit `fp=FY`, independently of other metadata.
- Valid dates give an inclusive duration of 364–371 days, independently of form/FP.
- Start/end or fiscal metadata is incomplete and an annual `10-K`/`10-K/A` form,
  or remaining integer FY without explicit quarterly FP, leaves annual relevance
  unresolved. Integer FY alone is filing-vintage metadata, not annual proof.

Preserve the corrected interactions: a 10-K/Q4 row with missing start remains
under surveillance; a 10-Q/Q4 row with integer FY and missing start is not inferred
annual solely from FY. Explicit FY and annual-length duration independently take
priority. A newer short 10-K with missing FP/FY remains unresolved annual evidence.

Choose the maximum valid end date across apparently annual rows from either
concept. Any apparently annual row with unlocatable/invalid end blocks establishment
because its relative position cannot be determined. Absence of any apparent annual
row is unavailable. A newer adverse endpoint SHALL prevent older-period fallback,
even when it contains only one concept, non-USD facts, invalid values, unsupported
forms, missing metadata, competing starts or conflicts.

At that endpoint require one unambiguous interval of exactly 365 or 366 inclusive
days. Unsupported annual intervals, reversed dates, 364/371-day fiscal years,
transition/stub periods and unresolved alternate starts block establishment.
Clearly identified shorter quarterly facts remain excluded and traceable, not
alternative annual intervals. No fiscal alignment, year-end inference or window
shopping is permitted.

For each admissible observation require exact FY, form `10-K` or `10-K/A`, valid
integer filing-vintage FY (not bool), canonical dates and SEC accession grammar
`[0-9]{10}-[0-9]{2}-[0-9]{6}`. Require `period_end <= filed <= capture UTC date`.
Do not equate filing-vintage FY with the economic period's calendar year. Frame
absence/differences alone do not disqualify a pair. The temporal claim is only
latest observed supported annual evidence inside this one capture, never complete
filing coverage, absolutely newest issuer period, publication time or PIT knowledge.

## 5. Common-filing agreement

After surveillance, identify all admissible rows for the unique target interval
and all accessions with both reviewed concepts. At least one common accession is
required. Within every common accession require one coherent form, filed date and
FY across both concepts. Across every common accession require one distinct exact
Revenue value and one distinct exact Operating Income value. Equal duplicates
are allowed and retain their separate row evidence.

Competing paired values or contradictory common-filing metadata are conflicts.
No latest/amended filing preference, majority vote, averaging or winner selection
is allowed. A fully adjudicated orphan with no paired concept in its accession is
excluded and cannot by itself manufacture paired-value conflict. A potentially
comparable row with unresolved material context at the target boundary is unsupported,
not a safely ignorable orphan. Preserve all selected, excluded, orphan and competing
references and reasons, including older-period and nonannual observations.

## 6. Closed result states and reasons

Use new native enum types; equal reason strings do not make research or legacy enum
instances acceptable. The reason vocabulary below intentionally reuses PR143's
bounded grammar; legacy `UPSTREAM_PROFILE_*` reasons have no meaning on this route.

| State | Closed applicable reasons |
| --- | --- |
| `PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED` | Empty reasons; all establishment conditions satisfied |
| `EVIDENCE_UNAVAILABLE` | `NO_APPARENT_ANNUAL_PERIOD`, `REVENUE_UNAVAILABLE`, `OPERATING_INCOME_UNAVAILABLE`, `FINITE_VALUE_UNAVAILABLE`, `NO_COMMON_ANNUAL_ACCESSION` |
| `EVIDENCE_UNSUPPORTED` | `ANNUAL_ENDPOINT_UNLOCATABLE`, `ANNUAL_INTERVAL_UNSUPPORTED`, `ANNUAL_INTERVAL_AMBIGUOUS`, `UNSUPPORTED_FILING_CONTEXT`, `UNSUPPORTED_UNIT_OR_ROW_CONTEXT`, `POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED` |
| `SOURCE_CONFLICT` | `INVALID_FILING_CHRONOLOGY`, `COMMON_FILING_METADATA_CONFLICT`, `COMPETING_REVENUE_VALUES`, `COMPETING_OPERATING_INCOME_VALUES` |

Reasons SHALL be unique and sorted lexically. Accumulate applicable reasons across
fully inspected relevant rows; precedence is conflict, unsupported, unavailable.
Absent reasons imply establishment only after complete replay/adjudication.
Missing admissible concept groups add the corresponding unavailable reason; no
common accession adds `NO_COMMON_ANNUAL_ACCESSION`. Missing/nonfinite row values
add `FINITE_VALUE_UNAVAILABLE`; non-USD relevant annual rows add
`UNSUPPORTED_UNIT_OR_ROW_CONTEXT`. Extraction issues remain separately inspectable.
Unknown states/reasons and impossible reconstructed combinations are programming
contract errors, not a new economic status.

Every non-established result SHALL have both scalar facts `None`, empty selected
observation IDs and empty established supporting-filings tuples. A separately
named adjudication inventory may retain raw observed values and competing filing
metadata, explicitly unqualified; it SHALL NOT expose partially selected facts.
Known target endpoint and interval may remain for diagnosis without implying
establishment. A conflict or unsupported result never emits an available ratio.

## 7. Immutable result and replay binding

The proposed result SHALL expose frozen, exact typed fields covering:

- All versions, kind, native status/reasons, authority and fixed limitations.
- Source CIK, accounting namespace/basis, exact ordered concepts, unit and temporal mode.
- Target endpoint and unique interval when determinable; both scalar facts only if established.
- Receipt ID, object hash/byte length, capture timestamp, canonical source locator,
  acquisition and extraction versions.
- Complete relevant extraction-inventory commitment, extraction issues and immutable
  adjudication references, including row locators, observation semantic/evidence IDs,
  dispositions, exclusion reasons and material competing exact value sets.
- Established supporting accessions, each with one form/date/FY and nonempty sorted
  unique observation-ID tuples for both concepts; their exact disjoint union equals
  selected IDs. No ID crosses concepts or accessions.
- Separately computed `semantic_id` and `evidence_id`.

A result SHALL additionally retain a private replay binding to the exact archive
and receipt used by its native factory. This is a local read capability, not a
public caller-supplied authority token or a financial fact. Do not include its
filesystem path or Python object identity in identities, export or diagnostics.
Do not duplicate the full Companyfacts payload or create a generic evidence framework.

The native consumer SHALL verify that binding by rereading the exact receipt and
object and recomputing the entire proposed qualification from source, then comparing
all public fields and identities with the supplied object. Exact type, frozen
fields, private constructors, claimed hashes or a cached success boolean alone are
insufficient. No result may provide its own validation callback. Validation uses
trusted module code and one verified replay snapshot, not overridable object methods.

Detached/serialized objects are not accepted as native evidence. To restore across
processes, supply the exact archive and receipt to the native factory again. Archive
loss/corruption causes an integrity error, not acceptance from cached fields. A
reconstruction that exactly equals a fresh authenticated replay conveys no additional
claim; it is accepted only on the strength of that replay. Changed amounts, omitted
newer rows, fabricated support and a replaced receipt with stale evidence all fail.
No Python mechanism claims security against arbitrary process or trust-anchor control.

This bounded replay binding is a proposed design choice for independent review.
It intentionally permits archive reads in this new consumer boundary; it changes
neither the legacy pure analyzer nor SecArchive's public contract.

## 8. Deterministic identity separation

Use SHA-256 with separate versioned semantic, evidence and extraction-inventory
domains; canonical sorted JSON, exact context-independent Decimal encoding, sorted
set-like tuples and no float conversion. Semantic identity binds versions, kind,
status/reasons, source CIK, accounting meaning, target dates, exact paired values
when established, material competing value sets, authority and limitations.
It excludes receipt/object hashes, timestamps, row positions, accessions and paths.

Evidence identity binds semantic identity plus exact receipt and object identity,
length, capture/acquisition/extraction provenance, the complete relevant extraction
inventory commitment, selected and excluded observation identities/locators,
adjudication dispositions/reasons and all filing support. Inventory identity binds
every extracted observation identity and locator plus extraction issues/version,
receipt and object, so omitted surveillance evidence changes the commitment.
Native validation recomputes all three identities; self-consistent hashes alone
never prove capture membership or truth.

Unchanged economics under legitimate recapture SHALL preserve semantic identity
and distinguish different receipts in evidence identity. Row reordering or irrelevant
added rows can change evidence identity without changing economic semantics. Changed
issuer, target period, fact value, status or material conflict changes semantics.
`100/20` and `200/40` are different fact semantics despite equal ratios. Numeric
forms `100`, `100.0` and `1E+2` have equal semantic numeric encoding. Repeated captures
of the same bytes do not prove independent issuer coverage.

## 9. Authority, compatibility and reuse

The fixed limitation set SHALL explicitly deny security-class eligibility, Ordinary
Compounder eligibility, EPS comparability, corporate-action/share-basis and cross-
period reporting-subject continuity; complete issuer coverage; universal total
revenue or cross-issuer/sector comparability; normalization, historical trends,
overall Quality, Durability, Confidence, Expected Return, investment admission,
ranking, allocation, sizing, execution, production, deployment, PIT/HISTORICAL_AS_OF
and V2 promotion. The only downstream permission proposed is the paired CURRENT
issuer research diagnostic. Missing/unsupported evidence is not bad-company evidence.

PR4C3, PR5B, PR5C v1, Ordinary Compounder v2, all existing Quality v1 contracts/types
and the research-candidate authority SHALL remain unchanged. No inheritance,
conversion, widening of legacy input types or candidate-to-native promotion is
permitted. No new external services, sources, dependencies or financial-data costs.
V1 stays frozen, V2 stays challenger, tuning stays `PROPOSAL_ONLY` and model rules
remain `2026-08-23-allocation-room-integrity-v7`.

### EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT

External component adoption: `NOT APPLICABLE` for this two-document phase; no
external technology search, license clearance or incorporation is claimed. The
bounded future design compares only existing repository resources at verified base
`eff6289c62fb1146fc1b0b5d2961af9c90ac624c`:

| Resource / source | Recommendation and limitation | Mandatory incremental external expenditure |
| --- | --- | --- |
| SecArchive and receipt verification, linked in section 2 | REUSE; existing integrity and trusted-local LIVE boundary, no new attestation claim | None for local replay on existing equipment |
| Existing Revenue / Operating Income extractor, linked in section 3 | REUSE; exact numbers and row lineage, no source substitutions | None; existing standard-library code |
| PR143 surveillance and existing exact numeric identity/arithmetic conventions | ADAPT selection mechanics into this bounded native factory; BUILD only new typed qualification/replay boundary, no candidate status conversion | None; no added package, service, subscription or hardware requirement proposed |

These are internal reuse recommendations, not a declaration of a third-party
open-source license or commercial redistribution permission. Existing source-use
restrictions persist; data redistribution/commercial-use clearance is not established
here and remains a separate Commercial & Compliance/CEO gate. No model weights,
datasets or external code are downloaded. Maintenance cost is duplication/drift risk;
future regressions must preserve PR143 surveillance cases without altering its authority.

Per [execution environments](../../../operations/PAM_EXECUTION_ENVIRONMENTS.md),
existing Python/POSIX archive mechanisms fit the development design; this new route
has no runtime benchmark yet. Memory includes full decoded Companyfacts plus relevant
rows; replay adds CPU and transient memory, with deterministic sorting of inventory.
No GPU, weights, new installation, paid API or external compute is required by the
design. Peak RAM/time and sustained resource fit are UNKNOWN. Chromebook has 2.7 GiB
reported RAM, no swap and Python 3.11.2 versus pinned development 3.12.13: compatibility
is not established. Do not infer operational fit from Mac validation or modify production.

## 10. Future validation and authentic-positive gate

This is a plan, not executed implementation tests. Future authorization SHALL require
fictional adversarial tests for:

- Correct bytes with wrong/missing receipt; malformed selector, OFFLINE receipt,
  corrupt bytes, hash/length/CIK mismatch, unsafe archive links and missing source CIK.
- Missing concepts/units/values, contradictory paired amounts, multiple agreeing and
  competing accessions, amendment conflicts, orphan handling and complete inventory.
- Missing/contradictory FY/FP/form/accession/filed metadata, invalid chronology,
  frame differences and unknown row extensions.
- 365/366 positives; unsupported 52/53-week and transition periods; ambiguous starts;
  unlocatable/newer adverse evidence; all three corrected PR143 surveillance interactions.
- Forged exact-type objects including recomputed IDs, removed inventory, changed facts,
  changed receipt, stale binding, detached objects, research/legacy type injection,
  and corruption after factory construction but before diagnostic consumption.
- Recapture/row-order/irrelevant-row identity invariants, equal ratios with different
  economics, original Decimal preservation and hostile Decimal contexts.
- Zero/negative Revenue evidence establishment without a positive-denominator claim;
  negative/zero Operating Income; legacy native behavior and exact-type isolation.

Use pinned Python/locked dependencies and the isolated runner. Include targeted and
adjacent archive, extraction, research, legacy Quality and Ordinary Compounder
regressions, then canonical preflight on the complete change set: STANDARD or FULL_PIT
as classified, unknown paths fail toward FULL_PIT. Never force DOCS_ONLY for code.
Preserve model rules, protected PIT/determinism fingerprints and Git integrity checks.

Authentic-positive applicability requires independently verified immutable LIVE
bytes and exact receipt, fresh native `PAIRED_ISSUER_REPORTED_FACTS_ESTABLISHED`,
associated native `AVAILABLE` issuer diagnostic, and independent full source-to-result
replay with preserved provenance/identities. A reported research replay, fabricated
LIVE fixture, synthetic suite or acquisition alone is insufficient. No authentic
positive is claimed or acquired in Phase 1; later use/acquisition needs its own scope.

## 11. Phase-1 delivery boundary

Verified canonical base branch: `model-v2/expected-return-challenger`.
HEAD: `eff6289c62fb1146fc1b0b5d2961af9c90ac624c`.
Tree: `bf68acd19886bc3cbce659770d7a9c40ce8683fc`.

Scope is exactly this new document and its linked new diagnostic contract. All
existing contracts, source, tests, model rules, protected documents and governance
status files are out of scope. Validate document consistency, UTF-8, Markdown,
relative links, exact two-file scope and Git integrity; run canonical
`./pam_preflight --base eff6289c62fb1146fc1b0b5d2961af9c90ac624c` on the committed
candidate snapshot, expecting DOCS_ONLY without overriding actual classification.
Verify delivered tree equals the validated tree. No implementation tests in Phase 1.

Commit/push/open the contract-draft PR, report observed CI/mergeability without
polling, and stop. No merge or Phase 2. Independent Architecture & Audit review is
next; the Program Manager integrates findings and obtains CEO contract approval
and a separate implementation release. This proposal does not close Stage C.
