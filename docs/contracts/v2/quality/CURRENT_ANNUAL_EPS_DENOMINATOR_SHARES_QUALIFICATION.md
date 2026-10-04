# CURRENT annual EPS denominator shares qualification

## Contract identity

- Contract version:
  `2026-10-04-current-annual-eps-denominator-shares-qualification-v1`
- Qualifier version:
  `2026-10-04-paired-common-filing-exact-decimal-qualification-v1`
- Evidence kind:
  `CURRENT_ANNUAL_EPS_DENOMINATOR_SHARES_QUALIFICATION`
- Authority:
  `QUALITY_DILUTION_EPS_DENOMINATOR_EVIDENCE_ONLY`

This is one bounded Stage-C evidence foundation. It is not a Quality
diagnostic, a dilution calculation, a score or an investment rule.

## Economic question

The qualifier answers exactly:

> For the latest annual fiscal period already established by PAM's supported
> ordinary-compounder route, can PAM establish from one coherent CURRENT SEC
> Companyfacts presentation the exact weighted-average basic and diluted share
> denominators used for EPS reporting?

It does not answer whether dilution is good or bad, whether shareholders were
diluted historically, whether stock-based compensation caused dilution,
whether shares were issued, whether repurchases were effective, whether
management allocated capital well or whether future dilution will occur.

## Exact public input

The public function accepts exactly:

1. `economic_facts.sec_archive.SecArchive`; and
2. `economic_facts.sec_ordinary_compounder_profile.OrdinaryCompounderMethodProfileQualification`.

Subclasses, dictionaries, mappings and duck-typed objects are rejected. The
caller cannot provide a CIK, period, receipt, source object, denominator value,
route-local identity or detached comparability object.

The issuer, route-local issuer/security identities, latest annual period and
Companyfacts receipt are derived from the profile's canonical embedded
comparability and security evidence graph. The qualifier rereads only the exact
immutable object selected by that embedded receipt and verifies receipt/object,
CIK and route coherence. It performs no live SEC fetch, provider acquisition,
clock read or historical reconstruction.

## Extraction boundary

`economic_facts/sec_eps_denominator_shares.py` extracts exactly these concepts:

- `us-gaap:WeightedAverageNumberOfSharesOutstandingBasic`; and
- `us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding`.

The reviewed unit is exactly `shares`. Issuer-extension synonyms, period-end
shares outstanding, other namespaces and other Companyfacts concepts do not
substitute.

Each immutable observation preserves:

- source CIK;
- namespace, concept and unit;
- exact base-ten `Decimal` value;
- start, end, FY, FP, form, filed date, accession and optional frame;
- source object hash, capture receipt identity and captured-at provenance;
- source locator and semantic locator;
- canonical row JSON and row-level source semantics;
- separate source-observation semantic and evidence identities.

JSON numeric values are parsed directly as `Decimal`. Binary float conversion
is forbidden. Malformed source structures fail closed; they do not become
silent absence.

## Canonical period and qualification

The target is the latest exact annual period in the canonical five-period
comparability chain. An established pair requires all of the following:

- upstream profile status is exactly
  `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED`;
- embedded comparability is exactly established, canonical and coherent;
- exactly five canonical period decisions remain exact matches;
- the embedded Companyfacts receipt/object belongs to the supplied archive;
- source, receipt, request, series and route CIK/identities agree;
- both reviewed concepts exist under `us-gaap`;
- unit is exactly `shares`;
- both values are finite, strictly positive exact `Decimal` values;
- rows are `10-K` or `10-K/A` annual `FY` presentations;
- both rows match the canonical latest period exactly;
- at least one filing accession supports both concepts;
- all admissible values for basic shares agree;
- all admissible values for diluted shares agree; and
- diluted weighted-average shares are greater than or equal to basic
  weighted-average shares.

The qualifier never averages, rounds, interpolates or arbitrarily chooses among
competing values. The `diluted >= basic` rule is an accounting/evidence
coherence invariant only; it is not an investment-policy threshold.

## Capability states

The result uses exactly:

