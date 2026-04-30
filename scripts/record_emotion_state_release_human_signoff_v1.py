#!/usr/bin/env python3
"""Record human release sign-off for emotion-state approved candidate."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_CHECKLIST = ART / "emotion_state_approved_candidate_release_checklist_latest.json"
DEFAULT_CANDIDATE = ART / "emotion_state_track_a_candidate_latest.json"
DEFAULT_OUT = ART / "emotion_state_release_human_signoff_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision", choices=("APPROVED", "REJECTED"), default="APPROVED")
    ap.add_argument("--note", default="Human release sign-off approved in-chat.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    checklist = _load(args.checklist)
    candidate = _load(args.candidate)
    payload = {
        "schema": "emotion_state_release_human_signoff_v1",
        "recorded_at_utc": _now(),
        "track": "emotion_state_control",
        "reviewer": args.reviewer,
        "decision": args.decision,
        "note": args.note,
        "inputs": {
            "checklist": str(args.checklist.resolve()),
            "candidate": str(args.candidate.resolve()),
        },
        "snapshot": {
            "candidate_status": candidate.get("status"),
            "checklist_ready_for_release_signoff": (checklist.get("summary") or {}).get("ready_for_release_signoff"),
        },
        "constraints": {
            "auto_release_enabled": False,
            "human_review_required_each_release": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.out), "decision": args.decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
