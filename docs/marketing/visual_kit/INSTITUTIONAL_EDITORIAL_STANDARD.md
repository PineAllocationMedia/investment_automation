# PAM Macro Lens — Institutional Editorial Design Gate v1.0

**Scope:** Blossom `@therealpam` Macro Lens image publications, including T1 Classic, optional T1 Evidence+, T2 and T3. This is a **visual/editorial review standard**, not an authorization to redesign the brand, amend protected governance, relax source evidence, replace the deterministic renderer or publish. The CEO decides whether to merge any proposed design changes and separately approves each exact post.

## Design intent

**A concise, credible macro research note adapted to mobile, not an elementary explainer card or a miniature terminal.**

The image should feel composed by a thoughtful market analyst: a sharp thesis, a verified signal, a visible economic relationship and an honest limitation. It should remain intuitive without becoming simplistic. An institutional look is earned by information architecture and editorial restraint—not by adding numbers, jargon, fake credentials or tiny footnotes.

### The intended hierarchy

1. **Thesis:** one original market/economic point, recognizable in three seconds.
2. **Evidence:** one central verified signal with the correct metric, units, period and as-of context.
3. **Mechanism or comparison:** the economic relationship that makes the signal relevant, readable without caption dependency.
4. **Qualification:** a blind spot, alternative explanation or observable tripwire.
5. **Provenance:** compact, unambiguous publisher labels and observation date in a legible footer; complete source detail lives in the evidence register.

A publication can vary its composition. Do not mechanically add five separate cards to reproduce this five-part reasoning order.

## Art-direction rules for new designs or revisions

- **Research-note framing, not social-card decoration.** Use precise column alignment, consistent baselines, deliberate whitespace and fine dividers. Prefer a coherent page grid over a parade of independent rounded rectangles.
- **Containers must earn their place.** Each filled panel must encode a true conceptual grouping, comparison or data relationship. For exploratory variants, prefer square or subtle-radius surfaces and thin rules. Avoid stacked bubbly tiles, pill badges, ornamental arrows, clip-art, emoji, shadows and gratuitous background gradients. These are design-review rules, not permission to silently alter the merged renderer.
- **No oversized scoreboard.** A hero number is allowed, but it must not dominate at the expense of its label, unit, period or causal explanation. One display-scale metric per issue unless a genuine two-signal comparison is the subject. Do not turn T1 Evidence+ into a miniature dashboard.
- **Typographic authority.** Use a restrained, repeatable hierarchy: headline > signal > mechanism > qualification > source. Prefer informative section titles to repeated schoolbook-style numbering. No fake “institutional,” “bank research,” analyst credentials, ratings, seals or implied affiliations.
- **Restraint in color.** Keep the approved pine, warm ivory and muted editorial palette. Use accent colors to guide attention, not to make the image festive; do not introduce neon, unapproved palettes or red/green trade cues. The approved reconstructed pine emblem and its exact hash remain mandatory for branded release.
- **Evidence makes the design credible.** Extra information is optional: T1 Classic is still the default; T1 Evidence+ may show at most two supported contextual indicators and at most one justified 3–4-month source-linked bar chart under its existing contract. No ornamental graphs, fabricated data density, unlabeled scales or statistical filler.
- **Be accessible, not childish.** Explain technical terms briefly when necessary, but do not talk down to readers. A sharp, plain-English sentence can be analytical; five oversized cartoon arrows are not. Reserve complexity for the economic mechanism, not the frame.
- **A compact footer is not a vague footer.** Use concise accurate labels (e.g. `U.S. BLS`), as-of context and existing advice disclaimer. Retain full original title, URL, observation/retrieval/publication timestamps, units, transformations and calculations for the independent auditor.
- **No premature template-wide change.** An experimental visual style is a DRAFT alternative until the CEO reviews the result, appropriate renderer changes are merged, tests pass, and an independent factual and visual audit checks the exact publication asset.

## Pre-CEO visual acceptance gate

