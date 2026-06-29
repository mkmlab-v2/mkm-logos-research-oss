#!/usr/bin/env python3
"""Query-time Logos subgraph GraphRAG for Studio API ([HYPO], B-track).

Reproduce:
  py scripts/encode_logos_studio_query_graphrag_v1.py --query "소망과 인내 시편"
  echo "반도체 유리 정제 은유" | py scripts/encode_logos_studio_query_graphrag_v1.py --query-stdin
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_showroom_qa_router_paths_v1 import (  # noqa: E402
    _build_ref_index,
    _router_path_v1,
)
from scripts.logos_studio_bloom_secondary_fetch_lib_v1 import (  # noqa: E402
    expand_verse_refs_via_bloom,
    load_bloom_index,
)
from scripts.run_logos_subgraph_graphrag_router_v1 import (  # noqa: E402
    DEFAULT_GEMATRIA_LEXICON,
    DEFAULT_LEMMA,
    DEFAULT_OSI_XREF,
    DEFAULT_REGISTRY,
    DEFAULT_SEED_CHAIN,
    DEFAULT_SINEW_XREF,
    DEFAULT_THEOGRAPHIC_ENTITY,
    _load_json,
    _load_jsonl,
    route,
)

DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_BLOOM = ROOT / "docs/final/artifacts/logos_studio_31k_bloom_secondary_fetch_v1_latest.json"


def _answer_ko_from_router(query: str, router_doc: dict, rp: dict | None) -> str:
    bridges = int(router_doc.get("bridges_matched") or 0)
    paths_n = len(router_doc.get("paths") or [])
    refs = (rp or {}).get("verse_refs") or []
    note = (rp or {}).get("note_ko") or ""
    path_id = (rp or {}).get("path_id") or ""
    parts = [
        f"[HYPO] query-time GraphRAG — bridges={bridges}, paths={paths_n}, verses={len(refs)}.",
    ]
    if note:
        parts.append(note)
    if path_id:
        parts.append(f"path_id={path_id}.")
    parts.append("citation lock 구절·경로만 — 인과 단답·TSK 전량 아님.")
    return " ".join(parts)


def encode_query(
    query: str,
    *,
    top_bridges: int = 3,
    graph_path: Path = DEFAULT_GRAPH,
) -> dict:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}

    registry = _load_json(DEFAULT_REGISTRY) or {}
    lemma_rows = _load_jsonl(DEFAULT_LEMMA)
    seed_chain = _load_json(DEFAULT_SEED_CHAIN)
    gematria_rows = _load_jsonl(DEFAULT_GEMATRIA_LEXICON)
    sinew_rows = _load_jsonl(DEFAULT_SINEW_XREF)
    osi_rows = _load_jsonl(DEFAULT_OSI_XREF)
    theographic_rows = _load_jsonl(DEFAULT_THEOGRAPHIC_ENTITY)

    if not graph_path.is_file():
        return {"ok": False, "error": "graph_slice_missing"}

    graph = json.loads(graph_path.read_text(encoding="utf-8-sig"))
    ref_index = _build_ref_index(graph)

    router_doc = route(
        q,
        registry=registry,
        lemma_rows=lemma_rows,
        seed_chain=seed_chain,
        gematria_lexicon_rows=gematria_rows,
        sinew_rows=sinew_rows,
        osi_rows=osi_rows,
        theographic_rows=theographic_rows,
        top_bridges=top_bridges,
    )

    rp = _router_path_v1("dynamic_graphrag", q, router_doc, graph, ref_index, preset=None)
    if not rp or not (rp.get("verse_refs") or rp.get("path_steps") or rp.get("node_ids")):
        return {
            "ok": False,
            "error": "no_path",
            "bridges_matched": int(router_doc.get("bridges_matched") or 0),
        }

    bloom_meta: dict[str, object] = {}
    bloom_index = load_bloom_index(DEFAULT_BLOOM)
    if bloom_index:
        primary_refs = list(rp.get("verse_refs") or [])
        expanded, bloom_meta = expand_verse_refs_via_bloom(q, primary_refs, bloom_index, max_extra=24)
        if bloom_meta.get("secondary_fetch_applied"):
            rp = dict(rp)
            rp["verse_refs"] = expanded[:64]
            rp["bloom_secondary_fetch_v1"] = bloom_meta

    highlight = list(rp.get("node_ids") or [])[:48]
    return {
        "ok": True,
        "schema": "logos_studio_query_graphrag_v1",
        "research_only": True,
        "non_gating": True,
        "query": q,
        "router_path_v1": rp,
        "bridges_matched": int(router_doc.get("bridges_matched") or 0),
        "paths_count": len(router_doc.get("paths") or []),
        "highlight_node_ids": highlight,
        "answer_ko": _answer_ko_from_router(q, router_doc, rp),
        "paths_preview": (router_doc.get("paths") or [])[:3],
        "bloom_secondary_fetch_v1": bloom_meta or None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default="")
    ap.add_argument("--query-stdin", action="store_true")
    ap.add_argument("--top-bridges", type=int, default=3)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    args = ap.parse_args()
    query = sys.stdin.read() if args.query_stdin else args.query
    out = encode_query(query, top_bridges=args.top_bridges, graph_path=args.graph_json)
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
