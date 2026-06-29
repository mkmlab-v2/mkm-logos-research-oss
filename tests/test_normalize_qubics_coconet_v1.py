"""Tests for normalize_qubics_coconet_v1."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.normalize_qubics_coconet_v1 import (
    normalize_qubics_coconet,
    qubics_ack_body,
)

FIXTURE = Path(__file__).resolve().parents[1] / "docs/final/artifacts/fixtures/qubics_coconet_sensor_post_v1.json"


def test_qubics_ack_requires_cid() -> None:
    assert qubics_ack_body({"cid": "2436009"}) == {"cid": "2436009", "result": "ok"}
    with pytest.raises(ValueError):
        qubics_ack_body({})


def test_normalize_qubics_from_fixture() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw["dt"] = int(datetime.now(UTC).timestamp())
    out = normalize_qubics_coconet(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
        comm_ok_max_age_sec=900,
    )
    p = out["payload"]
    assert out["message_type"] == "telemetry_ingest"
    assert p["soil_moisture_pct"] == pytest.approx(28.5)
    assert p["soil_temp_c"] == pytest.approx(22.1)
    assert p["soil_ec_us_cm"] == 0.0
    assert out["vendor_meta"]["ec_from_device"] is False
    assert out["vendor_meta"]["cid"] == "2436009"


def test_normalize_th_mtr_hum_from_pdf_fixture() -> None:
    raw = json.loads(
        (Path(__file__).resolve().parents[1] / "docs/final/artifacts/fixtures/qubics_coconet_th_mtr_post_v1.json").read_text(
            encoding="utf-8"
        )
    )
    raw["dt"] = int(datetime.now(UTC).timestamp())
    out = normalize_qubics_coconet(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
    )
    assert out["payload"]["soil_moisture_pct"] == pytest.approx(28.5)
    assert out["vendor_meta"]["type"] == "th_mtr"


def test_normalize_erth_th_mtr_from_mqtt_pdf() -> None:
    raw = {
        "cid": "446E12EF49C0",
        "gw": "G300",
        "type": "erth_th_mtr",
        "nm": "D301",
        "dt": int(datetime.now(UTC).timestamp()),
        "ertht": 27.4,
        "erthh": 41.3,
    }
    out = normalize_qubics_coconet(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
    )
    assert out["payload"]["soil_temp_c"] == pytest.approx(27.4)
    assert out["payload"]["soil_moisture_pct"] == pytest.approx(41.3)
    assert out["vendor_meta"]["type"] == "erth_th_mtr"


def test_normalize_stale_comm_not_ok() -> None:
    old_ts = int((datetime.now(UTC) - timedelta(hours=2)).timestamp())
    raw = {"cid": "1", "type": "soil_mtr", "dt": old_ts, "tmp": 20.0, "sm": 30.0}
    out = normalize_qubics_coconet(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
        comm_ok_max_age_sec=900,
    )
    assert out["payload"]["comm_ok"] is False
