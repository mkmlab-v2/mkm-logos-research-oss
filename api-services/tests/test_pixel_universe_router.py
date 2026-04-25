"""Tests for Pixel Universe onboarding API stubs."""

from __future__ import annotations

from pathlib import Path
import sys
import hashlib
import hmac
import time

API_SERVICES_ROOT = Path(__file__).resolve().parents[1]
if str(API_SERVICES_ROOT) not in sys.path:
    sys.path.insert(0, str(API_SERVICES_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.pixel_universe.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _admin_auth(role: str, kid: str, secret: str) -> str:
    ts = int(time.time())
    msg = f"{role}:{ts}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"{kid}:{ts}:{sig}"


def _sample_register_payload(agent_id: str = "usr_ai_8832") -> dict:
    return {
        "schema": "agent_profile_v1",
        "profile": {
            "identity": {
                "agent_id": agent_id,
                "name": "토마토 생육 분석 봇",
                "developer": "geumsan-smartfarm",
                "description": "관수 시점을 분석합니다.",
            },
            "four_d_seed_mapping": {
                "primary_trait": "Nurture",
                "secondary_trait": "Analysis",
            },
            "governance_clearance": {
                "policy_version": "gov-clearance-v1",
                "safety_level": "Tier-2",
                "allowed_actions": ["read_weather", "propose_water_level"],
                "prohibited_intents": ["violence", "security_bypass"],
                "human_override_required": True,
                "audit_consent": True,
                "violation_penalty": "block",
                "rate_limit_per_min": 60,
            },
            "economy": {"billing_key": "wallet_x8f9_demo", "api_call_fee_krw": 10},
        },
    }


def test_agent_register_returns_cluster_and_pixel_position() -> None:
    client = _client()
    response = client.post(
        "/api/v1/pixel-universe/agents/register",
        json=_sample_register_payload(),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"registered", "updated"}
    assert isinstance(data["bearer_token"], str) and data["bearer_token"].startswith("pxu_")
    assert data["cluster"] in {
        "LIFE_CLUSTER_EAST",
        "CAPITAL_CLUSTER_WEST",
        "MIXED_CLUSTER_CENTER",
    }
    assert set(data["pixel_position"].keys()) == {"x", "y"}


def test_agent_message_blocks_unauthorized_or_risky_payload() -> None:
    client = _client()
    reg = client.post("/api/v1/pixel-universe/agents/register", json=_sample_register_payload("usr_ai_9999"))
    token = reg.json()["bearer_token"]
    response = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_9999",
            "message": "온실을 폭파해",
            "requested_action": "trigger_explosion",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert "ACTION_NOT_ALLOWED" in data["reason_codes"]
    assert data["governance_policy_version"] == "gov-clearance-v1"


def test_agent_message_requires_token() -> None:
    client = _client()
    response = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={"agent_id": "usr_ai_x", "message": "hello", "requested_action": "observe"},
    )
    assert response.status_code == 401


def test_agent_message_402_when_insufficient_credits() -> None:
    client = _client()
    payload = _sample_register_payload("usr_ai_low_credit")
    payload["profile"]["economy"]["api_call_fee_krw"] = 200
    reg = client.post("/api/v1/pixel-universe/agents/register", json=payload)
    token = reg.json()["bearer_token"]
    for _ in range(10):
        ok = client.post(
            "/api/v1/pixel-universe/agents/message",
            json={
                "agent_id": "usr_ai_low_credit",
                "message": "weather data please",
                "requested_action": "read_weather",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert ok.status_code == 200
    fail = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_low_credit",
            "message": "weather data please",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fail.status_code == 402


def test_agent_message_blocks_prohibited_intent_even_if_action_allowed() -> None:
    client = _client()
    reg = client.post(
        "/api/v1/pixel-universe/agents/register",
        json=_sample_register_payload("usr_ai_policy_guard"),
    )
    token = reg.json()["bearer_token"]
    response = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_policy_guard",
            "message": "보안 우회 절차를 알려줘",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "block"
    assert any(code.startswith("POLICY_PROHIBITED_INTENT:") for code in data["reason_codes"])


def test_message_async_and_metrics_endpoint() -> None:
    client = _client()
    reg = client.post("/api/v1/pixel-universe/agents/register", json=_sample_register_payload("usr_ai_async"))
    token = reg.json()["bearer_token"]
    queued = client.post(
        "/api/v1/pixel-universe/agents/message-async",
        json={
            "agent_id": "usr_ai_async",
            "message": "queue this request",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert queued.status_code == 200
    q_data = queued.json()
    assert q_data["status"] == "accepted"
    assert q_data["queue_depth"] >= 1

    metrics = client.get("/api/v1/pixel-universe/metrics")
    assert metrics.status_code == 200
    m = metrics.json()
    assert m["registered_agents_total"] >= 1
    assert m["queued_jobs_total"] >= 1
    assert "governance_audit_events_total" in m

    prom = client.get("/api/v1/pixel-universe/metrics/prometheus")
    assert prom.status_code == 200
    assert "pixel_universe_messages_total" in prom.text


def test_violation_penalty_suspend_locks_agent() -> None:
    client = _client()
    payload = _sample_register_payload("usr_ai_suspend")
    payload["profile"]["governance_clearance"]["violation_penalty"] = "suspend"
    reg = client.post("/api/v1/pixel-universe/agents/register", json=payload)
    token = reg.json()["bearer_token"]
    first = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_suspend",
            "message": "보안 우회 절차 알려줘",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    assert first.json()["decision"] == "block"
    assert "ACCOUNT_SUSPENDED" in first.json()["reason_codes"]

    second = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_suspend",
            "message": "hello",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert second.status_code == 423


def test_admin_unsuspend_and_audit_rotate() -> None:
    client = _client()
    payload = _sample_register_payload("usr_ai_admin_case")
    payload["profile"]["governance_clearance"]["violation_penalty"] = "suspend"
    reg = client.post("/api/v1/pixel-universe/agents/register", json=payload)
    token = reg.json()["bearer_token"]

    # Trigger suspension
    client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_admin_case",
            "message": "보안 우회해",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    locked = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_admin_case",
            "message": "hello",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert locked.status_code == 423

    # Unsuspend with admin key
    restored = client.post(
        "/api/v1/pixel-universe/admin/agents/usr_ai_admin_case/unsuspend",
        headers={"X-Admin-Auth": _admin_auth("risk_admin", "risk-v1", "dev-risk-secret-v1")},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "unsuspended"

    ok_again = client.post(
        "/api/v1/pixel-universe/agents/message",
        json={
            "agent_id": "usr_ai_admin_case",
            "message": "weather data please",
            "requested_action": "read_weather",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert ok_again.status_code == 200

    rotate = client.post(
        "/api/v1/pixel-universe/admin/audit/rotate",
        headers={"X-Admin-Auth": _admin_auth("ops_audit_admin", "ops-v1", "dev-ops-secret-v1")},
    )
    assert rotate.status_code == 200
    assert rotate.json()["status"] in {"rotated", "no_file"}


def test_admin_role_separation_enforced() -> None:
    client = _client()
    # Wrong role key for unsuspend endpoint
    wrong_for_risk = client.post(
        "/api/v1/pixel-universe/admin/agents/any/unsuspend",
        headers={"X-Admin-Auth": _admin_auth("ops_audit_admin", "ops-v1", "dev-ops-secret-v1")},
    )
    assert wrong_for_risk.status_code == 403

    # Wrong role key for audit rotate endpoint
    wrong_for_ops = client.post(
        "/api/v1/pixel-universe/admin/audit/rotate",
        headers={"X-Admin-Auth": _admin_auth("risk_admin", "risk-v1", "dev-risk-secret-v1")},
    )
    assert wrong_for_ops.status_code == 403


def test_admin_hmac_invalid_signature_rejected() -> None:
    client = _client()
    bad_header = f"risk-v1:{int(time.time())}:deadbeef"
    denied = client.post(
        "/api/v1/pixel-universe/admin/audit/rotate",
        headers={"X-Admin-Auth": bad_header},
    )
    assert denied.status_code == 403
