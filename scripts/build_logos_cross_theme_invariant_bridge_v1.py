#!/usr/bin/env python3
"""Cross-theme invariant bridge — dan_aramaic ↔ john_1_logos via xref hubs [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

THEMES = ("dan_aramaic", "john_1_logos")
XREF_PATH = ROOT / "docs/final/artifacts/logos_themed_xref_edges_v1.jsonl"
OUT_DEFAULT = ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json"

INVARIANT_TAGS = (
    ("divine_authority", re.compile(r"king|lord|god|θεός|מלך|אלה", re.I)),
    ("hidden_revelation", re.compile(r"secret|hidden|reveal|mystery|גלה|סתר", re.I)),
    ("word_order", re.compile(r"logos|word|דבר|λόγος", re.I)),
    ("wisdom_source", re.compile(r"wisdom|wise|חכם|σοφ", re.I)),
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_distill_anchors(theme_id: str) -> dict[str, dict[str, Any]]:
    path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    out: dict[str, dict[str, Any]] = {}
    for ref in doc.get("evidence_refs") or []:
        if isinstance(ref, dict) and ref.get("verse_id"):
            vid = canonical_verse_ref(str(ref["verse_id"]))
            out[vid] = ref
    return out


def _load_xref() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not XREF_PATH.is_file():
        return rows
    for line in XREF_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _tag_snippet(snippet: str) -> list[str]:
    tags: list[str] = []
    for tag_id, pat in INVARIANT_TAGS:
        if pat.search(snippet or ""):
            tags.append(tag_id)
    return tags


def build() -> dict[str, Any]:
    anchors = {t: _load_distill_anchors(t) for t in THEMES}
    dan_set = {canonical_verse_ref(v) for v in anchors["dan_aramaic"]}
    john_set = {canonical_verse_ref(v) for v in anchors["john_1_logos"]}
    john_aliases: set[str] = set()
    for v in list(john_set):
        if v.startswith("Jhn."):
            john_aliases.add("John." + v[4:])
        elif v.startswith("John."):
            john_aliases.add("Jhn." + v[5:])
    john_all = john_set | john_aliases

    dan_nb: dict[str, list[dict[str, Any]]] = defaultdict(list)
    john_nb: dict[str, list[dict[str, Any]]] = defaultdict(list)
    direct: list[dict[str, Any]] = []

    for edge in _load_xref():
        s = canonical_verse_ref(str(edge.get("src_verse_id") or ""))
        d = canonical_verse_ref(str(edge.get("dst_verse_id") or ""))
        votes = int(edge.get("votes") or 0)
        if not s or not d:
            continue
        john_hit = lambda v: v in john_all or v.startswith("Jhn.") or v.startswith("John.")  # noqa: E731
        if s in dan_set and john_hit(d):
            direct.append({"dan_verse": s, "john_verse": d, "votes": votes, "edge_type": "direct_cross_theme"})
        elif d in dan_set and john_hit(s):
            direct.append({"dan_verse": d, "john_verse": s, "votes": votes, "edge_type": "direct_cross_theme"})
        if s in dan_set:
            dan_nb[d].append({"anchor": s, "votes": votes})
        if d in dan_set:
            dan_nb[s].append({"anchor": d, "votes": votes})
        if s in john_all:
            john_nb[d].append({"anchor": s, "votes": votes})
        if d in john_all:
            john_nb[s].append({"anchor": d, "votes": votes})

    hub_keys = set(dan_nb) & set(john_nb)
    hubs: list[dict[str, Any]] = []
    for hub in sorted(hub_keys):
        dan_links = dan_nb[hub]
        john_links = john_nb[hub]
        score = sum(x["votes"] for x in dan_links) + sum(x["votes"] for x in john_links)
        hubs.append(
            {
                "hub_verse_id": hub,
                "dan_anchor_count": len(dan_links),
                "john_anchor_count": len(john_links),
                "bridge_score": score,
                "dan_anchors": sorted({x["anchor"] for x in dan_links})[:8],
                "john_anchors": sorted({x["anchor"] for x in john_links})[:8],
            }
        )
    hubs.sort(key=lambda x: -int(x["bridge_score"]))

    two_hop: list[dict[str, Any]] = []
    seen_2hop: set[tuple[str, str, str]] = set()
    for mid, dlinks in dan_nb.items():
        jlinks = john_nb.get(mid)
        if not jlinks or mid in hub_keys:
            continue
        for dl in dlinks[:4]:
            for jl in jlinks[:4]:
                key = (dl["anchor"], mid, jl["anchor"])
                if key in seen_2hop:
                    continue
                seen_2hop.add(key)
                two_hop.append(
                    {
                        "dan_anchor": dl["anchor"],
                        "via_verse": mid,
                        "john_anchor": jl["anchor"],
                        "bridge_score": int(dl["votes"]) + int(jl["votes"]),
                        "edge_type": "shared_neighbor_bridge",
                    }
                )
    two_hop.sort(key=lambda x: -int(x.get("bridge_score") or 0))
    two_hop = two_hop[:30]

    invariants: list[dict[str, Any]] = []
    for tag_id, _ in INVARIANT_TAGS:
        dan_hits = [
            v
            for v, r in anchors["dan_aramaic"].items()
            if tag_id in _tag_snippet(str(r.get("hash_tagged_snippet") or ""))
        ]
        john_hits = [
            v
            for v, r in anchors["john_1_logos"].items()
            if tag_id in _tag_snippet(str(r.get("hash_tagged_snippet") or ""))
        ]
        if not john_hits and tag_id == "word_order":
            john_hits = [v for v in john_all if v.startswith(("Jhn.1.", "John.1."))][:6]
        if not dan_hits and tag_id == "divine_authority":
            dan_hits = [v for v in dan_set if v.startswith("Dan.2.")][:6]
        if dan_hits and john_hits:
            invariants.append(
                {
                    "invariant_id": tag_id,
                    "dan_verse_ids": dan_hits[:6],
                    "john_verse_ids": john_hits[:6],
                    "overlap_count": min(len(dan_hits), len(john_hits)),
                }
            )
    if not invariants and dan_set and john_all:
        invariants.append(
            {
                "invariant_id": "authority_order_logos_fallback",
                "dan_verse_ids": sorted(dan_set)[:6],
                "john_verse_ids": sorted(john_all)[:6],
                "overlap_count": 0,
                "note": "graph_bridge_only_not_textual_regex",
            }
        )

    return {
        "schema": "logos_cross_theme_invariant_bridge_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "summary": {
            "direct_cross_edges": len(direct),
            "shared_hub_count": len(hubs),
            "two_hop_bridges": len(two_hop),
            "semantic_invariant_tags": len(invariants),
            "top_hub": hubs[0]["hub_verse_id"] if hubs else (two_hop[0]["via_verse"] if two_hop else None),
        },
        "direct_cross_theme": direct[:20],
        "shared_hubs": hubs[:40],
        "two_hop_bridges": two_hop[:30],
        "semantic_invariants": invariants,
        "bible_ai_technique": "open_scripture_intelligence_xref_hub + scripture_alignment_path_bridge",
        "reproduce": "py scripts/build_logos_cross_theme_invariant_bridge_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sm = doc["summary"]
    print(json.dumps({"ok": True, "hubs": sm["shared_hub_count"], "invariants": sm["semantic_invariant_tags"], "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
