#!/usr/bin/env python3
"""Offline 4D kNN candidate edges for Logos meaning graph ([HYPO] B-track staging).

Writes to bible_meaning_graph_edges_candidate_v1.jsonl — never overwrites canonical
bible_meaning_graph_edges_v1.jsonl. LoRA / survivor / human sign-off required for merge.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_CANONICAL_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT_JSONL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_candidate_v1.jsonl"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/logos_candidate_edges_offline_knn_v1_latest.json"

SCHEMA = "bible_meaning_graph_edge_candidate_v1"
GENERATOR = "build_logos_candidate_edges_offline_knn_v1.py@1.0.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _extract_vector_4d(row: dict[str, Any]) -> list[float] | None:
    raw = row.get("vector_4d") or row.get("unified_4d_vector")
    if raw is None:
        p1 = row.get("pipeline1_simple_4d")
        if isinstance(p1, dict):
            raw = p1.get("vector_4d")
    if isinstance(raw, dict):
        keys = ("S", "L", "K", "M")
        if all(k in raw for k in keys):
            return [float(raw[k]) for k in keys]
    if isinstance(raw, list) and len(raw) >= 4:
        return [float(x) for x in raw[:4]]
    return None


def _node_id(verse_id: str) -> str:
    vid = str(verse_id).strip()
    if vid.startswith("aramaic::"):
        return vid
    return f"aramaic::{vid}"


def _verse_id_from_row(row: dict[str, Any]) -> str:
    return str(row.get("verse_id") or row.get("ref") or "").strip()


def _iter_corpus_rows(path: Path, max_verses: int) -> Iterator[dict[str, Any]]:
    cap = max_verses if max_verses > 0 else None
    n = 0
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if cap is not None and n >= cap:
                    break
                s = line.strip()
                if not s:
                    continue
                row = json.loads(s)
                if isinstance(row, dict) and _verse_id_from_row(row):
                    yield row
                    n += 1
        return

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("corpus JSON must be a top-level array")
    for row in raw:
        if cap is not None and n >= cap:
            break
        if isinstance(row, dict) and _verse_id_from_row(row):
            yield row
            n += 1


def _load_canonical_pairs(edges_path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    if not edges_path.is_file():
        return pairs
    for line in edges_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        a = str(row.get("src_node_id") or "")
        b = str(row.get("dst_node_id") or "")
        if a and b:
            pairs.add(tuple(sorted((a, b))))
    return pairs


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (na * nb)


def _normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    out: list[list[float]] = []
    for v in vectors:
        n = math.sqrt(sum(x * x for x in v))
        if n <= 1e-12:
            out.append([0.0] * len(v))
        else:
            out.append([x / n for x in v])
    return out


def _pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _mk_edge(src: str, dst: str, sim: float) -> dict[str, Any]:
    w = max(0.0, min(1.0, float(sim)))
    return {
        "schema": SCHEMA,
        "src_node_id": src,
        "dst_node_id": dst,
        "edge_type": "semantic_4d_knn",
        "edge_status": "candidate",
        "weight": round(w, 6),
        "similarity_4d_cosine": round(float(sim), 6),
        "as_of_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "hypothesis_tier": "B",
        "relation_basis": ["offline_4d_knn"],
        "source": "build_logos_candidate_edges_offline_knn_v1",
        "evidence": f"offline_4d_knn: cosine={sim:.4f} [HYPO]",
    }


def _collect_knn_edges_numpy(
    node_ids: list[str],
    vectors: list[list[float]],
    *,
    top_k: int,
    min_cosine: float,
    max_candidates: int,
    skip_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    import numpy as np

    x = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    x = x / np.maximum(norms, 1e-9)
    sim = x @ x.T
    np.fill_diagonal(sim, -2.0)

    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    n = len(node_ids)
    k = min(top_k, max(0, n - 1))
    if k == 0:
        return edges

    for i in range(n):
        row = sim[i]
        if k >= n - 1:
            idx = np.argsort(-row)
        else:
            idx = np.argpartition(-row, kth=k - 1)[:k]
            idx = idx[np.argsort(-row[idx])]
        for j in idx:
            if row[j] < min_cosine:
                continue
            src = node_ids[i]
            dst = node_ids[int(j)]
            if src == dst:
                continue
            key = _pair_key(src, dst)
            if key in seen or key in skip_pairs:
                continue
            seen.add(key)
            edges.append(_mk_edge(src, dst, float(row[j])))
            if len(edges) >= max_candidates:
                return edges
    return edges


def _collect_knn_edges_python(
    node_ids: list[str],
    vectors: list[list[float]],
    *,
    top_k: int,
    min_cosine: float,
    max_candidates: int,
    skip_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    normed = _normalize_vectors(vectors)
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    n = len(node_ids)

    for i in range(n):
        sims: list[tuple[float, int]] = []
        vi = normed[i]
        for j in range(n):
            if i == j:
                continue
            s = _cosine(vi, normed[j])
            if s >= min_cosine:
                sims.append((s, j))
        sims.sort(key=lambda t: t[0], reverse=True)
        for s, j in sims[:top_k]:
            src = node_ids[i]
            dst = node_ids[j]
            key = _pair_key(src, dst)
            if key in seen or key in skip_pairs:
                continue
            seen.add(key)
            edges.append(_mk_edge(src, dst, s))
            if len(edges) >= max_candidates:
                return edges
    return edges


def build_candidate_edges(
    *,
    corpus_path: Path,
    canonical_edges_path: Path,
    max_verses: int,
    top_k: int,
    min_cosine: float,
    max_candidates: int,
    skip_canonical: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    node_ids: list[str] = []
    vectors: list[list[float]] = []
    skipped_no_vector = 0

    for row in _iter_corpus_rows(corpus_path, max_verses):
        vec = _extract_vector_4d(row)
        vid = _verse_id_from_row(row)
        if vec is None:
            skipped_no_vector += 1
            continue
        node_ids.append(_node_id(vid))
        vectors.append(vec)

    skip_pairs: set[tuple[str, str]] = set()
    if skip_canonical:
        skip_pairs = _load_canonical_pairs(canonical_edges_path)

    use_numpy = False
    try:
        import numpy as np  # noqa: F401

        use_numpy = len(vectors) >= 32
    except ImportError:
        use_numpy = False

    if use_numpy:
        edges = _collect_knn_edges_numpy(
            node_ids,
            vectors,
            top_k=top_k,
            min_cosine=min_cosine,
            max_candidates=max_candidates,
            skip_pairs=skip_pairs,
        )
        backend = "numpy_cosine"
    else:
        edges = _collect_knn_edges_python(
            node_ids,
            vectors,
            top_k=top_k,
            min_cosine=min_cosine,
            max_candidates=max_candidates,
            skip_pairs=skip_pairs,
        )
        backend = "python_cosine"

    stats = {
        "verses_scanned": len(node_ids) + skipped_no_vector,
        "verses_with_vector_4d": len(node_ids),
        "verses_skipped_no_vector": skipped_no_vector,
        "candidate_edges_written": len(edges),
        "canonical_pairs_skipped": len(skip_pairs) if skip_canonical else 0,
        "similarity_backend": backend,
        "top_k_per_verse": top_k,
        "min_cosine": min_cosine,
        "max_candidates_cap": max_candidates,
    }
    return edges, stats


def resolve_corpus_path(manifest_path: Path, corpus_override: Path | None) -> Path:
    if corpus_override is not None:
        p = corpus_override if corpus_override.is_absolute() else ROOT / corpus_override
        return p.resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing corpus manifest: {manifest_path}")
    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    inp = doc.get("input_path")
    if not isinstance(inp, str) or not inp.strip():
        raise ValueError("Corpus manifest missing input_path")
    return (ROOT / inp).resolve()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--corpus-json", type=Path, default=None, help="Override verse corpus path")
    ap.add_argument("--canonical-edges-jsonl", type=Path, default=DEFAULT_CANONICAL_EDGES)
    ap.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUT_JSONL)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument(
        "--max-verses",
        type=int,
        default=2000,
        help="Cap verses indexed (default 2000 pilot). 0 = no cap (needs numpy; memory heavy).",
    )
    ap.add_argument("--top-k", type=int, default=3, help="Neighbors per verse (default 3)")
    ap.add_argument("--min-cosine", type=float, default=0.92, help="Minimum 4D cosine (default 0.92)")
    ap.add_argument("--max-candidates", type=int, default=5000, help="Hard cap on output edges")
    ap.add_argument(
        "--skip-canonical-pairs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip undirected pairs already in canonical edges (default: true)",
    )
    ap.add_argument("--append", action="store_true", help="Append to output JSONL instead of overwrite")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.top_k < 1:
        print("--top-k must be >= 1", file=sys.stderr)
        return 2
    if args.max_candidates < 1:
        print("--max-candidates must be >= 1", file=sys.stderr)
        return 2
    if not 0.0 <= args.min_cosine <= 1.0:
        print("--min-cosine must be in [0, 1]", file=sys.stderr)
        return 2

    manifest = args.corpus_manifest if args.corpus_manifest.is_absolute() else ROOT / args.corpus_manifest
    canonical = (
        args.canonical_edges_jsonl
        if args.canonical_edges_jsonl.is_absolute()
        else ROOT / args.canonical_edges_jsonl
    )
    out_jsonl = args.output_jsonl if args.output_jsonl.is_absolute() else ROOT / args.output_jsonl
    report_path = args.report_json if args.report_json.is_absolute() else ROOT / args.report_json

    try:
        corpus_path = resolve_corpus_path(manifest, args.corpus_json)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    if not corpus_path.is_file():
        print(f"Missing corpus: {corpus_path}", file=sys.stderr)
        return 2

    if args.max_verses == 0:
        print(
            "note: --max-verses 0 scans full corpus; requires numpy and may use multi-GB RAM.",
            file=sys.stderr,
        )

    edges, stats = build_candidate_edges(
        corpus_path=corpus_path,
        canonical_edges_path=canonical,
        max_verses=int(args.max_verses),
        top_k=int(args.top_k),
        min_cosine=float(args.min_cosine),
        max_candidates=int(args.max_candidates),
        skip_canonical=bool(args.skip_canonical_pairs),
    )

    report = {
        "schema": "logos_candidate_edges_offline_knn_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "generator": GENERATOR,
        "hypothesis_tier": "B",
        "research_only": True,
        "promotion_required": True,
        "non_gating": True,
        "track_wall": {
            "canonical_edges_unmodified": True,
            "no_trade_signals": True,
            "magic_orb_auto_merge": False,
        },
        "mode": "offline_4d_knn",
        "disclaimer_ko": "가설 엣지 스테이징. canonical graph·HUD [CORPUS] meaning edges 미변경. LoRA/survivor/휴먼 승격 전 merge 금지.",
        "inputs": {
            "corpus_path": _rel(corpus_path),
            "canonical_edges_jsonl": _rel(canonical) if canonical.is_file() else None,
            "max_verses": int(args.max_verses),
        },
        "stats": stats,
        "outputs": {
            "candidate_edges_jsonl": _rel(out_jsonl),
            "dry_run": bool(args.dry_run),
            "append_mode": bool(args.append),
        },
    }

    if args.dry_run:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.append else "w"
    with out_jsonl.open(mode, encoding="utf-8") as fh:
        for edge in edges:
            fh.write(json.dumps(edge, ensure_ascii=False) + "\n")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(report_path))
    print(f"candidate_edges={len(edges)} -> {out_jsonl}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
