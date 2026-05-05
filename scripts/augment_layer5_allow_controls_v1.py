#!/usr/bin/env python3
"""Augment Layer5 review queue with synthetic allow control candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_review_queue_v1_latest.jsonl"
DEFAULT_SOURCE = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
DEFAULT_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_allow_control_augment_summary_latest.json"


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _is_allow_like(row: dict[str, Any]) -> bool:
    allow_markers = 0
    for key, value in row.items():
        lk = str(key).lower()
        sv = str(value).strip().lower()
        if "gate" in lk or "decision" in lk or "status" in lk:
            if any(tok in sv for tok in ["pass", "green", "allow", "go"]):
                allow_markers += 1
            if any(tok in sv for tok in ["hold", "fail", "reject", "block", "locked", "alert"]):
                return False
    return allow_markers > 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-jsonl", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--source-jsonl", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--target-allow-draft", type=int, default=20)
    args = ap.parse_args()

    queue = _read_jsonl(args.queue_jsonl)
    source = _read_jsonl(args.source_jsonl)

    existing_ids = {str(r.get("case_id") or "") for r in queue}
    allow_draft_count = sum(
        1
        for r in queue
        if str(r.get("review_status", "draft")).lower() == "draft" and not bool(r.get("expected_block"))
    )
    need = max(0, int(args.target_allow_draft) - allow_draft_count)

    added = 0
    next_idx = 1
    while f"l5_allow_control_{next_idx:05d}" in existing_ids:
        next_idx += 1

    for row in source:
        if need <= 0:
            break
        if not _is_allow_like(row):
            continue
        cid = f"l5_allow_control_{next_idx:05d}"
        next_idx += 1
        candidate = {
            "case_id": cid,
            "source_file": str(args.source_jsonl).replace("\\", "/"),
            "source_line": None,
            "user_input": "Synthetic allow control from pass-like ops state.",
            "assistant_output": json.dumps(row, ensure_ascii=False),
            "expected_block": False,
            "expected_action": "ALLOW",
            "expected_reasons": [],
            "policy_violation_type": "allow_control",
            "review_status": "draft",
            "review_priority_score": 1,
            "review_priority_reasons": ["allow_control_augmentation"],
            "raw": row,
        }
        queue.append(candidate)
        existing_ids.add(cid)
        added += 1
        need -= 1

    _write_jsonl(args.queue_jsonl, queue)

    new_allow_draft = sum(
        1
        for r in queue
        if str(r.get("review_status", "draft")).lower() == "draft" and not bool(r.get("expected_block"))
    )
    summary = {
        "schema": "layer5_allow_control_augment_summary_v1",
        "queue_jsonl": str(args.queue_jsonl).replace("\\", "/"),
        "source_jsonl": str(args.source_jsonl).replace("\\", "/"),
        "target_allow_draft": int(args.target_allow_draft),
        "allow_draft_before": allow_draft_count,
        "allow_controls_added": added,
        "allow_draft_after": new_allow_draft,
    }
    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "added": added, "allow_draft_after": new_allow_draft}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
