"""Smoke: orchestrator poll dry-run exits 0 on example queue (no network)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_poll_dry_run_example_queue():
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    example = root / "docs" / "final" / "artifacts" / "todo_queue_example_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(example),
            "--dry-run",
            "--skip-lock",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_bootstrap_script_exists():
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts" / "bootstrap_mkm_orchestrator_queue_v1.ps1").is_file()


def test_poll_dry_run_smoke_first_python_queue():
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    q = root / "docs" / "final" / "artifacts" / "todo_queue_smoke_first_python_v1.json"
    r = subprocess.run(
        [
            sys.executable,
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(q),
            "--dry-run",
            "--skip-lock",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_poll_dry_run_skips_hitl_then_runs_next_task(tmp_path):
    """HITL promotion does not consume --max-tasks; low-friction task still runs same poll."""
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    q = tmp_path / "queue.json"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "tasks": [
                    {
                        "task_id": "hitl-first",
                        "title": "needs human",
                        "sensitivity_level": "high",
                        "state": "pending",
                        "runner": {
                            "kind": "python",
                            "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py",
                        },
                        "approval": {"required": False},
                    },
                    {
                        "task_id": "auto-second",
                        "title": "runs without approval",
                        "sensitivity_level": "low",
                        "state": "pending",
                        "runner": {
                            "kind": "python",
                            "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py",
                        },
                        "approval": {"required": False},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(q),
            "--dry-run",
            "--skip-lock",
            "--skip-heavy",
            "--max-tasks",
            "1",
            "--no-approval-snapshot",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    out = (r.stdout or "") + (r.stderr or "")
    assert "hitl-first" in out or "HITL" in out
    assert "auto-second" in out


def test_noop_python_script_exits_zero():
    root = Path(__file__).resolve().parents[1]
    noop = root / "scripts" / "mkm_orchestrator_noop_smoke_v1.py"
    r = subprocess.run(
        [sys.executable, str(noop)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr + r.stdout


def test_poll_skips_heavy_by_default(tmp_path):
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    q = tmp_path / "queue.json"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "tasks": [
                    {
                        "task_id": "heavy-1",
                        "title": "H",
                        "runtime_class": "heavy",
                        "sensitivity_level": "low",
                        "state": "pending",
                        "runner": {"kind": "python", "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py"},
                    },
                    {
                        "task_id": "quick-1",
                        "title": "Q",
                        "runtime_class": "quick",
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
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(q),
            "--skip-lock",
            "--skip-heavy",
            "--max-tasks",
            "1",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(q.read_text(encoding="utf-8"))
    by_id = {t.get("task_id"): t for t in doc.get("tasks", [])}
    assert by_id["heavy-1"]["state"] == "pending"
    assert by_id["quick-1"]["state"] == "done"


def test_heavy_auto_cursor_without_args_falls_back_to_runner(tmp_path):
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    q = tmp_path / "queue.json"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "tasks": [
                    {
                        "task_id": "heavy-fallback",
                        "title": "HF",
                        "runtime_class": "heavy",
                        "sensitivity_level": "low",
                        "state": "pending",
                        "runner": {
                            "kind": "python",
                            "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py",
                            "use_cursor_cli_auto": True,
                            "cursor_cli_args": [],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(q),
            "--skip-lock",
            "--heavy-only",
            "--max-tasks",
            "1",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(q.read_text(encoding="utf-8"))
    assert doc["tasks"][0]["state"] == "done"


def test_heavy_auto_cursor_failure_retries_once_with_original_runner(tmp_path):
    root = Path(__file__).resolve().parents[1]
    poll = root / "scripts" / "mkm_orchestrator_poll_v1.py"
    q = tmp_path / "queue.json"
    q.write_text(
        json.dumps(
            {
                "schema_version": "todo_queue_v1",
                "tasks": [
                    {
                        "task_id": "heavy-auto-fallback",
                        "title": "HF2",
                        "runtime_class": "heavy",
                        "sensitivity_level": "low",
                        "state": "pending",
                        "runner": {
                            "kind": "python",
                            "path_rel": "scripts/mkm_orchestrator_noop_smoke_v1.py",
                            "use_cursor_cli_auto": True,
                            "cursor_cli_args": ["--definitely-invalid-flag"],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            str(poll),
            "--workspace-root",
            str(root),
            "--queue",
            str(q),
            "--skip-lock",
            "--heavy-only",
            "--max-tasks",
            "1",
        ],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(q.read_text(encoding="utf-8"))
    assert doc["tasks"][0]["state"] == "done"
