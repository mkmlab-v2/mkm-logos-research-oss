#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Emit exploration brief only when dual-mode signal is strong.
# Keywords: exploration, strong_delta, brief, btrack
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


def main() -> int:
    ap = argparse.ArgumentParser(description="Build exploration brief when dual-mode signal is strong.")
    ap.add_argument("--dual-mode-json", default="docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json")
    ap.add_argument("--extended-sweep-summary-json", default="docs/final/artifacts/external_bible_crossref_extended_sweep_summary_latest.json")
    ap.add_argument("--thresholds-json", default="docs/final/artifacts/btrack_external_baseline_thresholds_v1.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json")
    args = ap.parse_args()

    p_dual = resolve(args.dual_mode_json)
    p_extended = resolve(args.extended_sweep_summary_json)
    p_thresholds = resolve(args.thresholds_json)
    out_path = resolve(args.output_json)
    if not p_dual.is_file():
        raise SystemExit(f"missing dual mode report: {p_dual}")

    dual = json.loads(p_dual.read_text(encoding="utf-8"))
    exp = ((dual.get("exploratory_mode") or {}).get("best_row_by_delta_then_precision") or {})
    sig = str(exp.get("exploration_signal", "none"))
    include = sig == "strong_delta"
    thresholds_doc = json.loads(p_thresholds.read_text(encoding="utf-8")) if p_thresholds.is_file() else {}
    thresholds = thresholds_doc.get("thresholds", {}) if isinstance(thresholds_doc.get("thresholds"), dict) else {}
    delta_prom = float(thresholds.get("delta_random_baseline_min_promising", 0.00017) or 0.00017)
    cov_watch = float(thresholds.get("coverage_overlap_min_watch", 0.000257) or 0.000257)
    extended_best_delta = None
    extended_best_coverage = None
    if p_extended.is_file():
        ext = json.loads(p_extended.read_text(encoding="utf-8"))
        best_expand = ext.get("best_expand", {}) if isinstance(ext.get("best_expand"), dict) else {}
        extended_best_delta = float(best_expand.get("delta_random_baseline", 0.0) or 0.0)
        extended_best_coverage = float(best_expand.get("coverage_overlap", 0.0) or 0.0)

    recommended_action = (
        "enqueue_human_review_and_run_extended_sweep"
        if sig == "strong_delta"
        else "monitor_only"
        if sig == "weak_delta"
        else "no_action"
    )
    # Re-evaluate with extended sweep evidence if present.
    if recommended_action == "enqueue_human_review_and_run_extended_sweep" and extended_best_delta is not None:
        if extended_best_delta < delta_prom or (extended_best_coverage is not None and extended_best_coverage < cov_watch):
            recommended_action = "monitor_only"

    out = {
        "schema": "external_bible_crossref_exploration_signal_brief_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "signal": sig,
        "included": include,
        "snapshot": exp if include else {},
        "next_action_policy": {
            "strong_delta": "enqueue_human_review_and_run_extended_sweep",
            "weak_delta": "monitor_only",
            "none": "no_action",
        },
        "recommended_next_action": recommended_action,
        "re_evaluation": {
            "extended_sweep_summary_ref": str(p_extended) if p_extended.is_file() else None,
            "thresholds_ref": str(p_thresholds) if p_thresholds.is_file() else None,
            "delta_random_baseline_min_promising": delta_prom,
            "coverage_overlap_min_watch": cov_watch,
            "extended_best_expand_delta": extended_best_delta,
            "extended_best_expand_coverage": extended_best_coverage,
        },
        "note": "Brief is emitted only for strong_delta to keep weekly output concise.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
