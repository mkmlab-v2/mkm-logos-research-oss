#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Consolidate external baseline overlap reports into a single comparison summary.
# Keywords: comparison, overlap, baseline, report, btrack
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


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"report must be object: {path}")
    return data


def extract_row(label: str, doc: dict[str, Any]) -> dict[str, Any]:
    counts = doc.get("counts", {}) if isinstance(doc.get("counts"), dict) else {}
    metrics = doc.get("metrics", {}) if isinstance(doc.get("metrics"), dict) else {}
    return {
        "label": label,
        "coverage_overlap": float(metrics.get("coverage_overlap", 0.0) or 0.0),
        "precision_at_k": float(metrics.get("precision_at_k", 0.0) or 0.0),
        "delta_random_baseline": float(metrics.get("delta_random_baseline", 0.0) or 0.0),
        "overlap_pair_count": int(counts.get("overlap_pair_count", 0) or 0),
        "internal_unique_pairs_normalized": int(counts.get("internal_unique_pairs_normalized", 0) or 0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build comparison summary for external baseline overlap reports.")
    ap.add_argument("--report-global", default="docs/final/artifacts/external_bible_crossref_openbible_overlap_report_latest.json")
    ap.add_argument("--report-core100", default="docs/final/artifacts/external_bible_crossref_openbible_overlap_report_core100_mapped_latest.json")
    ap.add_argument("--report-fullcanon", default="docs/final/artifacts/external_bible_crossref_openbible_overlap_report_fullcanon_latest.json")
    ap.add_argument("--thresholds-json", default="docs/final/artifacts/btrack_external_baseline_thresholds_v1.json")
    ap.add_argument("--quality-gate-json", default="docs/final/artifacts/core100_node_ref_map_quality_gate_latest.json")
    ap.add_argument("--dual-mode-json", default="docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json")
    ap.add_argument("--exploration-brief-json", default="docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_overlap_comparison_latest.json")
    args = ap.parse_args()

    p_global = resolve(args.report_global)
    p_core100 = resolve(args.report_core100)
    p_fullcanon = resolve(args.report_fullcanon)
    p_thresholds = resolve(args.thresholds_json)
    p_quality_gate = resolve(args.quality_gate_json)
    p_dual_mode = resolve(args.dual_mode_json)
    p_exploration_brief = resolve(args.exploration_brief_json)
    for p in (p_global, p_core100, p_fullcanon):
        if not p.is_file():
            raise SystemExit(f"missing report: {p}")

    d_global = load(p_global)
    d_core100 = load(p_core100)
    d_fullcanon = load(p_fullcanon)
    thresholds_doc = load(p_thresholds) if p_thresholds.is_file() else {}
    thresholds = thresholds_doc.get("thresholds", {}) if isinstance(thresholds_doc.get("thresholds"), dict) else {}

    rows = [
        extract_row("global_latest", d_global),
        extract_row("core100_mapped", d_core100),
        extract_row("fullcanon", d_fullcanon),
    ]
    cov_watch = float(thresholds.get("coverage_overlap_min_watch", 0.0) or 0.0)
    cov_prom = float(thresholds.get("coverage_overlap_min_promising", 0.0) or 0.0)
    delta_watch = float(thresholds.get("delta_random_baseline_min_watch", 0.0) or 0.0)
    delta_prom = float(thresholds.get("delta_random_baseline_min_promising", 0.0) or 0.0)
    for row in rows:
        cov = float(row["coverage_overlap"])
        dlt = float(row["delta_random_baseline"])
        if cov >= cov_prom and dlt >= delta_prom:
            row["threshold_label"] = "promising"
        elif cov >= cov_watch and dlt >= delta_watch:
            row["threshold_label"] = "watch"
        else:
            row["threshold_label"] = "below_watch"
    best = max(rows, key=lambda r: r["coverage_overlap"])
    out = {
        "schema": "external_bible_crossref_overlap_comparison_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "rows": rows,
        "thresholds_ref": str(p_thresholds) if p_thresholds.is_file() else None,
        "quality_gate_ref": str(p_quality_gate) if p_quality_gate.is_file() else None,
        "operating_mode_ref": str(p_dual_mode) if p_dual_mode.is_file() else None,
        "exploratory_mode_ref": str(p_exploration_brief) if p_exploration_brief.is_file() else None,
        "best_by_coverage_overlap": best["label"],
        "notes": [
            "Comparison is calibration-only; external baseline is manual editorial linkage.",
            "Do not use these scores as A-track production evidence.",
        ],
    }
    output_path = resolve(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
