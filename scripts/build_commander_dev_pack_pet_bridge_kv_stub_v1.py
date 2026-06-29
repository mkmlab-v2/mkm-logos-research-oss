#!/usr/bin/env python3
"""RQ-027 pet KV injection stub — parallel channels, no commander→pet merge [HYPO].

Builds:
  - operator dev channel (commander-dev) — local JSON only
  - pet [TARGET] bridge request dry-run (pet slots only)
  - KV path plan (stub_only, no remote write)

Output: reports/commander_dev_pack_pet_bridge_kv_stub_latest.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_pet_companion_device_bridge_live_v1 import (  # noqa: E402
    build_request_from_artifacts,
)

DEFAULT_PACK = ROOT / "reports" / "commander_dev_day_pack_latest.json"
DEFAULT_OUT = ROOT / "reports" / "commander_dev_pack_pet_bridge_kv_stub_latest.json"
MAP_PATH = ROOT / "docs" / "final" / "artifacts" / "commander_dev_pack_pet_bridge_field_map_v1.json"
FIXTURE = ROOT / "docs/final/artifacts/fixtures/pet_companion_device_memory_bridge_v1_fixture.json"
SLOTS_FALLBACK = ROOT / "docs/final/artifacts/fixtures/pet_companion_memory_slots_demo_fallback_v1.json"
BRIDGE_DRY_OUT = ROOT / "reports" / "tmp" / "commander_dev_pack_pet_bridge_request_dry_run_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _target_profile_id() -> str:
    return (os.getenv("MKM_PET_BRIDGE_TARGET_PROFILE_ID") or "pet-demo-001").strip()


def _target_subject_label() -> str:
    return (os.getenv("MKM_PET_BRIDGE_TARGET_SUBJECT") or "[TARGET]").strip()


def _operator_slots(pack: Dict[str, Any]) -> List[Dict[str, Any]]:
    dev = pack.get("developer_coaching") or {}
    energy = pack.get("energy_pacing") or {}
    four = pack.get("four_ai_roles_for_dev") or {}
    slots: List[Dict[str, Any]] = []
    if dev.get("one_line"):
        slots.append(
            {
                "slot_id": "commander-dev:developer_focus",
                "subject": "commander-dev",
                "fact_summary": str(dev["one_line"])[:200],
                "confidence_tier": "SLOT_OPERATOR_HYPO",
            }
        )
    if energy.get("summary"):
        slots.append(
            {
                "slot_id": "commander-dev:energy_pacing",
                "subject": "commander-dev",
                "fact_summary": str(energy["summary"])[:200],
                "confidence_tier": "SLOT_OPERATOR_HYPO",
            }
        )
    if four.get("taeyang"):
        slots.append(
            {
                "slot_id": "commander-dev:four_ai_taeyang",
                "subject": "commander-dev",
                "fact_summary": str(four["taeyang"])[:200],
                "confidence_tier": "SLOT_OPERATOR_HYPO",
            }
        )
    return slots


def _mapping_audit() -> List[Dict[str, Any]]:
    doc = _read_json(MAP_PATH)
    rows = []
    for m in doc.get("mappings") or []:
        if not isinstance(m, dict):
            continue
        transform = m.get("transform")
        rows.append(
            {
                "row": m.get("row"),
                "commander_path": m.get("commander_dev_pack_path"),
                "pet_target": m.get("pet_bridge_target"),
                "transform": transform,
                "stub_applied": transform in (
                    "parallel_pattern_only",
                    "copy_flags_only",
                    "separate_ids",
                    "SLOT_VERIFIED_pattern",
                    "enum_map",
                    "research_analog",
                    "human_channel_only",
                ),
                "blocked": transform in ("blocked", "must_not_merge", "forbidden"),
            }
        )
    return rows


def _commander_leak_in_pet_request(bridge_req: Dict[str, Any]) -> bool:
    """True if pet bridge body appears to contain commander 명리 / birth leakage."""
    blob = json.dumps(bridge_req, ensure_ascii=False)
    forbidden = ("경진", "무인", "계축", "갑자", "만세력", "일간 경", "지휘관", "commander-dev")
    return any(tok in blob for tok in forbidden)


def build_stub(
    *,
    pack_path: Path,
    slots_path: Path,
    pet_profile_id: str,
    write_bridge_dry: bool,
) -> Dict[str, Any]:
    pack = _read_json(pack_path)
    pet_pid = pet_profile_id or _target_profile_id()
    subject_label = _target_subject_label()

    bridge_req = build_request_from_artifacts(
        fixture_path=FIXTURE,
        slots_path=slots_path,
        profile_id=pet_pid,
        scenario="health_check",
        question_masked=f"{subject_label} 반려 동물 건강·루틴 관찰(마스킹·스텁) [HYPO]",
    )
    bridge_req["request_id"] = f"req-rq027-stub-{uuid.uuid4().hex[:12]}"
    bridge_req["client_ts_utc"] = _utc_now()

    injection = bridge_req.get("memory_context_injection") or {}
    extracted = injection.get("extracted_slots") if isinstance(injection.get("extracted_slots"), list) else []
    for slot in extracted:
        if isinstance(slot, dict) and subject_label != pet_pid:
            slot["subject"] = subject_label

    leak = _commander_leak_in_pet_request(bridge_req)

    if write_bridge_dry:
        BRIDGE_DRY_OUT.parent.mkdir(parents=True, exist_ok=True)
        BRIDGE_DRY_OUT.write_text(json.dumps(bridge_req, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    trust = pack.get("trust_packet_v2") if isinstance(pack.get("trust_packet_v2"), dict) else {}

    return {
        "schema": "commander_dev_pack_pet_bridge_kv_stub_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "rq_id": "RQ-027",
        "commander_to_pet_merge_forbidden": True,
        "integrity_check": {
            "commander_leak_in_pet_request": leak,
            "pass": not leak,
        },
        "pack_ref": str(pack_path.name),
        "pet_target": {
            "profile_id": pet_pid,
            "subject_placeholder": subject_label,
        },
        "operator_channel": {
            "profile_id": "commander-dev",
            "channel": "operator_dev_coach",
            "must_not_forward_to_pet_bridge": True,
            "slots": _operator_slots(pack),
        },
        "pet_kv_injection_plan": {
            "write_mode": "stub_only_no_remote_kv",
            "kv_prefix": "pet_companion/",
            "coach_events_path_pattern": "pet_companion/coach_events/{profile_id}/{event_id}.json",
            "profile_path_pattern": "pet_companion/profile/{profile_id}.json",
            "planned_event_id": f"stub-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
            "telemetry_only_fields": [
                "profile_id",
                "scenario",
                "status",
                "memory_context_injected",
            ],
        },
        "pet_bridge_request_dry_run": {
            "out_path": str(BRIDGE_DRY_OUT.relative_to(ROOT)).replace("\\", "/"),
            "schema": bridge_req.get("schema"),
            "request_id": bridge_req.get("request_id"),
            "profile_id": bridge_req.get("profile_id"),
            "scenario": bridge_req.get("scenario"),
            "slots_count": len(extracted),
            "hypothesis_tier": bridge_req.get("hypothesis_tier"),
            "research_only": bridge_req.get("research_only"),
        },
        "trust_packet_flags_aligned": {
            "hypothesis_tier": trust.get("hypothesis_tier") or pack.get("hypothesis_tier"),
            "research_only": trust.get("research_only", pack.get("research_only")),
            "non_gating": trust.get("non_gating", pack.get("non_gating")),
        },
        "mapping_audit": _mapping_audit(),
        "field_map_ref": str(MAP_PATH.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--slots-json", type=Path, default=SLOTS_FALLBACK)
    ap.add_argument("--pet-profile-id", default="")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--no-write-bridge-json", action="store_true")
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    pack_path = args.pack_json if args.pack_json.is_absolute() else ROOT / args.pack_json
    if not pack_path.is_file():
        print(f"MISSING: {pack_path}", flush=True)
        return 2

    slots_path = args.slots_json if args.slots_json.is_absolute() else ROOT / args.slots_json
    payload = build_stub(
        pack_path=pack_path,
        slots_path=slots_path,
        pet_profile_id=args.pet_profile_id or _target_profile_id(),
        write_bridge_dry=not args.no_write_bridge_json,
    )

    if payload["integrity_check"].get("commander_leak_in_pet_request"):
        print("WARN: integrity_check detected commander tokens in pet bridge — review dry-run JSON", flush=True)

    if not args.stdout_only:
        out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {out}")
    print(json.dumps({"ok": True, "pass": payload["integrity_check"]["pass"]}, ensure_ascii=False))
    return 0 if payload["integrity_check"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
