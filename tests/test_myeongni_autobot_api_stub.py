# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient

from scripts.myeongni_autobot_api_stub import app


def _payload():
    return {
        "name": "commander",
        "year": 1973,
        "month": 12,
        "day": 10,
        "hour": 4,
        "minute": 30,
        "second": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
        "user_prompt": "오늘 명리 핵심",
        "annual_start_year": 2026,
        "annual_years": 2,
        "monthly_months_per_year": 1,
    }


def test_autobot_api_contract_smoke():
    client = TestClient(app)
    resp = client.post("/api/v1/myeongni/autobot", json=_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["schema"] == "myeongni_autobot_response_v1"
    assert "answer_markdown" in body and "자동 고도화 명리 답변" in body["answer_markdown"]
    assert body["report"]["pillars"]["day"] == "경진"


def test_autobot_api_requires_key_when_configured(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("MYEONGNI_AUTOBOT_API_KEYS", "abc123")
    bad = client.post("/api/v1/myeongni/autobot", json=_payload())
    assert bad.status_code == 401
    ok = client.post("/api/v1/myeongni/autobot", json=_payload(), headers={"X-API-Key": "abc123"})
    assert ok.status_code == 200


def test_autobot_api_rate_limit(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("MYEONGNI_AUTOBOT_API_KEYS", "")
    monkeypatch.setenv("MYEONGNI_AUTOBOT_RATE_LIMIT_RPM", "1")
    first = client.post("/api/v1/myeongni/autobot", json=_payload())
    assert first.status_code == 200
    second = client.post("/api/v1/myeongni/autobot", json=_payload())
    assert second.status_code == 429
    body = second.json()
    assert body["detail"]["code"] == "rate_limited"


def test_healthz_and_audit_log(tmp_path, monkeypatch):
    client = TestClient(app)
    log_path = tmp_path / "audit.jsonl"
    monkeypatch.setenv("MYEONGNI_AUTOBOT_AUDIT_LOG_PATH", str(log_path))
    monkeypatch.setenv("MYEONGNI_AUTOBOT_API_KEYS", "")
    monkeypatch.setenv("MYEONGNI_AUTOBOT_RATE_LIMIT_RPM", "0")

    h = client.get("/healthz")
    assert h.status_code == 200
    body = h.json()
    assert body["ok"] is True
    assert body["service"] == "myeongni_autobot_api_stub"

    r = client.post("/api/v1/myeongni/autobot", json=_payload())
    assert r.status_code == 200
    assert log_path.exists()
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1

