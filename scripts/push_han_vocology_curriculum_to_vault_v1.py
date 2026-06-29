#!/usr/bin/env python3
"""Mirror Han Vocology curriculum MD + DOCX exports to MKM_DATA_VAULT (B-track · M17)."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/han_vocology_docx_export_manifest_v1.json"
OUT = ROOT / "reports/han_vocology_curriculum_vault_mirror_v1_latest.json"

EXTRA: list[str] = [
    "reports/han_vocology_export_volume_a_v0_1_latest.docx",
    "reports/han_vocology_export_volume_b_v0_1_latest.docx",
    "reports/han_vocology_export_volume_a_v0_1_latest.json",
    "reports/han_vocology_export_volume_b_v0_1_latest.json",
    "docs/final/artifacts/han_vocology_volume_gap_v1_latest.json",
    "docs/research/HAN_VOCOLOGY_SLIDES_M3_05_POC_V1.md",
    "reports/han_vocology_slides_export_v1_latest.json",
    "reports/han_vocology_slides_m3_05_poc_v1/deck.pptx",
    "reports/han_vocology_slides_m3_05_poc_v1/deck.html",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _vault_dest() -> Path | None:
    env = os.environ.get("MKM_VAULT_ROOT")
    candidates: list[Path] = []
    if env:
        candidates.append(Path(env) / "notebooklm_sources" / "한의음성학" / "curriculum")
        candidates.append(Path(env) / "vault" / "notebooklm_sources" / "한의음성학" / "curriculum")
    candidates.append(Path(r"G:\공유 드라이브\MKM_DATA_VAULT\notebooklm_sources\한의음성학\curriculum"))
    candidates.append(Path(r"G:\공유 드라이브\MKM_DATA_VAULT\vault\notebooklm_sources\한의음성학\curriculum"))
    for dest in candidates:
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            return dest
        except OSError:
            continue
    return None


def _chapter_paths() -> list[str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    volumes = manifest.get("volumes") or {}
    seen: set[str] = set()
    paths: list[str] = []
    for key in ("volume_a_core", "volume_b"):
        for rel in volumes.get(key, {}).get("chapters") or []:
            if rel not in seen:
                seen.add(rel)
                paths.append(rel)
    return paths


def main() -> int:
    dest = _vault_dest()
    if dest is None:
        log = {
            "schema": "han_vocology_curriculum_vault_mirror_v1",
            "ok": False,
            "skipped": True,
            "reason": "vault_not_mounted",
            "generated_at_utc": _utc(),
        }
        OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "skipped": True, "reason": "vault_not_mounted"}, ensure_ascii=False))
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    md_dir = dest / "md"
    docx_dir = dest / "docx"
    meta_dir = dest / "meta"
    for d in (md_dir, docx_dir, meta_dir):
        d.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []

    for rel in _chapter_paths() + EXTRA:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        if rel.endswith(".md"):
            dst = md_dir / Path(rel).name
        elif rel.endswith(".docx"):
            dst = docx_dir / Path(rel).name
        else:
            dst = meta_dir / Path(rel).name
        shutil.copy2(src, dst)
        copied.append(rel)

    stamp = dest / "_COPIED_AT_UTC.txt"
    stamp.write_text(_utc() + "\n", encoding="utf-8")

    log: dict[str, Any] = {
        "schema": "han_vocology_curriculum_vault_mirror_v1",
        "ok": not missing,
        "generated_at_utc": _utc(),
        "dest": str(dest),
        "copied_count": len(copied),
        "copied": copied,
        "missing": missing,
    }
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": log["ok"], "copied": len(copied), "dest": str(dest), "missing": missing},
            ensure_ascii=False,
        )
    )
    return 0 if log["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
