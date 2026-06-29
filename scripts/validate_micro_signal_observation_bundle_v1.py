#!/usr/bin/env python3
"""Validate micro_signal_observation bundle against JSON Schema."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "micro_signal_observation_bundle_v1_latest.json"
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "micro_signal_observation_v1.schema.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_doc(doc: dict[str, Any], validator: Any) -> list[str]:
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    return [f"{list(e.path)}: {e.message}" for e in errors[:24]]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    args = ap.parse_args()
    if not args.input.is_file():
        print(f"missing {args.input}", file=sys.stderr)
        return 2
    if not SCHEMA_PATH.is_file():
        print(f"missing schema {SCHEMA_PATH}", file=sys.stderr)
        return 2

    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print("jsonschema required", file=sys.stderr)
        return 2

    schema = _load(SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    doc = _load(args.input)
    if doc.get("schema") != "micro_signal_observation_bundle_v1":
        print("input must be micro_signal_observation_bundle_v1", file=sys.stderr)
        return 2

    errs = validate_doc(doc, validator)
    if errs:
        print("VALIDATION_FAIL")
        for e in errs:
            print(e)
        return 1

    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    print("VALIDATION_OK")
    print(f"n_observations={summary.get('n_observations')}")
    print(f"domains_present={','.join(summary.get('domains_present') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
