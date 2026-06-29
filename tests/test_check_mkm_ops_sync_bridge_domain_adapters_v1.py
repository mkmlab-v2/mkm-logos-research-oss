"""Smoke tests for check_mkm_ops_sync_bridge_domain_adapters_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check_mkm_ops_sync_bridge_domain_adapters_v1.py"


def test_gate_script_exit_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = json.loads(cp.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
