#!/usr/bin/env python3
"""B-track: GraphRAG router vs 6-topic fixture seeds — retrieval diagnostic."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json"


def normalize_topic_verse_ref(raw: str) -> str:
    return canonical_verse_ref(raw)


def collect_router_verses(router: dict) -> list[str]:
    out: list[str] = []
    for vid in router.get("verse_ids") or []:
        n = normalize_topic_verse_ref(str(vid))
        if n and re.search(r"\.\d+\.\d+", n):
            out.append(n)
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        for step in path.get("steps") or []:
            n = normalize_topic_verse_ref(str(step))
            if n and re.search(r"\.\d+\.\d+", n):
                out.append(n)
    seen: set[str] = set()
    deduped: list[str] = []
    for v in out:
        if v not in seen:
            seen.add(v)
            deduped.append(v)
    return deduped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--graphrag-ref-overrides",
        type=Path,
        default=None,
        help="JSON map topic_id -> graphrag_ref path (reports-only shadow audit).",
    )
    args = ap.parse_args()

    topics_doc = json.loads(args.topics_json.read_text(encoding="utf-8-sig"))
    ref_overrides: dict[str, str] = {}
    if args.graphrag_ref_overrides and args.graphrag_ref_overrides.is_file():
        raw = json.loads(args.graphrag_ref_overrides.read_text(encoding="utf-8-sig"))
        ref_overrides = {str(k): str(v) for k, v in (raw or {}).items()}
    rows = []
    topic_hits = 0
    seed_hits = 0
    seed_total = 0

    for topic in topics_doc.get("topics") or []:
        tid = str(topic.get("topic_id") or "")
        seeds = [str(s) for s in (topic.get("seed_verse_ids") or []) if s]
        ref = ref_overrides.get(tid) or str(topic.get("graphrag_ref") or "")
        router_path = ROOT / ref if ref else None
        router = json.loads(router_path.read_text(encoding="utf-8-sig")) if router_path and router_path.is_file() else {}
        router_verses = collect_router_verses(router)
        router_set = set(router_verses)
        seed_set = set(seeds)
        overlap = sorted(seed_set & router_set)
        seed_total += len(seeds)
        seed_hits += len(overlap)
        if overlap:
            topic_hits += 1
        rows.append(
            {
                "topic_id": tid,
                "graphrag_ref": ref,
                "seed_verse_ids": seeds,
                "router_verse_count": len(router_verses),
                "seed_router_overlap": overlap,
                "seed_hit_count": len(overlap),
                "topic_pass": len(overlap) > 0,
                "router_query": router.get("query"),
            }
        )

    doc = {
        "schema": "logos_topic_graphrag_seed_retrieval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "topics": len(rows),
            "topic_hits": f"{topic_hits}/{len(rows)}",
            "seed_hits": f"{seed_hits}/{seed_total}",
        },
        "interpretation_guard": "GraphRAG router path — not 4D centroid ANN; not Track A promotion.",
        "topics": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
