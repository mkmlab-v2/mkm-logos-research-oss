from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from mcp_server import _digest, create_server  # noqa: E402
from runtime import Privacy, RuntimeConfig, SecureAgentRuntime  # noqa: E402
from snapshot import SnapshotStore  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI snapshots only")


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "approved"
    root.mkdir()
    state = tmp_path / "state"
    runtime = SecureAgentRuntime(RuntimeConfig(
        approved_roots=[root],
        audit_log=state / "audit" / "actions.jsonl",
    ))
    broker = ApprovalBroker(state, protected_roots=[root])
    snapshots = SnapshotStore(state, protected_roots=[root])
    return runtime, broker, snapshots, root, state


def test_existing_file_snapshot_is_encrypted_and_restorable(env):
    _, _, snapshots, root, state = env
    target = root / "a.txt"
    target.write_bytes(b"before-value")
    snap = snapshots.capture(target)
    blob = (state / "snapshots" / f"{snap.snapshot_id}.bin").read_bytes()
    assert b"before-value" not in blob

    target.write_bytes(b"after-value")
    result = snapshots.restore(snap.snapshot_id)
    assert result["action"] == "RESTORE_BYTES"
    assert target.read_bytes() == b"before-value"
    assert result["after_sha256"] == hashlib.sha256(b"before-value").hexdigest()


def test_new_file_snapshot_restore_removes_created_file(env):
    _, _, snapshots, root, _ = env
    target = root / "new.txt"
    snap = snapshots.capture(target)
    assert snap.existed_before is False
    target.write_text("created", encoding="utf-8")
    result = snapshots.restore(snap.snapshot_id)
    assert result["action"] == "REMOVE_NEW_FILE"
    assert not target.exists()


@pytest.mark.anyio
async def test_mcp_approved_write_returns_snapshot_id_and_can_restore(env):
    runtime, broker, snapshots, root, _ = env
    target = root / "mcp.txt"
    target.write_text("before", encoding="utf-8")
    server = create_server(runtime, broker, snapshot_store=snapshots)

    content = "after"
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
    broker.approve(req["approval_id"])

    async with Client(server) as client:
        result = await client.call_tool(
            "execute_write_text",
            {
                "path": str(target),
                "content": content,
                "approval_id": req["approval_id"],
                "privacy": "INTERNAL",
            },
        )
    body = result.structured_content
    assert body["executed"] is True
    assert body["snapshot_id"].startswith("snap_")
    assert body["rollback"] == "LOCAL_CLI_ONLY"
    assert target.read_text(encoding="utf-8") == "after"

    snapshots.restore(body["snapshot_id"])
    assert target.read_text(encoding="utf-8") == "before"


@pytest.mark.anyio
async def test_runtime_status_reports_rollback_when_available(env):
    runtime, broker, snapshots, _, _ = env
    server = create_server(runtime, broker, snapshot_store=snapshots)
    async with Client(server) as client:
        result = await client.call_tool("runtime_status", {})
    assert result.structured_content["rollback"] == "LOCAL_DPAPI_SNAPSHOT_AVAILABLE"


@pytest.mark.anyio
async def test_write_over_one_mib_is_rejected_before_snapshot(env):
    runtime, broker, snapshots, root, state = env
    target = root / "large.txt"
    server = create_server(runtime, broker, snapshot_store=snapshots)
    oversized = "x" * (1024 * 1024 + 1)
    async with Client(server) as client:
        result = await client.call_tool(
            "request_write_text",
            {"path": str(target), "content": oversized},
        )
    assert result.is_error is True
    assert list((state / "snapshots").glob("snap_*.json")) == []
