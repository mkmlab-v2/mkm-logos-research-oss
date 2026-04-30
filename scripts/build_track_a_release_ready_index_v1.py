#!/usr/bin/env python3
"""Build release-ready index for Track A candidates."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_QUEUE = ART / "track_a_promotion_queue_v1_latest.json"
DEFAULT_PROPHECY_PACKET = ART / "prophecy_release_signoff_packet_v1_latest.json"
DEFAULT_PROPHECY_SIGNOFF = ART / "prophecy_release_human_signoff_v1_latest.json"
DEFAULT_OUT = ART / "track_a_release_ready_index_v1_latest.json"


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
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--prophecy-packet", type=Path, default=DEFAULT_PROPHECY_PACKET)
    ap.add_argument("--prophecy-signoff", type=Path, default=DEFAULT_PROPHECY_SIGNOFF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    queue = _load(args.queue)
    prophecy_packet = _load(args.prophecy_packet)
    prophecy_signoff = _load(args.prophecy_signoff)

    prophecy_ready = str(prophecy_packet.get("status") or "") == "READY_FOR_RELEASE_SIGNOFF"
    prophecy_signoff_ok = str(prophecy_signoff.get("decision") or "").upper() == "APPROVED"

    index = {
        "schema": "track_a_release_ready_index_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "inputs": {
            "queue": str(args.queue).replace("\\", "/"),
            "prophecy_packet": str(args.prophecy_packet).replace("\\", "/"),
            "prophecy_signoff": str(args.prophecy_signoff).replace("\\", "/"),
        },
        "tracks": {
            "prophecy": {
                "queue_status": (((queue.get("tracks") or {}).get("prophecy") or {}).get("status")),
                "release_packet_status": prophecy_packet.get("status"),
                "human_signoff_decision": prophecy_signoff.get("decision"),
                "ready": bool(prophecy_ready and prophecy_signoff_ok),
            },
            "lg_washer": {
                "queue_status": (((queue.get("tracks") or {}).get("lg_washer") or {}).get("status")),
                "ready": False,
                "note": "closed_submitted",
            },
        },
        "summary": {
            "ready_tracks": ["prophecy"] if (prophecy_ready and prophecy_signoff_ok) else [],
            "ready_count": 1 if (prophecy_ready and prophecy_signoff_ok) else 0,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"ready_count={index['summary']['ready_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
