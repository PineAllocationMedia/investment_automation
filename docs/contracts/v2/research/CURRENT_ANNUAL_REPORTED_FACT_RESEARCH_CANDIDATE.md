# V2 — CURRENT Annual Reported Revenue / Operating Income Research Candidate

**CEO_APPROVED_DESIGN_REFERENCE_ONLY — NOT_IMPLEMENTED — NO_RUNTIME_AUTHORITY**

**Work Order:** `WO-V2-CURRENT-ANNUAL-REPORTED-FACT-RESEARCH-CONTRACT-DRAFT-V1`

**CEO design-reference approval:** 2026-10-11 (Toronto local date).
**Governance Sync:** `WO-GOV-SYNC-V2-RESEARCH-CANDIDATE-CONTRACT-ADOPTION`.
**Original drafting-source SHA-256:** `9e5606934b6eaf70d60bd5afb55710347195bc147bbc6508aeebd06201cd1a8b`.


## 1. Contract identity and authority

The following identifiers are CEO-approved as design-reference identifiers only and have no current runtime authority.

| Field         | Approved design-reference identity                                                     |
| ------------- | --------------------------------------------------------------------- |
| Contract      | `2026-10-11-current-annual-reported-fact-research-candidate-v1`       |
| Evidence kind | `CURRENT_ANNUAL_REPORTED_REVENUE_OPERATING_INCOME_RESEARCH_CANDIDATE` |
| Result type   | `CurrentAnnualReportedFactResearchCandidate`                          |
| Authority     | `CURRENT_CAPTURE_RESEARCH_CANDIDATE_ONLY`                             |
| Source        | `SEC_COMPANYFACTS_SNAPSHOT`                                           |
| Temporal mode | `CURRENT_CAPTURE_BOUND_ONLY`                                          |

**Economic question**

Within one explicitly selected, authenticated SEC Companyfacts LIVE capture, does the observed source evidence support a coherent reported annual pair of Revenue and Operating Income for the latest annual period identifiable under this contract's supported grammar?

An established candidate means **coherent source-reported evidence**, not qualified native economic facts or analytical eligibility.

## 2. Exact public input and trust boundary

The only accepted inputs SHALL be:

1. An exact `economic_facts.sec_archive.SecArchive` instance.
2. One exact lowercase 64-hex immutable Companyfacts receipt identifier.

No caller-selected CIK, period, accession, fiscal-year anchor, numeric value, preferred filing, authority token, qualification boolean or detached source observation SHALL be accepted.

The evaluator SHALL:

- Read the exact stored receipt and object from the supplied archive.
- Verify receipt membership, identity, byte length and SHA-256.
- Require the existing native LIVE acquisition contract `2026-09-11-sec-live-companyfacts-v1`.
- Verify the canonical Companyfacts endpoint and source locator, receipt CIK and extracted source CIK agree.
- Preserve the exact source receipt and original bytes without rewriting them.

OFFLINE-supplied receipts, foreign CIKs, malformed selectors, detached receipts, corrupt objects and unsupported receipt contracts SHALL NOT establish a candidate. Invalid inputs and integrity failures SHALL raise closed contract/integrity errors, not economic `EVIDENCE_UNAVAILABLE`.

The LIVE acquisition identity provides the existing trusted-local-process provenance, **not cryptographic remote SEC attestation**.

The evaluator SHALL perform no network request, acquisition, clock read, archive mutation or implicit selection of a different receipt.

## 3. Supported observation grammar

The only permitted accounting facts are:

- `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`
- `us-gaap:OperatingIncomeLoss`

Required unit: exact `USD`. Accounting basis: source-presented `US_GAAP`.

The existing `extract_revenue_operating_income` extractor SHALL be used to preserve each original observation's exact `Decimal`, CIK, concept, unit, period, fiscal metadata, form, filed date, accession, optional frame, original source-row representation and semantic/evidence identities.

For positive annual pairing, observations SHALL have:

- Finite exact Decimal values, including legitimate zero and negative reported amounts.
- Valid exact `start` and `end` dates, with `start <= end`.
- Exact `fp=FY`.
- Form `10-K` or `10-K/A`.
- Valid SEC accession and filing-date metadata.
- Valid integer `fy` with coherent accession-local meaning.
- No unresolved material context or metadata limitation.

Reported `fy` SHALL be preserved as filing-presentation metadata and SHALL NOT automatically be equated to the year of the underlying comparative period.

