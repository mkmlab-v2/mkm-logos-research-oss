#!/usr/bin/env python3
"""Validate mkm_mcp_coordinator_v1 JSON against docs/final/schemas/mkm_mcp_coordinator_v1.schema.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = ROOT / "reports" / "mkm_mcp_coordinator_v1_latest.json"
DEFAULT_SCHEMA = ROOT / "docs" / "final" / "schemas" / "mkm_mcp_coordinator_v1.schema.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    args = ap.parse_args()

    if not args.json.is_file():
        print(f"FAIL: missing json {args.json}")
        return 2
    if not args.schema.is_file():
        print(f"FAIL: missing schema {args.schema}")
        return 2

    doc = json.loads(args.json.read_text(encoding="utf-8"))
    schema = json.loads(args.schema.read_text(encoding="utf-8"))

    try:
        import jsonschema
    except ImportError:
        print("FAIL: jsonschema not installed")
        return 2

    jsonschema.validate(instance=doc, schema=schema)
    print(json.dumps({"ok": True, "json": str(args.json), "schema": str(args.schema)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
