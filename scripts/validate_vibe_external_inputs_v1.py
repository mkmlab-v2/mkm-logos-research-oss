#!/usr/bin/env python3
"""Validate Vibe external input JSONL against schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "vibe_external_input_event_v1.schema.json"
INPUT_PATH = ROOT / "docs" / "final" / "artifacts" / "vibe_external_inputs_latest.jsonl"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", type=str, default=str(SCHEMA_PATH))
    parser.add_argument("--input-jsonl", type=str, default=str(INPUT_PATH))
    args = parser.parse_args()

    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    input_path = Path(args.input_jsonl)
    rows = [line.strip() for line in input_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    validator = jsonschema.Draft202012Validator(schema)
    errors = []
    for idx, row in enumerate(rows, start=1):
        obj = json.loads(row)
        for err in validator.iter_errors(obj):
            errors.append(f"line {idx}: {err.message}")

    if errors:
        print("validation: failed")
        for e in errors[:50]:
            print(e)
        return 1

    print("validation: ok")
    print(f"rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

