#!/usr/bin/env python3
"""[HYPO] Step2b-1: long-form MKVS binary spine bench (universal matrix slice)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/NEXTGEN_LONGFORM_SPINE_BENCH_INPUT_V1.json"
)
OUT_DEFAULT = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/results/ng40_spine_binary_billable_eval_longform_v1_latest.json"
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-raw-bytes", type=int, default=512)
    ap.add_argument("--max-cases", type=int, default=200)
    ap.add_argument("--bench-input", type=Path, default=BENCH_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-build-input", action="store_true")
    args = ap.parse_args()

    if not args.skip_build_input:
        b = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build_nextgen_longform_spine_bench_input_v1.py"),
                "--min-raw-bytes",
                str(args.min_raw_bytes),
                "--max-cases",
                str(args.max_cases),
                "--out-json",
                str(args.bench_input),
            ],
            cwd=str(ROOT),
        )
        if b.returncode != 0:
            return b.returncode

    ev = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_nextgen_spine_binary_billable_eval_v1.py"),
            "--bench-input",
            str(args.bench_input),
            "--out-json",
            str(args.out_json),
            "--arm-id",
            "ng40_spine_binary_billable_longform_v1",
            "--bench-label",
            "longform_universal_matrix",
        ],
        cwd=str(ROOT),
    )
    return ev.returncode


if __name__ == "__main__":
    raise SystemExit(main())
