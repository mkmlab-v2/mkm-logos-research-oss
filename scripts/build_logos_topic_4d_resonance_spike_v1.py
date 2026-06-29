#!/usr/bin/env python3
"""B-track topic 4D centroid vs verse cosine — no Track A / compression."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from heapq import heappush, heapreplace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d, cosine_similarity, renorm_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
OUT = ROOT / "reports/logos_topic_4d_resonance_spike_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
DEFAULT_TOPICS = {
    "ai_hubris_trade": ["Rev.18.2", "Jer.1.10", "Dan.5.25"],
    "risk_off_overnight": ["Ps.23.3", "Jer.31.33", "Luke.22.4"],
    "election_regime_watch": ["Neh.4.9", "1Chr.12.32", "Rev.18.2"],
}


def load_topics(path: Path | None) -> tuple[dict[str, list[str]], dict[str, str]]:
    refs: dict[str, str] = {}
    if path is None or not path.is_file():
        return DEFAULT_TOPICS, refs
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    topics: dict[str, list[str]] = {}
    for row in doc.get("topics") or []:
        tid = str(row.get("topic_id") or "")
        seeds = [str(s) for s in (row.get("seed_verse_ids") or []) if s]
        if tid and seeds:
            topics[tid] = seeds
            ref = row.get("graphrag_ref")
            if isinstance(ref, str) and ref.strip():
                refs[tid] = ref.strip()
    return (topics or DEFAULT_TOPICS), refs


def vec(row: dict) -> dict[str, float]:
    return coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})


def centroid(vs: list[dict[str, float]]) -> dict[str, float]:
    acc = {k: 0.0 for k in ("S", "L", "K", "M")}
    for v in vs:
        for k in acc:
            acc[k] += v[k]
    return renorm_4d(acc)


def seeds_for(jsonl: Path, topics: dict[str, list[str]]) -> dict[str, dict[str, float]]:
    want = {s for ss in topics.values() for s in ss}
    got: dict[str, dict[str, float]] = {}
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            if len(got) >= len(want):
                break
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid in want and vid not in got:
                got[vid] = vec(row)
    return got


def top_k(
    jsonl: Path,
    cent: dict[str, float],
    k: int,
    cap: int,
    *,
    dedupe: bool,
    places: int,
) -> list[dict]:
    heap: list[tuple[float, str, dict[str, float]]] = []
    seen: set[tuple[float, ...]] = set()
    n = 0
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            if cap and n >= cap:
                break
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if not vid:
                continue
            v = vec(row)
            if dedupe:
                vk = tuple(round(v[a], places) for a in ("S", "L", "K", "M"))
                if vk in seen:
                    continue
                seen.add(vk)
            sim = cosine_similarity(cent, v)
            n += 1
            item = (sim, vid, v)
            if len(heap) < k:
                heappush(heap, item)
            elif sim > heap[0][0]:
                heapreplace(heap, item)
    return [
        {"verse_id": vid, "cosine": round(sim, 6), "vector_4d": {a: round(v[a], 4) for a in v}}
        for sim, vid, v in sorted(heap, key=lambda x: -x[0])
    ]


def seed_hits(
    seed_idx: dict[str, dict[str, float]],
    seeds: list[str],
    cent: dict[str, float],
) -> list[dict]:
    out = []
    for sid in seeds:
        if sid not in seed_idx:
            continue
        v = seed_idx[sid]
        out.append(
            {
                "verse_id": sid,
                "cosine": round(cosine_similarity(cent, v), 6),
                "vector_4d": {a: round(v[a], 4) for a in v},
                "role": "seed",
            }
        )
    return sorted(out, key=lambda x: -x["cosine"])


def build_doc(
    *,
    jsonl: Path,
    topics: dict[str, list[str]],
    refs: dict[str, str],
    top_k_n: int,
    max_verses: int,
    topics_json: Path | None,
    dedupe_vectors: bool,
    dedupe_places: int,
    ensure_seeds_in_top_k: bool,
) -> dict:
    seed_idx = seeds_for(jsonl, topics)
    rows = []
    for tid, seeds in topics.items():
        ok = [seed_idx[s] for s in seeds if s in seed_idx]
        cent = centroid(ok) if ok else renorm_4d({})
        hits = top_k(
            jsonl,
            cent,
            max(1, top_k_n),
            max(0, max_verses),
            dedupe=dedupe_vectors,
            places=dedupe_places,
        )
        if ensure_seeds_in_top_k:
            seed_rows = seed_hits(seed_idx, seeds, cent)
            seed_ids = {s["verse_id"] for s in seed_rows}
            rest = [h for h in hits if h["verse_id"] not in seed_ids]
            hits = (seed_rows + rest)[: max(1, top_k_n)]
        row = {
            "topic_id": tid,
            "seed_verse_ids": seeds,
            "missing_seed_verse_ids": [s for s in seeds if s not in seed_idx],
            "centroid_4d": {k: round(cent[k], 6) for k in cent},
            "top_k": hits,
            "seed_in_top_k": [h["verse_id"] for h in hits if h["verse_id"] in seeds],
        }
        if tid in refs:
            row["graphrag_ref"] = refs[tid]
        rows.append(row)
    return {
        "schema": "logos_topic_4d_resonance_spike_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {
            "compression_track_a_touch": False,
            "apply_gematria_4d_bridge_policy": False,
            "topics_json": str(topics_json.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
            if topics_json
            else None,
            "dedupe_vectors": dedupe_vectors,
            "dedupe_round_places": dedupe_places,
            "ensure_seeds_in_top_k": ensure_seeds_in_top_k,
        },
        "interpretation_guard": "High cosine may reflect duplicate 4D vectors in corpus — not prophecy hit rate.",
        "topics": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--topics-json", type=Path, default=None, help="default: GraphRAG 2026 fixture if present")
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--max-verses", type=int, default=0)
    ap.add_argument("--dedupe-vectors", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--dedupe-places", type=int, default=4)
    ap.add_argument("--ensure-seeds-in-top-k", action="store_true")
    a = ap.parse_args()
    topics_path = a.topics_json
    if topics_path is None and FIXTURE.is_file():
        topics_path = FIXTURE
    topics, refs = load_topics(topics_path)
    doc = build_doc(
        jsonl=a.jsonl,
        topics=topics,
        refs=refs,
        top_k_n=a.top_k,
        max_verses=a.max_verses,
        topics_json=topics_path,
        dedupe_vectors=a.dedupe_vectors,
        dedupe_places=a.dedupe_places,
        ensure_seeds_in_top_k=a.ensure_seeds_in_top_k,
    )
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(a.out_json), "topics": len(doc["topics"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
