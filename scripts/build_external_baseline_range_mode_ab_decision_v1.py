#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.5}
# Balance: 90
# Purpose: Compare start vs expand range-mode sweeps and recommend baseline mode.
# Keywords: range mode, ab decision, start, expand
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def avg(rows: list[dict], key: str) -> float:
    vals = [float(r.get(key, 0.0) or 0.0) for r in rows]
    return (sum(vals) / len(vals)) if vals else 0.0


def main() -> int:
    ap = argparse.ArgumentParser(description="Build range-mode A/B decision report.")
    ap.add_argument("--start-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_latest.json")
    ap.add_argument("--expand-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_expand_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_range_mode_ab_decision_latest.json")
    args = ap.parse_args()

    p_start = resolve(args.start_json)
    p_expand = resolve(args.expand_json)
    out_path = resolve(args.output_json)
    for p in (p_start, p_expand):
        if not p.is_file():
            raise SystemExit(f"missing sweep json: {p}")

    d_start = json.loads(p_start.read_text(encoding="utf-8"))
    d_expand = json.loads(p_expand.read_text(encoding="utf-8"))
    rs = d_start.get("rows", [])
    re = d_expand.get("rows", [])
    if not isinstance(rs, list) or not isinstance(re, list):
        raise SystemExit("invalid sweep json rows")

    start_summary = {
        "avg_precision_at_k": round(avg(rs, "precision_at_k"), 6),
        "avg_delta_random_baseline": round(avg(rs, "delta_random_baseline"), 6),
        "avg_coverage_overlap": round(avg(rs, "coverage_overlap"), 6),
    }
    expand_summary = {
        "avg_precision_at_k": round(avg(re, "precision_at_k"), 6),
        "avg_delta_random_baseline": round(avg(re, "delta_random_baseline"), 6),
        "avg_coverage_overlap": round(avg(re, "coverage_overlap"), 6),
    }

    # Prefer expand only when it improves average delta and precision together.
    recommend = "start"
    if (
        expand_summary["avg_delta_random_baseline"] >= start_summary["avg_delta_random_baseline"]
        and expand_summary["avg_precision_at_k"] >= start_summary["avg_precision_at_k"]
    ):
        recommend = "expand"

    out = {
        "schema": "external_bible_crossref_range_mode_ab_decision_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "start_summary": start_summary,
        "expand_summary": expand_summary,
        "recommended_mode": recommend,
        "reason": "prefer mode with stronger average precision+delta_random_baseline on B-track benchmark sweeps",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
