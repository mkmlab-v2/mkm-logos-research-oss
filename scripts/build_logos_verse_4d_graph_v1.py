#!/usr/bin/env python3
"""Build verse-verse kNN graph + medoid manifest from logos_verse_4d_v1 (Track B).

Approximate top-k neighbors per verse via chunked brute-force cosine on L2-normalized 4D.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from heapq import nlargest
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_IN = OUT_DIR / "logos_verse_4d_v1_latest.jsonl"
DEFAULT_EDGES = OUT_DIR / "logos_verse_4d_graph_edges_v1_latest.jsonl"
DEFAULT_MEDOIDS = ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json"

TRACK_WALL: dict[str, bool] = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}

EDGE_SCHEMA = "logos_verse_4d_graph_edges_v1"
EDGE_VERSION = "1.0.0"
MEDOID_SCHEMA = "logos_verse_4d_medoids_v1"
MEDOID_VERSION = "1.0.0"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _book_from_verse_id(verse_id: str) -> str:
    vid = verse_id.strip()
    if ":" in vid:
        vid = vid.split(":", 1)[1]
    parts = vid.split(".")
    return parts[0] if parts else vid


def _vector4(row: dict[str, Any]) -> list[float] | None:
    v = row.get("vector_4d")
    if not isinstance(v, dict):
        return None
    try:
        return [float(v["S"]), float(v["L"]), float(v["K"]), float(v["M"])]
    except (KeyError, TypeError, ValueError):
        return None


def _l2_normalize_rows(vectors: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for vec in vectors:
        norm = math.sqrt(sum(x * x for x in vec))
        if norm <= 0.0:
            out.append([0.25, 0.25, 0.25, 0.25])
            continue
        out.append([x / norm for x in vec])
    return out


def _load_corpus(
    path: Path, max_rows: int
) -> tuple[list[str], list[str], list[str], list[list[float]]]:
    verse_ids: list[str] = []
    lanes: list[str] = []
    books: list[str] = []
    vectors: list[list[float]] = []
    for i, row in enumerate(_iter_jsonl(path)):
        if max_rows and i >= max_rows:
            break
        if row.get("schema") != "logos_verse_4d_v1":
            continue
        vid = row.get("verse_id")
        vec = _vector4(row)
        if not isinstance(vid, str) or not vid.strip() or vec is None:
            continue
        verse_ids.append(vid.strip())
        lanes.append(str(row.get("lane") or "other"))
        books.append(_book_from_verse_id(vid))
        vectors.append(vec)
    return verse_ids, lanes, books, vectors


def _topk_neighbors_numpy(
    matrix: Any,
    *,
    top_k: int,
    chunk_size: int,
) -> list[list[tuple[int, float]]]:
    import numpy as np

    n = matrix.shape[0]
    neighbors: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    k_eff = min(top_k, max(0, n - 1))
    if k_eff <= 0:
        return neighbors

    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        block = matrix[start:end]
        sims = block @ matrix.T
        for local_i, row_sims in enumerate(sims):
            gi = start + local_i
            row_sims[gi] = -np.inf
            if k_eff < n - 1:
                idx = np.argpartition(row_sims, -k_eff)[-k_eff:]
                idx = idx[np.argsort(row_sims[idx])[::-1]]
            else:
                idx = np.argsort(row_sims)[::-1][:k_eff]
            neighbors[gi] = [(int(j), float(row_sims[j])) for j in idx if int(j) != gi]
    return neighbors


def _topk_neighbors_python(
    matrix: list[list[float]],
    *,
    top_k: int,
    chunk_size: int,
) -> list[list[tuple[int, float]]]:
    n = len(matrix)
    neighbors: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    k_eff = min(top_k, max(0, n - 1))
    if k_eff <= 0:
        return neighbors

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        for gi in range(start, end):
            row = matrix[gi]
            scored: list[tuple[float, int]] = []
            for j, other in enumerate(matrix):
                if j == gi:
                    continue
                scored.append((dot(row, other), j))
            neighbors[gi] = [(j, sim) for sim, j in nlargest(k_eff, scored, key=lambda t: t[0])]
    return neighbors


def _edge_record(verse_id_a: str, verse_id_b: str, cosine: float) -> dict[str, Any]:
    w = max(0.0, float(cosine))
    return {
        "schema": EDGE_SCHEMA,
        "version": EDGE_VERSION,
        "verse_id_a": verse_id_a,
        "verse_id_b": verse_id_b,
        "metric": "cosine",
        "cosine_or_l2": float(cosine),
        "weight": w,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "track_wall": dict(TRACK_WALL),
    }


def _medoid_entries(
    ranked: list[tuple[str, float]],
    meta_lane: dict[str, str],
    meta_book: dict[str, str],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rank, (vid, cent) in enumerate(ranked[:limit], start=1):
        out.append(
            {
                "rank": rank,
                "verse_id": vid,
                "centrality": round(float(cent), 6),
                "lane": meta_lane.get(vid, "other"),
                "book": meta_book.get(vid, _book_from_verse_id(vid)),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos verse 4D kNN graph + medoids (Track B)")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--out-edges", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out-medoids", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--top-k-neighbors", type=int, default=16)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all rows")
    ap.add_argument("--top-medoids", type=int, default=50, help="Global medoid count")
    ap.add_argument(
        "--top-medoids-per-cluster",
        type=int,
        default=5,
        help="Medoids retained per lane / book cluster",
    )
    ap.add_argument("--chunk-size", type=int, default=512)
    args = ap.parse_args()

    in_path = Path(args.input_jsonl)
    if not in_path.is_absolute():
        in_path = ROOT / in_path
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}", flush=True)
        return 2

    verse_ids, lanes, books, raw_vectors = _load_corpus(in_path, int(args.max_rows))
    n = len(verse_ids)
    if n < 2:
        print(f"ERROR: need >=2 valid rows, got {n}", flush=True)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    norm_vectors = _l2_normalize_rows(raw_vectors)
    numpy_used = False
    neighbor_lists: list[list[tuple[int, float]]]

    try:
        import numpy as np

        mat = np.asarray(norm_vectors, dtype=np.float64)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        mat = mat / norms
        neighbor_lists = _topk_neighbors_numpy(
            mat, top_k=int(args.top_k_neighbors), chunk_size=max(1, int(args.chunk_size))
        )
        numpy_used = True
    except ImportError:
        neighbor_lists = _topk_neighbors_python(
            norm_vectors,
            top_k=int(args.top_k_neighbors),
            chunk_size=max(1, int(args.chunk_size)),
        )

    meta_lane = dict(zip(verse_ids, lanes))
    meta_book = dict(zip(verse_ids, books))
    centrality: dict[str, float] = defaultdict(float)
    edges_emitted = 0

    out_edges = Path(args.out_edges)
    if not out_edges.is_absolute():
        out_edges = ROOT / out_edges
    out_edges.parent.mkdir(parents=True, exist_ok=True)

    with out_edges.open("w", encoding="utf-8") as edge_f:
        for i, nbrs in enumerate(neighbor_lists):
            vid_a = verse_ids[i]
            for j, sim in nbrs:
                vid_b = verse_ids[j]
                rec = _edge_record(vid_a, vid_b, sim)
                edge_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                edges_emitted += 1
                w = rec["weight"]
                centrality[vid_a] += w
                centrality[vid_b] += w

    global_ranked = sorted(centrality.items(), key=lambda kv: (-kv[1], kv[0]))
    global_medoids = _medoid_entries(
        global_ranked, meta_lane, meta_book, limit=int(args.top_medoids)
    )

    by_lane: dict[str, list[tuple[str, float]]] = defaultdict(list)
    by_book: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for vid, cent in centrality.items():
        by_lane[meta_lane.get(vid, "other")].append((vid, cent))
        by_book[meta_book.get(vid, _book_from_verse_id(vid))].append((vid, cent))

    medoids_by_lane = {
        lane: _medoid_entries(
            sorted(items, key=lambda kv: (-kv[1], kv[0])),
            meta_lane,
            meta_book,
            limit=int(args.top_medoids_per_cluster),
        )
        for lane, items in sorted(by_lane.items())
    }
    medoids_by_book = {
        book: _medoid_entries(
            sorted(items, key=lambda kv: (-kv[1], kv[0])),
            meta_lane,
            meta_book,
            limit=int(args.top_medoids_per_cluster),
        )
        for book, items in sorted(by_book.items())
    }

    lane_counts: dict[str, int] = defaultdict(int)
    for lane in lanes:
        lane_counts[lane] += 1

    out_medoids = Path(args.out_medoids)
    if not out_medoids.is_absolute():
        out_medoids = ROOT / out_medoids
    out_medoids.parent.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "schema": MEDOID_SCHEMA,
        "version": MEDOID_VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "purpose": "Track B [HYPO] verse kNN hubs/medoids from 4D cosine; not Track A promotion.",
        "inputs": {
            "verse_4d_jsonl": str(in_path.as_posix()),
            "verse_4d_jsonl_sha256": _sha256_file(in_path),
        },
        "outputs": {
            "graph_edges_jsonl": str(out_edges.as_posix()),
            "graph_edges_jsonl_sha256": _sha256_file(out_edges),
            "medoid_manifest_self": str(out_medoids.as_posix()),
        },
        "build": {
            "top_k_neighbors": int(args.top_k_neighbors),
            "top_medoids_global": int(args.top_medoids),
            "top_medoids_per_cluster": int(args.top_medoids_per_cluster),
            "metric": "cosine",
            "similarity_on_l2_normalized": True,
            "chunk_size": max(1, int(args.chunk_size)),
            "numpy_used": numpy_used,
        },
        "counts": {
            "rows_used": n,
            "edges_emitted": edges_emitted,
            "unique_verse_ids": n,
            "lanes": dict(lane_counts),
            "books": len(by_book),
        },
        "global_medoids": global_medoids,
        "medoids_by_lane": medoids_by_lane,
        "medoids_by_book": medoids_by_book,
        "track_wall": dict(TRACK_WALL),
        "notes": "SSOT contract phase2: docs/final/artifacts/LOGOS_VERSE_4D_V1_CONTRACT.json",
    }
    out_medoids.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "rows_used": n,
                "edges_emitted": edges_emitted,
                "numpy_used": numpy_used,
                "top_global_medoid": global_medoids[0]["verse_id"] if global_medoids else None,
                "edges": str(out_edges),
                "medoids": str(out_medoids),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
