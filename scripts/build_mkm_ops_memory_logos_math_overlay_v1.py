#!/usr/bin/env python3
"""Merge Logos 4D/gematria/anchor/router JSON-slice nodes into ops memory index ([HYPO]).

  py scripts/build_mkm_ops_memory_logos_math_overlay_v1.py
  py scripts/build_mkm_ops_memory_logos_math_overlay_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    build_logos_math_overlay_nodes,
    extract_node_from_index,
    load_index,
    merge_overlay_nodes,
    missing_must_keep_tags,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
MIN_NODES = 4


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

    overlay_nodes = build_logos_math_overlay_nodes(root)
    if len(overlay_nodes) < MIN_NODES:
        print(
            f"FAIL: logos math overlay nodes={len(overlay_nodes)} expected >= {MIN_NODES}",
            file=sys.stderr,
        )
        return 1

    merged = merge_overlay_nodes(index, overlay_nodes, overlay_label="logos_math_v1")

    if not args.skip_post_gate:
        for node_id, node in overlay_nodes.items():
            block = extract_node_from_index(root, node)
            missing = missing_must_keep_tags(block, node.get("must_keep_tags") or [])
            if missing:
                print(f"FAIL: {node_id}: must_keep_tags missing: {missing}", file=sys.stderr)
                return 1
        print("must_keep gate (logos math overlay): OK")

    if args.dry_run:
        print(json.dumps({"nodes_added": sorted(overlay_nodes.keys())}, indent=2))
        return 0

    args.index.parent.mkdir(parents=True, exist_ok=True)
    args.index.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: merged logos math overlay -> {args.index} (+{len(overlay_nodes)} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
