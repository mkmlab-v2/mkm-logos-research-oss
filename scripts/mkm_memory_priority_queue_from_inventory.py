# -*- coding: utf-8 -*-
"""
Build a read-only priority queue JSON from mkm_memory_inventory CSV (no file mutations).

Default input: <workspace>/reports/memory/mkm_memory_inventory_latest.csv
Output:       <workspace>/reports/memory/mkm_memory_priority_queue_latest.json
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    r = _root()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--csv",
        type=Path,
        default=r / "reports" / "memory" / "mkm_memory_inventory_latest.csv",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=r / "reports" / "memory" / "mkm_memory_priority_queue_latest.json",
    )
    ap.add_argument("--top", type=int, default=200, help="Max rows in priority list (blacklist=yes).")
    args = ap.parse_args()

    if not args.csv.is_file():
        raise SystemExit(f"Missing CSV: {args.csv}")

    rows: List[Dict[str, Any]] = []
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            rows.append(dict(row))

    bl = [x for x in rows if str(x.get("blacklist_inefficient_raw", "")).lower() == "yes"]
    by_tier: Dict[str, int] = {}
    for x in bl:
        t = str(x.get("suggested_tier") or "unknown")
        by_tier[t] = by_tier.get(t, 0) + 1

    def char_len(x: Dict[str, Any]) -> int:
        try:
            return int(x.get("content_char_len") or 0)
        except ValueError:
            return 0

    bl.sort(key=char_len, reverse=True)
    top = bl[: max(0, int(args.top))]

    doc = {
        "schema": "mkm_memory_priority_queue_v1",
        "source_csv": str(args.csv.resolve()),
        "blacklist_inefficient_raw_count": len(bl),
        "blacklist_by_suggested_tier": by_tier,
        "priority_list_max": int(args.top),
        "priority_list": [
            {
                "rel_path": x.get("rel_path"),
                "content_char_len": x.get("content_char_len"),
                "suggested_tier": x.get("suggested_tier"),
                "schema_guess": x.get("schema_guess"),
                "collection": x.get("collection"),
            }
            for x in top
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out.resolve()), "blacklist_count": len(bl)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
