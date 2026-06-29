"""Tests for QuBICS MQTT uplink parsing and cid commission."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from scripts.smartfarm_qubics_device_resolver_v1 import (
    TBD,
    apply_cid_commission,
    load_manifest,
    resolve_zone_id,
)
from scripts.smartfarm_qubics_mqtt_uplink_v1 import (
    handle_uplink_message,
    parse_uplink_topic,
    relay_control_outcome,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json"
STAT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/qubics_coconet_mqtt_stat_d301_v1.json"
EVNT_FIXTURE = ROOT / "docs/final/artifacts/fixtures/qubics_coconet_mqtt_evnt_d202_v1.json"


def test_parse_uplink_topic() -> None:
    meta = parse_uplink_topic("qbsv4/uplink/stat/smartfarm/ABC123")
    assert meta == {"kind": "stat", "group_id": "smartfarm", "topic_cid": "ABC123"}


def test_resolve_zone_d301() -> None:
    manifest = load_manifest(MANIFEST)
    zone = resolve_zone_id(manifest, {"nm": "D301", "cid": "446E12EF49C0"})
    assert zone == "zone_01"


def test_handle_stat_erth_th_mtr() -> None:
    data = json.loads(STAT_FIXTURE.read_text(encoding="utf-8"))
    data["payload"]["dt"] = int(datetime.now(UTC).timestamp())
    manifest = load_manifest(MANIFEST)
    out = handle_uplink_message(
        topic=data["topic"],
        payload=data["payload"],
        manifest=manifest,
        dry_run=True,
    )
    assert "telemetry_normalized" in out["actions"]
    assert out["zone_id"] == "zone_01"
    assert out["normalized"]["payload"]["soil_moisture_pct"] == pytest.approx(41.3)


def test_handle_relay_evnt() -> None:
    data = json.loads(EVNT_FIXTURE.read_text(encoding="utf-8"))
    manifest = load_manifest(MANIFEST)
    out = handle_uplink_message(topic=data["topic"], payload=data["payload"], manifest=manifest, dry_run=True)
    assert out["relay_control_evnt"]["outcome"] == "ok"
    assert relay_control_outcome(data["payload"]) == "ok"


def test_apply_cid_commission_temp_manifest() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "manifest.json"
        shutil.copy2(MANIFEST, path)
        manifest = load_manifest(path)
        for dev in manifest["devices"]:
            if dev.get("nm") == "D301":
                dev["cid"] = TBD
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = apply_cid_commission(path, nm="D301", cid="446E12EF49C0", dry_run=False)
        assert result["changed"] is True
        updated = load_manifest(path)
        d301 = next(d for d in updated["devices"] if d["nm"] == "D301")
        assert d301["cid"] == "446E12EF49C0"
        again = apply_cid_commission(path, nm="D301", cid="446E12EF49C0", dry_run=False)
        assert again["reason"] == "already_set"
