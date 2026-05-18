#!/usr/bin/env python3
"""Record commander authorization to submit RQ-019 pack to legal (not counsel approval)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_handoff_pack_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_commander_legal_submission_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build(*, note: str = "") -> dict[str, Any]:
    if not HANDOFF.is_file():
        raise FileNotFoundError(f"missing handoff pack: {HANDOFF}")
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    return {
        "schema": "mkm_inter_agent_commander_legal_submission_v1",
        "generated_at_utc": _utc_now(),
        "classification": "INTERNAL_ONLY",
        "commander_authorized_legal_submission": True,
        "submitted_at_utc": _utc_now(),
        "legal_review_status": "SUBMITTED_TO_COUNSEL",
        "is_counsel_signoff": False,
        "handoff_pointer": (
            HANDOFF.relative_to(ROOT).as_posix()
            if HANDOFF.is_relative_to(ROOT)
            else str(HANDOFF)
        ),
        "manifest_pointer": (
            "docs/final/artifacts/mkm_inter_agent_counsel_export_manifest_v1_latest.json"
        ),
        "technical_closure_ready": handoff.get("technical_closure_ready"),
        "rq_019_status": "OPEN",
        "boundary_ack": (
            "Commander authorized internal submission to legal review. "
            "This is not counsel written approval. RQ-019 remains OPEN until checklist item 7."
        ),
        "submission_note": (note or "").strip() or None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--note", default="commander authorized counsel handoff 2026-05-18")
    args = ap.parse_args()
    doc = build(note=args.note)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output": str(args.out_json), "legal_review_status": doc["legal_review_status"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
