#!/usr/bin/env python3
"""Dry-run QuBICS MQTT uplink fixtures (no broker). Writes reports/smartfarm_qubics_mqtt_uplink_dry_run_latest.json"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.smartfarm_qubics_device_resolver_v1 import load_manifest
from scripts.smartfarm_qubics_mqtt_uplink_v1 import handle_uplink_message, process_uplink_and_forward

OUT = ROOT / "reports/smartfarm_qubics_mqtt_uplink_dry_run_latest.json"
MANIFEST_SRC = ROOT / "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json"
FIXTURES = [
    ROOT / "docs/final/artifacts/fixtures/qubics_coconet_mqtt_stat_d301_v1.json",
    ROOT / "docs/final/artifacts/fixtures/qubics_coconet_mqtt_evnt_d202_v1.json",
]


def main() -> int:
    errors: list[str] = []
    steps: list[dict] = []

    with tempfile.TemporaryDirectory() as tmp:
        manifest_copy = Path(tmp) / "manifest.json"
        shutil.copy2(MANIFEST_SRC, manifest_copy)
        manifest = load_manifest(manifest_copy)

        for fx in FIXTURES:
            data = json.loads(fx.read_text(encoding="utf-8"))
            handled = process_uplink_and_forward(
                topic=str(data["topic"]),
                payload=dict(data["payload"]),
                manifest=manifest,
                manifest_path=str(manifest_copy),
                api_base_url=None,
                jsonl_path=None,
                dry_run=False,
            )
            step = {"fixture": fx.name, "actions": handled.get("actions"), "reason": handled.get("reason")}
            steps.append(step)
            if fx.name.startswith("qubics_coconet_mqtt_stat") and "telemetry_normalized" not in handled.get("actions", []):
                errors.append(f"{fx.name}: expected telemetry_normalized")
            if fx.name.startswith("qubics_coconet_mqtt_evnt") and "relay_evnt_logged" not in handled.get("actions", []):
                errors.append(f"{fx.name}: expected relay_evnt_logged")

        updated = load_manifest(manifest_copy)
        d301 = next(d for d in updated["devices"] if d.get("nm") == "D301")
        stat_data = json.loads(FIXTURES[0].read_text(encoding="utf-8"))
        expected_cid = str(stat_data["payload"]["cid"])
        if d301.get("cid") != expected_cid:
            errors.append(f"D301 cid expected {expected_cid}, got {d301.get('cid')}")

    report = {
        "schema": "smartfarm_qubics_mqtt_uplink_dry_run_v1",
        "checked_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "verdict": "pass" if not errors else "fail",
        "errors": errors,
        "steps": steps,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
