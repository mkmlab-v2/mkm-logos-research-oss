#!/usr/bin/env python3
"""
Move old files under workspace/reports to F:\\MKM_Archive\\... preserving relative paths.
Skips *.lock, *.pid; never touches repo root outside reports/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports-root", type=Path, default=Path("reports"))
    ap.add_argument("--workspace-root", type=Path, default=Path.cwd())
    ap.add_argument("--dest-root", type=Path, default=Path("F:/MKM_Archive/reports_offload_v1"))
    ap.add_argument("--min-age-days", type=int, default=90)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--out-manifest",
        type=Path,
        default=None,
        help="Write JSON manifest (default: under dest-root)",
    )
    args = ap.parse_args()

    ws = args.workspace_root.resolve()
    rep = (ws / args.reports_root).resolve()
    if not rep.is_dir():
        print(f"error: reports dir missing: {rep}", file=sys.stderr)
        return 2

    now = time.time()
    min_age = float(args.min_age_days) * 86400.0
    skip_suffix = (".lock", ".pid")

    dest_root = args.dest_root
    if not dest_root.is_absolute():
        dest_root = (ws / dest_root).resolve()
    else:
        dest_root = dest_root.resolve()
    dest_root.mkdir(parents=True, exist_ok=True)

    moved: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for dirpath, _, filenames in os.walk(rep, topdown=True, followlinks=False):
        dp = Path(dirpath)
        for name in filenames:
            fp = dp / name
            if name.endswith(skip_suffix):
                skipped.append({"path": str(fp.relative_to(ws)), "reason": "lock_or_pid"})
                continue
            try:
                st = fp.stat()
            except OSError as e:
                errors.append({"path": str(fp.relative_to(ws)), "error": str(e)})
                continue
            if now - st.st_mtime < min_age:
                continue
            rel = fp.relative_to(ws)
            target = dest_root / rel
            if args.dry_run:
                moved.append(
                    {
                        "path": rel.as_posix(),
                        "bytes": st.st_size,
                        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                    }
                )
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    skipped.append({"path": str(rel), "reason": "dest_exists"})
                    continue
                shutil.move(str(fp), str(target))
                moved.append(
                    {
                        "path": rel.as_posix(),
                        "bytes": st.st_size,
                        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                    }
                )
            except OSError as e:
                errors.append({"path": str(rel), "error": str(e)})

    total_b = sum(x["bytes"] for x in moved)
    manifest = {
        "schema": "archive_old_reports_to_f_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": bool(args.dry_run),
        "min_age_days": args.min_age_days,
        "reports_root": str(rep),
        "dest_root": str(dest_root),
        "moved_count": len(moved),
        "moved_bytes": total_b,
        "skipped_count": len(skipped),
        "errors_count": len(errors),
        "moved_sample": moved[:200],
        "errors": errors[:50],
    }

    out = args.out_manifest
    if out is None:
        out = dest_root / "MANIFEST_last_run.json"
    else:
        out = out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)

    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(out)
    print(f"moved_files={len(moved)} bytes={total_b} dry_run={args.dry_run} errors={len(errors)}")
    return 1 if errors and not args.dry_run else 0


if __name__ == "__main__":
    raise SystemExit(main())
