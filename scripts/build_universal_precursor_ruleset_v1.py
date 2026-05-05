#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_root_str = str(ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

from tools.core.logos_encoder_gpu import LogosEncoder



def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (ROOT / p)


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def _verse_text(rec: dict[str, Any]) -> str:
    for k in ("logos_text", "text", "content", "verse_text"):
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    h = str(rec.get("text_hebrew") or "").strip()
    g = str(rec.get("text_greek") or "").strip()
    if h and g:
        return f"{h} {g}".strip()
    return h or g


def _kmeans(x: np.ndarray, k: int, iters: int = 20) -> tuple[np.ndarray, np.ndarray]:
    n = x.shape[0]
    if n == 0:
        return np.zeros((0,), dtype=np.int32), np.zeros((0, x.shape[1]), dtype=np.float32)
    k = max(1, min(k, n))
    # Deterministic init: first k rows after L2-norm sort by sum.
    order = np.argsort(x.sum(axis=1))
    c = x[order[:k]].copy()
    labels = np.zeros((n,), dtype=np.int32)
    for _ in range(iters):
        d = ((x[:, None, :] - c[None, :, :]) ** 2).sum(axis=2)
        new_labels = d.argmin(axis=1).astype(np.int32)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for i in range(k):
            members = x[labels == i]
            if len(members) > 0:
                c[i] = members.mean(axis=0)
    return labels, c


def main() -> int:
    ap = argparse.ArgumentParser(description="Build universal precursor ruleset from relaxed regime overlaps.")
    ap.add_argument(
        "--intersection-json",
        default="backtest_results/LOGOS_RESONANCE_QUAD_FUSION_REGIMES_INTERSECTION_TOP6866_REAL.json",
    )
    ap.add_argument(
        "--corpus-jsonl",
        default="G:/공유 드라이브/MKM_DATA_VAULT/vault/notebooklm_sources/data/logos/bible_original_hebrew_greek.jsonl",
    )
    ap.add_argument("--min-regimes-threshold", type=int, default=3)
    ap.add_argument("--cluster-k", type=int, default=12)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/universal_precursor_ruleset_v1_latest.json",
    )
    args = ap.parse_args()

    inter_path = _resolve(args.intersection_json)
    corpus_path = _resolve(args.corpus_jsonl)
    out_path = _resolve(args.output_json)

    inter = _read_json(inter_path)
    relaxed = inter.get("relaxed_gate") if isinstance(inter.get("relaxed_gate"), dict) else {}
    verse_ids = [str(v).strip() for v in (relaxed.get("verse_ids") or []) if str(v).strip()]
    count_relaxed = int(relaxed.get("count") or len(verse_ids))

    rows = _read_jsonl(corpus_path)
    index: dict[str, str] = {}
    for r in rows:
        vid = str(r.get("verse_id") or r.get("source_ref") or "").strip()
        if not vid:
            continue
        t = _verse_text(r)
        if t:
            index[vid] = t

    texts: list[str] = []
    ids_kept: list[str] = []
    for vid in verse_ids:
        t = index.get(vid)
        if t:
            ids_kept.append(vid)
            texts.append(t)

    enc = LogosEncoder().eval()
    emb = enc.encode_texts_batch_to_logos_embeddings(texts, device="cpu")
    x = emb.detach().cpu().numpy().astype(np.float32)
    labels, centers = _kmeans(x, k=int(args.cluster_k), iters=24)

    clusters: list[dict[str, Any]] = []
    for i in range(centers.shape[0]):
        idx = np.where(labels == i)[0]
        if len(idx) == 0:
            continue
        center = centers[i]
        # Representative by nearest centroid.
        d = ((x[idx] - center[None, :]) ** 2).sum(axis=1)
        rep_j = int(idx[int(d.argmin())])
        cluster_ids = [ids_kept[int(j)] for j in idx]
        coherence = float(1.0 / (1.0 + d.mean()))
        clusters.append(
            {
                "cluster_id": f"C{i+1:02d}",
                "size": int(len(idx)),
                "coherence_score_0_1": round(coherence, 6),
                "centroid_4d": {
                    "S": round(float(center[0]), 6),
                    "L": round(float(center[1]), 6),
                    "K": round(float(center[2]), 6),
                    "M": round(float(center[3]), 6),
                },
                "representative_verse_id": ids_kept[rep_j],
                "representative_text_preview": texts[rep_j][:200],
                "sample_verse_ids": cluster_ids[:25],
            }
        )

    clusters.sort(key=lambda c: c["size"], reverse=True)
    total_used = len(ids_kept)
    usable_ratio = (total_used / max(1, len(verse_ids))) if verse_ids else 0.0
    mean_coh = float(np.mean([c["coherence_score_0_1"] for c in clusters])) if clusters else 0.0

    out = {
        "schema": "universal_precursor_ruleset_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "a_track_binding_forbidden": True,
        "source_track": "B",
        "inputs": {
            "intersection_json": str(inter_path),
            "corpus_jsonl": str(corpus_path),
            "min_regimes_threshold": int(args.min_regimes_threshold),
            "cluster_k": int(args.cluster_k),
        },
        "gate": {
            "score": {
                "count_relaxed_gate": count_relaxed,
                "count_text_joined": total_used,
                "join_coverage_ratio": round(usable_ratio, 6),
                "mean_cluster_coherence_0_1": round(mean_coh, 6),
            },
            "threshold": {
                "min_relaxed_count": 300,
                "min_join_coverage_ratio": 0.8,
                "min_mean_cluster_coherence_0_1": 0.25,
            },
            "decision": "GO_RESEARCH"
            if (
                count_relaxed >= 300
                and usable_ratio >= 0.8
                and mean_coh >= 0.25
            )
            else "HOLD_RESEARCH",
            "note": "Semantic clusters are research candidates only; no live trigger binding.",
        },
        "universal_precursor_clusters": clusters,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    print(
        json.dumps(
            {
                "count_relaxed": count_relaxed,
                "count_joined": total_used,
                "cluster_count": len(clusters),
                "gate_decision": out["gate"]["decision"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
