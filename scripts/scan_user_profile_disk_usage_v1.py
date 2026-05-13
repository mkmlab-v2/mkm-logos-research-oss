#!/usr/bin/env python3
"""Read-only: approximate size per top-level folder under USERPROFILE (and optional C:\\Users)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def walk_size(root: Path, max_files: int) -> tuple[int, int, bool]:
    total = 0
    n = 0
    capped = False
    for dirpath, _, filenames in os.walk(root, topdown=True, followlinks=False):
        for name in filenames:
            if n >= max_files:
                return total, n, True
            fp = Path(dirpath) / name
            try:
                total += fp.stat().st_size
            except OSError:
                pass
            n += 1
    return total, n, capped


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", type=Path, default=Path(os.environ.get("USERPROFILE", "")))
    ap.add_argument("--max-files-per-top", type=int, default=400_000)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("F:/MKM_Archive/user_profile_disk_scan_v1.json"),
    )
    args = ap.parse_args()
    prof = args.profile.resolve()
    if not prof.is_dir():
        print(f"error: profile not found: {prof}", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for child in sorted(prof.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        b, n, cap = walk_size(child, args.max_files_per_top)
        rows.append(
            {
                "path": str(child),
                "name": child.name,
                "bytes": b,
                "files_walked": n,
                "capped": cap,
            }
        )

    rows.sort(key=lambda r: r["bytes"], reverse=True)
    payload = {
        "schema": "user_profile_disk_scan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile": str(prof),
        "max_files_per_top": args.max_files_per_top,
        "fact_lock_note": "Sizes are lower bounds if capped=true (walk stopped early). Read-only scan.",
        "top_level_directories": rows,
    }

    out = args.out
    if not out.is_absolute():
        out = Path.cwd() / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    for r in rows[:12]:
        gb = round(r["bytes"] / 1024**3, 2)
        cap = " (CAP)" if r["capped"] else ""
        print(f"{gb:>8} GB  {r['name']}{cap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
