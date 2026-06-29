"""OI 20460237 paste pack gate tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_kstartup_open_innovation_20460237_paste_ready_v1.py"
GATE = ROOT / "scripts/check_kstartup_open_innovation_20460237_paste_gate_v1.py"


def test_build_then_gate_exit_zero() -> None:
    bcp = subprocess.run([sys.executable, str(BUILD)], cwd=str(ROOT), capture_output=True, text=True)
    assert bcp.returncode == 0, bcp.stderr + bcp.stdout
    cp = subprocess.run([sys.executable, str(GATE)], cwd=str(ROOT), capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr + cp.stdout
