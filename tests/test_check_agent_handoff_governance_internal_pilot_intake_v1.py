"""Internal pilot intake validation smoke."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mkm_internal_intake_ok():
    r = subprocess.run(
        [sys.executable, "scripts/check_agent_handoff_governance_internal_pilot_intake_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout
