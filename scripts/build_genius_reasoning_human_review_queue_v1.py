#!/usr/bin/env python3
"""Build human review queue artifact for genius reasoning goldset."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_GOLDSET = ART / "genius_reasoning_human_goldset_v1.json"
DEFAULT_QUEUE_JSON = ART / "genius_reasoning_human_review_queue_latest.json"
DEFAULT_QUEUE_CSV = ART / "genius_reasoning_human_review_queue_latest.csv"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--goldset-json", type=Path, default=DEFAULT_GOLDSET)
    ap.add_argument("--output-queue-json", type=Path, default=DEFAULT_QUEUE_JSON)
    ap.add_argument("--output-queue-csv", type=Path, default=DEFAULT_QUEUE_CSV)
    args = ap.parse_args()

    goldset = _read_json(args.goldset_json)
    rows = goldset.get("rows") if isinstance(goldset.get("rows"), list) else []
    pending: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("review_status") or "").strip().lower()
        if status in {"approved"}:
            continue
        pending.append(
            {
                "task_id": row.get("task_id"),
                "review_status": row.get("review_status"),
                "label_source": row.get("label_source"),
                "reviewer": row.get("reviewer"),
                "reviewed_at_utc": row.get("reviewed_at_utc"),
                "note": row.get("note"),
            }
        )

    out = {
        "schema": "genius_reasoning_human_review_queue_v1",
        "generated_at_utc": _iso_now(),
        "source_goldset_json": str(args.goldset_json).replace("\\", "/"),
        "goldset_generated_at_utc": goldset.get("generated_at_utc"),
        "counts": {
            "total_rows": len(rows),
            "pending_rows": len(pending),
        },
        "pending_rows": pending,
    }
    args.output_queue_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_queue_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.output_queue_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_queue_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["task_id", "review_status", "label_source", "reviewer", "reviewed_at_utc", "note"],
        )
        writer.writeheader()
        writer.writerows(pending)

    print(
        json.dumps(
            {
                "ok": True,
                "output_queue_json": str(args.output_queue_json).replace("\\", "/"),
                "output_queue_csv": str(args.output_queue_csv).replace("\\", "/"),
                "pending_rows": len(pending),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
