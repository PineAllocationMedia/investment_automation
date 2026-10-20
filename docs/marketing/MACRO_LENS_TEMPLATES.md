# PAM | The Macro Lens — reusable Blossom templates v1.0

**Scope:** `@therealpam` image-post editorial templates, not investment recommendations.
**Policy:** [Editorial playbook](MACRO_LENS_PLAYBOOK.md). **Executable layout renderer + sample SVGs:** [Visual Kit](visual_kit/README.md). Always verify source facts before laying out data. Final rendering and CEO approval are separate gates.

The T1/T2/T3 specifications below now map to three separate deterministic 1080×1350 SVG layouts in `visual_kit/render_macro_lens.py`, with non-publishable synthetic example SVGs in `visual_kit/examples/`. The executable kit contains no source-fetching capability; independent factual and visual audits remain mandatory. Existing visual constraints, template-choice logic and governance below remain authoritative.\n\n## Universal visual grammar

- **Canvas:** 1080 × 1350 portrait working target (4:5); test against current Blossom mobile rendering and cropping before publication. A safe-area margin of 64 px is an internal design rule, not a Blossom specification.
- **Verified Blossom brand anchor (CEO screenshot, 2026-10-19):** a botanical forest-green pine branch and hanging pine cone, on a warm-ivory circular background. Treat this as a visual identity reference—not as a clean production image file. Obtain the actual square logo PNG from the CEO before releasing a final graphic. No guessed redraw, screenshot crop, or generic corporate replacement may be presented as the official logo.
- **Palette:** editorial ink `#11242A`, deep panel forest `#1A3233`, warm ivory `#F4F0E6`, muted sage-gray `#BDC8BE`, soft pine-sage accent `#A6CBB1`, warm amber `#E6C592`, pine-green emblem ink `#284936`. Red/green must express data meaning only, not an implied trade recommendation. Verify contrast in rendered output. Do not turn the series into a generic neon/blue market terminal.
- **Typography:** clear hierarchy; strong 1–2 line headline; short explanatory subhead; one hero signal, diagram or comparable chart; spacious footer with dated source line and account/series attribution. Fonts must be licensed/available; never redistribute font files.
- **Header:** `PAM  /  THE MACRO LENS` with issue date and `MARKET NOTE` or `MACRO EXPLAINER`. Do not use fake “institutional research” credentials.
- **Evidence treatment:** data panels require explicit date, market session, currency/units, provenance. If there is no verified data, use explanatory prose and labeled conceptual diagrams without quantitatively implied scale.
- **Footer:** concise `Sources: [publisher(s)] · Data as of [observation timestamp / timezone]`, and optional `Market commentary • Not investment advice`. Footer is not a substitute for full internal evidence register.
- **Caption:** natural English, usually 60–120 words but adjust to actual information. Expand the mechanism, not repeat every visual line. Source links may be included when Blossom supports them.
- **Guardrail:** never fill an empty slot with fabricated numbers, synthetic ticks/price paths, unverified claims or an irrelevant statistic. Delete the slot instead.
- **Status:** all drafts and design assets should visibly indicate `DRAFT / NOT VERIFIED` until the final fact audit passes. Remove the draft mark only after an explicit PASS; no publication without CEO approval.

## T1 — THE MECHANISM

**Purpose:** explain one real transmission chain: economic signal → intermediate forces → relevant market implication.

**Appropriate for:** changes in yields, dollar, liquidity, credit spreads, inflation expectations, economic policy. The chain must be qualified when conditional.

**Mobile image layout**
1. Small PAM header, issue date / observed time.
2. One-line editorial headline highlighting a tension or overlooked mechanism.
3. **Observed signal**: one sourced fact in a bounded panel, with as-of timestamp.
4. **Mechanism**: 2–3 connected text nodes. Connections use cautious language (`can`, `all else equal`) when effects are conditional.
5. **Blind spot**: a single original observation, distinguished from fact.
6. **Tripwire**: an observable macro datapoint that would weaken the interpretation.
7. Sources/date footer.

**Writing scaffold**

> HEADLINE: [specific tension, not a prediction]
>
> THE SIGNAL: [verified claim, date/unit]
>
> WHY IT MATTERS: [mechanism in plain language]
>
> WHAT GETS MISSED: [interpretation with appropriate uncertainty]
>
> WHAT TO WATCH: [observable test, not a trade instruction]

**Example headline pattern (not factual claim):** `[Market narrative] sounds simple. [Transmission mechanism] complicates it.`

**Abstention:** no causal explanation supported by defensible economic reasoning → text-only explanation with multiple possibilities, or skip.

## T2 — THE DIVERGENCE

