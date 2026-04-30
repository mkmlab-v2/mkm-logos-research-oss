#!/usr/bin/env python3
"""Run graph anomaly metric sweep from Logos embedding cache (GPU pipeline artifact)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
BACKTEST = ROOT / "backtest_results"

DEFAULT_CACHE = BACKTEST / "LOGOS_EMBEDDING_CACHE_V1.npz"
DEFAULT_OUT = ART / "gpu_graph_anomaly_sweep_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _l2n(x: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / (n + eps)


def _sample_pairs(n: int, sample_count: int, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    i = rng.integers(0, n, size=sample_count, endpoint=False)
    j = rng.integers(0, n, size=sample_count, endpoint=False)
    mask = i != j
    return np.stack([i[mask], j[mask]], axis=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-npz", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--sample-pairs", type=int, default=200000)
    ap.add_argument("--high-cos-cut", type=float, default=0.95)
    ap.add_argument("--mid-cos-low", type=float, default=0.60)
    ap.add_argument("--mid-cos-high", type=float, default=0.80)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.cache_npz.is_file():
        raise SystemExit(f"Missing cache file: {args.cache_npz}")

    data = np.load(args.cache_npz, allow_pickle=True)
    emb = data["embeddings"].astype(np.float32, copy=False)
    keys = data["corpus_keys"]
    n = emb.shape[0]
    if n < 2:
        raise SystemExit("Not enough embedding rows for anomaly sweep.")

    emb = _l2n(emb)
    pairs = _sample_pairs(n, int(args.sample_pairs))
    v1 = emb[pairs[:, 0]]
    v2 = emb[pairs[:, 1]]
    cos = np.sum(v1 * v2, axis=1)

    high_cut = float(args.high_cos_cut)
    mid_low = float(args.mid_cos_low)
    mid_high = float(args.mid_cos_high)

    high_mask = cos >= high_cut
    mid_mask = (cos >= mid_low) & (cos <= mid_high)

    total_pairs = int(cos.shape[0])
    high_pairs = int(np.count_nonzero(high_mask))
    mid_pairs = int(np.count_nonzero(mid_mask))

    k1 = keys[pairs[:, 0]]
    k2 = keys[pairs[:, 1]]
    cross_mask = k1 != k2
    high_cross_pairs = int(np.count_nonzero(high_mask & cross_mask))
    mid_cross_pairs = int(np.count_nonzero(mid_mask & cross_mask))

    cross_bridge_density = (high_cross_pairs / high_pairs) if high_pairs > 0 else 0.0
    mid_bridge_density = (mid_cross_pairs / mid_pairs) if mid_pairs > 0 else 0.0

    out = {
        "schema": "gpu_graph_anomaly_sweep_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "fact_lock_mode": "numeric_scan_only",
        "inputs": {
            "cache_npz": str(args.cache_npz.resolve()),
            "sample_pairs": int(args.sample_pairs),
            "high_cos_cut": high_cut,
            "mid_cos_low": mid_low,
            "mid_cos_high": mid_high,
        },
        "summary": {
            "embedding_rows": int(n),
            "pairs_evaluated": total_pairs,
            "cosine_mean": float(np.mean(cos)),
            "cosine_std": float(np.std(cos)),
            "cosine_p95": float(np.quantile(cos, 0.95)),
            "cosine_p99": float(np.quantile(cos, 0.99)),
        },
        "anomaly_metrics": {
            "high_similarity_pairs": high_pairs,
            "mid_similarity_pairs": mid_pairs,
            "high_cross_pairs": high_cross_pairs,
            "mid_cross_pairs": mid_cross_pairs,
            "cross_bridge_density_high_band": round(cross_bridge_density, 6),
            "cross_bridge_density_mid_band": round(mid_bridge_density, 6),
        },
        "constraints": {
            "no_auto_live_binding": True,
            "btrack_research_only": True,
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
