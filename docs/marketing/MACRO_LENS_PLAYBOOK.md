# PAM | The Macro Lens — Blossom editorial playbook v1.0

**Status:** Proposed operational playbook; takes effect only after CEO approval and merge.
**Owner:** Marketing & GTM under the existing bounded Blossom `@therealpam` mandate.
**Channel:** Blossom posts on `@therealpam` only, unless separately authorized.
**Authority:** Research, drafting, visual preparation, audit coordination and measurement; **no autonomous publication**.
**Companion files:** [Templates](MACRO_LENS_TEMPLATES.md) · [Visual Kit](visual_kit/README.md) · [Institutional Editorial Design Gate](visual_kit/INSTITUTIONAL_EDITORIAL_STANDARD.md) · [Editorial log](MACRO_LENS_EDITORIAL_LOG.md) · [Role charter](../../governance/roles/MARKETING_GTM.md).

## 1. Why this exists

Create an investing/finance account genuinely worth following: timely, original, understandable macroeconomic explanations with institutional research discipline, **without pretending to be an institution or selling investment recommendations**. PAM promotion is incidental. The audience's understanding is more important than post cadence or engagement.

Signature lens: **SIGNAL → MECHANISM → BLIND SPOT → TRIPWIRE**.

- **Signal:** a verified development, with correct observation period.
- **Mechanism:** *how* rates, currency, credit, liquidity, inflation, growth, productivity, or capital flows plausibly transmit into other markets.
- **Blind spot:** a non-obvious, defensible consideration, not manufactured contrarianism.
- **Tripwire:** an observable fact that could change the analysis, **not** a trading trigger.

These are internal editorial questions, **not mandatory identical headings on every graphic**. Write naturally; witty when earned; nuance is a strength. Never imitate a recognizable commentator's phrasing, publishing identity or proprietary layout. Avoid AI-market-news bingo cards, invented urgency, forced conclusions and fake terminal aesthetics. Do not claim originality if the insight is standard.

## Additional Blossom subject families (roadmap; no new runtime authority)

The `@therealpam` mandate spans macro, companies, sectors, valuations and cross-asset markets. **Default open-subject Prompt 2** — including `Subject: Best subject according to your interpretation of today's events` or `SCAN CURRENT MARKETS` — delegates *subject selection* to the editor. Scan today's meaningful developments, consider competing story opportunities, and select the one offering the best combination of timeliness, audience relevance, distinctive verified insight, and a clear visual explanation. **Choose the subject and thesis first; choose T1/T2/T3, M1, M2, M4, E1, or a bounded original concept afterward.** Never select Market Atlas merely because it is daily: use it when the geographic breadth/dispersion is itself the story. Do not favor whatever appears most sensational; credibility and insight outrank predicted likes. If nothing merits an intelligent post, recommend SKIP rather than filler. No template quotas, rotating calendar or autonomous posting. See [the visual roadmap](BLOSSOM_VISUAL_SYSTEM_ROADMAP.md) for optional subject families and depth; its proposed layouts are not automatically implemented.

**Market Atlas / canonical M1 routing:** The CEO's literal **Subject: Market Atlas** in Prompt 2 routes immediately to the standardized daily M1 world-market performance map (USD U.S.-listed country ETF proxy default, domestic indices only by explicit opt-in). Use the versioned [Market Atlas design and sourcing contract](visual_kit/MARKET_ATLAS_STANDARD.md) and [daily research-to-image runbook](visual_kit/M1_PRACTICAL_DAILY_WORKFLOW.md). The employee must search genuine closing-price pairs comprehensively across the 28 currently registered ETF candidates (25 original plus Argentina, Chile and Thailand), retrying viable source families before giving up; issuer directories alone are NOT quotation evidence. Missing some of the 28 ETF price pairs is a research-retry signal, **not** a 4/6-market arbitrary global rendering veto. No invented data, false cross-market basis or access-term bypass. An authentic ETF observation can be rendered to the **same clean, final-looking master template**, with fixed 3+3 row slots (blanks only when truly necessary). Daily data and dynamic colors change but title, brand, module coordinates, fonts, six-slot ranking layout and date/footer structure do not drift across the week. The first ordinary image generated has **no DRAFT / AUDIT ONLY / NOT FOR PUBLICATION visual overlay**. Prompt 2 emits exact native/390px assets, English race-style caption, factual price CSV and SHA-256 manifest; Prompt 3 independently audits those unchanged bytes, source facts and caption, without rerendering. Separate CEO approval of that exact post remains mandatory; a final-looking image is **not** an approval. This Market Atlas V1 behavior is canonical after merged PR #206; the Natural Earth 1:50m and public chrome corrections are canonical after merged PR #207. The renderer remains an OFFLINE assembler, not an automatic quote feed.

