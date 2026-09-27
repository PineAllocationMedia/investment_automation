# PR5A — Real Fact Admission gap review and closure plan

## 1. Executive conclusion

The merged V2 repository contains substantially more real-source infrastructure
than the previous roadmap records. The chain through PR #62 can acquire and
immutably retain controlled CURRENT SEC and Nasdaq evidence, resolve a five-year
reported diluted-EPS series, bind relevant periodic filings to one D1 boundary,
corroborate one exact SEC CIK / Nasdaq symbol / exchange relationship, locate
same-filing common-stock source scopes, and describe their correspondence across
multiple controlled filings.

That chain is useful evidence, but it deliberately stops before economic
qualification. It does not yet establish EPS applicability to the selected common
class, quote currency/unit, comparable share basis, one accounting reporting
subject, or a final admission decision. It also does not supply the observed
price, dividend/nonpayer state, ordinary-compounder profile, or governed policies
required by the existing Expected Return constructor.

The minimum safe strategy is therefore:

> support one narrow CURRENT SEC/Nasdaq ordinary-common route, positively qualify
> the properties that affect the economics, and fail closed outside that profile.

It is not necessary to build universal corporate-action, M&A, legal-right,
cross-market identity, listing-inventory, or historical-PIT engines before the
first real CURRENT Expected Return result. Four implementation PRs are sufficient
as a credible plan if each receives a separate reviewed contract: PR5B qualifies
the selected security, ordinary-common participation, route-local relevant-class
coverage, direct listing, and EPS applicability; PR5C qualifies a
no-transformation comparable EPS history; PR5D supplies the remaining real ER
roots and governed policies; PR5E performs final admission and adapts admitted
facts into the existing calculator path.

PR5A implements none of those capabilities. It freezes the closure plan for owner
review. No subsequent implementation is authorized by this document.

## 2. Audited base and repository state

The remote was fetched before review. The approved integration ref matched exactly:

| Item | Verified value |
| --- | --- |
| Repository | `PineAllocationMedia/investment_automation` |
| Base branch | `model-v2/expected-return-challenger` |
| Base commit | `880d61f001bdfb1b8196f9207212c8dc83257f2d` |
| Base tree | `98c7deebb10c7779cb77e0e9230ed38659a8637a` |
| Merged state | post-PR #62 / PR4D4D3B |
| Review branch | `codex/v2-pr5a-real-admission-gap-review` |

The worktree and index were clean before the branch was created from the exact
remote base. Existing local and divergent refs were not changed.

## 3. Scope and methodology

This is a documentation and architecture review. It adds no production Python,
test behavior, source authority, model rule, runtime path, portfolio behavior,
V1 behavior, dependency, deployment, or production configuration.

The review used the actual code and tests as authority. It inspected:

- the C1-C3 acquisition, archive, extraction, and exact-agreement EPS resolver;
- the D1 source-route registry and controlled CURRENT authority replay;
- the synthetic C4-C6 identity, share-basis, and reporting-subject qualifiers;
- every real-source D contract and implementation from D1 through D4D3B;
- tests for positive routes, conflicts, temporal boundaries, replay integrity,
  unsupported profiles, and explicit nonclaims;
- PR4A, PR4B1, PR4B2, their actual calculator/constructor modules, and tests;
- the constitution, roadmap, V1 freeze, relevant decision history, and system
  architecture.

The classifications below answer one narrow question: what is required to
produce the first safe CURRENT real ER result? `SUFFICIENT_FOR_FIRST_CURRENT_ROUTE`
means that the existing evidence is sufficient to be consumed by a future typed
admission gate for that narrow property. It does **not** mean the repository
currently emits an admitted fact or that a D-chain source report has silently
become economic authority. Obligation 7 remains required in every case.

## 4. Implemented real-source capability map

