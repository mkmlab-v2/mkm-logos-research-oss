#!/usr/bin/env python3
"""Poll MKM control queue and dispatch sequential valve commands via QuBICS MQTT template."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from scripts.smartfarm_qubics_mqtt_control_v1 import (  # noqa: E402
    broker_config,
    build_control_message,
    load_json,
    publish_mqtt,
)


def mkm_base_url() -> str:
    return os.environ.get("SMARTFARM_API_BASE_URL", "http://127.0.0.1:8020").rstrip("/")


def http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def map_command_to_channel(command: dict[str, Any], mapping: dict[str, Any]) -> str:
    meta = command.get("channel_id")
    if meta:
        return str(meta)
    reason = str(command.get("reason_code") or "")
    if "nutrient" in reason:
        return "ch2"
    if "flush" in reason:
        return "ch3"
    return "ch1"


def action_from_command(command: dict[str, Any]) -> str:
    action = str(command.get("action") or "open").lower()
    if action in {"on", "open"}:
        return "open"
    return "close"


def dispatch_once(
    *,
    farm_id: str,
    zone_id: str,
    spec: dict[str, Any],
    mapping: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    base = mkm_base_url()
    poll = http_json("GET", f"{base}/v1/control/next/{farm_id}/{zone_id}")
    if not poll.get("available"):
        return {"status": "no_command", "poll": poll}

    command = poll["command"]
    channel_id = map_command_to_channel(command, mapping)
    action = action_from_command(command)
    msg = build_control_message(spec=spec, mapping=mapping, channel_id=channel_id, action=action)

    if dry_run:
        return {"status": "dry_run", "command": command, "mqtt": msg}

    pub = publish_mqtt(
        broker=broker_config(spec),
        topic=str(msg["topic"]),
        payload=dict(msg["payload"]),
        dry_run=False,
    )
    ack_body = {
        "farm_id": farm_id,
        "zone_id": zone_id,
        "command_id": command.get("command_id"),
        "ts_utc": command.get("ts_utc"),
        "ack_status": "ok" if pub.get("published") else "fail",
        "ack_message": json.dumps(pub, ensure_ascii=False),
    }
    ack = http_json("POST", f"{base}/v1/control/ack", body=ack_body)
    return {"status": "dispatched", "mqtt": msg, "publish": pub, "ack": ack}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=ROOT / "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json")
    ap.add_argument("--mapping", type=Path, default=ROOT / "docs/final/artifacts/smartfarm_geumsan_6channel_valve_mapping_v1.json")
    ap.add_argument("--farm-id", default=os.environ.get("SMARTFARM_PILOT_FARM_ID", "geumsan_farm_01"))
    ap.add_argument("--zone-id", default=os.environ.get("SMARTFARM_PILOT_ZONE_ID", "zone_01"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval-sec", type=int, default=15)
    args = ap.parse_args()

    spec = load_json(args.spec)
    mapping = load_json(args.mapping)

    while True:
        result = dispatch_once(
            farm_id=args.farm_id,
            zone_id=args.zone_id,
            spec=spec,
            mapping=mapping,
            dry_run=args.dry_run,
        )
        print(json.dumps(result, ensure_ascii=False))
        if args.once or args.dry_run:
            return 0
        time.sleep(max(1, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
