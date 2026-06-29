#!/usr/bin/env python3
"""PoC: GraphRAG router verses + typology boost rerank vs topic seeds (CPU, reports-only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_logos_ann_typology_boost_v1 import apply_typology_boost
from scripts.audit_logos_topic_graphrag_seed_retrieval_v1 import collect_router_verses, normalize_topic_verse_ref
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_topic_typology_ann_rerank_poc_v1_latest.json"
ARTIFACT_SCHEMA = "logos_vector_ann_lite_query_result_v1"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    topics_doc = json.loads(args.topics_json.read_text(encoding="utf-8-sig"))
    lexicon = json.loads(args.lexicon_json.read_text(encoding="utf-8-sig"))
    rows = []
    topic_hits = 0
    seed_hits = 0
    seed_total = 0

    for topic in topics_doc.get("topics") or []:
        tid = str(topic.get("topic_id") or "")
        seeds = [canonical_verse_ref(str(s)) for s in (topic.get("seed_verse_ids") or []) if s]
        ref = str(topic.get("graphrag_ref") or "")
        router_path = ROOT / ref if ref else None
        router = json.loads(router_path.read_text(encoding="utf-8-sig")) if router_path and router_path.is_file() else {}
        query = str(router.get("query") or "")
        router_verses = [canonical_verse_ref(v) for v in collect_router_verses(router)]

        base_score = 0.42
        ann_stub = {
            "schema": ARTIFACT_SCHEMA,
            "query_seed": f"st_query:{query}",
            "top_k_requested": args.top_k,
            "top_k": [
                {"verse_id": vid, "score": round(base_score - i * 0.01, 6)}
                for i, vid in enumerate(router_verses[: max(args.top_k, len(router_verses))])
            ],
            "notes": "stub from graphrag router verses; typology boost overlay PoC",
        }
        boosted, meta = apply_typology_boost(ann_stub, query=query, query_id=None, lexicon=lexicon)
        top_ids = [canonical_verse_ref(str(h.get("verse_id") or "")) for h in boosted.get("top_k") or []]
        overlap = sorted(set(seeds) & set(top_ids))
        seed_total += len(seeds)
        seed_hits += len(overlap)
        if overlap:
            topic_hits += 1
        rows.append(
            {
                "topic_id": tid,
                "query": query,
                "seed_verse_ids": seeds,
                "router_verse_count": len(router_verses),
                "typology_themes": meta.get("themes_matched"),
                "injected_verse_ids": meta.get("injected_verse_ids"),
                "top_k_after_boost": top_ids,
                "seed_in_top_k": overlap,
                "topic_pass": bool(overlap),
            }
        )

    doc = {
        "schema": "logos_topic_typology_ann_rerank_poc_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "topics": len(rows),
            "topic_hits": f"{topic_hits}/{len(rows)}",
            "seed_hits": f"{seed_hits}/{seed_total}",
        },
        "interpretation_guard": "ANN-lite stub + typology assist — not semantic ST re-encode; not Track A.",
        "topics": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
