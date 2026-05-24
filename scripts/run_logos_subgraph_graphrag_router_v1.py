#!/usr/bin/env python3
"""Logos subgraph GraphRAG router v1 — concept_bridge + lemma edges ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/final/artifacts"
DEFAULT_REGISTRY = ART / "logos_concept_bridge_registry_v1_latest.json"
DEFAULT_LEMMA = ART / "logos_lemma_verse_edges_v1.jsonl"
DEFAULT_SEED_CHAIN = ART / "logos_graph_seed_chain_v1_latest.json"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = ART / "logos_subgraph_graphrag_router_v1_latest.json"

SCHEMA = "logos_subgraph_graphrag_router_v1"
VERSION = "1.0.0"
TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in TOKEN_RE.finditer(text.lower()):
        t = m.group(0)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _bridge_score(query_tokens: list[str], bridge: dict[str, Any]) -> int:
    parts: list[str] = []
    q = bridge.get("query") if isinstance(bridge.get("query"), dict) else {}
    parts.append(str(q.get("label_ko") or ""))
    parts.append(str(q.get("concept_id") or ""))
    for node in bridge.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        parts.append(str(node.get("label_ko") or ""))
        parts.append(str(node.get("label_en") or ""))
        parts.append(str(node.get("rationale_ko") or ""))
    hay = " ".join(parts).lower()
    return sum(1 for t in query_tokens if t in hay)


def _verse_ids_from_bridge(bridge: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for node in bridge.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "verse_ref":
            continue
        vid = node.get("verse_id") or node.get("node_id", "").replace("verse:", "")
        if isinstance(vid, str) and vid and vid not in seen:
            seen.add(vid)
            out.append(vid)
    hooks = bridge.get("graph_rag_hooks") if isinstance(bridge.get("graph_rag_hooks"), dict) else {}
    for sid in hooks.get("seed_verse_ids") or []:
        if isinstance(sid, str) and sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def route(
    query: str,
    *,
    registry: dict[str, Any],
    lemma_rows: list[dict[str, Any]],
    seed_chain: dict[str, Any] | None,
    top_bridges: int,
) -> dict[str, Any]:
    query_tokens = _tokens(query)
    bridge_docs: list[tuple[int, dict[str, Any], str]] = []
    for entry in registry.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        path = ROOT / rel.replace("/", "\\") if "\\" not in rel else Path(rel)
        if not path.is_file():
            path = ROOT / rel
        doc = _load_json(path)
        if not doc:
            continue
        score = _bridge_score(query_tokens, doc)
        if score > 0:
            bridge_docs.append((score, doc, rel))

    bridge_docs.sort(key=lambda x: x[0], reverse=True)
    selected = bridge_docs[:top_bridges]

    paths_out: list[dict[str, Any]] = []
    verse_ids: list[str] = []
    seen_v: set[str] = set()
    for score, doc, rel in selected:
        for path in doc.get("paths") or []:
            if not isinstance(path, dict):
                continue
            paths_out.append(
                {
                    "bridge_artifact": rel,
                    "path_id": path.get("path_id"),
                    "steps": path.get("steps"),
                    "note_ko": path.get("note_ko"),
                    "match_score": score,
                }
            )
        for vid in _verse_ids_from_bridge(doc):
            if vid not in seen_v:
                seen_v.add(vid)
                verse_ids.append(vid)

    lemma_hits: list[dict[str, Any]] = []
    for row in lemma_rows:
        dst = row.get("dst_node_id")
        if isinstance(dst, str) and any(dst in v or v.endswith(dst) for v in verse_ids):
            lemma_hits.append(
                {
                    "edge_id": row.get("edge_id"),
                    "src_node_id": row.get("src_node_id"),
                    "dst_node_id": dst,
                    "edge_type": row.get("edge_type"),
                }
            )

    seed_verses: list[str] = []
    if seed_chain:
        gr = seed_chain.get("graph_rag") if isinstance(seed_chain.get("graph_rag"), dict) else {}
        seed_verses = [str(x) for x in (gr.get("verse_node_ids") or [])[:20]]

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": query,
        "query_tokens": query_tokens,
        "bridges_matched": len(selected),
        "paths": paths_out,
        "verse_ids": verse_ids,
        "lemma_edge_hits": lemma_hits[:30],
        "seed_chain_verse_sample": seed_verses,
        "policy": {
            "no_prophecy_claim": True,
            "track_wall": "B_track_not_track_A",
            "router_kind": "logos_subgraph_v1",
        },
    }


def _query_from_gold(gold_path: Path, query_id: str) -> str | None:
    doc = _load_json(gold_path)
    if not doc:
        return None
    for it in doc.get("items") or []:
        if isinstance(it, dict) and str(it.get("id")) == query_id:
            return str(it.get("query_ko") or it.get("query_en") or "")
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", type=str, default="")
    ap.add_argument("--query-id", type=str, default="", help="Load query_ko from gold human JSON (e.g. q01)")
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--lemma-jsonl", type=Path, default=DEFAULT_LEMMA)
    ap.add_argument("--seed-chain-json", type=Path, default=DEFAULT_SEED_CHAIN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--top-bridges", type=int, default=2)
    args = ap.parse_args()

    query = (args.query or "").strip()
    if args.query_id:
        loaded = _query_from_gold(args.gold_json, args.query_id.strip())
        if not loaded:
            print(json.dumps({"ok": False, "error": f"query_id not found: {args.query_id}"}, ensure_ascii=False))
            return 2
        query = loaded
    if not query:
        query = "위기 가운데 언약의 안정과 신실"

    registry = _load_json(args.registry_json)
    if not registry:
        print(json.dumps({"ok": False, "error": "missing registry"}, ensure_ascii=False))
        return 2

    doc = route(
        query,
        registry=registry,
        lemma_rows=_load_jsonl(args.lemma_jsonl),
        seed_chain=_load_json(args.seed_chain_json),
        top_bridges=args.top_bridges,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "bridges_matched": doc["bridges_matched"],
                "paths": len(doc["paths"]),
                "verse_ids": len(doc["verse_ids"]),
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
