#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Build review queue for core100 node->verse mappings that are not verified_manual.
# Keywords: core100, review, queue, verified_manual
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build core100 mapping review queue.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--output-jsonl", default="docs/final/artifacts/core100_node_ref_review_queue_latest.jsonl")
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    out_path = resolve(args.output_jsonl)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")

    data = json.loads(map_path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")

    queue: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "")).strip()
        if status == "verified_manual":
            continue
        queue.append(
            {
                "node_id": row.get("node_id"),
                "verse_ref": row.get("verse_ref", ""),
                "current_status": status or "unknown",
                "review_action": "set_status",
                "allowed_next_status": ["verified_manual", "rejected_mapping", "provisional_sample", "provisional_autofill_openbible"],
                "review_note": "",
                "reviewed_by": "",
                "reviewed_at_utc": "",
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in queue), encoding="utf-8")
    print(str(out_path))
    print(f"queue_count={len(queue)} generated_at={now_utc()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
