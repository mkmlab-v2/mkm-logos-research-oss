#!/usr/bin/env python3
"""RQ-019 closure readiness summary (OPEN until legal item 7)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HANDOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_handoff_pack_latest.json"
SIGNOFF = ROOT / "docs/final/artifacts/mkm_inter_agent_legal_counsel_signoff_v1_latest.json"
SUBMISSION = ROOT / "docs/final/artifacts/mkm_inter_agent_commander_legal_submission_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/mkm_inter_agent_counsel_export_manifest_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_closure_readiness_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def build() -> dict[str, Any]:
    handoff = _load(HANDOFF) or {}
    signoff = _load(SIGNOFF) or {}
    submission = _load(SUBMISSION) or {}
    manifest = _load(MANIFEST) or {}
    checklist = handoff.get("checklist") or []
    item7 = next((c for c in checklist if c.get("id") == 7), {})
    item7_met = bool(item7.get("met")) or bool(signoff.get("rq_019_checklist_item_7_met"))
    # Submission stays SUBMITTED_TO_COUNSEL after counsel signs; prefer signoff/handoff.
    legal_status = (
        signoff.get("legal_review_status")
        or handoff.get("legal_review_status")
        or submission.get("legal_review_status")
    )

    blockers: list[str] = []
    if not item7_met:
        blockers.append("legal_signoff_checklist_item_7")
    if legal_status not in ("APPROVED", "COUNSEL_SIGNED"):
        blockers.append(f"legal_review_status={legal_status}")

    from scripts.mkm_inter_agent_rq019_status_v1 import CLOSE as CLOSE_PATH

    close_doc = _load(CLOSE_PATH) or {}
    if close_doc.get("rq_019_closed"):
        rq_status = "CLOSED"
    elif blockers:
        rq_status = "OPEN"
    else:
        rq_status = "READY_FOR_COMMANDER_CLOSE"

    return {
        "schema": "mkm_inter_agent_rq019_closure_readiness_v1",
        "generated_at_utc": _utc_now(),
        "rq_019_status": rq_status,
        "closure_allowed": len(blockers) == 0 or close_doc.get("rq_019_closed") is True,
        "blockers": blockers,
        "legal_review_status": legal_status,
        "commander_legal_submission": submission.get("commander_authorized_legal_submission"),
        "technical_closure_ready": handoff.get("technical_closure_ready"),
        "manifest_file_count": manifest.get("file_count"),
        "next_after_counsel_approval": [
            "Run record_mkm_inter_agent_legal_counsel_signoff_v1.py with counsel reference",
            "Rebuild legal handoff pack; set RQ-019 checklist item 7 met",
            "Promote approved copy to TRACK_C / PUBLIC_FACING per agreed path only",
        ],
        "boundary_ack": "READY_FOR_COMMANDER_CLOSE is internal ops only; not auto CLOSED in RESEARCH_OPEN_QUESTIONS.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "output": str(args.out_json), "closure_allowed": doc["closure_allowed"]},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
