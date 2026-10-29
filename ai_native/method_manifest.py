"""Pinned, repository-verified R1 method references for manual Project transfer.

The SHA values identify Git blobs inspected at the stated canonical base,
NOT what any live ChatGPT Project actually loaded or executed. Updating a
method file requires an explicit reviewed pin refresh; no branch-head trust,
remote fetch, background sync, policy change or source authentication.
"""
from __future__ import annotations

from typing import Any

REPOSITORY = "PineAllocationMedia/investment_automation"
REFERENCE_COMMIT = "690f2f1bc82ef2e2958b202da0e9e359c7440d0d"
ROOT = "docs/ai_native/integrated_build/"
DOCUMENT_BLOBS = {
    "docs/ai_native/integrated_build/research/SOURCE_FUSION_R1.md": "12143e14b655051e82787bc5e44dfef21ef3f5c7",
    "docs/ai_native/integrated_build/research/VALUATION_R1.md": "be82ed5bdc6ca506ebd8f70e3eaa88410a755abc",
    "docs/ai_native/integrated_build/portfolio/OBSERVATION_AND_ROOM_R1.md": "a7d0815dd6f64576077d5e6d2ffe6d93093d3dce",
    "docs/ai_native/integrated_build/portfolio/CONTRIBUTIONS_AND_COSTS_R1.md": "ba38423eb4b91e817c1b1632f5cc73f690fee182",
    "docs/ai_native/integrated_build/portfolio/LIFECYCLE_AND_HANDOFF_R1.md": "232a3d8b8cda8739e398ecc3310e8925bde73bd0",
    "docs/ai_native/integrated_build/research/HIGH_CAGR_METHOD_R1.md": "79de2e5d9f60f96a633a7755fe8c3d84adbdada2",
    "docs/ai_native/integrated_build/research/POLICY_PROPOSAL_BALANCED_R1.md": "27674108ba6cda47059af1fcc4a535c9bf782d3b",
    "docs/ai_native/integrated_build/research/POLICY_PROPOSAL_FAMILY_OFFICE_R1.md": "15b98a3013ffd2cb9aee8e834073bd105b149622",
    "docs/ai_native/integrated_build/research/POLICY_PROPOSAL_RATIONAL_AGGRESSIVE_R1.md": "2778f2fc2a946a19fd861aa011796ef11dc37cdf",
    "docs/ai_native/integrated_build/research/POLICY_PROPOSAL_INTELLIGENT_DIVIDEND_HARVESTER_R1.md": "81ec3f6d512021f9cd030299e9a379ab71a2f9ee",
    "docs/ai_native/integrated_build/research/POLICY_PROPOSAL_MODERN_ADAPTIVE_BROWNE_R1.md": "e992bc00a432d178a82158ee9ca03e3d3699a7c1",
}
IR_COMMON = (
    ROOT + "research/SOURCE_FUSION_R1.md",
    ROOT + "research/VALUATION_R1.md",
)
PI_COMMON = (
    ROOT + "portfolio/OBSERVATION_AND_ROOM_R1.md",
    ROOT + "portfolio/CONTRIBUTIONS_AND_COSTS_R1.md",
    ROOT + "portfolio/LIFECYCLE_AND_HANDOFF_R1.md",
)


def prepare_method_manifest(specialist: str,
                            mode_design_path: str | None) -> dict[str, Any]:
    """Provide immutable-looking *reference IDs*, never a loaded-method claim."""
    if specialist not in {"IR", "PI"}:
        raise ValueError("METHOD_MANIFEST_SPECIALIST_INVALID")
    if mode_design_path is not None and (
            not isinstance(mode_design_path, str)
            or not mode_design_path.startswith(ROOT + "research/")
            or mode_design_path not in DOCUMENT_BLOBS
            or mode_design_path in IR_COMMON):
        raise ValueError("METHOD_MANIFEST_DESIGN_REFERENCE_INVALID")

    files = []
    for path in (IR_COMMON if specialist == "IR" else PI_COMMON):
        files.append({
            "path": path,
            "git_blob_sha": DOCUMENT_BLOBS[path],
            "reference_role": "COMMON_CANDIDATE_METHOD",
            "loading_status": "NOT_VERIFIED_BY_ASSEMBLER",
        })
    if mode_design_path is not None:
        files.append({
            "path": mode_design_path,
            "git_blob_sha": DOCUMENT_BLOBS[mode_design_path],
            "reference_role": (
                "EXISTING_HIGH_CAGR_V2_SCOPE_REFERENCE"
                if mode_design_path.endswith("/HIGH_CAGR_METHOD_R1.md")
                else "UNAPPROVED_R1_STRATEGY_POLICY_PROPOSAL"
            ),
            "loading_status": "NOT_VERIFIED_BY_ASSEMBLER",
        })
    return {
        "status": "PINNED_REPOSITORY_REFERENCES_NOT_PROJECT_LOADING",
        "repository": REPOSITORY,
        "reference_commit": REFERENCE_COMMIT,
        "specialist": specialist,
        "documents": files,
        "source_authentication": "NOT_PERFORMED",
        "project_method_load_verification": "NOT_PERFORMED",
        "strategy_policy_approval": "NOT_GRANTED_BY_MANIFEST",
        "trading_authority": "NONE",
    }
