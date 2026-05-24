#!/usr/bin/env python3
"""Mirror reports/notebooklm_lens_packs_v1/* into Vault (best-effort, no MCP)."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = ROOT / "reports" / "notebooklm_lens_packs_v1"
VAULT = Path(os.environ.get("MKM_VAULT_ROOT", r"G:\공유 드라이브\MKM_DATA_VAULT\vault"))
OUT = ROOT / "reports/constitution/btrack_pilot/comp_lens_packs_vault_mirror_latest.json"

LENS_ALLOW = ("COMPRESSION_BTRACK", "IJEOMA_BTRACK")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not VAULT.is_dir():
        log = {
            "schema": "push_lens_packs_to_vault_v1",
            "generated_at_utc": _utc(),
            "skipped": True,
            "reason": f"vault not mounted: {VAULT}",
        }
        OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(log, ensure_ascii=False))
        return 0

    copied: list[str] = []
    for lens in LENS_ALLOW:
        src_dir = PACKS / lens
        if not src_dir.is_dir():
            continue
        dest = VAULT / "notebooklm_sources" / f"lens_pack_{lens.lower()}"
        dest.mkdir(parents=True, exist_ok=True)
        for f in src_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
                copied.append(str((dest / f.name).relative_to(VAULT)).replace("\\", "/"))

    log = {
        "schema": "push_lens_packs_to_vault_v1",
        "generated_at_utc": _utc(),
        "vault_root": str(VAULT),
        "copied_count": len(copied),
        "copied": copied,
    }
    OUT.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "copied": len(copied)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
