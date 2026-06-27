#!/usr/bin/env python3
"""Copy IJEOMA corpus SSOT from G: vault notebooklm_sources mirror into workspace."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "ijeoma_corpus_restore_v1.json"

G_BTRACK_DOCS = [
    "IJEOMA_GEUKCHIGO_YUGO_SECONDARY_INSIGHT_2026-03-29.md",
    "IJEOMA_GEUKCHI_CHEONYU_PAPER_PROXY_LAYER_2026-03-29.md",
    "SCISPACE_SASANG_LITERATURE_HELPFUL_ITEMS_2026-03-29.md",
    "IJEOMA_BOUNDARY_SSOT_2026-03-29.md",
    "KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md",
]

REL_COPIES = [
    (
        "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        "notebooklm_sources/data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    ),
    (
        "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
        "notebooklm_sources/data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
    ),
    (
        "data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md",
        "notebooklm_sources/data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md",
    ),
]


def discover_g_vault() -> Path | None:
    env = os.environ.get("MKM_VAULT_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    g = Path("G:/")
    if not g.is_dir():
        return None
    for vault in g.rglob("vault"):
        if vault.is_dir() and "MKM_DATA_VAULT" in str(vault):
            return vault
    return None


def discover_g_data_root(vault: Path) -> Path | None:
    """MKM_DATA_VAULT root (parent of vault/) for data/corpus/ijeoma mirrors."""
    if vault.name == "vault" and vault.parent.is_dir():
        return vault.parent
    return None


def main() -> int:
    vault = discover_g_vault()
    if not vault:
        print("MKM_DATA_VAULT not mounted", file=__import__("sys").stderr)
        return 2

    data_root = discover_g_data_root(vault)
    g_btrack = data_root / "notebooklm_sources" / "이제마_B_Track" if data_root else None
    copied: list[str] = []
    missing: list[str] = []
    stub_rel = "data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md"
    stub_dest = ROOT / stub_rel.replace("/", os.sep)

    mirror_root = vault / "notebooklm_sources" / "data" / "corpus" / "ijeoma"
    if g_btrack and g_btrack.is_dir():
        for name in G_BTRACK_DOCS:
            src = g_btrack / name
            dest = ROOT / "docs" / "final" / name
            if not src.is_file():
                missing.append(str(src))
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_file() and dest.stat().st_size == src.stat().st_size:
                continue
            shutil.copy2(src, dest)
            copied.append(f"docs/final/{name}")

    if data_root:
        e_mirror = data_root / "data" / "corpus" / "ijeoma" / "e_drive_mirror"
        if e_mirror.is_dir():
            for src in e_mirror.rglob("*"):
                if not src.is_file():
                    continue
                rel = src.relative_to(e_mirror)
                dest = ROOT / "data" / "corpus" / "ijeoma" / "e_drive_mirror" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.is_file() and dest.stat().st_size == src.stat().st_size:
                    continue
                shutil.copy2(src, dest)
                copied.append(f"data/corpus/ijeoma/e_drive_mirror/{rel.as_posix()}")

    if mirror_root.is_dir():
        for src in mirror_root.rglob("*"):
            if not src.is_file():
                continue
            rel = src.relative_to(mirror_root)
            dest = ROOT / "data" / "corpus" / "ijeoma" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.is_file() and dest.stat().st_size == src.stat().st_size:
                continue
            shutil.copy2(src, dest)
            copied.append(f"data/corpus/ijeoma/{rel.as_posix()}")
    for dest_rel, src_rel in REL_COPIES:
        src = vault / src_rel.replace("/", os.sep)
        dest = ROOT / dest_rel.replace("/", os.sep)
        if not src.is_file():
            missing.append(str(src))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(dest_rel)

    if stub_rel not in copied and not stub_dest.is_file():
        canonical = ROOT / "docs/sasang-origin/정교동의수세보원원문.txt"
        if canonical.is_file():
            stub_dest.parent.mkdir(parents=True, exist_ok=True)
            body = (
                "# B-track: 사상 외연 통합 연구 (격리 스텁)\n\n"
                "**Canonical SSOT (merged 원문):** `docs/sasang-origin/정교동의수세보원원문.txt`\n\n"
                "**Chunk table:** `data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl`\n\n"
                "**Verify:** `py scripts/verify_ijeoma_chunk_table.py`\n\n"
                "Vault mirror had no Drive-export MD; replace this stub when full MD is exported.\n"
                "[HYPO] — not Track A SSOT.\n"
            )
            stub_dest.write_text(body, encoding="utf-8")
            copied.append(stub_rel + " (canonical_pointer_stub)")

    out = {
        "schema": "ijeoma_corpus_restore_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vault_root": str(vault),
        "copied": copied,
        "missing_sources": missing,
        "restore_complete": len(missing) == 0,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "copied": len(copied), "missing": len(missing)}, ensure_ascii=False))
    return 0 if copied else 2


if __name__ == "__main__":
    raise SystemExit(main())
