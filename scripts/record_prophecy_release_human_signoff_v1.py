#!/usr/bin/env python3
"""Record human release sign-off event for prophecy approved candidate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_CHECKLIST = ART / "prophecy_approved_candidate_release_checklist_v1_latest.json"
DEFAULT_CANDIDATE = ART / "prophecy_track_a_candidate_v1_latest.json"
DEFAULT_OUT = ART / "prophecy_release_human_signoff_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checklist", type=Path, default=DEFAULT_CHECKLIST)
    ap.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision", choices=("APPROVED", "REJECTED"), default="APPROVED")
    ap.add_argument("--evidence-bundle", default="docs/final/artifacts/prophecy_track_a_candidate_v1_latest.json")
    ap.add_argument("--rollback-trigger", default="revert_to_btrack_candidate_only_on_release_regression")
    ap.add_argument("--note", default="Human release sign-off approved in-chat.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    checklist = _load(args.checklist)
    candidate = _load(args.candidate)

    payload = {
        "schema": "prophecy_release_human_signoff_v1",
        "recorded_at_utc": _now(),
        "track": "prophecy",
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
        "release_controls": {
            "evidence_bundle": args.evidence_bundle,
            "rollback_trigger": args.rollback_trigger,
        },
        "constraints": {
            "auto_release_enabled": False,
            "human_review_required_each_release": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision={args.decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
