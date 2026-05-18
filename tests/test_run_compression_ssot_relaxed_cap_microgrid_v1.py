"""Ssot relaxed-cap microgrid must not write Track A active."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_compression_ssot_relaxed_cap_microgrid_v1.py"
ACTIVE = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"


def test_refuses_track_a_active_as_out() -> None:
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--out-json", str(ACTIVE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode != 0
    assert "Refusing" in (cp.stderr or cp.stdout or "")
