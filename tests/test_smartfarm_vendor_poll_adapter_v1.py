"""Tests for smartfarm_vendor_poll_adapter_v1 normalization."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.smartfarm_vendor_poll_adapter_v1 import (
    normalize_ec_us_cm,
    normalize_moisture_pct,
    normalize_vendor_telemetry,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "docs/final/artifacts/fixtures/smartfarm_vendor_telemetry_sample_v1.json"
)


def test_normalize_moisture_fraction_to_percent() -> None:
    assert normalize_moisture_pct(0.213) == pytest.approx(21.3)


def test_normalize_ec_mS_to_uS() -> None:
    assert normalize_ec_us_cm(1.32) == pytest.approx(1320.0)


def test_normalize_vendor_telemetry_from_fixture() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    field_map = {
        "soil_moisture_pct": ["soil_moisture", "moisture_pct"],
        "soil_temp_c": ["soil_temp", "soil_temperature_c"],
        "soil_ec_us_cm": ["ec_uS", "ec_us_cm"],
        "device_battery_pct": ["battery"],
        "ts_utc": ["measured_at", "timestamp"],
        "online": ["online"],
    }
    out = normalize_vendor_telemetry(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
        field_map=field_map,
        comm_ok_max_age_sec=900,
    )
    assert out["message_type"] == "telemetry_ingest"
    p = out["payload"]
    assert p["farm_id"] == "geumsan_farm_01"
    assert p["soil_moisture_pct"] == pytest.approx(21.3)
    assert p["soil_ec_us_cm"] == pytest.approx(1320.0)
    assert p["device_battery_pct"] == pytest.approx(77.0)


def test_comm_ok_false_when_stale() -> None:
    old_ts = (datetime.now(UTC) - timedelta(hours=2)).isoformat().replace("+00:00", "Z")
    raw = {
        "online": True,
        "measured_at": old_ts,
        "soil": {"soil_moisture": 30, "soil_temp": 20, "ec_uS": 1000},
    }
    out = normalize_vendor_telemetry(
        raw,
        farm_id="geumsan_farm_01",
        zone_id="zone_01",
        timezone="Asia/Seoul",
        field_map={
            "soil_moisture_pct": ["soil_moisture"],
            "soil_temp_c": ["soil_temp"],
            "soil_ec_us_cm": ["ec_uS"],
            "ts_utc": ["measured_at"],
            "online": ["online"],
        },
        comm_ok_max_age_sec=900,
    )
    assert out["payload"]["comm_ok"] is False
