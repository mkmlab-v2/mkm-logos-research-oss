#!/usr/bin/env python3
"""Refresh clinic_km_mmp_loi_tracker_v1_latest.json readiness from gate artifacts.

Preserves human-edited slots. Writes docs/final/artifacts/clinic_km_mmp_loi_tracker_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRACKER = ROOT / "docs/final/artifacts/clinic_km_mmp_loi_tracker_v1_latest.json"
LANDING_GATE = ROOT / "reports/clinic_km_mmp_landing_gate_v1_latest.json"
FIGMA_GATE = ROOT / "reports/clinic_loi_figma_reverse_sync_gate_v1_latest.json"
FIGMA_PACK = ROOT / "reports/clinic_loi_figma_reverse_sync_pack_v1_latest.json"
GLASS_CMD = ROOT / "reports/trust_composition_glass_blur_commander_visual_v1_latest.json"
FULL_CHAIN = "scripts/Run-TrustCompositionClinicLoiFull_v1.ps1"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _slot_summary(slots: list[dict[str, Any]]) -> dict[str, Any]:
    received = sum(1 for s in slots if s.get("status") == "received")
    pending = len(slots) - received
    goal = len(slots)
    return {
        "received": received,
        "pending": pending,
        "target_met": received >= goal,
    }


def build_tracker(doc: dict[str, Any]) -> dict[str, Any]:
    landing = _load_json(LANDING_GATE) or {}
    figma_gate = _load_json(FIGMA_GATE) or {}
    figma_pack = _load_json(FIGMA_PACK) or {}
    glass = _load_json(GLASS_CMD) or {}

    sync_report = figma_gate.get("sync_report") or {}
    figma_api_status = sync_report.get("figma_api_status", "unknown")

    landing_ok = bool(landing.get("ok"))
    figma_ok = bool(figma_gate.get("ok"))
    readiness_ok = landing_ok and figma_ok

    slots = doc.get("slots") or []
    if not isinstance(slots, list):
        slots = []

    doc["updated_at_utc"] = _utc()
    doc["send_gate"] = "HOLD"
    doc["lane_status"] = doc.get("lane_status") or "frozen_deferred"
    doc["ready_for_external_send"] = False

    doc["landing_gate_report"] = "reports/clinic_km_mmp_landing_gate_v1_latest.json"
    doc["landing_design_chain"] = "scripts/Run-ClinicLoiLandingDesignChain_v1.ps1"
    doc["landing_tokens_v2_dtcg"] = "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json"
    doc["figma_token_map"] = "docs/final/artifacts/clinic_loi_figma_token_map_v1.json"
    doc["figma_reverse_sync_gate"] = "reports/clinic_loi_figma_reverse_sync_gate_v1_latest.json"
    doc["figma_reverse_sync_pack"] = "reports/clinic_loi_figma_reverse_sync_pack_v1_latest.json"
    doc["figma_tokens_studio_export"] = "reports/clinic_loi_figma_tokens_studio_export_v1.json"
    doc["figma_reference_screenshot"] = "reports/clinic_loi_figma_reference_screenshot_v1.png"
    doc["figma_reverse_sync_chain"] = "scripts/Run-ClinicLoiFigmaReverseSyncAuto_v1.ps1"
    doc["full_readiness_chain"] = FULL_CHAIN

    doc["readiness"] = {
        "ok": readiness_ok,
        "landing_gate_ok": landing_ok,
        "figma_reverse_sync_ok": figma_ok,
        "figma_api_status": figma_api_status,
        "figma_live_pending": figma_api_status in ("skipped", "unknown"),
        "glass_ab_verdict": glass.get("ab_verdict", "unknown"),
        "surface_default": figma_pack.get("surface_default", "flat_baseline"),
        "commander_unfreeze_required": True,
        "external_send_blocked": True,
    }

    doc["summary"] = _slot_summary(slots)
    doc["reproduce"] = (
        "powershell -File scripts/Run-TrustCompositionClinicLoiFull_v1.ps1; "
        "py scripts/check_clinic_km_mmp_loi_tracker_v1.py"
    )
    return doc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not TRACKER.is_file():
        print(f"MISSING: {TRACKER}")
        return 1

    doc = json.loads(TRACKER.read_text(encoding="utf-8"))
    if doc.get("schema") != "clinic_km_mmp_loi_tracker_v1":
        print("FAIL: schema")
        return 1

    updated = build_tracker(doc)
    payload = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"

    if args.dry_run:
        print(payload)
        return 0

    TRACKER.write_text(payload, encoding="utf-8")
    out = {
        "ok": True,
        "path": str(TRACKER),
        "readiness_ok": updated["readiness"]["ok"],
        "figma_api_status": updated["readiness"]["figma_api_status"],
    }
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
