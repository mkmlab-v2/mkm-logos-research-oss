#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.9, L:0.86, K:0.68, M:0.38}
# Balance: 90
# Purpose: Evaluate neutral-baseline AB promotion stability across multiple seeds.
# Keywords: bio, dna, ab, holdout, bootstrap, stability, neutral, seed
"""Run neutral-baseline AB evaluation across multiple seeds and summarize stability."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _percentile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    arr = sorted(vals)
    i = (len(arr) - 1) * q
    lo = int(i)
    hi = min(lo + 1, len(arr) - 1)
    w = i - lo
    return (arr[lo] * (1.0 - w)) + (arr[hi] * w)


def main() -> int:
    ap = argparse.ArgumentParser(description="Neutral baseline multi-seed stability sweep.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--seed-start", type=int, default=20260421)
    ap.add_argument("--seed-count", type=int, default=30)
    ap.add_argument("--holdout-ratio", type=float, default=0.3)
    ap.add_argument("--bootstrap-iterations", type=int, default=2000)
    ap.add_argument("--min-holdout-samples", type=int, default=60)
    ap.add_argument("--min-abs-uplift", type=float, default=0.02)
    ap.add_argument(
        "--summary-json",
        type=Path,
        default=root / "reports" / "bio_dna_ab_neutral_seed_stability_v1.json",
    )
    ap.add_argument(
        "--summary-csv",
        type=Path,
        default=root / "reports" / "bio_dna_ab_neutral_seed_stability_v1.csv",
    )
    ap.add_argument(
        "--run-dir",
        type=Path,
        default=root / "reports" / "bio_dna_ab_neutral_seed_runs_v1",
    )
    ns = ap.parse_args()

    autobuild_script = root / "scripts" / "run_bio_dna_ab_autobuild_and_eval_v1.py"
    ns.run_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for i in range(ns.seed_count):
        seed = ns.seed_start + i
        eval_out = ns.run_dir / f"eval_seed_{seed}.json"
        build_out = ns.run_dir / f"build_seed_{seed}.json"
        combined_out = ns.run_dir / f"combined_seed_{seed}.csv"
        cmd = [
            sys.executable,
            str(autobuild_script),
            "--use-blind-replay-profiles",
            "--baseline-mode",
            "neutral",
            "--seed",
            str(seed),
            "--holdout-ratio",
            str(ns.holdout_ratio),
            "--bootstrap-iterations",
            str(ns.bootstrap_iterations),
            "--min-holdout-samples",
            str(ns.min_holdout_samples),
            "--min-abs-uplift",
            str(ns.min_abs_uplift),
            "--combined-out-csv",
            str(combined_out),
            "--eval-out-json",
            str(eval_out),
            "--build-report-json",
            str(build_out),
        ]
        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0 or not eval_out.is_file():
            failures.append({"seed": seed, "exit_code": proc.returncode})
            continue
        data = json.loads(eval_out.read_text(encoding="utf-8"))
        m = data.get("metrics", {})
        b = data.get("bootstrap", {})
        g = data.get("promotion_gate", {})
        rows.append(
            {
                "seed": seed,
                "holdout_n": int(data.get("split", {}).get("holdout_count", 0)),
                "base_acc": float(m.get("holdout_baseline_accuracy", 0.0)),
                "treat_acc": float(m.get("holdout_treatment_accuracy", 0.0)),
                "uplift": float(m.get("holdout_uplift", 0.0)),
                "ci_low": float(b.get("ci_low", 0.0)),
                "ci_high": float(b.get("ci_high", 0.0)),
                "ready": bool(g.get("promotion_candidate_ready", False)),
            }
        )

    rows_sorted = sorted(rows, key=lambda x: x["seed"])
    ns.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    with ns.summary_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "seed",
                "holdout_n",
                "base_acc",
                "treat_acc",
                "uplift",
                "ci_low",
                "ci_high",
                "ready",
            ],
        )
        writer.writeheader()
        writer.writerows(rows_sorted)

    ready_count = sum(1 for r in rows_sorted if r["ready"])
    uplift_vals = [float(r["uplift"]) for r in rows_sorted]
    cilow_vals = [float(r["ci_low"]) for r in rows_sorted]
    summary: dict[str, Any] = {
        "schema": "bio_dna_ab_neutral_seed_stability_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "inputs": {
            "seed_start": ns.seed_start,
            "seed_count": ns.seed_count,
            "holdout_ratio": ns.holdout_ratio,
            "bootstrap_iterations": ns.bootstrap_iterations,
            "min_holdout_samples": ns.min_holdout_samples,
            "min_abs_uplift": ns.min_abs_uplift,
            "baseline_mode": "neutral",
            "source_mode": "blind_replay_profiles",
        },
        "outputs": {
            "summary_csv": str(ns.summary_csv.resolve()),
            "run_dir": str(ns.run_dir.resolve()),
        },
        "stats": {
            "attempted": ns.seed_count,
            "succeeded": len(rows_sorted),
            "failed": len(failures),
            "promotion_ready_count": ready_count,
            "promotion_ready_rate": (ready_count / len(rows_sorted)) if rows_sorted else 0.0,
            "uplift_median": _percentile(uplift_vals, 0.5),
            "uplift_p10": _percentile(uplift_vals, 0.1),
            "uplift_p90": _percentile(uplift_vals, 0.9),
            "ci_low_median": _percentile(cilow_vals, 0.5),
            "ci_low_p10": _percentile(cilow_vals, 0.1),
            "ci_low_p90": _percentile(cilow_vals, 0.9),
        },
        "failures": failures,
        "note": "Seed stability evidence for neutral baseline; promotion claims still require human review.",
    }
    ns.summary_json.parent.mkdir(parents=True, exist_ok=True)
    ns.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        "WROTE:",
        ns.summary_json.resolve(),
        f"succeeded={len(rows_sorted)}",
        f"ready_rate={summary['stats']['promotion_ready_rate']:.4f}",
    )
    print("WROTE:", ns.summary_csv.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
