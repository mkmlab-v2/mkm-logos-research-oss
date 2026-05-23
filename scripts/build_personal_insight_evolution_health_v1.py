#!/usr/bin/env python3
"""Build personal insight evolution health + candidates from JSONL feedback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.personal_insight_evolution_feedback_v1 import (  # noqa: E402
    build_evolution_candidates,
    default_lane_paths,
    summarize_feedback,
    utc_now,
    validate_jsonl_file,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/personal_insight_evolution_health_v1_latest.json"
DEFAULT_CANDIDATES = ROOT / "docs/final/artifacts/personal_insight_evolution_candidates_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agg-dir", type=Path, default=ROOT / "reports/personal_insight_evolution")
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--candidates-out", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    args.agg_dir.mkdir(parents=True, exist_ok=True)
    lane_paths = default_lane_paths(args.agg_dir)
    validation: dict[str, dict[str, int]] = {}
    for lane, path in lane_paths.items():
        ok, bad = validate_jsonl_file(path)
        validation[lane] = {"ok_rows": ok, "bad_rows": bad}
        if args.strict and bad > 0:
            print(f"strict_fail lane={lane} bad_rows={bad}")
            return 1

    summary = summarize_feedback(window_days=args.window_days, base_dir=args.agg_dir)
    candidates = build_evolution_candidates(summary)
    health = {
        "schema": "personal_insight_evolution_health_v1",
        "generated_at_utc": utc_now(),
        "feedback_summary": summary,
        "evolution_candidates": candidates,
        "lane_validation": validation,
        "lane_paths": {k: str(v) for k, v in lane_paths.items()},
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply_mode": "none",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.candidates_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.candidates_out.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"ok": True, "out": str(args.out), "candidates_out": str(args.candidates_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
