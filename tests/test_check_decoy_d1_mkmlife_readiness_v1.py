from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_decoy_d1_readiness_cli() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_decoy_d1_mkmlife_readiness_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
