#!/usr/bin/env python3
"""UTF-8-safe mirror of theory mathematization docs to NotebookLM vault (PS1 encoding workaround)."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/final/artifacts/theory_mathematization_vault_utf8_mirror_v1_latest.json"

COPY_REL: list[str] = [
    "docs/final/MKM12_75개_수학공식_전체목록_2026-01-31.md",
    "docs/final/MKM12_수학헌법_v4.0_최종봉인판_2026-01-31.md",
    "docs/final/MKM12_수학_헌법_2026-01-31.md",
    "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json",
    "reports/notebooklm_theory_mathematization_pack_v1/index.json",
]


def _vault_dest_root() -> Path:
    env = os.environ.get("MKM_VAULT_ROOT", "").strip()
    if env:
        return Path(env) / "notebooklm_sources"
    return Path(r"G:/공유 드라이브/MKM_DATA_VAULT/vault/notebooklm_sources")


def main() -> int:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dest_root = _vault_dest_root()
    copied: list[dict[str, str]] = []
    missing: list[str] = []

    for rel in COPY_REL:
        src = ROOT / rel.replace("/", os.sep)
        if not src.is_file():
            missing.append(rel)
            continue
        dest = dest_root / rel.replace("/", os.sep)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(
            {
                "src": rel,
                "dest": str(dest),
                "bytes": str(dest.stat().st_size),
            }
        )

    # mirror full theory pack directory
    pack_src = ROOT / "reports/notebooklm_theory_mathematization_pack_v1"
    pack_dest = dest_root / "reports/notebooklm_theory_mathematization_pack_v1"
    if pack_src.is_dir():
        if pack_dest.exists():
            shutil.rmtree(pack_dest)
        shutil.copytree(pack_src, pack_dest)
        copied.append(
            {
                "src": "reports/notebooklm_theory_mathematization_pack_v1/",
                "dest": str(pack_dest),
                "bytes": str(sum(f.stat().st_size for f in pack_dest.rglob("*") if f.is_file())),
            }
        )

    marker = dest_root / "_THEORY_MATHEMATIZATION_UTF8_MIRROR.txt"
    marker.write_text(f"last_ok_utc: {ts}\ncopied: {len(copied)}\n", encoding="utf-8")

    report = {
        "schema": "theory_mathematization_vault_utf8_mirror_v1",
        "generated_at_utc": ts,
        "dest_root": str(dest_root),
        "copied_count": len(copied),
        "missing": missing,
        "ok": len(missing) == 0 and dest_root.exists(),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
