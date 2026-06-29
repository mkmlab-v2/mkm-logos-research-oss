#!/usr/bin/env python3
"""Build and publish QuBICS MQTT relay control messages (qbsv4/downlink per vendor PDF)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from string import Formatter
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json"
DEFAULT_MAPPING = ROOT / "docs/final/artifacts/smartfarm_geumsan_6channel_valve_mapping_v1.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {path}")
    return data


def _resolve_channel(mapping: dict[str, Any], channel_id: str) -> dict[str, Any]:
    for ch in mapping.get("channels") or []:
        if ch.get("channel_id") == channel_id:
            return ch
    raise ValueError(f"unknown channel_id: {channel_id}")


def _format_value(template: str, ctx: dict[str, Any]) -> str:
    return Formatter().format(template, **{k: str(v) for k, v in ctx.items()})


def _relay_channel_hex(spec: dict[str, Any], relay_index: int) -> str:
    fmt = str(spec.get("relay_channel_hex_format") or "0x{relay_index:02X}")
    return fmt.format(relay_index=int(relay_index))


def _relay_cmd_string(spec: dict[str, Any], *, relay_index: int, action: str) -> str:
    action_map = spec.get("relay_action_hex_map") or {
        "on": "0x01",
        "open": "0x01",
        "off": "0x02",
        "close": "0x02",
    }
    action_l = action.strip().lower()
    if action_l not in action_map:
        raise ValueError(f"unsupported action: {action}")
    relay_channel_hex = _relay_channel_hex(spec, int(relay_index))
    relay_action_hex = str(action_map[action_l])
    template = str(
        spec.get("relay_cmd_template")
        or "0x01, 0x06, 0x00, {relay_channel_hex}, {relay_action_hex}, 0x00, 0x00, 0x00"
    )
    return template.format(relay_channel_hex=relay_channel_hex, relay_action_hex=relay_action_hex)


def build_control_message(
    *,
    spec: dict[str, Any],
    mapping: dict[str, Any],
    channel_id: str,
    action: str,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ch = _resolve_channel(mapping, channel_id)
    action_l = action.strip().lower()
    device_ids = spec.get("device_ids") or {}
    relay_index = int(ch.get("relay_index"))
    device_cid = os.environ.get(
        str(device_ids.get("relay_controller_cid_env") or "SMARTFARM_QUBICS_RELAY_CID"),
        device_ids.get("valve_controller_cid", "TBD_COMMISSIONING"),
    )
    group_id = str(spec.get("group_id") or "smartfarm")
    relay_cmd = _relay_cmd_string(spec, relay_index=relay_index, action=action_l)
    ctx: dict[str, Any] = {
        "channel_id": channel_id,
        "relay_index": relay_index,
        "role": ch.get("role"),
        "action": action_l,
        "group_id": group_id,
        "device_cid": device_cid,
        "relay_cmd": relay_cmd,
        "valve_controller_nm": device_ids.get("valve_controller_nm", "D202"),
    }
    if extra_ctx:
        ctx.update(extra_ctx)

    topic = _format_value(str(spec.get("topic_template") or "qbsv4/downlink/{group_id}/{device_cid}"), ctx)
    payload_template = spec.get("payload_template") or {"req": 11, "cmd": "{relay_cmd}"}
    payload: dict[str, Any] = {}
    for key, val in payload_template.items():
        if isinstance(val, str):
            payload[key] = _format_value(val, ctx) if "{" in val else val
        else:
            payload[key] = val

    return {
        "topic": topic,
        "payload": payload,
        "context": ctx,
        "vendor_status": spec.get("vendor_status", "template"),
        "qos": (spec.get("mqtt") or {}).get("qos_publish", 2),
    }


def broker_config(spec: dict[str, Any]) -> dict[str, Any]:
    broker = spec.get("broker") or {}
    host = os.environ.get(str(broker.get("host_env") or "SMARTFARM_MQTT_BROKER_HOST"), broker.get("host", "127.0.0.1"))
    port = int(os.environ.get(str(broker.get("port_env") or "SMARTFARM_MQTT_BROKER_PORT"), broker.get("port", 1883)))
    user = os.environ.get(str(broker.get("username_env") or "SMARTFARM_MQTT_USER"), broker.get("username") or "")
    password = os.environ.get(str(broker.get("password_env") or "SMARTFARM_MQTT_PASSWORD"), broker.get("password") or "")
    return {"host": host, "port": port, "username": user or None, "password": password or None}


def publish_mqtt(*, broker: dict[str, Any], topic: str, payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False)
    if dry_run:
        return {"dry_run": True, "broker": broker, "topic": topic, "payload": payload}
    try:
        import paho.mqtt.client as mqtt  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("paho-mqtt required for live publish: pip install paho-mqtt") from exc

    result: dict[str, Any] = {"topic": topic, "payload": payload}

    def _on_publish(client, userdata, mid):  # noqa: ANN001
        result["mid"] = mid

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if broker.get("username"):
        client.username_pw_set(broker["username"], broker.get("password"))
    client.on_publish = _on_publish
    client.connect(broker["host"], broker["port"], keepalive=60)
    client.loop_start()
    info = client.publish(topic, body, qos=1)
    info.wait_for_publish(timeout=10)
    client.loop_stop()
    client.disconnect()
    result["published"] = info.is_published()
    result["rc"] = int(info.rc)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    ap.add_argument("--channel", required=True, help="ch1|ch2|ch3")
    ap.add_argument("--action", required=True, help="open|close|on|off")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--publish", action="store_true", help="MQTT publish (requires paho-mqtt + broker)")
    args = ap.parse_args()

    spec = load_json(args.spec)
    mapping = load_json(args.mapping)
    msg = build_control_message(spec=spec, mapping=mapping, channel_id=args.channel, action=args.action)
    print(json.dumps(msg, ensure_ascii=False, indent=2))
    if args.publish and not args.dry_run:
        out = publish_mqtt(
            broker=broker_config(spec),
            topic=str(msg["topic"]),
            payload=dict(msg["payload"]),
            dry_run=False,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("published") else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
