"""D2: clinician km-classics PUBLIC_FACING copy gate tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_clinician_km_classics_public_copy_v1.py"


def test_copy_gate_exit_zero() -> None:
    cp = subprocess.run([sys.executable, str(GATE)], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
