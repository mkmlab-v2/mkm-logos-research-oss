"""Track C bridge → todo_queue_v1 merge contract (dry-run CLI)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_apply_trackc_bridge_dry_run_matches_todo_queue_v1_schema():
    jsonschema = pytest.importorskip("jsonschema")
    root = _root()
    schema = json.loads(
        (root / "docs" / "final" / "schemas" / "todo_queue_v1.schema.json").read_text(encoding="utf-8")
    )
    r = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "apply_trackc_plan_bridge_to_queue_v1.py"),
            "--workspace-root",
            str(root),
            "--dry-run",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    doc = json.loads(r.stdout)
    assert doc.get("schema_version") == "todo_queue_v1"
    assert isinstance(doc.get("tasks"), list)
    for t in doc["tasks"]:
        assert "plan_ref" not in t
        assert "plan_note" not in t
        assert t.get("task_id")
    jsonschema.Draft7Validator(schema).validate(doc)


def test_trackc_bridge_json_schema_version():
    root = _root()
    p = root / "docs" / "final" / "artifacts" / "mkm_trackc_plan_orchestrator_bridge_v1.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "mkm_trackc_plan_orchestrator_bridge_v1"
    assert isinstance(data.get("tasks"), list)


def test_apply_trackc_bridge_merge_existing_preserves_done_state(tmp_path):
    root = _root()
    q = tmp_path / "queue.json"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "generated_at_utc": "2026-05-02T00:00:00Z",
                "tasks": [
                    {
                        "task_id": "tc-plan-gates-smoke",
                        "title": "x",
                        "sensitivity_level": "low",
                        "state": "done",
                        "runner": {"kind": "python", "path_rel": "scripts/run_trackc_plan_gates_smoke_v1.py"},
                        "last_run": {"exit_code": 0},
                    },
                    {
                        "task_id": "manual-extra-task",
                        "title": "manual",
                        "sensitivity_level": "low",
                        "state": "pending",
                        "runner": {"kind": "python", "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py"},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(root / "scripts" / "apply_trackc_plan_bridge_to_queue_v1.py"),
            "--workspace-root",
            str(root),
            "--output",
            str(q),
            "--merge-existing",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, (r.stdout, r.stderr)
    doc = json.loads(q.read_text(encoding="utf-8"))
    by_id = {t.get("task_id"): t for t in doc.get("tasks", [])}
    assert by_id["tc-plan-gates-smoke"]["state"] == "done"
    assert by_id["tc-plan-gates-smoke"].get("last_run", {}).get("exit_code") == 0
    assert "manual-extra-task" in by_id
