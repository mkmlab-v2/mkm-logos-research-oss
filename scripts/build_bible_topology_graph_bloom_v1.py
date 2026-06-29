#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build magic_orb_graph_bloom_v1 from bible_topology_shard_v1 (Tier A passion seed).

Phase 0 bridge: Repo#2 OSS shard → mkmlife OrbGraphBloom POC JSON.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHARD = ROOT / "tests/fixtures/bible_topology/sample/sample_topology_synoptic_passion_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_bible_topology_passion_v1_latest.json"
DEFAULT_LATEST = ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json"
MKMLIFE_POC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_graph_bloom_poc_v1.json"

DEFAULT_QUERY = (
    "Synoptic passion week — parallel anchors (Tier A seed, contributor shards, research_only)"
)
MAX_NODES = 64
MAX_EDGES = 72
VERSE_NODE_CAP = 63  # reserve 1 slot for query::center


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_builder():
    path = ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"
    spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _node_id(ref: str) -> str:
    return f"synoptic::{ref.strip().upper()}"


def _human_label(ref: str) -> str:
    r = ref.strip().upper()
    book, rest = r.split(".", 1) if "." in r else (r, "")
    names = {
        "MAT": "Matt",
        "MRK": "Mark",
        "LUK": "Luke",
        "JHN": "John",
    }
    prefix = names.get(book, book.title())
    return f"{prefix} {rest.replace('.', ':')}" if rest else prefix


def shard_to_slice(shard: dict[str, Any]) -> dict[str, Any]:
    degree: dict[str, int] = defaultdict(int)
    edge_rows: list[dict[str, Any]] = []
    for edge in shard.get("edges") or []:
        src = str(edge.get("src_ref") or "").strip().upper()
        dst = str(edge.get("dst_ref") or "").strip().upper()
        if not src or not dst or src == dst:
            continue
        relation = str(edge.get("relation") or "parallel")
        degree[src] += 1
        degree[dst] += 1
        edge_rows.append(
            {
                "src_ref": src,
                "dst_ref": dst,
                "relation": relation,
                "weight": float(edge.get("weight") or 0.72),
            }
        )

    ranked_refs = sorted(degree.keys(), key=lambda r: (-degree[r], r))
    selected = set(ranked_refs[:VERSE_NODE_CAP])
    max_deg = max(degree.values()) if degree else 1

    nodes: list[dict[str, Any]] = []
    for ref in sorted(selected):
        nodes.append(
            {
                "id": _node_id(ref),
                "label": _human_label(ref),
                "kind": "verse",
                "corpus": "synoptic",
                "ref": ref,
                "hub_score": round(0.45 + 0.5 * (degree[ref] / max_deg), 3),
            }
        )

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in sorted(edge_rows, key=lambda r: (-r["weight"], r["src_ref"], r["dst_ref"])):
        if row["src_ref"] not in selected or row["dst_ref"] not in selected:
            continue
        src = _node_id(row["src_ref"])
        dst = _node_id(row["dst_ref"])
        key = (src, dst, row["relation"])
        if key in seen:
            continue
        seen.add(key)
        edges.append(
            {
                "src": src,
                "dst": dst,
                "edge_type": row["relation"],
                "weight": row["weight"],
            }
        )
        if len(edges) >= MAX_EDGES:
            break

    return {
        "schema": "bible_topology_graph_slice_v1",
        "slice_id": shard.get("slice_id"),
        "seed_query": DEFAULT_QUERY,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
        "nodes": nodes,
        "edges": edges,
    }


def build_bloom_from_shard(
    shard: dict[str, Any],
    *,
    query: str = DEFAULT_QUERY,
    node_cap: int = MAX_NODES,
    edge_cap: int = MAX_EDGES,
) -> dict[str, Any]:
    bloom_mod = _load_builder()
    bloom_mod.NODE_CAP = min(bloom_mod.MAX_ABS_NODE_CAP, node_cap)
    bloom_mod.EDGE_CAP = min(bloom_mod.MAX_ABS_EDGE_CAP, edge_cap)
    slice_doc = shard_to_slice(shard)
    doc = bloom_mod.bloom_from_topology_slice(slice_doc, query)
    doc["source"] = {
        "kind": "bible_topology_shard_v1",
        "slice_id": shard.get("slice_id"),
        "tier": shard.get("tier"),
        "edge_count_source": len(shard.get("edges") or []),
        "shard_schema": shard.get("schema"),
    }
    doc["display_locale"] = "ko"
    unique_verses = set()
    for edge in shard.get("edges") or []:
        unique_verses.add(str(edge.get("src_ref") or "").upper())
        unique_verses.add(str(edge.get("dst_ref") or "").upper())
    unique_verses.discard("")
    doc["stats"]["source_unique_verses"] = len(unique_verses)
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shard-json", type=Path, default=DEFAULT_SHARD)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--promote-latest", action="store_true", help="Also write magic_orb_graph_bloom_v1_latest.json")
    ap.add_argument("--sync-mkmlife", action="store_true", help="Copy to mkmlife public/data POC path")
    args = ap.parse_args()

    if not args.shard_json.is_file():
        print(json.dumps({"ok": False, "error": f"shard_missing:{args.shard_json}"}), file=sys.stderr)
        return 2

    shard = json.loads(args.shard_json.read_text(encoding="utf-8-sig"))
    doc = build_bloom_from_shard(shard, query=args.query)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.write_text(text, encoding="utf-8")

    written = [str(args.out_json.relative_to(ROOT)).replace("\\", "/")]
    if args.promote_latest:
        DEFAULT_LATEST.write_text(text, encoding="utf-8")
        written.append(str(DEFAULT_LATEST.relative_to(ROOT)).replace("\\", "/"))
    if args.sync_mkmlife:
        MKMLIFE_POC.parent.mkdir(parents=True, exist_ok=True)
        MKMLIFE_POC.write_text(text, encoding="utf-8")
        written.append(str(MKMLIFE_POC.relative_to(ROOT)).replace("\\", "/"))

    print(
        json.dumps(
            {
                "ok": True,
                "nodes": doc["stats"]["node_count"],
                "edges": doc["stats"]["edge_count"],
                "written": written,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
