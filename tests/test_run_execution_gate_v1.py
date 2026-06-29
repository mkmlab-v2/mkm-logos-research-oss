"""Regression tests for scripts/run_execution_gate_v1.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "run_execution_gate_v1.py"


def _run_gate(tmp_path: Path, intent: dict, risk: dict) -> dict:
    intent_path = tmp_path / "intent.json"
    risk_path = tmp_path / "risk.json"
    gov_path = tmp_path / "gov.json"
    sec_path = tmp_path / "sec.json"
    ops_path = tmp_path / "ops.json"
    out_path = tmp_path / "decision.json"

    intent_path.write_text(json.dumps(intent), encoding="utf-8")
    risk_path.write_text(json.dumps(risk), encoding="utf-8")
    gov_path.write_text(json.dumps({"status": "GO", "final_action_allowed": True}), encoding="utf-8")
    sec_path.write_text(json.dumps({"status": "GREEN"}), encoding="utf-8")
    ops_path.write_text(json.dumps({"mode": "NORMAL"}), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--governance-path",
            str(gov_path),
            "--security-status-path",
            str(sec_path),
            "--ops-status-path",
            str(ops_path),
            "--risk-profile-path",
            str(risk_path),
            "--intent-path",
            str(intent_path),
            "--output-path",
            str(out_path),
            "--audit-jsonl",
            str(tmp_path / "audit.jsonl"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert out_path.is_file(), proc.stderr or proc.stdout
    decision = json.loads(out_path.read_text(encoding="utf-8"))
    if decision.get("decision") == "ALLOW":
        assert proc.returncode == 0, proc.stderr or proc.stdout
    else:
        assert proc.returncode == 2, proc.stderr or proc.stdout
    return decision


def test_close_position_skips_max_position_cap(tmp_path: Path) -> None:
    decision = _run_gate(
        tmp_path,
        intent={
            "symbol": "BTCUSDT",
            "side": "SELL",
            "qty": 0.05,
            "intent_type": "close_position",
        },
        risk={"max_position_size": 0.03, "mode": "repo_shadow"},
    )
    assert decision["decision"] == "ALLOW"
    assert decision["allow_order"] is True


def test_open_long_still_blocked_by_max_position(tmp_path: Path) -> None:
    decision = _run_gate(
        tmp_path,
        intent={
            "symbol": "BTCUSDT",
            "side": "BUY",
            "qty": 0.05,
            "intent_type": "open_long_position",
        },
        risk={"max_position_size": 0.03, "mode": "repo_shadow"},
    )
    assert decision["decision"] == "BLOCK"
    assert any("max_position_size" in r for r in decision.get("reasons", []))
