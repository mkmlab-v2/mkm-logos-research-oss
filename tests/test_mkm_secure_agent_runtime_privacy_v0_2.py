from __future__ import annotations

from pathlib import Path
import sys

import pytest
from mcp import Client

ROOT = Path(__file__).parents[1]
PKG = ROOT / "experiments" / "mkm_secure_agent_runtime_v0"
sys.path.insert(0, str(PKG))

from approval import ApprovalBroker  # noqa: E402
from mcp_server import create_server  # noqa: E402
from privacy import redact_text, scan_text  # noqa: E402
from runtime import RuntimeConfig, SecureAgentRuntime  # noqa: E402


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
    return runtime, broker, root


def test_secret_signal_is_denied():
    text = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----"
    result = scan_text(text)
    assert result.state == "SECRET"
    assert result.release_decision == "DENY"
    assert result.signal_counts["PRIVATE_KEY"] == 1


def test_medical_context_plus_direct_identifier_is_phi_hold():
    text = "환자 진료기록 010-1234-5678 통증 호소"
    result = scan_text(text)
    assert result.state == "PHI"
    assert result.release_decision == "HOLD"
    assert result.medical_context is True
    assert result.manual_review_required is True


def test_personal_identifier_without_medical_context_is_personal_hold():
    result = scan_text("contact me at user@example.com")
    assert result.state == "PERSONAL"
    assert result.release_decision == "HOLD"


def test_clean_internal_text_is_allowed():
    result = scan_text("build report for local fixture")
    assert result.state == "INTERNAL"
    assert result.release_decision == "ALLOW"


def test_redaction_replaces_direct_identifiers_but_does_not_claim_name_detection():
    redacted, result = redact_text(
        "환자 010-1234-5678 email user@example.com"
    )
    assert "010-1234-5678" not in redacted
    assert "user@example.com" not in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "PERSON_NAME_DETECTION_NOT_ESTABLISHED" in result.limitations


@pytest.mark.anyio
async def test_mcp_read_blocks_secret_body(env):
    runtime, broker, root = env
    path = root / "secret.txt"
    path.write_text("password=supersecretvalue", encoding="utf-8")
    server = create_server(runtime, broker)
    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(path)})
    body = result.structured_content
    assert body["blocked"] is True
    assert body["text"] is None
    assert body["privacy_state"] == "SECRET"
    assert body["release_decision"] == "DENY"


@pytest.mark.anyio
async def test_mcp_read_blocks_phi_body(env):
    runtime, broker, root = env
    path = root / "chart.txt"
    path.write_text("환자 진료기록 010-1234-5678 요통", encoding="utf-8")
    server = create_server(runtime, broker)
    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(path)})
    body = result.structured_content
    assert body["blocked"] is True
    assert body["text"] is None
    assert body["privacy_state"] == "PHI"
    assert body["release_decision"] == "HOLD"


@pytest.mark.anyio
async def test_mcp_read_returns_clean_internal_text(env):
    runtime, broker, root = env
    path = root / "safe.txt"
    path.write_text("deterministic local fixture", encoding="utf-8")
    server = create_server(runtime, broker)
    async with Client(server) as client:
        result = await client.call_tool("read_text_file", {"path": str(path)})
    body = result.structured_content
    assert body["blocked"] is False
    assert body["text"] == "deterministic local fixture"
    assert body["privacy_state"] == "INTERNAL"


@pytest.mark.anyio
async def test_privacy_scan_file_returns_metadata_only(env):
    runtime, broker, root = env
    path = root / "mixed.txt"
    path.write_text("환자 010-1111-2222 진료", encoding="utf-8")
    server = create_server(runtime, broker)
    async with Client(server) as client:
        result = await client.call_tool("privacy_scan_file", {"path": str(path)})
    body = result.structured_content
    assert body["privacy_state"] == "PHI"
    assert body["release_decision"] == "HOLD"
    assert "text" not in body
    assert body["signal_counts"]["KOREAN_MOBILE_PHONE"] == 1
