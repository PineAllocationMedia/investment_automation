"""Read-only, on-demand R1 method handoff from an exact Git-pinned checkout.

Only the existing fixed R1 method manifest may select local repository files.
Git blob checks prove content-byte parity, not actual Project loading, method
approval, licensed source access, factual correctness or trade authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from .method_manifest import DOCUMENT_BLOBS, prepare_method_manifest

MAX_METHOD_BYTES = 200_000
MAX_BUNDLE_DOCUMENT_BYTES = 600_000


def _read_pinned_document(root: Path, path: str, expected_sha: str) -> str:
    """Fail closed on stale, missing, external or non-UTF-8 local method files."""
    if path not in DOCUMENT_BLOBS or DOCUMENT_BLOBS[path] != expected_sha:
        raise ValueError("METHOD_HANDOFF_REFERENCE_NOT_PINNED")
    try:
        candidate = root.joinpath(*path.split("/"))
        resolved = candidate.resolve(strict=True)
        if (not resolved.is_relative_to(root)
                or not resolved.is_file()
                or resolved.stat().st_size > MAX_METHOD_BYTES):
            raise ValueError("METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE")
        contents = resolved.read_bytes()
    except (OSError, RuntimeError) as exc:
        raise ValueError("METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE") from exc
    if len(contents) > MAX_METHOD_BYTES:
        raise ValueError("METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE")
    header = b"blob " + str(len(contents)).encode("ascii") + b"\x00"
    actual_sha = hashlib.sha1(header + contents).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError("METHOD_HANDOFF_LOCAL_BLOB_MISMATCH")
    try:
        return contents.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("METHOD_HANDOFF_METHOD_NOT_UTF8") from exc


def prepare_verified_method_handoff(
    continuation: Mapping[str, Any], *, repository_root: Path | None = None,
) -> dict[str, Any]:
    """Package only the *next* actual IR/PI manual transfer plus byte-checked methods.

    Does not send any packet. The complete output is PRIVATE and operator-carried.
    """
    if (not isinstance(continuation, Mapping)
            or continuation.get("status") != "PRIVATE_MANUAL_CONTINUATION_NOT_SENT"
            or continuation.get("storage") != "NONE"
            or continuation.get("project_invocation") != "NONE"
            or continuation.get("readiness") != "NOT_EVALUATED"):
        raise ValueError("METHOD_HANDOFF_CONTINUATION_INVALID")
    next_handoff = continuation.get("next_handoff")
    if not isinstance(next_handoff, Mapping) or len(next_handoff) != 1:
        raise ValueError("METHOD_HANDOFF_CONTINUATION_INVALID")
    label, packet = next(iter(next_handoff.items()))
    if label not in {"IR_REQUEST", "PI_REQUEST"} or not isinstance(packet, Mapping):
        raise ValueError("METHOD_HANDOFF_CONTINUATION_INVALID")
    if packet.get("packet_type") != label:
        raise ValueError("METHOD_HANDOFF_CONTINUATION_INVALID")
    specialist = "IR" if label == "IR_REQUEST" else "PI"
    design_path = packet.get("strategy_design_reference_not_loaded_or_approved")
    manifest = prepare_method_manifest(specialist, design_path)
    if packet.get("pinned_method_references_not_loaded_or_approved") != manifest:
        raise ValueError("METHOD_HANDOFF_MANIFEST_MISMATCH")

    try:
        root = (Path(repository_root) if repository_root is not None
                else Path(__file__).resolve().parents[1]).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE") from exc
    if not root.is_dir():
        raise ValueError("METHOD_HANDOFF_LOCAL_METHOD_UNAVAILABLE")
    documents = []
    total = 0
    for entry in manifest["documents"]:
        content = _read_pinned_document(root, entry["path"], entry["git_blob_sha"])
        total += len(content.encode("utf-8"))
        if total > MAX_BUNDLE_DOCUMENT_BYTES:
            raise ValueError("METHOD_HANDOFF_BUNDLE_TOO_LARGE")
        documents.append({
            **entry,
            "content": content,
            "local_git_blob_check": "MATCHED_EXPECTED_SHA_ONLY",
        })

    return {
        "status": "PRIVATE_METHOD_HANDOFF_PREPARED_NOT_SENT",
        "continuation_private": continuation,
        "document_contents_private": documents,
        "repository": manifest["repository"],
        "method_reference_commit": manifest["reference_commit"],
        "local_content_integrity": "GIT_BLOBS_MATCH_PINNED_REFERENCE",
        "project_method_load_verification": "NOT_PERFORMED",
        "strategy_policy_approval": "NOT_GRANTED_BY_ASSEMBLER",
        "source_authentication": "NOT_PERFORMED",
        "readiness": "NOT_EVALUATED",
        "storage": "NONE",
        "project_invocation": "NONE",
        "trading_authority": "NONE",
    }
