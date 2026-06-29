#!/usr/bin/env python3
"""B-track: audit duplicate 4D vectors in verse_decoded jsonl — no Track A touch."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
OUT = ROOT / "reports/logos_verse_4d_dedupe_audit_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"


def vec_key(v: dict[str, float], places: int = 4) -> tuple[float, ...]:
    return tuple(round(v[k], places) for k in ("S", "L", "K", "M"))


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def load_seed_ids(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    out: list[str] = []
    for row in doc.get("topics") or []:
        out.extend(str(s) for s in (row.get("seed_verse_ids") or []) if s)
    return sorted(set(out))


def audit(jsonl: Path, *, places: int, seeds: list[str], sample_per_cluster: int) -> dict:
    counts: Counter[tuple[float, ...]] = Counter()
    sample: dict[tuple[float, ...], list[str]] = defaultdict(list)
    seed_rows: dict[str, dict] = {}
    total = 0
    with jsonl.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if not vid:
                continue
            v = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
            k = vec_key(v, places)
            total += 1
            counts[k] += 1
            if len(sample[k]) < sample_per_cluster:
                sample[k].append(vid)
            if vid in seeds and vid not in seed_rows:
                seed_rows[vid] = {"vector_4d": {a: round(v[a], 4) for a in v}, "dup_cluster_size": counts[k]}

    dup_keys = [k for k, c in counts.items() if c > 1]
    verses_in_dup = sum(counts[k] for k in dup_keys)
    top_clusters = sorted(((counts[k], list(k), sample[k]) for k in dup_keys), reverse=True)[:10]

    seed_audit = []
    for sid in seeds:
        if sid not in seed_rows:
            seed_audit.append({"verse_id": sid, "present": False})
            continue
        sr = seed_rows[sid]
        seed_audit.append({"verse_id": sid, "present": True, **sr})

    return {
        "schema": "logos_verse_4d_dedupe_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {"compression_track_a_touch": False, "apply_gematria_4d_bridge_policy": False},
        "jsonl": _rel(jsonl),
        "round_places": places,
        "totals": {
            "verse_rows": total,
            "unique_vector_keys": len(counts),
            "duplicate_keys": len(dup_keys),
            "verses_in_duplicate_clusters": verses_in_dup,
            "duplicate_verse_fraction": round(verses_in_dup / total, 6) if total else 0.0,
            "max_cluster_size": max(counts.values()) if counts else 0,
        },
        "top_duplicate_clusters": [
            {"cluster_size": n, "vector_4d": {"S": k[0], "L": k[1], "K": k[2], "M": k[3]}, "sample_verse_ids": ids}
            for n, k, ids in top_clusters
        ],
        "graphrag_seed_audit": seed_audit,
        "interpretation_guard": "Duplicate keys are rounded-4D collisions — not prophecy accuracy.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--topics-json", type=Path, default=FIXTURE if FIXTURE.is_file() else None)
    ap.add_argument("--round-places", type=int, default=4)
    ap.add_argument("--sample-per-cluster", type=int, default=5)
    a = ap.parse_args()
    seeds = load_seed_ids(a.topics_json)
    doc = audit(a.jsonl, places=max(1, a.round_places), seeds=seeds, sample_per_cluster=max(1, a.sample_per_cluster))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(a.out_json), **doc["totals"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