**Market Atlas image-first recovery (Prompt 2; CEO direction):** A read-only GitHub connector and an isolated Python sandbox may not share files. This is an execution-tool limitation, **not a reason to return only `RENDER HOLD` when valid priced data and image creation capability are available**. First use the deterministic M1 renderer if its source is executable in the active environment; do not start a bootstrap, create a PR or demand a Git checkout merely to produce the working image. If that exact renderer cannot execute, **use the active conversation's available image creation/editing capability immediately with the CEO's October 20, 2026 visual reference and actual sourced current/prior ETF returns**. Deliver a professional 4:5 working image first, maintaining the registered masthead, world-map placement, 3+3 table, zero-centered colors, dated sessions, FX/source line and NOT INVESTMENT ADVICE. Do not present a generative/geographically unverified working image as a deterministic 50m output or claim its absent SVG/PNG hashes. State the rendering method and any geometry/lettering limitations **outside** the artwork. This fallback is for visual production, **never automatic publication**: independent geography/fact/source-rights/legibility review and exact CEO approval are still required before Blossom use. When no image-capable tool exists at all, report that real tool limitation briefly rather than pretending an image was made. Never reuse an old session's pixels as updated data, invent returns, or silently substitute national indices.

**Market Atlas weekly visual consistency:** Keep one registered institutional M1 visual grammar across seven consecutive requests. Use the pinned Natural Earth 1:50m country geometry merged in PR #207 (not invented alternate overlays); the actual country fill and land outline must use the very same polygon paths. Keep internal `GM-...` IDs and UTC audit/render cutoff OFF the graphic and inside the issue/manifest; retain the visible completed-US-session comparison near the title and NOT INVESTMENT ADVICE bottom-right. Same PAM pine brand, fixed positions of world map/legend/top-three and bottom-three/date blocks, identical typography and footer, continuous zero-centered dynamically labelled red/green scale, exact-zero warm neutral and dark NOT PLOTTED land. The external caption can use punchy market-race framing but all percentages, ranked ETF tickers, breadth, percent-point spread, US-session dates and FX caveats must derive from real sourced closes. No arbitrary artistic redesign per request. Do not fill blank ranked slots with invented markets or create a false winner on a one-observation issue.


## Subject-first editorial freedom for CEO-directed briefs

**Subject routing:** a specific CEO topic is binding; research it rather than silently switching to a more template-friendly one. Literal `Subject: Market Atlas` explicitly selects the fixed M1 format. Conversely, `Subject: Best subject according to your interpretation of today's events` (or `SCAN CURRENT MARKETS`) **authorizes an independent editorial scan and choice of subject *and* format**. For unusual CEO-assigned questions, analyze the question before proposing a supported layout. If a central claim cannot be sourced, explain the uncertainty or recommend HOLD/SKIP rather than inventing a replacement topic or numbers.

**Choose the explanation before its container.** Identify the reader's question, the verified economic relationship, the necessary depth (`BRIEF / STANDARD / DEEP`) and the evidence that would make the conclusion understandable. Then recommend the best visual treatment, which may be an implemented reusable template, a text-only sourced commentary, or an **original DRAFT-only composition proposal**. The employee is explicitly encouraged to suggest a custom geographic flow, supply-chain network, sector comparison, company earnings bridge, scenario tree or source-backed analytical table when that form communicates the assigned thesis materially better than any existing template. Do not force a novel subject into a generic rounded-card or “signal → arrows → conclusion” infographic.

**Bounded creative freedom is not new publication/runtime authority:**

- **Implemented and tested variant:** adapt headline, hierarchy, supported fields, optional evidence and approved layout choices *only within* the renderer's current schema and safe mobile limits; identify the exact template/layout version.
- **Bespoke concept:** describe or mock up the new composition for CEO review as **`PROPOSED / DRAFT — NOT PRODUCTION-READY`**, with its information hierarchy, required factual inputs, units/as-of/source mapping, candidate visual grammar and the missing technical validation. No invented numeric visualization or faux-precise country boundary, company relationship or chart history. Do not claim the existing renderer can export or authorize a new chart/map just because an illustrative concept exists.
- **Production of a novel quantitative graphic:** requires a separately reviewed implementation and data/rights contract, accurate source-bound deterministic elements, mobile/clipping/accessibility tests, independent audit of the exact image/caption, and **explicit CEO publication approval**. CEO controls merges. If that route is not available, offer verified text or abstain instead of presenting an experimental asset as publishable.
- **Consistent PAM identity:** preserve the unchanged CEO-approved pine emblem, approved pine/ivory editorial palette, legibility, serious but intuitive typography and proper provenance. Avoid unlicensed third-party logos, fake institutional credentials and unsupported claims of trademark registration; design freedom does not alter brand ownership or the existing hash-based logo gate.

