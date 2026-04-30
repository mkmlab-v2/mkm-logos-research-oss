#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> int:
    print("RUN:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run sasang symptom transition shadow chain v1.")
    ap.add_argument("--horizon-days", type=int, default=3)
    ap.add_argument(
        "--inject-balanced-labels",
        action="store_true",
        help="Enable synthetic balanced labels mode for B-track calibration stress.",
    )
    args = ap.parse_args()

    py = sys.executable
    build_cmd = [py, "scripts/build_sasang_symptom_market_proxy_v1.py", "--horizon-days", str(max(1, int(args.horizon_days)))]
    if args.inject_balanced_labels:
        build_cmd.append("--inject-balanced-labels")
    steps = [
        build_cmd,
        [py, "scripts/evaluate_sasang_symptom_transition_v1.py"],
        [py, "scripts/audit_sasang_symptom_transition_leakage_v1.py"],
        [py, "scripts/build_sasang_symptom_shadow_alert_v1.py"],
    ]
    for cmd in steps:
        code = _run(cmd)
        if code != 0:
            print(f"FAILED(exit={code}): {' '.join(cmd)}")
            return code
    print("OK: sasang symptom shadow chain completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
