#!/usr/bin/env python3
"""Normalize QuBICS CoCoNET HTTP/MQTT JSON to MKM smartfarm telemetry v1."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _first_present(obj: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in obj and obj[key] is not None:
            return obj[key]
    return None


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, (int, float)):
        sec = float(value)
        if sec > 1e12:
            sec /= 1000.0
        return datetime.fromtimestamp(sec, tz=UTC)
    if isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).astimezone(UTC)
    raise ValueError(f"unsupported timestamp: {value!r}")


def normalize_moisture_pct(raw: Any) -> float:
    val = float(raw)
    if 0.0 <= val <= 1.0:
        val *= 100.0
    return max(0.0, min(100.0, val))


def normalize_ec_us_cm(raw: Any) -> float:
    val = float(raw)
    if val < 50:
        return val * 1000.0
    return val


def normalize_qubics_coconet(
    vendor_payload: dict[str, Any],
    *,
    farm_id: str,
    zone_id: str,
    timezone: str,
    field_map: dict[str, list[str]] | None = None,
    comm_ok_max_age_sec: int = 900,
    missing_ec_us_cm: float = 0.0,
    sensor_type_allowlist: list[str] | None = None,
) -> dict[str, Any]:
    """Map QuBICS POST body (cid, type, dt, bat, tmp, …) to telemetry_ingest envelope."""
    fmap = field_map or {
        "soil_moisture_pct": ["erthh", "sm", "hum", "soil_moisture", "moisture_pct", "moisture"],
        "soil_temp_c": ["ertht", "tmp", "soil_temp", "soil_temperature_c"],
        "soil_ec_us_cm": ["ec", "ec_uS", "ec_us_cm", "soil_ec"],
        "device_battery_pct": ["bat", "battery", "battery_pct"],
        "ts_utc": ["dt", "measured_at", "timestamp"],
        "online": ["online"],
        "sensor_type": ["type"],
    }
    allow = {str(x).lower() for x in (sensor_type_allowlist or [])}
    sensor_type = _first_present(vendor_payload, fmap.get("sensor_type", ["type"]))
    if allow and sensor_type is not None and str(sensor_type).lower() not in allow:
        raise ValueError(f"sensor type not allowed: {sensor_type}")

    moisture_raw = _first_present(vendor_payload, fmap.get("soil_moisture_pct", []))
    temp_raw = _first_present(vendor_payload, fmap.get("soil_temp_c", []))
    ec_raw = _first_present(vendor_payload, fmap.get("soil_ec_us_cm", []))
    batt_raw = _first_present(vendor_payload, fmap.get("device_battery_pct", []))
    ts_raw = _first_present(vendor_payload, fmap.get("ts_utc", []))
    online_raw = _first_present(vendor_payload, fmap.get("online", []))

    if moisture_raw is None or temp_raw is None or ts_raw is None:
        raise ValueError("qubics payload missing required soil/time fields")

    ts_utc = _parse_ts(ts_raw)
    age_sec = (datetime.now(UTC) - ts_utc).total_seconds()
    online = bool(online_raw) if online_raw is not None else True
    comm_ok = online and age_sec <= comm_ok_max_age_sec

    payload: dict[str, Any] = {
        "farm_id": farm_id,
        "zone_id": zone_id,
        "ts_utc": ts_utc.isoformat().replace("+00:00", "Z"),
        "timezone": timezone,
        "soil_moisture_pct": normalize_moisture_pct(moisture_raw),
        "soil_temp_c": float(temp_raw),
        "soil_ec_us_cm": normalize_ec_us_cm(ec_raw) if ec_raw is not None else float(missing_ec_us_cm),
        "comm_ok": comm_ok,
    }
    if batt_raw is not None:
        batt = float(batt_raw)
        if batt <= 4.5:
            payload["device_battery_pct"] = max(0.0, min(100.0, (batt - 3.0) / 1.2 * 100.0))
        else:
            payload["device_battery_pct"] = max(0.0, min(100.0, batt))

    envelope: dict[str, Any] = {
        "message_type": "telemetry_ingest",
        "schema_version": "v1",
        "payload": payload,
        "vendor_meta": {
            "vendor": "qubics_coconet",
            "cid": vendor_payload.get("cid"),
            "gw": vendor_payload.get("gw"),
            "type": sensor_type,
            "nm": vendor_payload.get("nm"),
            "ec_from_device": ec_raw is not None,
        },
    }
    return envelope


def qubics_ack_body(vendor_payload: dict[str, Any]) -> dict[str, Any]:
    """Required HTTP response per QuBICS sensor data manual."""
    cid = vendor_payload.get("cid")
    if cid is None:
        raise ValueError("cid required for qubics ack")
    return {"cid": cid, "result": "ok"}
