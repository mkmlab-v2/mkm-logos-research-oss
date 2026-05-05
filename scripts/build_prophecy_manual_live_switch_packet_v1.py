#!/usr/bin/env python3
"""Build final manual live-switch packet for prophecy track."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_ENABLE_CHECKLIST = ART / "prophecy_live_enable_checklist_v1_latest.json"
DEFAULT_ENABLE_EVENT = ART / "prophecy_live_enable_event_v1_latest.json"
DEFAULT_ROLLBACK_POLICY = ART / "prophecy_live_rollback_policy_v1_latest.json"
DEFAULT_RELEASE_PACKET = ART / "prophecy_release_signoff_packet_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_manual_live_switch_packet_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--enable-checklist", type=Path, default=DEFAULT_ENABLE_CHECKLIST)
    ap.add_argument("--enable-event", type=Path, default=DEFAULT_ENABLE_EVENT)
    ap.add_argument("--rollback-policy", type=Path, default=DEFAULT_ROLLBACK_POLICY)
    ap.add_argument("--release-packet", type=Path, default=DEFAULT_RELEASE_PACKET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    checklist = _load(args.enable_checklist)
    event = _load(args.enable_event)
    rollback = _load(args.rollback_policy)
    release = _load(args.release_packet)

    ready = bool((checklist.get("summary") or {}).get("ready_to_enable_live"))
    approved = str(event.get("decision") or "").upper() == "APPROVED"
    rollback_ok = str(rollback.get("schema") or "") == "prophecy_live_rollback_policy_v1"
    release_ok = str(release.get("status") or "") == "READY_FOR_RELEASE_SIGNOFF"
    switch_ready = ready and approved and rollback_ok and release_ok

    payload = {
        "schema": "prophecy_manual_live_switch_packet_v1",
        "generated_at_utc": _now(),
        "track": "prophecy",
        "status": "READY_FOR_MANUAL_LIVE_SWITCH" if switch_ready else "HOLD",
        "inputs": {
            "enable_checklist": str(args.enable_checklist).replace("\\", "/"),
            "enable_event": str(args.enable_event).replace("\\", "/"),
            "rollback_policy": str(args.rollback_policy).replace("\\", "/"),
            "release_packet": str(args.release_packet).replace("\\", "/"),
        },
        "checks": {
            "enable_checklist_ready": ready,
            "live_enable_event_approved": approved,
            "rollback_policy_present": rollback_ok,
            "release_signoff_ready": release_ok,
        },
        "manual_execution_contract": {
            "auto_live_switch": False,
            "requires_operator_manual_action": True,
            "requires_post_switch_smoke_check": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"status={payload['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
