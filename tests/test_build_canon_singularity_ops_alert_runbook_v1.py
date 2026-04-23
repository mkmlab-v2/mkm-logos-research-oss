from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_build_canon_singularity_ops_alert_runbook_v1(tmp_path: Path):
    src = tmp_path / "rehearsal.json"
    freeze_gate = tmp_path / "freeze_gate.json"
    streak = tmp_path / "streak.json"
    out_json = tmp_path / "runbook.json"
    out_md = tmp_path / "runbook.md"
    src.write_text(
        json.dumps(
            {
                "task": {"status": "Ready", "last_result": "0"},
                "drift_gate": {"status": "alert", "drift_count": 2},
                "ops_alert_summary": {"ops_alert": True, "severity": "high", "consecutive_alert_count": 2},
                "recommended_action": {"kind": "run_strict_rehearsal", "reason": "drift_gate_alert", "command": "powershell ..."},
                "strict_auto_run": {"enabled": True, "triggered": True, "status": "pass", "exit_code": 0, "summary_path": "x.json"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    freeze_gate.write_text(
        json.dumps({"status": "pass", "metrics": {"window_size": 7, "frozen_rate": 0.857143}}, ensure_ascii=False),
        encoding="utf-8",
    )
    streak.write_text(
        json.dumps({"verdict": "hold", "metrics": {"window": 3, "window_size_observed": 1, "pass_count": 1, "latest_verdict": "pass"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    cmd = [
        sys.executable,
        "scripts/core/build_canon_singularity_ops_alert_runbook_v1.py",
        "--rehearsal-latest-json",
        str(src),
        "--freeze-v2-stability-gate-json",
        str(freeze_gate),
        "--observation-streak-json",
        str(streak),
        "--output-json",
        str(out_json),
        "--output-md",
        str(out_md),
    ]
    cp = subprocess.run(cmd, check=False, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
    assert cp.returncode == 0
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "original_corpus_regime_singularity_canon_ops_alert_runbook_v1"
    assert data["ops_alert_summary"]["severity"] == "high"
    assert data["freeze_v2_stability_gate"]["status"] == "pass"
    assert data["freeze_v2_stability_gate"]["frozen_rate"] == 0.857143
    assert data["observation_streak"]["verdict"] == "hold"
    assert "observation_streak_hold" in data["attention_reasons"]
    assert out_md.exists()

