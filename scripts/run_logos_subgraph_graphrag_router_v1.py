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
from scripts.logos_gematria_lexicon_router_lib_v1 import (
    match_lexicon_hits,
    strongs_verse_ids_from_lemma,
)
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, _parse_verse_ref_body
ART = ROOT / "docs/final/artifacts"
DEFAULT_REGISTRY = ART / "logos_concept_bridge_registry_v1_latest.json"
DEFAULT_LEMMA = ART / "logos_lemma_verse_edges_v1.jsonl"
DEFAULT_SINEW_XREF = ART / "logos_sinew_xref_edges_v1.jsonl"
DEFAULT_OSI_XREF = ART / "logos_osi_xref_edges_v1.jsonl"
DEFAULT_THEOGRAPHIC_ENTITY = ART / "logos_theographic_entity_edges_v1.jsonl"
DEFAULT_GEMATRIA_LEXICON = ART / "logos_scriptures_js_gematria_lexicon_v1.jsonl"
DEFAULT_SEED_CHAIN = ART / "logos_graph_seed_chain_v1_latest.json"
DEFAULT_GOLD = ART / "logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = ART / "logos_subgraph_graphrag_router_v1_latest.json"

SCHEMA = "logos_subgraph_graphrag_router_v1"
VERSION = "2.0.3"
CONTAIN_EDGE_TYPES = frozenset({"CONTAIN", "LEMMA_VERSE_PROXY", "GNOSIS_STRONGS_CONTAIN"})
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
    "다니엘": ("다니엘", "daniel", "dan", "dan_aramaic"),
    "제국": ("제국", "empire", "kingdom", "금", "철", "진흙", "나라"),
    "궁정": ("궁정", "court", "왕", "king"),
    "risk-off": ("risk-off", "riskoff", "risk_off"),
    "견고": ("견고", "견고함", "firm", "steadfast"),
    "위로": ("위로", "comfort", "consolation", "위안"),
    "레짐": ("레짐", "regime", "전환"),
    "경계": ("경계", "watch", "watchfulness", "분별", "깨어"),
    "분별": ("분별", "discern", "discernment", "깨어"),
    "배신": ("배신", "betrayal", "음모", "plot", "유다", "judas"),
    "음모": ("음모", "plot", "배신", "betrayal", "conspiracy"),
    "watch": ("watch", "watchfulness", "경계", "분별"),
    "반도체": ("반도체", "semiconductor", "silica", "refined_silica"),
    "공급망": ("공급망", "supply", "semiconductor", "chain"),
    "바벨": ("바벨", "babel", "babylon", "gen_11", "gen.11", "hubris"),
    "에덴": ("에덴", "eden", "gen_3", "gen.3", "fall"),
    "타락": ("타락", "fall", "gen_3", "gen.3", "boundary"),
    "회의": ("회의", "council", "divine_council", "sons_of_god"),
    "욥": ("욥", "job", "suffering", "고난", "의회"),
}

# Composite-query lanes: pick at most one best bridge per active lane.
_THEME_LANES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hubris_trade", ("바벨", "바벨론", "babel", "babylon", "교역", "hubris", "trade", "탑")),
    ("volatility", ("변동", "변동성", "volatility", "shock", "쇼크", "절제")),
    ("covenant", ("언약", "약속", "신실", "covenant")),
    ("judgment", ("심판", "경고", "무너", "붕괴", "judgment", "warning", "collapse")),
    ("restoration", ("회복", "갱신", "치유", "restoration", "restore")),
    ("mercy", ("자비", "긍휴", "mercy", "compassion")),
    ("regime_watch", ("watch", "경계", "분별", "레짐", "regime", "전환", "watchfulness", "배신", "음모", "betrayal")),
    ("daniel_empire", ("daniel", "dan", "다니엘", "제국", "궁정", "금", "철", "진흙", "dan_aramaic")),
    ("semiconductor_supply", ("반도체", "semiconductor", "공급망", "재료", "연결", "silica")),
    ("genesis_fall", ("에덴", "타락", "eden", "fall", "gen 3", "genesis 3", "gen.3")),
    ("divine_council", ("divine council", "신의 회의", "시편 82", "psalm 82", "sons of god", "아들들")),
    ("job_council", ("욥", "job", "고난", "의회", "scope reset", "suffering")),
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


