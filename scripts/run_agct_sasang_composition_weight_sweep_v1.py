#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.91, L:0.85, K:0.67, M:0.44}
# Balance: 89
# Purpose: Sweep AGCT->Sasang composition projection weight candidates and rank stable profiles.
# Keywords: agct, sasang, composition, weight_sweep, btrack

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASES = ("A", "C", "G", "T")
AXES = ("TY", "SY", "TE", "SE")

DEFAULT_BASE_AXIS_WEIGHTS: dict[str, dict[str, float]] = {
    "A": {"TY": 1.0, "SY": 0.2, "TE": 0.1, "SE": 0.4},
    "C": {"TY": 0.2, "SY": 1.0, "TE": 0.4, "SE": 0.1},
    "G": {"TY": 0.1, "SY": 0.4, "TE": 1.0, "SE": 0.2},
    "T": {"TY": 0.4, "SY": 0.1, "TE": 0.2, "SE": 1.0},
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mutate_weights(
    base: dict[str, dict[str, float]],
    rng: random.Random,
    jitter: float,
) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        out[b] = {}
        for a in AXES:
            v = base[b][a] + rng.uniform(-jitter, jitter)
            out[b][a] = max(0.01, round(v, 6))
    return out


def _run_projection(
    script: Path,
    genotype_csv: Path,
    cohort_csv: Path | None,
    weight_json: Path,
    output_json: Path,
) -> dict:
    cmd = [
        sys.executable,
        str(script),
        "--genotype-csv",
        str(genotype_csv),
        "--axis-weights-json",
        str(weight_json),
        "--output-json",
        str(output_json),
    ]
    if cohort_csv is not None:
        cmd.extend(["--cohort-csv", str(cohort_csv)])
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"projection failed: {res.stderr or res.stdout}")
    return json.loads(output_json.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="AGCT composition weight sweep (B-track only).")
    ap.add_argument("--genotype-csv", type=Path, required=True)
    ap.add_argument("--cohort-csv", type=Path, default=None)
    ap.add_argument("--projection-script", type=Path, default=Path("scripts/run_agct_sasang_composition_projection_v1.py"))
    ap.add_argument("--candidates", type=int, default=40)
    ap.add_argument("--jitter", type=float, default=0.18)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--work-dir", type=Path, default=Path("tmp/agct_composition_weight_sweep_v1"))
    ap.add_argument("--output-json", type=Path, default=Path("reports/agct_sasang_composition_weight_sweep_v1_latest.json"))
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    ns.work_dir.mkdir(parents=True, exist_ok=True)

    candidates: list[dict] = []
    for i in range(max(1, ns.candidates)):
        if i == 0:
            weights = DEFAULT_BASE_AXIS_WEIGHTS
            profile_id = "baseline_default"
        else:
            weights = _mutate_weights(DEFAULT_BASE_AXIS_WEIGHTS, rng, ns.jitter)
            profile_id = f"cand_{i:03d}"

        w_path = ns.work_dir / f"{profile_id}_weights.json"
        out_path = ns.work_dir / f"{profile_id}_projection.json"
        w_path.write_text(json.dumps(weights, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        proj = _run_projection(ns.projection_script, ns.genotype_csv, ns.cohort_csv, w_path, out_path)
        axis_summary = proj["summary"]["axis_summary"]
        risk_corr = proj.get("risk_axis_correlations", {})

        axis_balance_gap = max(v["mean_projection"] for v in axis_summary.values()) - min(
            v["mean_projection"] for v in axis_summary.values()
        )
        risk_signal_score = sum(abs((risk_corr.get(a, {}) or {}).get("pearson_corr_with_risk") or 0.0) for a in AXES)
        objective_score = float(risk_signal_score - axis_balance_gap)

        candidates.append(
            {
                "profile_id": profile_id,
                "weights_json": str(w_path.resolve()),
                "projection_json": str(out_path.resolve()),
                "axis_balance_gap": axis_balance_gap,
                "risk_signal_score": risk_signal_score,
                "objective_score": objective_score,
                "axis_top_counts": proj["summary"]["axis_top_counts"],
            }
        )

    ranked = sorted(candidates, key=lambda r: (r["objective_score"], -r["axis_balance_gap"]), reverse=True)
    payload = {
        "schema": "agct_sasang_composition_weight_sweep_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "genotype_csv": str(ns.genotype_csv.resolve()),
            "cohort_csv": str(ns.cohort_csv.resolve()) if ns.cohort_csv and ns.cohort_csv.is_file() else None,
            "candidates": int(ns.candidates),
            "jitter": float(ns.jitter),
            "seed": int(ns.seed),
        },
        "best_profile": ranked[0],
        "top_profiles": ranked[:10],
        "all_profiles_count": len(ranked),
        "notes": [
            "Weight sweep is exploratory only.",
            "No clinical claim and no A-track promotion from this artifact alone.",
        ],
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} best={ranked[0]['profile_id']} score={ranked[0]['objective_score']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
