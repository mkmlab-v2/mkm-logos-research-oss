"""Tests for QuBICS MQTT control message builder (no broker)."""

from __future__ import annotations

from pathlib import Path

from scripts.smartfarm_qubics_mqtt_control_v1 import build_control_message, load_json

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json"
MAPPING = ROOT / "docs/final/artifacts/smartfarm_geumsan_6channel_valve_mapping_v1.json"


def test_build_open_ch1() -> None:
    spec = load_json(SPEC)
    mapping = load_json(MAPPING)
    msg = build_control_message(spec=spec, mapping=mapping, channel_id="ch1", action="open")
    assert msg["payload"]["req"] == 11
    assert msg["payload"]["cmd"] == "0x01, 0x06, 0x00, 0x01, 0x01, 0x00, 0x00, 0x00"
    assert msg["topic"] == f"qbsv4/downlink/smartfarm/{spec['device_ids']['valve_controller_cid']}"


def test_build_close_ch2() -> None:
    spec = load_json(SPEC)
    mapping = load_json(MAPPING)
    msg = build_control_message(spec=spec, mapping=mapping, channel_id="ch2", action="close")
    assert msg["payload"]["cmd"] == "0x01, 0x06, 0x00, 0x02, 0x02, 0x00, 0x00, 0x00"
    assert "downlink/smartfarm" in msg["topic"]


def test_build_open_ch6() -> None:
    spec = load_json(SPEC)
    mapping = load_json(MAPPING)
    msg = build_control_message(spec=spec, mapping=mapping, channel_id="ch6", action="open")
    assert msg["payload"]["cmd"] == "0x01, 0x06, 0x00, 0x06, 0x01, 0x00, 0x00, 0x00"


def test_spec_confirmed_from_pdf() -> None:
    spec = load_json(SPEC)
    assert spec["vendor_status"] == "confirmed_from_pdf"
    assert "qbsv4/downlink" in spec["topic_template"]
