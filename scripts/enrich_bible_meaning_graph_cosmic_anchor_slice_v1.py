#!/usr/bin/env python3
"""Merge cosmic-anchor verse nodes into bible_meaning_graph (HYPO, no kernel mutation).

Reproducible:
  py scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
STATS = ROOT / "docs/final/artifacts/bible_meaning_graph_cosmic_anchor_enrich_v1_latest.json"

from scripts.core.enrich_bible_meaning_graph_cosmic_anchor_v1 import (
    build_cosmic_anchor_verse_enrichment,
    load_existing_verse_refs,
    merge_edges_jsonl,
    merge_jsonl,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--nodes-jsonl", type=Path, default=NODES)
    parser.add_argument("--edges-jsonl", type=Path, default=EDGES)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.manifest.is_file():
        print(f"FAIL: missing manifest {args.manifest}", file=sys.stderr)
        return 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    stems = sorted(manifest.get("paths", {}).keys())
    existing_refs = load_existing_verse_refs(args.nodes_jsonl)
    new_nodes, new_edges = build_cosmic_anchor_verse_enrichment(
        batch_dir=args.batch_dir,
        stems=stems,
        existing_refs=existing_refs,
    )

    stats = {
        "schema": "bible_meaning_graph_cosmic_anchor_enrich_v1",
        "hypothesis_class": "HYPO",
        "research_only": True,
        "anchor_stems": len(stems),
        "existing_verse_refs_before": len(existing_refs),
        "new_verse_nodes": sum(1 for n in new_nodes if n.get("schema") == "logos_cosmic_anchor_verse_node_v1"),
        "new_nodes_total": len(new_nodes),
        "new_edges_total": len(new_edges),
        "dry_run": args.dry_run,
        "reproducible_command": "py scripts/enrich_bible_meaning_graph_cosmic_anchor_slice_v1.py",
    }

    if args.dry_run:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    nodes_added = merge_jsonl(args.nodes_jsonl, new_nodes, key_field="node_id")
    edges_added = merge_edges_jsonl(args.edges_jsonl, new_edges)
    stats["nodes_appended"] = nodes_added
    stats["edges_appended"] = edges_added
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {STATS}")
    print(f"  nodes_appended={nodes_added} edges_appended={edges_added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
