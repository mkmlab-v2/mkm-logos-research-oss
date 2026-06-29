#!/usr/bin/env python3
"""Phase 0 dry-run E2E: batch -> QuBICS ingest -> auto evaluate -> control queue -> MQTT build.

Uses in-process FastAPI TestClient (no live gateway/MQTT broker required).
Writes: reports/smartfarm_qubics_phase0_e2e_latest.json
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

OUT = ROOT / "reports" / "smartfarm_qubics_phase0_e2e_latest.json"
SENSOR_FIXTURE = ROOT / "docs/final/artifacts/fixtures/qubics_coconet_sensor_post_v1.json"
BATCH_FIXTURE = ROOT / "docs/final/artifacts/fixtures/smartfarm_fermentation_batch_phase0_v1.json"
SPEC = ROOT / "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json"
MAPPING = ROOT / "docs/final/artifacts/smartfarm_geumsan_6channel_valve_mapping_v1.json"

FARM_ID = "geumsan_farm_01"
ZONE_ID = "zone_01"


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def main() -> int:
    from scripts.ai_smartfarm_api_stub import app
    from scripts.smartfarm_qubics_mqtt_control_v1 import build_control_message, load_json

    errors: list[str] = []
    steps: dict[str, Any] = {}
    client = TestClient(app)

    batch_body = json.loads(BATCH_FIXTURE.read_text(encoding="utf-8"))
    batch_body["ts_utc"] = _iso_now()
    batch_body["brew_start_ts_utc"] = (datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
    batch_body["brew_end_ts_utc"] = _iso_now()
    batch_resp = client.post("/v1/batch", json=batch_body)
    steps["batch_register"] = {"status_code": batch_resp.status_code}
    if batch_resp.status_code != 200:
        errors.append(f"batch register HTTP {batch_resp.status_code}")

    raw = json.loads(SENSOR_FIXTURE.read_text(encoding="utf-8"))
    raw["dt"] = int(datetime.now(UTC).timestamp())
    raw["sm"] = 0.12
    ingest = client.post("/v1/vendor/qubics/ingest", json=raw)
    steps["ingest"] = {"status_code": ingest.status_code, "soil_moisture_pct": 12.0}
    if ingest.status_code != 200:
        errors.append(f"ingest HTTP {ingest.status_code}")
    else:
        body = ingest.json()
        if body.get("ack", {}).get("result") != "ok":
            errors.append("ingest ack not ok")
        if body.get("normalized", {}).get("message_type") != "telemetry_ingest":
            errors.append("normalized message_type mismatch")

    state = client.get(f"/v1/state/{FARM_ID}/{ZONE_ID}")
    steps["state"] = {
        "status_code": state.status_code,
        "has_telemetry": bool(state.json().get("telemetry")),
        "has_batch": bool(state.json().get("batch")),
    }
    if state.status_code != 200 or not state.json().get("telemetry"):
        errors.append("zone state missing telemetry after ingest")
    if not state.json().get("batch"):
        errors.append("zone state missing batch after register")

    auto = client.post(
        "/v1/auto/evaluate",
        json={
            "farm_id": FARM_ID,
            "zone_id": ZONE_ID,
            "ts_utc": _iso_now(),
            "forecast_rain_mm_12h": 0.0,
            "mode": "auto",
            "desired_runtime_sec": 120,
            "estimated_volume_liter": 50,
            "soil_dry_threshold_pct": 23.0,
        },
    )
    auto_body = auto.json() if auto.status_code == 200 else {}
    steps["auto_evaluate"] = {
        "status_code": auto.status_code,
        "decision": auto_body.get("decision"),
        "reason_code": auto_body.get("reason_code"),
        "has_suggested_command": bool(auto_body.get("suggested_command")),
    }
    if auto.status_code != 200:
        errors.append(f"auto/evaluate HTTP {auto.status_code}")
    elif auto_body.get("decision") != "execute":
        errors.append(f"auto/evaluate expected execute, got {auto_body.get('decision')}")

    poll = client.get(f"/v1/control/next/{FARM_ID}/{ZONE_ID}")
    poll_body = poll.json() if poll.status_code == 200 else {}
    steps["control_poll"] = {
        "status_code": poll.status_code,
        "available": poll_body.get("available"),
        "command_id": (poll_body.get("command") or {}).get("command_id"),
    }
    if poll.status_code != 200 or not poll_body.get("available"):
        errors.append("control queue empty after auto execute")

    spec = load_json(SPEC)
    mapping = load_json(MAPPING)
    mqtt_msg = build_control_message(spec=spec, mapping=mapping, channel_id="ch1", action="open")
    steps["mqtt_build"] = {
        "topic": mqtt_msg.get("topic"),
        "payload": mqtt_msg.get("payload"),
        "vendor_status": mqtt_msg.get("vendor_status"),
    }
    if spec.get("vendor_status") != "confirmed_from_pdf":
        steps["mqtt_build"]["note"] = "control spec not confirmed_from_pdf"

    command_id = (poll_body.get("command") or {}).get("command_id")
    if command_id:
        ack = client.post(
            "/v1/control/ack",
            json={
                "farm_id": FARM_ID,
                "zone_id": ZONE_ID,
                "command_id": command_id,
                "ack_status": "executed",
                "ack_message": "phase0_dry_run",
                "ts_utc": _iso_now(),
            },
        )
        steps["control_ack"] = {"status_code": ack.status_code}
        if ack.status_code != 200:
            errors.append(f"control ack HTTP {ack.status_code}")

    root_ack = client.post("/", json=raw)
    steps["root_post_ack"] = root_ack.json() if root_ack.status_code == 200 else {"error": root_ack.status_code}
    if root_ack.status_code != 200:
        errors.append(f"root POST HTTP {root_ack.status_code}")

    report = {
        "schema": "smartfarm_qubics_phase0_e2e_v1",
        "checked_at_utc": _iso_now(),
        "verdict": "pass" if not errors else "fail",
        "errors": errors,
        "steps": steps,
        "boundary_ack": "Dry-run only; live field E2E requires gateway commission + MQTT broker",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
