#!/usr/bin/env python3
"""Export a diversified review batch from Layer5 review queue."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer5_review_diversified_batch_ids_v1.csv"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_review_diversified_batch_summary_latest.json"


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


def _is_boundary_case(row: dict[str, Any]) -> bool:
    reasons = row.get("expected_reasons")
    if not isinstance(reasons, list):
        return False
    reason_set = {str(x).lower() for x in reasons}
    boundary_tokens = {"regime", "track b", "track a", "direct_bridge", "auto_promote"}
    return any(token in reason_set for token in boundary_tokens)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--output-csv", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--batch-size", type=int, default=40)
    ap.add_argument("--min-allow", type=int, default=10)
    ap.add_argument("--min-block", type=int, default=20)
    ap.add_argument("--min-boundary", type=int, default=10)
    args = ap.parse_args()

    rows = _read_jsonl(args.queue_jsonl)
    draft = [r for r in rows if str(r.get("review_status", "draft")).lower() == "draft"]

    allow_pool = [r for r in draft if not bool(r.get("expected_block"))]
    block_pool = [r for r in draft if bool(r.get("expected_block"))]
    boundary_pool = [r for r in draft if _is_boundary_case(r)]

    picked: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take_from(pool: list[dict[str, Any]], n: int) -> int:
        count = 0
        for row in pool:
            cid = str(row.get("case_id") or "").strip()
            if not cid or cid in seen:
                continue
            picked.append(row)
            seen.add(cid)
            count += 1
            if count >= n:
                break
        return count

    took_allow = take_from(allow_pool, max(0, args.min_allow))
    took_block = take_from(block_pool, max(0, args.min_block))
    took_boundary = take_from(boundary_pool, max(0, args.min_boundary))

    # Fill remaining from draft queue in order.
    remaining = max(0, int(args.batch_size) - len(picked))
    if remaining > 0:
        take_from(draft, remaining)

    picked = picked[: max(1, int(args.batch_size))]

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["case_id", "expected_block", "is_boundary"])
        for row in picked:
            cid = str(row.get("case_id") or "")
            writer.writerow([cid, "true" if bool(row.get("expected_block")) else "false", "true" if _is_boundary_case(row) else "false"])

    summary = {
        "schema": "layer5_review_diversified_batch_summary_v1",
        "queue_jsonl": str(args.queue_jsonl).replace("\\", "/"),
        "output_csv": str(args.output_csv).replace("\\", "/"),
        "batch_size_requested": int(args.batch_size),
        "batch_size_written": len(picked),
        "requested_minima": {
            "min_allow": int(args.min_allow),
            "min_block": int(args.min_block),
            "min_boundary": int(args.min_boundary),
        },
        "taken_minima": {
            "allow": took_allow,
            "block": took_block,
            "boundary": took_boundary,
        },
        "actual_mix": {
            "allow": sum(1 for r in picked if not bool(r.get("expected_block"))),
            "block": sum(1 for r in picked if bool(r.get("expected_block"))),
            "boundary": sum(1 for r in picked if _is_boundary_case(r)),
        },
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "written": len(picked), "output_csv": str(args.output_csv)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
