#!/usr/bin/env python3
"""Build per-track Track-A promotion queue from separated signoff packet."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_IN = ART / "btrack_promotion_signoff_packet_separated_v1_latest.json"
DEFAULT_OUT = ART / "track_a_promotion_queue_v1_latest.json"


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

    doc = _read_json(args.signoff_json)
    ts = doc.get("track_status") if isinstance(doc.get("track_status"), dict) else {}
    prophecy = ts.get("prophecy") if isinstance(ts.get("prophecy"), dict) else {}
    lg = ts.get("lg_washer") if isinstance(ts.get("lg_washer"), dict) else {}

    queue = {
        "schema": "track_a_promotion_queue_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {"signoff_json": str(args.signoff_json.resolve())},
        "tracks": {
            "lg_washer": {
                "status": "READY_FOR_HUMAN_REVIEW"
                if str(lg.get("decision") or "") == "READY_FOR_HUMAN_SIGNOFF"
                else "HOLD",
                "decision": lg.get("decision"),
                "blockers": lg.get("blockers") or [],
                "next_actions_ko": lg.get("next_actions_ko") or [],
                "candidate_artifact": "docs/final/artifacts/lg_washer_track_a_candidate_pre_review_v1_latest.json",
            },
            "prophecy": {
                "status": "READY_FOR_HUMAN_REVIEW"
                if str(prophecy.get("decision") or "") == "READY_FOR_HUMAN_SIGNOFF"
                else "HOLD",
                "decision": prophecy.get("decision"),
                "blockers": prophecy.get("blockers") or [],
                "next_actions_ko": prophecy.get("next_actions_ko") or [],
                "candidate_artifact": "docs/final/artifacts/prophecy_track_a_candidate_pre_review_v1_latest.json",
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
