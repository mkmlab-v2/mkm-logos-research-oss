"""Smoke tests for QuBICS HTTP ingest on ai_smartfarm_api_stub."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.ai_smartfarm_api_stub import app

FIXTURE = Path(__file__).resolve().parents[1] / "docs/final/artifacts/fixtures/qubics_coconet_sensor_post_v1.json"


def test_qubics_root_post_returns_ack() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["dt"] = int(datetime.now(UTC).timestamp())
    client = TestClient(app)
    resp = client.post("/", json=raw)
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"cid": raw["cid"], "result": "ok"}


def test_qubics_named_ingest_returns_normalized() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["dt"] = int(datetime.now(UTC).timestamp())
    client = TestClient(app)
    resp = client.post("/v1/vendor/qubics/ingest", json=raw)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ack"]["result"] == "ok"
    assert body["normalized"]["message_type"] == "telemetry_ingest"


def test_qubics_ingest_resolves_zone_from_manifest(monkeypatch) -> None:
    manifest = Path(__file__).resolve().parents[1] / "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json"
    monkeypatch.setenv("SMARTFARM_QUBICS_DEVICE_MANIFEST", str(manifest))
    raw = {
        "cid": "CID302TEST",
        "gw": "G300",
        "type": "erth_th_mtr",
        "nm": "D302",
        "dt": int(datetime.now(UTC).timestamp()),
        "ertht": 24.0,
        "erthh": 35.0,
    }
    client = TestClient(app)
    resp = client.post("/v1/vendor/qubics/ingest", json=raw)
    assert resp.status_code == 200
    zone_id = resp.json()["normalized"]["payload"]["zone_id"]
    assert zone_id == "zone_02"
