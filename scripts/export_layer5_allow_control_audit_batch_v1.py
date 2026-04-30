#!/usr/bin/env python3
"""Export allow-control cases for priority human audit."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer5_allow_control_audit_batch_ids_v1.csv"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_allow_control_audit_batch_summary_latest.json"


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
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--batch-size", type=int, default=20)
    ap.add_argument("--include-approved", action="store_true")
    args = ap.parse_args()

    rows = _read_jsonl(args.queue_jsonl)
    candidates = []
    for row in rows:
        cid = str(row.get("case_id") or "")
        if not cid.startswith("l5_allow_control_"):
            continue
        status = str(row.get("review_status", "draft")).lower()
        if not args.include_approved and status != "draft":
            continue
        candidates.append((cid, status))

    picked = candidates[: max(1, int(args.batch_size))]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id", "current_status"])
        for cid, status in picked:
            writer.writerow([cid, status])

    summary = {
        "schema": "layer5_allow_control_audit_batch_summary_v1",
        "queue_jsonl": str(args.queue_jsonl).replace("\\", "/"),
        "output_csv": str(args.output_csv).replace("\\", "/"),
        "batch_size_requested": int(args.batch_size),
        "batch_size_written": len(picked),
        "include_approved": bool(args.include_approved),
        "first_case_ids": [cid for cid, _ in picked[:10]],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "written": len(picked), "output_csv": str(args.output_csv)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
