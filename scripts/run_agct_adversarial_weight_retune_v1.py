#!/usr/bin/env python3
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)


def _normalize_row(row: dict[str, float]) -> dict[str, float]:
    for k in AXES:
        row[k] = max(0.0, float(row.get(k, 0.0)))
    s = sum(row.values())
    if s <= 0:
        return {k: 0.25 for k in AXES}
    return {k: row[k] / s for k in AXES}


def _mutate(w: dict[str, dict[str, float]], rng: random.Random, sigma: float) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for b in BASES:
        row = {ax: float(w[b][ax]) + rng.uniform(-sigma, sigma) for ax in AXES}
        out[b] = _normalize_row(row)
    return out


def _score_with_profile_grid(root: Path, weights_json: Path, n_samples: int, seed: int, noise_grid: str, out_json: Path) -> dict:
    grid_script = root / "scripts" / "run_agct_adversarial_profile_grid_v1.py"
    _run(
        [
            sys.executable,
            str(grid_script),
            "--weights-json",
            str(weights_json),
            "--n-samples",
            str(n_samples),
            "--seed",
            str(seed),
            "--noise-grid",
            noise_grid,
            "--output-json",
            str(out_json),
        ]
    )
    return json.loads(out_json.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Retune AGCT weights for adversarial robustness (B-track).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--iterations", type=int, default=24)
    ap.add_argument("--sigma", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--n-samples", type=int, default=1200)
    ap.add_argument("--noise-grid", type=str, default="0.1,0.2,0.35,0.5,0.7")
    ap.add_argument("--best-weights-out-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_robust_candidate_v1.json")
    ap.add_argument("--output-json", type=Path, default=root / "reports" / "agct_adversarial_weight_retune_v1_latest.json")
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    base_weights = json.loads(ns.base_weights_json.read_text(encoding="utf-8"))

    work_dir = root / "tmp" / "agct_adversarial_retune_v1"
    work_dir.mkdir(parents=True, exist_ok=True)

    incumbent = base_weights
    incumbent_path = work_dir / "incumbent_weights.json"
    incumbent_path.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    inc_eval_path = work_dir / "incumbent_grid_eval.json"
    inc_eval = _score_with_profile_grid(root, incumbent_path, ns.n_samples, ns.seed, ns.noise_grid, inc_eval_path)
    inc_score = float(inc_eval["summary"]["avg_robustness_score"])

    trials = []
    for i in range(ns.iterations):
        cand = _mutate(incumbent, rng, ns.sigma)
        cand_path = work_dir / f"cand_{i:03d}_weights.json"
        cand_path.write_text(json.dumps(cand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        cand_eval_path = work_dir / f"cand_{i:03d}_grid_eval.json"
        cand_eval = _score_with_profile_grid(root, cand_path, ns.n_samples, ns.seed + 100 + i, ns.noise_grid, cand_eval_path)
        cand_score = float(cand_eval["summary"]["avg_robustness_score"])
        improved = cand_score > inc_score
        if improved:
            incumbent = cand
            inc_score = cand_score
            incumbent_path.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            inc_eval = cand_eval
        trials.append(
            {
                "iter": i,
                "candidate_score": cand_score,
                "incumbent_score_after_iter": inc_score,
                "accepted": improved,
                "candidate_eval_report": str(cand_eval_path.resolve()),
            }
        )

    ns.best_weights_out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.best_weights_out_json.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "agct_adversarial_weight_retune_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "iterations": ns.iterations,
            "sigma": ns.sigma,
            "noise_grid": ns.noise_grid,
            "n_samples": ns.n_samples,
        },
        "summary": {
            "best_avg_robustness_score": inc_score,
            "accepted_moves": sum(1 for t in trials if t["accepted"]),
            "best_profile_grid_eval": inc_eval,
        },
        "outputs": {
            "best_weights_json": str(ns.best_weights_out_json.resolve()),
            "work_dir": str(work_dir.resolve()),
        },
        "trials": trials,
    }
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.output_json.resolve()} best_avg_robustness={inc_score:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
