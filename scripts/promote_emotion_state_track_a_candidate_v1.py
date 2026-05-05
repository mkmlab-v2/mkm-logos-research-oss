#!/usr/bin/env python3
"""Promote emotion-state Track A candidate after human release sign-off."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CANDIDATE = ART / "emotion_state_track_a_candidate_latest.json"
DEFAULT_LOCK = ART / "emotion_state_manual_promotion_decision_lock_latest.json"
DEFAULT_SIGNOFF = ART / "emotion_state_release_human_signoff_latest.json"
DEFAULT_CHECKLIST = ART / "emotion_state_approved_candidate_release_checklist_latest.json"
DEFAULT_OUT = ART / "emotion_state_track_a_promoted_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--manual-lock", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--human-signoff", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--release-checklist", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    candidate = _load_json(args.candidate)
    lock = _load_json(args.manual_lock)
    signoff = _load_json(args.human_signoff)
    checklist = _load_json(args.release_checklist)

    checks = {
        "candidate_approved": str(candidate.get("status") or "") == "APPROVED_CANDIDATE",
        "manual_lock_approved": str(lock.get("final_decision") or "") == "approved",
        "human_signoff_approved": str(signoff.get("decision") or "").upper() == "APPROVED",
        "checklist_ready_for_release_signoff": bool((checklist.get("summary") or {}).get("ready_for_release_signoff")),
    }
    promoted = all(checks.values())

    out = {
        "schema": "emotion_state_track_a_promoted_v1",
        "promoted_at_utc": _now(),
        "status": "PROMOTED_TRACK_A_CANDIDATE" if promoted else "HOLD",
        "checks": checks,
        "inputs": {
            "candidate": str(args.candidate.resolve()),
            "manual_lock": str(args.manual_lock.resolve()),
            "human_signoff": str(args.human_signoff.resolve()),
            "release_checklist": str(args.release_checklist.resolve()),
        },
        "constraints": {
            "auto_release_enabled": False,
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_review_required_each_release": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.out), "status": out["status"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
