#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.6, M:0.8}
# Balance: 89
# Purpose: Query local note-memory SQLite index for relevant chunks.
# Keywords: sqlite, context, retrieval, notes, embedding

from __future__ import annotations

import argparse
import json
import math
import re
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_ann_lite_embedding_v1 import (  # noqa: E402
    EMBEDDING_SENTENCE_TRANSFORMERS,
    load_sentence_transformer,
)
from scripts.logos_vector_hash_stub_v1 import EMBEDDING_MODE as HASH_STUB_MODE  # noqa: E402
from scripts.logos_vector_hash_stub_v1 import hash_stub_v1_embedding_floats  # noqa: E402

DEFAULT_SQLITE = ROOT / "docs/final/artifacts/context_note_memory_v1.sqlite"


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _unpack(blob: bytes, dim: int) -> list[float]:
    return list(struct.unpack(f"<{dim}f", blob))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fts_safe_query(text: str) -> str:
    # Keep only word-like tokens to avoid FTS parser operator errors.
    toks = re.findall(r"[0-9A-Za-z_]+", text)
    if not toks:
        return ""
    return " ".join(f"\"{t}\"" for t in toks[:24])


def _query_tokens(text: str) -> set[str]:
    base = {t.lower() for t in re.findall(r"[0-9A-Za-z_]+", text) if t}
    if not base:
        return base
    # Lightweight domain synonym expansion for file-path priors.
    synonyms: dict[str, set[str]] = {
        "ssot": {"constitution", "facts", "implementation"},
        "constitution": {"ssot", "facts"},
        "p0": {"commercialization", "tracker"},
        "tracker": {"p0", "commercialization"},
        "fact": {"facts", "factlock"},
        "facts": {"fact", "factlock"},
        "ops": {"workflow", "local", "vps", "rule"},
        "workflow": {"ops", "runbook", "local", "vps"},
        "vps": {"ops", "workflow", "local"},
        "promotion": {"checklist", "gate", "track", "b", "a"},
        "checklist": {"promotion", "gate"},
        "portfolio": {"domain", "pointer", "mkm"},
        "pointer": {"portfolio", "domain", "mkm"},
        "domain": {"portfolio", "pointer", "mkm"},
    }
    expanded = set(base)
    for tok in list(base):
        expanded.update(synonyms.get(tok, set()))
    return expanded


def _path_token_boost(query_tokens: set[str], file_path: str) -> float:
    if not query_tokens:
        return 0.0
    path_tokens = {t.lower() for t in re.findall(r"[0-9A-Za-z_]+", file_path)}
    if not path_tokens:
        return 0.0
    inter = len(query_tokens.intersection(path_tokens))
    if inter == 0:
        return 0.0
    # Bounded lexical prior to avoid overpowering dense/lexical ranks.
    return min(0.4, 0.08 * inter)


def _path_prior_candidates(
    rows: list[tuple[Any, ...]], query_tokens: set[str], limit: int
) -> list[tuple[float, str, int, str]]:
    if not query_tokens:
        return []
    best_by_file: dict[str, tuple[int, str]] = {}
    for file_path, chunk_id, text_content, _dim, _mode, _vec_blob in rows:
        fp = str(file_path)
        if fp not in best_by_file or int(chunk_id) < best_by_file[fp][0]:
            best_by_file[fp] = (int(chunk_id), str(text_content))
    out: list[tuple[float, str, int, str]] = []
    for file_path, (chunk_id, text_content) in best_by_file.items():
        path_tokens = {t.lower() for t in re.findall(r"[0-9A-Za-z_]+", file_path)}
        if not path_tokens:
            continue
        inter = len(query_tokens.intersection(path_tokens))
        if inter == 0:
            continue
        score = inter / max(len(query_tokens), 1)
        out.append((score, file_path, chunk_id, text_content))
    out.sort(key=lambda x: x[0], reverse=True)
    return out[: max(limit, 0)]


