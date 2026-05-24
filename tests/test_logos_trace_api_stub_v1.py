"""Logos trace API stub — deterministic preset match + path."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> TestClient:
    from scripts.logos_trace_api_stub_v1 import app

    return TestClient(app)


def test_health_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    doc = r.json()
    assert doc["ok"] is True
    assert doc["no_trade_signals"] is True
    assert doc.get("graph_nodes", 0) >= 10


def test_trace_theme_regime_preset(client: TestClient) -> None:
    r = client.post(
        "/v1/logos/trace",
        json={"preset_id": "p3_theme_regime"},
    )
    assert r.status_code == 200
    doc = r.json()
    assert doc["schema_version"] == "logos_trace_stub_v1"
    assert doc["boundary"]["gating_status"] == "NON_GATING"
    assert doc["matched"]["preset_id"] == "p3_theme_regime"
    path = doc["reasoning_path_v1"]
    assert path["schema_version"] == "logos_reasoning_path_v1"
    assert len(path["node_ids"]) >= 2


def test_trace_seed_ids(client: TestClient) -> None:
    r = client.post(
        "/v1/logos/trace",
        json={
            "seed_ids": ["theme::imperial_transition", "aramaic::Dan.2.10"],
            "max_path_nodes": 4,
        },
    )
    assert r.status_code == 200
    doc = r.json()
    assert doc["matched"]["match_type"] == "seed_ids"
    assert "theme::imperial_transition" in doc["reasoning_path_v1"]["node_ids"]
