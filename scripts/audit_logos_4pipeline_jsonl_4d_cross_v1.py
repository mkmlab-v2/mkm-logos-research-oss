#!/usr/bin/env python3
"""B-track: cross-audit 4D vectors — verse_decoded jsonl vs verse_4pipeline_full."""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.myeongni.gematria_myeongri_math_v1 import coerce_4d

JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
FULL = ROOT / "data/logos/verse_4pipeline_full_31102.json"
OUT = ROOT / "reports/logos_4pipeline_jsonl_4d_cross_audit_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/logos_topic_4d_resonance_graphrag_2026_v1.json"
FALLBACK_KEY = (0.25, 0.25, 0.25, 0.25)


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def vec_key(v: dict[str, float], places: int) -> tuple[float, ...]:
    return tuple(round(v[k], places) for k in ("S", "L", "K", "M"))


def load_jsonl_index(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            vid = str(row.get("verse_id") or "")
            if vid:
                out[vid] = coerce_4d(row.get("vector_4d") or row.get("unified_4d_vector") or {})
    return out


def load_seeds(path: Path | None) -> list[str]:
    if path is None or not path.is_file():
        return []
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    seeds: list[str] = []
    for row in doc.get("topics") or []:
        seeds.extend(str(s) for s in (row.get("seed_verse_ids") or []) if s)
    return sorted(set(seeds))


def dup_stats(keys: list[tuple[float, ...]]) -> dict:
    counts = Counter(keys)
    dup_keys = [k for k, c in counts.items() if c > 1]
    in_dup = sum(counts[k] for k in dup_keys)
    top = sorted(((counts[k], k) for k in dup_keys), reverse=True)[:5]
    return {
        "rows": len(keys),
        "unique_keys": len(counts),
        "duplicate_keys": len(dup_keys),
        "rows_in_duplicate_clusters": in_dup,
        "duplicate_row_fraction": round(in_dup / len(keys), 6) if keys else 0.0,
        "max_cluster_size": max(counts.values()) if counts else 0,
        "fallback_025_cluster_size": counts.get(FALLBACK_KEY, 0),
        "top_duplicate_clusters": [
            {
                "cluster_size": n,
                "vector_4d": {"S": k[0], "L": k[1], "K": k[2], "M": k[3]},
            }
            for n, k in top
        ],
    }


def pipe_vec(row: dict) -> dict[str, float] | None:
    p4 = row.get("pipeline4_unified_v2") or {}
    raw = p4.get("vector_4d") if isinstance(p4, dict) else None
    return coerce_4d(raw) if isinstance(raw, dict) else None


def audit(*, jsonl: Path, full: Path, places: int, seeds: list[str]) -> dict:
    jidx = load_jsonl_index(jsonl)
    full_rows = json.loads(full.read_text(encoding="utf-8"))
    if not isinstance(full_rows, list):
        raise ValueError("4pipeline input must be top-level array")

    j_keys: list[tuple[float, ...]] = []
    p_keys: list[tuple[float, ...]] = []
    compared = 0
    exact = 0
    max_l2 = 0.0
    missing_in_jsonl = 0
    missing_pipe_vec = 0
    seed_rows = []

    for row in full_rows:
        if not isinstance(row, dict):
            continue
        vid = str(row.get("verse_id") or "")
        pv = pipe_vec(row)
        if pv:
            p_keys.append(vec_key(pv, places))
        else:
            missing_pipe_vec += 1
        if vid not in jidx:
            missing_in_jsonl += 1
            continue
        jv = jidx[vid]
        j_keys.append(vec_key(jv, places))
        if pv is None:
            continue
        compared += 1
        jk = vec_key(jv, places)
        pk = vec_key(pv, places)
        if jk == pk:
            exact += 1
        l2 = math.sqrt(sum((jv[k] - pv[k]) ** 2 for k in jv))
        max_l2 = max(max_l2, l2)
        if vid in seeds:
            seed_rows.append(
                {
                    "verse_id": vid,
                    "jsonl_4d": {k: round(jv[k], 6) for k in jv},
                    "pipeline_4d": {k: round(pv[k], 6) for k in pv},
                    "match_at_round_places": jk == pk,
                    "l2_delta": round(l2, 8),
                }
            )

    return {
        "schema": "logos_4pipeline_jsonl_4d_cross_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "boundary_ack": True,
        "fact_lock": {
            "compression_track_a_touch": False,
            "apply_gematria_4d_bridge_policy": False,
        },
        "inputs": {
            "jsonl": _rel(jsonl),
            "full_pipeline_json": _rel(full),
            "round_places": places,
        },
        "coverage": {
            "full_pipeline_rows": len(full_rows),
            "jsonl_rows": len(jidx),
            "intersection_compared": compared,
            "missing_in_jsonl": missing_in_jsonl,
            "missing_pipeline4_vector": missing_pipe_vec,
        },
        "vector_agreement": {
            "exact_match_at_round_places": exact,
            "exact_match_rate": round(exact / compared, 6) if compared else 0.0,
            "max_l2_delta": round(max_l2, 8),
        },
        "duplicate_stats": {
            "jsonl": dup_stats(j_keys),
            "pipeline4_unified_v2": dup_stats(p_keys),
        },
        "graphrag_seed_cross_check": seed_rows,
        "interpretation_guard": (
            "High duplicate fraction and (0.25^4) fallback clusters indicate encoder/coverage "
            "artefacts — not prophecy hit rate. jsonl is BHS+SBLGNT decode; 4pipeline is MT canon SSOT."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", type=Path, default=JSONL)
    ap.add_argument("--full", type=Path, default=FULL)
    ap.add_argument("--out-json", type=Path, default=OUT)
    ap.add_argument("--topics-json", type=Path, default=FIXTURE if FIXTURE.is_file() else None)
    ap.add_argument("--round-places", type=int, default=4)
    a = ap.parse_args()
    if not a.jsonl.is_file() or not a.full.is_file():
        print(json.dumps({"ok": False, "error": "missing input corpus"}))
        return 2
    doc = audit(jsonl=a.jsonl, full=a.full, places=max(1, a.round_places), seeds=load_seeds(a.topics_json))
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(a.out_json),
                "exact_rate": doc["vector_agreement"]["exact_match_rate"],
                "jsonl_dup_frac": doc["duplicate_stats"]["jsonl"]["duplicate_row_fraction"],
                "pipe_dup_frac": doc["duplicate_stats"]["pipeline4_unified_v2"]["duplicate_row_fraction"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
