#!/usr/bin/env python3
"""Archive symbol C validation artifacts with UTC timestamp."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_ARCHIVE_ROOT = REPORT_DIR / "history" / "symbol_c_validation"
ARTIFACTS = [
    "symbol_c_validation_packet_latest.json",
    "symbol_c_validation_packet_baseline_latest.json",
    "symbol_c_validation_queue_compare_latest.json",
    "symbol_c_validation_checklist_stable_latest.json",
    "symbol_c_validation_checklist_exploratory_latest.json",
]


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Archive symbol C validation artifacts by run timestamp")
    ap.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
    args = ap.parse_args()

    archive_root = _abs(args.archive_root)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = archive_root / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for name in ARTIFACTS:
        src = REPORT_DIR / name
        if not src.is_file():
            skipped += 1
            print(f"SKIP: missing {src}")
            continue
        dst = out_dir / name.replace("_latest", f"_{ts}")
        shutil.copy2(src, dst)
        copied += 1
        print(f"COPY: {src} -> {dst}")

    print("OK: symbol C validation archive completed")
    print(f"archive_dir={out_dir}")
    print(f"copied={copied} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
