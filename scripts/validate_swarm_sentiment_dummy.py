#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate docs/final dummy_swarm_score.jsonl lines against SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json (Draft 7). B-track wiring check only."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft7Validator
except ImportError as e:
    print("jsonschema required: pip install jsonschema", file=sys.stderr)
    raise SystemExit(2) from e


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Validate swarm sentiment JSONL against draft-07 schema.")
    p.add_argument(
        "--schema",
        type=Path,
        default=root / "docs" / "final" / "SWARM_SENTIMENT_METRIC_SCHEMA_DRAFT.json",
        help="Path to JSON Schema file",
    )
    p.add_argument(
        "--jsonl",
        type=Path,
        default=root / "docs" / "final" / "dummy_swarm_score.jsonl",
        help="Path to JSONL (one JSON object per line)",
    )
    args = p.parse_args()

    if not args.schema.is_file():
        print(f"Missing schema: {args.schema}", file=sys.stderr)
        return 1
    if not args.jsonl.is_file():
        print(f"Missing jsonl: {args.jsonl}", file=sys.stderr)
        return 1

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)

    bad = 0
    for i, line in enumerate(args.jsonl.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        inst = json.loads(line)
        errs = sorted(validator.iter_errors(inst), key=lambda e: e.path)
        if errs:
            bad += 1
            print(f"Line {i}: validation failed", file=sys.stderr)
            for e in errs:
                print(f"  {e.message} at {list(e.path)}", file=sys.stderr)
    if bad:
        return 1
    print("OK: all JSONL lines validate against schema.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
