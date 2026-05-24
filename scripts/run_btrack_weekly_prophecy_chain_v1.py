#!/usr/bin/env python3
"""[HYPO] One-click B-track weekly prophecy chain (aligned 30d + matched + review pack)."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{cp.stderr or cp.stdout}")
    if cp.stdout.strip():
        print(cp.stdout.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-aligned",
        action="store_true",
        help="Skip run_btrack_aligned_30d_experiment_v1.py",
    )
    ap.add_argument(
        "--skip-matched",
        action="store_true",
        help="Skip run_btrack_active_day_matched_compare_v1.py",
    )
    ap.add_argument(
        "--skip-pack",
        action="store_true",
        help="Skip run_btrack_weekly_prophecy_review_pack_v1.py",
    )
    ap.add_argument(
        "--include-hybrid-parallel",
        action="store_true",
        help="Run run_btrack_v1_ms_hybrid_parallel_v1.py (5 rules, parallel score builds).",
    )
    args = ap.parse_args()

    py = sys.executable
    if not args.skip_aligned:
        _run([py, "scripts/run_btrack_aligned_30d_experiment_v1.py"])
    if not args.skip_matched:
        _run([py, "scripts/run_btrack_active_day_matched_compare_v1.py"])
    if args.include_hybrid_parallel:
        _run([py, "scripts/run_btrack_v1_ms_hybrid_parallel_v1.py", "--max-workers", "5"])
    if not args.skip_pack:
        _run([py, "scripts/run_btrack_weekly_prophecy_review_pack_v1.py"])

    suffix = " + hybrid" if args.include_hybrid_parallel else ""
    print(f"CHAIN_OK: aligned + matched + weekly pack{suffix} (B-track research only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
