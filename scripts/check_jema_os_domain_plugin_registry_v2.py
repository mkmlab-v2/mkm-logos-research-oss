#!/usr/bin/env python3
"""Validate JEMA OS domain plugin registry v2 (anchors, intake mapping, pin isolation)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
DEFAULT_OUT = ROOT / "reports/jema_os_domain_plugin_registry_v2_check_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pin_paths(manifest_ref: str) -> set[str]:
    path = ROOT / manifest_ref
    if not path.is_file():
        return set()
    doc = json.loads(path.read_text(encoding="utf-8"))
    assets = doc.get("assets") or {}
    out: set[str] = set()
    for spec in assets.values():
        if isinstance(spec, dict) and spec.get("path"):
            out.add(str(spec["path"]).replace("\\", "/"))
    return out


def check_registry(doc: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    slots = doc.get("slots") or {}
    if not isinstance(slots, dict) or len(slots) < 4:
        failures.append("slots_missing_or_too_few")

    intake_path = ROOT / str(doc.get("intake_policy_ref") or "")
    intake_lanes: set[str] = set()
    intake_intents: set[str] = set()
    if intake_path.is_file():
        intake = json.loads(intake_path.read_text(encoding="utf-8"))
        intake_lanes = set(intake.get("domain_lanes") or [])
        intake_intents = set(intake.get("intent_chips") or [])
    else:
        failures.append(f"intake_policy_missing:{doc.get('intake_policy_ref')}")

    pin_paths_by_slot: dict[str, set[str]] = {}
    for slot_id, slot in slots.items():
        if not isinstance(slot, dict):
            failures.append(f"slot_invalid:{slot_id}")
            continue
        for ref_key in ("inventory_artifact_ref", "contract_ref"):
            ref = slot.get(ref_key)
            if ref and not (ROOT / str(ref)).is_file():
                failures.append(f"missing_{ref_key}:{slot_id}:{ref}")
        pin = slot.get("knowledge_pin")
        if isinstance(pin, dict):
            for ref_key in ("freeze_manifest_ref", "freeze_checker", "integrity_guard_module"):
                ref = pin.get(ref_key)
                if ref and not (ROOT / str(ref)).is_file():
                    failures.append(f"missing_pin_{ref_key}:{slot_id}:{ref}")
            manifest_ref = pin.get("freeze_manifest_ref")
            if manifest_ref:
                pin_paths_by_slot[slot_id] = _pin_paths(str(manifest_ref))
        lane = slot.get("spec_gap_intake_lane")
        intent = slot.get("spec_gap_intent_chip")
        if lane and intake_lanes and lane not in intake_lanes:
            failures.append(f"intake_lane_unknown:{slot_id}:{lane}")
        if intent and intake_intents and intent not in intake_intents:
            failures.append(f"intake_intent_unknown:{slot_id}:{intent}")
        if not lane and not intent:
            failures.append(f"intake_mapping_missing:{slot_id}")

    logos_paths = pin_paths_by_slot.get("logos", set())
    enterprise_paths = pin_paths_by_slot.get("enterprise_herbs_formulas", set())
    overlap = logos_paths & enterprise_paths
    if overlap:
        failures.append("pin_path_overlap:" + ",".join(sorted(overlap)[:5]))

    ok = not failures
    return {
        "schema": "jema_os_domain_plugin_registry_v2_check_v1",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "send_gate": "HOLD",
        "research_only": True,
        "registry_ref": str(
            doc.get("reproduce_command") or "docs/final/artifacts/jema_os_domain_plugin_registry_v2_latest.json"
        ),
        "slot_ids": sorted(slots.keys()),
        "failures": failures,
        "pin_isolation": {
            "logos_asset_count": len(logos_paths),
            "enterprise_asset_count": len(enterprise_paths),
            "overlap_count": len(overlap),
        },
        "reproduce": "py scripts/check_jema_os_domain_plugin_registry_v2.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.registry.is_file():
        print(f"Missing registry: {args.registry}", file=sys.stderr)
        return 2
    doc = json.loads(args.registry.read_text(encoding="utf-8"))
    report = check_registry(doc)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not report["ok"]:
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
