#!/usr/bin/env python3
"""Build a draft human-goldset file for genius reasoning benchmark review."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_BENCH = ART / "genius_reasoning_benchmark_report_latest.json"
DEFAULT_OUT = ART / "genius_reasoning_human_goldset_v1.json"


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


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--benchmark-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed-margin", type=float, default=0.08)
    ap.add_argument("--preserve-approved", action="store_true")
    args = ap.parse_args()

    bench = _read_json(args.benchmark_json)
    existing = _read_json(args.output_json)
    task_results = bench.get("task_results") if isinstance(bench.get("task_results"), list) else []
    existing_rows = existing.get("rows") if isinstance(existing.get("rows"), list) else []
    approved_map: dict[str, dict[str, Any]] = {}
    if args.preserve_approved:
        for row in existing_rows:
            if not isinstance(row, dict):
                continue
            task_id = str(row.get("task_id") or "").strip()
            if not task_id:
                continue
            if str(row.get("review_status") or "").strip().lower() == "approved":
                approved_map[task_id] = row

    rows: list[dict[str, Any]] = []
    for row in task_results:
        if not isinstance(row, dict):
            continue
        task_id = str(row.get("task_id") or "").strip()
        if not task_id:
            continue
        approved = approved_map.get(task_id)
        if approved is not None:
            rows.append(approved)
            continue
        score = float(row.get("score") or 0.0)
        suggested = _clip(score - float(args.seed_margin), 0.0, 1.0)
        rows.append(
            {
                "task_id": task_id,
                "expected_score": round(suggested, 4),
                "label_source": "human",
                "review_status": "draft",
                "reviewer": "",
                "reviewed_at_utc": "",
                "note": "Please replace expected_score and set review_status=approved after human review.",
            }
        )

    out = {
        "schema": "genius_reasoning_human_goldset_v1",
        "generated_at_utc": _iso_now(),
        "source_benchmark_json": str(args.benchmark_json).replace("\\", "/"),
        "rows": rows,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "rows": len(rows),
                "preserved_approved_rows": len(approved_map),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
