#!/usr/bin/env python3
"""Build actionable checklist from C validation queue."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"

IN_JSONL = PILOT / "symbol_c_validation_queue_latest.jsonl"
OUT_JSON = PILOT / "symbol_c_validation_checklist_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Build C queue validation checklist")
    ap.add_argument("--in-jsonl", default=str(IN_JSONL))
    ap.add_argument("--out-json", default=str(OUT_JSON))
    ap.add_argument("--top-k", type=int, default=50)
    args = ap.parse_args()

    in_path = _abs(args.in_jsonl)
    out_path = _abs(args.out_json)
    if not in_path.is_file():
        print(f"ERROR: missing file: {in_path}")
        return 2

    rows = list(_iter_jsonl(in_path))
    rows = rows[: args.top_k]
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    tasks: list[dict[str, Any]] = []
    for i, row in enumerate(rows, 1):
        symbol = str(row.get("symbol", "")).strip()
        score = float(row.get("score_tfidf_like", 0.0) or 0.0)
        source_mix = row.get("source_mix", {})
        tasks.append(
            {
                "id": f"cval_{i:03d}",
                "symbol": symbol,
                "priority_rank": i,
                "score_tfidf_like": round(score, 6),
                "source_mix": source_mix if isinstance(source_mix, dict) else {},
                "status": "pending_review",
                "required_checks": [
                    "scholarly_reference_match",
                    "contextual_semantic_fit",
                    "our_theory_alignment_decision",
                ],
            }
        )

    out = {
        "schema": "btrack_symbol_c_validation_checklist_v1",
        "generated_at_utc": ts,
        "input_jsonl": str(in_path),
        "top_k": args.top_k,
        "task_count": len(tasks),
        "tasks": tasks,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol C validation checklist generated")
    print(f"out={out_path}")
    print(f"task_count={len(tasks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
