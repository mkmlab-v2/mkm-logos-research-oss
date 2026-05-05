#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Build threshold tuning proposal from current comparison report.
# Keywords: threshold, tuning, proposal, baseline
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
    ap = argparse.ArgumentParser(description="Build tuning proposal for external baseline thresholds.")
    ap.add_argument("--comparison-json", default="docs/final/artifacts/external_bible_crossref_overlap_comparison_latest.json")
    ap.add_argument("--thresholds-json", default="docs/final/artifacts/btrack_external_baseline_thresholds_v1.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/btrack_external_baseline_threshold_tuning_proposal_latest.json")
    args = ap.parse_args()

    p_comp = resolve(args.comparison_json)
    p_thr = resolve(args.thresholds_json)
    out_path = resolve(args.output_json)
    if not p_comp.is_file() or not p_thr.is_file():
        raise SystemExit("missing input for threshold tuning proposal")

    comp = json.loads(p_comp.read_text(encoding="utf-8"))
    thr = json.loads(p_thr.read_text(encoding="utf-8"))
    rows = comp.get("rows", []) if isinstance(comp.get("rows"), list) else []
    thresholds = thr.get("thresholds", {}) if isinstance(thr.get("thresholds"), dict) else {}

    core100 = next((r for r in rows if isinstance(r, dict) and r.get("label") == "core100_mapped"), {})
    fullcanon = next((r for r in rows if isinstance(r, dict) and r.get("label") == "fullcanon"), {})

    cov_watch_current = float(thresholds.get("coverage_overlap_min_watch", 0.001) or 0.001)
    delta_watch_current = float(thresholds.get("delta_random_baseline_min_watch", 0.00005) or 0.00005)
    core_cov = float(core100.get("coverage_overlap", 0.0) or 0.0)
    core_delta = float(core100.get("delta_random_baseline", 0.0) or 0.0)
    full_cov = float(fullcanon.get("coverage_overlap", 0.0) or 0.0)

    proposal = {
        "coverage_overlap_min_watch": round(max(core_cov * 0.9, 0.0001), 6),
        "coverage_overlap_min_promising": round(max(full_cov * 0.9, cov_watch_current), 6),
        "delta_random_baseline_min_watch": round(max(core_delta, 0.0), 6),
        "delta_random_baseline_min_promising": round(max(float(fullcanon.get("delta_random_baseline", 0.0) or 0.0), delta_watch_current), 6),
    }

    out = {
        "schema": "btrack_external_baseline_threshold_tuning_proposal_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "current_thresholds": thresholds,
        "core100_snapshot": core100,
        "fullcanon_snapshot": fullcanon,
        "proposed_thresholds": proposal,
        "note": "Proposal is advisory. Apply only with human review because baseline is manual_editorial_heuristic.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
