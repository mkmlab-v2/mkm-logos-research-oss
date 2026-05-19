"""Smoke tests for check_prophecy_live_rollback_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rollback_check_ok_with_fixture(tmp_path: Path) -> None:
    trade = {
        "treatment": [
            {"realized_pnl": -1.0, "commission": 0.1},
            {"realized_pnl": 0.5, "commission": 0.1},
        ]
    }
    trade_path = tmp_path / "win.json"
    trade_path.write_text(json.dumps(trade), encoding="utf-8")
    policy = {
        "policy": {"max_daily_loss_pct": 2.0},
    }
    policy_path = tmp_path / "pol.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")
    go_path = tmp_path / "go.json"
    go_path.write_text(json.dumps({"go_no_go": "GO"}), encoding="utf-8")
    out = tmp_path / "out.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_prophecy_live_rollback_v1.py"),
        "--trade-window-json",
        str(trade_path),
        "--rollback-policy-json",
        str(policy_path),
        "--go-json",
        str(go_path),
        "--gates-json",
        str(tmp_path / "missing.json"),
        "--reference-usdt",
        "500",
        "--out-json",
        str(out),
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["rollback_triggered"] is False
    assert doc["observed"]["go_no_go"] == "GO"


def test_rollback_breach_loss_pct(tmp_path: Path) -> None:
    trade = {"treatment": [{"realized_pnl": -20.0, "commission": 1.0}]}
    trade_path = tmp_path / "win.json"
    trade_path.write_text(json.dumps(trade), encoding="utf-8")
    policy_path = tmp_path / "pol.json"
    policy_path.write_text(
        json.dumps({"policy": {"max_daily_loss_pct": 2.0}}), encoding="utf-8"
    )
    out = tmp_path / "out.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "check_prophecy_live_rollback_v1.py"),
        "--trade-window-json",
        str(trade_path),
        "--rollback-policy-json",
        str(policy_path),
        "--go-json",
        str(tmp_path / "go.json"),
        "--reference-usdt",
        "100",
        "--out-json",
        str(out),
        "--strict-exit",
    ]
    (tmp_path / "go.json").write_text(json.dumps({"go_no_go": "GO"}), encoding="utf-8")
    proc = subprocess.run(cmd, cwd=ROOT)
    assert proc.returncode == 2
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["rollback_triggered"] is True
