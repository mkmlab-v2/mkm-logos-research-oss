#!/usr/bin/env python3
"""Logos subgraph GraphRAG router v1 — concept_bridge + lemma edges ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref
ART = ROOT / "docs/final/artifacts"
DEFAULT_REGISTRY = ART / "logos_concept_bridge_registry_v1_latest.json"
DEFAULT_LEMMA = ART / "logos_lemma_verse_edges_v1.jsonl"
DEFAULT_SEED_CHAIN = ART / "logos_graph_seed_chain_v1_latest.json"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = ART / "logos_subgraph_graphrag_router_v1_latest.json"

SCHEMA = "logos_subgraph_graphrag_router_v1"
VERSION = "1.4.0"
TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+")

# Multi-syllable then single Hangul particles (longest-first).
_KO_PARTICLE_SUFFIXES = (
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "이며",
    "이라",
    "이고",
    "처럼",
    "보다",
    "한테",
)
_KO_SINGLE_PARTICLES = "이가은는을를의와과도로만"

# Query glue tokens — excluded from bridge overlap scoring (not thematic).
_SCORING_STOP_TOKENS = frozenset(
    {
        "때",
        "동시에",
        "엮이는",
        "성경",
        "어디인가",
        "경로는",
        "경로",
        "어디",
        "무엇",
        "어떻",
        "어떤",
        "있는",
        "없는",
        "무엇인가",
        "구조적으로",
        "대응되는",
        "서사",
        "거시",
        "현재",
        "logos",
        "사이에",
    }
)

# Query token → bridge haystack aliases (composite overlay queries).
_TOKEN_HAY_ALIASES: dict[str, tuple[str, ...]] = {
    "붕괴": ("붕괴", "무너", "collapse", "멸망", "fall"),
    "교역": ("교역", "trade", "바벨", "바벨론", "babylon"),
}

# Composite-query lanes: pick at most one best bridge per active lane.
_THEME_LANES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hubris_trade", ("바벨", "바벨론", "babel", "babylon", "교역", "hubris", "trade", "탑")),
    ("volatility", ("변동", "변동성", "volatility", "shock", "쇼크", "절제")),
    ("covenant", ("언약", "약속", "신실", "covenant")),
    ("judgment", ("심판", "경고", "무너", "붕괴", "judgment", "warning", "collapse")),
    ("restoration", ("회복", "갱신", "치유", "restoration", "restore")),
    ("mercy", ("자비", "긍휴", "mercy", "compassion")),
)


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


def _match_stems(token: str) -> list[str]:
    """Return token + particle-stripped stems for Korean substring overlap."""
    if len(token) < 2:
        return []
    stems: list[str] = [token]
    t = token
    for suf in _KO_PARTICLE_SUFFIXES:
        if len(t) > len(suf) + 1 and t.endswith(suf):
            stems.append(t[: -len(suf)])
    if len(t) >= 3:
        for p in _KO_SINGLE_PARTICLES:
            if t.endswith(p):
                stems.append(t[:-1])
                break
    seen: set[str] = set()
    out: list[str] = []
    for s in stems:
        if len(s) >= 2 and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _token_in_hay(token: str, hay: str) -> bool:
    for stem in _match_stems(token):
        if stem in hay:
            return True
    return False


def _bridge_haystack(bridge: dict[str, Any]) -> str:
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
    for path in bridge.get("paths") or []:
        if isinstance(path, dict):
            parts.append(str(path.get("note_ko") or ""))
    return " ".join(parts).lower()


def _token_aliases(token: str) -> tuple[str, ...]:
    return _TOKEN_HAY_ALIASES.get(token, (token,))


def _token_or_alias_in_hay(token: str, hay: str) -> bool:
    for alias in _token_aliases(token):
        if _token_in_hay(alias, hay):
            return True
    return False


def _bridge_token_hits(query_tokens: list[str], bridge: dict[str, Any]) -> set[str]:
    hay = _bridge_haystack(bridge)
    hits: set[str] = set()
    for t in query_tokens:
        if t in _SCORING_STOP_TOKENS:
            continue
        if _token_or_alias_in_hay(t, hay):
            hits.add(t)
    return hits


def _bridge_score(query_tokens: list[str], bridge: dict[str, Any]) -> int:
    return len(_bridge_token_hits(query_tokens, bridge))


def _active_theme_lanes(query: str) -> list[str]:
    q = query.lower()
    lanes: list[str] = []
    for lane_id, keywords in _THEME_LANES:
        if any(kw in q for kw in keywords):
            lanes.append(lane_id)
    return lanes


def _bridge_theme_lane(bridge: dict[str, Any]) -> str | None:
    blob = _bridge_haystack(bridge)
    for lane_id, keywords in _THEME_LANES:
        if any(kw in blob for kw in keywords):
            return lane_id
    return None


def _select_bridges_multi_coverage(
    candidates: list[tuple[int, set[str], dict[str, Any], str]],
    *,
    query: str,
    top_bridges: int,
    lane_backfill_pool: list[tuple[int, set[str], dict[str, Any], str]] | None = None,
) -> list[tuple[int, set[str], dict[str, Any], str]]:
    """Prefer diverse token coverage; force one bridge per active theme lane when composite."""
    if not candidates and not lane_backfill_pool:
        return []
    pool_all = lane_backfill_pool or candidates
    ranked = sorted(candidates, key=lambda x: (x[0], len(x[1])), reverse=True)
    selected: list[tuple[int, set[str], dict[str, Any], str]] = []
    selected_rels: set[str] = set()
    covered: set[str] = set()
    lanes_filled: set[str] = set()

    active_lanes = _active_theme_lanes(query)
    if len(active_lanes) >= 2:
        by_lane: dict[str, list[tuple[int, set[str], dict[str, Any], str]]] = {}
        for item in ranked:
            lane = _bridge_theme_lane(item[2])
            if lane:
                by_lane.setdefault(lane, []).append(item)
        for lane in active_lanes:
            pool = by_lane.get(lane) or []
            pool = sorted(pool, key=lambda x: (x[0], len(x[1])), reverse=True)
            if not pool:
                pool = [
                    item
                    for item in pool_all
                    if _bridge_theme_lane(item[2]) == lane and item[3] not in selected_rels
                ]
                pool = sorted(
                    pool,
                    key=lambda x: (x[0], len(x[2].get("paths") or []), len(x[1])),
                    reverse=True,
                )
            for item in pool:
                if item[3] in selected_rels:
                    continue
                selected.append(item)
                selected_rels.add(item[3])
                covered |= item[1]
                lanes_filled.add(lane)
                break

    composite_theme_only = len(active_lanes) >= 2

    for item in ranked:
        if len(selected) >= top_bridges:
            break
        score, hits, doc, rel = item
        if score <= 0 or rel in selected_rels:
            continue
        if composite_theme_only:
            lane = _bridge_theme_lane(doc)
            if lane not in active_lanes:
                continue
        if not selected:
            selected.append(item)
            selected_rels.add(rel)
            covered |= hits
            continue
        new_hits = hits - covered
        if new_hits or score >= selected[0][0]:
            selected.append(item)
            selected_rels.add(rel)
            covered |= hits

    if len(selected) < top_bridges and not composite_theme_only:
        for item in ranked:
            if len(selected) >= top_bridges:
                break
            if item[3] not in selected_rels and item[0] > 0:
                selected.append(item)
                selected_rels.add(item[3])

    selected.sort(key=lambda x: (x[0], len(x[1])), reverse=True)
    return selected[:top_bridges]


def _canonicalize_path_step(step: Any) -> str:
    raw = str(step).strip()
    if not raw:
        return raw
    if raw.startswith(
        ("concept:", "function:", "lemma:", "lemma_proxy:", "node:", "mc_", "func_", "lp_")
    ):
        return raw
    if raw.startswith("verse:"):
        inner = raw.split(":", 1)[1]
        c = canonical_verse_ref(inner)
        return c if c and "." in c else raw
    c = canonical_verse_ref(raw)
    if c and "." in c and re.match(r"^[A-Za-z0-9]", c):
        return c
    return raw


def _dedupe_canon_verse_ids(raw_ids: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for vid in raw_ids:
        c = canonical_verse_ref(str(vid))
        if not c or not re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
            continue
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _verse_ids_from_bridge(bridge: dict[str, Any]) -> list[str]:
    raw: list[str] = []
    seen: set[str] = set()
    for node in bridge.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("kind") != "verse_ref":
            continue
        vid = node.get("verse_id") or node.get("node_id", "").replace("verse:", "")
        if isinstance(vid, str) and vid and vid not in seen:
            seen.add(vid)
            raw.append(vid)
    hooks = bridge.get("graph_rag_hooks") if isinstance(bridge.get("graph_rag_hooks"), dict) else {}
    for sid in hooks.get("seed_verse_ids") or []:
        if isinstance(sid, str) and sid and sid not in seen:
            seen.add(sid)
            raw.append(sid)
    return _dedupe_canon_verse_ids(raw)


def route(
    query: str,
    *,
    registry: dict[str, Any],
    lemma_rows: list[dict[str, Any]],
    seed_chain: dict[str, Any] | None,
    top_bridges: int,
) -> dict[str, Any]:
    query_tokens = _tokens(query)
    candidates: list[tuple[int, set[str], dict[str, Any], str]] = []
    lane_backfill_pool: list[tuple[int, set[str], dict[str, Any], str]] = []
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
        hits = _bridge_token_hits(query_tokens, doc)
        item = (len(hits), hits, doc, rel)
        lane_backfill_pool.append(item)
        if hits:
            candidates.append(item)

    selected = _select_bridges_multi_coverage(
        candidates,
        query=query,
        top_bridges=top_bridges,
        lane_backfill_pool=lane_backfill_pool,
    )
    active_lanes = _active_theme_lanes(query)

    paths_out: list[dict[str, Any]] = []
    verse_ids: list[str] = []
    seen_v: set[str] = set()
    for score, _hits, doc, rel in selected:
        for path in doc.get("paths") or []:
            if not isinstance(path, dict):
                continue
            steps_raw = path.get("steps") or []
            steps_out = [_canonicalize_path_step(s) for s in steps_raw if s is not None]
            paths_out.append(
                {
                    "bridge_artifact": rel,
                    "path_id": path.get("path_id"),
                    "steps": steps_out,
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

    verse_ids = _dedupe_canon_verse_ids(verse_ids)
    seed_verses_canon = _dedupe_canon_verse_ids(seed_verses) if seed_verses else []

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": query,
        "query_tokens": query_tokens,
        "theme_lanes_active": active_lanes,
        "bridges_matched": len(selected),
        "paths": paths_out,
        "verse_ids": verse_ids,
        "lemma_edge_hits": lemma_hits[:30],
        "seed_chain_verse_sample": seed_verses_canon or seed_verses,
        "policy": {
            "no_prophecy_claim": True,
            "track_wall": "B_track_not_track_A",
            "router_kind": "logos_subgraph_v1",
            "bridge_selection": "multi_coverage_v1",
            "verse_ref_canonical_at_source": True,
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
    if args.query_id and not query:
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
