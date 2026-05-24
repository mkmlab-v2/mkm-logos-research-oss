#!/usr/bin/env python3
"""Apply human-approved rows to comp_anchor08 seed queue (B-track only, no Track A)."""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "reports/constitution/btrack_pilot/comp_anchor08_seed_curation_queue_v1.json"
OUT_APPLIED = ROOT / "reports/constitution/btrack_pilot/comp_anchor08_seed_curation_applied_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _approve_first_verified(row: dict) -> dict:
    verified = list(row.get("verified_in_codebook") or [])
    if not verified:
        return {**row, "human_status": "rejected", "reviewer_note": "no verified_in_codebook"}
    return {
        **row,
        "human_status": "approved",
        "approved_codebook_atom_id": str(verified[0]),
        "reviewer_note": "commander_bulk_approve_first_verified",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commander-approve-all",
        action="store_true",
        help="Set all pending rows approved with first verified_in_codebook atom_id",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not QUEUE.is_file():
        print(json.dumps({"error": f"missing {QUEUE}"}, ensure_ascii=False))
        return 2

    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue = list(doc.get("queue") or [])
    if args.commander_approve_all:
        new_queue = []
        for row in queue:
            if str(row.get("human_status")) == "pending":
                new_queue.append(_approve_first_verified(row))
            else:
                new_queue.append(row)
        queue = new_queue

    approved = [q for q in queue if q.get("human_status") == "approved"]
    pending = [q for q in queue if q.get("human_status") == "pending"]
    applied = {
        "schema": "comp_anchor08_seed_curation_applied_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_wall": {
            "track_a_auto_promotion": False,
            "live_codebook_merge": False,
        },
        "approved_count": len(approved),
        "pending_count": len(pending),
        "approved_rows": approved,
        "note": "Registry English labels mapped to hebrew:: codebook atoms only; not must_keep or Track A.",
    }

    if args.dry_run:
        print(json.dumps({"dry_run": True, "applied": applied}, ensure_ascii=False, indent=2))
        return 0

    doc["queue"] = queue
    doc["pending_count"] = len(pending)
    doc["approved_count"] = len(approved)
    doc["commander_approved_at_utc"] = _utc() if args.commander_approve_all else doc.get("commander_approved_at_utc")
    QUEUE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_APPLIED.write_text(json.dumps(applied, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote_queue": str(QUEUE.relative_to(ROOT)),
                "wrote_applied": str(OUT_APPLIED.relative_to(ROOT)),
                "approved": len(approved),
                "pending": len(pending),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
