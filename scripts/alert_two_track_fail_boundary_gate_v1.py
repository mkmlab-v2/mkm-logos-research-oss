#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate operational no-go status from fail boundary.")
    ap.add_argument(
        "--boundary-json",
        default="docs/final/artifacts/two_track_falsification_boundary_report_latest.json",
    )
    ap.add_argument(
        "--survivor-json",
        default="docs/final/artifacts/insight_survivor_candidates_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/two_track_fail_boundary_gate_latest.json",
    )
    args = ap.parse_args()

    bp = resolve(args.boundary_json)
    sp = resolve(args.survivor_json)
    op = resolve(args.output_json)
    if not bp.is_file():
        raise SystemExit(f"missing boundary json: {bp}")
    if not sp.is_file():
        raise SystemExit(f"missing survivor json: {sp}")

    bd = load(bp)
    sv = load(sp)
    summary = bd.get("boundary_summary") if isinstance(bd.get("boundary_summary"), dict) else {}
    max_safe = int(summary.get("max_safe_min_survivor_count", 0) or 0)
    min_break = summary.get("min_break_min_survivor_count")
    survivors = sv.get("survivors") if isinstance(sv.get("survivors"), list) else []
    survivor_count = int(sv.get("survivor_count", len(survivors)) or 0)

    should_trade = survivor_count >= max_safe and max_safe > 0
    rollback = not should_trade
    reasons = []
    if max_safe <= 0:
        reasons.append("missing_safe_boundary")
    if survivor_count < max_safe:
        reasons.append("survivor_count_below_safe_boundary")

    out = {
        "schema": "two_track_fail_boundary_gate_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "boundary_json": str(bp),
            "survivor_json": str(sp),
            "survivor_count": survivor_count,
            "max_safe_min_survivor_count": max_safe,
            "min_break_min_survivor_count": min_break,
        },
        "gate_eval": {
            "should_trade": should_trade,
            "rollback": rollback,
            "reasons": reasons,
        },
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

