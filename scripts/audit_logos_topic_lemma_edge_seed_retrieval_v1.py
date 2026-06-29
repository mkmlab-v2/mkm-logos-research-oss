#!/usr/bin/env python3
"""B-track: lemma→verse edge index vs 6-topic seeds."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_logos_gold_query_eval_report_v1 import normalize_verse_ref

DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/logos_topic_lemma_edge_seed_retrieval_v1_latest.json"


def edge_verse_id(dst: str) -> str:
    s = str(dst or "").strip()
    if "::" in s:
        s = s.split("::", 1)[1]
    return normalize_verse_ref(s)


def load_verse_edge_index(path: Path) -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    if not path.is_file():
        return idx
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = edge_verse_id(str(row.get("dst_node_id") or ""))
            if not vid or not re.search(r"\.\d+\.\d+", vid):
                continue
            idx.setdefault(vid, []).append(
                {
                    "edge_id": row.get("edge_id"),
                    "src_node_id": row.get("src_node_id"),
                    "edge_type": row.get("edge_type"),
                    "path_id": row.get("path_id"),
                }
            )
    return idx


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    idx = load_verse_edge_index(args.edges_jsonl)
    topics_doc = json.loads(args.topics_json.read_text(encoding="utf-8-sig"))
    rows = []
    topic_hits = 0
    seed_hits = 0
    seed_total = 0

    for topic in topics_doc.get("topics") or []:
        tid = str(topic.get("topic_id") or "")
        seeds = [normalize_verse_ref(str(s)) for s in (topic.get("seed_verse_ids") or []) if s]
        seed_edges = []
        for sid in seeds:
            edges = idx.get(sid) or []
            if edges:
                seed_hits += 1
                seed_edges.append({"verse_id": sid, "edge_count": len(edges), "sample": edges[:3]})
        seed_total += len(seeds)
        if seed_edges:
            topic_hits += 1
        rows.append(
            {
                "topic_id": tid,
                "seed_verse_ids": seeds,
                "seeds_with_lemma_edges": seed_edges,
                "seed_hit_count": len(seed_edges),
                "topic_pass": len(seed_edges) > 0,
            }
        )

    doc = {
        "schema": "logos_topic_lemma_edge_seed_retrieval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "summary": {
            "topics": len(rows),
            "topic_hits": f"{topic_hits}/{len(rows)}",
            "seed_hits": f"{seed_hits}/{seed_total}",
            "indexed_verse_ids": len(idx),
        },
        "interpretation_guard": "Lemma proxy edges — morphology not verified; assist only.",
        "topics": rows,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
