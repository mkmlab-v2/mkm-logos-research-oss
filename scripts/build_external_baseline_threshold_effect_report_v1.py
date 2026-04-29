#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.4, M:0.7}
# Balance: 88
# Purpose: Snapshot threshold label distribution and compare with previous run.
# Keywords: threshold effect, label distribution, comparison
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


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build threshold effect report from current comparison snapshot.")
    ap.add_argument("--comparison-json", default="docs/final/artifacts/external_bible_crossref_overlap_comparison_latest.json")
    ap.add_argument("--apply-log-summary-json", default="docs/final/artifacts/external_bible_crossref_threshold_apply_log_summary_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_threshold_effect_report_latest.json")
    args = ap.parse_args()

    p_comp = resolve(args.comparison_json)
    p_log_summary = resolve(args.apply_log_summary_json)
    p_out = resolve(args.output_json)
    current = load_json(p_comp)
    rows = current.get("rows", []) if isinstance(current.get("rows"), list) else []
    previous = load_json(p_out)
    prev_dist = previous.get("label_distribution", {}) if isinstance(previous.get("label_distribution"), dict) else {}
    prev_best = str(previous.get("best_by_coverage_overlap", ""))

    dist = {"promising": 0, "watch": 0, "below_watch": 0}
    for row in rows:
        if not isinstance(row, dict):
            continue
        lbl = str(row.get("threshold_label", "below_watch"))
        if lbl in dist:
            dist[lbl] += 1
    best = str(current.get("best_by_coverage_overlap", ""))
    delta = {
        "promising": int(dist.get("promising", 0)) - int(prev_dist.get("promising", 0) or 0),
        "watch": int(dist.get("watch", 0)) - int(prev_dist.get("watch", 0) or 0),
        "below_watch": int(dist.get("below_watch", 0)) - int(prev_dist.get("below_watch", 0) or 0),
    }
    out = {
        "schema": "external_bible_crossref_threshold_effect_report_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "comparison_ref": str(p_comp) if p_comp.is_file() else None,
        "apply_log_summary_ref": str(p_log_summary) if p_log_summary.is_file() else None,
        "apply_count_total": int(load_json(p_log_summary).get("apply_count_total", 0) or 0),
        "best_by_coverage_overlap": best,
        "best_changed_from_previous": bool(prev_best and best and prev_best != best),
        "label_distribution": dist,
        "label_distribution_delta_vs_previous": delta,
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