| Merged capability | Actual implemented result | Boundary that remains |
| --- | --- | --- |
| C1/C2 SEC Companyfacts capture | Exact bytes, immutable receipts, controlled LIVE acquisition contract, safe local request policy | Offline receipts are not LIVE authority; no publication timestamp or economic admission |
| C3 reported diluted EPS | Five consecutive 365/366-day annual `us-gaap:EarningsPerShareDiluted` values in `USD/shares`, exact `Decimal`, exact-agreement revision handling, complete retained filing-version lineage | Issuer evidence only; no class entitlement, basis, subject, or final admission |
| D1 CURRENT authority | Registered exact Companyfacts route establishes acquisition provenance, capture-bound observed availability, and CURRENT snapshot scope through T | Publication unknown; no PIT authority, freshness after T, identity, comparability, or admission |
| D2A complete submissions | Controlled exact-byte SEC filing capture | Capture is not economic interpretation |
| D2B Submissions inventory | Root/history replay and captured-reference closure | Not complete filing history, event history, publication, or Property 4 |
| D2C Nasdaq Listed | Controlled current directory snapshot with exact rows and conflict preservation | No CIK identity, quote currency, continuity, complete listing inventory, or admission |
| D3A registered securities | Exact supported taxonomy extraction of title/symbol/exchange source claims | Source claims, not security identity |
| D3B class/EPS facts | Common-shares-outstanding and diluted-EPS source claims with dimensions preserved | No class entitlement, unit economics, or applicability conclusion |
| D3C historical profiles | Finite reviewed historical D3A/D3B taxonomy support | Wider extraction coverage is not historical authority |
| D4A temporal dossier | Joins controlled D2B/D2A filings and retains D3A/D3B results for relevant periodic forms | No winner over conflict and no economic continuity |
| D4B CURRENT boundary | Replays D1 and D4A; requires captured evidence by T | Capture-by-T only; SEC acceptance is not publication or availability |
| D4C1 SEC association snapshot | Controlled CIK/name/ticker/exchange source rows | Association evidence, not durable economic identity |
| D4C2 registered-listing bridge | Exact CIK, symbol, `NASDAQ` / `Nasdaq`, and non-test Nasdaq-row corroboration at T | CURRENT source bridge only; no currency, inventory, continuity, or admission |
| D4D1 filing document inventory | Deterministic embedded filing-document inventory | No legal/economic interpretation |
| D4D2A direct Section-12 source | Identifies direct 10-K/10-K/A EX-4 description sources under closed anchors | No incorporated/external source resolution and no rights conclusion |
| D4D2B common-stock source claims | Exact common-stock scopes and topic-labelled passages | Topics are retained source claims, not interpreted rights |
| D4D3A same-filing class bridge | Exact closed common-stock title grammar joined to one same-filing source scope | Source correspondence, not durable class identity or admission |
| D4D3B temporal source series | At least two ordered controlled correspondences; stable and variation signals retained | Explicitly not security continuity, event absence, rights interpretation, or admission |

The positive tests do not erase those boundaries. The same suites deliberately
test that prebuilt assessments cannot bypass fresh replay, ambiguous symbols/classes
have no winner, post-T captures cannot repair T, source acceptance is not
publication, stable source text emits no continuity claim, and none of these
modules is consumed by model/runtime/V1 code.

## 5. Synthetic semantic-contract map

The C4-C6 implementations prove the meaning and failure behavior required of a
qualified chain. They do not prescribe that a real route use identical fictional
evidence structures.

| Contract | Semantics proved | Real-route implication |
| --- | --- | --- |
| C4 security identity | One issuer; ordinary residual common participation; complete relevant common-class coverage with no unresolved competing common class; one direct listing; applicability across every retained EPS observation/version; and fail-closed ambiguity | The first route needs the same economic conclusions, but a route-specific SEC/Nasdaq adapter may prove them from D evidence and reject everything else. Source correspondence or silence about another class is insufficient |
| C5 share basis | Every retained observation is already on one evidenced target denomination; every relevant event and filing-specific treatment is covered; transformation is `NONE` | Real admission must positively establish comparable presentation. It need not implement EPS arithmetic or every corporate-action type |
| C6 reporting subject | Every retained observation and the current issuer belong to one accounting reporting subject throughout the required interval | CIK/security sameness is insufficient. A narrow real qualifier may admit only simple continuous cases and reject predecessor/successor ambiguity |

Synthetic success retains `SYNTHETIC_TEST_ONLY` and all real admission blockers.
The real route must never relabel a C4/C5/C6 synthetic result as real evidence.

## 6. Existing blocker model

C3 emits exactly seven downstream blockers. Their first-route dispositions are:

| C3 blocker | Property protected | First-route disposition |
| --- | --- | --- |
| `OFFLINE_CAPTURE_NOT_AUTHENTICATED` | Controlled acquisition provenance | D1 can discharge this only for an exact LIVE Companyfacts replay; offline inputs remain rejected |
| `PUBLICATION_AND_AVAILABILITY_NOT_ESTABLISHED` | No use of evidence before it is known | D1 supplies capture-bound CURRENT observed availability. Exact original publication remains unknown and must not be invented; the real ER fact contract must represent that distinction |
| `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED` | Correct issuer/security/class participation, relevant-class coverage, listing, and EPS entitlement | Existing D evidence is an adequate source foundation, but a positive qualifier must establish ordinary participation, affirmative route-local relevant-class coverage, EPS applicability, and reject ambiguity. Absence of an observed second class is not coverage |
| `SPLIT_BASIS_NOT_ESTABLISHED` | Comparable currency/share denomination | Requires a real no-transformation basis qualifier; C3 exact agreement alone is insufficient |
| `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED` | One accounting reporting subject | Requires a real subject-continuity qualifier; same CIK is insufficient |
| `SNAPSHOT_COVERAGE_ONLY` | Evidence scope/temporal completeness | May be discharged only for the exact evidence graph and interval positively covered by the narrow qualifiers; it is not removed globally |
| `UPSTREAM_EVIDENCE_ONLY` | Separation of evidence from admission | Discharged only by the final real admission join in PR5E |

