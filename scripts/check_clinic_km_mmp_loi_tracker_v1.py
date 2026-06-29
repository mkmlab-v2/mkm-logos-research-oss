#!/usr/bin/env python3
"""Validate clinic_km_mmp_loi_tracker_v1_latest.json structure."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs/final/artifacts/clinic_km_mmp_loi_tracker_v1_latest.json"


def main() -> int:
    if not TRACKER.is_file():
        print(f"MISSING: {TRACKER}")
        return 1
    doc = json.loads(TRACKER.read_text(encoding="utf-8"))
    if doc.get("schema") != "clinic_km_mmp_loi_tracker_v1":
        print("FAIL: schema")
        return 1
    slots = doc.get("slots")
    if not isinstance(slots, list) or len(slots) != 5:
        print("FAIL: slots must be 5")
        return 1
    received = sum(1 for s in slots if s.get("status") == "received")
    summary = doc.get("summary") or {}
    if summary.get("received") != received:
        print(f"FAIL: summary.received {summary.get('received')} != {received}")
        return 1
    if summary.get("target_met") is not False and received < 5:
        if summary.get("target_met") is True:
            print("FAIL: target_met true but received < 5")
            return 1
    readiness = doc.get("readiness")
    if readiness is not None:
        if not isinstance(readiness, dict):
            print("FAIL: readiness must be object")
            return 1
        for key in (
            "ok",
            "landing_gate_ok",
            "figma_reverse_sync_ok",
            "commander_unfreeze_required",
            "external_send_blocked",
        ):
            if key not in readiness:
                print(f"FAIL: readiness missing {key}")
                return 1
        if readiness.get("external_send_blocked") is not True:
            print("FAIL: external_send_blocked must be true while frozen_deferred")
            return 1
        if doc.get("ready_for_external_send") is True:
            print("FAIL: ready_for_external_send must stay false")
            return 1
    print(
        json.dumps(
            {
                "ok": True,
                "received": received,
                "pending": 5 - received,
                "readiness_ok": (readiness or {}).get("ok"),
                "path": str(TRACKER),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
