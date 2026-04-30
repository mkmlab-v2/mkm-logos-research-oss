#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Apply reviewed decisions to core100 node->verse mapping file.
# Keywords: core100, review, decisions, verified_manual
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED_STATUSES = {"verified_manual", "rejected_mapping", "provisional_sample", "provisional_autofill_openbible"}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply core100 mapping review decisions.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--decisions-jsonl", default="docs/final/artifacts/core100_node_ref_review_queue_latest.jsonl")
    ap.add_argument("--output-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    decisions_path = resolve(args.decisions_jsonl)
    out_path = resolve(args.output_json)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")
    if not decisions_path.is_file():
        raise SystemExit(f"missing decisions jsonl: {decisions_path}")

    doc = json.loads(map_path.read_text(encoding="utf-8"))
    rows = doc.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")
    by_node = {str(r.get("node_id", "")).strip(): r for r in rows if isinstance(r, dict)}

    updated = 0
    for line in decisions_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        item = json.loads(s)
        if not isinstance(item, dict):
            continue
        node_id = str(item.get("node_id", "")).strip()
        next_status = str(item.get("current_status", "")).strip()
        if node_id not in by_node or next_status not in ALLOWED_STATUSES:
            continue
        row = by_node[node_id]
        row["status"] = next_status
        if "review_note" in item:
            row["note"] = str(item.get("review_note") or row.get("note", ""))
        if item.get("verse_ref"):
            row["verse_ref"] = str(item["verse_ref"])
        row["reviewed_at_utc"] = str(item.get("reviewed_at_utc") or now_utc())
        row["reviewed_by"] = str(item.get("reviewed_by", "")).strip()
        updated += 1

    doc["review_apply_meta"] = {"applied_at_utc": now_utc(), "updated_row_count": updated}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    print(f"updated_row_count={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
