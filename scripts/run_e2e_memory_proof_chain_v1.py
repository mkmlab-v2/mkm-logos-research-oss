#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str]) -> int:
    proc = subprocess.run([sys.executable, *args], cwd=str(ROOT))
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline-runs", type=int, default=5)
    ap.add_argument("--live-runs", type=int, default=3)
    ap.add_argument("--execute-guard", action="store_true")
    ap.add_argument("--guard-samples", type=int, default=1)
    args = ap.parse_args()

    steps = [
        ["scripts/run_e2e_memory_proof_offline_ab_v1.py", "--runs", str(max(1, args.offline_runs))],
        [
            "scripts/run_e2e_memory_proof_live_ab_v1.py",
            "--runs",
            str(max(1, args.live_runs)),
            "--guard-samples",
            str(max(1, args.guard_samples)),
        ],
        ["scripts/aggregate_e2e_memory_proof_stats_v1.py"],
        ["scripts/build_e2e_memory_proof_b2b_pack_v1.py"],
    ]
    if args.execute_guard:
        steps[1].append("--execute-guard")
    for step in steps:
        rc = _run(step)
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
