#!/usr/bin/env python3
"""Compare OS-style graph metrics across canon and null logos_verse_4d corpora (Track B Phase 4)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_logos_verse_4d_graph_v1 import (  # noqa: E402
    _load_corpus,
    _l2_normalize_rows,
    _topk_neighbors_numpy,
    _topk_neighbors_python,
)

OUT_DIR = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_verse_4d_os_compare_v1_latest.json"

DEFAULT_CORPORA: list[tuple[str, Path]] = [
    ("canon", OUT_DIR / "logos_verse_4d_v1_latest.jsonl"),
    ("null_vector_permutation", OUT_DIR / "logos_verse_4d_null_vector_permutation_v1_latest.jsonl"),
    ("null_char_shuffle", OUT_DIR / "logos_verse_4d_null_char_shuffle_v1_latest.jsonl"),
    ("null_token_shuffle", OUT_DIR / "logos_verse_4d_null_token_shuffle_v1_latest.jsonl"),
]

TRACK_WALL: dict[str, bool] = {
    "a_track_auto_promotion": False,
    "live_trading_trigger": False,
    "ready_for_external_send": False,
}


def _gini(values: list[float]) -> float:
    if not values:
        return 0.0
    xs = sorted(float(v) for v in values if v >= 0.0)
    n = len(xs)
    if n == 0:
        return 0.0
    total = sum(xs)
    if total <= 0.0:
        return 0.0
    cum = 0.0
    for i, x in enumerate(xs, start=1):
        cum += i * x
    return (2.0 * cum) / (n * total) - (n + 1.0) / n


def _sample_indices(n: int, sample_size: int, seed: int) -> list[int]:
    if n <= sample_size:
        return list(range(n))
    import random

    rng = random.Random(seed)
    return sorted(rng.sample(range(n), sample_size))


def _mean_top1_cosine(norm_vectors: list[list[float]], indices: list[int]) -> float:
    if len(indices) < 2:
        return 0.0
    try:
        import numpy as np

        sub = np.asarray([norm_vectors[i] for i in indices], dtype=np.float64)
        sims = sub @ sub.T
        top1: list[float] = []
        for local_i in range(sub.shape[0]):
            row = sims[local_i].copy()
            row[local_i] = -np.inf
            top1.append(float(np.max(row)))
        return float(np.mean(top1)) if top1 else 0.0
    except ImportError:
        tops: list[float] = []
        for a_pos, gi in enumerate(indices):
            row = norm_vectors[gi]
            best = -1.0
            for b_pos, gj in enumerate(indices):
                if a_pos == b_pos:
                    continue
                other = norm_vectors[gj]
                sim = sum(x * y for x, y in zip(row, other))
                if sim > best:
                    best = sim
            tops.append(best if best >= 0.0 else 0.0)
        return sum(tops) / len(tops) if tops else 0.0


def _graph_metrics(
    norm_vectors: list[list[float]],
    indices: list[int],
    *,
    top_k: int,
    chunk_size: int,
) -> dict[str, Any]:
    if len(indices) < 2:
        return {
            "rows_in_graph": len(indices),
            "edges_emitted": 0,
            "top_medoid_centrality": 0.0,
            "gini_centrality": 0.0,
            "mean_edge_weight": 0.0,
            "numpy_used": False,
        }

    sub = [norm_vectors[i] for i in indices]
    numpy_used = False
    try:
        import numpy as np

        mat = np.asarray(sub, dtype=np.float64)
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms > 0, norms, 1.0)
        mat = mat / norms
        neighbor_lists = _topk_neighbors_numpy(
            mat, top_k=min(top_k, len(sub) - 1), chunk_size=max(1, chunk_size)
        )
        numpy_used = True
    except ImportError:
        neighbor_lists = _topk_neighbors_python(
            sub,
            top_k=min(top_k, len(sub) - 1),
            chunk_size=max(1, chunk_size),
        )

    centrality = [0.0] * len(sub)
    weights: list[float] = []
    edges = 0
    for i, nbrs in enumerate(neighbor_lists):
        for _j, sim in nbrs:
            w = max(0.0, float(sim))
            weights.append(w)
            centrality[i] += w
            centrality[_j] += w
            edges += 1

    top_cent = max(centrality) if centrality else 0.0
    mean_w = sum(weights) / len(weights) if weights else 0.0
    return {
        "rows_in_graph": len(sub),
        "edges_emitted": edges,
        "top_medoid_centrality": round(top_cent, 6),
        "gini_centrality": round(_gini(centrality), 6),
        "mean_edge_weight": round(mean_w, 6),
        "numpy_used": numpy_used,
    }


def _metrics_for_corpus(
    path: Path,
    *,
    label: str,
    max_rows: int,
    sample_size: int,
    top_k: int,
    full_graph: bool,
    seed: int,
    chunk_size: int,
) -> dict[str, Any]:
    verse_ids, _lanes, _books, raw_vectors = _load_corpus(path, max_rows)
    n = len(verse_ids)
    norm_vectors = _l2_normalize_rows(raw_vectors)
    graph_n = n if full_graph else min(n, sample_size)
    graph_indices = _sample_indices(n, graph_n, seed) if n else []
    cosine_indices = _sample_indices(n, min(n, sample_size), seed + 1) if n else []

    return {
        "label": label,
        "path": str(path.as_posix()),
        "rows": n,
        "mean_top1_cosine": round(_mean_top1_cosine(norm_vectors, cosine_indices), 6),
        "cosine_sample_size": len(cosine_indices),
        "graph": _graph_metrics(
            norm_vectors,
            graph_indices,
            top_k=top_k,
            chunk_size=chunk_size,
        ),
    }


def _delta(a: float | int, b: float | int) -> float:
    return round(float(a) - float(b), 6)


def _build_deltas(canon: dict[str, Any], others: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in others:
        label = str(item["label"])
        g_canon = canon.get("graph") or {}
        g_other = item.get("graph") or {}
        out[label] = {
            "delta_mean_top1_cosine": _delta(
                item.get("mean_top1_cosine", 0), canon.get("mean_top1_cosine", 0)
            ),
            "delta_top_medoid_centrality": _delta(
                g_other.get("top_medoid_centrality", 0),
                g_canon.get("top_medoid_centrality", 0),
            ),
            "delta_gini_centrality": _delta(
                g_other.get("gini_centrality", 0), g_canon.get("gini_centrality", 0)
            ),
            "delta_mean_edge_weight": _delta(
                g_other.get("mean_edge_weight", 0), g_canon.get("mean_edge_weight", 0)
            ),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare logos verse 4D OS metrics (Track B Phase 4)")
    ap.add_argument(
        "--corpus",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="Repeatable; default loads canon + null JSONLs if present",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-rows", type=int, default=0, help="0 = all rows per corpus")
    ap.add_argument("--sample-size", type=int, default=500)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--full-graph", action="store_true", help="Build graph on all rows (not sample)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--chunk-size", type=int, default=512)
    args = ap.parse_args()

    corpora: list[tuple[str, Path]] = []
    if args.corpus:
        for spec in args.corpus:
            if "=" not in spec:
                print(f"ERROR: bad --corpus {spec!r}, want LABEL=PATH", flush=True)
                return 2
            label, p = spec.split("=", 1)
            corpora.append((label.strip(), Path(p.strip())))
    else:
        for label, p in DEFAULT_CORPORA:
            path = p if p.is_absolute() else ROOT / p
            if path.is_file():
                corpora.append((label, path))

    if not corpora:
        print("ERROR: no corpus inputs found", flush=True)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    metrics: list[dict[str, Any]] = []
    for label, path in corpora:
        p = path if path.is_absolute() else ROOT / path
        if not p.is_file():
            print(f"WARN: skip missing {label}: {p}", flush=True)
            continue
        metrics.append(
            _metrics_for_corpus(
                p,
                label=label,
                max_rows=int(args.max_rows),
                sample_size=int(args.sample_size),
                top_k=int(args.top_k),
                full_graph=bool(args.full_graph),
                seed=int(args.seed),
                chunk_size=int(args.chunk_size),
            )
        )

    if not metrics:
        print("ERROR: no metrics computed", flush=True)
        return 2

    canon_entry = next((m for m in metrics if m["label"] == "canon"), metrics[0])
    others = [m for m in metrics if m is not canon_entry]
    deltas = _build_deltas(canon_entry, others)

    report: dict[str, Any] = {
        "schema": "logos_verse_4d_os_compare_v1",
        "version": "1.0.0",
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "purpose": "Track B [HYPO] canon vs null OS-graph metric comparison; not causal proof.",
        "interpretation_note": (
            "[HYPO] Metric deltas between canon and null corpora describe distributional separation "
            "under fixed recipes; they are not proof of semantic structure or promotion readiness. "
            "Production showroom and B2B copy must cite build.sample_size and build.max_rows from this "
            "report (small max_rows such as 30 indicates a smoke sample, not full-corpus OS metrics)."
        ),
        "build": {
            "sample_size": int(args.sample_size),
            "top_k_neighbors": int(args.top_k),
            "full_graph": bool(args.full_graph),
            "max_rows": int(args.max_rows),
            "seed": int(args.seed),
            "chunk_size": int(args.chunk_size),
        },
        "corpora": metrics,
        "deltas_vs_canon": deltas,
        "track_wall": dict(TRACK_WALL),
    }

    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "corpora": len(metrics),
                "canon_mean_top1": canon_entry.get("mean_top1_cosine"),
                "deltas_vs_canon": deltas,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