Historical mode remains rejected by C3 and D1. Nothing in this plan removes a
blocker globally, accepts a caller boolean, or treats a hash/report as a capability.

## 7. Property 4A-4H matrix

| Property | State | Current real evidence | Missing / first-route effect | Smallest safe closure and explicit deferral |
| --- | --- | --- | --- | --- |
| 4A — issuer identity | `SUFFICIENT_FOR_FIRST_CURRENT_ROUTE` | Controlled Companyfacts CIK; controlled SEC filing/submission CIK; D4C1 CIK association; D4C2 exact CIK/symbol/exchange join | No global PAM economic-issuer identifier. A final consumer still must replay exact evidence and bind one route-local issuer anchor | PR5B binds the exact SEC registrant CIK to the selected route and rejects disagreement/reorganization ambiguity. Global entity resolution, LEI mapping, aliases, and cross-market identity are deferred |
| 4B — security identity | `SUFFICIENT_FOR_FIRST_CURRENT_ROUTE` | D3A registered title/symbol/exchange claims; D4C2 exact current Nasdaq correspondence; D4D3A/D4D3B exact source scopes through controlled filings | No durable security identity across arbitrary ticker/listing changes | PR5B creates a route-local security key from the exact controlled evidence and rejects conflicts. Universal security masters and ticker-transition engines are deferred |
| 4C — class identity / rights | `REQUIRES_REAL_CLOSURE` | D3A exact `COMMON STOCK` or reviewed `CLASS … COMMON STOCK` grammar; D4D2B source scopes and uninterpreted rights topics; D4D3A same-filing match; D4D3B ordered correspondence | The D-chain does not establish that the selected source class satisfies the supported ordinary residual common participation profile. A title or matched source scope is not an economic/legal participation conclusion | PR5B performs a narrow positive ordinary-common participation qualification and blocks unsupported or ambiguous participation. Exhaustive interpretation of every legal right remains deferred |
| 4D — relevant common-class inventory | `REQUIRES_REAL_CLOSURE` | D3A/D3B and the D4 dossier retain observed registered and outstanding-class source claims, dimensions, scopes, and conflicts | The D-chain does not affirmatively establish route-local relevant-class coverage or the absence of another economically relevant common class. Silence about a second class is insufficient | PR5B requires affirmative coverage for the exact supported route and no unresolved competing economically relevant common class for the EPS-applicability question; every observed contradiction or multiple-class condition blocks. A universal issuer-wide, historical, U.S., or global class-inventory engine is deferred |
| 4E — EPS applicability | `REQUIRES_REAL_CLOSURE` | C3 retains every period, filing version, and observation; D3B retains EPS dimensions; D4D3A links one common-stock source scope | No real qualifier binds every retained C3 EPS observation/version to selected supported ordinary-common economics. Undimensioned EPS or one matched `COMMON STOCK` scope cannot establish applicability | Only after PR5B positively closes 4C and 4D may it bind every retained C3 observation/version to the selected class, require supported total diluted-EPS semantics, and block dimension/class conflicts. Other numerator/entitlement profiles are deferred |
| 4F — listing / quote semantics | `REQUIRES_REAL_CLOSURE` | D4C2 establishes one exact current direct Nasdaq source correspondence; C3 EPS unit is `USD/shares` | No observed-price route and no evidence-backed quote currency/unit. Venue does not prove currency | PR5D adds a controlled price/quote source with explicit currency, per-share unit, observation time, and selected-listing linkage. Other venues/currencies and FX conversion are deferred |
| 4G — listing inventory | `DEFERRED_BEYOND_FIRST_ROUTE` | D3A/D4C1 retain observed SEC listings; D2C/D4C2 retain the selected current Nasdaq row and target-local ambiguity | No complete U.S. or historical listing inventory | The first route admits one exact direct Nasdaq listing and blocks observed conflicts/multiple candidates. Complete inventory, dual listings, migrations, and wrapper reconciliation remain future work |
| 4H — continuity | `REQUIRES_REAL_CLOSURE` | D4A/B provide ordered controlled filing evidence through T; D4D3B exposes ordered source correspondence and variation signals | D4D3B explicitly does not prove security/class continuity or absence of basis/subject events | PR5B/PR5C require an affirmative, bounded continuity decision across the oldest EPS start through T and reject gaps, ticker/class conflicts, reclassifications, mergers, and unsupported transitions. Universal lifecycle history is deferred |

