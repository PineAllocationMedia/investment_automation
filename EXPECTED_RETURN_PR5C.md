# PR5C — Comparable real EPS qualification

> Positive historical-presentation comparability only. This contract does not
> establish the denominator basis of a later/current market quote, perform EPS
> normalization, or grant final Expected Return admission.

## Reviewed base and exact scope

After `git fetch origin`, the approved integration ref was exactly:

| Item | Verified value |
| --- | --- |
| Branch | `origin/model-v2/expected-return-challenger` |
| Commit | `64dbfc20b6d3b282ce0d29a80ace22588d556c67` |
| Tree | `755747f3452dd48267e4408ceabd2f41d29ba4c4` |
| Implementation branch | `codex/v2-pr5c-comparable-real-eps` |

The starting worktree and index were clean. The prior local branch was preserved.
This PR adds one strict SEC five-period presentation extractor, one composite
comparability qualifier, focused fictional SEC-shaped fixtures and tests, this
contract, and minimal roadmap/decision clarifications.

It does not modify C3, PR5B, PR5C0A, PR5C0B, the Expected Return calculator or
constructor, model rules, runtime, V1, production, deployment, or provider routes.

## Approved positive route

PR5C supports one deliberately narrow route:

```text
freshly replayed successful PR5B route
+ exact resolved C3 five-period diluted-EPS series
+ one controlled primary 10-K or 10-K/A HTML document
+ one exact five-period reported diluted-EPS presentation
+ freshly replayed PR5C0A reporting-subject source evidence
+ freshly replayed PR5C0B share-basis/action source evidence
-> comparable historical real EPS qualification
```

The presentation must contain exactly five annual columns under the finite
`Years Ended <month> <day>` grammar and one supported reported diluted-EPS row
for common stockholders/common shares. Its period endpoints must equal the five
C3 endpoints. Every value is parsed as an exact `Decimal` and must equal the
corresponding C3 value with no tolerance, rounding repair, arithmetic, inference,
or replacement. C3's original `Decimal` objects and complete observation/version
lineage remain authoritative in every period decision.

Basic-only, adjusted, core, operating, normalized, non-GAAP, Street,
continuing-operations, management-adjusted, malformed, ambiguous, incomplete,
six-period, invalid-decimal, and multiple-candidate presentations fail closed.
PR5C v1 does not stitch partial tables or documents.

## Presentation extractor

```python
extract_sec_five_year_eps_presentation(
    filing_archive: SecFilingArchive,
    request: SecFiveYearEPSPresentationRequest,
) -> SecFiveYearEPSPresentation
```

The frozen/slotted request selects one exact immutable filing receipt. Replay
uses the existing filing-document inventory and accepts only the primary document
of a controlled `10-K` or `10-K/A`. The extractor uses a bounded finite HTML-table
grammar and retains the exact row label, period heading/labels, exact source
values, parsed decimals, table HTML, hash, byte location, filing receipt, document
identity and capture metadata.

It adds no PDF parser, OCR, browser repair, network call, generic scraper, generic
table inference, LLM, or exhibit-profile expansion. Unsupported representations
remain unavailable or unsupported rather than being repaired.

## Fresh replay and closed qualification request

```python
qualify_sec_current_eps_comparability(
    current_archive: SecArchive,
    submissions_archive: SecSubmissionsArchive,
    filing_archive: SecFilingArchive,
    ticker_exchange_archive: SecTickerExchangeArchive,
    nasdaq_listed_archive: NasdaqListedArchive,
    request: SecCurrentEPSComparabilityRequest,
) -> RealEPSComparabilityQualification
```

The request contains exact typed upstream selector requests plus the expected
semantic/evidence identities of PR5B, C3, PR5C0A, PR5C0B and the presentation.
The qualifier freshly replays every layer and rejects any identity mismatch. It
does not accept detached result objects, caller-authored source assessments,
`qualified=True`, same-basis assertions, source bytes, prices, quotes, clocks, or
untyped selectors.

The selected presentation must belong to the exact CIK and controlled filing
route used by the successful PR5B qualification, and its accession must be among
the PR5B EPS-applicability decisions. Foreign CIKs, foreign accessions/routes, or
evidence captured after the PR5B CURRENT boundary fail closed. Same CIK, ticker,
name, or class text alone is not accounting-subject authority.

## Historical share-basis conclusion

The one positive five-period issuer presentation is the authority for the narrow
claim that the five retained values are presented together on one reported
per-share basis. An empty PR5C0B action inventory is permitted but is never
converted into evidence that no action occurred.

If PR5C0B retains a supported effective stock split, reverse split, or stock
dividend, qualification can continue only when:

