"""CLI smoke for run_conditional_action_gate_v1 (subprocess, no live order)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_GATE = _ROOT / "projects" / "bitcoin-trading" / "scripts" / "run_conditional_action_gate_v1.py"
_FIXTURE = _ROOT / "tests" / "fixtures" / "risk_profile_fact_safe_gate_pass_minimal_v1.json"
_LOCKED_FIXTURE = _ROOT / "tests" / "fixtures" / "risk_profile_fact_safe_gate_locked_minimal_v1.json"
_TACTICAL_FIXTURE = _ROOT / "tests" / "fixtures" / "risk_profile_fact_safe_locked_tactical_pass_v1.json"
_HUMAN_GO = _ROOT / "tests" / "fixtures" / "trading_human_execution_approval_gate_fixture_GO.json"
_HUMAN_BAD = _ROOT / "tests" / "fixtures" / "trading_human_execution_approval_gate_fixture_BAD_HASH.json"
_FRAME_GOOD = _ROOT / "tests" / "fixtures" / "btc_frame_governance_stage_payload_gate_valid_v1.json"
_FRAME_NOT_LIVE = _ROOT / "tests" / "fixtures" / "btc_frame_governance_stage_payload_gate_not_live_v1.json"


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


def test_gate_api_dry_run_with_human_approval_fixture_exits_zero() -> None:
    assert _HUMAN_GO.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_FIXTURE),
        "--human-approval-json",
        str(_HUMAN_GO),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_gate_api_dry_run_human_approval_hash_fail_exit_7() -> None:
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_FIXTURE),
        "--human-approval-json",
        str(_HUMAN_BAD),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 7, proc.stderr + proc.stdout


def test_gate_api_dry_run_with_frame_payload_exits_zero() -> None:
    assert _FRAME_GOOD.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_FIXTURE),
        "--human-approval-json",
        str(_HUMAN_GO),
        "--frame-payload-json",
        str(_FRAME_GOOD),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_gate_api_pass_live_with_not_live_frame_payload_exit_8() -> None:
    assert _FRAME_NOT_LIVE.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_FIXTURE),
        "--human-approval-json",
        str(_HUMAN_GO),
        "--frame-payload-json",
        str(_FRAME_NOT_LIVE),
        "--pass-live",
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 8, proc.stderr + proc.stdout


def test_gate_api_dry_run_tactical_override_on_locked_mode_exits_zero() -> None:
    assert _TACTICAL_FIXTURE.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--enable-tactical-long",
        "--risk-json",
        str(_TACTICAL_FIXTURE),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_gate_api_dry_run_locked_fixture_exit_3() -> None:
    assert _LOCKED_FIXTURE.is_file()
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--risk-json",
        str(_LOCKED_FIXTURE),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.001",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 3, proc.stderr + proc.stdout


def test_gate_api_dry_run_locked_fixture_exit_zero_on_block_flag(tmp_path: Path) -> None:
    assert _LOCKED_FIXTURE.is_file()
    summary = tmp_path / "conditional_gate_test.json"
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--dry-run-exit-zero-on-block",
        "--risk-json",
        str(_LOCKED_FIXTURE),
        "--gate-summary",
        str(summary),
        "--skip-human-approval",
        "--skip-frame-payload",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(summary.read_text(encoding="utf-8"))
    assert doc.get("gate_ok") is False
    assert doc.get("gate_reason") == "trinity_governor_LOCKED_MODE"


def test_gate_api_dry_run_tactical_override_qty_cap_fail_exit_3() -> None:
    cmd = [
        sys.executable,
        str(_GATE),
        "--backend",
        "api",
        "--dry-run",
        "--enable-tactical-long",
        "--risk-json",
        str(_TACTICAL_FIXTURE),
        "--symbol",
        "BTCUSDT",
        "--side",
        "BUY",
        "--qty",
        "0.003",
        "--tactical-max-qty",
        "0.002",
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 3, proc.stderr + proc.stdout
