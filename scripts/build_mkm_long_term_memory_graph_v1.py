#!/usr/bin/env python3
"""Build storage/meta/mkm_long_term_memory_graph_v1.json — doctrine concept wiring.

[HYPO] / research_only / B-track — no Track A·live trading auto-merge.

  py scripts/build_mkm_long_term_memory_graph_v1.py
  py scripts/build_mkm_long_term_memory_graph_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_long_term_memory_graph_lib_v1 import (
    DEFAULT_GRAPH_PATH,
    build_graph_document,
    verify_graph_sources,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_GRAPH_PATH)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-post-gate", action="store_true")
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    try:
        doc = build_graph_document(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: graph build: {exc}", file=sys.stderr)
        return 1

    missing = doc.get("build_missing_coordinates") or []
    if missing:
        for line in missing:
            print(f"WARN: coordinate missing: {line}", file=sys.stderr)

    if not args.skip_post_gate:
        errors = verify_graph_sources(root, doc)
        if errors:
            for err in errors:
                print(f"FAIL: post-build gate: {err}", file=sys.stderr)
            return 1
        print("must_keep gate (phase=source, graph concepts): OK")

    if args.dry_run:
        print(
            f"DRY-RUN OK: concepts={doc.get('concept_count')} "
            f"edges={doc.get('edge_count')}"
        )
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
