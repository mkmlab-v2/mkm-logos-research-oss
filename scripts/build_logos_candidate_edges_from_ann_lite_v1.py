#!/usr/bin/env python3
"""Batch kNN candidate edges from logos_vector_index_ann_lite SQLite ([HYPO] B-track).

Uses sentence_transformers_v1 vectors already in index — separate staging file from 4D kNN.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"
DEFAULT_SQLITE = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_ann_lite_v1.jsonl"
DEFAULT_SUMMARY = ROOT / "docs/final/artifacts/logos_candidate_edges_ann_lite_v1_latest.json"

SCHEMA = "bible_meaning_graph_edge_candidate_v1"
GENERATOR = "build_logos_candidate_edges_from_ann_lite_v1.py@1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _node_id(verse_id: str) -> str:
    vid = str(verse_id).strip()
    return vid if vid.startswith("aramaic::") else f"aramaic::{vid}"


def _load_canonical_pairs(path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if not path.is_file():
        return pairs
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        a = str(row.get("src_node_id") or "")
        b = str(row.get("dst_node_id") or "")
        if a and b:
            pairs.add(tuple(sorted((a, b))))
    return pairs


def _load_sqlite_vectors(sqlite_path: Path) -> tuple[list[str], list[list[float]], str, int]:
    con = sqlite3.connect(str(sqlite_path))
    try:
        cur = con.execute("SELECT verse_id, dim, embedding_mode, vec_blob FROM logos_vec_stub")
        rows = cur.fetchall()
    finally:
        con.close()

    if not rows:
        raise RuntimeError("empty logos_vec_stub table")

    dims = {r[1] for r in rows}
    modes = {r[2] for r in rows}
    if len(dims) != 1 or len(modes) != 1:
        raise RuntimeError("mixed dim/mode in sqlite index")

    dim = next(iter(dims))
    mode = next(iter(modes))
    ids: list[str] = []
    vectors: list[list[float]] = []
    for verse_id, d, _mode, blob in rows:
        vals = struct.unpack(f"<{d}f", blob)
        ids.append(_node_id(str(verse_id)))
        vectors.append(list(vals))
    return ids, vectors, mode, dim


def _mk_edge(src: str, dst: str, sim: float, mode: str) -> dict[str, Any]:
    w = max(0.0, min(1.0, float(sim)))
    return {
        "schema": SCHEMA,
        "src_node_id": src,
        "dst_node_id": dst,
        "edge_type": "semantic_ann_lite_knn",
        "edge_status": "candidate",
        "weight": round(w, 6),
        "similarity_ann_lite_cosine": round(float(sim), 6),
        "as_of_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "hypothesis_tier": "B",
        "relation_basis": ["ann_lite_cosine"],
        "embedding_mode": mode,
        "source": "build_logos_candidate_edges_from_ann_lite_v1",
        "evidence": f"ann_lite_cosine: score={sim:.4f} mode={mode} [HYPO]",
    }


def build_ann_lite_candidates(
    *,
    node_ids: list[str],
    vectors: list[list[float]],
    embedding_mode: str,
    max_query_verses: int,
    top_k: int,
    min_cosine: float,
    max_candidates: int,
    skip_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    import numpy as np

    n = len(node_ids)
    qn = n if max_query_verses <= 0 else min(n, max_query_verses)
    x = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    x = x / np.maximum(norms, 1e-9)

    sim = x[:qn] @ x.T
    for i in range(qn):
        sim[i, i] = -2.0

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    k = min(top_k, max(0, n - 1))

    for i in range(qn):
        row = sim[i]
        if k >= n - 1:
            idx = np.argsort(-row)
        else:
            idx = np.argpartition(-row, kth=k - 1)[:k]
            idx = idx[np.argsort(-row[idx])]
        for j in idx:
            score = float(row[j])
            if score < min_cosine:
                continue
            src = node_ids[i]
            dst = node_ids[int(j)]
            key = tuple(sorted((src, dst)))
            if key in seen or key in skip_pairs:
                continue
            seen.add(key)
            edges.append(_mk_edge(src, dst, score, embedding_mode))
            if len(edges) >= max_candidates:
                return edges
    return edges


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ann-report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--canonical-edges-jsonl", type=Path, default=DEFAULT_CANONICAL)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--max-query-verses", type=int, default=500, help="Verses to query (default 500 pilot)")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--min-cosine", type=float, default=0.55)
    ap.add_argument("--max-candidates", type=int, default=2000)
    ap.add_argument("--skip-canonical-pairs", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sqlite_path = args.sqlite if args.sqlite.is_absolute() else ROOT / args.sqlite
    if not sqlite_path.is_file() and args.ann_report_json.is_file():
        rep = json.loads((ROOT / args.ann_report_json).read_text(encoding="utf-8-sig"))
        rel = ((rep.get("sqlite") or {}).get("path") or "").strip()
        if rel:
            sqlite_path = (ROOT / rel).resolve()

    if not sqlite_path.is_file():
        print(f"Missing sqlite index: {sqlite_path}", file=sys.stderr)
        return 2

    try:
        node_ids, vectors, mode, dim = _load_sqlite_vectors(sqlite_path)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3

    canonical = args.canonical_edges_jsonl if args.canonical_edges_jsonl.is_absolute() else ROOT / args.canonical_edges_jsonl
    skip_pairs = _load_canonical_pairs(canonical) if args.skip_canonical_pairs else set()

    try:
        edges = build_ann_lite_candidates(
            node_ids=node_ids,
            vectors=vectors,
            embedding_mode=mode,
            max_query_verses=int(args.max_query_verses),
            top_k=int(args.top_k),
            min_cosine=float(args.min_cosine),
            max_candidates=int(args.max_candidates),
            skip_pairs=skip_pairs,
        )
    except ImportError:
        print("numpy required for ann_lite batch kNN", file=sys.stderr)
        return 4

    sims = [float(e.get("similarity_ann_lite_cosine", 0.0)) for e in edges]
    summary = {
        "schema": "logos_candidate_edges_ann_lite_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "hypothesis_tier": "B",
        "research_only": True,
        "promotion_required": True,
        "mode": "ann_lite_cosine",
        "embedding_mode": mode,
        "vector_dim": dim,
        "index_rows": len(node_ids),
        "stats": {
            "candidate_edges_written": len(edges),
            "similarity_mean": round(sum(sims) / max(1, len(sims)), 6) if sims else 0.0,
            "similarity_min": round(min(sims), 6) if sims else 0.0,
            "similarity_max": round(max(sims), 6) if sims else 0.0,
            "max_query_verses": int(args.max_query_verses),
            "top_k": int(args.top_k),
            "min_cosine": float(args.min_cosine),
        },
        "outputs": {
            "candidate_jsonl": str(
                (args.output_jsonl if args.output_jsonl.is_absolute() else ROOT / args.output_jsonl).resolve()
            ).replace("\\", "/"),
            "dry_run": bool(args.dry_run),
        },
    }

    if args.dry_run:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    out_jsonl = args.output_jsonl if args.output_jsonl.is_absolute() else ROOT / args.output_jsonl
    summary_path = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as fh:
        for edge in edges:
            fh.write(json.dumps(edge, ensure_ascii=False) + "\n")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(summary_path))
    print(f"candidate_edges={len(edges)} -> {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
