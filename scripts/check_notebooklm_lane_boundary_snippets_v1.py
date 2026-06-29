#!/usr/bin/env python3
"""Offline check: lane boundary snippets contain expected NEVER cross-talk phrases."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SNIPPETS = {
    "22_ACODEAI": ROOT / "reports/notebooklm_core_fact_sync_pack_v1/00_core_fact_lane_boundary_snippet.md",
    "23_BTRACK": ROOT
    / "reports/notebooklm_compression_btrack_sync_pack_v1/00_compression_btrack_lane_boundary_snippet.md",
    "20_CLINICIAN": ROOT
    / "reports/notebooklm_clinician_sync_pack_v1/00_clinician_lane_boundary_snippet.md",
    "21_CONSUMER": ROOT
    / "reports/notebooklm_consumer_sync_pack_v1/00_consumer_lane_boundary_snippet.md",
    "00_OPS": ROOT / "reports/notebooklm_ops_command_sync_pack_v1/00_ops_command_handoff_snippet.md",
}

REQUIRED_PHRASES = {
    "22_ACODEAI": ["B-track", "47.5%", "FAIL-COMP", "실매매"],
    "23_BTRACK": ["Track A", "research_only", "[HYPO]", "합선", "auto-merge"],
    "20_CLINICIAN": ["consumer", "physician", "SOAP"],
    "21_CONSUMER": ["physician", "consumer_survey", "Track A"],
    "00_OPS": ["Fact-Lock", "CONSTITUTION", "99_ARCHIVE"],
}


def main() -> int:
    rows = []
    fail = 0
    for lane, path in SNIPPETS.items():
        if not path.is_file():
            rows.append({"lane": lane, "ok": False, "error": "missing snippet"})
            fail += 1
            continue
        text = path.read_text(encoding="utf-8")
        missing = [p for p in REQUIRED_PHRASES[lane] if p not in text]
        ok = not missing
        rows.append({"lane": lane, "path": str(path.name), "ok": ok, "missing_phrases": missing})
        if not ok:
            fail += 1
    out = ROOT / "reports/notebooklm_lane_boundary_offline_check_v1_latest.json"
    out.write_text(json.dumps({"lanes": rows, "all_ok": fail == 0}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_ok": fail == 0, "out": str(out)}, ensure_ascii=False))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
