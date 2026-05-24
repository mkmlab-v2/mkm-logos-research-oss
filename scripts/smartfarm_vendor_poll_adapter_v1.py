#!/usr/bin/env python3
"""Poll vendor cloud API and mirror telemetry into MKM smartfarm API v1.

Phase 1 bridge: vendor REST (config-driven) -> POST /v1/telemetry on MKM stub/production.

Config: docs/final/artifacts/smartfarm_phase1_vendor_adapter_config_v1.example.json
Spec:   docs/final/artifacts/smartfarm_phase1_vendor_adapter_spec_v1.json

Run:
  py scripts/smartfarm_vendor_poll_adapter_v1.py --config docs/final/artifacts/smartfarm_phase1_vendor_adapter_config_v1.example.json --dry-run
  py scripts/smartfarm_vendor_poll_adapter_v1.py --config path/to/config.json --once
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _deep_get(obj: Any, dotted: str) -> Any:
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


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


def normalize_vendor_telemetry(
    vendor_payload: dict[str, Any],
    *,
    farm_id: str,
    zone_id: str,
    timezone: str,
    field_map: dict[str, list[str]],
    comm_ok_max_age_sec: int,
) -> dict[str, Any]:
    soil = vendor_payload.get("soil") if isinstance(vendor_payload.get("soil"), dict) else vendor_payload
    power = vendor_payload.get("power") if isinstance(vendor_payload.get("power"), dict) else vendor_payload

    moisture_raw = _first_present(soil, field_map.get("soil_moisture_pct", []))
    temp_raw = _first_present(soil, field_map.get("soil_temp_c", []))
    ec_raw = _first_present(soil, field_map.get("soil_ec_us_cm", []))
    batt_raw = _first_present(power if isinstance(power, dict) else vendor_payload, field_map.get("device_battery_pct", []))
    ts_raw = _first_present(vendor_payload, field_map.get("ts_utc", []))
    online_raw = _first_present(vendor_payload, field_map.get("online", []))

    if moisture_raw is None or temp_raw is None or ec_raw is None or ts_raw is None:
        raise ValueError("vendor payload missing required soil/time fields")

    ts_utc = _parse_ts(ts_raw)
    age_sec = (datetime.now(UTC) - ts_utc).total_seconds()
    online = bool(online_raw) if online_raw is not None else True
    comm_ok = online and age_sec <= comm_ok_max_age_sec

    out: dict[str, Any] = {
        "message_type": "telemetry_ingest",
        "schema_version": "v1",
        "payload": {
            "farm_id": farm_id,
            "zone_id": zone_id,
            "ts_utc": ts_utc.isoformat().replace("+00:00", "Z"),
            "timezone": timezone,
            "soil_moisture_pct": normalize_moisture_pct(moisture_raw),
            "soil_temp_c": float(temp_raw),
            "soil_ec_us_cm": normalize_ec_us_cm(ec_raw),
            "comm_ok": comm_ok,
        },
    }
    if batt_raw is not None:
        out["payload"]["device_battery_pct"] = max(0.0, min(100.0, float(batt_raw)))
    return out


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "smartfarm_phase1_vendor_adapter_config_v1":
        raise ValueError(f"unexpected config schema: {data.get('schema')}")
    return data


def mkm_base_url(config: dict[str, Any]) -> str:
    mkm = config.get("mkm_api") or {}
    env_name = str(mkm.get("base_url_env") or "SMARTFARM_API_BASE_URL")
    return os.environ.get(env_name, str(mkm.get("base_url_default") or "http://127.0.0.1:8020")).rstrip("/")


def vendor_auth_headers(config: dict[str, Any]) -> dict[str, str]:
    auth = (config.get("vendor_api") or {}).get("auth") or {}
    headers = {"Accept": "application/json"}
    if auth.get("type") == "bearer":
        token_env = str(auth.get("token_env") or "SMARTFARM_VENDOR_API_TOKEN")
        token = os.environ.get(token_env, "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_sec: int = 30,
) -> Any:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} {url}: {detail}") from exc


def fetch_vendor_telemetry(config: dict[str, Any]) -> dict[str, Any]:
    vendor_api = config["vendor_api"]
    base = str(vendor_api["base_url"]).rstrip("/")
    tel = vendor_api["telemetry_get"]
    path = str(tel["path"])
    url = f"{base}{path}"
    timeout = int(tel.get("timeout_sec") or 30)
    return http_json("GET", url, headers=vendor_auth_headers(config), timeout_sec=timeout)


def post_mkm_telemetry(config: dict[str, Any], envelope: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"dry_run": True, "would_post": envelope}
    base = mkm_base_url(config)
    url = f"{base}/v1/telemetry"
    return http_json("POST", url, body=envelope["payload"], timeout_sec=30)


def poll_once(config: dict[str, Any], *, dry_run: bool) -> dict[str, Any]:
    pilot = config["pilot"]
    vendor_raw = fetch_vendor_telemetry(config)
    envelope = normalize_vendor_telemetry(
        vendor_raw,
        farm_id=str(pilot["farm_id"]),
        zone_id=str(pilot["zone_id"]),
        timezone=str(pilot.get("timezone") or "Asia/Seoul"),
        field_map=config.get("field_map") or {},
        comm_ok_max_age_sec=int(config.get("comm_ok_max_age_sec") or 900),
    )
    ack = post_mkm_telemetry(config, envelope, dry_run=dry_run)
    return {"vendor_sample_keys": list(vendor_raw.keys())[:20], "telemetry": envelope, "mkm_response": ack}


def main() -> int:
    parser = argparse.ArgumentParser(description="MKM smartfarm Phase 1 vendor poll adapter")
    parser.add_argument("--config", required=True, help="Path to smartfarm_phase1_vendor_adapter_config_v1.json")
    parser.add_argument("--dry-run", action="store_true", help="Normalize only; do not call vendor or MKM")
    parser.add_argument("--once", action="store_true", help="Single poll then exit")
    parser.add_argument("--fixture", help="JSON file instead of vendor HTTP (local test)")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    interval = int(config.get("poll_interval_sec") or 120)

    def run_cycle() -> dict[str, Any]:
        if args.fixture:
            vendor_raw = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
            pilot = config["pilot"]
            envelope = normalize_vendor_telemetry(
                vendor_raw,
                farm_id=str(pilot["farm_id"]),
                zone_id=str(pilot["zone_id"]),
                timezone=str(pilot.get("timezone") or "Asia/Seoul"),
                field_map=config.get("field_map") or {},
                comm_ok_max_age_sec=int(config.get("comm_ok_max_age_sec") or 900),
            )
            ack = post_mkm_telemetry(config, envelope, dry_run=args.dry_run)
            return {"telemetry": envelope, "mkm_response": ack}
        return poll_once(config, dry_run=args.dry_run)

    result = run_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.once or args.dry_run or args.fixture:
        return 0

    while True:
        time.sleep(interval)
        try:
            result = poll_once(config, dry_run=False)
            print(json.dumps(result, ensure_ascii=False))
        except Exception as exc:
            print(f"poll_error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