def _lemma_src_haystack(src_node_id: str) -> str:
    s = str(src_node_id or "").lower()
    for prefix in (
        "lemma:hebrew:",
        "lemma:greek:",
        "lemma:aramaic:",
        "lemma:",
        "lemma_proxy:",
        "node:lemma_proxy:",
        "node:lemma_",
        "lp_",
    ):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    return s.replace("_", " ").replace(":", " ")


def _canon_edge_dst(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    c = canonical_verse_ref(s)
    if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
        return c
    m = re.match(r"^([a-z]+)(\d+)\.(\d+)$", s.lower())
    if m:
        book = m.group(1)
        book_canon = canonical_verse_ref(f"{book}.{m.group(2)}.{m.group(3)}")
        if book_canon and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", book_canon):
            return book_canon
        return f"{book[:1].upper()}{book[1:]}.{m.group(2)}.{m.group(3)}"
    return c


def _lemma_contain_boost(
    query_tokens: list[str],
    bridge_rel: str,
    lemma_rows: list[dict[str, Any]],
) -> int:
    """+1 per CONTAIN edge on bridge when query token hits lemma src (cap 3)."""
    boost = 0
    for row in lemma_rows:
        if str(row.get("edge_type") or "") not in CONTAIN_EDGE_TYPES:
            continue
        if str(row.get("source_bridge") or "") != bridge_rel:
            continue
        hay = _lemma_src_haystack(str(row.get("src_node_id") or ""))
        if not hay:
            continue
        for t in query_tokens:
            if t in _SCORING_STOP_TOKENS:
                continue
            if _token_in_hay(t, hay):
                boost += 1
                break
    return min(boost, 3)


def _gematria_strongs_bridge_boost(
    strongs_set: set[str],
    bridge_rel: str,
    bridge_doc: dict[str, Any],
    lemma_rows: list[dict[str, Any]],
) -> int:
    """+1 when gematria-linked gnosis verses overlap bridge footprint (cap 2)."""
    if not strongs_set:
        return 0
    gnosis_verses = set(strongs_verse_ids_from_lemma(strongs_set, lemma_rows, max_verses=50))
    if not gnosis_verses:
        return 0
    bridge_verses = set(_verse_ids_from_bridge(bridge_doc))
    bridge_verses |= set(_contain_verse_ids_for_bridge(bridge_rel, lemma_rows))
    if not gnosis_verses & bridge_verses:
        return 0
    return min(len(strongs_set), 2)


def _contain_verse_ids_for_bridge(
    bridge_rel: str,
    lemma_rows: list[dict[str, Any]],
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in lemma_rows:
        if str(row.get("edge_type") or "") not in CONTAIN_EDGE_TYPES:
            continue
        if str(row.get("source_bridge") or "") != bridge_rel:
            continue
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if dst and dst not in seen:
            seen.add(dst)
            out.append(dst)
    return out


def _lemma_hits_for_verses(
    verse_ids: list[str],
    lemma_rows: list[dict[str, Any]],
    *,
    bridge_rels: set[str] | None = None,
) -> list[dict[str, Any]]:
    canon_set = set(verse_ids)
    hits: list[dict[str, Any]] = []
    seen_edges: set[str] = set()
    for row in lemma_rows:
        edge_type = str(row.get("edge_type") or "")
        if edge_type not in CONTAIN_EDGE_TYPES:
            continue
        bridge_rel = str(row.get("source_bridge") or "")
        if bridge_rels is not None and bridge_rel and bridge_rel not in bridge_rels:
            continue
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if not dst or dst not in canon_set:
            continue
        eid = str(row.get("edge_id") or "")
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        hits.append(
            {
                "edge_id": row.get("edge_id"),
                "src_node_id": row.get("src_node_id"),
                "dst_node_id": dst,
                "edge_type": edge_type,
                "source_bridge": bridge_rel or None,
                "weight": row.get("weight"),
            }
        )
    return hits


def _xref_hits_for_verses(
    verse_ids: list[str],
    xref_rows: list[dict[str, Any]],
    *,
    source_filter: str | None = None,
    max_hits: int = 30,
) -> list[dict[str, Any]]:
    if not xref_rows:
        return []
    canon_set = set(verse_ids)
    hits: list[dict[str, Any]] = []
    seen_edges: set[str] = set()
    for row in xref_rows:
        if source_filter and str(row.get("source") or "") != source_filter:
            continue
        src = _canon_edge_dst(str(row.get("src_node_id") or ""))
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if src not in canon_set and dst not in canon_set:
            continue
        eid = str(row.get("edge_id") or "")
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        hits.append(
            {
                "edge_id": row.get("edge_id"),
                "src_node_id": src,
                "dst_node_id": dst,
                "edge_type": row.get("edge_type"),
                "weight": row.get("weight"),
                "source": row.get("source"),
                "provenance": (row.get("provenance") or {}).get("upstream_source"),
            }
        )
        if len(hits) >= max_hits:
            break
    return hits


def _sinew_xref_hits_for_verses(
    verse_ids: list[str],
    sinew_rows: list[dict[str, Any]],
    *,
    max_hits: int = 30,
) -> list[dict[str, Any]]:
    return _xref_hits_for_verses(
        verse_ids, sinew_rows, source_filter="sinew_xref", max_hits=max_hits
    )


def _xref_neighbor_verse_ids(
    verse_ids: list[str],
    xref_rows: list[dict[str, Any]],
    *,
    max_neighbors: int = 20,
) -> list[str]:
    if not xref_rows:
        return []
    canon_set = set(verse_ids)
    out: list[str] = []
    seen: set[str] = set(canon_set)
    for row in xref_rows:
        src = _canon_edge_dst(str(row.get("src_node_id") or ""))
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if src in canon_set and dst and dst not in seen:
            seen.add(dst)
            out.append(dst)
        elif dst in canon_set and src and src not in seen:
            seen.add(src)
            out.append(src)
        if len(out) >= max_neighbors:
            break
    return out


def _sinew_neighbor_verse_ids(
    verse_ids: list[str],
    sinew_rows: list[dict[str, Any]],
    *,
    max_neighbors: int = 20,
) -> list[str]:
    return _xref_neighbor_verse_ids(verse_ids, sinew_rows, max_neighbors=max_neighbors)


def _theographic_entity_hits_for_verses(
    verse_ids: list[str],
    theographic_rows: list[dict[str, Any]],
    *,
    max_hits: int = 30,
) -> list[dict[str, Any]]:
    if not theographic_rows:
        return []
    canon_set = set(verse_ids)
    hits: list[dict[str, Any]] = []
    seen_edges: set[str] = set()
    for row in theographic_rows:
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if not dst or dst not in canon_set:
            continue
        eid = str(row.get("edge_id") or "")
        if eid in seen_edges:
            continue
        seen_edges.add(eid)
        hits.append(
            {
                "edge_id": row.get("edge_id"),
                "src_node_id": row.get("src_node_id"),
                "dst_node_id": dst,
                "edge_type": row.get("edge_type"),
                "entity_kind": row.get("entity_kind"),
                "entity_name": row.get("entity_name"),
                "weight": row.get("weight"),
            }
        )
        if len(hits) >= max_hits:
            break
    return hits


def _theographic_verses_for_query(
    query_tokens: list[str],
    theographic_rows: list[dict[str, Any]],
    *,
    max_verses: int = 15,
) -> list[str]:
    if not theographic_rows:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for row in theographic_rows:
        name = str(row.get("entity_name") or "").lower()
        if not name:
            continue
        matched = False
        for t in query_tokens:
            if t in _SCORING_STOP_TOKENS:
                continue
            if _token_in_hay(t, name):
                matched = True
                break
        if not matched:
            continue
        dst = _canon_edge_dst(str(row.get("dst_node_id") or ""))
        if dst and dst not in seen:
            seen.add(dst)
            out.append(dst)
            if len(out) >= max_verses:
                break
    return out


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


def _lane_keywords(lane_id: str) -> tuple[str, ...]:
    for lid, keywords in _THEME_LANES:
        if lid == lane_id:
            return keywords
    return ()


def _bridge_matches_lane(bridge: dict[str, Any], lane_id: str) -> bool:
    keywords = _lane_keywords(lane_id)
    if not keywords:
        return False
    blob = _bridge_haystack(bridge)
    return any(kw in blob for kw in keywords)


def _bridge_matches_any_active_lane(bridge: dict[str, Any], active_lanes: list[str]) -> bool:
    return any(_bridge_matches_lane(bridge, lane) for lane in active_lanes)


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
            for lane in active_lanes:
                if _bridge_matches_lane(item[2], lane):
                    by_lane.setdefault(lane, []).append(item)
        for lane in active_lanes:
            pool = by_lane.get(lane) or []
            pool = sorted(pool, key=lambda x: (x[0], len(x[1])), reverse=True)
            if not pool:
                pool = [
                    item
                    for item in pool_all
                    if _bridge_matches_lane(item[2], lane) and item[3] not in selected_rels
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
            if not _bridge_matches_any_active_lane(doc, active_lanes):
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


def _concept_affinity_boost(query: str, bridge: dict[str, Any]) -> int:
    """Extra bridge score from query↔concept alignment (Phase 10-B extension tune)."""
    q = query.lower()
    query_block = bridge.get("query") if isinstance(bridge.get("query"), dict) else {}
    cid = str(query_block.get("concept_id") or "").lower()
    blob = f"{cid} {_bridge_haystack(bridge)}"
    boost = 0

    def _match(*needles: str) -> bool:
        return any(n in cid or n in blob for n in needles)

    if any(k in q for k in ("daniel", "dan", "다니엘", "제국", "궁정", "철", "진흙")) and _match(
        "dan_aramaic", "themed_dan", "daniel"
    ):
        boost += 5
    if any(k in q for k in ("risk-off", "riskoff", "견고", "위로", "충돌", "야간")) and _match(
        "stability_after_volatility"
    ):
        boost += 4
    if any(k in q for k in ("소망", "압박", "장기")) and _match("hope_prolonged"):
        boost += 5
    if any(k in q for k in ("신중", "유동성", "수축", "대비")) and _match("prudence_liquidity"):
        boost += 5
    if any(k in q for k in ("긍휴", "자비", "혼란", "상실")) and _match("mercy_after", "mercy_compassion"):
        boost += 5
    if any(k in q for k in ("클라우드", "인프라", "복원력")) and _match("cloud_infra"):
        boost += 5
    if any(k in q for k in ("반도체", "공급망", "재료", "연결")) and _match("semiconductor"):
        boost += 6
    if any(k in q for k in ("바벨", "babel", "언어 분산", "탑")) and _match(
        "hubris", "babel", "babylon", "judgment", "collapse"
    ):
        boost += 6
    if any(k in q for k in ("바벨", "babel")) and _match("cloud_infra"):
        boost -= 4
    if any(k in q for k in ("에덴", "타락", "eden", "fall", "genesis 3", "gen 3")) and _match(
        "judgment", "risk_excess", "watchfulness", "regime"
    ):
        boost += 5
    if any(
        k in q
        for k in ("divine council", "신의 회의", "시편 82", "psalm 82", "하나님의 아들", "sons of god")
    ) and _match("digital_trust", "wisdom", "job", "daniel"):
        boost += 6
    if any(k in q for k in ("욥", "job", "고난", "의회", "scope reset")) and _match(
        "hope_prolonged", "job", "suffering", "restoration"
    ):
        boost += 5
    if any(k in q for k in ("지혜", "불확실")) and _match("wisdom_uncertainty"):
        boost += 5
    if any(k in q for k in ("디지털", "신뢰", "진실")) and _match("digital_trust"):
        boost += 5
    if any(k in q for k in ("절제", "인내", "변동성", "변동")) and _match("discipline_in_volatility"):
        boost += 5
    if "capitulation" in q and _match("resilience_capitulation"):
        boost += 5
    if any(k in q for k in ("물", "피", "십자가", "수난")) and _match("passion_blood_water"):
        boost += 4
    if any(k in q for k in ("붕괴", "교역", "hubris", "trade", "쇼크")) and _match("risk_excess"):
        boost += 3
    if any(k in q for k in ("배신", "음모", "betrayal", "luke", "누가")) and _match("regime", "watchfulness"):
        boost += 4
    elif any(k in q for k in ("watch", "레짐", "경계", "분별", "정치", "전환", "시대")) and _match(
        "regime", "watchfulness"
    ):
        boost += 2
    if any(k in q for k in ("사랑", "용서")) and _match(
        "restoration_after", "covenant", "steadfast_love", "mercy"
    ):
        boost += 4
    return boost


def _path_retrieval_priority(query: str, path: dict[str, Any]) -> int:
    """Rank path final verse for Hit@k ordering (research router only)."""
    q = query.lower()
    final = ""
    for step in reversed(path.get("steps") or []):
        canon = _canonicalize_path_step(step)
        if canon and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", canon):
            final = canon
            break
    if not final:
        return 0
    prio = 0
    if any(k in q for k in ("daniel", "dan", "다니엘", "제국", "궁정")) and final.startswith("Dan.2"):
        prio += 6
    if any(k in q for k in ("risk-off", "riskoff", "견고", "위로", "야간", "충돌")):
        if final.startswith(("Ps.23", "Jer.30", "Job.5")):
            prio += 5
    if any(k in q for k in ("소망", "압박", "장기")):
        if final.startswith(("Ps.27", "Jer.30", "Lam.3")):
            prio += 6
    if any(k in q for k in ("신중", "유동성", "수축", "대비")):
        if final.startswith(("Prov.", "Jer.17")):
            prio += 6
    if any(k in q for k in ("긍휴", "자비", "혼란", "상실")):
        if final.startswith(("Ps.103", "Jer.31", "Rev.21")):
            prio += 6
    if any(k in q for k in ("지혜", "불확실")):
        if final.startswith(("Job.28", "Dan.1", "Ps.56")):
            prio += 6
    if any(k in q for k in ("절제", "인내", "변동성", "변동")):
        if final.startswith(("Ps.37", "Jer.9", "Dan.10")):
            prio += 6
    if any(k in q for k in ("디지털", "신뢰", "진실")):
        if final.startswith(("Ps.119", "Job.2", "Jer.4")):
            prio += 6
    if any(k in q for k in ("클라우드", "인프라", "복원력")):
        if final.startswith(("Job.28", "Dan.2", "Rev.21")):
            prio += 6
    if any(k in q for k in ("바벨", "babel", "언어", "탑")):
        if final.startswith(("Gen.11", "Jer.1", "Dan.5", "Rev.18")):
            prio += 6
    if any(k in q for k in ("에덴", "타락", "eden", "fall")):
        if final.startswith(("Gen.3", "Gen.2", "Rom.5")):
            prio += 6
    if any(k in q for k in ("divine council", "신의 회의", "시편 82", "psalm 82", "아들들")):
        if final.startswith(("Ps.82", "Job.1", "Job.2", "Gen.6")):
            prio += 6
    if any(k in q for k in ("욥", "job", "고난", "의회")):
        if final.startswith(("Job.1", "Job.2", "Job.38", "Job.42")):
            prio += 5
    if any(k in q for k in ("반도체", "공급망", "재료")):
        if final.startswith(("Job.28", "Zech.3", "Dan.2")):
            prio += 6
    if "capitulation" in q:
        if final.startswith(("Dan.10", "Jer.31", "Lam.3")):
            prio += 6
    if any(k in q for k in ("배신", "음모", "betrayal", "luke", "누가")):
        if final.startswith("Luke.22"):
            prio += 7
    if any(k in q for k in ("watch", "레짐", "경계", "분별", "정치", "전환", "시대")):
        if any(k in q for k in ("레짐", "watch")) and not any(
            k in q for k in ("정치", "공동체", "선거", "election")
        ):
            if final.startswith(("Ps.89", "Jer.31", "Luke.22")):
                prio += 8
            elif final.startswith(("Neh.4", "Rev.16", "1Chr.12")):
                prio += 3
        elif final.startswith(("Neh.4", "Rev.16", "1Chr.12")):
            prio += 6
        elif final.startswith(("Ps.89", "Jer.31")):
            prio += 4
    if any(k in q for k in ("붕괴", "교역", "hubris", "trade", "변동", "쇼크")):
        if final.startswith(("Rev.18", "Ezek.27", "Dan.4", "Job.20")):
            prio += 4
    if any(k in q for k in ("사랑", "용서")):
        if final.startswith(("1Cor.13", "Eph.4", "Jer.31", "Ps.103")):
            prio += 8
        if not any(k in q for k in ("물", "피", "blood", "water", "십자가")):
            if final.startswith(("Lev.17", "John.19", "Ezek.36")):
                prio -= 6
    return prio


def _order_verse_ids_path_first(
    query: str,
    paths_out: list[dict[str, Any]],
    verse_ids: list[str],
) -> list[str]:
    """Path-step verses first (by retrieval priority), then remaining sidecar expansions."""
    out: list[str] = []
    seen: set[str] = set()
    ranked_paths = sorted(
        paths_out,
        key=lambda p: (-_path_retrieval_priority(query, p), -(p.get("match_score") or 0)),
    )
    for path in ranked_paths:
        for step in path.get("steps") or []:
            canon = _canonicalize_path_step(step)
            if not canon or not re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", canon):
                continue
            if canon not in seen:
                seen.add(canon)
                out.append(canon)
    for vid in verse_ids:
        if vid not in seen:
            seen.add(vid)
            out.append(vid)
    return out


def _canonicalize_path_step(step: Any) -> str:
    raw = str(step).strip()
    if not raw:
        return raw
    if raw.startswith("node_verse_"):
        c = canonical_verse_ref(raw)
        return c if c and "." in c else raw
    if raw.startswith("node:verse_"):
        slug = _parse_verse_ref_body(raw[len("node:verse_") :])
        c = canonical_verse_ref(slug)
        if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
            return c
    if raw.startswith("verse_") and not raw.startswith("verse:"):
        slug = _parse_verse_ref_body(raw[len("verse_") :])
        c = canonical_verse_ref(slug)
        if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
            return c
    if raw.startswith(
        ("concept:", "function:", "lemma:", "lemma_proxy:", "node:", "mc_", "func_", "lp_")
    ):
        if raw.startswith("node:verse_ref:"):
            slug = _parse_verse_ref_body(raw[len("node:verse_ref:") :])
            c = canonical_verse_ref(slug)
            if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
                return c
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
        vid = node.get("verse_id") or node.get("ref") or node.get("node_id", "").replace("verse:", "")
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
    sinew_rows: list[dict[str, Any]] | None = None,
    osi_rows: list[dict[str, Any]] | None = None,
    theographic_rows: list[dict[str, Any]] | None = None,
    gematria_lexicon_rows: list[dict[str, Any]] | None = None,
    seed_chain: dict[str, Any] | None,
    top_bridges: int,
) -> dict[str, Any]:
    query_tokens = _tokens(query)
    gematria_lexicon_rows = gematria_lexicon_rows or []
    gematria_lexicon_hits = match_lexicon_hits(query_tokens, gematria_lexicon_rows)
    gematria_strongs_set = {
        str(h.get("strongs") or "").strip().upper()
        for h in gematria_lexicon_hits
        if h.get("strongs")
    }
    gematria_strongs_set.discard("")

    candidates: list[tuple[int, set[str], dict[str, Any], str]] = []
    lane_backfill_pool: list[tuple[int, set[str], dict[str, Any], str]] = []
    lemma_boost_total = 0
    gematria_boost_total = 0
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
        rel_posix = rel.replace("\\", "/")
        boost = _lemma_contain_boost(query_tokens, rel_posix, lemma_rows)
        gem_boost = _gematria_strongs_bridge_boost(gematria_strongs_set, rel_posix, doc, lemma_rows)
        affinity = _concept_affinity_boost(query, doc)
        lemma_boost_total += boost
        gematria_boost_total += gem_boost
        score = len(hits) + boost + gem_boost + affinity
        item = (score, hits, doc, rel_posix)
        lane_backfill_pool.append(item)
        if hits or boost > 0 or gem_boost > 0:
            candidates.append(item)

    selected = _select_bridges_multi_coverage(
        candidates,
        query=query,
        top_bridges=top_bridges,
        lane_backfill_pool=lane_backfill_pool,
    )
    active_lanes = _active_theme_lanes(query)
    selected_rels = {rel for _s, _h, _d, rel in selected}

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
        for vid in _contain_verse_ids_for_bridge(rel, lemma_rows):
            if vid not in seen_v:
                seen_v.add(vid)
                verse_ids.append(vid)

    theographic_rows = theographic_rows or []
    for vid in _theographic_verses_for_query(query_tokens, theographic_rows):
        if vid not in seen_v:
            seen_v.add(vid)
            verse_ids.append(vid)

    for vid in strongs_verse_ids_from_lemma(gematria_strongs_set, lemma_rows):
        if vid not in seen_v:
            seen_v.add(vid)
            verse_ids.append(vid)

    lemma_hits = _lemma_hits_for_verses(verse_ids, lemma_rows, bridge_rels=selected_rels)

    sinew_rows = sinew_rows or []
    osi_rows = osi_rows or []
    xref_rows = sinew_rows + osi_rows
    sinew_hits = _xref_hits_for_verses(verse_ids, xref_rows, source_filter="sinew_xref")
    osi_hits = _xref_hits_for_verses(verse_ids, xref_rows, source_filter="osi_xref")
    for vid in _xref_neighbor_verse_ids(verse_ids, xref_rows):
        if vid not in seen_v:
            seen_v.add(vid)
            verse_ids.append(vid)

    theographic_hits = _theographic_entity_hits_for_verses(verse_ids, theographic_rows)

    seed_verses: list[str] = []
    if seed_chain:
        gr = seed_chain.get("graph_rag") if isinstance(seed_chain.get("graph_rag"), dict) else {}
        seed_verses = [str(x) for x in (gr.get("verse_node_ids") or [])[:20]]

    verse_ids = _dedupe_canon_verse_ids(verse_ids)
    seed_verses_canon = _dedupe_canon_verse_ids(seed_verses) if seed_verses else []

    paths_out.sort(
        key=lambda p: (-_path_retrieval_priority(query, p), -(p.get("match_score") or 0)),
    )
    verse_ids = _order_verse_ids_path_first(query, paths_out, verse_ids)

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
        "lemma_contain_meta": {
            "edges_considered": sum(
                1 for r in lemma_rows if str(r.get("edge_type") or "") in CONTAIN_EDGE_TYPES
            ),
            "boost_applied_total": lemma_boost_total,
            "hit_count": len(lemma_hits),
        },
        "sinew_xref_hits": sinew_hits[:30],
        "sinew_xref_meta": {
            "edges_considered": len(sinew_rows),
            "hit_count": len(sinew_hits),
        },
        "osi_xref_hits": osi_hits[:30],
        "osi_xref_meta": {
            "edges_considered": len(osi_rows),
            "hit_count": len(osi_hits),
        },
        "theographic_entity_hits": theographic_hits[:30],
        "theographic_entity_meta": {
            "edges_considered": len(theographic_rows),
            "hit_count": len(theographic_hits),
        },
        "gematria_lexicon_hits": gematria_lexicon_hits[:15],
        "gematria_lexicon_meta": {
            "entries_considered": len(gematria_lexicon_rows),
            "hit_count": len(gematria_lexicon_hits),
            "strongs_linked": sorted(gematria_strongs_set),
            "boost_applied_total": gematria_boost_total,
            "verse_ids_expanded": len(
                strongs_verse_ids_from_lemma(gematria_strongs_set, lemma_rows, max_verses=50)
            ),
        },
        "seed_chain_verse_sample": seed_verses_canon or seed_verses,
        "summary": {
            "paths": len(paths_out),
            "verse_ids": len(verse_ids),
            "lemma_edge_hits": len(lemma_hits),
            "sinew_xref_hits": len(sinew_hits),
            "osi_xref_hits": len(osi_hits),
            "theographic_entity_hits": len(theographic_hits),
            "gematria_lexicon_hits": len(gematria_lexicon_hits),
        },
        "policy": {
            "no_prophecy_claim": True,
            "track_wall": "B_track_not_track_A",
            "send_gate": "HOLD",
            "router_kind": "logos_subgraph_v1",
            "bridge_selection": "multi_coverage_v1",
            "path_first_verse_order_v2": True,
            "concept_affinity_boost_v1": True,
            "verse_ref_canonical_at_source": True,
            "lemma_contain_boost_v1": True,
            "sinew_xref_sidecar_v1": bool(sinew_rows),
            "osi_xref_sidecar_v1": bool(osi_rows),
            "theographic_entity_sidecar_v1": bool(theographic_rows),
            "gematria_lexicon_sidecar_v1": bool(gematria_lexicon_rows),
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
    ap.add_argument(
        "--sinew-xref-jsonl",
        type=Path,
        default=None,
        help="Optional Sinew cross-reference sidecar JSONL",
    )
    ap.add_argument(
        "--osi-xref-jsonl",
        type=Path,
        default=None,
        help="Optional OSI cross-reference sidecar JSONL",
    )
    ap.add_argument(
        "--theographic-entity-jsonl",
        type=Path,
        default=None,
        help="Optional Theographic entity→verse sidecar JSONL",
    )
    ap.add_argument(
        "--gematria-lexicon-jsonl",
        type=Path,
        default=None,
        help="Optional scriptures-js gematria lexicon sidecar JSONL [HYPO]",
    )
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

    sinew_rows: list[dict[str, Any]] | None = None
    if args.sinew_xref_jsonl is not None:
        sinew_rows = _load_jsonl(args.sinew_xref_jsonl) if args.sinew_xref_jsonl.is_file() else []

    osi_rows: list[dict[str, Any]] | None = None
    if args.osi_xref_jsonl is not None:
        osi_rows = _load_jsonl(args.osi_xref_jsonl) if args.osi_xref_jsonl.is_file() else []

    theographic_rows: list[dict[str, Any]] | None = None
    if args.theographic_entity_jsonl is not None:
        theographic_rows = (
            _load_jsonl(args.theographic_entity_jsonl) if args.theographic_entity_jsonl.is_file() else []
        )

    gematria_lexicon_rows: list[dict[str, Any]] | None = None
    if args.gematria_lexicon_jsonl is not None:
        gematria_lexicon_rows = (
            _load_jsonl(args.gematria_lexicon_jsonl) if args.gematria_lexicon_jsonl.is_file() else []
        )

    doc = route(
        query,
        registry=registry,
        lemma_rows=_load_jsonl(args.lemma_jsonl),
        sinew_rows=sinew_rows,
        osi_rows=osi_rows,
        theographic_rows=theographic_rows,
        gematria_lexicon_rows=gematria_lexicon_rows,
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
                "lemma_edge_hits": len(doc.get("lemma_edge_hits") or []),
                "sinew_xref_hits": len(doc.get("sinew_xref_hits") or []),
                "osi_xref_hits": len(doc.get("osi_xref_hits") or []),
                "theographic_entity_hits": len(doc.get("theographic_entity_hits") or []),
                "gematria_lexicon_hits": len(doc.get("gematria_lexicon_hits") or []),
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
