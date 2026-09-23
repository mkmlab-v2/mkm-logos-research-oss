from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from cursor_agent_bridge import CursorAgentBridge, CursorAgentBridgeError  # noqa: E402
from mcp_server import create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402


class FakeSessionManager:
    def __init__(self, workspace: Path, user_data_dir: Path):
        self.workspace = workspace
        self.user_data_dir = user_data_dir

    def agent_context(self, session_id: str):
        assert session_id == "devsess_fixture"
        return {
            "session_id": session_id,
            "workspace_path": str(self.workspace),
            "user_data_dir": str(self.user_data_dir),
            "bound_window_pid": 4242,
            "window_ref": "ui_fixture",
        }


@dataclass
class FakeInstance:
    pid: int = 5000
    app_name: str = "Cursor"
    app_version: str = "3.17.19"
    user_data_dir: str = ""


class FakeBridge:
    def __init__(self, user_data_dir: Path):
        self.user_data_dir = str(user_data_dir)
        self.sent = []

    def session_instance(self, user_data_dir):
        assert str(user_data_dir) == self.user_data_dir
        return FakeInstance(user_data_dir=self.user_data_dir)

    def list_threads(self, user_data_dir):
        assert str(user_data_dir) == self.user_data_dir
        return [
            {
                "id": "thread-1",
                "title": "Synthetic worker",
                "source": "local",
                "status": "idle",
                "lastUpdatedAt": 10,
                "windowId": 7,
            },
            {
                "id": "thread-sensitive",
                "title": "contact user@example.com",
                "source": "local",
                "status": "idle",
                "lastUpdatedAt": 9,
                "windowId": 7,
            },
        ]

    def validate_prompt(self, text):
        from cursor_agent_bridge import CursorAgentBridge
        # Reuse the production policy without invoking discovery/CLI.
        return CursorAgentBridge(bridge_dir=Path(".")).validate_prompt(text)

    def send(self, user_data_dir, thread_id, text, force=False):
        assert force is False
        assert str(user_data_dir) == self.user_data_dir
        self.sent.append((thread_id, text))
        return {
            "status": "submitted",
            "threadId": thread_id,
            "windowId": 7,
            "threadTitle": "Synthetic worker",
        }


def _build(tmp_path: Path, bridge=None):
    workspace = tmp_path / "approved" / "repo"
    workspace.mkdir(parents=True)
    state = tmp_path / "state"
    user_data = state / "cursor-user-data"
    user_data.mkdir(parents=True)
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[tmp_path / "approved"],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[tmp_path / "approved"])
    manager = FakeSessionManager(workspace, user_data)
    bridge = bridge or FakeBridge(user_data)
    server = create_server(
        runtime,
        broker,
        session_manager=manager,
        cursor_agent_bridge=bridge,
    )
    return runtime, broker, manager, bridge, server


@pytest.mark.anyio
async def test_agent_status_established_for_exact_session(tmp_path: Path):
    _, _, _, _, server = _build(tmp_path)
    async with Client(server) as client:
        result = await client.call_tool(
            "cursor_agent_status", {"session_id": "devsess_fixture"}
        )
    body = result.structured_content
    assert body["bridge_state"] == "ESTABLISHED"
    assert body["bridge_pid"] == 5000
    assert body["user_data_dir_match"] is True
    assert body["send_gate"] == "HOLD"


@pytest.mark.anyio
async def test_thread_list_hides_sensitive_title(tmp_path: Path):
    _, _, _, _, server = _build(tmp_path)
    async with Client(server) as client:
        result = await client.call_tool(
            "cursor_agent_threads", {"session_id": "devsess_fixture"}
        )
    rows = {x["id"]: x for x in result.structured_content["threads"]}
    assert rows["thread-1"]["title"]["text"] == "Synthetic worker"
    assert rows["thread-sensitive"]["title"]["text"] == "[SENSITIVE_THREAD_TITLE]"
    assert rows["thread-sensitive"]["title"]["privacy_state"] == "PERSONAL"


