"""CLI smoke for run_conditional_action_gate_v1 (subprocess, no live order)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_GATE = _ROOT / "projects" / "bitcoin-trading" / "scripts" / "run_conditional_action_gate_v1.py"
_FIXTURE = _ROOT / "tests" / "fixtures" / "risk_profile_fact_safe_gate_pass_minimal_v1.json"


def test_gate_api_dry_run_fixture_exits_zero() -> None:
    assert _FIXTURE.is_file()
    assert _GATE.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_FIXTURE),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_fixture_json_is_valid_gate_pass_shape() -> None:
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert doc.get("trinity_governor", {}).get("mode") == "ACTIVE_MODE"
    assert doc.get("governance_bridge", {}).get("final_action_allowed") is True
