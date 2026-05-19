#!/usr/bin/env python3
"""Fused handoff: OpenData 327 + LG HS + B-track (read-only merge of lane JSON)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/mkm_parallel_lanes_fused_handoff_latest.json"

POINTERS = {
    "opendata_commander": ROOT / "reports/opendata_327_commander_handoff_latest.json",
    "opendata_readiness": ROOT / "reports/opendata_327_submission_readiness_latest.json",
    "lg_pre_meeting": ROOT / "reports/lg_hs_pre_meeting_readiness_v1_latest.json",
    "lg_followup": ROOT / "docs/final/artifacts/lg_hs_meeting_followup_v1.json",
    "btrack_wave6": ROOT / "reports/btrack_parallel_wave6_v1_latest.json",
}


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    op_handoff = _load(POINTERS["opendata_commander"]) or {}
    op_ready = _load(POINTERS["opendata_readiness"]) or {}
    lg_ready = _load(POINTERS["lg_pre_meeting"]) or {}
    lg_follow = _load(POINTERS["lg_followup"]) or {}
    wave6 = _load(POINTERS["btrack_wave6"]) or {}

    lg_outcome = (lg_follow.get("result_expected") or {}).get("status", "unknown")

    return {
        "schema": "mkm_parallel_lanes_fused_handoff_v1",
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "lanes": {
            "opendata_327": {
                "technical_ready": op_ready.get("technical_ready_for_pdf_bundle"),
                "kstartup_upload": op_ready.get("ready_for_kstartup_upload"),
                "bcd_merged_pdf": "reports/opendata_327_submission_bcd_merged_v1.pdf",
                "cover_a": "pending_human",
                "cover_merge_cmd": (
                    "py scripts/merge_opendata_327_submission_pdf_v1.py --cover-pdf <표지A.pdf>"
                ),
                "prep_one_liner": (
                    "powershell -NoProfile -ExecutionPolicy Bypass -File "
                    "scripts\\Run-OpenData327SubmissionPrep_v1.ps1"
                ),
            },
            "lg_hs": {
                "ready_for_internal_meeting": lg_ready.get("ready_for_internal_meeting"),
                "external_send_allowed": lg_ready.get("external_send_allowed"),
                "outcome_status": lg_outcome,
                "record_outcome_cmd": (
                    'py scripts/record_lg_hs_meeting_outcome_v1.py '
                    '--outcome-class <class> --summary-one-line "…"'
                ),
            },
            "btrack": {
                "wave6_all_ok": wave6.get("all_ok"),
                "track_wall": "[HYPO] · 90d freeze · no auto Track A / live",
            },
        },
        "commander_single_action": (
            "OpenData: provide cover Part A PDF path, then merge --cover-pdf"
        ),
        "boundary_ack": (
            "Fused view only; lane SSOT remains per-lane JSON files. "
            "No portal submit or legal send from this artifact."
        ),
        "pointers": {k: v.relative_to(ROOT).as_posix() for k, v in POINTERS.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build()
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
