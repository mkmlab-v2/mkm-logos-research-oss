#!/usr/bin/env python3
"""One-shot local runner for symbol lane gate -> baseline lock -> regression check."""

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
    ap = argparse.ArgumentParser(description="Run symbol lane gate+lock in one shot")
    ap.add_argument("--python", default=sys.executable, help="Python executable")
    ap.add_argument(
        "--include-shared-vault",
        action="store_true",
        help="Pass shared vault inclusion to symbol lane gate runner.",
    )
    ap.add_argument("--extract-top-k", type=int, default=1000, help="Forwarded to gate runner.")
    ap.add_argument("--extract-min-df", type=int, default=2, help="Forwarded to gate runner.")
    ap.add_argument("--curate-top-k", type=int, default=200, help="Forwarded to gate runner.")
    ap.add_argument("--curate-min-count", type=int, default=200, help="Forwarded to gate runner.")
    ap.add_argument(
        "--approve-numeric-near-miss",
        action="store_true",
        help="Forwarded approval flag for numeric near-miss promotion export.",
    )
    ap.add_argument("--profile-tag", default="stable", help="Output profile tag forwarded to gate runner.")
    ap.add_argument(
        "--gate-template",
        default="data/logos/btrack_pilot/gates/symbol_lane_gate_template.json",
        help="Gate template used for evaluation and lock metadata.",
    )
    ap.add_argument(
        "--baseline-out",
        default="reports/constitution/btrack_pilot/btrack_symbol_lane_baseline_lock_stable_latest.json",
        help="Baseline lock output path.",
    )
    args = ap.parse_args()
    py = args.python

    gate_cmd = [
        py,
        "scripts/run_btrack_symbol_lane_gate.py",
        "--extract-top-k",
        str(args.extract_top_k),
        "--extract-min-df",
        str(args.extract_min_df),
        "--curate-top-k",
        str(args.curate_top_k),
        "--curate-min-count",
        str(args.curate_min_count),
        "--profile-tag",
        str(args.profile_tag),
        "--gate-template",
        str(args.gate_template),
    ]
    if args.include_shared_vault:
        gate_cmd.append("--include-shared-vault")
    if args.approve_numeric_near_miss:
        gate_cmd.append("--approve-numeric-near-miss")
    _run(gate_cmd)
    _run(
        [
            py,
            "scripts/lock_btrack_symbol_lane_baseline.py",
            "--lane-gate",
            f"reports/constitution/btrack_pilot/symbol_lane_gate_{args.profile_tag}_latest.json",
            "--lane-summary",
            f"reports/constitution/btrack_pilot/symbol_lane_summary_{args.profile_tag}_latest.json",
            "--gate-template",
            str(args.gate_template),
            "--out",
            str(args.baseline_out),
        ]
    )
    _run(
        [
            py,
            "scripts/check_btrack_symbol_lane_regression.py",
            "--baseline",
            str(args.baseline_out),
            "--lane-gate",
            f"reports/constitution/btrack_pilot/symbol_lane_gate_{args.profile_tag}_latest.json",
        ]
    )
    print("OK: B-Track symbol lane gate+lock completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
