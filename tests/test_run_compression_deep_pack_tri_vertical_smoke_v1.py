"""Smoke runner for compression deep pack tri-vertical chain."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_compression_deep_pack_tri_vertical_smoke_v1.py"


def test_compression_deep_pack_tri_vertical_smoke_exit_zero() -> None:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--skip-pytest"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert '"ok": true' in (proc.stdout or "")
