#!/usr/bin/env python3
"""Logos 성경 최대 고도화 체인 — corpus enrich → registry → batch → dual-gate → UI sim.

Reproducible:
  py scripts/run_logos_max_advancement_chain_v1.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHAIN = (
    ("enrich_logos_motif_gematria_from_corpus_v1.py", []),
    ("build_logos_motif_registry_top100_v1.py", []),
    ("run_logos_spread_tuning_chain_v1.py", []),
    ("run_logos_cosmic_anchor_ui_resonance_sim_v1.py", []),
)


def main() -> int:
    for script, extra in CHAIN:
        proc = subprocess.run(
            [sys.executable, f"scripts/{script}", *extra],
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
