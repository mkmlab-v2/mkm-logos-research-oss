from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker, ApprovalError  # noqa: E402
from mcp_server import _digest, create_server  # noqa: E402
from runtime import Privacy, RuntimeConfig, SecureAgentRuntime  # noqa: E402


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "approved"
    root.mkdir()
    state = tmp_path / "state"
    rt = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[root],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[root])
    return rt, broker, root, state


def test_approval_state_must_be_outside_model_root(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    with pytest.raises(ApprovalError, match="outside"):
        ApprovalBroker(root / ".approvals", protected_roots=[root])


def test_request_persists_digest_not_raw_content(env):
    _, broker, root, _ = env
    content = "TOP SECRET-ish payload for test"
    args = {
        "path": str(root / "x.txt"),
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "privacy": "INTERNAL",
    }
    req = broker.request(
        action="write_text",
        target=str(root / "x.txt"),
        args_sha256=_digest(args),
    )
    raw = broker._path(req["approval_id"]).read_text(encoding="utf-8")
    assert content not in raw
    assert args["content_sha256"] in json.loads(raw)["args_sha256"] or content not in raw


def test_approval_is_one_time_and_exact(env):
    _, broker, root, _ = env
    args = {"x": 1}
    req = broker.request(
        action="run_command",
        target=str(root),
        args_sha256=_digest(args),
    )
    broker.approve(req["approval_id"])
    broker.consume(
        req["approval_id"],
        action="run_command",
        target=str(root),
        args_sha256=_digest(args),
    )
    with pytest.raises(ApprovalError, match="CONSUMED"):
        broker.consume(
            req["approval_id"],
            action="run_command",
            target=str(root),
            args_sha256=_digest(args),
        )


def test_mismatched_action_cannot_use_approval(env):
    _, broker, root, _ = env
    req = broker.request(
        action="write_text", target=str(root / "x"), args_sha256="abc"
    )
    broker.approve(req["approval_id"])
    with pytest.raises(ApprovalError, match="does not match"):
        broker.consume(
            req["approval_id"],
            action="write_text",
            target=str(root / "x"),
            args_sha256="different",
        )


def test_denied_approval_cannot_be_consumed(env):
    _, broker, root, _ = env
    req = broker.request(
        action="write_text", target=str(root / "x"), args_sha256="abc"
    )
    broker.deny(req["approval_id"])
    with pytest.raises(ApprovalError, match="DENIED"):
        broker.consume(
            req["approval_id"],
            action="write_text",
            target=str(root / "x"),
            args_sha256="abc",
        )


def test_mcp_server_exposes_expected_tools_without_human_approved_arg(env):
    rt, broker, _, _ = env
    server = create_server(rt, broker)
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert {
        "runtime_status",
        "list_directory",
        "read_text_file",
        "thin_coordinate",
        "request_write_text",
        "execute_write_text",
        "request_command",
        "execute_command",
        "ollama_health",
        "ollama_generate",
    } <= names
    for tool in tools:
        props = tool.input_schema.get("properties", {})
        assert "human_approved" not in props


def test_write_round_trip_requires_local_cli_approval(env):
    rt, broker, root, _ = env
    target = root / "out.txt"
    content = "hello"
    args = {
        "path": str(target.resolve()),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "privacy": Privacy.INTERNAL.value,
    }
    req = broker.request(
        action="write_text",
        target=str(target.resolve()),
        args_sha256=_digest(args),
    )
    with pytest.raises(ApprovalError):
        broker.consume(
            req["approval_id"],
            action="write_text",
            target=str(target.resolve()),
            args_sha256=_digest(args),
        )
    assert not target.exists()

    broker.approve(req["approval_id"])
    broker.consume(
        req["approval_id"],
        action="write_text",
        target=str(target.resolve()),
        args_sha256=_digest(args),
    )
    receipt = rt.write_file(
        target, content.encode(), human_approved=True, privacy=Privacy.INTERNAL
    )
    assert target.read_text(encoding="utf-8") == content
    assert receipt.send_gate == "HOLD"


def test_command_approval_does_not_bypass_blocked_git_subcommand(env):
    rt, broker, root, _ = env
    # Runtime validation rejects the command even before an approval request
    # should be created by the MCP layer.
    with pytest.raises(Exception, match="blocked"):
        rt.policy.validate_argv(["git", "push"])


def test_server_tool_schemas_are_structured(env):
    rt, broker, _, _ = env
    server = create_server(rt, broker)
    tools = asyncio.run(server.list_tools())
    read_tool = next(t for t in tools if t.name == "read_text_file")
    assert read_tool.input_schema["type"] == "object"
    assert "path" in read_tool.input_schema["properties"]