- exact ratio and effective date are retained;
- the exact named common class matches the freshly replayed PR5B class;
- an affirmative retrospective per-share/EPS claim is in the same controlled
  presentation document and the same source-local action;
- the retrospective scope is `ALL_PERIODS_PRESENTED`; and
- all five presented values still exactly equal C3.

PR5C performs no adjustment arithmetic. Missing/vague/one-period retrospective
treatment, unresolved lifecycle, ambiguous class linkage, conflicting ratio/date,
multiple-class ambiguity, class conversion, recapitalization, merger/security
exchange, spin-off, redenomination, unsupported consolidation, other
basis-affecting action, or uninterpreted basis language blocks the route.

## Historical reporting-subject conclusion

The subject proposition is deliberately local: the one exact controlled filing
presents all five required diluted-EPS periods as one coherent historical
presentation for the exact supported filing entity/security route, with no
retained conflicting subject-transition evidence inside the selected source
surface.

PR5C0A conflict, incomplete selection, unsupported source profile, or retained
predecessor/successor, accounting-acquirer, reverse-acquisition,
reverse-recapitalization, predecessor/successor-period, carve-out, combined-
financial-statement, or uninterpreted restructuring claims block qualification.
PR5C does not claim that a CIK is an eternal reporting subject or that universal
M&A/perimeter continuity has been proved.

## Result, outcomes and identity

The immutable composite result retains separately inspectable historical
share-basis and reporting-subject conclusions, qualified dimensional identities
or `None`, five exact period decisions and lineage, every freshly replayed
upstream result, reason codes, limitations, and the closed outcome vocabulary:

- `COMPARABLE_REAL_EPS_ESTABLISHED`;
- `COMPARABILITY_UNAVAILABLE`;
- `COMPARABILITY_UNSUPPORTED`; and
- `SOURCE_CONFLICT`.

Success requires both dimensions and all five exact value/period matches. A
failed dimension does not erase independent diagnostics, but no composite
authority is emitted. There is no score, percentage, ranking, majority/latest
winner, or first-element selection.

Domain-separated semantic identity binds contract/qualifier versions, PR5B/C3/
PR5C0A/PR5C0B/presentation semantics, route-local identities, dimensional
conclusions, all period decisions, outcome, reasons and limitations. Evidence
identity additionally binds each exact upstream evidence identity, including the
presentation's receipt/document/table bytes. Equivalent recapture can preserve
semantics while changing evidence. Caller order does not change semantics.

## Authority boundary and explicit nonclaims

PR5C establishes only historical five-period presentation comparability at the
exact controlled presentation/evidence boundary. Filing capture time is retained
as capture metadata; it is not relabeled as SEC publication time, PAM historical
availability, or coverage through current market time.

In particular:

- PR5C consumes no current price, bid, ask, quote, quote currency, or market time;
- PR5C does not establish that a later/current quote uses this denominator basis;
- PR5D must positively bridge a controlled current quote to the qualified PR5C
  basis at its own quote boundary;
- PR5E must freshly replay successful PR5C and PR5D before final blocker discharge
  or economic admission;
- C3 blockers are not mutated in place;
- no EPS normalization, corporate-action engine, M&A engine, historical-PIT
  authority, paid source, investment-rule change, recommendation, deployment, or
  V1 behavior is introduced.

Thus PR5C may establish the historical propositions protected by
`SPLIT_BASIS_NOT_ESTABLISHED` and `ECONOMIC_COMPARABILITY_NOT_ESTABLISHED`, but it
does not finally discharge the complete Expected Return graph's split-basis
requirement without PR5D's current quote-to-basis linkage and PR5E's final join.

## Validation contract

Validation uses the repository's pinned Python and locked environment, controlled
fictional SEC-shaped bytes, isolated test execution and denied external authority.
Focused coverage includes the ordinary positive route, explicit split-adjusted
positive route without arithmetic, exact decimal/lineage preservation, every
required presentation/action/subject failure family, foreign/late evidence,
replay forgery, caller ordering, equal-byte recapture and differing-byte conflict.

The complete change is `STANDARD`: all discovered ordinary tests run except only
the isolated heavyweight PIT adapter-equivalence module. Protected PIT and
determinism fingerprints and `MODEL_RULES_VERSION` remain unchanged.

## Handoff

PR5C closes the narrow historical EPS presentation-comparability layer. PR5D is
next and must independently establish a controlled current price/quote, exact
currency/per-share semantics, and a positive quote-to-PR5C-basis bridge, alongside
its remaining reviewed roots. PR5E remains the only final admission join.
