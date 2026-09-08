#!/usr/bin/env python3
"""Compare preserved V1/V2 on an existing COMPLETE_PIT bundle; never collect data."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pit_comparison.bundle import verify_bundle
from pit_comparison.runner import run_comparison
from pit_comparison.source_export import V2_SHA


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--expected-bundle-hash", required=True)
    parser.add_argument("--store", type=Path)
    parser.add_argument("--v2-revision", default=V2_SHA)
    parser.add_argument("--inspect", action="store_true", help="Validate only; PARTIAL_PIT cannot execute")
    args = parser.parse_args()
    try:
        if args.inspect:
            bundle = verify_bundle(args.bundle, args.expected_bundle_hash)
            print(bundle.manifest["bundle_id"], bundle.manifest["pit_quality"])
        else:
            if args.store is None:
                parser.error("--store is required for execution")
            print(run_comparison(repo=Path(__file__).resolve().parents[1], bundle_root=args.bundle,
                expected_bundle_hash=args.expected_bundle_hash, store=args.store, v2_revision=args.v2_revision))
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
