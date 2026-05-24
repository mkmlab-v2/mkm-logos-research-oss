#!/usr/bin/env python3
"""COMP-CORPUS-01 readiness: ijeoma tree + SASANG draft + optional verify (no Drive ingest)."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_corpus01_readiness_v1.json"

REQUIRED_PATHS = [
    "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
    "data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md",
]
OPTIONAL_ORIGINALS = [
    "data/corpus/ijeoma/originals/jeokcheonsu_core_logic_chunk.md",
]


def _exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file() or (ROOT / rel).is_file()


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    missing = [p for p in REQUIRED_PATHS if not _exists(p)]
    optional_present = [p for p in OPTIONAL_ORIGINALS if _exists(p)]

    verify_exit: int | None = None
    chunk_table = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
    if chunk_table.is_file():
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_ijeoma_chunk_table.py")],
            cwd=str(ROOT),
            check=False,
        )
        verify_exit = int(proc.returncode)

    sasang = ROOT / "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json"
    sasang_entries = 0
    if sasang.is_file():
        doc = json.loads(sasang.read_text(encoding="utf-8"))
        sasang_entries = len(doc.get("entries") or [])

    blocked = bool(missing)
    out = {
        "schema": "comp_corpus01_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "corpus_import_ready": not blocked and verify_exit in (0, None),
        "blocked_reason": "missing_paths" if blocked else None,
        "missing_required": missing,
        "optional_originals_present": optional_present,
        "sasang_cross_ref_draft": {
            "path": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json",
            "exists": sasang.is_file(),
            "entry_count": sasang_entries,
        },
        "verify_ijeoma_chunk_table_exit": verify_exit,
        "next_human_step": (
            "Export Drive MD to data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md "
            "and restore _inventory from vault or G: mirror; then re-run this script."
            if blocked
            else "Run NotebookLM B-track ingest per docs/NotebookLM_sources_manifest.md §이제마."
        ),
        "notebooklm_pointer": "docs/NotebookLM_sources_manifest.md",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "corpus_import_ready": out["corpus_import_ready"], "missing": len(missing)}, ensure_ascii=False))
    return 0 if not blocked else 2


if __name__ == "__main__":
    raise SystemExit(main())
