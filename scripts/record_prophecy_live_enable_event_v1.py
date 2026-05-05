#!/usr/bin/env python3
"""Record explicit live-enable approval event for prophecy track."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "prophecy_live_enable_event_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="PRO")
    ap.add_argument("--decision", choices=("APPROVED", "REJECTED"), default="APPROVED")
    ap.add_argument("--evidence-bundle", default="docs/final/artifacts/prophecy_release_signoff_packet_v1_latest.json")
    ap.add_argument("--rollback-trigger", default="disable_live_on_gate_fail_or_loss_threshold_breach")
    ap.add_argument("--note", default="Explicit user approval for live enable.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload = {
        "schema": "prophecy_live_enable_event_v1",
        "recorded_at_utc": _now(),
        "track": "prophecy",
        "reviewer": args.reviewer,
        "decision": args.decision,
        "evidence_bundle": args.evidence_bundle,
        "rollback_trigger": args.rollback_trigger,
        "note": args.note,
        "constraints": {
            "auto_enable_live": False,
            "human_approval_mandatory": True,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"decision={args.decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
