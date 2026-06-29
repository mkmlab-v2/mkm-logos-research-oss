"""Offline smoke: BigSet studio conflict sidecar mirror."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "scripts/check_bigset_studio_conflict_sidecar_smoke_v1.py"


def test_studio_conflict_sidecar_offline_smoke():
    proc = subprocess.run(
        [sys.executable, str(SMOKE), "--require-pending-field"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
