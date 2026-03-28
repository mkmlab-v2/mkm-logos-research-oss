#!/usr/bin/env python3
"""
Backfill char_len and sha256 on Logos manuscript JSONL rows (same canonical rules as verify).

  py scripts/backfill_logos_manuscript_hashes.py
  py scripts/backfill_logos_manuscript_hashes.py --jsonl data/logos/manuscripts/dss_parsed.jsonl

Creates .bak next to each file unless --no-backup.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_verify_module():
    path = repo_root() / "scripts" / "verify_logos_manuscripts_integrity.py"
    spec = importlib.util.spec_from_file_location("logos_manuscripts_verify", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def backfill_file(path: Path, verify_mod, dry_run: bool, no_backup: bool) -> int:
    lines_out: list[str] = []
    n = 0
    with path.open(encoding="utf-8") as f:
        for raw in f:
            s = raw.rstrip("\n\r")
            if not s.strip():
                lines_out.append(raw if raw.endswith("\n") else raw + "\n")
                continue
            row = json.loads(s)
            if not isinstance(row, dict):
                raise ValueError(f"{path}: non-object row")
            ct = verify_mod.canonical_text_for_row(row)
            row["char_len"] = len(ct.encode("utf-8"))
            row["sha256"] = verify_mod.row_sha256(ct)
            lines_out.append(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1

    if dry_run:
        print(f"DRY-RUN {path}: would write {n} row(s)")
        return n

    if not no_backup and path.is_file():
        bak = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, bak)
        print(f"Backup: {bak}")

    path.write_text("".join(lines_out), encoding="utf-8")
    print(f"Wrote {path} ({n} row(s))")
    return n


def main() -> int:
    root = repo_root()
    default_files = [
        root / "data/logos/manuscripts/dss_parsed.jsonl",
        root / "data/logos/manuscripts/apocrypha_std.jsonl",
    ]

    ap = argparse.ArgumentParser(description="Backfill char_len/sha256 on manuscript JSONL")
    ap.add_argument(
        "--jsonl",
        type=Path,
        nargs="*",
        default=default_files,
        help="JSONL paths (default: dss + apocrypha)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    verify_mod = load_verify_module()
    total = 0
    for p in args.jsonl:
        p = p.resolve()
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2
        total += backfill_file(p, verify_mod, args.dry_run, args.no_backup)

    if not args.dry_run:
        print(f"\nDone. Total rows: {total}. Run: py scripts/verify_logos_manuscripts_integrity.py --strict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
