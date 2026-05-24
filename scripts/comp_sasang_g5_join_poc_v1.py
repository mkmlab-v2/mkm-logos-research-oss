#!/usr/bin/env python3
"""G5 PoC: SASANG_CROSS_REF draft lint + LOGOS_STATE_MAPPING join (no chunk table required)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_sasang_g5_join_poc_v1.json"

SASANG = ROOT / "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json"
LOGOS = ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json"
CHUNK = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    if not SASANG.is_file():
        print("missing SASANG_CROSS_REF_DRAFT.json", file=__import__("sys").stderr)
        return 2

    sasang = json.loads(SASANG.read_text(encoding="utf-8"))
    entries = sasang.get("entries") or []
    logos_states: set[int] = set()
    if LOGOS.is_file():
        logos_doc = json.loads(LOGOS.read_text(encoding="utf-8"))
        for row in logos_doc.get("states") or []:
            sid = row.get("state_id")
            if isinstance(sid, int):
                logos_states.add(sid)

    chunk_ids: set[str] = set()
    if CHUNK.is_file():
        with CHUNK.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                cid = row.get("chunk_id")
                if cid:
                    chunk_ids.add(str(cid))

    missing_chunk_ref = 0
    missing_state = 0
    link_types: dict[str, int] = {}
    for e in entries:
        lt = str(e.get("link_type") or "unknown")
        link_types[lt] = link_types.get(lt, 0) + 1
        cid = e.get("chunk_id")
        if chunk_ids and cid and cid not in chunk_ids:
            missing_chunk_ref += 1
        sid = e.get("state_candidate_id")
        if logos_states and isinstance(sid, int) and sid not in logos_states:
            missing_state += 1

    out = {
        "schema": "comp_sasang_g5_join_poc_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "track_wall": "B-track [HYPO] — no Track A or live trading promotion",
        "sasang_entry_count": len(entries),
        "chunk_table_on_disk": CHUNK.is_file(),
        "chunk_table_row_count": len(chunk_ids),
        "entries_missing_chunk_id_in_table": missing_chunk_ref if chunk_ids else None,
        "logos_mapping_present": LOGOS.is_file(),
        "logos_state_count": len(logos_states),
        "entries_state_not_in_logos": missing_state if logos_states else None,
        "link_type_histogram": link_types,
        "g5_poc_ok": len(entries) >= 1 and (not logos_states or missing_state == 0),
        "next_step": (
            "Restore IJEOMA_CHUNK_TABLE + manifest + sasang_extension MD under data/corpus/ijeoma/"
            if not CHUNK.is_file()
            else "Run verify_ijeoma_chunk_table.py then NotebookLM §이제마 ingest"
        ),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "g5_poc_ok": out["g5_poc_ok"], "entries": len(entries)}, ensure_ascii=False))
    return 0 if out["g5_poc_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
