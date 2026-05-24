#!/usr/bin/env python3
"""Locate IJEOMA corpus SSOT files on G: vault, F: archive, and workspace (read-only probe)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "ijeoma_corpus_source_probe_v1.json"

NAMES = (
    "IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
    "IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
    "sasang_extension_unified_field_research.md",
)


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


def shallow_hits(root: Path, max_depth: int = 8) -> list[str]:
    hits: list[str] = []
    if not root.is_dir():
        return hits
    depth = 0
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack and len(hits) < 50:
        cur, d = stack.pop()
        if d > max_depth:
            continue
        try:
            children = list(cur.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_file() and child.name in NAMES:
                hits.append(str(child))
            elif child.is_dir() and child.name.lower() in {
                "ijeoma",
                "_inventory",
                "corpus",
                "data",
                "mkm-life-pr",
                "workspace_archive",
            }:
                stack.append((child, d + 1))
            elif child.is_dir() and d < 4:
                stack.append((child, d + 1))
    return hits


def main() -> int:
    roots: list[tuple[str, Path]] = [
        ("workspace", ROOT),
        ("f_archive", Path(r"F:\BACKUP\MKM_ARCHIVE_FROM_F")),
    ]
    gv = discover_g_vault()
    if gv:
        roots.append(("g_vault", gv))
        roots.append(("g_btrack", gv / "btrack_artifacts_verified"))

    report: dict = {
        "schema": "ijeoma_corpus_source_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "roots": [],
    }
    any_hit = False
    for label, path in roots:
        exists = path.is_dir()
        hits = shallow_hits(path) if exists else []
        if hits:
            any_hit = True
        report["roots"].append(
            {
                "label": label,
                "path": str(path),
                "exists": exists,
                "hits": hits[:30],
                "hit_count": len(hits),
            }
        )

    required_ws = [
        "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl",
        "data/corpus/ijeoma/_inventory/IJEOMA_MASTER_MANIFEST_DRAFT_2026-03-29.json",
        "data/corpus/ijeoma/originals/sasang_extension_unified_field_research.md",
    ]
    report["workspace_required_present"] = {
        rel: (ROOT / rel.replace("/", os.sep)).is_file() for rel in required_ws
    }
    report["restore_recommended"] = (
        "Copy hits into data/corpus/ijeoma/ preserving relative paths; re-run comp_corpus01_readiness_v1.py"
        if any_hit
        else "No SSOT filenames on F/G shallow probe — Drive export or full vault mirror required"
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": OUT.name, "any_hit": any_hit}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
