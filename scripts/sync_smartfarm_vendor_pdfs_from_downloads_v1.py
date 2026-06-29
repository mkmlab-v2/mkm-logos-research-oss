#!/usr/bin/env python3
"""Sync QuBICS/vendor PDFs from user Downloads into reports/smartfarm_vendor_replies/."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = Path.home() / "Downloads"
DEST = ROOT / "reports" / "smartfarm_vendor_replies"
OUT = ROOT / "reports" / "smartfarm_vendor_pdf_sync_latest.json"

PATTERNS = (
    "QuBICS",
    "CoCoNET",
    "260520_견적",
    "260522_견적",
    "260522_목소리",
)


def should_sync(name: str) -> bool:
    return any(p in name for p in PATTERNS)


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    missing: list[str] = []

    sources = sorted(p for p in DOWNLOADS.glob("*.pdf") if should_sync(p.name))
    if not sources:
        missing.append(str(DOWNLOADS))

    for src in sources:
        dst = DEST / src.name
        if dst.exists() and dst.stat().st_size == src.stat().st_size and dst.stat().st_mtime >= src.stat().st_mtime:
            skipped.append({"file": src.name, "reason": "dest_same_or_newer"})
            continue
        shutil.copy2(src, dst)
        copied.append({"file": src.name, "bytes": str(src.stat().st_size)})

    report = {
        "schema": "smartfarm_vendor_pdf_sync_v1",
        "synced_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_dir": str(DOWNLOADS),
        "dest_dir": str(DEST),
        "copied": copied,
        "skipped": skipped,
        "missing_source_glob": missing,
        "verdict": "ok" if sources else "no_matching_pdfs_in_downloads",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if sources else 1


if __name__ == "__main__":
    raise SystemExit(main())
