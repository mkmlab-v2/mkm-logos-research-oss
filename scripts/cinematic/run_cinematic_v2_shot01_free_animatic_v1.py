#!/usr/bin/env python3
"""[HYPO] Free ($0) cinematic v2 SHOT_01 — thin wrapper around free animatic bundle."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "scripts/cinematic/run_cinematic_v2_free_animatic_bundle_v1.py"


def main() -> int:
    proc = subprocess.run(
        [sys.executable, str(BUNDLE), "--shot-id", "SHOT_01", "--skip-concat"],
        cwd=str(ROOT),
    )
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
