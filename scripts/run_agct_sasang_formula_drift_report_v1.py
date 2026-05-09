#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build drift report for Sasang formula contribution ranks.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--start-seed", type=int, default=20260505)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--cohort-csv", type=Path, default=root / "tmp" / "bio_real_cohort_merged_with_sidecar_v1.csv")
    ap.add_argument("--genotype-csv", type=Path, default=root / "tmp" / "bio_genotype_long_v1.csv")
    ap.add_argument("--weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_sasang_formula_drift_report_v1_latest.json",
    )
    ns = ap.parse_args()

    contrib_script = root / "scripts" / "run_agct_sasang_formula_contribution_report_v1.py"
    work = root / "tmp" / "agct_formula_drift_v1"
    work.mkdir(parents=True, exist_ok=True)

    runs = []
    segment_component_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    segment_top_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for i in range(ns.runs):
        seed = ns.start_seed + i
        out = work / f"formula_contrib_seed_{seed}.json"
        _run(
            [
                sys.executable,
                str(contrib_script),
                "--cohort-csv",
                str(ns.cohort_csv),
                "--genotype-csv",
                str(ns.genotype_csv),
                "--weights-json",
                str(ns.weights_json),
                "--output-json",
                str(out),
            ]
        )
        d = json.loads(out.read_text(encoding="utf-8"))
        seg = d.get("segment_reports", {})
        run_item = {"seed": seed, "segments": {}}
        for seg_name, seg_obj in seg.items():
            ranking = seg_obj.get("ranking_summary", [])
            run_item["segments"][seg_name] = ranking
            if ranking:
                top_comp = ranking[0]["component"]
                segment_top_counts[seg_name][top_comp] += 1
            for r in ranking:
                comp = r["component"]
                score = float(r["contribution_score"])
                segment_component_scores[seg_name][comp].append(score)
        runs.append(run_item)

    summary_segments = {}
    for seg_name, comp_map in segment_component_scores.items():
        avg_scores = {comp: (sum(vals) / len(vals) if vals else 0.0) for comp, vals in comp_map.items()}
        ranked = sorted(avg_scores.items(), key=lambda kv: kv[1], reverse=True)
        summary_segments[seg_name] = {
            "avg_contribution_scores": avg_scores,
            "top_component_frequency": dict(segment_top_counts.get(seg_name, {})),
            "avg_rank_order": [c for c, _ in ranked],
        }

    payload = {
        "schema": "agct_sasang_formula_drift_report_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "start_seed": ns.start_seed,
            "runs": ns.runs,
            "cohort_csv": str(ns.cohort_csv.resolve()),
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "weights_json": str(ns.weights_json.resolve()),
        },
        "summary": {
            "n_runs": ns.runs,
            "segments": summary_segments,
        },
        "runs": runs,
        "notes": [
            "Seed-based drift report is proxy variability diagnostic only.",
            "Do not interpret as clinical/causal proof.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} runs={ns.runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
