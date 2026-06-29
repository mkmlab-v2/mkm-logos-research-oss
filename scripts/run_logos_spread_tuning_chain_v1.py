#!/usr/bin/env python3
"""Wave 2.5 spread-tuning research chain (B-track sandbox).

Reproducible:
  py scripts/run_logos_spread_tuning_chain_v1.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHAIN = (
    "build_logos_motif_registry_top100_v1.py",
    "build_logos_cosmic_anchor_batch_v1.py",
    "build_logos_cosmic_anchor_batch_sandbox_v1.py",
    "build_logos_anchor_resonance_stats_v1.py",
)


def main() -> int:
    for script in CHAIN:
        proc = subprocess.run(
            [sys.executable, f"scripts/{script}"],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            print(f"FAIL: {script} exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        print(f"OK: {script}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
