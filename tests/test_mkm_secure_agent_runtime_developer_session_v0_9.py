from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from developer_session import (  # noqa: E402
    CursorCLI,
    DeveloperSessionError,
    DeveloperSessionManager,
)
from mcp_server import create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows session semantics only")


class FakeRefs:
    def __init__(self):
        self.payloads = {}

    def resolve(self, ui_ref, expected_kind=None):
        return self.payloads[ui_ref]


class FakeDesktop:
    def __init__(self):
        self.ui_refs = FakeRefs()
        self.rows = []

    def list_windows(self, max_windows=100):
        return list(self.rows)


def _runtime(tmp_path: Path):
    approved = tmp_path / "approved"
    approved.mkdir()
    state = tmp_path / "state"
    config = RuntimeConfig(
        approved_roots=[approved],
        audit_log=state / "audit" / "actions.jsonl",
    )
    runtime = SecureAgentRuntime(config)
    broker = ApprovalBroker(state, protected_roots=[approved])
    desktop = FakeDesktop()
    manager = DeveloperSessionManager(config, state, desktop)
    return runtime, broker, manager, approved, state


def _fake_cli(tmp_path: Path) -> CursorCLI:
    exe = tmp_path / "Cursor.exe"
    cli = tmp_path / "cli.js"
    exe.write_bytes(b"fixture")
    cli.write_text("// fixture", encoding="utf-8")
    return CursorCLI(str(exe), str(cli), "fixture-1.0")


def test_prepare_creates_exact_workspace_mapping_outside_project(tmp_path: Path, monkeypatch):
    _, _, manager, approved, state = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    monkeypatch.setattr("developer_session.find_cursor_cli", lambda: _fake_cli(tmp_path))

    result = manager.prepare(workspace)
    session_dir = state / "developer_sessions" / result["session_id"]
    workspace_file = next(session_dir.glob("*.code-workspace"))
    payload = json.loads(workspace_file.read_text(encoding="utf-8"))

    assert payload["folders"] == [{"path": str(workspace.resolve())}]
    assert payload["settings"]["window.title"].startswith("MKM-WORKER-devsess_")
    assert result["status"] == "PREPARED_NOT_STARTED"
    assert len(result["workspace_file_sha256"]) == 64
    assert len(result["window_marker_sha256"]) == 64
    assert len(result["launch_argv_sha256"]) == 64
    assert not str(workspace).startswith(str(session_dir))


