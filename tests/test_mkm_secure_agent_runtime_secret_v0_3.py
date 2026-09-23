from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from mcp_server import create_server  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402
from secrets_dpapi import DPAPISecretStore, SecretStoreError  # noqa: E402


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI only")


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
    store = DPAPISecretStore(state)
    return runtime, broker, store, root, state


def test_dpapi_round_trip_and_plaintext_not_persisted(env):
    _, _, store, _, state = env
    secret = b"correct-horse-battery-staple"
    meta = store.set_secret(
        "secret://test/service",
        secret,
        service="fixture",
        label="test only",
    )
    files = list((state / "secrets").glob("*.json"))
    assert len(files) == 1
    raw = files[0].read_bytes()
    assert secret not in raw
    assert b"correct-horse" not in raw
    assert meta.provider == "WINDOWS_DPAPI_CURRENT_USER"

    material = store.materialize_for_local_consumer("secret://test/service")
    try:
        assert bytes(material) == secret
    finally:
        store.wipe(material)
    assert all(v == 0 for v in material)


def test_metadata_never_contains_ciphertext_or_secret(env):
    _, _, store, _, _ = env
    store.set_secret(
        "secret://github/main",
        b"ghp_fixture_not_real",
        service="github",
        label="main",
    )
    meta = store.metadata("secret://github/main")
    payload = meta.__dict__
    assert "ciphertext_b64" not in payload
    assert "secret" not in payload
    assert payload["secret_material_exposed"] is False


def test_verify_returns_digest_not_secret(env):
    _, _, store, _, _ = env
    store.set_secret(
        "secret://verify/me",
        b"verification-material",
        service="fixture",
    )
    result = store.verify("secret://verify/me")
    assert result["ok"] is True
    assert result["bytes"] == len(b"verification-material")
    assert len(result["sha256"]) == 64
    assert result["secret_material_exposed"] is False


def test_remove_is_local_store_operation(env):
    _, _, store, _, state = env
    store.set_secret(
        "secret://remove/me",
        b"remove-material",
        service="fixture",
    )
    assert store.remove("secret://remove/me") is True
    assert store.remove("secret://remove/me") is False
    assert list((state / "secrets").glob("*.json")) == []


@pytest.mark.anyio
async def test_mcp_secret_handle_info_is_metadata_only(env):
    runtime, broker, store, _, _ = env
    store.set_secret(
        "secret://github/main",
        b"not-exposed-value",
        service="github",
        label="main credential",
    )
    server = create_server(runtime, broker, secret_store=store)
    async with Client(server) as client:
        result = await client.call_tool(
            "secret_handle_info", {"handle": "secret://github/main"}
        )
        status = await client.call_tool("runtime_status", {})
    body = result.structured_content
    assert body["available"] is True
    assert body["handle"] == "secret://github/main"
    assert body["service"] == "github"
    assert body["secret_material_exposed"] is False
    assert "ciphertext" not in json.dumps(body).lower()
    assert "not-exposed-value" not in json.dumps(body)
    assert status.structured_content["secret_material_access"] == "LOCAL_DPAPI_METADATA_ONLY"


@pytest.mark.anyio
async def test_mcp_unknown_secret_handle_does_not_leak_path(env):
    runtime, broker, store, _, state = env
    server = create_server(runtime, broker, secret_store=store)
    async with Client(server) as client:
        result = await client.call_tool(
            "secret_handle_info", {"handle": "secret://missing/value"}
        )
    body = result.structured_content
    assert body["available"] is False
    assert body["secret_material_exposed"] is False
    assert str(state) not in json.dumps(body)
