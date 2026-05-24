#!/usr/bin/env python3
"""One-shot: harvest homogeneous lanes, refresh manifest, run expansion dry-run + pool compare."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-counts", default="40,80,120,200,400")
    ap.add_argument("--skip-harvest", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()

    py = sys.executable
    steps: list[list[str]] = []
    if not args.skip_harvest:
        steps.extend(
            [
                [py, "scripts/build_golden40_logos_verse_compression_lane_v1.py"],
                [
                    py,
                    "scripts/build_universal_compression_bench_lane_from_md_v1.py",
                    "--manifest",
                    "docs/final/artifacts/golden_40_en_ops_lane_manifest_v1.json",
                    "--out",
                    "docs/final/artifacts/golden_40_en_ops_compression_lane_v1.json",
                ],
            ]
        )
    steps.append([py, "scripts/build_golden40_homogeneous_expansion_manifest_v1.py"])

    compare_cmd = [
        py,
        "scripts/run_golden40_expansion_pool_compare_v1.py",
        "--target-counts",
        args.target_counts,
    ]
    if args.plan_only:
        compare_cmd.append("--plan-only")
    steps.append(compare_cmd)

    worst = 0
    for cmd in steps:
        rc = _run(cmd)
        worst = max(worst, rc)
    return 0 if worst == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