**Purpose:** explain why two market/economic signals are disagreeing, including why the conflict may be only apparent.

**Appropriate for:** equity optimism versus credit stress, currency versus trade narrative, earnings growth versus valuation changes, nominal versus real yields.

**Mobile image layout**
1. PAM header and issue date.
2. Headline: `Two signals. One uncomfortable question.` is an optional *pattern*; do not repeat verbatim each issue.
3. Two matched side-by-side evidence panels (**A** and **B**) with comparable dates, reference periods and proper definitions.
4. Central **explanation** or uncertainty callout: why both could coexist.
5. **What resolves the tension?** One or two measurable future observations.
6. Compact sources/date footer.

**Writing scaffold**

> A: [verified macro observation with timestamp]
>
> B: [verified market observation, comparable timestamp]
>
> The tension: [clearly posed question]
>
> Our interpretation: [conditional hypothesis and alternative]
>
> Reality check: [what evidence distinguishes explanations]

**Abstention:** if series are from non-comparable periods/units and cannot be fairly reconciled, do not publish misleading juxtaposition.

## T3 — THE REGIME SHIFT

**Purpose:** provide historical context for a changing macro regime without pretending to identify turning points precisely.

**Appropriate for:** changing inflation dynamics, monetary policy stance, productivity/earnings composition, credit cycles, policy reversals.

**Mobile image layout**
1. PAM header/date and one sharp conclusion-style headline, appropriately qualified.
2. **Then vs Now**: matched official observations or a genuine plotted time series with explicit axis, source and period.
3. **What changed structurally?** 1–2 causal/conditional mechanisms.
4. **What would disprove this shift?** A single testable observation.
5. Source and vintage footer.

**Writing scaffold**

> WHAT LOOKED TRUE BEFORE: [past observation, evidence period]
>
> WHAT LOOKS DIFFERENT NOW: [current observation, evidence period]
>
> POSSIBLE REGIME MECHANISM: [interpretation + uncertainty]
>
> TEST: [observation that would distinguish regime from noise]

**Abstention:** insufficient history or revisions invalidate comparison → no regime claim.

## Decision tree

- One strong verified mechanism → **T1**.
- Two genuinely comparable signals with a useful tension → **T2**.
- Sufficient historical evidence for a time-based comparison → **T3**.
- No suitable evidence or macro angle → **SKIP** or a short text-only verified Blossom post.

Do not add decorative stock charts, sparklines or “buy the dip” labels merely because space exists. The stable identity comes from precise explanation and consistently branded readability, not identical module density.

## Edition assembly checklist

```text
Issue ID: ML-YYYYMMDD-XX
Blossom account: @therealpam
Session/date/timezone:
Template: T1 | T2 | T3 | TEXT ONLY
Template version: 1.0
Fact sheet ID/link:
Source URLs, units and observation timestamps complete? YES / NO
Actual image checked against fact sheet? YES / NO
Clarity at Blossom mobile crop checked? YES / NO
Caption and image mutually consistent? YES / NO
Causal language and scenario uncertainty checked? YES / NO
Investment advice / affiliate risk checked? YES / NO
Independent review: PASS | HOLD | REJECT
CEO approval: PENDING | APPROVED | DECLINED
Publication: DRAFT | APPROVED_NOT_PUBLISHED | PUBLISHED
URL (ONLY IF ACTUALLY PUBLISHED):
```

## Design / experimentation boundary

Keep header, palette, type hierarchy, accessibility and disclosure stable for a pilot. Change only one major editorial variable per designed experiment: e.g., T1 mechanism diagram versus short narrative with comparable topic; declarative versus question headline; number of data points. Do not change brand palette, template, text length, topic, and publishing time all at once and then attribute results to the visual.

Do not automatically pick whichever style “wins” a single post. Performance evaluation must follow the playbook and [editorial log](MACRO_LENS_EDITORIAL_LOG.md).

## Evidence register template

Use one record per material claim and include source-specific rights notes where relevant.

| Claim ID | Literal claim | Type (FACT/INTERPRETATION/HYPOTHESIS) | Original source URL | Published / retrieved / observed (TZ) | Units / reference period | Calculation / corroboration | Verification |
|---|---|---|---|---|---|---|---|
| [id] | [text] | [type] | [URL] | [timestamps] | [units] | [method] | UNRESOLVED |

## Audit issue template

| ID | Severity | Image/caption location | Source and specific problem | Required correction | Recheck |
|---|---|---|---|---|---|
| [id] | BLOCKER/MATERIAL/MINOR | [where] | [what failed] | [exact fix] | PENDING |

**No placeholder row is publishable data.**
