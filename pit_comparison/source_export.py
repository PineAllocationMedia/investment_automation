"""Export only source blobs from exact Git objects; never a repository archive."""
from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

from .bundle import BundleError, canonical, digest, fingerprint, inventory, loads, relative_path

V1_SHA = "c5fc27c82c29c2a6027eccee245098c4a072fdf1"
V2_SHA = "2d7abc5ca23f6cf8225793f10034e8e6bae1d41e"
V1_TREE = "26a69bb0b2185ab141af0763da2d965602c8346b"
V2_TREE = "8489fb82b5c75701ea0c4a229e001e259fa1a2fe"
RULES = "2026-08-23-allocation-room-integrity-v7"
TOP_FILES = {"main.py", "requirements.txt", "requirements.lock", ".python-version"}


def allowed_source(path):
    return path in TOP_FILES or (path.startswith("src/") and path.endswith(".py") and len(path.split("/")) == 2)


def git(repo, *args):
    result = subprocess.run(["git", "--no-pager", "-C", str(repo), *args], check=True,
                            capture_output=True, env={"PATH": "/usr/bin:/bin", "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/nonexistent"})
    return result.stdout


def export_revision(repo: Path, revision: str, destination: Path, *, lineage: str):
    if not re.fullmatch(r"[0-9a-f]{40}", revision) or lineage not in {"V1", "V2"}:
        raise BundleError("Explicit full commit SHA and lineage required")
    if lineage == "V1" and revision != V1_SHA:
        raise BundleError("Preserved V1 revision mismatch")
    commit = git(repo, "rev-parse", revision + "^{commit}").decode().strip()
    tree = git(repo, "rev-parse", revision + "^{tree}").decode().strip()
    blobs = {}
    for entry in git(repo, "ls-tree", "-rz", revision).split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        path = name.decode("utf-8")
        if not allowed_source(path):
            continue
        mode, kind, oid = metadata.decode().split()
        if mode not in {"100644", "100755"} or kind != "blob":
            raise BundleError("Nonregular source object")
        relative_path(path)
        blobs[path] = git(repo, "cat-file", "blob", oid)
    return write_export(destination, commit, tree, lineage, blobs)


def write_export(destination, commit, tree, lineage, blobs):
    """Also used by checked-in code-only test fixtures with verified blob hashes."""
    if not TOP_FILES <= blobs.keys() or any(not allowed_source(p) for p in blobs):
        raise BundleError("Source allowlist/required files mismatch")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for name, payload in sorted(blobs.items()):
        relative_path(name)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        records.append({"path": name, "byte_length": len(payload), "sha256": digest(payload)})
    manifest = {"source_schema_version": "pit-source-v1", "git_commit_sha": commit,
                "git_tree_sha": tree, "model_lineage": lineage, "files": records}
    manifest["source_export_hash"] = fingerprint(manifest)
    (destination / "source_manifest.json").write_bytes(canonical(manifest))
    return manifest


def verify_export(root, expected):
    files = inventory(Path(root))
    manifest = loads(files.pop("source_manifest.json"))
    if manifest != expected or manifest["source_export_hash"] != fingerprint({k: v for k, v in manifest.items() if k != "source_export_hash"}):
        raise BundleError("Source export identity mismatch")
    declared = {r["path"]: r for r in manifest["files"]}
    if set(files) != set(declared) or any(not allowed_source(p) for p in files):
        raise BundleError("Source export file set mismatch")
    for p, raw in files.items():
        if len(raw) != declared[p]["byte_length"] or digest(raw) != declared[p]["sha256"]:
            raise BundleError("Source blob mismatch")
    if manifest["model_lineage"] == "V1" and (manifest["git_commit_sha"], manifest["git_tree_sha"]) != (V1_SHA, V1_TREE):
        raise BundleError("V1 provenance mismatch")
    return manifest


def literal_assignment(root, filename, name):
    tree = ast.parse((Path(root) / filename).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise BundleError(f"Missing static provenance: {name}")
