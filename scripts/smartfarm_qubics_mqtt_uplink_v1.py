#!/usr/bin/env python3
"""Parse and handle QuBICS MQTT uplink (stat/evnt) messages."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib import error, request

from scripts.normalize_qubics_coconet_v1 import normalize_qubics_coconet
from scripts.smartfarm_persist_jsonl_v1 import append_jsonl
from scripts.smartfarm_qubics_device_resolver_v1 import (
    apply_cid_commission,
    farm_id_from_manifest,
    load_manifest,
    relay_controller_nm,
    resolve_zone_id,
)

TOPIC_RE = re.compile(
    r"^qbsv4/uplink/(?P<kind>stat|evnt)/(?P<group_id>[^/]+)/(?P<topic_cid>[^/]+)$"
)

SOIL_TYPES = frozenset({"erth_th_mtr", "soil_mtr", "th_mtr"})
RELAY_TYPES = frozenset({"rly_ctr", "evnt_log"})


def parse_uplink_topic(topic: str) -> dict[str, str]:
    m = TOPIC_RE.match(topic.strip())
    if not m:
        raise ValueError(f"unsupported uplink topic: {topic!r}")
    return dict(m.groupdict())


def merge_vendor_payload(payload: dict[str, Any], topic_meta: dict[str, str]) -> dict[str, Any]:
    body = dict(payload)
    if not body.get("cid"):
        body["cid"] = topic_meta["topic_cid"]
    if not body.get("gid"):
        body["gid"] = topic_meta["group_id"]
    return body


def is_relay_control_evnt(payload: dict[str, Any], manifest: dict[str, Any]) -> bool:
    msg = str(payload.get("msg") or "")
    if "즉각 제어" not in msg:
        return False
    relay_nm = relay_controller_nm(manifest)
    if relay_nm and str(payload.get("nm") or "") != relay_nm:
        return False
    return payload.get("type") in RELAY_TYPES or "릴레이" in msg


def relay_control_outcome(payload: dict[str, Any]) -> str | None:
    msg = str(payload.get("msg") or "")
    if "즉각 제어 완료" in msg:
        return "ok"
    if "즉각 제어 실패" in msg:
        return "fail"
    return None


def handle_uplink_message(
    *,
    topic: str,
    payload: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: str | None = None,
    farm_id: str | None = None,
    timezone: str = "Asia/Seoul",
    comm_ok_max_age_sec: int = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    topic_meta = parse_uplink_topic(topic)
    vendor = merge_vendor_payload(payload, topic_meta)
    farm = farm_id or farm_id_from_manifest(manifest)
    sensor_type = str(vendor.get("type") or "")

    result: dict[str, Any] = {
        "schema": "smartfarm_qubics_mqtt_uplink_handled_v1",
        "topic": topic,
        "uplink_kind": topic_meta["kind"],
        "cid": vendor.get("cid"),
        "nm": vendor.get("nm"),
        "sensor_type": sensor_type,
        "actions": [],
    }

    if manifest_path and vendor.get("cid") and vendor.get("nm"):
        commission = apply_cid_commission(
            manifest_path,
            nm=str(vendor.get("nm")),
            cid=str(vendor.get("cid")),
            dry_run=dry_run,
        )
        result["commission"] = commission
        if commission.get("changed"):
            result["actions"].append("cid_commissioned")

    if topic_meta["kind"] == "evnt" and is_relay_control_evnt(vendor, manifest):
        outcome = relay_control_outcome(vendor)
        result["relay_control_evnt"] = {
            "outcome": outcome,
            "msg": vendor.get("msg"),
        }
        result["actions"].append("relay_evnt_logged")
        return result

    if topic_meta["kind"] == "stat" and sensor_type in SOIL_TYPES:
        zone_id = resolve_zone_id(manifest, vendor)
        if not zone_id:
            result["reason"] = "zone_unresolved"
            return result
        normalized = normalize_qubics_coconet(
            vendor,
            farm_id=farm,
            zone_id=zone_id,
            timezone=timezone,
            comm_ok_max_age_sec=comm_ok_max_age_sec,
        )
        result["zone_id"] = zone_id
        result["normalized"] = normalized
        result["actions"].append("telemetry_normalized")
        return result

    if topic_meta["kind"] == "stat" and sensor_type in RELAY_TYPES:
        result["actions"].append("relay_stat_logged")
        return result

    result["reason"] = "unhandled_message_type"
    return result


def http_post_json(url: str, body: dict[str, Any], *, timeout: int = 30) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def forward_telemetry_to_api(
    *,
    api_base_url: str,
    vendor_payload: dict[str, Any],
    ingest_path: str = "/v1/vendor/qubics/ingest",
) -> dict[str, Any]:
    url = api_base_url.rstrip("/") + ingest_path
    return http_post_json(url, vendor_payload)


def process_uplink_and_forward(
    *,
    topic: str,
    payload: dict[str, Any],
    manifest: dict[str, Any],
    manifest_path: str | None = None,
    api_base_url: str | None = None,
    farm_id: str | None = None,
    timezone: str = "Asia/Seoul",
    comm_ok_max_age_sec: int = 900,
    jsonl_path: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    handled = handle_uplink_message(
        topic=topic,
        payload=payload,
        manifest=manifest,
        manifest_path=manifest_path,
        farm_id=farm_id,
        timezone=timezone,
        comm_ok_max_age_sec=comm_ok_max_age_sec,
        dry_run=dry_run,
    )
    append_jsonl(
        jsonl_path,
        {
            "event_type": "qubics_mqtt_uplink",
            "topic": topic,
            "payload": payload,
            "handled": handled,
        },
    )

    if api_base_url and "telemetry_normalized" in handled.get("actions", []):
        if dry_run:
            handled["api_forward"] = {"dry_run": True, "url": api_base_url}
        else:
            vendor = merge_vendor_payload(payload, parse_uplink_topic(topic))
            handled["api_forward"] = forward_telemetry_to_api(
                api_base_url=api_base_url,
                vendor_payload=vendor,
            )
    return handled
