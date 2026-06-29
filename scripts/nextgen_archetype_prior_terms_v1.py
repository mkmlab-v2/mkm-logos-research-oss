"""[HYPO] Extract salience boost terms from nav frame + concept_bridge bindings."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

WORD_RE = re.compile(r"[A-Za-z0-9_가-힣]{2,}")


def _tokens_from_label(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def terms_from_concept_bridge(doc: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        for key in ("label_ko", "label_en", "label"):
            v = node.get(key)
            if v:
                terms.update(_tokens_from_label(str(v)))
        nid = str(node.get("node_id", ""))
        if nid.startswith("lemma:"):
            parts = nid.split(":")
            if len(parts) >= 3:
                terms.add(parts[-1].replace("_proxy", "").lower())
    q = doc.get("query") or {}
    for key in ("label_ko", "concept_id"):
        v = q.get(key)
        if v:
            terms.update(_tokens_from_label(str(v).replace("concept:", "")))
    return terms


def terms_from_nav_frame(doc: dict[str, Any]) -> set[str]:
    terms: set[str] = set()
    graph = doc.get("navigation_graph") or {}
    for node in graph.get("archetype_nodes") or []:
        for key in ("label_ko", "node_id"):
            v = node.get(key)
            if v:
                terms.update(
                    _tokens_from_label(
                        str(v).replace("archetype:", "").replace("function:", "")
                    )
                )
    return terms


def load_prior_terms(
    *,
    root: Path,
    salience_hook_path: Path | None = None,
    nav_frame_path: Path | None = None,
    logos_pack_path: Path | None = None,
    max_terms: int = 256,
) -> tuple[frozenset[str], dict[str, Any]]:
    """Merge terms from hook-bound bridges, nav frame, and optional logos pack."""
    meta: dict[str, Any] = {
        "bridge_sources": [],
        "nav_frame": None,
        "logos_pack": None,
    }
    terms: set[str] = set()

    if nav_frame_path and nav_frame_path.is_file():
        nav = json.loads(nav_frame_path.read_text(encoding="utf-8-sig"))
        terms |= terms_from_nav_frame(nav)
        meta["nav_frame"] = str(nav_frame_path)

    if salience_hook_path and salience_hook_path.is_file():
        hook = json.loads(salience_hook_path.read_text(encoding="utf-8-sig"))
        for binding in hook.get("concept_bridge_bindings") or []:
            art = binding.get("bridge_artifact")
            if not art:
                continue
            p = root / str(art)
            if not p.is_file():
                meta["bridge_sources"].append({"artifact": art, "present": False})
                continue
            bridge = json.loads(p.read_text(encoding="utf-8-sig"))
            terms |= terms_from_concept_bridge(bridge)
            meta["bridge_sources"].append(
                {
                    "artifact": art,
                    "present": True,
                    "concept_id": binding.get("concept_id"),
                }
            )

    if logos_pack_path and logos_pack_path.is_file():
        doc = json.loads(logos_pack_path.read_text(encoding="utf-8-sig"))
        for edge in doc.get("sample_edges") or doc.get("edges") or []:
            if isinstance(edge, dict):
                for k in ("src_term", "dst_term", "term", "label"):
                    v = edge.get(k)
                    if v:
                        terms.add(str(v).lower())
        for block in doc.get("bridge_terms") or []:
            if isinstance(block, str):
                terms.add(block.lower())
        meta["logos_pack"] = str(logos_pack_path)

    trimmed = frozenset(sorted(terms)[:max_terms])
    meta["term_count"] = len(trimmed)
    return trimmed, meta