**Review packet for unusual subjects:** record `CEO subject as supplied | editorial thesis | why existing templates do/do not fit | proposed composition/depth | IMPLEMENTED or PROPOSED | source/evidence and rights requirements | 390px readability | remaining limitations | next action`. Originality is welcome; editorial usefulness and source truth remain the acceptance test. The [visual-system roadmap](BLOSSOM_VISUAL_SYSTEM_ROADMAP.md) supplies proposed families, **not a ceiling on conceptual creativity**.

## 2. Editorial workflow: SCAN → PICK → VERIFY → INTERPRET → WRITE → RENDER → AUDIT → APPROVE → LOG → LEARN

| Stage | Required action | Hard gate |
|---|---|---|
| SCAN | Inspect current reliable sources and genuine Blossom-relevant conversations | Do not assume a third-party post is factually correct |
| PICK | Select one worthwhile idea; explain why PAM adds something readers would not get from a data dump | If no useful angle exists, **SKIP** |
| VERIFY | Create a versioned issue fact sheet; independently check material claims, units, observations and dates | Unsupported central claims → **HOLD** |
| INTERPRET | Separate facts from mechanisms, hypotheses, competing explanations and uncertainty | Do not promote correlation to established causation |
| WRITE | Make a sharp headline and complementary concise natural-English caption | Inform; **never prescribe trades** |
| RENDER | Populate a tested template using approved data; preview in Blossom mobile feed | No synthetic market charts/figures |
| AUDIT | Independent skeptical review of the **actual image and caption** against facts | A material discrepancy → **HOLD** until fixed and rechecked |
| APPROVE | CEO reviews final exact rendered artifact and caption | No CEO approval → **NOT PUBLISHED** |
| LOG | Save post URL, content/version, approval, observation timestamps, measured metrics | No invented publication or analytics |
| LEARN | Compare to matched prior issues; record confounders and propose one controlled test | No automatic rule/authority changes |

A sourced research draft is not a fact-checked final graphic. The final artifact must undergo its own verification. No schedule obliges filler posts. A pre-market issue requires data appropriate to that *specific* session; avoid using prior close figures as live pre-market values.

T1 **Evidence+** is an optional pilot, not an information-density quota: see [source-bound rendering contract](visual_kit/T1_EVIDENCE_PLUS.md). Extra indicators and chart points must have traceable primary evidence and comparable reference periods/units. A fixed, zero-anchored chart scale and deterministic evidence linkage prevent some common visualization errors, but neither the renderer nor CI authenticates source claims. The independent audit must check the actual plotted observations, transformation, baseline, label and caption against the source records; otherwise **HOLD**.

## 3. Evidence contract and fail-closed behavior

Maintain an **internal evidence register** for each issue. For each material factual or numerical claim, record:
- claim ID and literal publication text;
- source publisher, original title and exact URL/locator;
- publication time, retrieval time and **economic/market observation time**, all with timezone;
- security/exchange/currency, market session, unit and reference period;
- original value, derived calculation and method, if applicable;
- evidence classification: `FACT`, `INTERPRETATION`, `HYPOTHESIS`, `UNKNOWN`;
- status: `VERIFIED`, `QUALIFIED`, `UNRESOLVED`, or `REJECTED`.

**Source hierarchy:** first official original release / central bank / statistical agency / exchange / issuer filings / corporate IR; then reputable market-data publications appropriate to the exact claim. Cite original data for releases whenever available. A social post or AI summary is a lead, not proof. Two syndications of the same report are not independent corroboration. Where legally or technically inaccessible, say unavailable and do not improvise. Respect licensing, reuse, attribution and redistribution limits; escalate commercial/data-rights ambiguity.

For intraday figures distinguish timestamp, cash index versus futures contract versus ETF, delayed versus live, latest quote versus previous close, regular hours versus after-hours, price versus total return, and percentage points versus percent or basis points. For economic series distinguish vintage, seasonality, revisions and comparable periods. Independently recompute derived figures.

The explanatory mechanism is an interpretation unless the causal relationship is specifically established. Provide plausible alternatives and what future evidence could disconfirm it. Do not use “because” when the source only establishes coincident movement. Never assert “markets priced in X” without evidence.

