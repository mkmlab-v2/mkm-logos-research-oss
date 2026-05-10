#!/usr/bin/env python3
"""Validate JSONL rows against lens_music_internal_eval_session_v1 (M4 batch hygiene).

Each non-empty line must be one JSON object satisfying the schema.
Exit 0 iff every non-empty line validates and at least one row exists.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    jsonschema = None
    try:
        import jsonschema as _jsonschema  # type: ignore

        jsonschema = _jsonschema
    except ImportError:
        print("jsonschema required", file=sys.stderr)
        return 3

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--jsonl",
        type=Path,
        required=True,
        help="Path to .jsonl file (UTF-8)",
    )
    args = ap.parse_args()

    schema_path = ROOT / "docs/final/schemas/lens_music_internal_eval_session_v1.schema.json"
    if not schema_path.is_file():
        print(f"missing schema: {schema_path}", file=sys.stderr)
        return 2
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    path = args.jsonl
    if not path.is_file():
        print(f"missing jsonl: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    ok_rows = 0
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {i}: JSON decode error: {e}")
            continue
        try:
            jsonschema.validate(instance=obj, schema=schema)
            ok_rows += 1
        except jsonschema.ValidationError as e:
            errors.append(f"line {i}: schema: {e.message}")

    if ok_rows == 0:
        print("validate_lens_music_internal_eval_jsonl_v1: no valid rows", file=sys.stderr)
        return 1

    if errors:
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "rows_validated": ok_rows, "jsonl": str(path.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
