#!/usr/bin/env python3
"""Mirror COMP-ATOM NotebookLM source pack into Vault notebooklm_sources (no MCP)."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "reports" / "constitution" / "btrack_pilot" / "comp_atom_notebooklm_source_pack_v1.json"
VAULT = Path(os.environ.get("MKM_VAULT_ROOT", r"G:\공유 드라이브\MKM_DATA_VAULT\vault"))
DEST = VAULT / "notebooklm_sources" / "comp_atom_compression_btrack"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not PACK.is_file():
        print(f"ABORT: missing {PACK}")
        return 1
    pack = json.loads(PACK.read_text(encoding="utf-8"))
    if not VAULT.is_dir():
        print(f"SKIP: vault not mounted: {VAULT}")
        return 0
    DEST.mkdir(parents=True, exist_ok=True)
    copied = []
    for row in pack.get("sources") or []:
        rel = row.get("path")
        if not rel or not row.get("exists"):
            continue
        src = ROOT / rel
        dst = DEST / Path(rel).name
        shutil.copy2(src, dst)
        copied.append(str(dst.relative_to(VAULT)).replace("\\", "/"))
    stamp = DEST / "_COPIED_AT_UTC.txt"
    stamp.write_text(_utc() + "\n", encoding="utf-8")
    log = {
        "schema": "push_comp_atom_sources_to_notebooklm_vault_v1",
        "generated_at_utc": _utc(),
        "dest": str(DEST),
        "copied_count": len(copied),
        "copied": copied,
    }
    out = ROOT / "reports" / "constitution" / "btrack_pilot" / "comp_atom_vault_mirror_latest.json"
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "copied": len(copied), "dest": str(DEST)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
