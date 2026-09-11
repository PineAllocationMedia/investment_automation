#!/usr/bin/env python3
"""Explicit manual capture of one CIK. User-Agent is required in the environment."""
import argparse
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from economic_facts.sec_acquisition import SecAcquisitionError, acquire_companyfacts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cik", required=True, help="Exactly ten decimal digits")
    parser.add_argument("--archive-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = acquire_companyfacts(cik=args.cik, archive_root=args.archive_root)
    except SecAcquisitionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"success": True, "cik": result.cik, "content_sha256": result.content_sha256,
                      "receipt_id": result.archive_receipt_id, "captured_at": result.captured_at}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
