"""Customer intake readiness + drop watch internal tenant skip."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READINESS = ROOT / "scripts/check_wtt_customer_intake_readiness_v1.py"
WATCH = ROOT / "scripts/watch_wtt_pilot_intake_drop_v1.py"


def test_customer_intake_readiness_report(tmp_path: Path) -> None:
    out = tmp_path / "ready.json"
    proc = subprocess.run(
        [sys.executable, str(READINESS), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "wtt_customer_intake_readiness_v1"
    assert doc.get("send_gate") == "HOLD"
    assert "operator_panel_separate" in doc


def test_drop_watch_skips_internal_operator_tenant(tmp_path: Path) -> None:
    intake = tmp_path / "intake"
    intake.mkdir()
    op = intake / "wtt-operator-panel-v1.jsonl"
    op.write_text(
        json.dumps(
            {
                "session_id": "x",
                "turns": [{"role": "user", "text": "test"}],
                "labels": ["operator_panel"],
                "customer_provided": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    state = tmp_path / "state.json"
    report_out = tmp_path / "watch.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(WATCH),
            "--intake-dir",
            str(intake),
            "--state",
            str(state),
            "--out",
            str(report_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(report_out.read_text(encoding="utf-8"))
    assert report["actions"][0].get("reason") == "internal_lane_tenant"
