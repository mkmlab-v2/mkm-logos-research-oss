#!/usr/bin/env python3
"""Emit UTF-8 JSON manifest for Korean paths (PS1 5.1 mojibake workaround)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/notebooklm_vault_sync_utf8_extra_paths_v1_latest.json"

# SSOT: paths that must not be embedded as Korean literals in .ps1 on Windows PS 5.1
UTF8_SOURCE_FILES = [
    "docs/final/MKM12_75개_수학공식_전체목록_2026-01-31.md",
    "docs/final/MKM12_수학헌법_v4.0_최종봉인판_2026-01-31.md",
    "docs/final/MKM12_수학_헌법_2026-01-31.md",
]


def _win_rel(path: str) -> str:
    return path.replace("/", os.sep)


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source_files: list[str] = []
    missing: list[str] = []
    for rel in UTF8_SOURCE_FILES:
        src = ROOT / rel
        win_rel = _win_rel(rel)
        if src.is_file():
            source_files.append(win_rel)
        else:
            missing.append(win_rel)

    doc = {
        "schema": "notebooklm_vault_sync_utf8_extra_paths_v1",
        "generated_at_utc": ts,
        "source_files": source_files,
        "source_dirs": [],
        "missing": missing,
        "ok": len(missing) == 0,
        "note": "Loaded by sync_notebooklm_sources_to_mkm_data_vault.ps1 via UTF-8 ReadAllText",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "ok": doc["ok"], "files": len(source_files)}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