The sufficiency decisions for 4A and 4B are evidence decisions, not admission
tokens. Properties 4C-4E require positive PR5B qualification for the deliberately
narrow route. In particular, absence of an observed second class is not affirmative
relevant-class coverage, and EPS applicability depends on successful 4C/4D closure.
Property 4G remains deferred, not silently satisfied by a selected listing.

## 8. Obligations 5-7 matrix

| Obligation | State | Current real evidence and synthetic reference | Why it blocks / what is missing | Smallest safe closure and explicit deferral |
| --- | --- | --- | --- | --- |
| 5 — share-basis comparability | `REQUIRES_REAL_CLOSURE` | C3 exact values/lineage and D4 class correspondence are real; C5 proves per-observation target-basis and event-treatment semantics synthetically | `USD/shares` and cross-filing numerical agreement do not identify a share-denomination epoch or cover post-period basis events through T | PR5C implements a positive no-transformation qualifier for supported simple cases, with affirmative basis coverage and every retained version checked. Any split, reclassification, conflicting presentation, incomplete coverage, or uncertain event blocks. A universal action engine and normalization arithmetic are deferred |
| 6 — reporting-subject comparability | `REQUIRES_REAL_CLOSURE` | D4 supplies filing chronology and issuer/class evidence; C6 proves complete single-subject interval semantics synthetically | Same CIK, legal issuer, and security do not prove the same accounting reporting subject | PR5C positively binds each retained observation and the boundary to one supported subject span. Predecessor/successor, reverse acquisition, carve-out/combined financials, reporting reset, conflict, or gap blocks. A universal M&A/perimeter engine is deferred |
| 7 — final economic admission | `REQUIRES_REAL_CLOSURE` | D1 and D4 results are inspectable evidence reports; no existing route may grant `FINAL_ECONOMIC_ADMISSION` | No gate replays the complete evidence graph, discharges exact blockers, emits typed real facts, or preserves unresolved limitations | PR5E performs one closed final join after PR5B-D, emits admitted or blocked—not partial authority—and creates the real constructor boundary. Broader admission profiles remain deferred |

## 9. CURRENT versus HISTORICAL_AS_OF

The first route has one CURRENT boundary T. These distinct times and meanings must
remain separate:

1. the analysis is run for CURRENT information at T;
2. the EPS values describe five earlier fiscal periods;
3. each value has filing/source events and retained accession lineage;
4. PAM has controlled capture timestamps;
5. exact publication/public availability may be different and may be unknown;
6. a historical-as-of question asks what PAM could have known at a past cutoff.

For CURRENT analysis, each accepted historical EPS observation must be present in
controlled source evidence observed available by T and must pass the current
identity/comparability/admission gates. The route does **not** need to prove when
each historical value first became public. The fact that an economic period is
historical does not turn a CURRENT analysis into historical PIT replay.

For HISTORICAL_AS_OF, evidence captured after the requested cutoff cannot establish
knowledge at that cutoff. C3 and D1 correctly reject this mode. Exact historical
publication/availability and vintage reconstruction are deferred beyond the first
route and remain necessary before retrospective PIT authority can be claimed.

## 10. Share-basis closure analysis

The correct first-route choice is a constrained form of option B, with an important
qualification: **absence of a detected conflict is not by itself affirmative basis
evidence**.

C3 resolves exact reported values and retains every filing version. Its exact-
agreement checks are strong conflict detectors: a split-restated value that differs
from an earlier filing cannot be silently selected. But C3 does not identify the
denomination epoch, prove complete corporate-action coverage, or establish whether
a post-fiscal-year action changed the basis used by a CURRENT price.

C5 demonstrates the relevant invariant: all retained values must already be on one
evidenced target basis through T, and every relevant observation/version must be
covered. The first real route can implement that invariant without a universal
event graph or any EPS arithmetic by accepting only a positively evidenced
no-transformation profile. PR5C must:

- bind the selected security/class and required interval;
- inspect every retained C3 filing version and any required basis evidence;
- establish one target currency/share-basis identity through T;
- affirmatively cover the interval, not infer completeness from silence;
- reject any split, stock dividend, conversion, recapitalization, merger exchange,
  spin-off, redenomination, fractional settlement, inconsistent presentation, or
  unresolved action/basis evidence;
