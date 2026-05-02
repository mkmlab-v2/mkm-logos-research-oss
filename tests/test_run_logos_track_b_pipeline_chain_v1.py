# @MKM12-METADATA
# Type: Logic
# Purpose: Track B pipeline chain CLI smoke (cross-platform).
# Keywords: logos, track_b, pipeline

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CHAIN = _ROOT / "scripts" / "run_logos_track_b_pipeline_chain_v1.py"


def test_pipeline_chain_help_exits_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(_CHAIN), "--help"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0
    assert "skip-readiness-report" in cp.stdout
