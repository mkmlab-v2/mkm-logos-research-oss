#!/usr/bin/env python3
"""Emit lg_washer Track A candidate pre-review artifact when signoff says READY."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_IN = ART / "btrack_promotion_signoff_packet_separated_v1_latest.json"
DEFAULT_OUT = ART / "lg_washer_track_a_candidate_pre_review_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--signoff-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    signoff = _read_json(args.signoff_json)
    track = ((signoff.get("track_status") or {}).get("lg_washer") or {}) if isinstance(signoff, dict) else {}
    decision = str(track.get("decision") or "")
    ready = decision == "READY_FOR_HUMAN_SIGNOFF"

    doc = {
        "schema": "lg_washer_track_a_candidate_pre_review_v1",
        "generated_at_utc": _now(),
        "status": "PRE_REVIEW_CANDIDATE" if ready else "HOLD",
        "source_track": "B",
        "decision_snapshot": decision,
        "blockers": track.get("blockers") or [],
        "next_actions_ko": track.get("next_actions_ko") or [],
        "runtime_constraints": {
            "track_b_to_a_auto_bridge": False,
            "live_trigger_auto_enabled": False,
            "human_signoff_required": True,
        },
        "evidence": {
            "signoff_packet": str(args.signoff_json.resolve()),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
