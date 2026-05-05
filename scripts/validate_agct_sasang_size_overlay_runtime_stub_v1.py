#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.86, L:0.88, K:0.62, M:0.48}
# Balance: 88
# Purpose: Validate AGCT-Sasang runtime stub against schema and invariants.
# Keywords: agct, sasang, runtime, schema, validate
"""Validate AGCT-Sasang runtime stub."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate AGCT-Sasang runtime stub v1.")
    ap.add_argument("--input-json", type=Path, required=True)
    ap.add_argument(
        "--schema-json",
        type=Path,
        default=Path("docs/final/artifacts/schemas/agct_sasang_size_overlay_runtime_stub_v1.schema.json"),
    )
    ns = ap.parse_args()

    doc = _load_json(ns.input_json)
    schema = _load_json(ns.schema_json)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: e.path)
    if errors:
        for e in errors:
            loc = ".".join(str(x) for x in e.path)
            print(f"SCHEMA_FAIL: {loc}: {e.message}", file=sys.stderr)
        return 2

    rt = doc.get("runtime_stub", {})
    mul = rt.get("multipliers", {})
    lo = float(mul.get("low_risk", 1.0))
    ne = float(mul.get("neutral", 1.0))
    hi = float(mul.get("high_risk", 1.0))
    if not (hi <= ne <= lo):
        print(
            f"INVARIANT_FAIL: expected high<=neutral<=low, got high={hi}, neutral={ne}, low={lo}",
            file=sys.stderr,
        )
        return 3

    print(f"OK: {ns.input_json.resolve()} validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
