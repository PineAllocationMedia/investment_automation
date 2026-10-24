# PAM — Competitive Visual Intelligence | Private screenshot archive

**Internal design-reference archive only.** All associated qualitative descriptions and source limitations remain in [the Competitive Visual Intelligence library](../COMPETITIVE_VISUAL_INTELLIGENCE.md).

This directory now contains **62 original PNG screenshots supplied by the CEO** in the PAM Marketing & GTM ChatGPT conversation (through 2026-10-24) and an `ASSET_MANIFEST.json` file associating each PNG with its case ID, ordinal, description, image dimensions, byte size and SHA-256 hash.

Naming: `cvi_batch00_01.png` is the original seed screenshot (CVI-001). `cvi_batch01`, `batch02`, `batch03`, `batch04`, `batch05` and `batch06` hold, respectively, 12, 14, 15, 7, 3 and 10 original images. Images are embedded under their matching case headings in the Markdown library. Batch ordinal is meaningful; do not rename these files.

**Rights and provenance:** These are third-party screenshots retained privately at the CEO's direction for internal analysis. Possession and internal retention **do not establish ownership, republication/redistribution rights, data licenses or permission to imitate proprietary art**. Do not publish this folder via Pages, releases or a public repository without separate rights review. Numerical facts and competitor engagement shown in the screenshots remain unverified. These are not PAM production templates or proof of PAM capabilities.

## Integrity verification

The initial **49 original PNGs** were validated during the PR #227 recovery. **Three new original PNGs** from batch 5 and **ten new original PNGs** from batch 6 are archived with matching original Git object SHA-1 checks and source-file SHA-256 hashes, bringing the private archive to **62 PNGs** across **49 analytical cases**. After each archive update, verify GitHub file paths and manifest records, then run the local validator. After cloning the repository, run `python docs/marketing/competitive_visual_assets/verify_assets.py` to check SHA-256 hashes and sizes against the manifest. Keep the repository private and do not change these images without refreshing the manifest.

## Inspecting batch 6 as an authorized agent

Open `../COMPETITIVE_VISUAL_INTELLIGENCE.md` to view ten **inline original-resolution-linked previews** for cases `CVI-20261023-040` through `-049`. Follow each relative `[PNG](competitive_visual_assets/cvi_batch06_XX.png)` link (relative to the library Markdown) or read the files directly in this private directory to inspect pixel content; the Markdown descriptions alone are not the images. Every file is committed as a real binary Git blob, not a hotlink, text placeholder, or externally hosted image. Run `python docs/marketing/competitive_visual_assets/verify_assets.py` on a checkout; it fails on missing files and checksum mismatches. Grant agents ordinary authorized private-repo read access—archiving a file does not change external agent permissions.