def _intent_override_substrings(query_tokens: set[str]) -> list[str]:
    # Explicit file-prior intents for high-value SSOT documents.
    out: list[str] = []
    if {"implementation", "facts", "ssot"}.issubset(query_tokens) or (
        "constitution" in query_tokens and "facts" in query_tokens
    ):
        out.append("CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md")
    if {"central", "memory", "factlock"}.issubset(query_tokens) or (
        "central" in query_tokens and "memory" in query_tokens
    ):
        out.append("CENTRAL_AGENT_MEMORY_V1.md")
    if {"p0", "commercialization", "tracker"}.intersection(query_tokens) >= {
        "commercialization",
        "tracker",
    }:
        out.append("P0_COMMERCIALIZATION_TRACKER.md")
    if {"promotion", "checklist"}.issubset(query_tokens):
        out.append("MKM_PROMOTION_GATE_CHECKLIST_B_TO_A_C_V1.md")
    if {"ops", "workflow", "local", "vps"}.intersection(query_tokens) >= {"workflow", "vps"}:
        out.append("LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md")
    if {"mkm", "domain", "portfolio", "pointer"}.intersection(query_tokens) >= {
        "domain",
        "portfolio",
    }:
        out.append("MKM_DOMAIN_PORTFOLIO_POINTER_V1.md")
    return out


