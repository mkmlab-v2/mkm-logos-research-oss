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
    args = ap.parse_args()
    py = args.python

    gate_cmd = [py, "scripts/run_btrack_symbol_lane_gate.py"]
    if args.include_shared_vault:
        gate_cmd.append("--include-shared-vault")
    _run(gate_cmd)
    _run([py, "scripts/lock_btrack_symbol_lane_baseline.py"])
    _run([py, "scripts/check_btrack_symbol_lane_regression.py"])
    print("OK: B-Track symbol lane gate+lock completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
