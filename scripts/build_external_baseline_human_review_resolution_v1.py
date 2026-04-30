#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.3, M:0.7}
# Balance: 88
# Purpose: Build latest human-review resolution snapshot from queue state.
# Keywords: human review, resolution, status
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
    ap = argparse.ArgumentParser(description="Build human review resolution latest artifact.")
    ap.add_argument("--queue-json", default="docs/final/artifacts/external_bible_crossref_human_review_queue_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_human_review_resolution_latest.json")
    args = ap.parse_args()

    p_queue = resolve(args.queue_json)
    out_path = resolve(args.output_json)
    if not p_queue.is_file():
        raise SystemExit(f"missing queue json: {p_queue}")
    q = json.loads(p_queue.read_text(encoding="utf-8"))
    items = q.get("items", []) if isinstance(q.get("items"), list) else []
    open_count = sum(1 for i in items if isinstance(i, dict) and str(i.get("status", "open")) == "open")
    closed_count = sum(1 for i in items if isinstance(i, dict) and str(i.get("status", "")) == "closed")

    out = {
        "schema": "external_bible_crossref_human_review_resolution_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "queue_ref": str(p_queue),
        "queue_status": q.get("status", "closed"),
        "counts": {
            "item_total": len(items),
            "open_count": open_count,
            "closed_count": closed_count,
        },
        "resolution_state": "pending" if open_count > 0 else "completed",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
