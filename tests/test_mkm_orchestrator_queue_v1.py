"""Smoke: todo_queue example validates and approve script imports."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_todo_queue_example_schema_version():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "artifacts" / "todo_queue_example_v1.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["schema_version"] == "todo_queue_v1"
    assert isinstance(data["tasks"], list)
    assert data["tasks"][0]["runner"]["path_rel"].endswith(".ps1")
    assert "noop_smoke" in data["tasks"][0]["runner"]["path_rel"]


def test_connection_spec_has_daily_runner_path():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "final" / "artifacts" / "mkm_orchestrator_connection_spec_v1.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    anchor = data["daily_runner_anchor"]["script_ps1"]
    assert "Invoke-MkmAiV2DailyReadiness.ps1" in anchor


def test_show_queue_status_example_queue_exits_zero():
    root = Path(__file__).resolve().parents[1]
    show = root / "scripts" / "show_mkm_orchestrator_queue_status_v1.py"
    example = root / "docs" / "final" / "artifacts" / "todo_queue_example_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(show),
            "--workspace-root",
            str(root),
            "--queue",
            str(example),
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "batch-approve would touch" in (r.stdout or "")


def test_batch_approve_marks_awaiting_and_pending_hitl(tmp_path):
    root = Path(__file__).resolve().parents[1]
    approve = root / "scripts" / "approve_mkm_orchestrator_task_v1.py"
    q = tmp_path / "q.json"
    py_noop = "scripts/mkm_orchestrator_noop_smoke_v1.py"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "tasks": [
                    {
                        "task_id": "high-pending",
                        "title": "H",
                        "sensitivity_level": "high",
                        "state": "pending",
                        "runner": {"kind": "python", "path_rel": py_noop},
                    },
                    {
                        "task_id": "awaiting-1",
                        "title": "A",
                        "sensitivity_level": "low",
                        "state": "awaiting_approval",
                        "runner": {"kind": "python", "path_rel": py_noop},
                        "approval": {"required": True, "idempotency_key": "a1"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(approve),
            "--queue",
            str(q),
            "--batch-approve",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    data = json.loads(q.read_text(encoding="utf-8"))
    for t in data["tasks"]:
        assert t.get("approval", {}).get("resolution") == "approved"
