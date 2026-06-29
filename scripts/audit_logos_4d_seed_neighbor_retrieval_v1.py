#!/usr/bin/env python3
"""B-track: seed cosine rank vs topic centroid — retrieval diagnostic (not promotion gate)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d, cosine_similarity, renorm_4d

DEFAULT_JSONL = ROOT / "reports/logos_verse_4d_bridge_v2_overlay_v1_latest.jsonl"
DEFAULT_TOPICS = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_4d_seed_neighbor_retrieval_v1_latest.json"


def load_topics(path: Path) -> dict[str, list[str]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    out: dict[str, list[str]] = {}
    for row in doc.get("topics") or []:
        tid = str(row.get("topic_id") or "")
        seeds = [str(s) for s in (row.get("seed_verse_ids") or []) if s]
        if tid and seeds:
            out[tid] = seeds
    return out


def load_vectors(jsonl: Path) -> dict[str, dict[str, float]]:
    idx: dict[str, dict[str, float]] = {}
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid and vid not in idx:
                idx[vid] = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
    return idx


def centroid(vs: list[dict[str, float]]) -> dict[str, float]:
    acc = {k: 0.0 for k in ("S", "L", "K", "M")}
    for v in vs:
        for k in acc:
            acc[k] += v[k]
    return renorm_4d(acc)


def rank_seeds(
    *,
    all_vectors: dict[str, dict[str, float]],
    seeds: list[str],
    cent: dict[str, float],
    top_k: int,
) -> list[dict]:
    sims = [(cosine_similarity(cent, v), vid) for vid, v in all_vectors.items()]
    sims.sort(key=lambda x: -x[0])
    rank_by_vid = {vid: i + 1 for i, (_, vid) in enumerate(sims)}
    cutoff_sim = sims[min(top_k, len(sims)) - 1][0] if sims else 0.0
    rows = []
    for sid in seeds:
        if sid not in all_vectors:
            rows.append({"verse_id": sid, "present": False})
            continue
        sc = cosine_similarity(cent, all_vectors[sid])
        rk = rank_by_vid[sid]
        rows.append(
            {
                "verse_id": sid,
                "present": True,
                "cosine_to_centroid": round(sc, 6),
                "rank_among_corpus": rk,
                "corpus_size": len(sims),
                "percentile": round(100.0 * (1.0 - (rk - 1) / max(1, len(sims) - 1)), 4),
                "top_k_cutoff_cosine": round(cutoff_sim, 6),
                "gap_to_top_k": round(cutoff_sim - sc, 6),
                "would_hit_top_k": sc >= cutoff_sim,
            }
        )
    return rows


def build_doc(*, jsonl: Path, topics_path: Path, top_k: int) -> dict:
    topics = load_topics(topics_path)
    vectors = load_vectors(jsonl)
    topic_rows = []
    seeds_in_top_k = 0
    seed_total = 0
    for tid, seeds in topics.items():
        ok = [vectors[s] for s in seeds if s in vectors]
        cent = centroid(ok) if ok else renorm_4d({})
        seed_rows = rank_seeds(all_vectors=vectors, seeds=seeds, cent=cent, top_k=top_k)
        hits = sum(1 for r in seed_rows if r.get("would_hit_top_k"))
        seeds_in_top_k += hits
        seed_total += len(seeds)
        topic_rows.append(
            {
                "topic_id": tid,
                "seed_verse_ids": seeds,
                "centroid_4d": {k: round(cent[k], 6) for k in cent},
                "seed_neighbor_audit": seed_rows,
                "seed_hits_top_k": hits,
            }
        )
    return {
        "schema": "logos_4d_seed_neighbor_retrieval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {"compression_track_a_touch": False},
        "jsonl": str(jsonl.relative_to(ROOT)).replace("\\", "/"),
        "topics_json": str(topics_path.relative_to(ROOT)).replace("\\", "/"),
        "top_k": top_k,
        "summary": {
            "topics": len(topic_rows),
            "seed_hits_top_k": f"{seeds_in_top_k}/{seed_total}",
            "organic_topic_spike_equivalent": f"{sum(1 for t in topic_rows if t['seed_hits_top_k'] > 0)}/{len(topic_rows)}",
        },
        "interpretation_guard": "Rank gap shows centroid-ANN retrieval limit — not gold router quality.",
        "topics": topic_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--topics-json", type=Path, default=DEFAULT_TOPICS)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 2
    doc = build_doc(jsonl=args.jsonl, topics_path=args.topics_json, top_k=max(1, args.top_k))
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), **doc["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
