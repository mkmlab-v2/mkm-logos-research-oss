#!/usr/bin/env python3
"""Generate summary for ENTRY_08 (4Q319 / 4QOtot) source-hunt JSONL."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_log.jsonl"
OUT = ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_summary_latest.json"

PLACEHOLDER_ANCHORS = {
    "",
    "unknown",
    "none",
    "tbd",
    "line=tbd",
    "probe only",
    "plate=pls x-xiii line=tbd",
}


def main() -> int:
    if not SRC.exists():
        raise SystemExit(f"missing log: {SRC}")

    rows = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s))

    conf = Counter(str(r.get("confidence", "")).strip() for r in rows)
    witness = Counter(str(r.get("fragment_line_direct_witness", "")).strip() for r in rows)
    modes = Counter(str(r.get("access_mode", "")).strip() for r in rows)
    line_ready = [
        r
        for r in rows
        if str(r.get("line_anchor", "")).strip().lower() not in PLACEHOLDER_ANCHORS
        and "tbd" not in str(r.get("line_anchor", "")).lower()
        and str(r.get("resource_type", "")) != "availability_probe"
    ]

    has_direct = witness.get("yes", 0) > 0
    if has_direct:
        action = "prepare_manual_crossref_anchor_review"
        next_gate = "update_cross_ref_dss_draft_entry08"
    elif line_ready:
        action = "scholarly_translation_only_not_fragment_line"
        next_gate = "keep_partial_anchor_sigla_plates"
    else:
        action = "pause_hunt_until_4q319_line_transcription"
        next_gate = "wait_queue_entry08"

    summary = {
        "schema": "entry08_source_hunt_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cross_ref_entry": "ENTRY_08",
        "target_loc": "4Q319 (4QOtot) Pls X-XIII fragment-line",
        "source_log": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "track": "B-track",
        "research_only": True,
        "hypo": True,
        "total_sources": len(rows),
        "confidence_counts": dict(conf),
        "fragment_line_witness_counts": dict(witness),
        "access_mode_counts": dict(modes),
        "line_anchor_ready_count": len(line_ready),
        "has_fragment_line_direct_witness": has_direct,
        "next_gate": next_gate,
        "action_recommendation": action,
        "ssot_mutation": False,
        "operator_hint": (
            "Persée/DJD translation lines are not DJD fragment-line anchors; "
            "IAA archive has plates without machine line table."
        ),
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