def _intent_override_candidates(
    rows: list[tuple[Any, ...]], query_tokens: set[str]
) -> list[tuple[float, str, int, str]]:
    targets = _intent_override_substrings(query_tokens)
    if not targets:
        return []
    # One earliest chunk per matched file, with strong bounded prior.
    best: dict[str, tuple[int, str]] = {}
    for file_path, chunk_id, text_content, _dim, _mode, _vec_blob in rows:
        fp = str(file_path)
        if not any(t in fp for t in targets):
            continue
        cid = int(chunk_id)
        if fp not in best or cid < best[fp][0]:
            best[fp] = (cid, str(text_content))
    return [(1.0, fp, v[0], v[1]) for fp, v in best.items()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query", required=True)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument(
        "--retrieval-mode",
        choices=("dense", "lexical", "hybrid"),
        default="hybrid",
        help="dense=embedding only, lexical=FTS5 only, hybrid=RRF fusion.",
    )
    ap.add_argument(
        "--rrf-k",
        type=int,
        default=60,
        help="RRF constant for hybrid fusion.",
    )
    ap.add_argument("--sentence-transformer-model", default=None)
    ap.add_argument("--output-json", type=Path, default=None)
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2
    if args.top_k < 1:
        print("--top-k must be >= 1", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(args.sqlite))
    try:
        rows = con.execute(
            "SELECT file_path, chunk_id, text_content, dim, embedding_mode, vec_blob FROM note_chunks"
        ).fetchall()
    finally:
        con.close()

    if not rows:
        print("Empty note_chunks table.", file=sys.stderr)
        return 3

    dims = {int(r[3]) for r in rows}
    modes = {str(r[4]) for r in rows}
    if len(dims) != 1 or len(modes) != 1:
        print("Mixed dim/embedding_mode in index; rebuild required.", file=sys.stderr)
        return 2
    dim = next(iter(dims))
    mode = next(iter(modes))

    qvec: list[float] | None = None
    if args.retrieval_mode in ("dense", "hybrid"):
        if mode == HASH_STUB_MODE:
            qvec = hash_stub_v1_embedding_floats(f"query_v1|{args.query}", dim)
            mode_note = "hash_stub_v1 query scores are deterministic but not semantic."
        elif mode == EMBEDDING_SENTENCE_TRANSFORMERS:
            if not args.sentence_transformer_model:
                print(
                    "Index mode is sentence_transformers_v1; pass --sentence-transformer-model.",
                    file=sys.stderr,
                )
                return 8
            try:
                model = load_sentence_transformer(args.sentence_transformer_model)
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return 6
            qvec = model.encode([args.query], normalize_embeddings=True)[0].tolist()
            mode_note = "sentence_transformers_v1 cosine similarity."
        else:
            print(f"Unsupported embedding mode: {mode}", file=sys.stderr)
            return 2
    else:
        mode_note = "lexical-only retrieval via FTS5."

    scored_dense: list[tuple[float, str, int, str]] = []
    if args.retrieval_mode in ("dense", "hybrid"):
        assert qvec is not None
        for file_path, chunk_id, text_content, _dim, _mode, vec_blob in rows:
            vec = _unpack(vec_blob, dim)
            scored_dense.append((_cos(qvec, vec), str(file_path), int(chunk_id), str(text_content)))
        scored_dense.sort(key=lambda x: x[0], reverse=True)

    scored_lex: list[tuple[float, str, int, str]] = []
    if args.retrieval_mode in ("lexical", "hybrid"):
        con2 = sqlite3.connect(str(args.sqlite))
        try:
            fts_q = _fts_safe_query(args.query)
            if not fts_q:
                print("Lexical/hybrid query has no searchable tokens.", file=sys.stderr)
                return 2
            try:
                # bm25() returns lower is better; invert sign for "higher is better" convention.
                lex_rows = con2.execute(
                    """
                    SELECT file_path, chunk_id, text_content, bm25(note_chunks_fts) AS rank
                    FROM note_chunks_fts
                    WHERE note_chunks_fts MATCH ?
                    LIMIT ?
                    """,
                    (fts_q, max(args.top_k * 8, 30)),
                ).fetchall()
            except sqlite3.OperationalError as e:
                if "no such table" in str(e).lower() or "fts5" in str(e).lower():
                    print(
                        "Lexical/hybrid requires FTS5 table note_chunks_fts. Rebuild index with current builder.",
                        file=sys.stderr,
                    )
                    return 7
                raise
        finally:
            con2.close()
        for file_path, chunk_id, text_content, rank in lex_rows:
            scored_lex.append((-float(rank), str(file_path), int(chunk_id), str(text_content)))
        scored_lex.sort(key=lambda x: x[0], reverse=True)

    q_toks = _query_tokens(args.query)
    path_candidates = _path_prior_candidates(rows, q_toks, max(args.top_k * 4, 24))
    intent_candidates = _intent_override_candidates(rows, q_toks)

    if args.retrieval_mode == "dense":
        top = scored_dense[: args.top_k]
    elif args.retrieval_mode == "lexical":
        merged_lex = list(scored_lex)
        # Path prior fallback for exact filename-ish intents.
        for s, fp, cid, txt in path_candidates:
            merged_lex.append((0.5 + s, fp, cid, txt))
        for s, fp, cid, txt in intent_candidates:
            merged_lex.append((1.2 + s, fp, cid, txt))
        merged_lex.sort(key=lambda x: x[0], reverse=True)
        top = merged_lex[: args.top_k]
    else:
        # Reciprocal Rank Fusion over dense + lexical rankings.
        fused: dict[tuple[str, int, str], float] = {}
        rrf_k = max(args.rrf_k, 1)
        for rank, item in enumerate(scored_dense[: max(args.top_k * 8, 50)], start=1):
            key = (item[1], item[2], item[3])
            fused[key] = fused.get(key, 0.0) + (1.0 / (rrf_k + rank))
        for rank, item in enumerate(scored_lex[: max(args.top_k * 8, 50)], start=1):
            key = (item[1], item[2], item[3])
            fused[key] = fused.get(key, 0.0) + (1.0 / (rrf_k + rank))
        merged = []
        for key, score in fused.items():
            path_boost = _path_token_boost(q_toks, key[0])
            merged.append((score + path_boost, key[0], key[1], key[2]))
        for s, fp, cid, txt in path_candidates:
            merged.append((0.3 + s, fp, cid, txt))
        for s, fp, cid, txt in intent_candidates:
            merged.append((1.0 + s, fp, cid, txt))
        merged.sort(key=lambda x: x[0], reverse=True)
        top = merged[: args.top_k]

    doc: dict[str, Any] = {
        "schema": "context_note_query_result_v1",
        "version": "1.0.0",
        "ts_utc": _now(),
        "non_gating_ack": True,
        "hypothesis_tier": "B",
        "query": args.query,
        "sqlite_path": str(args.sqlite.resolve()),
        "embedding_mode": mode,
        "retrieval_mode": args.retrieval_mode,
        "notes": mode_note,
        "top_k": [
            {
                "score": round(score, 6),
                "file_path": file_path,
                "chunk_id": chunk_id,
                "text_preview": text[:240],
            }
            for score, file_path, chunk_id, text in top
        ],
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(payload)
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

