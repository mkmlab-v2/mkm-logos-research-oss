#!/usr/bin/env python3
"""Validate weather_ground_truth_row_v1 JSONL (schema, dup keys, binary/precip consistency)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/weather_ground_truth_row_v1.schema.json"


def validate_jsonl(path: Path, *, threshold_mm: float = 0.1) -> tuple[list[str], int]:
    errors: list[str] = []
    seen: set[str] = set()
    count = 0
    validator = None
    if SCHEMA_PATH.is_file():
        try:
            from jsonschema import Draft202012Validator

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema)
        except ImportError:
            errors.append("jsonschema not installed; structural checks only")

    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: invalid json: {exc}")
            continue
        if row.get("schema") != "weather_ground_truth_row_v1":
            errors.append(f"line {line_no}: schema must be weather_ground_truth_row_v1")
        if validator is not None:
            for err in validator.iter_errors(row):
                errors.append(f"line {line_no}: schema:{err.message}")
        key = f"{row.get('station_or_region_id')}|{row.get('observation_date_local')}"
        if key in seen:
            errors.append(f"line {line_no}: duplicate key {key}")
        seen.add(key)
        precip = row.get("precip_mm_day")
        binary = row.get("precip_binary_gt_0_1mm")
        if isinstance(precip, (int, float)) and isinstance(binary, bool):
            expected = float(precip) > threshold_mm
            if binary != expected:
                errors.append(
                    f"line {line_no}: precip_binary_gt_0_1mm={binary} inconsistent with precip_mm_day={precip} threshold={threshold_mm}"
                )
    return errors, count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--threshold-mm", type=float, default=0.1)
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing input: {ns.input}", file=sys.stderr)
        return 2
    errors, count = validate_jsonl(ns.input, threshold_mm=ns.threshold_mm)
    if errors:
        for err in errors[:50]:
            print(err, file=sys.stderr)
        if len(errors) > 50:
            print(f"... and {len(errors) - 50} more", file=sys.stderr)
        return 1
    print(f"OK: {ns.input} rows={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