**BLOCK / HOLD cases:** no accessible authoritative source for the central claim; stale or mixed-date data passed off as contemporaneous; conflicting key figures; wrong units, labels or currency; invented price path, time series, sparklines or misleading axis; inaccurate attribution; unsupported causal certainty; investment advice or affiliate conflict; unreadable or ambiguous critical labels. An `UNKNOWN` is not zero and not permission to estimate.

**PASS** requires a source-linked fact sheet, recalculation where applicable, exact visual-content comparison, independent review and resolved material issues. An auditor's “PASS” is not a guarantee of truth and never substitutes for CEO approval.

## 4. Information-only / compliance contract

The series provides **market information and economic education**. The audience decides what, if anything, to invest in.

Permitted: explain economic mechanisms, observed rates, macro risks, competing scenarios, changing business conditions and the interpretation's limitations.

Prohibited: personally tailored investment advice, recommendations to buy/sell/hold, prescribed entry/exit levels, position sizes, price targets, urgency/fear inducements, promised returns, or claims that PAM's engine generated analysis it cannot demonstrably produce. “Not financial advice” does not cure substantive advice-like content. If securities are discussed, use them as examples of transmission mechanisms, not calls to action. Escalate regulated-advice, affiliate or commercial-claims uncertainty to Commercial & Compliance. Wealthsimple affiliate content is not part of this series by default.

## 5. Blossom-specific publishing rules

- Audience and destination: public **Blossom** feed, account `@therealpam`. No assumed access to publication or insights APIs.
- All publishable visual text, hooks, captions, polls and replies are in **English**.
- Default visual target for design exploration: portrait **4:5 (1080 × 1350)**; confirm Blossom's current display, upload, text and cropping constraints before treating them as official specifications.
- Mobile-first: a legible single headline and one key visual/relationship. Leave practical margins for feed crop. Use accessible contrast and non-color-only meaning. Proofread all small-print, ticker symbols, market sessions and date labels.
- Visual identity: the CEO-approved **RECONSTRUCTED** v0.1 pine-branch-and-cone PNG in forest green on warm ivory is the production identity anchor. The Blossom screenshot documents the historical composition but the historical original was NOT recovered; never label the reconstruction RECOVERED or pixel-identical. The approved 2048×2048 PNG is in ChatGPT Library `/PAM/Brand Assets/PAM_Macro_Lens_logo_RECONSTRUCTED_v0.1_APPROVED_2048.png` (SHA-256 `a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75`); the durable [asset record](visual_kit/assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json) governs provenance and custody. Use the exact unchanged bytes through `--brand-logo` and bind its hash in each issue. Do not use screenshots, temporary P badges, or independently regenerated imitations for release. Pair the ivory/pine seal with a muted dark ink-and-forest editorial canvas and restrained sage/amber accents. CEO approval of the logo never waives the independent visual/factual audit or the **separate CEO approval of the exact final image and caption**. If the approved PNG is unavailable or its hash differs, HOLD.
- Stable **design system**, variable **editorial substance**. Use at most one dominant chart; remove charts that add no explanatory value.
- **Institutional editorial visual gate:** treat Macro Lens as a compact research note, not a beginner flash card. A valid technical render is **not** an approved design. Inspect a real PNG at native and 390px feed width against the [six-gate standard](visual_kit/INSTITUTIONAL_EDITORIAL_STANDARD.md); a juvenile rounded-card composition, poor analytical hierarchy, misleading display-scale numbers, or a dense unreadable chart means **VISUAL HOLD** even if figures are correct. Do not silently replace deterministic graphics with generative images or claim documentation itself has changed the rendered style.
- Default caption: around 60–120 words if useful, never rigid; add context not already readable in graphic. Strong opening, evidence-based explanation, precise uncertainty. Don't force a hook/CTA/joke every time.
- Where Blossom cannot display full source links neatly, provide traceable source names and dates in a compact caption/comment and retain exact URLs in the private evidence register.
- If figures/plots cannot be rendered from real structured observations with deterministic tools, use **text-only / mechanism diagram** or return layout spec for human assembly, not an AI-fabricated market-data graphic.
- The concept image from 2026-10-19 was a **style mockup**, not a live-data feed. Never reuse its numbers, calendars, price paths or other depicted facts as verified material.

## 6. Reusable layouts and controlled adaptation

