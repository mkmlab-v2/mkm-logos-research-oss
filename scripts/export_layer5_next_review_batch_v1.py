#!/usr/bin/env python3
"""Export next review batch case_ids from Layer5 review queue."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_review_next_batch_ids_v1.csv"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_review_next_batch_summary_latest.json"


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
    ap.add_argument("--queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--batch-size", type=int, default=40)
    args = ap.parse_args()

    rows = _read_jsonl(args.queue_jsonl)
    approved = {str(r.get("case_id")) for r in rows if str(r.get("review_status", "")).lower() == "approved"}
    draft_rows = [r for r in rows if str(r.get("review_status", "draft")).lower() == "draft"]

    # Queue is already priority-sorted; preserve order.
    picked_ids: list[str] = []
    for row in draft_rows:
        cid = str(row.get("case_id") or "").strip()
        if not cid or cid in approved:
            continue
        picked_ids.append(cid)
        if len(picked_ids) >= max(1, int(args.batch_size)):
            break

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id"])
        for cid in picked_ids:
            writer.writerow([cid])

    summary = {
        "schema": "layer5_review_next_batch_summary_v1",
        "queue_jsonl": str(args.queue_jsonl).replace("\\", "/"),
        "output_csv": str(args.output_csv).replace("\\", "/"),
        "approved_count_in_queue": len(approved),
        "draft_count_in_queue": len(draft_rows),
        "batch_size_requested": int(args.batch_size),
        "batch_size_written": len(picked_ids),
        "first_case_ids": picked_ids[:10],
        "note": "Review these IDs and move approved ones into approval CSV.",
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "written": len(picked_ids), "output_csv": str(args.output_csv)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
