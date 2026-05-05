from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_trading_go_nogo_status_v1.py"


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_go_status(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    approval = tmp_path / "approval.json"
    risk = tmp_path / "risk.json"
    out = tmp_path / "status.json"
    _write(
        gate,
        {
            "schema": "conditional_action_gate_v1",
            "gate_ok": True,
            "gate_reason": "go_trinity_ACTIVE_MODE",
            "backend": "api",
        },
    )
    _write(
        approval,
        {
            "schema": "trading_human_execution_approval_v1",
            "domain": "trading",
            "track": "A",
            "proposal_id": "p1",
            "proposal_body_sha256": "a" * 64,
            "decision": "GO",
            "approved_at_utc": "2026-05-04T00:00:00Z",
            "valid_until_utc": "2099-12-31T23:59:59Z",
        },
    )
    _write(
        risk,
        {
            "schema_version": "risk_profile_v0.1",
            "expires_at": "2099-12-31T23:59:59Z",
            "trinity_governor": {"mode": "ACTIVE_MODE"},
            "governance_bridge": {"final_action_allowed": True},
        },
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-summary",
            str(gate),
            "--approval-json",
            str(approval),
            "--risk-json",
            str(risk),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["go_no_go"] == "GO"
    assert doc["reasons"] == []


def test_build_no_go_when_approval_missing(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    risk = tmp_path / "risk.json"
    out = tmp_path / "status.json"
    _write(gate, {"gate_ok": True})
    _write(
        risk,
        {
            "expires_at": "2099-12-31T23:59:59Z",
            "trinity_governor": {"mode": "ACTIVE_MODE"},
            "governance_bridge": {"final_action_allowed": True},
        },
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gate-summary",
            str(gate),
            "--approval-json",
            str(tmp_path / "missing.json"),
            "--risk-json",
            str(risk),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["go_no_go"] == "NO_GO"
    assert "missing_or_invalid_human_approval" in doc["reasons"]

