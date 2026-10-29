"""Read-only local R1 method-pin integrity preflight.

From an authorized repo checkout:
    python -B -m scripts.r1_method_preflight

No CEO/private inputs, remote queries, file writes, subscriptions, Project
invocations, trading, or method/policy approval. Report paths are fixed.
"""
from __future__ import annotations

import json
from typing import TextIO
import sys

from ai_native.method_handoff_bundle import inspect_local_method_pins


def main(*, outstream: TextIO | None = None) -> int:
    out = outstream if outstream is not None else sys.stdout
    result = inspect_local_method_pins()
    out.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return 0 if result["status"] == "LOCAL_PINNED_METHOD_FILES_MATCH" else 3


if __name__ == "__main__":
    raise SystemExit(main())
