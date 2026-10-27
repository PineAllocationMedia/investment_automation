# Unified Private Durability Research Sheet V1

Work Order: `WO-V2-STAGE-D-UNIFIED-RESEARCH-SHEET-V1`.
Primary Work Order owner: Product & UX; implementation executor: Codex Development.
Version: `2026-10-26-unified-private-durability-research-sheet-v1`.
Status: implementation candidate; independent review and CEO merge remain required.
Sheet authority: `PRIVATE_RESEARCH_PRESENTATION_ONLY`.

## Interface and separate authority

`src.unified_durability_research_sheet.render_unified_durability_research_sheet_v1(qualification, note=None) -> str`
returns one deterministic standalone private HTML document with:

1. **A. Reported annual financial context:** native
   [Contract A](CURRENT_ANNUAL_ISSUER_TWO_PERIOD_REVENUE_OPERATING_INCOME_QUALIFICATION_V1.md),
   [D1](D1_TWO_PERIOD_OPERATING_PROFIT_CONTINUITY_DIAGNOSTIC_V1.md) and
   [D2](D2_TWO_PERIOD_REPORTED_TRAJECTORY_DIAGNOSTIC_V1.md) outputs only.
2. **B. Manual qualitative research:** the existing
   [qualitative note](QUALITATIVE_DURABILITY_RESEARCH_NOTE_V1.md), retaining its
   `MANUAL_RESEARCH_ONLY / NOT_NATIVE_EVIDENCE_ADMISSION / CURRENT_CAPTURE_BOUND_ONLY`
   boundary, operator review metadata and evidence limitations.
3. **C. Research synthesis:** the note's operator-authored conclusion, escaped and
   displayed once. If absent, `NOT PROVIDED`. No generated conclusion is supplied.

The only financial input is the exact native
`CurrentAnnualIssuerTwoPeriodRevenueOperatingIncomeQualificationV1` with its
original archive binding. There is no precomputed-D1/D2 input, financial dictionary,
identity-string shortcut, source-selector override or caller-supplied fact route.
The optional manual argument must be the exact existing note type; `None` creates
an empty unreviewed note with explicit missing information. Invalid manual data
raise the existing `ResearchNoteError`, not a financial availability result.

This is single-security private research context, not security admission. Native
financial identity is issuer-level CIK context. Any supplied qualitative artifact
is operator-selected: its issuer name, reference, source location and review status
do not authenticate its association with that CIK. This limitation is always
displayed, even if names/references happen to match. No financial-to-narrative join
or common native evidence identity is established. Same-issuer statements are not
independent corroboration; D1/D2 changes are not attributed to a manual hypothesis.

## Native financial verification and status handling

The adapter resolves the native qualification module through D1's existing exact
canonical type gate, preserving the model/source dependency direction without
importing `economic_facts` into `src`. It invokes Contract A's existing
`_verified_comparative_snapshot`.
It derives D1 and D2 through their unchanged native analyzers from that same exact
reconstructed bound qualification. Each analyzer independently replays through its
existing trusted boundary. This intentionally retains three native replays rather
than adding a cache, bypass or alternative trust layer.

Before combining a financial table, the adapter requires exact analytical result
types; equal verified Contract-A semantic/evidence identities, upstream status and
reasons; coherent CIK, annual periods and four facts; matching accounting semantics;
and consistent analytical availability. Independent recapture with equal economics
but different evidence identity cannot supply one half of a paired comparison.
Caller-provided result instances are never accepted as financial input. No new
financial formula, comparability rule or evidence authority is introduced.

| Condition | Financial section |
|---|---|
| `AVAILABLE` | Established four facts, exact dates and permitted D1/D2 analytical values |
| `NOT_APPLICABLE` | Established facts/dates/reasons; D1 signs and continuity retained; no ratios/ratio direction or D2 directions/relative change |
| `UNAVAILABLE / UNSUPPORTED / SOURCE_CONFLICT` | Exact native/analytical statuses and separate reasons; no comparative facts or periods table, no guessed zero/flat/negative judgment |
| Invalid, detached, forged, mismatched or broken evidence | Explicit `INTEGRITY_FAILURE`; no financial facts, analytical outputs or unverified identities displayed |

Native integrity exceptions, analytical contract exceptions, pairing errors and
archive I/O errors stop the financial presentation. They never become ordinary
`UNAVAILABLE`. The failure text is fixed and excludes exception text, private
archive paths and supplied identities. The independent manual section may still
be shown, retaining its limitations. Unexpected programming errors propagate.

The financial section displays verified CIK, namespace/concepts, US-GAAP reporting
basis, USD unit, bound capture timestamp, native qualification reasons, permitted
annual facts and dates, D1 signs/continuity/ratios/difference/direction, D2 amount
directions/relative Revenue change, analytical/upstream reasons and limitations.
Expandable read-only details distinguish Contract A's native semantic/evidence
identity, receipt/object/source/filing references from D1/D2 analytical identities
and their native evidence binding. Capture date is taken from the verified bound
snapshot; no current-clock or operator capture-date substitute exists. Local native
LIVE provenance does not imply remote cryptographic SEC attestation or source-use rights.

