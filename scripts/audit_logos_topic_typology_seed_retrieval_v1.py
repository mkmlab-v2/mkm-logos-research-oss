#!/usr/bin/env python3
"""B-track: typology lexicon boost coverage vs 6-topic seeds (CPU overlay diagnostic)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.apply_logos_ann_typology_boost_v1 import match_lexicon_entries
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_topic_typology_seed_retrieval_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
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
        query = ""
        if router_path and router_path.is_file():
            query = str(json.loads(router_path.read_text(encoding="utf-8-sig")).get("query") or "")

        entries = match_lexicon_entries(query=query, query_id=None, lexicon=lexicon)
        boost_ids: list[str] = []
        themes: list[str] = []
        for entry in entries:
            themes.append(str(entry.get("theme_id") or ""))
            for raw in entry.get("boost_verse_ids") or []:
                n = canonical_verse_ref(str(raw))
                if n:
                    boost_ids.append(n)
        boost_set = set(boost_ids)
        seed_set = set(seeds)
        overlap = sorted(seed_set & boost_set)
        seed_total += len(seeds)
        seed_hits += len(overlap)
        if overlap:
            topic_hits += 1
        rows.append(
            {
                "topic_id": tid,
                "query": query,
                "matched_themes": themes,
                "boost_verse_count": len(boost_set),
                "seed_verse_ids": seeds,
                "typology_seed_overlap": overlap,
                "seed_hit_count": len(overlap),
                "topic_pass": len(overlap) > 0,
            }
        )

    doc = {
        "schema": "logos_topic_typology_seed_retrieval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "topics": len(rows),
            "topic_hits": f"{topic_hits}/{len(rows)}",
            "seed_hits": f"{seed_hits}/{seed_total}",
        },
        "interpretation_guard": "Typology boost assist — router-primary; not organic 4D spike.",
        "topics": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
