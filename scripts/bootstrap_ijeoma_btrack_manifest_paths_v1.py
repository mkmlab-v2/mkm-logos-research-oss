#!/usr/bin/env python3
"""Bootstrap missing 이제마 B-track manifest paths from workspace mirrors (no MCP)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "ijeoma_btrack_manifest_bootstrap_v1.json"

BOOTSTRAP = [
    (
        "data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md",
        "docs/final/myeongni_fusion_schema_v2_draft.md",
    ),
    (
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md",
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md",
    ),
]

JEOKCHEONSU_STUB = """# 《적천수》 핵심 로직 스캐드 (B-track · workspace bootstrap)

[HYPO] / research_only — A-track·OOF·실매매 자동 합선 금지.

본 파일은 NotebookLM manifest 경로 placeholder입니다. 전문 원전 청크는 지휘관 export 또는 Vault 복원 후 교체하세요.

## 스캐드 (요지)
- 일간 강약·격국 맥락은 **명리 결정론 체인**(`run_myeongni_lens_chain_from_bot_v1.py`)과 **분리** 유지.
- 사상(동의수세보원) 청크 조인: `data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl`
- SASANG cross-ref: `docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json` (analogy_bench only)

## SSOT
- `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md`
- `docs/NotebookLM_sources_manifest.md` §이제마_B_Track
"""


def main() -> int:
    actions: list[dict] = []
    jeok = ROOT / "data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md"
    if not jeok.is_file():
        jeok.parent.mkdir(parents=True, exist_ok=True)
        jeok.write_text(JEOKCHEONSU_STUB, encoding="utf-8")
        actions.append({"path": str(jeok.relative_to(ROOT)).replace("\\", "/"), "action": "wrote_stub"})

    for dest_rel, src_rel in BOOTSTRAP:
        src = ROOT / src_rel.replace("/", "\\") if "\\" in src_rel else ROOT / src_rel
        dest = ROOT / dest_rel.replace("/", "\\") if "\\" in dest_rel else ROOT / dest_rel
        if dest.is_file():
            actions.append({"path": dest_rel, "action": "already_exists"})
            continue
        if not src.is_file():
            actions.append({"path": dest_rel, "action": "missing_source", "source": src_rel})
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        actions.append({"path": dest_rel, "action": "copied", "source": src_rel})

    manifest_paths = [
        "data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md",
        "data/corpus/ijeoma/schemas/myeongni_fusion_schema_v2_draft.md",
        "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS_Myeongni_Ext.md",
        "docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json",
    ]
    present = {p: (ROOT / p).is_file() for p in manifest_paths}

    out = {
        "schema": "ijeoma_btrack_manifest_bootstrap_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "actions": actions,
        "manifest_core_files_present": present,
        "b7_ready": all(present.values()),
        "notebooklm_manual_pack": "reports/notebooklm_lens_packs_v1/IJEOMA_BTRACK/",
        "mcp_note": "Do not auto add_source; manual upload or new chat after MCP toggle off",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "b7_ready": out["b7_ready"]}, ensure_ascii=False))
    return 0 if out["b7_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
