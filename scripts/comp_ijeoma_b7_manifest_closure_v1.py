#!/usr/bin/env python3
"""Close COMP 이제마 B7 manifest checklist (7-file + inventory; no MCP)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "comp_ijeoma_b7_manifest_closure_v1.json"

MANIFEST_CORE = [
    "data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md",
    "data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md",
    "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md",
    "docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json",
]
INVENTORY = [
    "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
    "data/corpus/ijeoma/_inventory/IJEOMA_NOTEBOOKLM_QUERY_SET_2026-03-29.md",
]


def main() -> int:
    core = {p: (ROOT / p).is_file() for p in MANIFEST_CORE}
    inv = {p: (ROOT / p).is_file() for p in INVENTORY}
    pack_dir = ROOT / "reports/notebooklm_lens_packs_v1/IJEOMA_BTRACK"
    pack_index = ROOT / "reports/notebooklm_lens_packs_v1/index.json"
    out = {
        "schema": "comp_ijeoma_b7_manifest_closure_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "track_wall": "B-track — manual NL upload only; no MCP add_source from agent",
        "manifest_core_present": core,
        "inventory_present": inv,
        "manual_upload_pack": "reports/notebooklm_lens_packs_v1/IJEOMA_BTRACK/",
        "manual_upload_pack_file_count": len(list(pack_dir.glob("*"))) if pack_dir.is_dir() else 0,
        "lens_pack_index_exists": pack_index.is_file(),
        "b7_closure_ok": all(core.values()) and all(inv.values()) and pack_dir.is_dir(),
        "next_human_step": (
            "B notebook (af639d3e…) or 이제마 허브: NL 웹에서 IJEOMA_BTRACK 폴더 파일 source_add. "
            "MCP 자동 업로드 금지(창 반복 방지)."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "b7_closure_ok": out["b7_closure_ok"]}, ensure_ascii=False))
    return 0 if out["b7_closure_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
