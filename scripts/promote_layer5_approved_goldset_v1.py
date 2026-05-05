#!/usr/bin/env python3
"""Promote approved Layer-5 review cases into benchmark goldset."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_summary_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--sample-size", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--allow-fallback-draft", action="store_true")
    args = ap.parse_args()

    rows = _read_jsonl(args.input_jsonl)
    approved = [r for r in rows if str(r.get("review_status", "")).lower() == "approved"]
    source = approved
    source_mode = "approved_only"

    if not source and args.allow_fallback_draft:
        source = [r for r in rows if str(r.get("review_status", "draft")).lower() == "draft"]
        source_mode = "fallback_draft"

    rng = random.Random(args.seed)
    if len(source) > args.sample_size:
        picked = rng.sample(source, args.sample_size)
    else:
        picked = list(source)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for row in picked:
            out = dict(row)
            out["goldset_source_mode"] = source_mode
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")

    summary = {
        "schema": "layer5_incident_goldset_human_summary_v1",
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "source_mode": source_mode,
        "approved_count": len(approved),
        "picked_count": len(picked),
        "sample_size_requested": int(args.sample_size),
        "seed": int(args.seed),
        "note": "Production benchmark should use approved_only mode.",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "picked": len(picked), "source_mode": source_mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
