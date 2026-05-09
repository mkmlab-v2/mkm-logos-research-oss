# -*- coding: utf-8 -*-
from fastapi.testclient import TestClient

from scripts.mkm_compose_api_stub import app


def _payload(query: str = "오늘 BTC 시장 분석") -> dict:
    return {
        "name": "commander",
        "query": query,
        "year": 2011,
        "month": 10,
        "day": 22,
        "hour": 15,
        "minute": 23,
        "second": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
        "annual_start_year": 2026,
        "annual_years": 2,
    }


def test_compose_market_contract_smoke():
    client = TestClient(app)
    r = client.post("/api/v1/mkm/compose", json=_payload())
    assert r.status_code == 200
    b = r.json()
    assert b["schema"] == "mkm_compose_response_v1"
    assert b["domain"] == "market"
    assert b["lens"]["logos"]["non_gating"] is True
    assert b["final_action"]["decision"] in {"HOLD", "WATCH", "GO"}


def test_compose_auth_guard(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("MKM_COMPOSE_API_KEYS", "k1")
    bad = client.post("/api/v1/mkm/compose", json=_payload())
    assert bad.status_code == 401
    ok = client.post("/api/v1/mkm/compose", json=_payload(), headers={"X-API-Key": "k1"})
    assert ok.status_code == 200

