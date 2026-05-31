#!/usr/bin/env python3
"""Build storage/meta/mkm_ops_memory_index_v1.json from anchor-tagged SSOT slices.

[HYPO] / research_only / B-track — no Track A·live trading auto-merge.

  py scripts/build_mkm_ops_memory_index_v1.py
  py scripts/build_mkm_ops_memory_index_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    build_index_document,
    verify_index_sources,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--dry-run", action="store_true", help="Validate only; do not write JSON.")
    ap.add_argument(
        "--skip-post-gate",
        action="store_true",
        help="Skip phase-1 must_keep verification after build.",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    mission_log = root / "MISSION_LOG.md"
    if not mission_log.is_file():
        print(f"FAIL: MISSION_LOG.md missing at {mission_log}", file=sys.stderr)
        print("Local-only SSOT (gitignored) — fail-fast.", file=sys.stderr)
        return 1

    try:
        doc = build_index_document(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: index build: {exc}", file=sys.stderr)
        return 1

    if not args.skip_post_gate:
        errors = verify_index_sources(root, doc)
        if errors:
            for err in errors:
                print(f"FAIL: post-build gate: {err}", file=sys.stderr)
            return 1
        print("must_keep gate (phase=source): OK")

    if args.dry_run:
        print(f"DRY-RUN OK: {len(doc.get('nodes', {}))} nodes validated")
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
