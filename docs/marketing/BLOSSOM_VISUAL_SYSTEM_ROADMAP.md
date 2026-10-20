# PAM Blossom — Research Visual System roadmap v0.1 (PROPOSAL)

**Status:** CEO review only. **Account:** `@therealpam`. **Purpose:** expand useful finance/investing communication beyond macro while maintaining one approved PAM identity, reliable sourcing, accessible mobile explanation and explicit CEO publication control.

**Implementation state in this change set:** Macro Lens `T1` (Classic, optional Research Note and Evidence+), `T2`, `T3`, plus a **bounded M4 Cross-Asset Market Brief renderer candidate**, documented in [M4 pilot contract](visual_kit/M4_DAILY_MARKET_BRIEF.md). M4 is code-implemented on this PR branch but **not canonical until CEO merge** and not an approved post without real original-source/data-rights review, independent exact-asset audit and separate CEO post approval. All other M/E/P layouts, feeds, instrument mappings and capabilities remain **PROPOSED/NOT IMPLEMENTED**. Do not confuse an implemented source-bound renderer with live automated market data.

Related: [institutional visual gate](visual_kit/INSTITUTIONAL_EDITORIAL_STANDARD.md) · [Global Market Map methodology](visual_kit/GLOBAL_MARKET_MAP_M1_SPEC.md) · [T1 institutional restyle proposal](visual_kit/INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md) · [current templates](MACRO_LENS_TEMPLATES.md).

## 1. Two-axis design: subjects × depth, not “degrees of professionalism”

**One non-negotiable professional baseline** for all posts. Do not label an accessible post “less professional.” Vary **analytical depth and the shape of the evidence** to fit the research question:

| Editorial depth | Intended use | Data/visual envelope (guideline; never a quota) | Reading experience |
|---|---|---|---|
| `BRIEF` — editorial note | One sharp claim, misconception or observation | One central verified fact or qualified thesis; optional single relationship | Understand it in ~5 seconds |
| `STANDARD` — research note (default) | A signal plus mechanism, company development or market comparison | Central signal, 1–2 high-value contextual facts when justified, clear qualifier | Understand thesis quickly; inspect evidence in ~10–20 seconds |
| `DEEP` — research plate (exception) | Actual comparison, sector decomposition, earnings/valuation framework or global coverage | Multiple independently verified comparable observations, perhaps one dominant chart/map and a bounded table | Readable mobile overview plus exact methodology/evidence available outside image |

**DEEP is not inherently more credible**. On a 1080×1350 canvas, when labels, uncertainty, axes or sources are too small, **split into separately audited panels, move detail to caption or choose STANDARD**. Never add mock institutional insignia, unverifiable ratings or data filler.

## 2. Proposed subject families and design motifs

All names/IDs below are **proposals**, not registered production templates. The existing Macro Lens name is preserved. The umbrella `PAM Research Visual System` is an internal library label, **not a public positioning/rebrand decision**.

| Family / proposed ID | Editorial use | Distinct composition | Required substantive gate |
|---|---|---|---|
| **Macro Lens** `T1/T2/T3` (implemented) | Rates, inflation, FX, credit, mechanisms, divergence, regime context | Mechanism / two-signal / matched-period comparison | Existing source, comparability, logo and publication contracts |
| **Macro Lens** `T4 Global Pulse` | Major regional financial-condition developments | Carefully labeled comparable country/region strips | Measurement and synchronized-vintage review |
| **Markets** `M1 Global Equity Map` | Same-session cross-country equity-market breadth | **Accurate geographic choropleth**, compact rank movers and methodology | Strict map/proxy/currency/session contract; see M1 spec |
| **Markets** `M2 Sector Rotation` (**implementation candidate, CEO merge pending**) | Eleven comparable U.S. large-cap sector index price returns over 20 eligible sessions, with one-session context | Zero-centered ranked return strips, calculated breadth, leader–laggard spread | One sector taxonomy/index family/currency/close clock; real data and rights review, [M2 specification](visual_kit/M2_SECTOR_ROTATION.md) |
| **Markets** `M3 Breadth & Leadership` | How much of an index participates in its move | Headline + breadth/weighting comparison | Same index universe and reconstitution date; valid constituents |
| **Markets** `M4 Cross-Asset Pulse` (**implementation pilot**) | Two equity gauges at most, rates, FX and commodity latest completed session returns/movements | Source-attributed cross-asset table with separate percent/bp measures, one thesis and WATCH | Explicit measurement/venue/currency/timezone and source-rights checks; [M4 contract](visual_kit/M4_DAILY_MARKET_BRIEF.md) |
| **Equity** `E1 Company Lens` | Material company event, fundamentals and narrative | Thesis, two or three cited facts, counter-case, what to watch | Primary issuer filing and exact period, currency, GAAP/non-GAAP basis |
| **Equity** `E2 Earnings Bridge` | Explain change in growth/margins/guidance | Decomposition of reported drivers or bounded scenario comparison | Same units/base periods, no invented attribution; forecast clearly marked |
| **Equity** `E3 Valuation Debate` | Valuation vs fundamental assumptions | Assumption/evidence matrix, not target-price recommendation | Separate observed price/multiples from assumptions; no buy/sell instruction |
| **Sector** `S1 Industry Structure` | Supply chains, capacity, competitive landscape | Driver matrix or source-traced flow; bounded uncertainty | Source-qualified segments, companies and periods; licensing |
| **Investor Perspective** `P1 Narrative vs Evidence` | Common finance misconceptions, portfolio thinking | Claim / actual evidence / caveat | No false generalization, no personalized portfolio advice |

