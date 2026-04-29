#!/usr/bin/env python3
"""Check READY drift against strict gate and readiness packet."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_READY = ART / "sasang_commercialization_readiness_packet_latest.json"
DEFAULT_STRICT = ART / "sasang_high_reliability_gate_strict_latest.json"
DEFAULT_OUT = ART / "sasang_ready_drift_check_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ready-packet", type=Path, default=DEFAULT_READY)
    ap.add_argument("--strict-gate", type=Path, default=DEFAULT_STRICT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.ready_packet.is_file() or not args.strict_gate.is_file():
        print("ERROR: required artifacts missing")
        return 2
    ready = json.loads(args.ready_packet.read_text(encoding="utf-8"))
    strict = json.loads(args.strict_gate.read_text(encoding="utf-8"))

    ready_decision = str(ready.get("decision") or "")
    go = bool((ready.get("go_no_go") or {}).get("go"))
    strict_decision = str(strict.get("decision") or "")
    drift = not (ready_decision == "READY" and go and strict_decision == "PASS")

    payload = {
        "schema": "sasang_ready_drift_check_v1",
        "checked_at_utc": _now(),
        "ready_packet_path": str(args.ready_packet.resolve()),
        "strict_gate_path": str(args.strict_gate.resolve()),
        "snapshot": {
            "ready_decision": ready_decision,
            "ready_go": go,
            "strict_decision": strict_decision,
        },
        "drift_detected": drift,
        "status": "DRIFT" if drift else "STABLE_READY",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0 if not drift else 1


if __name__ == "__main__":
    raise SystemExit(main())