`frame` differences alone SHALL NOT establish a conflict.

Unsupported concepts, aliases, issuer extensions, other units, adjusted figures, EBIT/EBITDA, arithmetic reconstructions, conversions and inferred amounts SHALL NOT substitute for the two exact source facts.

Material unknown row extensions or unresolved context semantics at the selected annual boundary SHALL prevent establishment rather than being assumed harmless.

## 4. Deterministic capture-bound period selection

### 4.1 Full relevant inventory

The evaluator SHALL inspect every extracted observation for both reviewed concepts, including non-USD units and otherwise ineligible filing contexts for the purpose of detecting potentially newer annual evidence.

For temporal surveillance, an observation is **apparently annual** when at least one of these conditions holds:

- It explicitly reports `fp=FY`.
- Its valid start/end dates represent 364–371 inclusive days, regardless of form or `fp`.
- Its period metadata is incomplete but its supported annual-filing form or remaining FY metadata leaves annual relevance unresolved.

Other clearly identified quarterly or shorter-duration facts SHALL remain visible but SHALL NOT become annual candidates.

The surveillance inventory is broader than the positive-admissibility inventory. Its purpose is to prevent adverse or incomplete newer evidence from disappearing before period selection.

### 4.2 Latest apparent endpoint

The target endpoint SHALL be the maximum valid period-end date among apparently annual observations from either reviewed concept.

If there is no apparent annual evidence, return `EVIDENCE_UNAVAILABLE`.

If an apparently annual observation lacks a locatable or valid end date and its relative position cannot be established, return `EVIDENCE_UNSUPPORTED`. Do not assume it belongs to an older period.

A newer apparent annual endpoint SHALL block fallback to an older coherent pair, even if evidence for the newer endpoint is incomplete, conflicting or unsupported.

### 4.3 Supported annual interval

For the target endpoint, positive establishment requires one unambiguous annual start/end interval satisfying:

- An inclusive duration of exactly 365 or 366 days.
- Coherent `FY`/annual-form presentation.
- No contradictory candidate annual interval for that endpoint.
- No unresolved transition or material context evidence that prevents identifying the supported interval.

A known shorter nonannual fact ending on the same date is not itself an alternative annual interval; it is retained as excluded evidence.

A 364-day/52-week or 371-day/53-week annual presentation, an unresolved fiscal transition, incompatible annual starts or another unsupported apparent annual context SHALL yield `EVIDENCE_UNSUPPORTED` rather than a shifted, annualized or inferred interval.

No preceding-year substitution, fiscal-window shopping, artificial year-end alignment or caller preference is permitted.

### 4.4 Chronology

Four concepts SHALL remain separate:

- Economic period start/end.
- Filing-vintage `fy` and fiscal-period `fp`.
- SEC-reported `filed` date.
- Local archive `captured_at` timestamp.

For an admissible filing, `period_end <= filed <= capture UTC date` SHALL hold. Contradictory chronology prevents establishment.

`captured_at` establishes the local observation boundary only. It does not establish SEC publication time, historical availability, completeness through capture time, or what PAM knew at an earlier cutoff.

The sole permitted temporal claim is **latest observed supported annual evidence within the specified CURRENT capture**.

## 5. Common-filing qualification and conflict discipline

After selecting the exact target period, the evaluator SHALL:

1. Identify all fully admissible Revenue observations and all fully admissible Operating Income observations for that period.
2. Identify every SEC accession containing at least one admissible observation for **both** concepts.
3. Require at least one such common accession.
4. Require one coherent form, filed date and filing-vintage `fy` within each common accession.
5. Compare **every** admissible paired Revenue value and **every** admissible paired Operating Income value across all common accessions.

A candidate SHALL be coherent only if the paired observations yield exactly one distinct Revenue value and exactly one distinct Operating Income value under exact Decimal numerical equality.

No majority vote, latest filing preference, amendment preference, averaging, rounding, arbitrary representative selection or conflicting-value suppression is permitted.

An **orphan** observation present for only one concept, with no corresponding admissible observation for the other concept in that accession, SHALL remain visible as excluded evidence. It SHALL NOT, by itself, manufacture a conflict between fully qualified common pairs.

A potentially comparable observation with unresolved context or material metadata at the target endpoint SHALL NOT be silently treated as safely irrelevant. Where its relation to the admissible pairs cannot be determined, establishment SHALL remain unsupported.

All selected, competing, orphan, nonselected, and materially excluded relevant observations SHALL retain their source identities and exclusion reasons.

