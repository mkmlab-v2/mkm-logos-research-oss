#!/usr/bin/env python3
"""Backup Cursor/MKM rule files for scheduled `RulesBackup` task on Windows.

Default: copy key repo rule files into reports/rules_backup/<timestamp>/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "reports" / "rules_backup"

# Files to include (repo tracked patterns; missing files are skipped with a note).
_RELATIVE_PATTERNS = [
    Path(".cursorrules"),
    Path("AGENTS.md"),
    Path("CLAUDE.md"),
]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)


def cmd_create(dest_root: Path) -> int:
    stamp = _utc_stamp()
    run_dir = dest_root / stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    for rel in _RELATIVE_PATTERNS:
        src = ROOT / rel
        if src.is_file():
            dst = run_dir / rel.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(str(rel))
        else:
            skipped.append(str(rel))

    cursor_rules = ROOT / ".cursor" / "rules"
    if cursor_rules.is_dir():
        _copy_tree(cursor_rules, run_dir / "cursor_rules")

    manifest = {
        "schema": "rules_backup_manifest_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "destination": str(run_dir),
        "copied_files": copied,
        "skipped_missing": skipped,
    }
    man_path = run_dir / "manifest.json"
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Lightweight integrity line for diff audit
    h = hashlib.sha256()
    for p in sorted(run_dir.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            h.update(p.read_bytes())
    (run_dir / "bundle.sha256").write_text(h.hexdigest() + "\n", encoding="utf-8")

    print(f"OK rules backup -> {run_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Backup MKM/Cursor rule files.")
    ap.add_argument(
        "command",
        nargs="?",
        default="create",
        choices=("create",),
        help="create: write timestamped backup under reports/rules_backup/",
    )
    ap.add_argument(
        "--dest",
        type=Path,
        default=DEFAULT_DIR,
        help=f"Root folder for timestamped runs (default: {DEFAULT_DIR})",
    )
    ns = ap.parse_args()
    if ns.command == "create":
        return cmd_create(ns.dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
