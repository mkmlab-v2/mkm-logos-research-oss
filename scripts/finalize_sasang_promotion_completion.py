#!/usr/bin/env python3
"""Finalize Sasang promotion completion artifact (human-approved)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_AUTH = ART / "sasang_promotion_authorization_latest.json"
DEFAULT_READY = ART / "sasang_commercialization_readiness_packet_latest.json"
DEFAULT_OUT = ART / "sasang_promotion_completion_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--authorization", type=Path, default=DEFAULT_AUTH)
    ap.add_argument("--ready", type=Path, default=DEFAULT_READY)
    ap.add_argument("--operator", default="user-approved")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.authorization.is_file() or not args.ready.is_file():
        print("ERROR: missing authorization or readiness artifact")
        return 2
    auth = json.loads(args.authorization.read_text(encoding="utf-8"))
    ready = json.loads(args.ready.read_text(encoding="utf-8"))

    auth_ok = bool(auth.get("promotion_to_a_track_allowed"))
    ready_ok = str(ready.get("decision") or "") == "READY" and bool((ready.get("go_no_go") or {}).get("go"))
    completed = auth_ok and ready_ok

    payload = {
        "schema": "sasang_promotion_completion_v1",
        "completed_at_utc": _now(),
        "operator": args.operator,
        "checks": {"authorization_ok": auth_ok, "readiness_ok": ready_ok},
        "promotion_completed": completed,
        "inputs": {
            "authorization": str(args.authorization.resolve()),
            "readiness": str(args.ready.resolve()),
        },
        "note": "Human-approved completion marker for commercialization promotion.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"promotion_completed={completed}")
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
