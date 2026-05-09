#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.5, M:0.9}
# Balance: 91
# Purpose: Build local SQLite note-memory index with semantic relation inference.
# Keywords: sqlite, embedding, memory, context, notes, rag

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import re
import sqlite3
import struct
import sys
from fnmatch import fnmatch
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

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
DEFAULT_RELATIONS = ROOT / "docs/final/artifacts/context_note_relations_latest.json"
DEFAULT_GLOB = "docs/final/**/*.md"


@dataclass
class Chunk:
    path: str
    chunk_id: int
    text: str
    vec: list[float]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _split_chunks(text: str, max_chars: int) -> list[str]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for block in blocks:
        if len(block) > max_chars:
            # Hard-split very large paragraphs.
            for i in range(0, len(block), max_chars):
                part = block[i : i + max_chars].strip()
                if part:
                    chunks.append(part)
            continue
        extra = len(block) + (2 if cur else 0)
        if cur and cur_len + extra > max_chars:
            chunks.append("\n\n".join(cur))
            cur = [block]
            cur_len = len(block)
        else:
            cur.append(block)
            cur_len += extra
    if cur:
        chunks.append("\n\n".join(cur))
    return chunks


def _iter_files(pattern: str, max_files: int, exclude_globs: list[str]) -> Iterable[Path]:
    pat = pattern.strip()
    if not pat:
        return
    pattern_path = Path(pat)
    if pattern_path.is_absolute():
        matched = sorted(Path(x) for x in glob.glob(pat, recursive=True))
    else:
        matched = sorted(ROOT.glob(pat))
    n = 0
    for p in matched:
        if not p.is_file():
            continue
        p_norm = str(p.resolve()).replace("\\", "/")
        rel_norm = _display_path(p)
        excluded = any(fnmatch(rel_norm, g) or fnmatch(p_norm, g) for g in exclude_globs)
        if excluded:
            continue
        yield p
        n += 1
        if max_files > 0 and n >= max_files:
            break


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _pack_vec(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glob", default=DEFAULT_GLOB, help="File glob under repo root.")
    ap.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Glob to exclude (repeatable). Example: docs/final/artifacts/archive/**/*.md",
    )
    ap.add_argument("--max-files", type=int, default=300, help="0 means unlimited.")
    ap.add_argument("--max-chars", type=int, default=900)
    ap.add_argument("--vector-dim", type=int, default=384)
    ap.add_argument(
        "--embedding-backend",
        choices=("hash_stub_v1", "sentence_transformers"),
        default="hash_stub_v1",
    )
    ap.add_argument("--sentence-transformer-model", default=None)
    ap.add_argument("--sqlite-out", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--relations-json", type=Path, default=DEFAULT_RELATIONS)
    ap.add_argument("--relation-threshold", type=float, default=0.72)
    ap.add_argument("--max-relations-per-file", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.max_chars < 100:
        print("--max-chars must be >= 100", file=sys.stderr)
        return 2
    if args.vector_dim < 8:
        print("--vector-dim must be >= 8", file=sys.stderr)
        return 2

    st_model = None
    embedding_mode = HASH_STUB_MODE
    if args.embedding_backend == "sentence_transformers":
        if not args.sentence_transformer_model:
            print("--sentence-transformer-model is required for sentence_transformers backend", file=sys.stderr)
            return 2
        try:
            st_model = load_sentence_transformer(args.sentence_transformer_model)
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 6
        embedding_mode = EMBEDDING_SENTENCE_TRANSFORMERS

    files = list(_iter_files(args.glob, args.max_files, args.exclude_glob))
    if not files:
        print("No files matched.", file=sys.stderr)
        return 3

    chunks: list[Chunk] = []
    by_file: dict[str, list[list[float]]] = {}

    for p in files:
        rel = _display_path(p)
        text = _read_text(p).strip()
        if not text:
            continue
        parts = _split_chunks(text, args.max_chars)
        file_vecs: list[list[float]] = []
        for i, part in enumerate(parts):
            if args.embedding_backend == "sentence_transformers":
                assert st_model is not None
                vec = st_model.encode([part], normalize_embeddings=True)[0].tolist()
            else:
                vec = hash_stub_v1_embedding_floats(f"{rel}|chunk:{i}|{part[:120]}", args.vector_dim)
            file_vecs.append(vec)
            chunks.append(Chunk(path=rel, chunk_id=i, text=part, vec=vec))
        if file_vecs:
            by_file[rel] = file_vecs

    if not chunks:
        print("No non-empty chunks extracted.", file=sys.stderr)
        return 3

    args.sqlite_out.parent.mkdir(parents=True, exist_ok=True)
    if args.sqlite_out.exists():
        args.sqlite_out.unlink()

    con = sqlite3.connect(str(args.sqlite_out))
    try:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE note_chunks (
                file_path TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                text_sha256 TEXT NOT NULL,
                text_content TEXT NOT NULL,
                dim INTEGER NOT NULL,
                embedding_mode TEXT NOT NULL,
                vec_blob BLOB NOT NULL,
                indexed_at_utc TEXT NOT NULL,
                PRIMARY KEY(file_path, chunk_id)
            )"""
        )
        fts_ready = True
        try:
            cur.execute(
                """CREATE VIRTUAL TABLE note_chunks_fts USING fts5(
                    file_path UNINDEXED,
                    chunk_id UNINDEXED,
                    text_content
                )"""
            )
        except sqlite3.OperationalError:
            # If current sqlite build has no FTS5, dense search still works.
            fts_ready = False
        now = _utc_now()
        for c in chunks:
            cur.execute(
                "INSERT INTO note_chunks VALUES (?,?,?,?,?,?,?,?)",
                (
                    c.path,
                    c.chunk_id,
                    _sha(c.text),
                    c.text,
                    len(c.vec),
                    embedding_mode,
                    _pack_vec(c.vec),
                    now,
                ),
            )
            if fts_ready:
                cur.execute(
                    "INSERT INTO note_chunks_fts(file_path, chunk_id, text_content) VALUES (?,?,?)",
                    (c.path, c.chunk_id, c.text),
                )
        con.commit()
    finally:
        con.close()

    # File-level relation inference via max cosine across chunk pairs.
    file_paths = sorted(by_file.keys())
    relations: dict[str, list[dict[str, float | str]]] = {k: [] for k in file_paths}
    for i, src in enumerate(file_paths):
        src_vecs = by_file[src]
        for j, dst in enumerate(file_paths):
            if i == j:
                continue
            dst_vecs = by_file[dst]
            best = -1.0
            for sv in src_vecs:
                for dv in dst_vecs:
                    sc = _cos(sv, dv)
                    if sc > best:
                        best = sc
            if best >= args.relation_threshold:
                relations[src].append({"related_path": dst, "score": round(best, 6)})
        relations[src].sort(key=lambda x: float(x["score"]), reverse=True)
        relations[src] = relations[src][: max(args.max_relations_per_file, 0)]

    out_doc = {
        "schema": "context_note_relations_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_mode": embedding_mode,
        "glob": args.glob,
        "exclude_globs": args.exclude_glob,
        "files_indexed": len(by_file),
        "chunks_indexed": len(chunks),
        "sqlite_path": str(args.sqlite_out.resolve()),
        "relation_threshold": args.relation_threshold,
        "relations_by_file": relations,
        "fts5_enabled": True,
    }
    try:
        # If table doesn't exist (fts disabled), mark as false.
        con_probe = sqlite3.connect(str(args.sqlite_out))
        try:
            con_probe.execute("SELECT COUNT(*) FROM note_chunks_fts").fetchone()
        finally:
            con_probe.close()
    except sqlite3.OperationalError:
        out_doc["fts5_enabled"] = False
    args.relations_json.parent.mkdir(parents=True, exist_ok=True)
    args.relations_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(
            f"files={len(by_file)} chunks={len(chunks)} mode={embedding_mode} "
            f"sqlite={args.sqlite_out} relations={args.relations_json}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