- preserve the original exact `Decimal` values unchanged.

Supporting already-adjusted split cases may be added later under a separately
reviewed positive evidence contract. A full action engine remains valuable for
Portfolio State and broad coverage, but omission of that universal engine does not
block the first route because affected or uncertain issuers can be admission-blocked.

## 11. Reporting-subject closure analysis

Three anchors must not be collapsed:

- the SEC CIK identifies the registrant/source namespace;
- the selected issuer/security evidence identifies the legal/economic route target;
- the accounting reporting subject identifies whose historical earnings the EPS
  series measures.

C6 correctly accepts ordinary acquisitions, divestitures, policy changes, and
discontinued-operations presentation when one accounting subject still spans the
required interval. It rejects formal predecessor/successor replacement, reverse-
acquisition resets, and carve-out/combined-subject replacement within the interval.

The first real route therefore needs affirmative subject coverage over the oldest
required EPS period start through T and every retained observation reference. It
does not need a universal M&A history or an economic normalization model. PR5C may
admit only simple cases where controlled filing evidence supports one reporting
subject and no contradictory transition exists. It must fail closed on:

- different or unresolved accounting-subject anchors;
- reverse acquisition or predecessor/successor presentation inside the interval;
- carve-out, combined, or replacement financial statements;
- a subject gap or uncovered retained observation;
- disagreement among mandatory sources;
- an unsupported restructuring whose effect cannot be bounded.

Ordinary business perimeter change is not itself a subject change and must not be
misclassified as one merely because business mix or reported results look unusual.

## 12. Publication and availability conclusion

D1 accurately records `PublicationSemantics.UNKNOWN` and capture-bound observed
availability. D4B also keeps SEC acceptance, filing/report dates, capture time, and
T distinct. The final route must preserve those facts.

For the first CURRENT route, a controlled source object present by T is sufficient
for current observed availability. Exact original publication time is not a
separate blocker. Capture time must never be presented as publication time, and an
SEC acceptance timestamp must not be relabelled publication or PAM availability.

There is one constructor compatibility issue: PR4B1's synthetic `Provenance`
requires concrete `published_at <= available_at <= captured_at`, and accepts only
synthetic adapter/source enums. A real adapter cannot fill `published_at` with T or
SEC acceptance without fabricating meaning. PR5E must introduce a real-capable
provenance contract, or a backward-compatible constructor input evolution, that
represents CURRENT observed availability with publication unknown while preserving
all existing synthetic behavior. This is an adapter-contract blocker, not a reason
to require historical PIT acquisition for current ER.

## 13. Expected Return root/input gap matrix

The PR4B1 constructor requires more than EPS. It requires one qualified ordinary
compounder, a positive current price, five consecutive positive annual diluted EPS
facts, a latest-period ordinary dividend or verified nonpayer state, matched
currency/share basis and accounting basis, explicit provenance, and three applicable
analytical policies. The classifications below describe current readiness.

| Required root/fact/policy | State | Audit conclusion |
| --- | --- | --- |
| CURRENT `as_of` / boundary | `REAL_ADAPTER_NEEDED` | D1 supplies T, but no real `QualifiedFacts` adapter consumes it |
| Security and common-class identity | `REAL_ADAPTER_NEEDED` | Existing D evidence is a sufficient source foundation, but PR5B must positively qualify ordinary participation and route-local relevant-class coverage before PR5E emits a source-neutral typed identity |
| Observed price | `REAL_SOURCE_MISSING` | No reviewed real price acquisition/qualification route exists |
| Price quote currency and per-share unit | `REAL_SOURCE_MISSING` | Nasdaq venue/ticker correspondence does not prove quote currency or unit |
| Five reported diluted-EPS values/history | `REAL_SOURCE_READY` | C3 supplies exact real `Decimal` values and full retained filing-version lineage; Property 4E and obligations 5-7 still gate admission |
| EPS period/calendar and latest required fiscal end | `REAL_SOURCE_READY` | C3 supplies the exact supported 365/366-day periods and required endpoint; PR5E must adapt the admitted result |
| Reported EPS unit | `REAL_SOURCE_READY` | C3 positively supplies `USD/shares`; this is a source unit, not proof of the target share denomination through T |
| Target share basis shared with current price | `REAL_SOURCE_MISSING` | PR5C must establish the denominator epoch and PR5D must link the price quote to it |
| Accounting basis | `REAL_SOURCE_READY` | C3's reviewed concept/profile supplies candidate `US_GAAP`; final admission must bind it to the qualified series |
| Ordinary annual dividend excluding specials | `REAL_SOURCE_MISSING` | No controlled real root exists for the latest matched annual period |
| Verified nonpayer alternative | `REAL_SOURCE_MISSING` | Absence of a dividend root is not verified nonpayer evidence |
| Payout-related input | `REAL_ADAPTER_NEEDED` | PR4B1 derives payout from matched dividend/EPS or nonpayer, but only after those roots and an applicable distribution policy exist |
| `ORDINARY_COMPOUNDER` profile and all exclusions | `REAL_SOURCE_MISSING` | No real evidence-backed profile qualifier covers the required exclusion set |
| Root provenance / confidence | `REAL_ADAPTER_NEEDED` | D1/D evidence has source hashes, T, limitations, and authority, but PR4B1 only understands synthetic source kinds and derives confidence from them |
| Mature-growth policy | `REAL_SOURCE_MISSING` | Required governed analytical input; values exist only in tests. This is a policy gap, not an external factual-source gap |
| Terminal-valuation policy | `REAL_SOURCE_MISSING` | Required governed analytical input; no production-approved values exist |
| Distribution policy | `REAL_SOURCE_MISSING` | Required governed analytical input matched to payer/nonpayer route; no production-approved value exists |
| Buyback root, analyst forecast, quality score, portfolio input | `NOT_REQUIRED_FOR_FIRST_PROFILE` | The current constructor neither requires nor accepts these as substitutes |

