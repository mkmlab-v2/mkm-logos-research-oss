#!/usr/bin/env python3
"""Generate summary for ENTRY_07 (11Q19 cols XLVI-XLVII) source-hunt JSONL."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_log.jsonl"
OUT = ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_summary_latest.json"

PLACEHOLDER_ANCHORS = {
    "",
    "unknown",
    "none",
    "tbd",
    "line=tbd",
    "cols.xlvi-xlvii line=tbd",
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
    witness = Counter(str(r.get("xlvi_xlvii_direct_witness", "")).strip() for r in rows)
    modes = Counter(str(r.get("access_mode", "")).strip() for r in rows)
    line_ready = [
        r
        for r in rows
        if str(r.get("line_anchor", "")).strip().lower() not in PLACEHOLDER_ANCHORS
        and "tbd" not in str(r.get("line_anchor", "")).lower()
    ]
    comparandum_line = [r for r in rows if r.get("comparandum_only") is True]

    has_direct = witness.get("yes", 0) > 0
    if has_direct:
        action = "prepare_manual_crossref_anchor_review"
        next_gate = "update_cross_ref_dss_draft_entry07"
    elif line_ready:
        action = "comparandum_only_do_not_promote_entry07"
        next_gate = "keep_partial_anchor_column_range"
    else:
        action = "pause_hunt_until_11q19_line_transcription"
        next_gate = "wait_queue_entry07"

    summary = {
        "schema": "entry07_source_hunt_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cross_ref_entry": "ENTRY_07",
        "target_loc": "11Q19 cols.XLVI-XLVII",
        "source_log": str(SRC.relative_to(ROOT)).replace("\\", "/"),
        "track": "B-track",
        "research_only": True,
        "hypo": True,
        "total_sources": len(rows),
        "confidence_counts": dict(conf),
        "xlvi_xlvii_witness_counts": dict(witness),
        "access_mode_counts": dict(modes),
        "line_anchor_ready_count": len(line_ready),
        "comparandum_line_rows_count": len(comparandum_line),
        "has_xlvi_xlvii_direct_witness": has_direct,
        "next_gate": next_gate,
        "action_recommendation": action,
        "ssot_mutation": False,
        "operator_hint": (
            "11Q20 QD line extraction is comparandum-only; do not map QD fragment col 46 to 11Q19 XLVI."
        ),
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
