#!/usr/bin/env python3
"""Check the 49 CEO-supplied CVI screenshots against the private archive manifest."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent
manifest = root / "ASSET_MANIFEST.json"
if not manifest.is_file():
    raise SystemExit("MISSING: ASSET_MANIFEST.json — the screenshot import is incomplete.")
entries = json.loads(manifest.read_text(encoding="utf-8"))["entries"]
errors = []
for entry in entries:
    file = root / entry["filename"]
    if not file.is_file():
        errors.append(f"MISSING: {file.name}")
        continue
    data = file.read_bytes()
    if len(data) != entry["size_bytes"]:
        errors.append(f"SIZE MISMATCH: {file.name}")
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        errors.append(f"SHA-256 MISMATCH: {file.name}")
if len(entries) != 49:
    errors.append(f"EXPECTED 49 MANIFEST ENTRIES, found {len(entries)}")
if errors:
    print("\n".join(errors))
    raise SystemExit(1)
print("PASS: 49 original screenshots match the asset manifest.")