`REAL_SOURCE_READY` describes source availability only. It does not bypass the
Property 4, comparability, admission, or constructor adapters. No item in the table
authorizes guessed values or manual booleans.

## 14. Source authority and permitted-use separation

D1 already contains the right structural separation for its one Companyfacts
route:

- factual powers are route-specific and hashed without legal metadata;
- `license_status` is `UNKNOWN`;
- `use_status` is `REVIEW_REQUIRED`;
- no provider-wide trust is granted.

Other controlled routes have contract-specific use bases but are not all represented
in one equivalent registry. The first internal development/result route therefore
requires each consumed source route to carry an explicit reviewed use status and
to fail closed for a prohibited or unresolved intended use. This is partially
required now so factual evidence is not consumed outside its reviewed use.

A full global source/licensing registry, commercial redistribution rights, paid
provider governance, and commercial-use approval are deferred until broader
coverage/commercialization work. Terms uncertainty must remain a use limitation;
it must not rewrite a valid factual extraction as factually false or reduce economic
Quality. Commercial use is a separate owner/legal decision.

## 15. Immediate blockers

The first safe CURRENT real ER route remains blocked by exactly these capability
groups:

1. positive route-local issuer/security qualification, ordinary-common
   participation, affirmative relevant-common-class coverage, direct-listing
   source qualification, and EPS applicability, including bounded continuity and
   fail-closed ambiguity;
2. positive no-transformation share-basis and single-reporting-subject
   comparability through T;
3. a controlled current price with quote semantics, latest-period ordinary
   dividend or verified nonpayer evidence, ordinary-compounder profile evidence,
   and owner-reviewed applicable ER policies;
4. a final evidence-replaying admission join and real-capable constructor
   provenance/adapter.

The D1 CURRENT publication distinction and per-route permitted-use state must be
preserved within those capabilities. They do not require separate universal
engines before the first result.

## 16. Deferred non-blockers

The following remain important requirements but do not block the first route:

- universal corporate-action history and transformation arithmetic;
- portfolio-state corporate-action processing;
- legal interpretation of every Section-12 right;
- durable global issuer/security/class/listing identity;
- complete U.S. class and listing inventories;
- historical ticker/listing transition engines;
- ADR/ADS, wrapper, dual-listing, NYSE, foreign-issuer, and non-SEC routes;
- arbitrary fiscal calendars and non-US-GAAP profiles;
- universal merger/perimeter history;
- HISTORICAL_AS_OF availability and retrospective PIT authority;
- full global capability and source-use registry implementation;
- commercial redistribution/use approval;
- Quality, Durability, Confidence aggregation, portfolio authority, production,
  deployment, or shadow-readiness work.

These are deferred, not waived. The roadmap's broader pre-shadow and global
architecture requirements remain unchanged.

## 17. Minimal implementation sequence after PR5A

Each PR below fails the omission test: without it, the first safe CURRENT real ER
route remains blocked. Each needs a separately reviewed implementation contract.

### PR5B — Narrow CURRENT security and EPS qualification

