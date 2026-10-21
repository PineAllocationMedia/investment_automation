#!/usr/bin/env python3
"""Materialize exact PAM M1 runtime bytes from a private GitHub repository.

Only requires Python stdlib, an authorized read-only GH_TOKEN/GITHUB_TOKEN and
the existing CEO-approved PNG. Does not retrieve market prices or publish.
Use --source-tree for an already-local, verified repository checkout instead.
"""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

REPO = "PineAllocationMedia/investment_automation"
REF = "model-v2/expected-return-challenger"
KIT = "docs/marketing/visual_kit"
FILES = (
    "m1_etf_daily.py",
    "m1_country_etf_mode.py",
    "render_global_index_map.py",
    "render_macro_lens.py",
    "t1_evidence_plus.py",
    "examples/m1_us_etf_synthetic.json",
    "assets/m1_natural_earth_50m_v5_1_1.json",
)
GEO = "assets/m1_natural_earth_50m_v5_1_1.json"
GEO_BLOB = "9f298a1bac5923c787a8e2aaf937221da04c4a58"
LOGO_SHA256 = "a352aa5dc6b9c5f1a142a36747eb4361a2d22cbc628805ee9a4e28da51ca9c75"
MAX_BYTES = 8 * 1024 * 1024


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def api_get(path, token):
    url = "https://api.github.com/repos/" + REPO + "/" + path
    req = Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PAM-M1-exact-runtime-bootstrap/1",
    })
    try:
        with urlopen(req, timeout=45) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("GitHub response exceeds safe byte limit")
        return json.loads(data)
    except HTTPError as exc:
        raise ValueError("GitHub API HTTP %s for %s (check token/repo access)" %
                         (exc.code, path.split("?")[0])) from exc
    except URLError as exc:
        raise ValueError("GitHub API unreachable: use a network-enabled runner "
                         "or --source-tree with a verified checkout") from exc


def read_blob(token, sha):
    info = api_get("git/blobs/" + sha, token)
    if info.get("encoding") != "base64" or not isinstance(info.get("content"), str):
        raise ValueError("GitHub blob not delivered as base64")
    data = base64.b64decode(info["content"], validate=False)
    if blob_sha(data) != sha:
        raise ValueError("Git blob SHA verification failed: " + sha)
    return data


def read_from_github(token, ref):
    commit = api_get("commits/" + quote(ref, safe=""), token)
    commit_sha = commit.get("sha", "")
    if len(commit_sha) != 40:
        raise ValueError("Cannot pin a Git commit before downloading")
    out = {}
    for name in FILES:
        remote = KIT + "/" + name
        meta = api_get("contents/" + remote + "?ref=" + commit_sha, token)
        sha = meta.get("sha", "")
        if len(sha) != 40 or meta.get("type") != "file":
            raise ValueError("Missing Git blob metadata: " + remote)
        if name == GEO and sha != GEO_BLOB:
            raise ValueError("Canonical 50m geography SHA drift")
        out[name] = (read_blob(token, sha), sha)
    return out, commit_sha


def read_from_checkout(root):
    kit = root / KIT
    out = {}
    for name in FILES:
        path = kit / name
        data = path.read_bytes()
        sha = blob_sha(data)
        if name == GEO and sha != GEO_BLOB:
            raise ValueError("Checkout 50m geography SHA drift")
        out[name] = (data, sha)
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    if len(commit) != 40:
        raise ValueError("Checkout has no pinned Git commit")
    for name, (_data, sha) in out.items():
        tracked = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD:" + KIT + "/" + name],
            capture_output=True, text=True, check=True).stdout.strip()
        if tracked != sha:
            raise ValueError("Source-tree file differs from HEAD: " + name)
    return out, commit


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".pam-m1-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dest", required=True, type=Path,
                   help="Local directory where the exact renderer will run")
    p.add_argument("--brand-logo", required=True, type=Path,
                   help="Exact CEO-approved reconstructed v0.1 PNG, from Library")
    p.add_argument("--ref", default=REF,
                   help="Git commit/ref to pin, default canonical integration branch")
    p.add_argument("--source-tree", type=Path,
                   help="Alternative: existing authenticated Git checkout (no API token needed)")
    args = p.parse_args(argv)
    try:
        logo = args.brand_logo.read_bytes()
        if hashlib.sha256(logo).hexdigest() != LOGO_SHA256:
            raise ValueError("Provided PNG is NOT the exact CEO-approved PAM logo")
        if args.source_tree:
            files, commit = read_from_checkout(args.source_tree.resolve())
            source = "verified_git_checkout"
        else:
            token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
            if not token:
                raise ValueError("Set read-only GH_TOKEN/GITHUB_TOKEN, or pass "
                                 "--source-tree for an existing authenticated checkout")
            files, commit = read_from_github(token, args.ref)
            source = "authenticated_git_blob_api"
        dest = args.dest.resolve()
        record = {}
        for name, (data, sha) in files.items():
            atomic_write(dest / name, data)
            record[name] = {"git_blob_sha1": sha, "sha256": hashlib.sha256(data).hexdigest(),
                            "bytes": len(data)}
        logo_name = "approved_pam_logo.png"
        atomic_write(dest / logo_name, logo)
        record[logo_name] = {"sha256": LOGO_SHA256, "bytes": len(logo)}
        manifest = {
            "schema": "PAM_M1_VERIFIED_RUNTIME_MATERIALIZATION_V1",
            "repository": REPO, "source": source, "commit_sha": commit,
            "geometry_blob_sha1": GEO_BLOB, "files": record,
            "not_factual_or_publication_approval": True,
        }
        atomic_write(dest / "m1_runtime_materialization.json",
                     (json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
        sys.path.insert(0, str(dest))
        from render_global_index_map import load_geometry
        geo = load_geometry(dest / GEO)
        if importlib.util.find_spec("fitz") is None:
            print("PNG prerequisite: install PyMuPDF (python -m pip install PyMuPDF)",
                  file=sys.stderr)
        print(json.dumps({"status": "VERIFIED_M1_RUNTIME_READY", "commit": commit,
                          "geometry_countries": len(geo["features"]),
                          "destination": str(dest),
                          "logo": str(dest / logo_name),
                          "manifest": str(dest / "m1_runtime_materialization.json")}))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            ImportError, KeyError) as exc:
        print("M1 RUNTIME MATERIALIZATION ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
