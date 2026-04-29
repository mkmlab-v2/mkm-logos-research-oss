#!/usr/bin/env python3
"""Authorize Sasang promotion to Track A (human-gated artifact)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_READY = ART / "sasang_commercialization_readiness_packet_latest.json"
DEFAULT_SIGNOFF = ART / "sasang_human_signoff_latest.json"
DEFAULT_DRIFT = ART / "sasang_ready_drift_check_latest.json"
DEFAULT_OUT = ART / "sasang_promotion_authorization_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ready", type=Path, default=DEFAULT_READY)
    ap.add_argument("--signoff", type=Path, default=DEFAULT_SIGNOFF)
    ap.add_argument("--drift", type=Path, default=DEFAULT_DRIFT)
    ap.add_argument("--authorizer", default="user-approved")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for p in (args.ready, args.signoff, args.drift):
        if not p.is_file():
            print(f"ERROR: missing required artifact: {p}")
            return 2

    ready = json.loads(args.ready.read_text(encoding="utf-8"))
    signoff = json.loads(args.signoff.read_text(encoding="utf-8"))
    drift = json.loads(args.drift.read_text(encoding="utf-8"))

    ready_ok = str(ready.get("decision") or "") == "READY" and bool((ready.get("go_no_go") or {}).get("go"))
    signoff_ok = str(signoff.get("decision") or "").upper() == "APPROVED"
    drift_ok = not bool(drift.get("drift_detected"))
    allow = ready_ok and signoff_ok and drift_ok

    payload = {
        "schema": "sasang_promotion_authorization_v1",
        "authorized_at_utc": _now(),
        "authorizer": args.authorizer,
        "checks": {
            "ready_ok": ready_ok,
            "signoff_ok": signoff_ok,
            "drift_ok": drift_ok,
        },
        "promotion_to_a_track_allowed": allow,
        "notes": [
            "This is a human-gated authorization artifact.",
            "Track B autobind remains forbidden without this explicit authorization.",
        ],
        "inputs": {
            "ready_packet": str(args.ready.resolve()),
            "human_signoff": str(args.signoff.resolve()),
            "drift_check": str(args.drift.resolve()),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"promotion_to_a_track_allowed={allow}")
    return 0 if allow else 1


if __name__ == "__main__":
    raise SystemExit(main())
