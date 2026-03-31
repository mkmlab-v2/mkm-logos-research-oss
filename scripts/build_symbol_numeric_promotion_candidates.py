#!/usr/bin/env python3
"""Build promotion candidates from numeric near-miss queue with approval guard."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_INPUT = PILOT / "symbol_numeric_injection_stable_latest.json"
DEFAULT_OUTPUT = PILOT / "numeric_promotion_candidates_latest.json"
REQUIRED_FLAG = "approve_numeric_near_miss=true"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build numeric promotion candidates with approval guard")
    ap.add_argument("--input-json", default=str(DEFAULT_INPUT))
    ap.add_argument("--out-json", default=str(DEFAULT_OUTPUT))
    ap.add_argument(
        "--approval-flag",
        default="",
        help="Must be exactly 'approve_numeric_near_miss=true' to enable promotion export.",
    )
    args = ap.parse_args()

    in_path = _abs(args.input_json)
    out_path = _abs(args.out_json)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2

    payload = json.loads(in_path.read_text(encoding="utf-8"))
    queue = payload.get("p1_manual_review_queue", [])
    if not isinstance(queue, list):
        queue = []

    approved = str(args.approval_flag).strip() == REQUIRED_FLAG
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out_rows: list[dict[str, Any]] = []
    if approved:
        for row in queue:
            if not isinstance(row, dict):
                continue
            out_rows.append(
                {
                    "seed_symbol": row.get("seed_symbol", ""),
                    "candidate": row.get("candidate", ""),
                    "score_tfidf_like": float(row.get("score_tfidf_like", 0.0) or 0.0),
                    "source_mix": row.get("source_mix", {}),
                    "origin_queue_id": row.get("id", ""),
                    "promoted_at_utc": ts,
                }
            )

    result = {
        "schema": "numeric_promotion_candidates_v1",
        "generated_at_utc": ts,
        "input_json": str(in_path),
        "approval": {
            "required_flag": REQUIRED_FLAG,
            "provided_flag": str(args.approval_flag),
            "approved": approved,
        },
        "stats": {
            "manual_review_queue_count": len(queue),
            "promotion_candidate_count": len(out_rows),
        },
        "promotion_candidates": out_rows,
        "note": "Near-miss candidates are exported only when explicit approval flag is provided.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: numeric promotion candidates built")
    print(f"out={out_path}")
    print(f"approved={approved} promoted={len(out_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
