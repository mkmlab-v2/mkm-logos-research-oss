#!/usr/bin/env python3
"""Prioritize Sasang GT expansion queue for human labeling."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_QUEUE = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_queue_latest.jsonl"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "sasang_gt_expansion_priority_top126_latest.jsonl"
DEFAULT_REPORT = ART / "sasang_gt_expansion_priority_report_latest.json"


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


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _source_weight(src: str) -> float:
    s = src.lower()
    if "btrack_eval_full_mapped" in s:
        return 1.0
    if "encoder_smoke" in s:
        return 0.75
    if "candidate_subset" in s:
        return 0.6
    if "predictions.real" in s:
        return 0.9
    return 0.5


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--top-k", type=int, default=126)
    args = ap.parse_args()

    if not args.queue.is_file():
        print(f"ERROR: missing queue file: {args.queue}")
        return 2

    rows = _read_jsonl(args.queue)
    scored: list[dict[str, Any]] = []
    for r in rows:
        conf = float(r.get("suggested_confidence") or 0.0)
        src = str(r.get("source_file") or "")
        score = (0.8 * conf) + (0.2 * _source_weight(src))
        out = dict(r)
        out["priority_score"] = round(score, 6)
        out["priority_rank_reason"] = "confidence_and_source_weight"
        scored.append(out)

    scored.sort(key=lambda x: float(x.get("priority_score") or 0.0), reverse=True)
    top_k = max(0, int(args.top_k))
    selected = scored[:top_k]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in selected) + ("\n" if selected else ""),
        encoding="utf-8",
    )

    report = {
        "schema": "sasang_gt_expansion_priority_report_v1",
        "generated_at_utc": _now(),
        "queue_path": str(args.queue.resolve()),
        "queue_rows": len(rows),
        "top_k": top_k,
        "selected_rows": len(selected),
        "output_path": str(args.out.resolve()),
        "policy": {
            "human_label_required": True,
            "auto_label_forbidden": True,
            "track_b_to_a_autobind_forbidden": True,
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(f"WROTE: {args.report}")
    print(f"selected_rows={len(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