- `PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED`;
- `EVIDENCE_UNAVAILABLE`;
- `EVIDENCE_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Upstream profile states map without reinterpretation:

| Upstream profile state | Result state |
| --- | --- |
| `ORDINARY_COMPOUNDER_PROFILE_ESTABLISHED` plus coherent pair | `PAIRED_EPS_DENOMINATOR_SHARES_ESTABLISHED` |
| `PROFILE_UNAVAILABLE` | `EVIDENCE_UNAVAILABLE` |
| `PROFILE_UNSUPPORTED` | `EVIDENCE_UNSUPPORTED` |
| `SOURCE_CONFLICT` | `SOURCE_CONFLICT` |

Unknown future states and contradictory supposedly-established profile objects
are programming-contract errors.

Incomplete but noncontradictory required evidence is
`EVIDENCE_UNAVAILABLE`. Out-of-contract upstream profile/accounting structure
is `EVIDENCE_UNSUPPORTED`. Competing admissible values, incoherent route/source
identity and diluted shares below basic shares are `SOURCE_CONFLICT`.

Every non-established result contains `None` for both denominator values and an
empty selected-observation/supporting-filing surface. Missing evidence never
becomes zero shares and conflicting evidence never becomes a low-confidence
number.

## Immutable output

The result preserves the minimum semantic and evidence surface for:

- contract version, qualifier version and evidence kind;
- capability status and closed reasons;
- native upstream profile state and reasons;
- route-local issuer/security context and source CIK;
- exact annual period start/end;
- accounting namespace/basis, exact concepts and unit;
- exact basic and diluted weighted-average share values when established;
- upstream profile and comparability semantic/evidence identities;
- capture receipt, source object, captured-at and source-locator provenance;
- selected basic/diluted observation evidence identities;
- supporting accessions and filing provenance;
- authority and closed limitations;
- separate deterministic `semantic_id` and `evidence_id`.

There is no difference, spread, ratio, percentage, basis-point conversion,
dilution rate, score, grade, rank, confidence, recommendation, allocation or
sizing field.

## Identity

`semantic_id` binds:

- contract version, qualifier version and evidence kind;
- capability state and exact reasons;
- native upstream profile state and reasons;
- route-local identifiers and source CIK;
- upstream profile and comparability semantic IDs;
- exact target period;
- accounting namespace/basis, concept identities and unit;
- exact established base-ten basic/diluted values;
- authority and limitations.

It does not independently bind capture timestamps, local archive paths,
temporary filenames, receipts, object hashes or selected evidence observations.

`evidence_id` binds the result semantic ID plus:

- upstream profile and comparability evidence IDs;
- canonical capture receipt and object identity;
- captured-at/source-locator evidence provenance;
- selected source observation evidence identities; and
- supporting accessions/filing provenance.

Therefore, with unchanged upstream semantics:

```text
same economic meaning + new valid evidence recapture
→ same semantic_id
→ different evidence_id
```

A changed value, period, status, reason, concept, unit or route meaning changes
`semantic_id`. Identity projection uses exact `Decimal` structure and never
binary64.

## Closed limitations

The output pins the reviewed concept scope and the following limitations:

- no dilution-quality conclusion;
- no historical dilution trend;
- no SBC causal attribution;
- no issuance causal attribution;
- no repurchase-effectiveness conclusion;
- no period-end shares-outstanding claim;
- no class-specific shares-outstanding claim;
- no cross-sector comparability;
- no Expected Return effect;
- no Durability conclusion;
- no Confidence conclusion;
- no recommendation, ranking, allocation or sizing;
- no execution, production or V2-promotion authority; and
- no `HISTORICAL_AS_OF` or PIT authority.

## CURRENT and PIT boundary

This is CURRENT evidence about one historical annual reporting period. It does
not prove what PAM knew at the fiscal period end, filing date or any historical
cutoff. It creates no PIT reconstruction and no historical share-count series.

## Separation from Quality, other pillars and policy

There is no acceptable-dilution threshold, good/bad label, maximum spread,
Quality grade, Quality weight, ranking cutoff or composite `QualityScore`.

The foundation does not read, alter or depend on Expected Return, VFV, the
company/VFV comparator, cash-like carry, B1/B2 or Stage-B unsupported-case
handling. It makes no moat, persistence, resilience, sustainable-compounder or
future-dilution conclusion. It has no confidence field. It creates no
recommendation, ranking, sizing, allocation, Opportunity Set admission,
portfolio-room effect, monitoring escalation or execution instruction.

## V1 freeze and operational boundary

V1 and the first Quality diagnostic remain untouched and unimported. This
foundation does not use V1 dilution thresholds, labels, scores or allocation
adjustments. It creates no parent Quality object and does not aggregate with
`FivePeriodEPSConsistencyResult`.

`MODEL_RULES_VERSION` remains
`2026-08-23-allocation-room-integrity-v7`. The protected PIT and determinism
fingerprints remain unchanged. No investment/model rule, production behavior,
deployment or V2-promotion authority is modified.
