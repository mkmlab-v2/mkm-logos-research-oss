#!/usr/bin/env python3
"""Merge ltm_* A2A bridge overlay nodes into mkm_ops_memory_index_v1.json ([HYPO] / B-track).

  py scripts/build_mkm_ops_memory_ltm_a2a_overlay_v1.py
  py scripts/build_mkm_ops_memory_ltm_a2a_overlay_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    build_ltm_a2a_overlay_nodes,
    load_index,
    merge_overlay_nodes,
    missing_must_keep_tags,
    verify_index_sources,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-post-gate", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    try:
        index = load_index(args.index)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc} — run build_mkm_ops_memory_index_v1.py first", file=sys.stderr)
        return 1

    overlay_nodes = build_ltm_a2a_overlay_nodes(root)
    if not overlay_nodes:
        print("FAIL: no ltm_a2a overlay nodes built (pilot/status JSON missing?)", file=sys.stderr)
        return 1

    merged = merge_overlay_nodes(index, overlay_nodes, overlay_label="ltm_a2a_v1")

    if not args.skip_post_gate:
        errors = verify_index_sources(root, merged)
        if errors:
            for err in errors:
                print(f"FAIL: post-merge gate: {err}", file=sys.stderr)
            return 1
        print("must_keep gate (phase=source): OK")

    if args.dry_run:
        print(f"DRY-RUN OK: would merge {len(overlay_nodes)} ltm_* nodes")
        return 0

    args.index.parent.mkdir(parents=True, exist_ok=True)
    args.index.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.index} (+{len(overlay_nodes)} ltm_a2a overlay nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
