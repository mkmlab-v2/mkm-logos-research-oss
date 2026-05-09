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


def _eval_metrics(root: Path, weights_json: Path, n_samples: int, seed: int, robustness_n_samples: int) -> dict[str, float]:
    robust_script = root / "scripts" / "run_agct_adversarial_profile_grid_v1.py"
    ext_script = root / "scripts" / "run_agct_sasang_external_blind_proxy_eval_v1.py"
    tmp_dir = root / "tmp" / "agct_joint_retune_v1"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    robust_out = tmp_dir / f"robust_{weights_json.stem}_{seed}.json"
    ext_out = tmp_dir / f"external_{weights_json.stem}_{seed}.json"

    _run(
        [
            sys.executable,
            str(robust_script),
            "--weights-json",
            str(weights_json),
            "--n-samples",
            str(robustness_n_samples),
            "--seed",
            str(seed),
            "--output-json",
            str(robust_out),
        ]
    )
    _run(
        [
            sys.executable,
            str(ext_script),
            "--prior-profile",
            "aggressive",
            "--n-samples",
            str(n_samples),
            "--seed",
            str(seed),
            "--active-weights-json",
            str(weights_json),
            "--output-json",
            str(ext_out),
        ]
    )
    robust = json.loads(robust_out.read_text(encoding="utf-8"))
    ext = json.loads(ext_out.read_text(encoding="utf-8"))
    return {
        "robustness_score": float(robust["summary"]["avg_robustness_score"]),
        "external_accuracy": float(ext["summary"]["top_axis_accuracy_vs_proxy_label"]),
        "external_risk_corr": float(ext["summary"]["predicted_risk_corr_with_proxy_risk"] or 0.0),
        "robust_report": str(robust_out.resolve()),
        "external_report": str(ext_out.resolve()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Joint retune: robustness + external correlation (B-track).")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--base-weights-json", type=Path, default=root / "tmp" / "agct_sasang_axis_weights_active_btrack_v1.json")
    ap.add_argument("--iterations", type=int, default=48)
    ap.add_argument("--sigma", type=float, default=0.08)
    ap.add_argument("--seed", type=int, default=20260505)
    ap.add_argument("--external-n-samples", type=int, default=1200)
    ap.add_argument("--robustness-n-samples", type=int, default=800)
    ap.add_argument("--w-robustness", type=float, default=0.4)
    ap.add_argument("--w-ext-corr", type=float, default=0.5)
    ap.add_argument("--w-ext-acc", type=float, default=0.1)
    ap.add_argument(
        "--best-weights-out-json",
        type=Path,
        default=root / "tmp" / "agct_sasang_axis_weights_joint_candidate_v1.json",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "reports" / "agct_joint_retune_robust_external_v1_latest.json",
    )
    ns = ap.parse_args()

    rng = random.Random(ns.seed)
    base = json.loads(ns.base_weights_json.read_text(encoding="utf-8"))
    work_dir = root / "tmp" / "agct_joint_retune_v1"
    work_dir.mkdir(parents=True, exist_ok=True)
    incumbent = base
    inc_path = work_dir / "incumbent_weights.json"
    inc_path.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    inc_metrics = _eval_metrics(root, inc_path, ns.external_n_samples, ns.seed, ns.robustness_n_samples)
    inc_score = (
        ns.w_robustness * inc_metrics["robustness_score"]
        + ns.w_ext_corr * inc_metrics["external_risk_corr"]
        + ns.w_ext_acc * inc_metrics["external_accuracy"]
    )

    trials = []
    for i in range(ns.iterations):
        cand = _mutate(incumbent, rng, ns.sigma)
        cand_path = work_dir / f"cand_{i:03d}_weights.json"
        cand_path.write_text(json.dumps(cand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        m = _eval_metrics(root, cand_path, ns.external_n_samples, ns.seed + i + 1, ns.robustness_n_samples)
        score = ns.w_robustness * m["robustness_score"] + ns.w_ext_corr * m["external_risk_corr"] + ns.w_ext_acc * m["external_accuracy"]
        accepted = score > inc_score
        if accepted:
            incumbent = cand
            inc_metrics = m
            inc_score = score
            inc_path.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        trials.append(
            {
                "iter": i,
                "accepted": accepted,
                "candidate_score": score,
                "incumbent_score_after_iter": inc_score,
                "candidate_metrics": m,
            }
        )

    ns.best_weights_out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.best_weights_out_json.write_text(json.dumps(incumbent, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    payload = {
        "schema": "agct_joint_retune_robust_external_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "inputs": {
            "base_weights_json": str(ns.base_weights_json.resolve()),
            "iterations": ns.iterations,
            "sigma": ns.sigma,
            "external_n_samples": ns.external_n_samples,
            "robustness_n_samples": ns.robustness_n_samples,
            "weights": {
                "robustness": ns.w_robustness,
                "external_corr": ns.w_ext_corr,
                "external_acc": ns.w_ext_acc,
            },
        },
        "summary": {
            "best_joint_score": inc_score,
            "accepted_moves": sum(1 for t in trials if t["accepted"]),
            "best_metrics": inc_metrics,
        },
        "outputs": {
            "best_weights_json": str(ns.best_weights_out_json.resolve()),
            "work_dir": str(work_dir.resolve()),
        },
        "trials": trials,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {ns.output_json.resolve()} "
        f"joint={inc_score:.4f} robust={inc_metrics['robustness_score']:.4f} "
        f"ext_corr={inc_metrics['external_risk_corr']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
