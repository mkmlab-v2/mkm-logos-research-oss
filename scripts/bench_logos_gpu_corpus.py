# -*- coding: utf-8 -*-
"""Full-corpus Logos batch encoding benchmark → backtest_results/LOGOS_GPU_BENCH.json.

Loads Hebrew/Greek JSONL via ``logos_corpus_loader`` (default: canonical Bible SSOT),
optionally **DSS** + **Apocrypha** from ``data/logos/manuscripts/``, runs
``LogosEncoder.encode_texts_batch_to_logos_embeddings`` in chunks.
Does not import regime/finance modules (Logos-first).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Repo root on sys.path so `py scripts\bench_logos_gpu_corpus.py` works without PYTHONPATH.
_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_root_str = str(_WORKSPACE_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

from tools.core.logos_corpus_loader import (
    default_canon_plus_manuscripts,
    default_hebrew_greek_jsonl,
    iter_hebrew_greek_jsonl,
    iter_union_jsonl,
    verse_logos_text,
)
from tools.core.logos_encoder_gpu import LogosEncoder


def _default_dss_manifest_path(root: Path) -> Path:
    return root / "data" / "logos" / "manuscripts" / "LOGOS_DSS_MANIFEST.json"


def _manuscript_paths_from_manifest(root: Path, manifest: Path) -> List[Path]:
    """Resolve ``path_workspace`` entries from LOGOS_DSS_MANIFEST.json."""
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    out: List[Path] = []
    for entry in raw.get("manuscript_files", []):
        rel = entry.get("path_workspace")
        if not rel:
            continue
        p = (root / rel).resolve()
        if p.is_file() and p not in out:
            out.append(p)
    return out


def _manifest_meta_for_payload(root: Path, manifest: Path) -> Dict[str, Any]:
    """Subset of manifest for benchmark JSON (paths relative to repo)."""
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    files: List[Dict[str, Any]] = []
    for entry in raw.get("manuscript_files", []):
        rel = entry.get("path_workspace")
        files.append(
            {
                "path_workspace": rel,
                "row_count": entry.get("row_count"),
                "file_sha256": entry.get("file_sha256"),
            }
        )
    return {
        "manifest_id": raw.get("manifest_id"),
        "schema_version": raw.get("schema_version"),
        "updated_utc": raw.get("updated_utc"),
        "manifest_path": str(manifest.resolve().relative_to(root)) if manifest.is_file() else str(manifest),
        "manuscript_files": files,
    }


def _workspace_root() -> Path:
    return _WORKSPACE_ROOT


def _parse_args() -> argparse.Namespace:
    root = _workspace_root()
    p = argparse.ArgumentParser(description="Benchmark LogosEncoder on Hebrew/Greek JSONL.")
    p.add_argument(
        "--jsonl",
        type=Path,
        default=None,
        help="Primary corpus path (default: data/logos/bible_original_hebrew_greek.jsonl)",
    )
    p.add_argument(
        "--also",
        type=Path,
        action="append",
        default=[],
        metavar="JSONL",
        help="Additional JSONL corpus (repeatable). Skipped if file missing.",
    )
    p.add_argument(
        "--include-dss-apocrypha",
        action="store_true",
        help="After primary (and --also), append DSS + Apocrypha SSOT paths if present.",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="LOGOS_DSS_MANIFEST.json: use path_workspace entries for manuscripts (with --include-dss-apocrypha).",
    )
    p.add_argument(
        "--ancient-resonance",
        action="store_true",
        help="Canon + DSS + Apocrypha via manifest; writes backtest_results/LOGOS_GPU_BENCH_v2.json.",
    )
    p.add_argument("--chunk-size", type=int, default=512, help="Verses per encode_batch call.")
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Single corpus: max JSON lines read. Multi corpus: max non-empty verses total.",
    )
    p.add_argument(
        "--dss-weight",
        type=float,
        default=1.5,
        help="Metadata only: downstream risk/fusion policy hint for DSS (default 1.5).",
    )
    p.add_argument(
        "--apocrypha-weight",
        type=float,
        default=1.0,
        help="Metadata only: downstream policy hint for Apocrypha (default 1.0).",
    )
    p.add_argument(
        "--canon-weight",
        type=float,
        default=1.0,
        help="Metadata only: canonical corpus weight hint (default 1.0).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root / "backtest_results" / "LOGOS_GPU_BENCH.json",
        help="JSON metrics output path.",
    )
    return p.parse_args()


def _corpus_paths(args: argparse.Namespace, root: Path) -> List[Path]:
    primary = args.jsonl or default_hebrew_greek_jsonl(root)
    paths: List[Path] = [primary]
    for extra in args.also:
        if extra.is_file():
            paths.append(extra)
    if args.include_dss_apocrypha:
        if getattr(args, "manifest", None) and args.manifest.is_file():
            for p in _manuscript_paths_from_manifest(root, args.manifest):
                if p not in paths:
                    paths.append(p)
        else:
            for p in default_canon_plus_manuscripts(root)[1:]:
                if p.is_file() and p not in paths:
                    paths.append(p)
    return paths


def _corpus_key(path: Path) -> str:
    stem = path.stem.lower()
    if "dss" in stem:
        return "dss"
    if "apocrypha" in stem:
        return "apocrypha"
    return "canon"


def main() -> None:
    args = _parse_args()
    root = _workspace_root()
    if args.ancient_resonance:
        args.include_dss_apocrypha = True
        if args.manifest is None:
            args.manifest = _default_dss_manifest_path(root)
        args.output = root / "backtest_results" / "LOGOS_GPU_BENCH_v2.json"
    corpus_paths = _corpus_paths(args, root)
    primary = corpus_paths[0]
    if not primary.is_file():
        raise FileNotFoundError(f"Primary corpus not found: {primary}")

    try:
        import torch
    except ImportError as e:
        raise RuntimeError("PyTorch required for LogosEncoder benchmark.") from e

    device = "cuda" if torch.cuda.is_available() else "cpu"
    encoder = LogosEncoder()
    encoder.eval()

    chunk_size = max(1, int(args.chunk_size))
    texts_buf: List[str] = []
    ids_buf: List[str] = []
    total = 0
    encode_seconds = 0.0
    chunks = 0
    per_corpus: Dict[str, int] = {}

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    def flush_buf() -> None:
        nonlocal total, encode_seconds, chunks, texts_buf, ids_buf
        if not texts_buf:
            return
        t_e0 = time.perf_counter()
        encoder.encode_texts_batch_to_logos_embeddings(texts_buf, device=device)
        encode_seconds += time.perf_counter() - t_e0
        total += len(texts_buf)
        chunks += 1
        texts_buf = []
        ids_buf = []

    t0 = time.perf_counter()
    multi = len(corpus_paths) > 1

    if multi:
        for path, rec in iter_union_jsonl(corpus_paths, global_limit=args.limit):
            key = _corpus_key(path)
            per_corpus[key] = per_corpus.get(key, 0) + 1
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "")
            txt = verse_logos_text(rec)
            ids_buf.append(vid or f"row_{len(ids_buf)}")
            texts_buf.append(txt)
            if len(texts_buf) >= chunk_size:
                flush_buf()
        flush_buf()
    else:
        for rec in iter_hebrew_greek_jsonl(primary, limit=args.limit):
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "")
            txt = verse_logos_text(rec)
            if not txt:
                continue
            key = _corpus_key(primary)
            per_corpus[key] = per_corpus.get(key, 0) + 1
            ids_buf.append(vid or f"row_{len(ids_buf)}")
            texts_buf.append(txt)
            if len(texts_buf) >= chunk_size:
                flush_buf()
        flush_buf()

    wall_seconds = time.perf_counter() - t0

    peak_cuda_mb: Optional[float] = None
    if device == "cuda":
        peak_cuda_mb = torch.cuda.max_memory_allocated() / (1024.0**2)

    items_per_sec = (total / encode_seconds) if encode_seconds > 0 else 0.0
    wall_items_per_sec = (total / wall_seconds) if wall_seconds > 0 else 0.0

    corpus_bytes_total = sum(p.stat().st_size for p in corpus_paths if p.is_file())
    weight_policy = {
        "canon": float(args.canon_weight),
        "dss": float(args.dss_weight),
        "apocrypha": float(args.apocrypha_weight),
        "note": "Hints for downstream fusion / risk bridge; encoder throughput unchanged.",
    }

    payload: Dict[str, Any] = {
        "schema": "logos_gpu_bench_v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "corpus_paths": [str(p.resolve()) for p in corpus_paths],
        "corpus_path": str(primary.resolve()),
        "corpus_bytes": corpus_bytes_total,
        "verses_encoded": total,
        "verses_per_corpus": per_corpus,
        "multi_corpus": multi,
        "weight_policy_meta": weight_policy,
        "chunk_size": chunk_size,
        "chunks": chunks,
        "device": device,
        "cuda_available": torch.cuda.is_available(),
        "encode_seconds": round(encode_seconds, 6),
        "wall_seconds": round(wall_seconds, 6),
        "items_per_second_encode_phase": round(items_per_sec, 4),
        "items_per_second_wall": round(wall_items_per_sec, 4),
        "peak_cuda_memory_mb": round(peak_cuda_mb, 4) if peak_cuda_mb is not None else None,
    }
    if getattr(args, "manifest", None) and args.manifest and args.manifest.is_file():
        payload["dss_manifest"] = _manifest_meta_for_payload(root, args.manifest)

    out: Path = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