**One capability:** produce a positive or blocked route-local qualification for
one supported issuer, security, ordinary-common participation profile,
affirmatively covered relevant-common-class boundary, direct Nasdaq listing, and
the applicability of every retained C3 EPS observation/version.

- **Discharges:** Properties 4A, 4B, 4C, 4D, and 4E for the exact supported first
  route; the route-specific
  `SECURITY_SHARE_CLASS_AND_LISTING_NOT_ESTABLISHED` blocker; and the
  source-correspondence portion of 4H.
- **Dependencies:** unchanged C3, D1, and D2A-D4D3B controlled archives/replayers.
- **Exit:** fresh replay positively establishes one route-local issuer/security,
  supported ordinary-common economic participation, affirmative relevant-class
  coverage with no unresolved competing economic common class, direct Nasdaq
  listing source qualification, and EPS applicability for every retained C3
  observation/version—or returns explicit blocked reasons. Every ambiguity,
  unsupported participation profile, contradictory/multiple-class condition, and
  coverage gap fails closed; coverage is never inferred from silence.
- **Nonclaims:** no global durable identity, universal issuer-wide class inventory,
  complete listing inventory, exhaustive legal-right interpretation, quote
  currency, share basis, reporting subject, final admission, or ER input.
- **Omission test:** yes, omitted PR5B leaves no positive EPS-to-security/class
  applicability decision and no affirmative ordinary-participation/relevant-class
  boundary.

### PR5C — Comparable real EPS qualification

**One capability:** establish that the already-qualified five-year EPS history is
on one unchanged share basis and belongs to one accounting reporting subject.

- **Discharges:** `SPLIT_BASIS_NOT_ESTABLISHED`,
  `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`, remaining required 4H continuity,
  obligations 5 and 6 for the supported profile.
- **Dependencies:** successful PR5B plus controlled positive basis/subject evidence.
- **Exit:** all retained observations are bound to one target basis and one subject
  through T with original `Decimal` values unchanged, or the case is blocked.
- **Nonclaims:** no EPS normalization, universal corporate-action engine, event
  transformation, universal M&A/perimeter history, or Portfolio State capability.
- **Omission test:** yes, omitted PR5C leaves historical EPS economically
  incomparable to itself and to the current price basis.

### PR5D — Remaining real Expected Return roots

**One capability:** produce a complete, qualified non-EPS input bundle for the
initial ordinary-compounder ER profile.

- **Discharges:** Property 4F and the missing price, latest-period dividend/nonpayer,
  profile, quote-unit/currency, and governed-policy gaps.
- **Dependencies:** PR5B identity/listing; PR5C target share basis; separately
  reviewed controlled source routes and owner-approved policy values.
- **Exit:** one exact selected security has a positive current observed price on
  the same currency/share basis, exactly one matched dividend/nonpayer state, an
  evidence-backed ordinary-compounder profile with all required exclusions, and
  three applicable versioned policies.
- **Nonclaims:** no alternate profile, analyst forecast, universal price/dividend
  provider authority, Quality/Durability score, or investment recommendation.
- **Omission test:** yes, omitted PR5D makes PR4B1 return missing price, dividend
  status, profile, and/or policy reasons even if EPS is fully admitted.

### PR5E — Final admission and real ER adapter

**One capability:** freshly replay and join PR5B-D with D1 authority, issue the
final admission decision, and map admitted real roots into the existing PR4B1 to
PR4A calculator path.

- **Discharges:** `SNAPSHOT_COVERAGE_ONLY` and `UPSTREAM_EVIDENCE_ONLY` only for
  the exact admitted graph; obligation 7; the synthetic-only provenance/adapter
  incompatibility; CURRENT publication-unknown representation.
- **Dependencies:** successful PR5B-D and explicit per-route use status.
- **Exit:** a clean end-to-end test produces a PR4A diagnostic from controlled
  real CURRENT evidence with no synthetic authority, guessed value, caller
  qualification boolean, ticker-only join, or model-rule change; every negative
  case remains unavailable/admission-blocked.
- **Nonclaims:** no V1 decision, allocation, recommendation, production authority,
  deployment, shadow readiness, historical PIT, or automatic V2 promotion.
- **Omission test:** yes, omitted PR5E leaves evidence reports disconnected from
  final admission and the constructor.

## 18. Exact first-route definition

The initial supported route is all of the following, not a looser union:

- CURRENT analysis at one explicit D1 boundary T;
- controlled LIVE SEC Companyfacts acquisition and supported C3 profile;
- SEC-reporting issuer under one exact controlled CIK;
- one ordinary common equity under the closed D4D3A source-title grammar and a
  positive supported ordinary residual participation qualification;
