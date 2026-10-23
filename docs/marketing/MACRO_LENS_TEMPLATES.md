# PAM | The Macro Lens — reusable Blossom templates v1.0

**Scope:** `@therealpam` image-post editorial templates, not investment recommendations.
**Policy:** [Editorial playbook](MACRO_LENS_PLAYBOOK.md). **Executable layout renderer + sample SVGs:** [Visual Kit](visual_kit/README.md). Always verify source facts before laying out data. Final rendering and CEO approval are separate gates.

The T1/T2/T3 specifications below now map to three separate deterministic 1080×1350 SVG layouts in `visual_kit/render_macro_lens.py`, with non-publishable synthetic example SVGs in `visual_kit/examples/`. The executable kit contains no source-fetching capability; independent factual and visual audits remain mandatory. Existing visual constraints, template-choice logic and governance below remain authoritative.\n\n## Institutional editorial quality standard

**Required visual-quality review for all T1/T2/T3 drafts:** [Institutional Editorial Design Gate](visual_kit/INSTITUTIONAL_EDITORIAL_STANDARD.md). The target is a concise macro research note for mobile—not an elementary explainer card, a poster of giant numbers or a cramped dashboard. Prefer crisp grid alignment, precise typography, purposeful evidence grouping and restrained color over repetitive oversized rounded tiles. Review the exact 390px PNG using its six PASS/HOLD criteria. Passing source validation and renderer CI alone **does not** certify editorial visual quality. If a draft looks childish, visually cluttered or unintuitive, return **VISUAL HOLD** and propose a controlled, CEO-reviewed renderer adjustment instead of claiming the current template already meets the higher bar.

## Wider PAM Blossom visual families — proposal-only

**Market Atlas / M1 is IMPLEMENTED** via the deterministic [PAM Market Atlas V1 daily standard](visual_kit/MARKET_ATLAS_STANDARD.md) and [M1 code](visual_kit/render_global_index_map.py), with a fixed original 30-country domestic-index mode and an expanded 33-row USD ETF daily mode (28 candidate funds, five no-proxy countries); legacy 30-row ETF research inputs remain supported. Literal **Subject: Market Atlas** in Prompt 2 takes this fixed world-map format automatically. Daily changes are source-linked returns, completed-session comparison dates **near the title**, adaptive continuous legend endpoint numbers, country shades, rankings and English caption; map coordinates, typography, exact approved reconstructed pine master, public footer and 3+3 panel slots remain identical throughout a week. The M1 geography is pinned Natural Earth **1:50m** Admin-0, with identical source polygons for highlighted and neutral land (including detailed Canadian Arctic/island shapes). Its private `GM-...` issue identifier and `AS OF ... UTC` cutoff are retained in the source/manifest and **never printed** on the public image; the footer retains `NOT INVESTMENT ADVICE`. Do not pass an image-tool fallback off as an exact Natural Earth map or approved release artwork. The CEO-approved image-first working fallback is described below; final publication requires geographic accuracy and the independent review. Never add unsupported on-image audit metadata. The source-researcher must actually obtain two completed-session USD exchange-close observations per plotted ETF. The offline renderer does not fetch the data itself. Domestic local-currency national-index mode is explicit opt-in and cannot be mixed with USD ETF moves. The separate T1/T2/T3 and other visual families retain their own specialized standards.

**Current Visual Kit supports T1/T2/T3 and additional merged M1/M2/M4/E1 modules**; choose an implemented renderer, never guess capability from an old roadmap. For a more serious T1 look, follow the separate [institutional T1 restyle implementation brief](visual_kit/INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md); documentation alone does not change rounded cards or WATCH typography.

**Copyright notice:** the CEO-approved reconstructed pine logo stays unchanged; do **not** place `©` next to or inside the emblem. An optional, discreet footer notice may be proposed **only after confirming the actual rights holder and any third-party data/graphic licenses**, with Commercial & Compliance review where needed. Do not imply ownership of underlying market data, supplant essential sources or use `®` without registration evidence. No footer copyright notice is automatically rendered by this proposal.

### Market Atlas Prompt 2: deliver the visual, not a render-status report

For literal **Subject: Market Atlas**, the first deliverable is the image using the CEO's October 20, 2026 reference composition. Prefer exact deterministic M1/50m rendering when the Python runtime can execute its source. **If GitHub code cannot be moved into the local renderer**, that alone is not an editorial stop: directly create/edit the same 1080×1350-style working plate using an available image creation tool, with the factual ETF price results, matching completed-session dates and correct English display text. Do not run an additional bootstrap or submit a research-only handoff in place of the image. A graphical fallback **is not a verified Natural Earth render**; disclose this externally for subsequent independent cartography/figure/source QA before publication. Never claim SVG/390px derivatives, approved-logo exact-byte use, or an asset manifest unless those actual files exist. The source and CEO approval conditions govern *publishing*, not the first visual draft. This exception does not apply to fabricated return data or fake domestic-index coverage.

## Universal visual grammar

