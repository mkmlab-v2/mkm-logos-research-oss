#!/usr/bin/env python3
"""NL manual upload manifest for COMPRESSION_BTRACK + IJEOMA_BTRACK (no MCP batch)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK_ROOT = ROOT / "reports/notebooklm_lens_packs_v1"
OUT = ROOT / "reports/constitution/btrack_pilot/comp_nl_manual_upload_manifest_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pack_files(lens_dir: Path) -> list[dict]:
    if not lens_dir.is_dir():
        return []
    rows = []
    for p in sorted(lens_dir.iterdir()):
        if p.is_file():
            rows.append(
                {
                    "filename": p.name,
                    "relative_path": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "size_bytes": p.stat().st_size,
                }
            )
    return rows


def main() -> int:
    packs = {
        "COMPRESSION_BTRACK": _pack_files(PACK_ROOT / "COMPRESSION_BTRACK"),
        "IJEOMA_BTRACK": _pack_files(PACK_ROOT / "IJEOMA_BTRACK"),
    }
    doc = {
        "schema": "comp_nl_manual_upload_manifest_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "mcp_add_source_batch": False,
        "instructions": [
            "NotebookLM web UI: upload each file under the matching B-track notebook.",
            "Do not use MCP add_source for bulk ingestion (policy: achievement_index forbidden).",
            "Start with comp_cross_chat_achievement_index_v1.json then comp_compression_lane_handoff_v1.json.",
        ],
        "packs": packs,
        "file_counts": {k: len(v) for k, v in packs.items()},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "counts": doc["file_counts"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
