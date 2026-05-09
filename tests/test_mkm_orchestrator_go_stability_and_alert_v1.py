from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write_json(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def test_check_go_stability_detects_down_transition(tmp_path: Path) -> None:
    current = {
        "schema": "mkm_global_orchestrator_v1",
        "result": {"decision": "WATCH", "reason": "intermediate_signal"},
    }
    previous = {
        "schema": "mkm_global_orchestrator_v1",
        "result": {"decision": "GO", "reason": "high_confidence_and_direction"},
    }
    current_path = tmp_path / "current.json"
    previous_path = tmp_path / "previous.json"
    out_path = tmp_path / "stability.json"
    _write_json(current_path, current)
    _write_json(previous_path, previous)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "check_mkm_orchestrator_go_stability_v1.py"),
            "--current-json",
            str(current_path),
            "--previous-json",
            str(previous_path),
            "--output-json",
            str(out_path),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["transition"] == "GO->WATCH"
    assert doc["down_transition_detected"] is True
    assert doc["go_stable"] is False


def test_down_transition_alert_script_marks_alert_without_webhook(tmp_path: Path) -> None:
    stability = {
        "schema": "mkm_orchestrator_go_stability_v1",
        "current_decision": "WATCH",
        "previous_decision": "GO",
        "transition": "GO->WATCH",
        "down_transition_detected": True,
        "go_stable": False,
    }
    stability_path = tmp_path / "stability.json"
    out_path = tmp_path / "alert.json"
    _write_json(stability_path, stability)

    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "send_mkm_orchestrator_down_transition_alert_v1.py"),
            "--stability-json",
            str(stability_path),
            "--output-json",
            str(out_path),
            "--dry-run",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["should_alert"] is True
    assert doc["transition"] == "GO->WATCH"
    assert doc["webhook_sent"] is False
    assert doc["webhook_result"] == "dry_run"
