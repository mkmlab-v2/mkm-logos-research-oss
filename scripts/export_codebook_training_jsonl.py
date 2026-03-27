#!/usr/bin/env python3
"""Export dual-track master codebook training records to JSONL.

Purpose:
- Keep runtime lookup SSOT immutable
- Export only training track for fine-tuning datasets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = WORKSPACE_ROOT / "docs" / "final" / "master_codebook_dual_track.template.json"
DEFAULT_OUTPUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_latest.jsonl"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise ValueError("input must be a top-level JSON object")
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Export master codebook training records to JSONL")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_INPUT), help="Input dual-track codebook JSON")
    ap.add_argument("--out", dest="output_path", default=str(DEFAULT_OUTPUT), help="Output JSONL path")
    ap.add_argument(
        "--include-failed-quality",
        action="store_true",
        help="Include records with quality_gate_passed=false (default: false)",
    )
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    output_path = _as_abs(args.output_path)
    if not input_path.is_file():
        print(f"❌ input not found: {input_path}")
        return 1

    try:
        payload = _load_json(input_path)
    except Exception as e:
        print(f"❌ input parse failed: {e}")
        return 1

    lookup = payload.get("lookup", {})
    training = payload.get("training", {})
    if not isinstance(lookup, dict) or not isinstance(training, dict):
        print("❌ invalid structure: lookup/training must be objects")
        return 1

    entries = lookup.get("entries", [])
    records = training.get("records", [])
    if not isinstance(entries, list) or not isinstance(records, list):
        print("❌ invalid structure: lookup.entries/training.records must be arrays")
        return 1

    lookup_index: dict[str, dict[str, Any]] = {}
    for row in entries:
        if isinstance(row, dict):
            lid = row.get("lookup_id")
            if isinstance(lid, str) and lid:
                lookup_index[lid] = row

    exported: list[dict[str, Any]] = []
    skipped_quality = 0
    skipped_ref = 0
    for row in records:
        if not isinstance(row, dict):
            continue

        if not args.include_failed_quality and row.get("quality_gate_passed") is not True:
            skipped_quality += 1
            continue

        lref = row.get("lookup_id_ref")
        if not isinstance(lref, str) or lref not in lookup_index:
            skipped_ref += 1
            continue

        lookup_row = lookup_index[lref]
        exported.append(
            {
                "training_id": row.get("training_id"),
                "lookup_id_ref": lref,
                "domain": lookup_row.get("domain"),
                "input_key": lookup_row.get("input_key"),
                "prompt": row.get("prompt"),
                "response": row.get("response"),
                "split": row.get("split"),
                "quality_gate_passed": row.get("quality_gate_passed"),
                "codebook_id": payload.get("codebook_id"),
                "schema_version": payload.get("schema_version"),
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for row in exported:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"✅ exported: {len(exported)}")
    print(f"output: {output_path.resolve()}")
    print(f"skipped_quality: {skipped_quality}")
    print(f"skipped_bad_lookup_ref: {skipped_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
