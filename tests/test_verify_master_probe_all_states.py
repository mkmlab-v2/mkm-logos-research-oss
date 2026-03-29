"""Smoke: bundled Master Probe JSON passes full-state structural audit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_verify_master_probe_all_states_exit_zero():
    root = Path(__file__).resolve().parent.parent
    script = root / "scripts" / "verify_master_probe_all_states.py"
    probe = root / "data" / "myeongni" / "16_STATE_MASTER_PROBE_v1.json"
    r = subprocess.run(
        [sys.executable, str(script), str(probe)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert '"all_pass": true' in r.stdout