## 6. Closed capability states and reasons

**Approved design-reference states — not production enums**

| State                  | Meaning                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------- |
| `CANDIDATE_COHERENT`   | One supported target annual interval and a unanimously agreeing common-filing pair                   |
| `EVIDENCE_UNAVAILABLE` | Required source facts, annual period or common pair are not established                              |
| `EVIDENCE_UNSUPPORTED` | Annual calendar, context, metadata or source representation cannot be adjudicated under this grammar |
| `SOURCE_CONFLICT`      | Admissible facts or filing metadata provide contradictory evidence                                   |

**Approved design-reference closed reasons**

| Family      | Reasons                                                                                                                                                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unavailable | `NO_APPARENT_ANNUAL_PERIOD`, `REVENUE_UNAVAILABLE`, `OPERATING_INCOME_UNAVAILABLE`, `FINITE_VALUE_UNAVAILABLE`, `NO_COMMON_ANNUAL_ACCESSION`                                                            |
| Unsupported | `ANNUAL_ENDPOINT_UNLOCATABLE`, `ANNUAL_INTERVAL_UNSUPPORTED`, `ANNUAL_INTERVAL_AMBIGUOUS`, `UNSUPPORTED_FILING_CONTEXT`, `UNSUPPORTED_UNIT_OR_ROW_CONTEXT`, `POTENTIALLY_COMPARABLE_CONTEXT_UNRESOLVED` |
| Conflict    | `INVALID_FILING_CHRONOLOGY`, `COMMON_FILING_METADATA_CONFLICT`, `COMPETING_REVENUE_VALUES`, `COMPETING_OPERATING_INCOME_VALUES`                                                                         |

Applicable reasons SHALL be unique and deterministically ordered by their exact identifier strings.

If multiple families apply, the result-state precedence SHALL be:

`SOURCE_CONFLICT` → `EVIDENCE_UNSUPPORTED` → `EVIDENCE_UNAVAILABLE`.

Integrity and public-input errors are evaluated before these economic-evidence states and SHALL not be recoded as ordinary unavailability.

For any non-`CANDIDATE_COHERENT` outcome:

- Both selected numeric fields SHALL be `None`.
- No partial selected pair SHALL be published.
- Available period, observation and source-provenance evidence SHALL remain inspectable.
- Reasons SHALL identify why establishment failed.

## 7. Immutable result and provenance

The proposed result SHALL be frozen, typed and versioned.

Its minimum public surface SHALL preserve:

| Category       | Required content                                                                            |
| -------------- | ------------------------------------------------------------------------------------------- |
| Contract       | Contract version, evidence kind, authority, state, reasons, limitations                     |
| Source         | CIK, source kind, exact concepts, US-GAAP basis, USD                                        |
| Period         | Observed target endpoint and target interval where determinable                             |
| Facts          | Exact Revenue and Operating Income Decimals only when coherent                              |
| Capture        | Receipt ID, object SHA-256, captured-at, source locator, acquisition identity               |
| Observations   | Selected semantic/evidence IDs and exact row locators                                       |
| Filing support | All supporting accessions, form, filed date, FY and selected observation partitions         |
| Exclusions     | Nonselected, orphan, competing and unsupported relevant-observation references with reasons |
| Identity       | Separate candidate semantic ID and evidence ID                                              |

The result SHALL NOT copy the complete Companyfacts source payload.

Compact observation references and an authenticated extraction-inventory identity SHALL preserve traceability to the complete immutable archive. The result's evidence identity SHALL bind the relevant selection and exclusion inventory even when detailed source rows remain in the original archive.

## 8. Semantic and evidence identities

The candidate SHALL use separate, versioned and domain-separated SHA-256 identity constructions.

**Semantic identity SHALL bind:**

- Contract and selection-policy versions.
- Bounded result kind, state, material reasons and authority limitations.
- Source CIK, accounting namespace, concepts and unit.
- Selected period when determined.
- Both exact source-reported amounts when coherent.
- Any economically material unresolved conflict classification.

It SHALL NOT directly bind incidental filesystem paths, capture timestamps, receipt IDs or row-order positions.

**Evidence identity SHALL additionally bind:**

- Candidate semantic identity.
- Exact capture receipt and source-object identities.
- Acquisition and extraction versions.
- Selected observation semantic/evidence IDs and row locators.
- Supporting filing and accession evidence.
- Materially excluded/competing observation references and the complete relevant inventory commitment.

Canonical serialization SHALL be deterministic, with exact base-ten numeric representation, sorted set-like identifiers and no binary floating-point conversion or lossy rounding.

Required invariants:

- Unchanged economic meaning under a legitimate recapture MAY preserve semantic identity.
- Different authentic receipts MUST remain distinguishable through evidence identity.
- Changed selected values, target period, material conflict or capability state MUST affect semantic identity.
- Added irrelevant source observations SHALL NOT create a new economic claim, even if a changed source object produces a different evidence identity.
- Identical object hashes under separate receipts SHALL NOT be counted as independent issuer-coverage demonstrations.

## 9. Fail-closed and native-authority isolation

The result is **research-candidate evidence only**.

It SHALL NOT:

- Construct or impersonate `OrdinaryCompounderMethodProfileQualification`.
- Emit `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED`.
- Construct the existing Stage-C `CurrentAnnualRevenueOperatingIncomeQualification`.
- Emit existing `PAIRED_REVENUE_OPERATING_INCOME_ESTABLISHED`.
- Satisfy the native operating-income/revenue diagnostic's exact input type.
- Grant any native Quality or Expected Return `AVAILABLE` state.
- Establish historical-as-of, point-in-time or current market-quote authority.
- Establish a score, ratio, margin, ranking, recommendation, portfolio adjustment, execution or production entitlement.

The existing PR4C3, PR5B, PR5C, Ordinary Compounder and Stage-C source-to-analysis contracts SHALL remain unchanged.

Separate result type, contract/version domains, authority identifiers and absence of conversion/admission functions SHALL be mandatory safeguards.

These are proposed runtime requirements, **not claims of verified isolation in code that does not yet exist**.

## 10. Explicit limitations

Even a `CANDIDATE_COHERENT` result does not prove:

- Complete issuer SEC filing coverage or absence of later filings.
- That the selected annual period is the issuer's absolutely newest annual reporting period.
- Universal economic equivalence between reported revenue and total company revenue.
- Security-class eligibility, ordinary-common participation or legal/economic continuity.
- Corporate-action and share-basis continuity.
- Historical cross-period comparability, growth or operating-margin trends.
- Reporting-subject continuity beyond the narrow source-presented filing context.
- Normalized profitability, business quality or durability.
- Ordinary Compounder eligibility or native model admissibility.
- PIT, historical availability, investment attractiveness or execution readiness.

Source uncertainty SHALL remain source uncertainty. An unavailable candidate is not a negative judgment about the issuer.

## 11. Proposed acceptance and rejection scenarios

These are normative **future validation criteria**, not executed tests.

| Scenario                                                 | Required decision                                                         |
| -------------------------------------------------------- | ------------------------------------------------------------------------- |
| One exact 365/366-day coherent annual common pair        | `CANDIDATE_COHERENT` with both original Decimal values and full lineage   |
| Revenue or Operating Income absent                       | `EVIDENCE_UNAVAILABLE`; no selected values                                |
| No common admissible accession                           | `EVIDENCE_UNAVAILABLE / NO_COMMON_ANNUAL_ACCESSION`                       |
| Competing admissible paired amounts                      | `SOURCE_CONFLICT`; no winner                                              |
| Inconsistent accession-local form, filed date or FY      | `SOURCE_CONFLICT / COMMON_FILING_METADATA_CONFLICT`                       |
| Newer apparent annual evidence incomplete or unsupported | No older-period fallback; appropriate unavailable/unsupported result      |
| Orphan alongside a coherent common pair                  | Preserve/exclude orphan without manufactured pair conflict                |
| Unsupported 52/53-week or fiscal transition              | `EVIDENCE_UNSUPPORTED`; no calendar reconstruction                        |
| Receipt, byte-length, hash or source CIK mismatch        | Contract/integrity error; never coherent                                  |
| Legitimate unchanged-economic recapture                  | Stable candidate semantics where applicable; capture-distinct evidence ID |
| Changed values or selected period                        | Different semantic identity                                               |
| Research result presented to native Quality analyzer     | Exact-type rejection; no promotion                                        |

Later implementation validation would need fictional adversarial fixtures for all these cases, including misleading annual metadata, ambiguous newer endpoints, malformed source rows, changed capture ordering and forged canonical identities.

Passing synthetic tests would establish mechanics only. Authentic applicability would remain a separate evidence question.

---

**End of CEO-approved design reference. Repository adoption conveys no implementation, deployment or runtime authority.**