Finite Decimals are shown using exact `str(Decimal)` text; any exponent notation
is exact and explicitly explained. Ratios show the native integer numerator and
denominator, including signs and canonical zero, without new division, floating
point, rounding or percentages. Missing analytical values display `NOT PROVIDED`.

## Safe HTML reuse and isolation

The minimal backwards-compatible extension to the qualitative module is
`render_qualitative_durability_research_note_fragment_v1(note, *, include_conclusion=True)`.
It uses the same validation, escaping, authority notices and content as the existing
renderer, but returns no doctype/html/head/body wrappers. The exact-boolean option
only suppresses the manually authored conclusion so the sheet can place it once
in section C. It changes no review or evidence authority. The existing standalone
function retains its signature and byte-identical HTML for baseline empty and
complete fictional notes. The old contract version and all old tests are preserved.

The adapter composes trusted renderer fragments, never a nested standalone document
or runtime string surgery. Operator text is escaped; source locators are inert text.
No scripts, active links or external assets are introduced. A restrictive CSP blocks
scripts/network assets, base URLs and form actions. Native `details` elements only
expand read-only provenance/limitations. The fragment alone relies on the containing
document's CSP; the existing standalone and new sheet both supply it.

No file writes, acquisition, persistence, publication, clock or randomness occur.
Financial authentication necessarily performs **existing read-only local archive
reads**; these are the sole intended I/O exception to offline formatting. Manual
locators are never opened. No new data acquisition, evidence qualification layer,
V1 runtime/compact-report, scoring, allocation or recommendation integration exists.
No original Microsoft evidence or authentic issuer assertions are test fixtures.

## EXISTING TECHNOLOGY & RESOURCE REUSE ASSESSMENT

REUSE the current PAM baseline: trusted Contract A replay, unchanged D1/D2 analyzers
and the existing safe manual-note representation/renderer. ADAPT only the minimal
qualitative fragment seam needed to compose valid HTML; BUILD only this presentation
adapter. A general template framework, financial recalculation engine or new evidence
join is unnecessary. Current first-party code/contract versions were inspected;
no outside code is copied, dependency installed or third-party service adopted.

REUSE the pinned Python standard library, including
[`html.escape`](https://docs.python.org/3.12/library/html.html), under the existing
[PSF license](https://docs.python.org/3.12/license.html) and its notice obligations;
official sources/license were checked in this implementation session's preceding
manual-note assessment. Commercial software-use permission is separate from source
data display/redistribution rights, which this adapter does not establish.
Mandatory incremental acquisition/integration/operation cost: **$0 default satisfied**;
no paid tier, API, hardware, hosting, model, download or ongoing service is required.

Consulted [execution environments](../../../operations/PAM_EXECUTION_ENVIRONMENTS.md):
CPU-only existing Python 3.12.13 and locked environment; no accelerator or external
compute. Three full native replays incur inherited source-size-dependent CPU/RAM
and read overhead; no new resource ceiling or complexity benchmark is claimed.
Mac validation does not certify Chromebook compatibility or deployment; its older
system Python and unknown effective memory constraints remain unresolved.

## Scope and validation handoff

Verified base: `model-v2/expected-return-challenger`,
`b099691738d26152b97142702b002e6e58a4d441`, tree
`d4bcfb336ae4a8052703d4b0ec4b180fb5f531b2`. Scope: this new contract, one adapter,
one focused test module and the necessary qualitative renderer fragment refactor.
No native financial implementation, existing tests, other contracts, protected
governance, configuration or workflow change is authorized or made.

Focused tests cover complete fictional capture, exact identities, wrong-source and
recapture mismatches, detached/forged inputs, all nonavailable states, distinct
NOT_APPLICABLE behavior, broken receipts/objects, missing manual content, unauthenticated
association, same-issuer corroboration limits, conclusion placement, hostile text,
document composition, exact hostile-Decimal formatting, deterministic read-only
replay and byte-exact standalone compatibility. Adjacent native D1/D2, Contract A
and qualitative tests plus full `FULL_PIT`, four-mode and protected fingerprint/model
checks are required. Exact tested commit, commands/counts and limitations are recorded
in the PR handoff. Synthetic mechanics are never authentic issuer qualification.

Evidence-authority limits remain unchanged; Stage D remains `INCOMPLETE`. Required
next step is bounded independent review and a separate CEO merge decision. No new
specialist activity, source campaign, D3, protected amendment, paid CI, manual rerun,
protection bypass, deployment, promotion or autonomous follow-up is activated.
The CEO-reported exhausted free Actions quota permits disclosed PR publication on
successful local validation; no GitHub CI PASS is established or assumed.
