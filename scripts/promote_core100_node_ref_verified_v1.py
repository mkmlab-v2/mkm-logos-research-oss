#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Promote resolved core100 node mappings to verified_manual with audit trail.
# Keywords: core100, promote, verified_manual, mapping
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote resolved core100 mapping rows to verified_manual.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--reviewed-by", default="athena_auto_pass")
    ap.add_argument("--only-status", default="provisional_sample,provisional_autofill_openbible")
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    out_path = resolve(args.output_json)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")

    allowed = {x.strip() for x in str(args.only_status).split(",") if x.strip()}
    data = json.loads(map_path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")

    promoted = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        verse_ref = str(row.get("verse_ref", "")).strip()
        if not verse_ref:
            continue
        status = str(row.get("status", "")).strip()
        if status not in allowed:
            continue
        row["status"] = "verified_manual"
        row["reviewed_by"] = str(args.reviewed_by)
        row["reviewed_at_utc"] = now_utc()
        row["note"] = "Promoted to verified_manual after baseline calibration workflow."
        promoted += 1

    data["promotion_meta"] = {
        "promoted_count": promoted,
        "reviewed_by": str(args.reviewed_by),
        "promoted_at_utc": now_utc(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    print(f"promoted_count={promoted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
