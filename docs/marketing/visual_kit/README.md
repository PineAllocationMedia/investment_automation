# PAM Macro Lens Visual Kit v1.0

**Target:** Blossom @therealpam; native drafting canvas 1080×1350 (4:5). **Status:** proposed repository implementation; no publishing or market-data access. Companion: `docs/marketing/MACRO_LENS_PLAYBOOK.md` and `MACRO_LENS_TEMPLATES.md`.

## What it actually does

Produces consistent branded SVG graphics, plus optional PNG, from manually sourced, reviewed issue JSON. Three real layouts share PAM identity but use different compositions:

- **T1 / The Mechanism:** a sourced signal, three causal or conditional text links, blind spot, tripwire.
- **T2 / The Divergence:** comparable A/B evidence cards, a cautious explanation, blind spot, tripwire.
- **T3 / The Regime Shift:** same series/units in two periods; then versus now, interpretation, tripwire. **Never invents a chart or historical path.**

The program has **no market data feed**, no publishing API, no autonomous recurring job and no factual validation of underlying linked sources. It checks source references, timestamps with timezone, completeness, length, matched periods/units where required, and blocks unresolved records and risky display overflow. A `VERIFIED` field is a **human research assertion, not proof**: an independent fact checker must open sources and recompute material claims. Image-generation tools must not fill these graphics with invented market figures.

## Brand identity — CEO-approved RECONSTRUCTED pine emblem (2026-10-19)

The CEO supplied a screenshot of the existing Blossom `@therealpam` profile emblem: a pine branch and hanging cone in forest green on a warm-ivory circle. The historical source file has **not** been recovered. A new 2048×2048 RGBA PNG was reconstructed from that screenshot; the CEO explicitly approved **v0.1 as PAM Macro Lens's production master on 2026-10-19**. This is **RECONSTRUCTED**, not the recovered or pixel-identical historical original. Do not describe it as a restored original.

Canonical, versioned provenance record: [PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json](assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json).

- **Approved master custody:** ChatGPT Library → `/PAM/Brand Assets/PAM_Macro_Lens_logo_RECONSTRUCTED_v0.1_APPROVED_2048.png`. The binary is **not committed to this repo**; move an authorized copy from Library to the rendering host before production use.
- **Size:** 2048×2048 PNG (RGBA, transparent corners), 1,868,624 bytes. **Exact SHA-256:** `a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75`.
- **Runtime binding:** supply that exact file through `--brand-logo /authorized/local/path/logo.png`, and put the **same SHA-256** in `brand_logo_sha256` in the issue JSON. The renderer rejects an unapproved PNG in release mode, even when an issue author changes their self-declared hash. The image bytes are embedded in the final SVG.
- **Provenance limit:** source avatar screenshot is small and partly occluded; the pine-cone scales and needle strokes differ from the historical design. The reconstructed file is the **approved new master**, not evidence of the old original.
- **Authority limit:** CEO *logo* approval is not CEO *post* approval. Every post still requires independent factual and visual audits of the **exact image + caption** and separate explicit CEO publication approval. No automatic merge, publication, or deployment.

Production handoff: retrieve the asset from its durable Library location, preserve bytes, verify the SHA-256 below and then supply the verified file to the renderer. **Never** use the screenshot, the provisional P badge, a different reconstruction, or an unverified logo as a release fallback. If the approved bytes are unavailable, **HOLD**.

```bash
python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" /authorized/local/path/logo.png
```

The dark forest/ivory editorial design and circular seal remain unchanged; this is a narrow asset provenance + release-policy reconciliation, not a branding redesign.

## T1 Evidence+ (optional controlled pilot)

T1 Classic remains the default and renders exactly as before. An optional T1 `t1_variant: EVIDENCE_PLUS` adds **up to two source-linked supporting indicators** and **at most one zero-anchored monthly bar chart** (three or four consecutive verified observations) while preserving the hero fact, causal stages, blind spot and tripwire. The plotted numeric values are read directly from registered `evidence` records; unregistered raw chart values, non-finite figures, mismatched figure labels, mixed units or missing months halt rendering. The footer includes **all displayed evidence sources**.

See [T1 Evidence+ pilot contract](T1_EVIDENCE_PLUS.md) and [synthetic example](examples/t1_evidence_plus_synthetic.json). If the extra information fails to clarify the story or mobile readability suffers, use Classic. No chart is required. Factual truth still requires external source verification and final-artifact review; the machine validates only structural consistency. Existing logo-hash and CEO release safeguards are unchanged.

## Minimal usage

Run from repository root (Python 3.11+):

```bash
python docs/marketing/visual_kit/render_macro_lens.py \
  docs/marketing/visual_kit/examples/t1_synthetic.json \
  --output /tmp/macro-lens-draft.svg \
  --png /tmp/macro-lens-draft.png
```

SVG: Python standard library only. PNG: PyMuPDF (`fitz`), already pinned in the repository `requirements.txt`. Rendering is offline, self-contained, with no external API call or obligatory paid service. No installation or hardware assumptions beyond normal local Python and the dependency, which may be absent on a given host (in that case omit `--png`). All static assets are code; fonts are system fallback only; no redistributed fonts. PNG path must be writable. SVG can be opened directly in a browser.

Example JSON files contain **synthetic layout-only** tokens, not actual verified economic information. Generated previews have **DRAFT · NOT AUDITED** and a provisional P-brand mark. Never publish them, even if they look finished. The exporter actively rejects a release manifest paired to these fixtures.

## Draft to approved final