- **Canvas:** 1080 × 1350 portrait working target (4:5); test against current Blossom mobile rendering and cropping before publication. A safe-area margin of 64 px is an internal design rule, not a Blossom specification.
- **CEO-approved reconstructed brand anchor (2026-10-19):** botanical pine branch and hanging cone in forest green on a warm-ivory circle. The historical source is unavailable; the newly reconstructed v0.1 2048×2048 PNG was explicitly CEO-approved as the production master. Provenance remains **RECONSTRUCTED**, never **RECOVERED**. Exact file: ChatGPT Library `/PAM/Brand Assets/PAM_Macro_Lens_logo_RECONSTRUCTED_v0.1_APPROVED_2048.png`; canonical SHA-256: `a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75`. See [asset register](visual_kit/assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json). No other file or edited derivative is authorized for release. This logo approval does not replace the independent visual/factual audit and separate CEO approval of each post.
- **Palette:** editorial ink `#11242A`, deep panel forest `#1A3233`, warm ivory `#F4F0E6`, muted sage-gray `#BDC8BE`, soft pine-sage accent `#A6CBB1`, warm amber `#E6C592`, pine-green emblem ink `#284936`. Red/green must express data meaning only, not an implied trade recommendation. Verify contrast in rendered output. Do not turn the series into a generic neon/blue market terminal.
- **Typography:** clear hierarchy; strong 1–2 line headline; short explanatory subhead; one hero signal, diagram or comparable chart; spacious footer with dated source line and account/series attribution. Fonts must be licensed/available; never redistribute font files.
- **Header:** `PAM  /  THE MACRO LENS` with issue date and `MARKET NOTE` or `MACRO EXPLAINER`. Do not use fake “institutional research” credentials.
- **Evidence treatment:** data panels require explicit date, market session, currency/units, provenance. If there is no verified data, use explanatory prose and labeled conceptual diagrams without quantitatively implied scale.
- **Footer:** concise `Sources: [publisher(s)] · Data as of [observation timestamp / timezone]`, and optional `Market commentary • Not investment advice`. Footer is not a substitute for full internal evidence register.
- **Default source-attribution style:** use the shortest **accurate, recognizable publisher name**, e.g. `U.S. BLS`, `BEA`, `Federal Reserve`, `Statistics Canada`, where the abbreviation unambiguously identifies the actual cited publisher. The graphic's `source_title` field is rendered as provided: **the renderer does not automatically abbreviate or authenticate names**. Use a longer name when a short one would be ambiguous or misleading; the T1 footer may wrap safely. Do not hide any materially distinct source used by a displayed number or chart. In the independent evidence register, preserve **full publisher and original document/release title, original URL, observation/retrieval/publication timestamps, units, calculations and verification notes**. A short footer is a navigation aid, not a replacement for provenance.
- **Caption:** natural English, usually 60–120 words but adjust to actual information. Expand the mechanism, not repeat every visual line. Source links may be included when Blossom supports them.
- **Guardrail:** never fill a slot with fabricated numbers, synthetic price paths or unverified claims. For the fixed recurring **Market Atlas** league table, keep the physical slot and show an em dash if exceptionally no qualified market belongs in that position; **do not move the modules or fabricate a performance**.
- **Status — all visual families:** a genuine-source first-render image MUST have **no internal DRAFT / NOT AUDITED / NOT FOR PUBLICATION / AUDIT ONLY / approval-pending wording** in its pixels, including header badges and footers. Preserve draft state and audit/CEO references in the separate exact-asset SHA manifest and review response. Synthetic example images retain a visible `DRAFT · SYNTHETIC TEST` identifier. Bespoke SVGs should pass `visual_kit/artwork_status_guard.py` plus actual exported PNG review. This changes only presentation hygiene; an unwatermarked candidate is still NOT approved until independent evidence/rights/visual audit and exact CEO publication approval.

## T1 controlled institutional restyle — source-bound renderer variant

An **opt-in** `t1_layout: RESEARCH_NOTE` renderer option is included in the pending T1 restyle implementation PR. The default T1 Classic visual stays unchanged; Evidence+ and T2/T3 remain untouched. The Research Note geometry uses aligned rows, hairline dividers, a three-column explanatory strip instead of rounded mechanism cards, and a legible WATCH line. No new economics, data or source rights are introduced. See the [Visual Kit README](visual_kit/README.md) and [restyle design brief](visual_kit/INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md). Never claim this opt-in is in the canonical merged renderer until the implementation PR has been CEO-merged and verified. A visually improved draft still needs the six-point mobile gate, independent fact/visual audit and exact CEO post approval.

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

### Optional T1 Evidence+ pilot — not a replacement for Classic

T1 Classic remains the default. When **additional verified evidence genuinely clarifies the mechanism**, choose opt-in `t1_variant: EVIDENCE_PLUS`: one unchanged hero statistic, **up to two** same-period contextual indicators, and an **optional** compact zero-anchored bar chart with 3–4 strictly consecutive monthly observations of one consistent metric. Draw every bar from checked evidence records, never from invented prices, decorative traces, truncated scales or unsourced labels. Keep the three mechanism stages, blind spot and tripwire prominent. If material comparability/legibility fails, omit the extras or revert to T1 Classic. See [implementation, schema, refusal conditions and synthetic example](visual_kit/T1_EVIDENCE_PLUS.md). CEO approval and independent review remain required.

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

## Decision tree — subject first, format second

On an open-market scan, **do not default to M1 or any other visual family**. Select the most worthwhile verified topic and thesis first, then match the evidence to an implemented contract:

- One strong economic transmission mechanism → **T1**; comparable signals in tension → **T2**; a credible historical regime comparison → **T3**.
- Major *country-level* equity ETF dispersion/leadership is the point → **M1 Market Atlas**; meaningful movements across equities, rates, FX and commodities → **M4 Daily Market Brief**.
- Comparable sector leadership/rotation → **M2**; a documented issuer event or financial-reporting insight → **E1**.
- Another topic better served by a distinct composition → an explicitly **proposed working concept**, or a verified text-only post if no suitable renderer exists.
- No worthwhile source-supported angle → **SKIP**. Never publish filler, pick a template on a fixed schedule, or pretend a concept has a validated renderer.

An explicit CEO topic or literal `Subject: Market Atlas` still takes precedence over autonomous scanning.

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
Institutional editorial six-gate review: PASS | VISUAL HOLD (reason + mobile proof)
Visual hierarchy / restrained panel design / evidence proportionality documented? YES / NO
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
