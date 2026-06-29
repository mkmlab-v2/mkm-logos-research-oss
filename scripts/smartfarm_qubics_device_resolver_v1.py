#!/usr/bin/env python3
"""Resolve QuBICS CoCoNET devices (nm/cid) to MKM farm/zone via device manifest."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/smartfarm_qubics_device_manifest_v1.json"
TBD = "TBD_COMMISSIONING"


def load_manifest(path: Path | str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_MANIFEST
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object JSON: {p}")
    return data


def _devices(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    devices = manifest.get("devices")
    if not isinstance(devices, list):
        return []
    return [d for d in devices if isinstance(d, dict)]


def find_device(
    manifest: dict[str, Any],
    *,
    nm: str | None = None,
    cid: str | None = None,
    role: str | None = None,
) -> dict[str, Any] | None:
    nm_s = str(nm).strip() if nm else ""
    cid_s = str(cid).strip() if cid else ""
    for dev in _devices(manifest):
        if role and dev.get("role") != role:
            continue
        if nm_s and str(dev.get("nm") or "") == nm_s:
            return dev
        if cid_s and str(dev.get("cid") or "") == cid_s:
            return dev
    return None


def farm_id_from_manifest(manifest: dict[str, Any]) -> str:
    pilot = manifest.get("pilot") or {}
    return str(pilot.get("farm_id") or "geumsan_farm_01")


def resolve_zone_id(manifest: dict[str, Any], vendor_payload: dict[str, Any]) -> str | None:
    dev = find_device(
        manifest,
        nm=vendor_payload.get("nm"),
        cid=vendor_payload.get("cid"),
        role="soil_sensor",
    )
    if dev and dev.get("zone_id"):
        return str(dev["zone_id"])
    return None


def relay_controller_nm(manifest: dict[str, Any]) -> str | None:
    dev = find_device(manifest, role="relay_controller")
    return str(dev["nm"]) if dev and dev.get("nm") else None


def apply_cid_commission(
    manifest_path: Path | str,
    *,
    nm: str | None,
    cid: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Fill cid on manifest device when still TBD; idempotent if cid already set."""
    path = Path(manifest_path)
    manifest = load_manifest(path)
    cid_s = str(cid).strip()
    if not cid_s or cid_s == TBD:
        raise ValueError("cid required for commission")

    nm_s = str(nm).strip() if nm else ""
    dev = find_device(manifest, nm=nm_s or None, cid=cid_s)
    if dev is None and nm_s:
        dev = find_device(manifest, nm=nm_s)
    if dev is None:
        dev = find_device(manifest, cid=cid_s)

    result: dict[str, Any] = {
        "schema": "smartfarm_qubics_cid_commission_v1",
        "commissioned_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "manifest_path": str(path),
        "nm": nm_s or (dev or {}).get("nm"),
        "cid": cid_s,
        "changed": False,
        "reason": "ok",
    }

    if dev is None:
        result["reason"] = "device_not_in_manifest"
        return result

    prev = str(dev.get("cid") or "")
    if prev == cid_s:
        result["reason"] = "already_set"
        result["role"] = dev.get("role")
        return result
    if prev and prev != TBD and prev != cid_s:
        result["reason"] = "cid_conflict"
        result["previous_cid"] = prev
        return result

    if not dry_run:
        dev["cid"] = cid_s
        manifest["updated_at_utc"] = result["commissioned_at_utc"]
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result["changed"] = not dry_run
    result["role"] = dev.get("role")
    result["zone_id"] = dev.get("zone_id")
    return result


def manifest_path_from_env() -> Path | None:
    import os

    raw = os.environ.get("SMARTFARM_QUBICS_DEVICE_MANIFEST", "").strip()
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None