1. Research **one meaningful topic**, compile an internal evidence register and independent sources, record full URL, date, precise observation time, currency/units/period, calculations and verification notes. Store the original source outside the image. Create a JSON issue like one of the examples, replacing every synthetic field with real, checked content. Do not copy synthetic metadata into a real draft.
2. Run the renderer. On schema, source, timestamp or layout problems it exits with `HOLD` (exit code 2) instead of fabricating data or silently truncating text. SVG carries a DRAFT watermark. Keep the caption in the editorial handoff (outside the image JSON); independently review caption as well.
3. Give the **exact actual draft image + its final caption + source register** to a skeptical independent reviewer. Correct errors and rerender until the final image is factually consistent and legible at actual Blossom feed size. If the underlying data can't be verified, do not publish.
4. Obtain **explicit CEO approval of that exact final artifact and caption**. The caption is included in the hashed JSON, so any change invalidates prior authorization. A separate audit manifest can be recorded, e.g.:

```json
{
  "input_sha256": "PUT_RENDERER_OUTPUT_INPUT_SHA256_HERE",
  "independent_audit": "PASS",
  "auditor_reference": "external fact-check record link/ID",
  "ceo_approved": true,
  "ceo_approval_reference": "explicit approval of exact asset and caption"
}
```

5. Only then render a non-watermarked final graphic:

```bash
python docs/marketing/visual_kit/render_macro_lens.py approved_issue.json \
  --release-manifest independent_review_and_ceo_approval.json \
  --brand-logo /path/to/official_pam_logo.png \
  --output /tmp/macro-lens-approved.svg \
  --png /tmp/macro-lens-approved.png
```

The input SHA-256 binds the manifest to a specific JSON payload including `brand_logo_sha256`; the CLI separately hashes the PNG bytes and rejects any mismatch. Release is blocked unless the exact CEO-approved reconstructed logo file is supplied and its hash matches the canonical approved hash; any content change invalidates that manifest. **The manifest is not cryptographically authenticated**, does not prove a human actually reviewed it, does not validate remote claims, and should be managed through CEO-controlled procedures. Publication itself is separate and manual unless the CEO explicitly authorizes a supported publishing workflow.

## Fact sheet JSON contract

Required top-level fields:

| Field | Requirement |
|---|---|
| `schema_version` | `"1.0"` |
| `issue_id` | `ML-YYYYMMDD-NN` |
| `template` | `T1`, `T2`, `T3` |
| `account` | `@therealpam` |
| `issue_at` | ISO-8601 timestamp with explicit UTC offset |
| `headline`, `deck`, `blind_spot`, `tripwire` | Concise public text; strict length and layout limits |
| `caption` | Exact proposed English Blossom caption; excluded from SVG layout but INCLUDED in hash-bound review |
| `brand_logo_sha256` | SHA-256 of the exact CEO-approved reconstructed v0.1 PNG listed in `assets/PAM_MACRO_LENS_LOGO_RECONSTRUCTED_v0.1.json`; required with `--brand-logo` and for final release. Omit in synthetic draft examples. |
| `evidence` | 1+ records with claim ID, label, display, unit, period, observation timestamp, retrieval timestamp, original HTTPS source, short title, verification note, classification and review status |
| `fact_ids` | T1: one evidence claim ID; T2/T3: two IDs |
| `mechanism` | T1: exactly three short text links |
| `interpretation` | T2/T3: qualified explanatory statement |

T2 requires equal periods and exact observation timestamps to avoid deceptive juxtapositions. T3 requires a matching metric label/unit and genuinely different periods and observation times. Stronger economic comparability checks still require human review. The tool omits charts rather than invent historical shapes.

## Reusable editorial handoff

```text
Issue and topic:
Why now:
Template choice (T1/T2/T3):
Verified source list + observation times:
Mechanism / alternative explanation:
Draft SVG/PNG + caption:
Independent visual and factual audit verdict:
CEO approval of exact final asset:
Published Blossom URL (only after actual publication):
Observed metrics and editorial experiment ID:
```

## Tests and scope

```bash
cd docs/marketing/visual_kit
python -m unittest discover -s tests -v
```

The tests use only synthetic mock observations. They cover XML escaping, all three layouts, unit/session comparability, missing/unverified evidence, unsafe URLs, oversized text, draft watermark, SHA-linked authorization, logo-asset hash binding and local PNG dimensions. They do **not** establish source truth, macroeconomic accuracy, independent compliance approval, actual Blossom upload behavior or follower conversion.

This is a pure documentation/graphic creation utility. **No product/model changes, investment decisions, data sources, scheduling, account publication privileges or spending authority are introduced.** Keep Marketing & GTM charter and CEO merge/publication gates intact.

### Lightweight reuse & resource assessment

- **REUSE:** Python standard library for file validation, XML escaping, structured deterministic SVG; no new dependency for SVG. Existing pinned PyMuPDF handles optional SVG→PNG conversion. Licensing: Python PSF, PyMuPDF AGPL/commercial dual license; **potential commercial redistribution/use implications must be reviewed by Commercial & Compliance before external distribution of this renderer**, although local internal research use is the proposed pilot. Do not claim the dependency has no legal constraints.
- **ADAPT:** Basic no-cost platform SVG/browser display uses normal browsers. Not relying on third-party web rendering, AI-generated charts, subscription services or data APIs.
- **BUILD (bounded):** small bespoke design layouts, because brand-specific information architecture and strict fail-closed fields are the functionality sought. No external monetary outlay required for an SVG-only pilot. PNG export uses already pinned dependency; compatibility with each actual PAM host has not been established. Chromebook/WSL resource footprints unmeasured and no production host change proposed.