- affirmative route-local relevant-common-class coverage with no unresolved
  competing economically relevant common class for EPS applicability;
- one direct, exact, non-test Nasdaq listing under the D4C2 profile;
- a supported D3A/D3B taxonomy profile;
- five consecutive positive 365/366-day annual US-GAAP diluted-EPS periods in
  `USD/shares`, with all retained versions in exact agreement;
- unambiguous EPS applicability to the selected common equity;
- one affirmatively covered no-transformation share basis through T;
- one affirmatively covered accounting reporting subject through T;
- no ADR/ADS/wrapper, preferred security, partnership, fund, dual-listing,
  multiple-class ambiguity, ticker/listing conflict, unsupported restructuring,
  split/reclassification, subject transition, source conflict, or coverage gap;
- one controlled positive current price with explicit quote currency/unit on the
  admitted basis;
- one matched latest-period ordinary dividend excluding specials or verified
  nonpayer state;
- one evidence-backed ordinary-compounder profile with all PR4B1 unsupported
  structures explicitly excluded;
- applicable reviewed mature-growth, terminal-valuation, and distribution policies;
- only explicitly registered source routes with preserved factual/use limitations.

Any failed clause produces `DATA_UNAVAILABLE` / admission blocked. It does not
produce a guessed input, lower Quality, a sell signal, or a substitute security.

## 19. Stage A exit condition

Stage A is complete for the first supported CURRENT route when PAM can take one
explicitly supported real ordinary common equity from controlled source evidence
through:

1. CURRENT acquisition, immutable provenance, and observed-available-by-T authority;
2. route-local issuer/security qualification, supported ordinary-common economic
   participation, affirmative relevant-common-class coverage, and direct-Nasdaq
   source qualification;
3. every retained diluted-EPS observation/version's applicability to that common
   equity after the class boundary in step 2 is established;
4. one positively evidenced no-transformation share basis and one accounting
   reporting subject across the required interval through T;
5. a closed final admission decision that freshly verifies its inputs;
6. qualified price, dividend/nonpayer, ordinary-profile, policy, provenance, and
   confidence inputs; and
7. real-capable typed facts accepted by the existing PR4B1/PR4A computation path.

The path must use no synthetic authority, guessed values, caller-supplied
qualification booleans, ticker-only identity, fabricated publication timestamp,
model-rule change, positive-capital analysis, portfolio authority, or production
authority.

Completion for this route does not mean all U.S. securities, international
markets, global identity, Portfolio State, V2 feature completeness, shadow
readiness, production readiness, deployment, or promotion is complete.

## 20. Explicit nonclaims

PR5A:

- creates no factual, identity, basis, subject, publication, use, or admission
  authority;
- implements no PR5B-E code and grants no authorization to implement it;
- does not alter PR4A/PR4B1 methodology or numerical behavior;
- does not change `MODEL_RULES_VERSION` or either protected fingerprint;
- does not run real issuer analysis or positive-capital analysis;
- does not change V1, production, deployment, portfolio, Chromebook, or source
  configuration;
- does not declare V2 feature-complete, shadow-ready, production-ready, or promoted;
- does not waive the roadmap's global and broader pre-shadow requirements.

## 21. Validation

Validation for this documentation-only change requires:

- changed-file scope limited to this contract and the narrow roadmap update;
- no production Python, tests, runtime, model, V1, dependency, or configuration
  changes;
- `git diff --check`, `git diff --cached --check`, and committed-tree whitespace
  checks;
- the complete isolated test suite;
- unchanged protected PIT fingerprint
  `f1e73b27b80e41d96ff5e0fe990b482bad71b7220db0b5bd6a2f470d72786166`;
- unchanged protected determinism fingerprint
  `f8457910665391e39c234274cae4c029802c681211eebc7dba986a63000876f1`;
- unchanged `MODEL_RULES_VERSION`
  `2026-08-23-allocation-room-integrity-v7`.

Final executed results are recorded in the PR description and final handoff after
validation. No expected value may be regenerated to make a failure pass.

## 22. Next handoff

After owner review of PR5A, the next proposed chantier is PR5B — Narrow CURRENT
security and EPS qualification. Its contract must start from the then-current
verified V2 integration head, preserve all D-chain nonclaims, positively qualify
ordinary-common participation and route-local relevant-class coverage before EPS
applicability, define exact positive and negative route cases, and stop before
share-basis/reporting-subject admission.

If owner review changes the first-route scope or concludes that an evidence source
cannot positively support PR5B/PR5C, revise this closure plan explicitly. Do not
silently broaden an existing source claim or weaken a blocker to keep the proposed
sequence intact.
