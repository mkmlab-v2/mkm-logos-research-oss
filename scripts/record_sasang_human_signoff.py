#!/usr/bin/env python3
"""Record human sign-off for Sasang commercialization readiness."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_READY = ART / "sasang_commercialization_readiness_packet_latest.json"
DEFAULT_OUT = ART / "sasang_human_signoff_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ready-packet", type=Path, default=DEFAULT_READY)
    ap.add_argument("--approver", default="user-approved")
    ap.add_argument("--decision", choices=("APPROVED", "REJECTED"), default="APPROVED")
    ap.add_argument("--note", default="Manual sign-off recorded after READY packet review.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.ready_packet.is_file():
        print(f"ERROR: missing readiness packet: {args.ready_packet}")
        return 2
    ready = json.loads(args.ready_packet.read_text(encoding="utf-8"))

    payload = {
        "schema": "sasang_human_signoff_v1",
        "recorded_at_utc": _now(),
        "approver": args.approver,
        "decision": args.decision,
        "note": args.note,
        "readiness_packet_path": str(args.ready_packet.resolve()),
        "readiness_decision_snapshot": ready.get("decision"),
        "go_snapshot": (ready.get("go_no_go") or {}).get("go"),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
