#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Build dual-mode report keeping operating(start) and exploratory(expand) snapshots together.
# Keywords: dual mode, operating, exploratory, range mode, btrack
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def pick_best_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    # B-track exploratory preference: maximize delta_random_baseline, then precision_at_k.
    return max(
        rows,
        key=lambda r: (
            float(r.get("delta_random_baseline", 0.0) or 0.0),
            float(r.get("precision_at_k", 0.0) or 0.0),
        ),
    )


def label_row(row: dict[str, Any], thresholds: dict[str, Any]) -> str:
    cov = float(row.get("coverage_overlap", 0.0) or 0.0)
    dlt = float(row.get("delta_random_baseline", 0.0) or 0.0)
    cov_watch = float(thresholds.get("coverage_overlap_min_watch", 0.0) or 0.0)
    cov_prom = float(thresholds.get("coverage_overlap_min_promising", 0.0) or 0.0)
    delta_watch = float(thresholds.get("delta_random_baseline_min_watch", 0.0) or 0.0)
    delta_prom = float(thresholds.get("delta_random_baseline_min_promising", 0.0) or 0.0)
    if cov >= cov_prom and dlt >= delta_prom:
        return "promising"
    if cov >= cov_watch and dlt >= delta_watch:
        return "watch"
    return "below_watch"


def exploration_signal(row: dict[str, Any], thresholds: dict[str, Any]) -> str:
    dlt = float(row.get("delta_random_baseline", 0.0) or 0.0)
    prc = float(row.get("precision_at_k", 0.0) or 0.0)
    delta_watch = float(thresholds.get("delta_random_baseline_min_watch", 0.0) or 0.0)
    precision_watch = float(thresholds.get("precision_at_k_min_watch", 0.0) or 0.0)
    if dlt > delta_watch and prc >= precision_watch:
        return "strong_delta"
    if dlt > 0.0:
        return "weak_delta"
    return "none"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build dual-mode report for start/expand sweeps.")
    ap.add_argument("--start-sweep-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_latest.json")
    ap.add_argument("--expand-sweep-json", default="docs/final/artifacts/external_bible_crossref_topk_sweep_expand_latest.json")
    ap.add_argument("--thresholds-json", default="docs/final/artifacts/btrack_external_baseline_thresholds_v1.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json")
    args = ap.parse_args()

    p_start = resolve(args.start_sweep_json)
    p_expand = resolve(args.expand_sweep_json)
    p_thresholds = resolve(args.thresholds_json)
    out_path = resolve(args.output_json)
    for p in (p_start, p_expand):
        if not p.is_file():
            raise SystemExit(f"missing sweep json: {p}")

    d_start = json.loads(p_start.read_text(encoding="utf-8"))
    d_expand = json.loads(p_expand.read_text(encoding="utf-8"))
    rows_start = d_start.get("rows", []) if isinstance(d_start.get("rows"), list) else []
    rows_expand = d_expand.get("rows", []) if isinstance(d_expand.get("rows"), list) else []
    d_thresholds = json.loads(p_thresholds.read_text(encoding="utf-8")) if p_thresholds.is_file() else {}
    thresholds = d_thresholds.get("thresholds", {}) if isinstance(d_thresholds.get("thresholds"), dict) else {}

    best_start = pick_best_row(rows_start)
    best_expand = pick_best_row(rows_expand)
    if best_start:
        best_start = {**best_start, "threshold_label": label_row(best_start, thresholds)}
    if best_expand:
        best_expand = {
            **best_expand,
            "threshold_label": label_row(best_expand, thresholds),
            "exploration_signal": exploration_signal(best_expand, thresholds),
        }

    out = {
        "schema": "external_bible_crossref_dual_mode_report_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "operating_mode": {
            "range_mode": "start",
            "sweep_ref": str(p_start),
            "best_row_by_delta_then_precision": best_start,
        },
        "exploratory_mode": {
            "range_mode": "expand",
            "sweep_ref": str(p_expand),
            "best_row_by_delta_then_precision": best_expand,
        },
        "thresholds_ref": str(p_thresholds) if p_thresholds.is_file() else None,
        "note": "Operating mode is fixed for weekly comparability; exploratory mode tracks upside candidates.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
