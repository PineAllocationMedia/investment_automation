# PAM color reference — CEO choice, October 27, 2026

The CEO selected the Anthropic “THE $80.7B LOSS ISN’T AN OPERATING LOSS”
image supplied in the conversation as the common editorial color reference.
Reference custody: Library `image.png`, ID `libfile_09e34cf400f4819188b8eddc68fc892d`.
It is a color reference only; its logo pixels and financial figures are not assets
to reuse in subsequent issues.

`pam_theme.py` is the single source of editorial color tokens. BG `#0F2429`
and AMBER `#E7C691` are sampled pixel values. Supporting ivory, sage, dividers
and panel tones are normalized design choices, not recovered vector-source values.
Use its tokens for T1/T2/T3, Evidence+, E1, M2, M4, M1 editorial chrome and
one-off/bespoke SVG compositions. Do not choose a company-specific page background.
If composing outside Python, copy these exact token values and record this theme
version in the external handoff; manually inspect native and 390px proofs.

M1 geography, fixed module positions and positive/negative/zero return scales
remain unchanged. Map ocean/land and data colors are semantic exceptions, not
alternative editorial themes. Other chart colors may express data meaning;
do not turn an amber editorial emphasis into a positive/negative signal.

Theme version is included in the shared input hash, invalidating approvals made
under the earlier hash scheme. A changed theme requires a version increment,
fresh exact-artifact review and separate CEO publication approval. Existing logo
bytes/hash, synthetic warnings, factual gates and release authority are preserved.

Reuse/resource assessment: ADAPT existing standard-library SVG renderers and
their shared imports; no new dependency, service, license or cost. No financial
data or model-rule changes. This implementation is proposed through a PR;
CEO merge remains separate.
