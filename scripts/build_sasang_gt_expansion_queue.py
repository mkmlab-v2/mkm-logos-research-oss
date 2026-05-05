#!/usr/bin/env python3
"""Build GT expansion queue from non-shadow prediction sources.

Output queue is for human labeling workflow (not auto-labeling).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PARENTS = {"TY", "SY", "TE", "SE"}

DEFAULT_GT = ROOT / "data" / "constitution" / "korean_cohort" / "gt_cohort.real.latest.jsonl"
DEFAULT_PRED_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_queue_latest.jsonl"
DEFAULT_REPORT = ART / "sasang_gt_expansion_queue_report_latest.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _is_non_shadow_source(path: Path) -> bool:
    s = path.as_posix().lower()
    blocked = ("synthetic", "proxy", "template", "blind_replay", "shadow")
    return not any(t in s for t in blocked)


def _gt_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    for row in _read_jsonl(path):
        sid = str(row.get("sample_id") or "").strip()
        ep = str(row.get("expected_parent") or "").strip().upper()
        if sid and ep in PARENTS:
            ids.add(sid)
    return ids


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gt", type=Path, default=DEFAULT_GT)
    ap.add_argument("--pred-dir", type=Path, default=DEFAULT_PRED_DIR)
    ap.add_argument("--queue-out", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--target-min-gt", type=int, default=128)
    args = ap.parse_args()

    if not args.gt.is_file():
        print(f"ERROR: missing GT file: {args.gt}")
        return 2
    if not args.pred_dir.is_dir():
        print(f"ERROR: missing prediction directory: {args.pred_dir}")
        return 2

    gt_ids = _gt_ids(args.gt)
    queue: dict[str, dict[str, Any]] = {}
    source_counts: dict[str, int] = {}

    for pred_path in sorted(args.pred_dir.glob("*predictions*.jsonl")):
        if not _is_non_shadow_source(pred_path):
            continue
        accepted = 0
        for row in _read_jsonl(pred_path):
            sid = str(row.get("sample_id") or "").strip()
            parent = str(row.get("predicted_parent") or "").strip().upper()
            conf = row.get("confidence")
            if not sid or sid in gt_ids or parent not in PARENTS:
                continue
            if not isinstance(conf, (int, float)):
                continue
            c = float(conf)
            if c < 0.0 or c > 1.0:
                continue
            current = queue.get(sid)
            candidate = {
                "sample_id": sid,
                "suggested_parent": parent,
                "suggested_confidence": round(c, 6),
                "source_file": pred_path.name,
                "label_status": "PENDING_HUMAN_LABEL",
                "generated_at_utc": _now(),
                "note": "For GT expansion queue only; do not auto-promote or auto-label.",
            }
            if current is None or c > float(current["suggested_confidence"]):
                queue[sid] = candidate
            accepted += 1
        source_counts[pred_path.name] = accepted

    queue_rows = [queue[sid] for sid in sorted(queue)]
    args.queue_out.parent.mkdir(parents=True, exist_ok=True)
    args.queue_out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in queue_rows) + ("\n" if queue_rows else ""),
        encoding="utf-8",
    )

    gt_now = len(gt_ids)
    need = max(0, int(args.target_min_gt) - gt_now)
    report = {
        "schema": "sasang_gt_expansion_queue_report_v1",
        "generated_at_utc": _now(),
        "gt_current_valid_rows": gt_now,
        "target_min_gt_rows": int(args.target_min_gt),
        "gap_rows": need,
        "queue_rows": len(queue_rows),
        "source_hit_counts": source_counts,
        "queue_path": str(args.queue_out.resolve()),
        "track_wall": {
            "human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.queue_out}")
    print(f"WROTE: {args.report_out}")
    print(f"queue_rows={len(queue_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
