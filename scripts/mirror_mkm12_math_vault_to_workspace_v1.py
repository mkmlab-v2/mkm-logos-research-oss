#!/usr/bin/env python3
"""Mirror MKM12 math constitution sealed docs from G: vault into workspace."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAULT_ROOT = Path(r"G:/공유 드라이브/MKM_DATA_VAULT")
MIRROR_DIR = ROOT / "docs/final/vault_mirror/mkm12_mathematics"
REPORT = ROOT / "docs/final/artifacts/mkm12_math_vault_mirror_report_v1_latest.json"

# vault_relative_path -> workspace_relative_path (under ROOT)
COPY_MAP: list[tuple[str, str]] = [
    (
        "projects/bitcoin-trading/docs/archive/2026-01/MKM12_수학헌법_v4.0_최종봉인판_2026-01-31.md",
        "docs/final/MKM12_수학헌법_v4.0_최종봉인판_2026-01-31.md",
    ),
    (
        "projects/bitcoin-trading/docs/archive/2026-01/MKM12_수학_헌법_2026-01-31.md",
        "docs/final/MKM12_수학_헌법_2026-01-31.md",
    ),
    (
        "projects/bitcoin-trading/docs/archive/2026-01/MKM12_75개_수학공식_전체목록_2026-01-31.md",
        "docs/final/vault_mirror/mkm12_mathematics/MKM12_75개_수학공식_전체목록_2026-01-31.md",
    ),
    (
        "projects/bitcoin-trading/docs/final/MKM12_수학공식_인덱스_2026-01-31.md",
        "docs/final/vault_mirror/mkm12_mathematics/MKM12_수학공식_인덱스_2026-01-31.md",
    ),
    (
        "projects/bitcoin-trading/docs/final/MKM12_한글_압축률_수학헌법_기반_재정리_2026-01-31.md",
        "docs/final/vault_mirror/mkm12_mathematics/MKM12_한글_압축률_수학헌법_기반_재정리_2026-01-31.md",
    ),
    (
        "projects/bitcoin-trading/docs/archive/2026-01/MKM12_수학공식_검증결과_2026-01-31.md",
        "docs/final/vault_mirror/mkm12_mathematics/MKM12_수학공식_검증결과_2026-01-31.md",
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ts = utc_now()
    MIRROR_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    missing: list[str] = []

    for vault_rel, dest_rel in COPY_MAP:
        src = VAULT_ROOT / vault_rel.replace("/", "\\")
        if not src.is_file():
            src = VAULT_ROOT / vault_rel
        dest = ROOT / dest_rel
        if not src.is_file():
            missing.append(vault_rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(
            {
                "vault_path": str(src),
                "workspace_path": dest_rel.replace("\\", "/"),
                "bytes": str(dest.stat().st_size),
            }
        )

    report = {
        "schema": "mkm12_math_vault_mirror_report_v1",
        "generated_at_utc": ts,
        "vault_root": str(VAULT_ROOT),
        "copied_count": len(copied),
        "missing_count": len(missing),
        "copied": copied,
        "missing": missing,
        "ok": len(missing) == 0,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