Avoid a generic chart catalogue. Each new template must solve a meaningfully distinct **evidence and comprehension** problem. Do not mandate symbols, flags, national icons or ticker logos without rights review.

## 3. Editorial selection and bounded adaptation

**SCAN → PICK → VERIFY → DECIDE FOCUS → SELECT FAMILY → SELECT DEPTH → ASSEMBLE → RENDER → INDEPENDENT AUDIT → CEO APPROVAL.**

A scan of latest developments is *not* limited to Macro Lens: assess macro, markets, sectors and issuers. Pick the strongest genuine insight, not a template-shaped opportunity. Select the family **after** source and narrative evaluation, then choose depth according to available comparable evidence. If no relevant implemented template can express the subject accurately, choose a short sourced **text-only** post or prepare a proposed unpublishable layout for CEO review; **do not silently treat a roadmap-only template as implemented**.

Allowed adaptation **within an approved implemented family**: choose wording, omit optional content, use its declared data-bound fields, select approved hierarchy variants and rational spacing within tested safe bounds. A new chart type, geographic geometry, color semantic, data schema, font hierarchy or asset placement outside those tested bounds is **a design variant requiring implementation PR and mobile regression**. Do not ask a generative image tool to fabricate quantitative visuals.

**Reason for template choice (required):** `signal/question | why this family | why this depth | what was omitted | evidence/assumption limits | fallback`. For M1, identify the precise cross-market relationship worth interpreting; “markets went up/down” alone may not justify a post. Record `template_status: IMPLEMENTED | PROPOSED`, and `visual_quality: PASS | VISUAL_HOLD`.

## 4. Brand, rights and footer

Keep the **exact CEO-approved reconstructed pine-cone emblem** with existing byte-hash checks. **Do not add a copyright mark beside the logo**: `©` is a notice, not part of the approved master asset. Do not embed it into, modify or recrop the master.

If the CEO wants a notice, use **a quiet optional footer line** separate from source/date/disclaimer, subject to a rights-owner and Commercial & Compliance check; example *only if accurate*: `© 2026 [confirmed legal rights holder]`. Verify ownership, year, jurisdiction/context and whether third-party source/geo/chart assets have their own attribution obligations. A copyright notice **does not confer ownership of economic data**, imply a trademark registration, replace a source credit, establish exclusivity or substitute for permission/licenses. Never use `®` without verified registration. If an accurate rights holder cannot be established, **omit notice** rather than claim it.

For all families: keep short **unambiguous** on-graphic publisher names, exact as-of/observation context and an advice-risk line when required. Retain complete original release, URLs, instrument definitions, calculations, vintage, rights notes and audit materials outside the image. Source/attribution and disclosure lines must remain **visibly readable at 390px**; copyright text is optional and must never displace these.

## 5. Institutional look without hiding the argument

This roadmap adopts the [six-point visual gate](visual_kit/INSTITUTIONAL_EDITORIAL_STANDARD.md) for all proposed family implementations. The first trial should directly address the supplied Oct. 20 T1 draft's **three over-rounded mechanism cards, instructional numbering, small WATCH note and excessive empty lower region**. Use a thinner-column-and-rule research-note hierarchy while keeping the same facts, source and caption; reference the [controlled T1 restyle](visual_kit/INSTITUTIONAL_T1_RESTYLE_PROPOSAL.md). The old draft's review was **VISUAL HOLD**, not a factual-audit PASS or publication authorization.

Institutionalism is **not** tiny text, more indicators, longer captions or an invented institutional research department. One central insight, precise labels, clear evidence, meaningful negative space and repeatable typography should create authority.

## 6. Implementation order and launch gates

1. **Restyle T1 Classic in a separate controlled renderer PR**: same input JSON, SHA-approved logo and facts; baseline versus proposed 390px PNG; check new geometry, human comprehension, old/new source footer, no T2/T3 changes. Keep current T1 available until CEO selects direction.
2. **Prototype M1 methodology and geography**: evidence table and mapping choices first, then accurate licensed/publicly usable boundary data and tests. **No publishable choropleth until complete validated data + visual + accessibility audits.**
3. Implement one of `M2` or `E1` **after** identifying a sourced story that merits it. Avoid creating unused templates.
4. Add further families only after real readability and editorial feedback. Track actual results, not hypothetical engagement.

**Implementation PR minimum:** bounded contract; approved reusable libraries/rights and resource assessment; evidence schema + source provenance; synthetic visual fixtures clearly labeled DRAFT; exact renderer tests for clipping/mobile/currency/axis/legend; negative tests (stale, missing, contradictory, invalid rights); independent factual + visual audit of *each real post*; CEO merge and separate post approval. This roadmap **does not add** any implemented template or market-data integration.
