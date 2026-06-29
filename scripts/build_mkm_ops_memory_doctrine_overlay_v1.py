#!/usr/bin/env python3
"""Merge LTM graph concept nodes into mkm_ops_memory_index_v1.json ([HYPO] / B-track).

  py scripts/build_mkm_ops_memory_doctrine_overlay_v1.py
  py scripts/build_mkm_ops_memory_doctrine_overlay_v1.py --topic "태양인 희귀성"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_long_term_memory_graph_lib_v1 import (
    DEFAULT_GRAPH_PATH,
    build_doctrine_overlay_nodes,
    load_graph,
)
from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    extract_node_from_index,
    load_index,
    merge_overlay_nodes,
    missing_must_keep_tags,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH_PATH)
    ap.add_argument("--topic", default="", help="Optional topic to subset LTM overlay nodes.")
    ap.add_argument("--max-nodes", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-post-gate", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    try:
        index = load_index(args.index)
    except FileNotFoundError as exc:
        print(f"FAIL: {exc} — run build_mkm_ops_memory_index_v1.py first", file=sys.stderr)
        return 1

    graph = None
    if args.graph.is_file():
        graph = load_graph(args.graph)
    elif not args.topic.strip():
        print(
            f"WARN: graph missing at {args.graph} — building overlay from CONCEPT_SPECS only",
            file=sys.stderr,
        )

    overlay_nodes = build_doctrine_overlay_nodes(
        root,
        graph,
        query=args.topic,
        max_nodes=args.max_nodes,
    )
    if not overlay_nodes:
        print("WARN: no doctrine overlay nodes built", file=sys.stderr)
        return 0

    merged = merge_overlay_nodes(index, overlay_nodes, overlay_label="doctrine_graph_v1")

    if not args.skip_post_gate:
        errors: list[str] = []
        for node_id, node in overlay_nodes.items():
            try:
                block = extract_node_from_index(root, node)
            except (FileNotFoundError, ValueError, KeyError) as exc:
                errors.append(f"{node_id}: extract failed: {exc}")
                continue
            missing = missing_must_keep_tags(block, node.get("must_keep_tags") or [])
            if missing:
                errors.append(f"{node_id}: must_keep_tags missing: {missing}")
        if errors:
            for err in errors:
                print(f"FAIL: post-overlay gate: {err}", file=sys.stderr)
            return 1
        print("must_keep gate (phase=source, doctrine overlay): OK")

    if args.dry_run:
        print(
            f"DRY-RUN OK: overlay nodes={sorted(overlay_nodes)} "
            f"total_nodes={len(merged.get('nodes') or {})}"
        )
        return 0

    args.index.parent.mkdir(parents=True, exist_ok=True)
    args.index.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE doctrine overlay merge: {args.index} (+{len(overlay_nodes)} nodes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
