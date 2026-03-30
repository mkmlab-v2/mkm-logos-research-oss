#!/usr/bin/env python3
"""One-shot runner: question logs -> V3 sampled dataset -> performance report."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> None:
    print(f"[run] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run V3 measured pipeline in one shot")
    ap.add_argument("--python", default=sys.executable, help="Python executable")
    ap.add_argument("--in", dest="input_path", required=True, help="Question log JSONL")
    ap.add_argument("--dataset-out", required=True, help="V3 dataset JSONL output")
    ap.add_argument("--sampling-summary-out", required=True, help="Sampling summary JSON output")
    ap.add_argument("--performance-out", required=True, help="Performance report JSON output")
    ap.add_argument("--sample-size", type=int, default=200, help="Sample size")
    ap.add_argument("--seed", type=int, default=42, help="Random seed")
    ap.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    ap.add_argument("--val-ratio", type=float, default=0.1, help="Validation split ratio")
    args = ap.parse_args()

    py = args.python
    _run(
        [
            py,
            "scripts/build_v3_input_from_question_logs.py",
            "--in",
            args.input_path,
            "--out",
            args.dataset_out,
            "--summary-out",
            args.sampling_summary_out,
            "--sample-size",
            str(args.sample_size),
            "--seed",
            str(args.seed),
            "--train-ratio",
            str(args.train_ratio),
            "--val-ratio",
            str(args.val_ratio),
        ]
    )
    _run(
        [
            py,
            "scripts/report_v3_pipeline_performance.py",
            "--in",
            args.dataset_out,
            "--out",
            args.performance_out,
        ]
    )

    print("OK: V3 measured pipeline completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
