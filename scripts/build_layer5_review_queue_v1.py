#!/usr/bin/env python3
"""Build prioritized human review queue from Layer-5 incident candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_candidates_v1_latest.jsonl"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_summary_latest.json"

HIGH_RISK_HINTS = {
    "auto_promote",
    "direct_bridge",
    "violation",
    "reject",
    "block",
    "locked",
    "alert",
    "regime",
}


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


def _risk_score(row: dict[str, Any]) -> tuple[int, list[str]]:
    reasons = row.get("expected_reasons")
    reason_list = [str(x).lower() for x in reasons] if isinstance(reasons, list) else []
    score = 0
    hits: list[str] = []
    if bool(row.get("expected_block")):
        score += 3
        hits.append("expected_block=true")
    for token in reason_list:
        if token in HIGH_RISK_HINTS:
            score += 2
            hits.append(f"reason:{token}")
    if "review_status" in row and str(row.get("review_status")).lower() == "draft":
        score += 1
        hits.append("review_status=draft")
    return score, hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--max-items", type=int, default=100)
    args = ap.parse_args()

    rows = _read_jsonl(args.input_jsonl)
    queue: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("review_status", "draft")).lower() != "draft":
            continue
        score, hits = _risk_score(row)
        item = dict(row)
        item["review_priority_score"] = score
        item["review_priority_reasons"] = hits
        queue.append(item)

    queue.sort(key=lambda x: (int(x.get("review_priority_score", 0)), str(x.get("case_id", ""))), reverse=True)
    if len(queue) > args.max_items:
        queue = queue[: args.max_items]

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.output_jsonl.open("w", encoding="utf-8") as fh:
        for item in queue:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = {
        "schema": "layer5_incident_review_queue_summary_v1",
        "input_jsonl": str(args.input_jsonl).replace("\\", "/"),
        "output_jsonl": str(args.output_jsonl).replace("\\", "/"),
        "queue_size": len(queue),
        "max_items": int(args.max_items),
        "top_case_ids": [str(x.get("case_id")) for x in queue[:10]],
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "queue_size": len(queue), "output_jsonl": str(args.output_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
