#!/usr/bin/env python3
"""
Logos manuscript supply-line v1: copy local dumps into canonical paths, backfill hashes, verify, manifest.

Targets verifier rules in scripts/verify_logos_manuscripts_integrity.py (canonical_text_for_row, row_sha256).

Usage:
  py scripts/ingest_logos_manuscripts_v1.py copy --src "G:\\path\\dss_parsed.jsonl" [--dest data/logos/manuscripts/dss_parsed.jsonl] [--dry-run]
  py scripts/ingest_logos_manuscripts_v1.py hash [--jsonl path] [--dry-run]
  py scripts/ingest_logos_manuscripts_v1.py verify [--jsonl path] [--strict]
  py scripts/ingest_logos_manuscripts_v1.py manifest

Open-access / license note (design only; no network fetch in v1):
  - ETCBC DSS and similar corpora require explicit licensing; do not scrape without rights.
  - Prefer a local NDJSON/JSONL dump you already own; this script only copies and validates.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
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


def cmd_copy(args: argparse.Namespace) -> int:
    src = Path(args.src).expanduser().resolve()
    dest = (repo_root() / args.dest).resolve() if not Path(args.dest).is_absolute() else Path(args.dest).resolve()
    if not src.is_file():
        print(f"ERROR: source not a file: {src}", file=sys.stderr)
        return 2
    dest.parent.mkdir(parents=True, exist_ok=True)
    if args.dry_run:
        print(f"DRY-RUN: would copy {src} -> {dest}")
        return 0
    shutil.copy2(src, dest)
    print(f"Copied {src} -> {dest}")
    return 0


def cmd_hash(args: argparse.Namespace) -> int:
    backfill = repo_root() / "scripts" / "backfill_logos_manuscript_hashes.py"
    cmd = [sys.executable, str(backfill)]
    if args.jsonl:
        cmd.extend(["--jsonl", str(Path(args.jsonl).resolve())])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.no_backup:
        cmd.append("--no-backup")
    return subprocess.call(cmd, cwd=str(repo_root()))


def cmd_verify(args: argparse.Namespace) -> int:
    verify = repo_root() / "scripts" / "verify_logos_manuscripts_integrity.py"
    cmd = [sys.executable, str(verify)]
    if args.jsonl:
        cmd.extend(["--jsonl", str(Path(args.jsonl).resolve())])
    if args.strict:
        cmd.append("--strict")
    return subprocess.call(cmd, cwd=str(repo_root()))


def cmd_manifest(args: argparse.Namespace) -> int:
    build = repo_root() / "scripts" / "build_logos_dss_manifest.py"
    return subprocess.call([sys.executable, str(build)], cwd=str(repo_root()))


def main() -> int:
    root = repo_root()
    ap = argparse.ArgumentParser(description="Logos manuscript local supply v1")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_copy = sub.add_parser("copy", help="Copy a local JSONL dump into canonical data/logos/manuscripts/")
    p_copy.add_argument("--src", required=True, help="Absolute or relative path to source .jsonl")
    p_copy.add_argument(
        "--dest",
        default="data/logos/manuscripts/dss_parsed.jsonl",
        help="Destination relative to repo root (default: DSS canonical)",
    )
    p_copy.add_argument("--dry-run", action="store_true")
    p_copy.set_defaults(func=cmd_copy)

    p_hash = sub.add_parser("hash", help="Backfill char_len/sha256 via backfill_logos_manuscript_hashes.py")
    p_hash.add_argument("--jsonl", type=Path, help="Single JSONL (default: backfill script defaults)")
    p_hash.add_argument("--dry-run", action="store_true")
    p_hash.add_argument("--no-backup", action="store_true")
    p_hash.set_defaults(func=cmd_hash)

    p_ver = sub.add_parser("verify", help="Run verify_logos_manuscripts_integrity.py")
    p_ver.add_argument("--jsonl", type=Path)
    p_ver.add_argument("--strict", action="store_true")
    p_ver.set_defaults(func=cmd_verify)

    p_man = sub.add_parser("manifest", help="Run build_logos_dss_manifest.py")
    p_man.set_defaults(func=cmd_manifest)

    args = ap.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
