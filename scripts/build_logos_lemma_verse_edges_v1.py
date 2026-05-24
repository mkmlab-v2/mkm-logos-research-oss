#!/usr/bin/env python3
"""Phase 1+: lemma↔verse edges from concept_bridge + corpus graph tokens ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE = ROOT / "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json"
DEFAULT_GRAPH_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"

TOK_RE = re.compile(r"[\u0590-\u05FF]{3,}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_edges(bridge_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not bridge_path.is_file():
        raise FileNotFoundError(bridge_path)
    doc = json.loads(bridge_path.read_text(encoding="utf-8"))
    verse_by_short: dict[str, str] = {}
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("node_id") or "")
        vid = node.get("verse_id")
        if nid.startswith("verse:") and vid:
            verse_by_short[nid] = str(vid)

    rows: list[dict[str, Any]] = []
    edge_i = 0
    for path in doc.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = path.get("steps") or []
        if not isinstance(steps, list):
            continue
        lemma_id: str | None = None
        for step in steps:
            sid = str(step) if isinstance(step, str) else str((step or {}).get("node_id") or "")
            if not sid:
                continue
            if "lemma" in sid:
                lemma_id = sid
            elif sid.startswith("verse:") and lemma_id:
                dst = verse_by_short.get(sid, sid.replace("verse:", ""))
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::{edge_i}",
                        "src_node_id": lemma_id,
                        "dst_node_id": dst,
                        "edge_type": "LEMMA_VERSE_PROXY",
                        "weight": 0.5,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "path_id": path.get("path_id"),
                    }
                )
                edge_i += 1
                lemma_id = None
    manifest = {
        "schema": "logos_lemma_verse_edges_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "source_bridge": bridge_path.relative_to(ROOT).as_posix()
        if bridge_path.is_relative_to(ROOT)
        else str(bridge_path),
        "edge_count": len(rows),
        "note": "Educational proxy edges from concept_bridge; not morphology-verified.",
    }
    return rows, manifest


def _edges_from_graph_nodes(
    nodes_path: Path,
    *,
    max_edges: int,
    tokens_per_verse: int,
) -> list[dict[str, Any]]:
    if not nodes_path.is_file() or max_edges <= 0:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    edge_i = 0
    with nodes_path.open("r", encoding="utf-8") as f:
        for line in f:
            if len(rows) >= max_edges:
                break
            line = line.strip()
            if not line:
                continue
            node = json.loads(line)
            if not isinstance(node, dict):
                continue
            ref = str(node.get("ref") or "")
            corpus = str(node.get("corpus") or "unknown")
            text = str(node.get("text_norm") or "")
            if not ref or not text:
                continue
            tokens = TOK_RE.findall(text)[:tokens_per_verse]
            for tok in tokens:
                if len(rows) >= max_edges:
                    break
                lemma_id = f"lemma:{corpus}:{tok}_heuristic"
                key = (lemma_id, ref)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::graph_{edge_i}",
                        "src_node_id": lemma_id,
                        "dst_node_id": ref,
                        "edge_type": "LEMMA_VERSE_HEURISTIC",
                        "weight": 0.35,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "source": "bible_meaning_graph_nodes_v1",
                    }
                )
                edge_i += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos lemma-verse edges v1 (Phase 1+)")
    ap.add_argument("--bridge-json", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument("--graph-nodes-jsonl", type=Path, default=DEFAULT_GRAPH_NODES)
    ap.add_argument("--include-graph-heuristic", action="store_true", default=True)
    ap.add_argument("--no-graph-heuristic", action="store_false", dest="include_graph_heuristic")
    ap.add_argument("--graph-max-edges", type=int, default=47)
    ap.add_argument("--graph-tokens-per-verse", type=int, default=2)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    args = ap.parse_args()

    rows, manifest = build_edges(args.bridge_json)
    if args.include_graph_heuristic:
        graph_rows = _edges_from_graph_nodes(
            args.graph_nodes_jsonl,
            max_edges=args.graph_max_edges,
            tokens_per_verse=args.graph_tokens_per_verse,
        )
        rows.extend(graph_rows)
        manifest["graph_heuristic_edges"] = len(graph_rows)
    manifest["edge_count"] = len(rows)
    manifest["note"] = (
        "Bridge proxy + optional corpus graph heuristic tokens; not morphology-verified."
    )
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else "")
    args.out_jsonl.write_text(text, encoding="utf-8")
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "edge_count": len(rows), "out": str(args.out_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
