"""infra_compliance_gate_v1 — Entry B cloud IDE + PHI co-occurrence block."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts import infra_compliance_gate_v1 as mod

WS = Path(__file__).resolve().parents[1]
SAFE = WS / "tests/fixtures/infra_compliance_gate_v1_safe.env"
BLOCKED = WS / "tests/fixtures/infra_compliance_gate_v1_blocked.env"


def test_analyze_safe_env_passes() -> None:
    text = SAFE.read_text(encoding="utf-8")
    result = mod.analyze_text(text, path=str(SAFE))
    assert result.ok is True
    assert result.blocked is False
    assert result.cloud_hits
    assert not result.phi_hits


def test_analyze_blocked_env_fails() -> None:
    text = BLOCKED.read_text(encoding="utf-8")
    result = mod.analyze_text(text, path=str(BLOCKED))
    assert result.ok is False
    assert result.blocked is True
    assert result.cloud_hits
    assert result.phi_hits
    assert "cloud_ide_and_phi_co_occurrence" in result.reasons


def test_cli_safe_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(WS / "scripts/infra_compliance_gate_v1.py"), str(SAFE), "--out", str(out)],
        cwd=str(WS),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_cli_blocked_exit_one(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(WS / "scripts/infra_compliance_gate_v1.py"), str(BLOCKED), "--out", str(out)],
        cwd=str(WS),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 1, proc.stderr + proc.stdout
