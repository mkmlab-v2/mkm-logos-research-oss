#!/usr/bin/env python3
"""Local NotebookLM source pack manifest for COMP-ATOM (no MCP)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "comp_atom_notebooklm_source_pack_v1.json"

SOURCES = [
    ("CENTRAL compression bullets", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"),
    ("Fact-Lock compression pipeline", "docs/final/COMPRESSION_INTERPRETATION_PIPELINE_FACT_LOCK_2026-03-31.md"),
    ("Restoration evolution index", "docs/final/COMPRESSION_RESTORATION_EVOLUTION_INDEX_V1.md"),
    ("Pointer feasibility", "reports/constitution/btrack_pilot/comp_atom02_pointer_feasibility_summary_v1.json"),
    ("COMP-ATOM manifest", "reports/constitution/btrack_pilot/comp_atom_research_manifest_v1.json"),
    ("Track B closure", "reports/constitution/btrack_pilot/comp_atom_track_b_closure_v1.json"),
    ("Frozen active report (read-only ref)", "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"),
]


def main() -> int:
    rows = []
    for label, rel in SOURCES:
        p = ROOT / rel.replace("/", "\\") if "\\" not in rel else ROOT / rel
        p = ROOT / rel
        rows.append({"label": label, "path": rel.replace("\\", "/"), "exists": p.is_file()})
    out = {
        "schema": "comp_atom_notebooklm_source_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mcp_note": "Add each existing path via NotebookLM MCP add_source or UI; admin@no1kmedi.com profile.",
        "sources": rows,
        "exists_count": sum(1 for r in rows if r["exists"]),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "exists": out["exists_count"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
