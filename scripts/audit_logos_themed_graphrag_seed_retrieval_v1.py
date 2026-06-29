#!/usr/bin/env python3
"""B-track: themed distill anchors vs GraphRAG router (organic vs xref-enriched)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_logos_topic_graphrag_seed_retrieval_v1 import collect_router_verses, normalize_topic_verse_ref
from scripts.build_logos_themed_retrieval_eval_v1 import _anchor_ids

ART = ROOT / "docs/final/artifacts"
DEFAULT_OUT = ROOT / "reports/logos_themed_graphrag_seed_retrieval_v1_latest.json"
THEMES = ("dan_aramaic", "john_1_logos")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _alias_set(vid: str) -> set[str]:
    out = {vid, normalize_topic_verse_ref(vid)}
    if vid.startswith("Jhn."):
        out.add("John." + vid[4:])
    elif vid.startswith("John."):
        out.add("Jhn." + vid[5:])
    return {x for x in out if x}


def _overlap(seeds: set[str], router_ids: set[str]) -> list[str]:
    hits: list[str] = []
    for sid in sorted(seeds):
        if sid in router_ids or _alias_set(sid) & router_ids:
            hits.append(sid)
    return hits


def _router_slices(router: dict[str, Any]) -> tuple[set[str], set[str]]:
    verse_ids = [normalize_topic_verse_ref(str(v)) for v in (router.get("verse_ids") or []) if v]
    verse_ids = [v for v in verse_ids if v]
    enrich = router.get("xref_enrichment") or {}
    router_n = int(enrich.get("router_verse_count") or 0)
    if router_n > 0 and router_n <= len(verse_ids):
        organic = set(verse_ids[:router_n])
        full = set(verse_ids)
    else:
        organic = set(collect_router_verses(router))
        full = organic | set(verse_ids)
    return organic, full


def audit_theme(theme_id: str) -> dict[str, Any]:
    router_path = ART / f"logos_subgraph_graphrag_router_{theme_id}_latest.json"
    router = json.loads(router_path.read_text(encoding="utf-8-sig")) if router_path.is_file() else {}
    seeds = _anchor_ids(theme_id)
    organic, full = _router_slices(router)
    overlap_organic = _overlap(seeds, organic)
    overlap_full = _overlap(seeds, full)
    xref_only = sorted(set(overlap_full) - set(overlap_organic))
    enrich = router.get("xref_enrichment") or {}
    return {
        "theme_id": theme_id,
        "graphrag_ref": str(router_path.relative_to(ROOT)).replace("\\", "/"),
        "anchor_seed_count": len(seeds),
        "router_organic_count": len(organic),
        "router_full_count": len(full),
        "seed_router_overlap_organic": overlap_organic,
        "seed_router_overlap_full": overlap_full,
        "seed_hit_organic": f"{len(overlap_organic)}/{len(seeds)}",
        "seed_hit_full": f"{len(overlap_full)}/{len(seeds)}",
        "xref_neighbor_count": enrich.get("neighbor_count", 0),
        "xref_boost_seed_hits": xref_only,
        "topic_pass_organic": len(overlap_organic) > 0,
        "router_query": router.get("query"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = [audit_theme(tid) for tid in THEMES]
    seed_total = sum(r["anchor_seed_count"] for r in rows)
    organic_hits = sum(len(r["seed_router_overlap_organic"]) for r in rows)
    full_hits = sum(len(r["seed_router_overlap_full"]) for r in rows)

    doc = {
        "schema": "logos_themed_graphrag_seed_retrieval_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "notes": "distill anchors as seeds — organic=router-only; full=after xref enrichment",
        "summary": {
            "themes": len(rows),
            "seed_hits_organic": f"{organic_hits}/{seed_total}",
            "seed_hits_full": f"{full_hits}/{seed_total}",
            "topics_pass_organic": sum(1 for r in rows if r["topic_pass_organic"]),
        },
        "themes": rows,
        "reproduce": "py scripts/audit_logos_themed_graphrag_seed_retrieval_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
