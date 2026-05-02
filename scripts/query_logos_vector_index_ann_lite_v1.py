#!/usr/bin/env python3
"""Brute-force Top-K retrieval against logos_vec_stub SQLite (hash_stub_v1).

Scores are dot products (vectors are L2-normalized). Non-semantic stub space —
use for plumbing verification only.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_vector_hash_stub_v1 import (
    EMBEDDING_MODE,
    hash_stub_v1_embedding_floats,
)

DEFAULT_SQLITE = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
QUERY_SEED_PREFIX = "query_v1|"

ARTIFACT_SCHEMA = "logos_vector_ann_lite_query_result_v1"
VERSION = "1.0.0"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument(
        "--query",
        type=str,
        required=True,
        help=f"Ad-hoc text; embedded as seed {QUERY_SEED_PREFIX}<query>",
    )
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional path to write result JSON (still prints stdout).",
    )
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2

    if args.top_k < 1:
        print("--top-k must be >= 1.", file=sys.stderr)
        return 2

    con = sqlite3.connect(str(args.sqlite))
    try:
        cur = con.execute(
            "SELECT verse_id, dim, embedding_mode, vec_blob FROM logos_vec_stub"
        )
        fetched = cur.fetchall()
    finally:
        con.close()

    if not fetched:
        print("Empty logos_vec_stub table.", file=sys.stderr)
        return 3

    dims = {row[1] for row in fetched}
    modes = {row[2] for row in fetched}
    if len(dims) != 1:
        print("Mixed dimensions in index; rebuild required.", file=sys.stderr)
        return 2
    dim = next(iter(dims))
    if modes != {EMBEDDING_MODE}:
        print("Unexpected embedding_mode in sqlite.", file=sys.stderr)
        return 2

    seed = QUERY_SEED_PREFIX + args.query
    qvec = hash_stub_v1_embedding_floats(seed, dim)

    scored: list[tuple[str, float]] = []
    for verse_id, _d, _mode, blob in fetched:
        vals = struct.unpack(f"<{dim}f", blob)
        score = sum(a * b for a, b in zip(qvec, vals))
        scored.append((verse_id, score))

    scored.sort(key=lambda x: -x[1])
    top = scored[: args.top_k]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_mode": EMBEDDING_MODE,
        "sqlite_path": str(args.sqlite.resolve()),
        "query_seed": seed,
        "dim": dim,
        "top_k": [{"verse_id": vid, "score": round(score, 9)} for vid, score in top],
        "notes": "hash_stub_v1 scores are not semantic relevance.",
    }

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(text)

    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
