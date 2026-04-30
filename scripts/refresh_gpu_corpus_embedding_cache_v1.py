#!/usr/bin/env python3
"""Refresh expanded Logos corpus embedding cache on GPU (research-only)."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.core.logos_corpus_loader import iter_union_jsonl, verse_logos_text  # noqa: E402
from tools.core.logos_encoder_gpu import LogosEncoder  # noqa: E402

ART = ROOT / "docs" / "final" / "artifacts"
DATA = ROOT / "data" / "logos"
MS = DATA / "manuscripts"
BACKTEST = ROOT / "backtest_results"

DEFAULT_CANON = DATA / "verse_decoded_v2.jsonl"
DEFAULT_DSS = MS / "dss_original_only_latest.jsonl"
DEFAULT_APOCRYPHA = MS / "apocrypha_original_only_latest.jsonl"
DEFAULT_CACHE = BACKTEST / "LOGOS_EMBEDDING_CACHE_V1.npz"
DEFAULT_REPORT = ART / "gpu_corpus_embedding_refresh_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _corpus_key(path: Path) -> str:
    stem = path.stem.lower()
    if "dss" in stem:
        return "dss"
    if "apocrypha" in stem:
        return "apocrypha"
    return "canon"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canon-jsonl", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--dss-jsonl", type=Path, default=DEFAULT_DSS)
    ap.add_argument("--apocrypha-jsonl", type=Path, default=DEFAULT_APOCRYPHA)
    ap.add_argument("--chunk-size", type=int, default=1024)
    ap.add_argument("--cache-out", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    corpus_paths = [args.canon_jsonl, args.dss_jsonl, args.apocrypha_jsonl]
    corpus_paths = [p for p in corpus_paths if p.is_file()]
    if not corpus_paths:
        raise SystemExit("No corpus files found for cache refresh.")

    try:
        import torch
    except ImportError as e:
        raise RuntimeError("PyTorch required for GPU cache refresh.") from e

    device = "cuda" if torch.cuda.is_available() else "cpu"
    encoder = LogosEncoder().eval()
    chunk_size = max(1, int(args.chunk_size))

    verse_ids: list[str] = []
    corpus_keys: list[str] = []
    embeddings: list[np.ndarray] = []
    per_corpus: dict[str, int] = {"canon": 0, "dss": 0, "apocrypha": 0}

    texts_buf: list[str] = []
    ids_buf: list[str] = []
    keys_buf: list[str] = []

    t0 = time.perf_counter()
    encode_seconds = 0.0
    row_idx = 0

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    def flush() -> None:
        nonlocal encode_seconds
        if not texts_buf:
            return
        te0 = time.perf_counter()
        emb_t = encoder.encode_texts_batch_to_logos_embeddings(texts_buf, device=device)
        encode_seconds += time.perf_counter() - te0
        emb = emb_t.detach().float().cpu().numpy()
        embeddings.append(emb)
        verse_ids.extend(ids_buf)
        corpus_keys.extend(keys_buf)
        texts_buf.clear()
        ids_buf.clear()
        keys_buf.clear()

    for path, rec in iter_union_jsonl(corpus_paths):
        txt = verse_logos_text(rec)
        if not txt:
            continue
        row_idx += 1
        vid = str(rec.get("verse_id") or rec.get("source_ref") or f"row_{row_idx}")
        ck = _corpus_key(path)
        per_corpus[ck] = per_corpus.get(ck, 0) + 1
        texts_buf.append(txt)
        ids_buf.append(vid)
        keys_buf.append(ck)
        if len(texts_buf) >= chunk_size:
            flush()
    flush()

    wall_seconds = time.perf_counter() - t0
    if embeddings:
        matrix = np.vstack(embeddings).astype(np.float32, copy=False)
    else:
        matrix = np.zeros((0, 4), dtype=np.float32)

    args.cache_out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.cache_out,
        verse_ids=np.array(verse_ids, dtype=object),
        corpus_keys=np.array(corpus_keys, dtype=object),
        embeddings=matrix,
    )

    peak_cuda_memory_mb: float | None = None
    if device == "cuda":
        peak_cuda_memory_mb = float(torch.cuda.max_memory_allocated() / (1024.0**2))

    report = {
        "schema": "gpu_corpus_embedding_refresh_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "fact_lock_mode": "numeric_scan_only",
        "inputs": {
            "corpus_paths": [str(p.resolve()) for p in corpus_paths],
            "chunk_size": chunk_size,
        },
        "outputs": {
            "cache_npz": str(args.cache_out.resolve()),
            "embedding_dim": int(matrix.shape[1]) if matrix.ndim == 2 else 0,
            "rows": int(matrix.shape[0]),
        },
        "performance": {
            "device": device,
            "cuda_available": bool(torch.cuda.is_available()),
            "encode_seconds": round(encode_seconds, 6),
            "wall_seconds": round(wall_seconds, 6),
            "items_per_second_encode_phase": round((matrix.shape[0] / encode_seconds), 4) if encode_seconds > 0 else 0.0,
            "items_per_second_wall": round((matrix.shape[0] / wall_seconds), 4) if wall_seconds > 0 else 0.0,
            "peak_cuda_memory_mb": round(peak_cuda_memory_mb, 4) if peak_cuda_memory_mb is not None else None,
        },
        "corpus_breakdown": per_corpus,
        "constraints": {
            "no_auto_live_binding": True,
            "btrack_research_only": True,
        },
    }
    args.report_out.parent.mkdir(parents=True, exist_ok=True)
    args.report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE_CACHE: {args.cache_out}")
    print(f"WROTE_REPORT: {args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
