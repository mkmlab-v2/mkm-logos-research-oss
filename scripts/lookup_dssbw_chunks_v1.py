#!/usr/bin/env python3
"""Lookup DSSBW verified chunks by keyword / constitution label (A1 → E2 citation pilot)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNK_TABLE = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
EMBED_CACHE = ROOT / "reports/constitution/btrack_pilot/km_dssbw_chunk_embeddings_cache_v1_latest.json"
CORPUS_ID = "dssbw-edt-2026-03-29"
SOURCE_ID = "ijeoma-dssbw-edt"

CONSTITUTION_KO_TO_HANJA = {
    "태양": "太陽",
    "태음": "太陰",
    "소양": "少陽",
    "소음": "少陰",
    "태양인": "太陽",
    "태음인": "太陰",
    "소양인": "少陽",
    "소음인": "少陰",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_chunks(path: Path | None = None) -> list[dict]:
    p = path or CHUNK_TABLE
    rows: list[dict] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _expand_query_terms(query: str) -> list[str]:
    terms = [query.strip()]
    for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
        if ko in query:
            terms.append(hanja)
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in terms:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _tokenize(text: str) -> list[str]:
    text = (text or "").lower()
    tokens = re.findall(r"[\uac00-\ud7a3]{2,}|[\u4e00-\u9fff]{1,}|[a-z0-9]+", text)
    return tokens


def _chunk_haystack(row: dict) -> str:
    return f"{row.get('preview_80chars') or ''} {row.get('section_label') or ''}"


def _build_idf(chunks: list[dict]) -> dict[str, float]:
    doc_freq: Counter[str] = Counter()
    n = len(chunks) or 1
    for row in chunks:
        toks = set(_tokenize(_chunk_haystack(row)))
        for t in toks:
            doc_freq[t] += 1
    return {t: math.log((n + 1) / (df + 1)) + 1.0 for t, df in doc_freq.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    return {t: tf[t] * idf.get(t, 1.0) for t in tf}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


HASH_EMBED_DIM = 256


def _hash_embed(text: str) -> dict[int, float]:
    """Deterministic feature-hashing embedding (shadow tier, no API/deps)."""
    vec: dict[int, float] = {}
    tokens = _tokenize(text)
    grams: list[str] = []
    for tok in tokens:
        grams.append(tok)
        if len(tok) >= 2:
            for i in range(len(tok) - 1):
                grams.append(tok[i : i + 2])
    for gram in grams:
        digest = hashlib.sha256(gram.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % HASH_EMBED_DIM
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vec[idx] = vec.get(idx, 0.0) + sign
    return vec


def search_chunks_embedding_shadow(
    query: str,
    *,
    chunks: list[dict] | None = None,
    limit: int = 5,
    min_score: float = 0.01,
) -> dict:
    """Hashed n-gram embedding shadow ranker (E2 PoC; not production embedding API)."""
    chunks = chunks if chunks is not None else load_chunks()
    q_text = query
    for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
        if ko in query:
            q_text = f"{q_text} {ko} {hanja}"
    q_vec = _hash_embed(q_text)
    scored: list[tuple[float, dict]] = []
    for row in chunks:
        score = _cosine(q_vec, _hash_embed(_chunk_haystack(row)))
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("chunk_id") or ""))
    top = [r for _, r in scored[:limit]]
    return {
        "query": query,
        "ranker": "hashed_embedding_shadow_v1",
        "hit_count": len(top),
        "chunks": top,
        "scores": [round(s, 6) for s, _ in scored[:limit]],
    }


def _load_embed_backend():
    import importlib.util

    path = ROOT / "scripts/km_dssbw_live_embedding_backend_v1.py"
    spec = importlib.util.spec_from_file_location("embed_backend", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_embedding_cache(path: Path | None = None) -> dict:
    p = path or EMBED_CACHE
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc.get("embeddings") or {}


def search_chunks_live_embedding(
    query: str,
    *,
    chunks: list[dict] | None = None,
    cache_path: Path | None = None,
    limit: int = 5,
    min_score: float = 0.01,
    backend: str = "auto",
) -> dict:
    """Live embedding ranker using cached chunk vectors + on-the-fly query embed."""
    chunks = chunks if chunks is not None else load_chunks()
    cache = _load_embedding_cache(cache_path)
    if not cache:
        return {
            "query": query,
            "ranker": "live_embedding_unavailable",
            "hit_count": 0,
            "chunks": [],
            "scores": [],
            "backend": None,
            "cache_missing": True,
        }

    backend_mod = _load_embed_backend()
    q_text = query
    for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
        if ko in query:
            q_text = f"{q_text} {ko} {hanja}"
    q_vecs, used = backend_mod.embed_texts([q_text], backend=backend)
    qv = q_vecs[0]

    scored: list[tuple[float, dict]] = []
    for row in chunks:
        cid = row.get("chunk_id")
        dv = cache.get(cid) if cid else None
        if not dv:
            continue
        score = backend_mod._cosine_dense(qv, dv)
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("chunk_id") or ""))
    top = [r for _, r in scored[:limit]]
    cache_doc = json.loads((cache_path or EMBED_CACHE).read_text(encoding="utf-8"))
    return {
        "query": query,
        "ranker": "live_embedding_v1",
        "hit_count": len(top),
        "chunks": top,
        "scores": [round(s, 6) for s, _ in scored[:limit]],
        "backend": used,
        "cache_backend": cache_doc.get("backend"),
        "cached_chunks_used": len([r for r in chunks if r.get("chunk_id") in cache]),
    }


def search_chunks_semantic(
    query: str,
    *,
    chunks: list[dict] | None = None,
    limit: int = 5,
    min_score: float = 0.01,
) -> dict:
    """TF-IDF cosine ranker over chunk preview+label (deterministic, no embedding API)."""
    chunks = chunks if chunks is not None else load_chunks()
    idf = _build_idf(chunks)
    q_tokens = _tokenize(query)
    for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
        if ko in query:
            q_tokens.extend(_tokenize(ko))
            q_tokens.extend(_tokenize(hanja))
    q_vec = _tfidf_vector(q_tokens, idf)
    scored: list[tuple[float, dict]] = []
    for row in chunks:
        hay = _chunk_haystack(row)
        score = _cosine(q_vec, _tfidf_vector(_tokenize(hay), idf))
        if score >= min_score:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("chunk_id") or ""))
    top = [r for _, r in scored[:limit]]
    return {
        "query": query,
        "ranker": "tfidf_cosine_v1",
        "hit_count": len(top),
        "chunks": top,
        "scores": [round(s, 6) for s, _ in scored[:limit]],
    }


def search_chunks_hybrid(
    query: str,
    *,
    chunks: list[dict] | None = None,
    limit: int = 5,
    kw_weight: float = 10.0,
    tfidf_weight: float = 1.0,
    min_combined: float = 0.01,
) -> dict:
    """Keyword constitution/hanja boost + TF-IDF rerank (E2 default for citations)."""
    chunks = chunks if chunks is not None else load_chunks()
    terms = _expand_query_terms(query)
    idf = _build_idf(chunks)
    q_tokens = _tokenize(query)
    for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
        if ko in query:
            q_tokens.extend(_tokenize(ko))
            q_tokens.extend(_tokenize(hanja))
    q_vec = _tfidf_vector(q_tokens, idf)
    hanja_values = set(CONSTITUTION_KO_TO_HANJA.values())

    scored: list[tuple[float, float, float, dict]] = []
    for row in chunks:
        hay = _chunk_haystack(row)
        kw_score = 0.0
        for t in terms:
            if t in hay:
                kw_score += 3.0 if t in hanja_values else 1.0
        for ko, hanja in CONSTITUTION_KO_TO_HANJA.items():
            if ko in query and hanja in hay:
                kw_score += 5.0
        tfidf_score = _cosine(q_vec, _tfidf_vector(_tokenize(hay), idf))
        combined = kw_weight * kw_score + tfidf_weight * tfidf_score
        if combined >= min_combined and (kw_score > 0 or tfidf_score >= 0.01):
            scored.append((combined, kw_score, tfidf_score, row))
    scored.sort(key=lambda x: (-x[0], -x[1], -x[2], x[3].get("chunk_id") or ""))
    top = [r for _, _, _, r in scored[:limit]]
    return {
        "query": query,
        "ranker": "hybrid_kw_hanja_tfidf_v1",
        "terms": terms,
        "hit_count": len(top),
        "chunks": top,
        "scores": [round(s, 6) for s, _, _, _ in scored[:limit]],
        "kw_scores": [round(k, 4) for _, k, _, _ in scored[:limit]],
        "tfidf_scores": [round(t, 6) for _, _, t, _ in scored[:limit]],
    }


def search_chunks_for_citation(
    query: str,
    *,
    chunks: list[dict] | None = None,
    limit: int = 5,
    ranker: str = "hybrid",
) -> dict:
    """CDS citation entry: hybrid default, keyword fallback alias."""
    if ranker in ("hybrid", "hybrid_kw_hanja_tfidf_v1", "default"):
        return search_chunks_hybrid(query, chunks=chunks, limit=limit)
    if ranker in ("keyword", "kw"):
        return search_chunks(query, chunks=chunks, limit=limit)
    if ranker in ("semantic", "tfidf"):
        return search_chunks_semantic(query, chunks=chunks, limit=limit)
    if ranker in ("live", "live_embedding"):
        return search_chunks_live_embedding(query, chunks=chunks, limit=limit)
    return search_chunks_hybrid(query, chunks=chunks, limit=limit)


def search_chunks(
    query: str,
    *,
    chunks: list[dict] | None = None,
    limit: int = 5,
    min_hits: int = 1,
) -> dict:
    chunks = chunks if chunks is not None else load_chunks()
    terms = _expand_query_terms(query)
    scored: list[tuple[int, dict]] = []
    for row in chunks:
        preview = row.get("preview_80chars") or ""
        label = row.get("section_label") or ""
        hay = f"{preview} {label}"
        score = sum(1 for t in terms if t in hay or t in query)
        if score >= min_hits:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("chunk_id") or ""))
    top = [r for _, r in scored[:limit]]
    return {
        "query": query,
        "terms": terms,
        "hit_count": len(top),
        "chunks": top,
    }


def chunks_to_evidence_items(search_result: dict, *, retrieved_at_utc: str | None = None) -> list[dict]:
    ts = retrieved_at_utc or _utc()
    items: list[dict] = []
    for row in search_result.get("chunks") or []:
        chunk_id = row.get("chunk_id") or ""
        preview = (row.get("preview_80chars") or "").strip()
        claim = preview[:120] if preview else f"DSSBW chunk {chunk_id}"
        items.append(
            {
                "claim": claim,
                "evidence_grade": "encyclopedic_ref",
                "citation": {
                    "source_id": SOURCE_ID,
                    "chunk_id": chunk_id,
                    "chunk_ref": chunk_id,
                    "document_version": CORPUS_ID,
                    "retrieved_at_utc": ts,
                },
                "relevance": "high" if row == (search_result.get("chunks") or [None])[0] else "medium",
                "notes": f"section={row.get('section_label')} lines={row.get('line_start')}-{row.get('line_end')}",
            }
        )
    return items


def chunks_to_rag_manifest(search_result: dict) -> list[dict]:
    chunk_ids = [r.get("chunk_id") for r in search_result.get("chunks") or [] if r.get("chunk_id")]
    if not chunk_ids:
        return []
    return [
        {
            "corpus_id": CORPUS_ID,
            "snapshot_version": "IJEOMA-CHUNK-RULES-2026-03-29",
            "chunk_ids": chunk_ids,
        }
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", required=True, help="Search query (Korean constitution or hanja)")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--semantic", action="store_true", help="Use TF-IDF semantic ranker")
    ap.add_argument("--hybrid", action="store_true", help="Use keyword hanja boost + TF-IDF hybrid ranker")
    ap.add_argument("--embedding-shadow", action="store_true", help="Use hashed embedding shadow ranker")
    ap.add_argument("--live-embedding", action="store_true", help="Use live embedding ranker (cache required)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.live_embedding:
        result = search_chunks_live_embedding(args.query, limit=args.limit)
    elif args.embedding_shadow:
        result = search_chunks_embedding_shadow(args.query, limit=args.limit)
    elif args.hybrid:
        result = search_chunks_hybrid(args.query, limit=args.limit)
    elif args.semantic:
        result = search_chunks_semantic(args.query, limit=args.limit)
    else:
        result = search_chunks(args.query, limit=args.limit)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for row in result.get("chunks") or []:
            print(row.get("chunk_id"), row.get("preview_80chars"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
