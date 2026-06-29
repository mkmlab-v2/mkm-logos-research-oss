#!/usr/bin/env python3
"""Append internal B2B Graph Studio pilot session outcome (no external SEND)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_LATEST = ROOT / "reports/logos_graph_studio_pilot_session_v1_latest.json"
OUT_LOG = ROOT / "reports/logos_graph_studio_pilot_session_log_v1.jsonl"
APPROVAL = ROOT / "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json"
PREFLIGHT = ROOT / "reports/logos_graph_studio_b2b_pilot_day_preflight_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--outcome",
        required=True,
        choices=("completed", "deferred", "cancelled", "no_show"),
    )
    ap.add_argument("--attendees", default="", help="Comma-separated attendee labels (internal only).")
    ap.add_argument("--notes", default="", help="Free-text debrief (no PII).")
    ap.add_argument(
        "--follow-up",
        default="",
        help="Next action one-liner (e.g. SOW revision, second demo).",
    )
    args = ap.parse_args()

    doc: dict[str, Any] = {
        "schema": "logos_graph_studio_pilot_session_v1",
        "recorded_at_utc": _utc(),
        "outcome": args.outcome,
        "attendees": [a.strip() for a in args.attendees.split(",") if a.strip()],
        "notes": args.notes.strip(),
        "follow_up": args.follow_up.strip(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "demo_primary_url": (
            "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
            "?preset=job_job_suffering_reason"
        ),
        "evidence_pointers": {
            "commander_approval": str(APPROVAL.relative_to(ROOT)).replace("\\", "/"),
            "pilot_day_preflight": str(PREFLIGHT.relative_to(ROOT)).replace("\\", "/")
            if PREFLIGHT.is_file()
            else None,
            "b2b_rehearsal_live": "reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json",
        },
        "boundary_ack": (
            "Session log is internal ops only. Does not open external SEND or billing."
        ),
    }

    approval = _load(APPROVAL)
    doc["commander_signoff_at_record"] = bool(approval.get("commander_signoff"))

    OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_LATEST.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_LOG.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(OUT_LATEST),
                "outcome": args.outcome,
                "send_gate": "HOLD",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
