#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _normalize_row(row: dict[str, float]) -> dict[str, float]:
    s = sum(float(row[a]) for a in AXES)
    if s <= 0:
        return {a: 0.25 for a in AXES}
    return {a: float(row[a]) / s for a in AXES}


def _mutate_weights(base: dict[str, dict[str, float]], rng: random.Random, sigma: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        row = {}
        for a in AXES:
            v = float(base[b][a]) + rng.gauss(0.0, sigma)
            row[a] = max(1e-9, v)
        out[b] = _normalize_row(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Perturbation sweep for AGCT Sasang formula contribution ranking stability.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--trials", type=int, default=20)
    ap.add_argument("--sigma", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_formula_contribution_perturbation_sweep_v1_latest.json",
    )
    ns = ap.parse_args()

    report_script = root / "scripts" / "run_agct_sasang_formula_contribution_report_v1.py"
    work = root / "tmp" / "agct_formula_perturbation_v1"
    work.mkdir(parents=True, exist_ok=True)

    base_w = json.loads(ns.base_weights_json.read_text(encoding="utf-8"))
    rng = random.Random(ns.seed)

    segment_top_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    rows = []

    for i in range(ns.trials):
        w = _mutate_weights(base_w, rng, ns.sigma)
        w_path = work / f"weights_trial_{i:03d}.json"
        r_path = work / f"formula_contrib_trial_{i:03d}.json"
        w_path.write_text(json.dumps(w, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _run(
            [
                sys.executable,
                str(report_script),
                "--weights-json",
                str(w_path),
                "--output-json",
                str(r_path),
            ]
        )
        rep = json.loads(r_path.read_text(encoding="utf-8"))
        seg = rep.get("segment_reports", {})
        trial_row = {"trial": i, "segments": {}}
        for seg_name, seg_obj in seg.items():
            ranking = seg_obj.get("ranking_summary", [])
            trial_row["segments"][seg_name] = ranking
            if ranking:
                segment_top_counts[seg_name][ranking[0]["component"]] += 1
        rows.append(trial_row)

    segment_summary = {}
    for seg_name, top_map in segment_top_counts.items():
        sorted_top = sorted(top_map.items(), key=lambda kv: kv[1], reverse=True)
        segment_summary[seg_name] = {
            "top_component_frequency": dict(top_map),
            "dominant_component": sorted_top[0][0] if sorted_top else None,
            "dominant_component_share": (sorted_top[0][1] / ns.trials) if sorted_top else 0.0,
        }

    payload = {
        "schema": "agct_formula_contribution_perturbation_sweep_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "trials": ns.trials,
            "sigma": ns.sigma,
            "seed": ns.seed,
        },
        "summary": {
            "segment_rank_stability": segment_summary,
        },
        "trials": rows,
        "notes": [
            "Weight perturbation sweep is robustness diagnostics only.",
            "No causal/clinical interpretation.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} trials={ns.trials} sigma={ns.sigma}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