def test_prepare_rejects_workspace_outside_approved_roots(tmp_path: Path, monkeypatch):
    _, _, manager, _, _ = _runtime(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setattr("developer_session.find_cursor_cli", lambda: _fake_cli(tmp_path))
    with pytest.raises(DeveloperSessionError, match="outside approved roots"):
        manager.prepare(outside)


def test_start_sets_bound_only_after_matching_marker_and_pid(tmp_path: Path, monkeypatch):
    _, _, manager, approved, _ = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    monkeypatch.setattr("developer_session.find_cursor_cli", lambda: _fake_cli(tmp_path))
    prepared = manager.prepare(workspace)

    record = manager._load(prepared["session_id"])
    monkeypatch.setattr(manager, "_launch", lambda _r: None)
    monkeypatch.setattr(manager, "_matching_window", lambda _r: {
        "window_ref": "ui_fixture",
        "window_pid": 4242,
        "window_title_sha256": "a" * 64,
        "session_process_count": 3,
    })

    result = manager.start(prepared["session_id"], wait_seconds=5)
    assert result["binding_state"] == "BOUND_ESTABLISHED"
    assert result["bound_window_pid"] == 4242
    assert result["window_ref"] == "ui_fixture"
    stored = manager._load(prepared["session_id"])
    assert stored["status"] == "BOUND_ESTABLISHED"


def test_start_failure_is_fail_closed_and_marks_session(tmp_path: Path, monkeypatch):
    _, _, manager, approved, _ = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    monkeypatch.setattr("developer_session.find_cursor_cli", lambda: _fake_cli(tmp_path))
    prepared = manager.prepare(workspace)

    monkeypatch.setattr(manager, "_launch", lambda _r: None)
    monkeypatch.setattr(manager, "_matching_window", lambda _r: None)
    monkeypatch.setattr("developer_session.time.monotonic", iter([0.0, 10.0]).__next__)
    terminated = {"count": 0}
    monkeypatch.setattr(manager, "_terminate_session_processes", lambda _r: terminated.__setitem__("count", 1) or 1)

    with pytest.raises(DeveloperSessionError, match="binding not established"):
        manager.start(prepared["session_id"], wait_seconds=5)
    assert terminated["count"] == 1
    assert manager._load(prepared["session_id"])["status"] == "START_FAILED_NO_BOUND_WINDOW"


def test_verify_pid_change_becomes_stale_not_silent_rebind(tmp_path: Path, monkeypatch):
    _, _, manager, approved, _ = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    monkeypatch.setattr("developer_session.find_cursor_cli", lambda: _fake_cli(tmp_path))
    prepared = manager.prepare(workspace)
    record = manager._load(prepared["session_id"])
    record["status"] = "BOUND_ESTABLISHED"
    record["bound_window_pid"] = 100
    record["bound_window_title_sha256"] = "a" * 64
    manager._save(record)

    monkeypatch.setattr(manager, "_matching_window", lambda _r: {
        "window_ref": "ui_new",
        "window_pid": 101,
        "window_title_sha256": "a" * 64,
        "session_process_count": 2,
    })
    result = manager.verify(prepared["session_id"])
    assert result["binding_state"] == "BOUND_STALE_PID_CHANGED"
    assert manager._load(prepared["session_id"])["status"] == "BOUND_STALE"


class FakeSessionManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.started = 0
        self.closed = 0
        self.record = {
            "session_id": "devsess_fixture",
            "status": "PREPARED_NOT_STARTED",
            "workspace_path": str(workspace),
            "workspace_file_sha256": "1" * 64,
            "window_marker_sha256": "2" * 64,
            "launch_argv_sha256": "3" * 64,
            "cursor_version": "fixture",
            "repo": {"is_git": False, "repo_root": None, "head": None},
            "bound_window_pid": None,
            "created_at": "2026-09-24T00:00:00Z",
            "started_at": None,
            "verified_at": None,
            "closed_at": None,
        }

    def prepare(self, workspace_path):
        assert str(workspace_path) == str(self.workspace)
        return self._public(self.record)

    def _load(self, session_id):
        assert session_id == self.record["session_id"]
        return dict(self.record)

    def _public(self, record):
        return {
            "session_id": record["session_id"],
            "status": record["status"],
            "binding_state": record["status"],
            "workspace_path": record["workspace_path"],
            "workspace_file_sha256": record["workspace_file_sha256"],
            "window_marker_sha256": record["window_marker_sha256"],
            "launch_argv_sha256": record["launch_argv_sha256"],
            "cursor_version": record["cursor_version"],
            "repo": record["repo"],
            "bound_window_pid": record["bound_window_pid"],
            "created_at": record["created_at"],
            "started_at": record["started_at"],
            "verified_at": record["verified_at"],
            "closed_at": record["closed_at"],
            "send_gate": "HOLD",
        }

    def start(self, session_id, wait_seconds=20):
        self.started += 1
        self.record["status"] = "BOUND_ESTABLISHED"
        self.record["bound_window_pid"] = 999
        result = self._public(self.record)
        result["window_ref"] = "ui_bound"
        result["session_process_count"] = 2
        return result

    def verify(self, session_id):
        result = self._public(self.record)
        result["binding_state"] = "BOUND_ESTABLISHED"
        result["window_ref"] = "ui_bound"
        result["session_process_count"] = 2
        return result

    def close(self, session_id):
        self.closed += 1
        self.record["status"] = "CLOSED_PROCESS_ONLY"
        result = self._public(self.record)
        result["terminated_process_count"] = 2
        result["session_state_retained"] = True
        result["user_data_deleted"] = False
        return result


@pytest.mark.anyio
async def test_mcp_session_start_requires_exact_local_approval(tmp_path: Path):
    runtime, broker, _manager, approved, _ = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    fake = FakeSessionManager(workspace)
    server = create_server(runtime, broker, session_manager=fake)

    async with Client(server) as client:
        req = await client.call_tool(
            "request_dev_session_start",
            {"workspace_path": str(workspace), "wait_seconds": 20},
        )
        body = req.structured_content
        assert body["approval_status"] == "HUMAN_GATE"
        assert fake.started == 0

        broker.approve(body["approval_id"])
        wrong = await client.call_tool(
            "execute_dev_session_start",
            {
                "session_id": body["session_id"],
                "approval_id": body["approval_id"],
                "wait_seconds": 21,
            },
        )
        assert wrong.is_error is True
        assert fake.started == 0


@pytest.mark.anyio
async def test_mcp_session_start_and_close_after_approval(tmp_path: Path):
    runtime, broker, _manager, approved, _ = _runtime(tmp_path)
    workspace = approved / "repo"
    workspace.mkdir()
    fake = FakeSessionManager(workspace)
    server = create_server(runtime, broker, session_manager=fake)

    async with Client(server) as client:
        req = await client.call_tool(
            "request_dev_session_start",
            {"workspace_path": str(workspace), "wait_seconds": 20},
        )
        broker.approve(req.structured_content["approval_id"])
        started = await client.call_tool(
            "execute_dev_session_start",
            {
                "session_id": req.structured_content["session_id"],
                "approval_id": req.structured_content["approval_id"],
                "wait_seconds": 20,
            },
        )
        assert started.structured_content["binding_state"] == "BOUND_ESTABLISHED"
        assert fake.started == 1

        close_req = await client.call_tool(
            "request_dev_session_close",
            {"session_id": req.structured_content["session_id"]},
        )
        assert fake.closed == 0
        broker.approve(close_req.structured_content["approval_id"])
        closed = await client.call_tool(
            "execute_dev_session_close",
            {
                "session_id": req.structured_content["session_id"],
                "approval_id": close_req.structured_content["approval_id"],
            },
        )
        assert closed.structured_content["status"] == "CLOSED_PROCESS_ONLY"
        assert fake.closed == 1
        assert closed.structured_content["user_data_deleted"] is False
