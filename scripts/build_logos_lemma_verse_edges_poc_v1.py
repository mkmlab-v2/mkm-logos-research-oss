#!/usr/bin/env python3
"""Phase-1 lemma→verse edge PoC from signed gold bridges (no graph merge, B-track)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_lemma_verse_edges_poc_v1_latest.json"
DEFAULT_BRIDGES = (
    ROOT / "docs/final/artifacts/logos_concept_bridge_gold_q09_prudence_liquidity_stress_gemini_v1_latest.json",
    ROOT / "docs/final/artifacts/logos_concept_bridge_gold_q10_resilience_capitulation_phase_gemini_v1_latest.json",
)


def _normalize_verse_id(raw: str) -> str:
    s = raw.strip()
    if "::" in s:
        s = s.split("::", 1)[1]
    return s


def _lemma_from_node(node: dict[str, Any]) -> str | None:
    if node.get("kind") != "lemma_proxy":
        return None
    nid = str(node.get("node_id") or "")
    label = str(node.get("label_ko") or "")
    if nid.startswith("lemma"):
        return nid.replace("lemma_", "").replace("lemma:", "")
    return label or nid or None


_BOOK_MAP = {
    "prov": "Prov",
    "jer": "Jer",
    "dan": "Dan",
    "lam": "Lam",
    "isa": "Isa",
    "ps": "Ps",
}


def _verse_id_from_node_id(nid: str) -> str | None:
    s = nid.replace("verse_", "").replace("verse:", "").strip()
    if "." in s:
        book, rest = s.split(".", 1)
        b = _BOOK_MAP.get(book.lower(), book[:1].upper() + book[1:].lower())
        return f"{b}.{rest}"
    parts = s.split("_")
    if len(parts) < 2:
        return None
    book = _BOOK_MAP.get(parts[0].lower(), parts[0].capitalize())
    return f"{book}.{parts[1]}"


def _edges_from_bridge(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8"))
    nodes = doc.get("nodes") if isinstance(doc.get("nodes"), list) else []
    by_id = {str(n.get("node_id")): n for n in nodes if isinstance(n, dict) and n.get("node_id")}
    edges: list[dict[str, Any]] = []
    paths = doc.get("paths") if isinstance(doc.get("paths"), list) else []
    qid = (doc.get("query") or {}).get("gold_query_id") if isinstance(doc.get("query"), dict) else None
    for p in paths:
        if not isinstance(p, dict):
            continue
        steps = p.get("steps")
        if not isinstance(steps, list):
            continue
        lemma_node = verse_node = None
        for sid in steps:
            n = by_id.get(str(sid))
            if not isinstance(n, dict):
                continue
            if n.get("kind") == "lemma_proxy" and lemma_node is None:
                lemma_node = n
            if n.get("kind") == "verse_ref":
                verse_node = n
        if not lemma_node or not verse_node:
            continue
        verse_id = _verse_id_from_node_id(str(verse_node.get("node_id") or ""))
        if not verse_id:
            hooks = doc.get("graph_rag_hooks") if isinstance(doc.get("graph_rag_hooks"), dict) else {}
            seeds = hooks.get("seed_verse_ids") if isinstance(hooks.get("seed_verse_ids"), list) else []
            for s in seeds:
                if isinstance(s, str):
                    verse_id = _normalize_verse_id(s)
                    break
        edges.append(
            {
                "gold_query_id": qid,
                "lemma_proxy": _lemma_from_node(lemma_node),
                "verse_id": verse_id,
                "path_id": p.get("path_id"),
                "note_ko": p.get("note_ko"),
                "bridge_artifact": path.name,
                "graph_router_invoked": False,
            }
        )
    return edges


def main() -> int:
    ap = argparse.ArgumentParser(description="Lemma→verse PoC edges from gold bridges.")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bridge", type=Path, action="append", default=[])
    args = ap.parse_args()
    bridges = args.bridge or list(DEFAULT_BRIDGES)
    all_edges: list[dict[str, Any]] = []
    for bp in bridges:
        all_edges.extend(_edges_from_bridge(bp))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": "logos_lemma_verse_edges_poc_v1",
        "version": "1.0.0",
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "non_gating": True,
        "generated_at_utc": now,
        "edge_count": len(all_edges),
        "edges": all_edges,
        "note": "Educational proxy edges from human-signed bridges; not Phase-1 graph ingest.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out.resolve()} ({len(all_edges)} edges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