For **each candidate image**, inspect the actual exported PNG (not only source code or an SVG viewer) at native 1080×1350 and downscaled to **390px feed width**; check cropping in the available Blossom posting preview when possible. A 390px mock is a design test, **not** a claim about official Blossom specifications. Read the graphic as an ordinary viewer, without zooming or reading the caption first.

Mark each criterion **PASS / HOLD**, with one short observation:

| Gate | Required observation | Typical HOLD example |
|---|---|---|
| **Thesis first** | A reader can identify the analytical point within ~3 seconds | Cute framing or giant number buries the argument |
| **Visible mechanism** | The economic cause/relationship is apparent in a quick 5–10 second scan | Disconnected statistic tiles, decorative arrows or empty conclusions |
| **Serious restraint** | The composition reads as a considered research note without fake authority | Stacked rounded bubbles, colorful badges, schoolbook illustrations |
| **Proportionate evidence** | Every displayed number or plot improves understanding and is clearly qualified | Data clutter, chart-for-credibility, unlabeled or misleading comparison |
| **Mobile typography** | Headline, signal labels, mechanism, dates, axes and source/disclaimer are readable at 390px; no clipping/overlap | Source legible only after zoom, chart labels colliding, overfull text |
| **Brand and truth** | CEO-approved seal unchanged, approved palette, sourced facts and full evidence packet match image | Substitute logo, made-up figure, missing period, ambiguous publisher |

**Any HOLD blocks a design-quality PASS for that draft.** A factually sound but childish-looking image may be **visual HOLD** and must be redesigned, not published just because the renderer's code tests passed. Conversely, attractive typography never substitutes for independently verifying sources, figures, interpretation and advice/compliance risk. CEO may reject a visually passing draft on editorial grounds.

The reviewer should also state the main trade-off: **What was removed to improve clarity? What information was retained to preserve rigor?** Do not solve "too childish" by reducing body text until it is unreadable, or "more institutional" by adding needless charts.

## Subjects, depth and the actual layout limitation

Use the [Blossom Research Visual System roadmap](../BLOSSOM_VISUAL_SYSTEM_ROADMAP.md) for proposed macro, market, sector, equity and investor-perspective formats. `BRIEF`, `STANDARD` and `DEEP` are levels of **necessary analytical detail**, not different permission to be childish or to lower editorial quality. A deep note with unreadable labels fails the same mobile gate as a light note. The first controlled research-note implementation direction is the [T1 institutional restyle brief](INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md), informed by the CEO-provided Oct. 20 visual HOLD packet. This is a proposed development task; the current renderer's cards are not magically modified by a style specification.

## Controlled upgrade procedure

When the existing canonical template fails this gate:

1. Record the exact deficiency on a **draft** (e.g. `T1: 3 large rounded steps feel like educational flash cards`). Do not claim to have inspected a deleted or inaccessible conversation's old image.
2. Keep the **same sourced issue JSON, facts, caption and approved logo** when comparing a baseline and an alternative. If those bytes do not survive, rebuild the issue and verify it independently rather than inventing continuity.
3. Propose **one bounded visual variable** per iteration (e.g. panel geometry + typographic hierarchy as a coherent art-direction pass). Prefer adapting the existing deterministic SVG renderer; no decorative AI-generated economic diagrams or charts.
4. Export side-by-side mobile-size previews and explain what became clearer, what became harder to see and whether the standard's six gates pass.
5. If accepted, implement via scoped PR with SVG/PNG layout regressions, keep T1/T2/T3 data schemas and source/release gates unchanged, and seek a **new independent audit of the exact render** plus separate CEO per-post publication approval.

**Current limitation:** the pre-existing renderer uses relatively rounded cards and display-scale metrics. Adding this standard to the repository **does not itself restyle its generated images** or establish that the renderer has passed the new gate. Until an approved visual implementation improves the output, mark visual quality **HOLD** whenever a particular draft fails these checks. Never misstate a documentation-only PR as a finished design refresh.