@pytest.mark.anyio
async def test_request_agent_prompt_does_not_send_before_approval(tmp_path: Path):
    _, _, _, bridge, server = _build(tmp_path)
    async with Client(server) as client:
        req = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": "Update the synthetic function and stop before any git mutation.",
            },
        )
    body = req.structured_content
    assert body["status"] == "HUMAN_GATE"
    assert body["executed"] is False
    assert len(body["prompt_sha256"]) == 64
    assert bridge.sent == []


@pytest.mark.anyio
async def test_approved_exact_prompt_sends_once(tmp_path: Path):
    _, broker, _, bridge, server = _build(tmp_path)
    prompt = "Update the synthetic function and stop before any git mutation."
    async with Client(server) as client:
        req = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": prompt,
            },
        )
        broker.approve(req.structured_content["approval_id"])
        ex = await client.call_tool(
            "execute_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": prompt,
                "approval_id": req.structured_content["approval_id"],
            },
        )
    assert ex.structured_content["executed"] is True
    assert ex.structured_content["status"] == "submitted"
    assert bridge.sent == [("thread-1", prompt)]


@pytest.mark.anyio
async def test_prompt_change_cannot_reuse_approval(tmp_path: Path):
    _, broker, _, bridge, server = _build(tmp_path)
    prompt = "Change only app.py."
    async with Client(server) as client:
        req = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": prompt,
            },
        )
        broker.approve(req.structured_content["approval_id"])
        ex = await client.call_tool(
            "execute_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": "Change app.py and tests too.",
                "approval_id": req.structured_content["approval_id"],
            },
        )
    assert ex.is_error is True
    assert bridge.sent == []


@pytest.mark.anyio
async def test_wrong_thread_is_denied_before_approval(tmp_path: Path):
    _, _, _, bridge, server = _build(tmp_path)
    async with Client(server) as client:
        result = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "other-thread",
                "prompt": "Change only the synthetic fixture.",
            },
        )
    assert result.structured_content["status"] == "DENIED"
    assert result.structured_content["reason"] == "THREAD_NOT_EXACTLY_BOUND_TO_SESSION"
    assert bridge.sent == []


@pytest.mark.anyio
async def test_personal_prompt_is_denied(tmp_path: Path):
    _, _, _, bridge, server = _build(tmp_path)
    async with Client(server) as client:
        result = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": "Email user@example.com and update the fixture.",
            },
        )
    assert result.structured_content["status"] == "DENIED"
    assert result.structured_content["reason"] == "PROMPT_PRIVACY_PERSONAL"
    assert bridge.sent == []


@pytest.mark.anyio
async def test_git_push_directive_is_denied(tmp_path: Path):
    _, _, _, bridge, server = _build(tmp_path)
    async with Client(server) as client:
        result = await client.call_tool(
            "request_cursor_agent_prompt",
            {
                "session_id": "devsess_fixture",
                "thread_id": "thread-1",
                "prompt": "Fix the test and git push when done.",
            },
        )
    assert result.structured_content["status"] == "DENIED"
    assert result.structured_content["reason"] == "FORBIDDEN_ACTION_DIRECTIVE"
    assert bridge.sent == []


@pytest.mark.anyio
async def test_real_bridge_object_fails_closed_when_discovery_absent(tmp_path: Path):
    workspace = tmp_path / "approved" / "repo"
    workspace.mkdir(parents=True)
    state = tmp_path / "state"
    user_data = state / "cursor-user-data"
    user_data.mkdir(parents=True)
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[tmp_path / "approved"],
        audit_log=state / "audit.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[tmp_path / "approved"])
    manager = FakeSessionManager(workspace, user_data)
    bridge = CursorAgentBridge(bridge_dir=tmp_path / "missing-bridge")
    server = create_server(
        runtime,
        broker,
        session_manager=manager,
        cursor_agent_bridge=bridge,
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "cursor_agent_status", {"session_id": "devsess_fixture"}
        )
    body = result.structured_content
    assert body["bridge_state"] == "NOT_ESTABLISHED"
    assert body["reason"] == "CURSOR_DESKTOP_BRIDGE_NOT_ESTABLISHED"
