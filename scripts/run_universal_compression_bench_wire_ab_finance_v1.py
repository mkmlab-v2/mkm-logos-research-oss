#!/usr/bin/env python3
"""Thin wrapper: finance lane wire AB (delegates to run_universal_compression_bench_wire_ab_lane_v1)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_universal_compression_bench_wire_ab_lane_v1.py"),
        "--lane",
        "finance",
    ]
    if "--dry-run" in sys.argv:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, cwd=ROOT)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
