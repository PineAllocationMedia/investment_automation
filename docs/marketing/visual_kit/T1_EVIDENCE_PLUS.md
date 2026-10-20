# T1 Evidence+ — controlled pilot v1.1

**Scope:** optional enhanced T1 graphic for Blossom `@therealpam`; **T1 Classic (existing/default) remains unchanged**. No new publishing authority, product data feed, chart extrapolation or automatic market data verification.

**Visual-quality gate:** use the [Institutional Editorial Design Gate](INSTITUTIONAL_EDITORIAL_STANDARD.md) on the actual mobile preview. More indicators do not equal more authority; a crowded Evidence+ panel, oversized card composition or tiny chart labels require **VISUAL HOLD** or fallback to T1 Classic, even if the deterministic schema and source binding pass. No new design has been implemented by this requirement alone.

## When to use

Use Evidence+ only if the contextual evidence demonstrably improves the mechanism. A visually attractive but unnecessary chart should be omitted. For the first pilot, compare the clarity and quality of the evidence-rich draft against T1 Classic; keep an independent factual audit and CEO approval for the exact image/caption.

- **One hero metric**, already required by T1.
- **Zero to two supporting indicators**, each tied to a separately verified `evidence` record with the **same exact reference period and observation time** as the hero. Different units must be displayed, never obscured or implicitly compared.
- **Zero or one compact zero-anchored bar chart**, depicting **three or four consecutive monthly observations of one consistently defined metric**. The chart may reference the hero fact. No unverified line interpolation, arbitrary Y-axis truncation, missing months, mismatched series, inferred values or invented graph elements.
- At least one supporting indicator or eligible chart is required to select Evidence+. Otherwise choose Classic.
- Keep all three mechanism stages, a blind spot and a factual tripwire. Never force extra facts to satisfy a quota.

## Input contract and provenance

Add `"t1_variant": "EVIDENCE_PLUS"` to an otherwise standard T1 issue JSON. Existing inputs without this field default to **Classic**.

An Evidence+ issue may have:

```json
{
  "t1_variant": "EVIDENCE_PLUS",
  "support_fact_ids": ["SUPPORT_1", "SUPPORT_2"],
  "mini_chart": {
    "kind": "bar",
    "title": "Verified monthly series",
    "fact_ids": ["SERIES_JUL", "SERIES_AUG", "SERIES_SEP"]
  }
}
```

The graphic gets **all text and values** from the issue's `evidence` array by ID. For charted records, add `"numeric_value": <number>` (without a `%` sign) **alongside** the corresponding `display` string (e.g., `"+2.3%"`). The renderer rejects disagreement between the plotted numeric value and displayed observation. Do not pass raw values through `mini_chart`: only allowed fields are `kind`, `title`, and `fact_ids`.

Charted records must have:

- `period`: `YYYY-MM`, consecutive and strictly ascending, **three or four months**.
- Identical `label` and `unit` for each point; use a unit that includes transformation and seasonality where relevant (e.g. `% m/m, SA`, `% y/y, NSA`).
- Authored source URL, reference period, observed timestamp, retrieved timestamp and genuine external verification note on **each** evidence row.
- A finite number `numeric_value` matching `display` precisely (allowed precision 0.0005), not NaN, infinity or Boolean.
- Scale anchored at zero, with literal numerical point labels and visible period labels. Never suggest continuity between months using invented paths.

The **renderer verifies structure only**, not the truth or data rights of outside source content. Research must check and record original BLS, Fed, statistical agency, issuer or other first-party observations and publication release dates. The final SVG/PNG **and** English Blossom caption require adversarial source review. If the result looks compressed on mobile, omit the chart/supporting indicator or use Classic. A chart must never hide qualifiers through visual placement.

Use `examples/t1_evidence_plus_synthetic.json` **only for testing**. It uses `example.org`, synthetic numbers and a DRAFT watermark, and is expressly ineligible for release under the existing policy. No example values constitute current market observations.

## Usage

```bash
python docs/marketing/visual_kit/render_macro_lens.py \
  docs/marketing/visual_kit/examples/t1_evidence_plus_synthetic.json \
  --output /tmp/evidence-plus-draft.svg \
  --png /tmp/evidence-plus-draft.png
```

Run the existing Visual Kit suite plus the new Evidence+ tests:

```bash
cd docs/marketing/visual_kit
python -m unittest discover -s tests -v
```

A final release still requires the unchanged exact approved logo SHA-256, an external evidence register and audit, SHA-bound caption+image approval manifest, and explicit separate CEO publication approval. PR merge does not approve a post.