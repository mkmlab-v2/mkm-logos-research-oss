#!/usr/bin/env python3
"""2안 RAG 격파 1라운드 — B-track / research_only (isolated btrack_pilot).

DoD: query preprocess, adaptive top_k + score floor, medoid-weight rerank stub,
before/after mean_top1_cosine on logos_semantic_query_set_v3.

Does NOT touch prophecy_promotion_gates, Track A compression, or gematria bridge.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_ann_lite_embedding_v1 import (
    EMBEDDING_SENTENCE_TRANSFORMERS,
    load_sentence_transformer,
    verse_text_for_embedding,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_VERSE_JSONL = PILOT / "logos_verse_4d_single_anchor_v1_latest.jsonl"
DEFAULT_SQLITE = PILOT / "logos_vector_index_ann_lite_st_u_v1.sqlite"
DEFAULT_BUILD_REPORT = PILOT / "logos_vector_index_ann_lite_st_u_v1_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_v1_latest.json"
DEFAULT_QUERY_SET = ROOT / "docs" / "final" / "artifacts" / "logos_semantic_query_set_v3.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "LOGOS_VECTOR_INDEX_POLICY_V1.json"
DEFAULT_MEDOIDS = ROOT / "docs" / "final" / "artifacts" / "logos_verse_4d_medoids_v1_latest.json"
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

SCHEMA = "comp_logos_rag_retrieval_v1"
VERSION = "1.0.0"

_WS_RE = re.compile(r"\s+")
_PUNCT_EDGE_RE = re.compile(r"^[\s\W]+|[\s\W]+$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def preprocess_query(raw: str) -> str:
    """Light normalization for ANN query input (KO/EN/Han mixed)."""
    q = str(raw or "").strip()
    if not q:
        return ""
    q = _WS_RE.sub(" ", q)
    q = _PUNCT_EDGE_RE.sub("", q)
    return q.lower()


def _load_queries(path: Path) -> list[str]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(obj, dict) and isinstance(obj.get("queries"), list):
        return [str(x).strip() for x in obj["queries"] if str(x).strip()]
    raise ValueError(f"Invalid query set: {path}")


def _load_medoid_weights(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    meds = doc.get("global_medoids")
    if not isinstance(meds, list):
        return {}
    out: dict[str, float] = {}
    for row in meds:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        cent = row.get("centrality")
        if isinstance(vid, str) and isinstance(cent, (int, float)):
            out[vid] = float(cent)
    return out


def _load_index(sqlite: Path) -> tuple[list[tuple[str, bytes]], int, str]:
    con = sqlite3.connect(str(sqlite))
    try:
        cur = con.execute(
            "SELECT verse_id, dim, embedding_mode, vec_blob FROM logos_vec_stub"
        )
        rows = cur.fetchall()
    finally:
        con.close()
    if not rows:
        raise RuntimeError("empty_index")
    dims = {r[1] for r in rows}
    modes = {r[2] for r in rows}
    if len(dims) != 1 or len(modes) != 1:
        raise RuntimeError("mixed_index_metadata")
    dim = next(iter(dims))
    mode = next(iter(modes))
    if mode != EMBEDDING_SENTENCE_TRANSFORMERS:
        raise RuntimeError(f"expected_sentence_transformers_index got={mode}")
    fetched = [(str(r[0]), r[3]) for r in rows]
    return fetched, dim, mode


def _encode_query(model: Any, query: str) -> list[float]:
    import numpy as np

    q = model.encode([query], normalize_embeddings=True)[0]
    return np.asarray(q, dtype=np.float32).tolist()


def _score_all(
    qvec: list[float],
    index_rows: list[tuple[str, bytes]],
    dim: int,
) -> list[tuple[str, float]]:
    scored: list[tuple[str, float]] = []
    for verse_id, blob in index_rows:
        vals = struct.unpack(f"<{dim}f", blob)
        score = sum(a * b for a, b in zip(qvec, vals))
        scored.append((verse_id, score))
    scored.sort(key=lambda x: -x[1])
    return scored


def _retrieve_baseline(scored: list[tuple[str, float]], top_k: int) -> list[dict[str, Any]]:
    return [
        {"verse_id": vid, "score": round(sc, 9), "rank": i + 1}
        for i, (vid, sc) in enumerate(scored[:top_k])
    ]


def _retrieve_improved(
    scored: list[tuple[str, float]],
    *,
    max_k: int,
    floor_abs: float,
    floor_ratio: float,
    medoid_weights: dict[str, float],
    medoid_boost_cap: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not scored:
        return [], {"floor_effective": floor_abs, "candidates_before_rerank": 0}
    top1 = scored[0][1]
    floor_eff = max(floor_abs, top1 * floor_ratio)
    candidates: list[tuple[str, float]] = []
    for vid, sc in scored:
        if sc < floor_eff:
            break
        candidates.append((vid, sc))
        if len(candidates) >= max_k:
            break
    if not candidates:
        candidates = scored[: min(3, max_k)]

    max_cent = max(medoid_weights.values()) if medoid_weights else 1.0
    reranked: list[tuple[str, float, float, float]] = []
    for vid, sc in candidates:
        cent = medoid_weights.get(vid, 0.0)
        boost = 0.0
        if cent > 0 and max_cent > 0:
            boost = min(medoid_boost_cap, (cent / max_cent) * medoid_boost_cap)
        reranked.append((vid, sc, boost, sc + boost))
    reranked.sort(key=lambda x: -x[3])

    hits = [
        {
            "verse_id": vid,
            "score": round(sc, 9),
            "medoid_boost": round(boost, 9),
            "rerank_score": round(rs, 9),
            "rank": i + 1,
        }
        for i, (vid, sc, boost, rs) in enumerate(reranked)
    ]
    meta = {
        "floor_effective": round(floor_eff, 9),
        "top1_cosine_pre_floor": round(top1, 9),
        "candidates_before_rerank": len(candidates),
        "max_k": max_k,
    }
    return hits, meta


def _eval_profile(
    *,
    label: str,
    queries: list[str],
    model: Any,
    index_rows: list[tuple[str, bytes]],
    dim: int,
    preprocess: bool,
    improved: bool,
    top_k: int,
    max_k: int,
    floor_abs: float,
    floor_ratio: float,
    medoid_weights: dict[str, float],
    medoid_boost_cap: float,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for raw_q in queries:
        q_in = preprocess_query(raw_q) if preprocess else raw_q.strip()
        try:
            qvec = _encode_query(model, q_in)
            scored = _score_all(qvec, index_rows, dim)
            if improved:
                hits, meta = _retrieve_improved(
                    scored,
                    max_k=max_k,
                    floor_abs=floor_abs,
                    floor_ratio=floor_ratio,
                    medoid_weights=medoid_weights,
                    medoid_boost_cap=medoid_boost_cap,
                )
            else:
                hits = _retrieve_baseline(scored, top_k)
                meta = {"mode": "fixed_top_k", "top_k": top_k}
            top1 = hits[0] if hits else {}
            rows.append(
                {
                    "query_raw": raw_q,
                    "query_effective": q_in,
                    "status": "ok",
                    "top_match_verse_id": top1.get("verse_id"),
                    "top_match_cosine": top1.get("score"),
                    "top_match_rerank_score": top1.get("rerank_score"),
                    "retrieval_meta": meta,
                    "top_hits": hits[:5],
                }
            )
        except Exception as e:
            rows.append({"query_raw": raw_q, "status": "error", "error": str(e)[:300]})

    ok = [r for r in rows if r.get("status") == "ok"]
    scores = [
        float(r["top_match_cosine"])
        for r in ok
        if isinstance(r.get("top_match_cosine"), (int, float))
    ]
    mean_top1 = sum(scores) / len(scores) if scores else None
    return {
        "profile": label,
        "preprocess": preprocess,
        "improved_retrieval": improved,
        "queries_total": len(rows),
        "queries_ok": len(ok),
        "mean_top1_cosine": None if mean_top1 is None else round(mean_top1, 9),
        "rows": rows,
    }


def _maybe_build_index(
    *,
    verse_jsonl: Path,
    sqlite_out: Path,
    build_report: Path,
    model_id: str,
    max_verses: int,
    skip_build: bool,
) -> dict[str, Any]:
    if skip_build and sqlite_out.is_file():
        return {"skipped": True, "reason": "existing_sqlite", "path": str(sqlite_out)}
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "build_logos_vector_index_ann_lite_v1.py"),
        "--verse-json",
        str(verse_jsonl),
        "--max-verses",
        str(max_verses),
        "--embedding-backend",
        "sentence_transformers",
        "--sentence-transformer-model",
        model_id,
        "--sqlite-out",
        str(sqlite_out),
        "--report-json",
        str(build_report),
    ]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    elapsed = round(time.monotonic() - t0, 2)
    step = {
        "command": "build_logos_vector_index_ann_lite_v1",
        "exit_code": proc.returncode,
        "elapsed_s": elapsed,
        "sqlite": str(sqlite_out),
    }
    if proc.returncode != 0:
        step["stderr_tail"] = (proc.stderr or proc.stdout or "")[-600:]
        return step
    if build_report.is_file():
        step["build_report"] = json.loads(build_report.read_text(encoding="utf-8"))
    return step


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--build-report", type=Path, default=DEFAULT_BUILD_REPORT)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-verses", type=int, default=0, help="0 = full U jsonl")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--baseline-top-k", type=int, default=3)
    ap.add_argument("--improved-max-k", type=int, default=24)
    ap.add_argument("--score-floor-abs", type=float, default=0.12)
    ap.add_argument("--score-floor-ratio", type=float, default=0.62)
    ap.add_argument("--medoid-boost-cap", type=float, default=0.08)
    args = ap.parse_args()

    if not args.query_set_json.is_file():
        print(f"Missing query set: {args.query_set_json}", file=sys.stderr)
        return 2
    if not args.verse_jsonl.is_file():
        print(f"Missing verse jsonl: {args.verse_jsonl}", file=sys.stderr)
        return 2

    args.sqlite.parent.mkdir(parents=True, exist_ok=True)
    build_step = _maybe_build_index(
        verse_jsonl=args.verse_jsonl,
        sqlite_out=args.sqlite,
        build_report=args.build_report,
        model_id=args.sentence_transformer_model,
        max_verses=args.max_verses,
        skip_build=args.skip_build,
    )
    if build_step.get("exit_code", 0) != 0:
        print(json.dumps({"ok": False, "build": build_step}, ensure_ascii=False), file=sys.stderr)
        return int(build_step.get("exit_code") or 1)

    try:
        index_rows, dim, mode = _load_index(args.sqlite)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3

    try:
        model = load_sentence_transformer(args.sentence_transformer_model)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 6

    queries = _load_queries(args.query_set_json)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    before = _eval_profile(
        label="before_baseline_v1",
        queries=queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=False,
        top_k=args.baseline_top_k,
        max_k=args.baseline_top_k,
        floor_abs=0.0,
        floor_ratio=0.0,
        medoid_weights={},
        medoid_boost_cap=0.0,
    )
    after = _eval_profile(
        label="after_round1_v1",
        queries=queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=True,
        improved=True,
        top_k=args.baseline_top_k,
        max_k=args.improved_max_k,
        floor_abs=args.score_floor_abs,
        floor_ratio=args.score_floor_ratio,
        medoid_weights=medoid_weights,
        medoid_boost_cap=args.medoid_boost_cap,
    )

    b_mean = before.get("mean_top1_cosine")
    a_mean = after.get("mean_top1_cosine")
    delta = None
    if isinstance(b_mean, (int, float)) and isinstance(a_mean, (int, float)):
        delta = round(float(a_mean) - float(b_mean), 9)

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating_ack": True,
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
        "inputs": {
            "verse_jsonl": str(args.verse_jsonl.resolve()),
            "sqlite": str(args.sqlite.resolve()),
            "query_set_json": str(args.query_set_json.resolve()),
            "medoids_json": str(args.medoids_json.resolve()) if args.medoids_json.is_file() else None,
            "sentence_transformer_model_id": args.sentence_transformer_model,
            "index_rows": len(index_rows),
            "embedding_mode": mode,
            "vector_dim": dim,
            "medoid_verse_count": len(medoid_weights),
        },
        "knobs": {
            "baseline_top_k": args.baseline_top_k,
            "improved_max_k": args.improved_max_k,
            "score_floor_abs": args.score_floor_abs,
            "score_floor_ratio": args.score_floor_ratio,
            "medoid_boost_cap": args.medoid_boost_cap,
            "query_preprocess": "preprocess_query_v1",
        },
        "build_step": build_step,
        "before": before,
        "after": after,
        "summary": {
            "mean_top1_cosine_before": b_mean,
            "mean_top1_cosine_after": a_mean,
            "mean_top1_delta": delta,
            "baseline_reference_pilot_hit": 0.27,
            "note": "before uses raw query + fixed top_k on ST index with verse text_span; after adds preprocess, floor, medoid rerank.",
        },
        "components": [
            "scripts/query_logos_vector_index_ann_lite_v1.py",
            "scripts/philosophy_lane_rag_pilot_v1.py",
            "scripts/run_logos_rag_retrieval_round_v1.py",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.output_json),
                "mean_before": b_mean,
                "mean_after": a_mean,
                "delta": delta,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