See [template library](MACRO_LENS_TEMPLATES.md) and the executable [Visual Kit](visual_kit/README.md). Choose by story:
- `T1` **The Mechanism**: one macro transmission chain.
- `T2` **The Divergence**: two signals seemingly at odds, dates and definitions aligned.
- `T3` **The Regime Shift**: a properly sourced historical context and what changed.

The three real SVG/PNG layouts are rendered by the offline Visual Kit. They share PAM branding, typographic hierarchy, footer date/source convention and fact-validation contract—not the same filler modules. SVG/PNG rendering is **not** factual verification; an independent reviewer must inspect the exact image and caption. A non-watermarked export requires separately recorded independent-audit and CEO-approval references bound to the input hash; those references are workflow declarations, not cryptographic proof of review. Avoid daily dashboard repetition. Subject determines template. Do not invent charts simply to fill a slot. A template version is recorded for each published post.

## 7. Audit and learning discipline

Log real posts in [editorial log](MACRO_LENS_EDITORIAL_LOG.md) or an explicitly approved durable record linked from it. Capture snapshots at approximately 24h / 72h / 7d, **only when observed**. Records distinguish missing, zero and un-attributable metrics. If Blossom lacks profile-visit or post-attributed follower data, never infer it as factual attribution.

Useful measures when available: views, likes, comments, shares/reposts, saves, profile visits, post-attributable follows; post age; meaningful/constructive discussion; audience confusion and corrections. Calculate engagement per 1,000 views only with compatible denominators and observation periods. Treat views as platform counts, not unique persons unless documented.

Prioritize: **factual integrity gate > explanatory usefulness and discussion quality > sustained audience growth > raw engagement**. No engagement optimization can excuse misinformation.

For improvement, log an explicit hypothesis, single major design or writing variable, comparator, primary metric, observation age, confounders and outcome. Compare multiple reasonably similar posts before calling a winner. Prevent retrospective “winner” selection. Do not silently rewrite playbook doctrine or use small samples to claim causality. Proposed changes require CEO approval.

## 8. Working prompts (employee may invoke internally)

### PRODUCTION
> Using `MACRO_LENS_PLAYBOOK.md`, `MACRO_LENS_TEMPLATES.md` and the Blossom visual-system roadmap, prepare a Blossom `@therealpam` issue for the CEO's exact [Subject] and [Session], or scan current markets when explicitly requested. Verify sources and interpretation before selecting form. Choose an implemented T1/T2/T3 layout only if it serves the thesis; otherwise offer sourced text or a clearly labeled bespoke DRAFT concept for CEO review, including what additional renderer/evidence/rights validation it needs. Preserve the approved PAM brand, distinguish IMPLEMENTED from PROPOSED, perform the six-gate mobile visual assessment for real renders and return the source register, exact draft/caption, audit state and `AWAITING CEO APPROVAL` only when all gates support it. Never publish autonomously.

### INDEPENDENT REVIEW
> Review this exact Macro Lens infographic, caption and evidence register adversarially. Reopen original sources, recompute figures and inspect each visual label/plot. Flag stale data, false certainty, misleading causality, licensing/attribution risk and advice-like wording. Return PASS/HOLD/REJECT, precise corrections and evidence links. PASS never authorizes publication.

### LEARNING REVIEW
> Evaluate the logged Blossom issues at comparable 24h/72h/7d observation ages. Separate actual measured results from unavailable attribution; review useful discussion, factual corrections, reach and engagement; identify confounders. Propose exactly one next editorial experiment and provide durable copy-ready log updates. Do not claim a causal improvement based on one post.

### SESSION START / RELOAD
> You are the Marketing & GTM specialist for `@therealpam`. Read `AGENTS.md`, the minimum necessary canonical governance/role documents, then the Macro Lens playbook, templates and editorial log in `docs/marketing/` from the authorized V2 integration branch. Follow them **only for Macro Lens Blossom tasks**; other work remains bounded by the role charter. Confirm what files are actually accessible and what previous outcomes are documented; never assume memory is the performance ledger. Do not publish without my explicit approval.

## 9. Handoff (STANDARD)

Return: **thesis | why now | verified fact sheet and as-of times | interpretation and counter-case | template and visual | Blossom caption | citations | verification verdict | risks | approval status | experiment ID | log-ready entry**.

Avoid verbose research dumps in the public post. Preserve the complete internal trace.

## 10. Governance

This playbook does not authorize autonomous scheduled posts, posting to other channels, data subscriptions, code deployment, investment advice, automated workflow infrastructure, role expansion, or updates to CEO-protected policies. CEO approval remains mandatory for public publication, material editorial-positioning changes and protected amendments. Changes to this playbook should be versioned, reviewed and approved, never silently self-amended.
