#!/usr/bin/env python3
"""MQTT subscriber bridge: QuBICS qbsv4 uplink -> JSONL + optional HTTP ingest + cid commission.

Examples:
  py scripts/smartfarm_qubics_mqtt_subscriber_v1.py --dry-run --fixture docs/final/artifacts/fixtures/qubics_coconet_mqtt_stat_d301_v1.json
  py scripts/smartfarm_qubics_mqtt_subscriber_v1.py --once --max-messages 5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.smartfarm_qubics_device_resolver_v1 import load_manifest, manifest_path_from_env
from scripts.smartfarm_qubics_mqtt_uplink_v1 import process_uplink_and_forward
from scripts.smartfarm_qubics_mqtt_control_v1 import broker_config, load_json

DEFAULT_SPEC = ROOT / "docs/final/artifacts/smartfarm_qubics_mqtt_control_spec_v1.example.json"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json"
COMMISSION_REPORT = ROOT / "reports/smartfarm_qubics_cid_commission_latest.json"


def _env_manifest_path(args: argparse.Namespace) -> Path:
    if args.manifest:
        return Path(args.manifest)
    env = manifest_path_from_env()
    return env or DEFAULT_MANIFEST


def _api_base_url(args: argparse.Namespace) -> str | None:
    if args.no_api_forward:
        return None
    return (args.api_base_url or os.environ.get("SMARTFARM_API_BASE_URL", "http://127.0.0.1:8020")).rstrip("/")


def _jsonl_path(args: argparse.Namespace) -> str | None:
    if args.jsonl:
        return str(args.jsonl)
    raw = os.environ.get("SMARTFARM_QUBICS_MQTT_JSONL", "").strip()
    if raw:
        return raw
    raw = os.environ.get("SMARTFARM_QUBICS_RAW_JSONL", "").strip()
    return raw or str(ROOT / "reports/smartfarm_qubics_mqtt_uplink.jsonl")


def _subscribe_topics(manifest: dict[str, Any]) -> list[str]:
    mqtt = manifest.get("mqtt") or {}
    wildcards = mqtt.get("subscribe_wildcards")
    if isinstance(wildcards, list) and wildcards:
        return [str(x) for x in wildcards]
    group_id = (manifest.get("coconet") or {}).get("group_id") or "smartfarm"
    return [
        f"qbsv4/uplink/stat/{group_id}/#",
        f"qbsv4/uplink/evnt/{group_id}/#",
    ]


def process_fixture(path: Path, *, args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = _env_manifest_path(args)
    manifest = load_manifest(manifest_path)
    fixture = json.loads(path.read_text(encoding="utf-8"))
    topic = str(fixture["topic"])
    payload = dict(fixture["payload"])
    handled = process_uplink_and_forward(
        topic=topic,
        payload=payload,
        manifest=manifest,
        manifest_path=str(manifest_path),
        api_base_url=_api_base_url(args),
        farm_id=args.farm_id,
        timezone=args.timezone,
        comm_ok_max_age_sec=args.comm_ok_max_age_sec,
        jsonl_path=_jsonl_path(args),
        dry_run=args.dry_run,
    )
    report = {
        "schema": "smartfarm_qubics_mqtt_subscriber_run_v1",
        "mode": "fixture",
        "fixture": str(path),
        "manifest_path": str(manifest_path),
        "handled": handled,
        "dry_run": args.dry_run,
    }
    if handled.get("commission"):
        COMMISSION_REPORT.parent.mkdir(parents=True, exist_ok=True)
        COMMISSION_REPORT.write_text(
            json.dumps(handled["commission"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return report


def run_mqtt_loop(*, args: argparse.Namespace) -> int:
    try:
        import paho.mqtt.client as mqtt  # type: ignore[import-untyped]
    except ImportError:
        print("paho-mqtt required: pip install paho-mqtt", file=sys.stderr)
        return 1

    spec = load_json(args.spec or DEFAULT_SPEC)
    broker = broker_config(spec)
    manifest_path = _env_manifest_path(args)
    manifest = load_manifest(manifest_path)
    topics = _subscribe_topics(manifest)
    qos = int((spec.get("mqtt") or {}).get("qos_subscribe", 2))
    count = 0
    results: list[dict[str, Any]] = []

    def on_connect(client, userdata, flags, reason_code, properties=None):  # noqa: ANN001, ARG001
        for topic in topics:
            client.subscribe(topic, qos=qos)

    def on_message(client, userdata, msg):  # noqa: ANN001, ARG001
        nonlocal count
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {"_raw": msg.payload.decode("utf-8", errors="replace")}
        handled = process_uplink_and_forward(
            topic=msg.topic,
            payload=payload if isinstance(payload, dict) else {"_raw": payload},
            manifest=manifest,
            manifest_path=str(manifest_path),
            api_base_url=_api_base_url(args),
            farm_id=args.farm_id,
            timezone=args.timezone,
            comm_ok_max_age_sec=args.comm_ok_max_age_sec,
            jsonl_path=_jsonl_path(args),
            dry_run=args.dry_run,
        )
        results.append({"topic": msg.topic, "handled": handled})
        print(json.dumps({"topic": msg.topic, "actions": handled.get("actions"), "reason": handled.get("reason")}, ensure_ascii=False))
        if handled.get("commission"):
            COMMISSION_REPORT.write_text(
                json.dumps(handled["commission"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        count += 1
        if args.max_messages and count >= args.max_messages:
            client.disconnect()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if broker.get("username"):
        client.username_pw_set(broker["username"], broker.get("password"))
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(broker["host"], broker["port"], keepalive=60)
    if args.once or args.max_messages:
        client.loop_forever()
        return 0
    while True:
        client.loop(timeout=1.0)
        time.sleep(0.05)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--manifest", type=Path, default=None)
    ap.add_argument("--fixture", type=Path, help="Offline single-message dry-run from JSON fixture")
    ap.add_argument("--api-base-url", default=None)
    ap.add_argument("--no-api-forward", action="store_true")
    ap.add_argument("--farm-id", default=os.environ.get("SMARTFARM_PILOT_FARM_ID", "geumsan_farm_01"))
    ap.add_argument("--timezone", default=os.environ.get("SMARTFARM_PILOT_TIMEZONE", "Asia/Seoul"))
    ap.add_argument("--comm-ok-max-age-sec", type=int, default=900)
    ap.add_argument("--jsonl", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true", help="No manifest write / no API forward")
    ap.add_argument("--once", action="store_true", help="Disconnect after first message")
    ap.add_argument("--max-messages", type=int, default=0)
    args = ap.parse_args()

    if args.fixture:
        report = process_fixture(args.fixture, args=args)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    return run_mqtt_loop(args=args)


if __name__ == "__main__":
    raise SystemExit(main())
