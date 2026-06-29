#!/usr/bin/env python3
"""Job-only live probe for magic-orb four-slot showroom (B-track gate)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "scripts/probe_mkmlife_magic_orb_live_v1.py"
OUT = ROOT / "reports/magic_orb_job_four_slot_live_probe_latest.json"


def main() -> int:
    cmd = [sys.executable, str(MAIN), "--profile", "job_four_slot", "--out", str(OUT)]
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
