#!/usr/bin/env python3
"""CEO-approved, opt-in cleanup of EXACTLY issue #275's historical branch manifest.

Nothing happens without --execute --log PATH. gh CLI must be authenticated with
repository rights; no token, password or private portfolio data are stored here.
Never changes main, challenger, three divergent refs or any unlisted branch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import quote

REPO = "PineAllocationMedia/investment_automation"
OWNER = "PineAllocationMedia"
ISSUE = 275
EXPECTED_COUNT = 240
V2 = "model-v2/expected-return-challenger"
KEEP = frozenset({
    "main", V2,
    "codex/connector-mac-docsonly-proof-wo184-20261016",
    "marketing/blossom-profile-scan-20261022",
    "marketing/m1-top3-frontrunners-laggards-v1",
    "pm/fs-r1-m3-funded-cost-reconciliation-20261028",
    "pm/fs-r1-m4-user-requested-case-comparison-20261028",
})
EXPECTED_BASES = frozenset({"main", V2})
ISSUE_LINE = re.compile(
    r"^- \x60([^\x60]+)\x60 \| \x60([0-9a-f]{40})\x60 \| #([0-9]+)"
    r" \| \x60([^\x60]+)\x60$", re.MULTILINE
)
MANIFEST = (Path(__file__).resolve().parents[1] / "docs" / "operations"
            / "GITHUB_BRANCH_HYGIENE_APPROVED_20261028.tsv")


class SafetyAbort(RuntimeError):
    pass


def api(path: str, *, method: str = "GET", allow_404: bool = False):
    cmd = ["gh", "api", "--method", method,
           "-H", "Accept: application/vnd.github+json", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                check=False, timeout=65)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SafetyAbort("GH_CLI_NOT_AVAILABLE_OR_TIMED_OUT") from exc
    if result.returncode:
        msg = result.stderr.strip()[:300]
        if allow_404 and ("HTTP 404" in msg or "404 Not Found" in msg):
            return None
        raise SafetyAbort(f"GITHUB_API_{method}_FAILED: {path}: {msg}")
    if method == "DELETE":
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SafetyAbort(f"INVALID_JSON_RESPONSE: {path}") from exc


def manifest_from_file():
    if not MANIFEST.is_file():
        raise SafetyAbort("APPROVED_MANIFEST_MISSING")
    output = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 4:
            raise SafetyAbort("MANIFEST_ROW_NOT_FOUR_FIELDS")
        name, sha, pr, base = parts
        if (not re.fullmatch(r"[A-Za-z0-9._/-]+", name)
                or not re.fullmatch(r"[0-9a-f]{40}", sha)
                or not pr.isdigit() or base not in EXPECTED_BASES
                or name in KEEP):
            raise SafetyAbort("MANIFEST_ROW_UNSAFE")
        output.append((name, sha, int(pr), base))
    if len(output) != EXPECTED_COUNT or len(set(r[0] for r in output)) != EXPECTED_COUNT:
        raise SafetyAbort("MANIFEST_COUNT_OR_DUPLICATES_UNSAFE")
    return output


def assert_issue_manifest(rows):
    issue = api(f"repos/{REPO}/issues/{ISSUE}")
    if issue.get("number") != ISSUE:
        raise SafetyAbort("ISSUE_ID_MISMATCH")
    actual = [(name, sha, int(pr), base)
              for name, sha, pr, base in ISSUE_LINE.findall(issue.get("body") or "")]
    if actual != rows or len(actual) != EXPECTED_COUNT:
        raise SafetyAbort("ISSUE_MANIFEST_CHANGED_OR_NOT_EQUAL_TO_APPROVED_LIST")


def assert_no_open_prs():
    open_prs = api(f"repos/{REPO}/pulls?state=open&per_page=100")
    if not isinstance(open_prs, list) or open_prs:
        raise SafetyAbort("OPEN_PRS_PRESENT_OR_UNVERIFIABLE")


def branch_info(name):
    # GitHub accepts percent-encoded slash in {branch}; subprocess has no shell.
    return api(f"repos/{REPO}/branches/{quote(name, safe='')}", allow_404=True)


def assert_canonical():
    main = branch_info("main")
    challenger = branch_info(V2)
    if not main or not challenger:
        raise SafetyAbort("CANONICAL_BRANCH_MISSING")
    if main.get("name") != "main" or challenger.get("name") != V2:
        raise SafetyAbort("CANONICAL_BRANCH_IDENTITY_MISMATCH")
    return challenger["commit"]["sha"]


def verify_one(row, v2_sha):
    name, sha, pr_number, merge_target = row
    branch = branch_info(name)
    if not branch:
        raise SafetyAbort(f"MANIFEST_BRANCH_MISSING: {name}")
    if branch.get("name") != name or branch.get("commit", {}).get("sha") != sha:
        raise SafetyAbort(f"BRANCH_HEAD_CHANGED: {name}")
    if branch.get("protected") is not False:
        raise SafetyAbort(f"BRANCH_PROTECTION_NOT_VERIFIED_UNPROTECTED: {name}")
    pr = api(f"repos/{REPO}/pulls/{pr_number}")
    if (pr.get("number") != pr_number or not pr.get("merged")
            or not pr.get("merged_at") or pr.get("base", {}).get("ref") != merge_target
            or pr.get("head", {}).get("sha") != sha):
        raise SafetyAbort(f"MERGED_PR_HEAD_PROOF_FAILED: {name}")
    reachable = api(f"repos/{REPO}/compare/{sha}...{v2_sha}")
    if reachable.get("status") not in {"ahead", "identical"} or reachable.get("behind_by") != 0:
        raise SafetyAbort(f"CANONICAL_REACHABILITY_FAILED: {name}")
    # Keep the original SHA as immutable deletion precondition: re-fetch at deletion time.
    return name, sha


def emit(event, file=None):
    line = json.dumps(event, ensure_ascii=True, sort_keys=True)
    print(line, flush=True)
    if file is not None:
        file.write(line + "\n")
        file.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="Actually delete authorized refs; default is check-only")
    parser.add_argument("--log", type=Path, default=None,
                        help="JSONL event log; required in execute mode")
    parser.add_argument("--start", type=int, default=0,
                        help="Zero-based manifest offset, useful when resuming")
    parser.add_argument("--limit", type=int, default=20,
                        help="Number to process, 1..240; use 240 for full cleanup")
    args = parser.parse_args()
    if (args.start < 0 or args.limit < 1 or args.limit > EXPECTED_COUNT
            or args.start + args.limit > EXPECTED_COUNT):
        parser.error("start/limit outside the approved 240-entry manifest")
    if args.execute and args.log is None:
        parser.error("--execute requires --log for auditable deletion")
    rows = manifest_from_file()
    assert_issue_manifest(rows)
    assert_no_open_prs()
    v2_sha = assert_canonical()
    selected = rows[args.start:args.start + args.limit]
    handle = None
    try:
        if args.execute:
            if args.log.is_dir():
                raise SafetyAbort("LOG_MUST_BE_A_FILE")
            handle = args.log.open("a", encoding="utf-8")
        emit({"event": "START", "issue": ISSUE, "mode": "EXECUTE" if args.execute else "CHECK_ONLY",
              "canonical_v2_head": v2_sha, "start": args.start, "count": len(selected)},
             handle)
        for i, row in enumerate(selected):
            name, sha = verify_one(row, v2_sha)
            emit({"event": "VERIFIED", "index": args.start + i, "branch": name, "sha": sha},
                 handle)
            if args.execute:
                # Recheck no new PR and the current SHA directly before each mutation.
                assert_no_open_prs()
                if assert_canonical() != v2_sha:
                    raise SafetyAbort("CANONICAL_HEAD_CHANGED_DURING_EXECUTION")
                again = branch_info(name)
                if (again is None or again.get("commit", {}).get("sha") != sha
                        or again.get("protected") is not False):
                    raise SafetyAbort(f"BRANCH_CHANGED_BEFORE_DELETE: {name}")
                api(f"repos/{REPO}/git/refs/heads/{name}", method="DELETE")
                if branch_info(name) is not None:
                    raise SafetyAbort(f"DELETION_NOT_CONFIRMED: {name}")
                emit({"event": "DELETED_CONFIRMED", "index": args.start + i,
                      "branch": name, "sha": sha, "merged_pr": row[2]},
                     handle)
            if (i + 1) % 20 == 0:
                emit({"event": "BATCH_COMPLETE", "count_in_run": i + 1}, handle)
                time.sleep(1)
        emit({"event": "COMPLETE", "mode": "EXECUTE" if args.execute else "CHECK_ONLY",
              "count": len(selected)}, handle)
    finally:
        if handle:
            handle.close()


if __name__ == "__main__":
    try:
        main()
    except SafetyAbort as exc:
        print(f"SAFETY_ABORT: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(2)
