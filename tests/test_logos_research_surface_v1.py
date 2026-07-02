"""Logos research surface gate — homepage Q&A first (payment deferred)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts/check_logos_research_surface_v1.py"


def test_surface_check_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
