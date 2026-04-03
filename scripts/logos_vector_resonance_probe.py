# -*- coding: utf-8 -*-
"""
Keyword → full-corpus Logos (4D) cosine resonance; optional regime fingerprint alignment.

- Corpus pathing mirrors ``bench_logos_gpu_corpus.py`` (``--ancient-resonance``).
- **Logos-first**: only ``LogosEncoder`` + ``logos_corpus_loader`` for text; regime
  is read from ``data/regimes/regime_map.json`` (no trading stack imports).
- Stage 1: encode query strings and every verse; rank top-k per query by cosine sim.
- Stage 2 (if ``--regime``): re-encode top-hit texts and report cosine vs that regime's
  ``unified_4d_vector`` (same 4D space as Logos embeddings).
- Optional ``--rank-by-regime``: skip keyword ranking; scan the full corpus and keep
  **top-k verses by cosine(verse_embedding, regime fingerprint)** only (regime-primary).

**Operational layer split (do not merge in prose or pipelines):**

- **Regime resonance (this script):** ``--rank-by-regime`` uses ``regime_map.json`` keys
  (e.g. ``imf``, ``lehman``, ``covid``) and Logos embeddings — **not** live index levels.
- **KOSPI time series:** use ``scripts/run_chronos_forward_kospi_baseline.ps1`` (or downstream
  JSON under ``data/chronos_forward_training/``) — **do not** pass KOSPI prints into this probe.
- **Lemma / original-language frequency:** not computed here; any frequency-vs-verse study is a
  **separate research script** and must not be auto-fused with A-track or this probe's output.

This is a **measurement / research** probe, not a live trading signal.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from heapq import heappush, heapreplace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_root_str = str(_WORKSPACE_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

from tools.core.logos_corpus_loader import (  # noqa: E402
    default_canon_plus_manuscripts,
    default_hebrew_greek_jsonl,
    iter_hebrew_greek_jsonl,
    iter_union_jsonl,
    verse_logos_text,
)
from tools.core.logos_encoder_gpu import LogosEncoder  # noqa: E402


def _default_dss_manifest_path(root: Path) -> Path:
    return root / "data" / "logos" / "manuscripts" / "LOGOS_DSS_MANIFEST.json"


def _manuscript_paths_from_manifest(root: Path, manifest: Path) -> List[Path]:
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


def _corpus_key(path: Path) -> str:
    stem = path.stem.lower()
    if "dss" in stem:
        return "dss"
    if "apocrypha" in stem:
        return "apocrypha"
    return "canon"


def _corpus_paths(
    root: Path,
    *,
    jsonl: Optional[Path],
    also: Sequence[Path],
    include_dss_apocrypha: bool,
    manifest: Optional[Path],
) -> List[Path]:
    primary = jsonl or default_hebrew_greek_jsonl(root)
    paths: List[Path] = [primary]
    for extra in also:
        if extra.is_file():
            paths.append(extra)
    if include_dss_apocrypha:
        if manifest and manifest.is_file():
            for p in _manuscript_paths_from_manifest(root, manifest):
                if p not in paths:
                    paths.append(p)
        else:
            for p in default_canon_plus_manuscripts(root)[1:]:
                if p.is_file() and p not in paths:
                    paths.append(p)
    return paths


def _l2n(x: np.ndarray, axis: int = -1, eps: float = 1e-8) -> np.ndarray:
    n = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / (n + eps)


def _load_regime_vector(root: Path, regime_map: Path, regime_id: str) -> np.ndarray:
    raw = json.loads(regime_map.read_text(encoding="utf-8"))
    reg = raw.get("regimes") or {}
    entry = reg.get(regime_id)
    if not entry:
        keys = sorted(reg.keys())
        raise KeyError(f"Unknown regime {regime_id!r}; known: {keys}")
    fp = entry.get("fingerprint") or {}
    u4 = fp.get("unified_4d_vector") or {}
    arr = np.array(
        [float(u4.get("S", 0.0)), float(u4.get("L", 0.0)), float(u4.get("K", 0.0)), float(u4.get("M", 0.0))],
        dtype=np.float32,
    )
    return _l2n(arr.reshape(1, -1))[0]


@dataclass
class _Hit:
    sim_keyword: float
    verse_id: str
    full_text: str
    text_preview: str
    corpus_key: str


class _TopK:
    """Min-heap of (sim, counter, hit) — keep k largest sims."""

    def __init__(self, k: int) -> None:
        self.k = max(1, k)
        self._h: List[Tuple[float, int, _Hit]] = []
        self._ctr = 0

    def push(self, sim: float, hit: _Hit) -> None:
        self._ctr += 1
        item = (sim, self._ctr, hit)
        if len(self._h) < self.k:
            heappush(self._h, item)
            return
        if sim > self._h[0][0]:
            heapreplace(self._h, item)

    def best(self) -> List[_Hit]:
        return [t[2] for t in sorted(self._h, key=lambda x: -x[0])]


def _parse_args() -> argparse.Namespace:
    root = _WORKSPACE_ROOT
    p = argparse.ArgumentParser(description="Logos 4D keyword resonance over JSONL corpus.")
    p.add_argument("--jsonl", type=Path, default=None)
    p.add_argument("--also", type=Path, action="append", default=[], metavar="JSONL")
    p.add_argument("--include-dss-apocrypha", action="store_true")
    p.add_argument("--manifest", type=Path, default=None)
    p.add_argument(
        "--ancient-resonance",
        action="store_true",
        help="Canon + DSS + Apocrypha via manifest (same as GPU bench v2).",
    )
    p.add_argument(
        "--queries",
        type=str,
        default=None,
        help="Comma-separated query strings (any language; fed to LogosEncoder). "
        "Optional when --rank-by-regime (ignored in that mode).",
    )
    p.add_argument(
        "--rank-by-regime",
        action="store_true",
        help="Rank entire corpus by cosine to regime fingerprint only (requires --regime). "
        "Ignores --queries for ranking.",
    )
    p.add_argument("--top-k", type=int, default=12)
    p.add_argument("--chunk-size", type=int, default=512)
    p.add_argument("--limit", type=int, default=None, help="Max non-empty verses (dev).")
    p.add_argument(
        "--regime",
        type=str,
        default=None,
        help="regime_map.json key, e.g. imf, lehman, covid — adds regime_cosine for hits.",
    )
    p.add_argument(
        "--regime-map",
        type=Path,
        default=root / "data" / "regimes" / "regime_map.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root / "backtest_results" / "LOGOS_RESONANCE_PROBE.json",
    )
    return p.parse_args()


def _run_regime_primary_scan(
    *,
    encoder: Any,
    device: str,
    corpus_paths: List[Path],
    primary: Path,
    args_limit: Optional[int],
    chunk_size: int,
    regime_vec: np.ndarray,
    top_k: int,
) -> Tuple[int, List[_Hit]]:
    """Full corpus pass: keep top-k verses by cosine(emb, regime_vec)."""
    top_regime = _TopK(top_k)
    texts_buf: List[str] = []
    meta_buf: List[Tuple[str, str, str]] = []
    total = 0
    row_idx = 0

    def flush() -> None:
        nonlocal total, texts_buf, meta_buf
        if not texts_buf:
            return
        ve = encoder.encode_texts_batch_to_logos_embeddings(texts_buf, device=device)
        v_np = _l2n(ve.detach().float().cpu().numpy())
        sims = v_np @ regime_vec  # (B,)
        for i, (vid, full_txt, ckey) in enumerate(meta_buf):
            s = float(sims[i])
            prev = full_txt.replace("\n", " ")[:240]
            top_regime.push(
                s,
                _Hit(
                    sim_keyword=s,
                    verse_id=vid,
                    full_text=full_txt,
                    text_preview=prev,
                    corpus_key=ckey,
                ),
            )
        total += len(texts_buf)
        texts_buf = []
        meta_buf = []

    multi = len(corpus_paths) > 1
    if multi:
        for path, rec in iter_union_jsonl(corpus_paths, global_limit=args_limit):
            txt = verse_logos_text(rec)
            if not txt:
                continue
            row_idx += 1
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "") or f"row_{row_idx}"
            texts_buf.append(txt)
            meta_buf.append((vid, txt, _corpus_key(path)))
            if len(texts_buf) >= chunk_size:
                flush()
        flush()
    else:
        for rec in iter_hebrew_greek_jsonl(primary, limit=args_limit):
            txt = verse_logos_text(rec)
            if not txt:
                continue
            row_idx += 1
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "") or f"row_{row_idx}"
            texts_buf.append(txt)
            meta_buf.append((vid, txt, _corpus_key(primary)))
            if len(texts_buf) >= chunk_size:
                flush()
        flush()

    return total, top_regime.best()


def main() -> int:
    args = _parse_args()
    root = _WORKSPACE_ROOT
    if args.ancient_resonance:
        args.include_dss_apocrypha = True
        if args.manifest is None:
            args.manifest = _default_dss_manifest_path(root)

    corpus_paths = _corpus_paths(
        root,
        jsonl=args.jsonl,
        also=args.also,
        include_dss_apocrypha=args.include_dss_apocrypha,
        manifest=args.manifest,
    )
    primary = corpus_paths[0]
    if not primary.is_file():
        raise FileNotFoundError(f"Primary corpus not found: {primary}")

    try:
        import torch
    except ImportError as e:
        raise RuntimeError("PyTorch required.") from e

    device = "cuda" if torch.cuda.is_available() else "cpu"
    encoder = LogosEncoder()
    encoder.eval()

    if args.rank_by_regime:
        if not args.regime:
            raise SystemExit("--rank-by-regime requires --regime")
        if not args.regime_map.is_file():
            raise FileNotFoundError(f"Regime map not found: {args.regime_map}")
        regime_vec = _load_regime_vector(root, args.regime_map, args.regime)
        total, hits = _run_regime_primary_scan(
            encoder=encoder,
            device=device,
            corpus_paths=corpus_paths,
            primary=primary,
            args_limit=args.limit,
            chunk_size=max(1, int(args.chunk_size)),
            regime_vec=regime_vec,
            top_k=args.top_k,
        )
        hits_out: List[Dict[str, Any]] = []
        for h in hits:
            hits_out.append(
                {
                    "cosine_to_regime_fingerprint_4d": round(h.sim_keyword, 6),
                    "verse_id": h.verse_id,
                    "corpus_key": h.corpus_key,
                    "text_preview": h.text_preview,
                }
            )
        results: Dict[str, Any] = {
            "schema": "logos_resonance_probe_v2",
            "rank_mode": "regime_primary",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "verses_scanned": total,
            "corpus_paths": [str(p.resolve()) for p in corpus_paths],
            "device": device,
            "regime_id": args.regime,
            "top_k": args.top_k,
            "hits": hits_out,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "verses_scanned": total, "output": str(args.output)}, indent=2))
        return 0

    query_list = [q.strip() for q in (args.queries or "").split(",") if q.strip()]
    if not query_list:
        raise SystemExit("No queries after parsing --queries (required unless --rank-by-regime)")

    q_emb = encoder.encode_texts_batch_to_logos_embeddings(query_list, device=device)
    q_np = _l2n(q_emb.detach().float().cpu().numpy())

    regime_vec: Optional[np.ndarray] = None
    if args.regime:
        if not args.regime_map.is_file():
            raise FileNotFoundError(f"Regime map not found: {args.regime_map}")
        regime_vec = _load_regime_vector(root, args.regime_map, args.regime)

    tops = [_TopK(args.top_k) for _ in query_list]
    chunk_size = max(1, int(args.chunk_size))
    texts_buf: List[str] = []
    meta_buf: List[Tuple[str, str, str]] = []  # (verse_id, full_text, corpus_key)
    total = 0
    row_idx = 0

    def flush() -> None:
        nonlocal total, texts_buf, meta_buf
        if not texts_buf:
            return
        ve = encoder.encode_texts_batch_to_logos_embeddings(texts_buf, device=device)
        v_np = _l2n(ve.detach().float().cpu().numpy())
        sims = v_np @ q_np.T  # (B, Q)
        for i, (vid, full_txt, ckey) in enumerate(meta_buf):
            prev = full_txt.replace("\n", " ")[:240]
            for qi in range(sims.shape[1]):
                s = float(sims[i, qi])
                tops[qi].push(
                    s,
                    _Hit(
                        sim_keyword=s,
                        verse_id=vid,
                        full_text=full_txt,
                        text_preview=prev,
                        corpus_key=ckey,
                    ),
                )
        total += len(texts_buf)
        texts_buf = []
        meta_buf = []

    multi = len(corpus_paths) > 1
    if multi:
        for path, rec in iter_union_jsonl(corpus_paths, global_limit=args.limit):
            txt = verse_logos_text(rec)
            if not txt:
                continue
            row_idx += 1
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "") or f"row_{row_idx}"
            texts_buf.append(txt)
            meta_buf.append((vid, txt, _corpus_key(path)))
            if len(texts_buf) >= chunk_size:
                flush()
        flush()
    else:
        for rec in iter_hebrew_greek_jsonl(primary, limit=args.limit):
            txt = verse_logos_text(rec)
            if not txt:
                continue
            row_idx += 1
            vid = str(rec.get("verse_id") or rec.get("source_ref") or "") or f"row_{row_idx}"
            texts_buf.append(txt)
            meta_buf.append((vid, txt, _corpus_key(primary)))
            if len(texts_buf) >= chunk_size:
                flush()
        flush()

    results: Dict[str, Any] = {
        "schema": "logos_resonance_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "verses_scanned": total,
        "corpus_paths": [str(p.resolve()) for p in corpus_paths],
        "device": device,
        "queries": query_list,
        "top_k": args.top_k,
        "regime_id": args.regime,
        "hits_by_query": [],
    }

    for qi, q in enumerate(query_list):
        hits = tops[qi].best()
        texts_r = [h.full_text for h in hits]
        regime_cos: List[Optional[float]] = [None] * len(hits)
        if regime_vec is not None and texts_r:
            ve2 = encoder.encode_texts_batch_to_logos_embeddings(texts_r, device=device)
            v2 = _l2n(ve2.detach().float().cpu().numpy())
            regime_cos = [float(np.dot(v2[i], regime_vec)) for i in range(len(hits))]

        hits_out: List[Dict[str, Any]] = []
        for hi, h in enumerate(hits):
            d: Dict[str, Any] = {
                "cosine_to_query": round(h.sim_keyword, 6),
                "verse_id": h.verse_id,
                "corpus_key": h.corpus_key,
                "text_preview": h.text_preview,
            }
            if regime_cos[hi] is not None:
                d["cosine_to_regime_fingerprint_4d"] = round(regime_cos[hi], 6)
            hits_out.append(d)

        results["hits_by_query"].append({"query": q, "hits": hits_out})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "verses_scanned": total, "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
