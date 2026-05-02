#!/usr/bin/env python3
"""Build a lite SQLite vector store using deterministic hash_stub_v1 embeddings.

Not a neural embedding model: vectors are SHA-derived floats for ANN plumbing tests.
For real embeddings, wire a local model only when LOGOS_VECTOR_INDEX_POLICY status=active
and budget/embedder fields are set (separate change).

Default verse source: corpus manifest input_path; rows capped by --max-verses (default 500).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_vector_hash_stub_v1 import EMBEDDING_MODE, hash_stub_v1_embedding_blob

DEFAULT_POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"
DEFAULT_CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"
DEFAULT_SQLITE = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"

ARTIFACT_SCHEMA = "logos_vector_index_ann_lite_build_report_v1"
VERSION = "1.0.0"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _load_verse_rows(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("verse JSON must be a top-level array")
    rows: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("verse_id"):
            rows.append(item)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--corpus-manifest", type=Path, default=DEFAULT_CORPUS_MANIFEST)
    ap.add_argument(
        "--verse-json",
        type=Path,
        default=None,
        help="Override verse array JSON (default: corpus manifest input_path).",
    )
    ap.add_argument(
        "--max-verses",
        type=int,
        default=500,
        help="Max rows to index (default 500). Use 0 for no cap.",
    )
    ap.add_argument("--vector-dim", type=int, default=384)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--sqlite-out", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print row count; still writes DB/report.",
    )
    args = ap.parse_args()

    if not args.policy.is_file():
        print(f"Missing policy: {args.policy}", file=sys.stderr)
        return 2

    policy_doc = json.loads(args.policy.read_text(encoding="utf-8"))
    if policy_doc.get("schema") != "logos_vector_index_policy_v1":
        print("Policy schema must be logos_vector_index_policy_v1.", file=sys.stderr)
        return 2

    verse_path: Path
    if args.verse_json is not None:
        verse_path = args.verse_json
    else:
        if not args.corpus_manifest.is_file():
            print(f"Missing corpus manifest: {args.corpus_manifest}", file=sys.stderr)
            return 2
        man_doc = json.loads(args.corpus_manifest.read_text(encoding="utf-8"))
        inp = man_doc.get("input_path")
        if not isinstance(inp, str) or not inp.strip():
            print("Corpus manifest missing input_path.", file=sys.stderr)
            return 2
        verse_path = (ROOT / inp).resolve()

    if not verse_path.is_file():
        print(f"Missing verse JSON: {verse_path}", file=sys.stderr)
        return 2

    try:
        rows = _load_verse_rows(verse_path)
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"Failed to load verses: {e}", file=sys.stderr)
        return 2

    if not rows:
        print("No verse rows with verse_id found.", file=sys.stderr)
        return 3

    cap = args.max_verses
    if cap > 0:
        rows = rows[:cap]

    dim = args.vector_dim
    if dim < 8 or dim > 4096:
        print("--vector-dim must be between 8 and 4096.", file=sys.stderr)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    args.sqlite_out.parent.mkdir(parents=True, exist_ok=True)
    if args.sqlite_out.exists():
        args.sqlite_out.unlink()

    con = sqlite3.connect(str(args.sqlite_out))
    try:
        cur = con.cursor()
        cur.execute(
            """CREATE TABLE logos_vec_stub (
            verse_id TEXT PRIMARY KEY,
            dim INTEGER NOT NULL,
            embedding_mode TEXT NOT NULL,
            vec_sha256 TEXT NOT NULL,
            vec_blob BLOB NOT NULL
        )"""
        )
        for row in rows:
            vid = str(row["verse_id"])
            blob = hash_stub_v1_embedding_blob(vid, dim)
            h = hashlib.sha256(blob).hexdigest()
            cur.execute(
                "INSERT INTO logos_vec_stub VALUES (?,?,?,?,?)",
                (vid, dim, EMBEDDING_MODE, h, blob),
            )
        con.commit()
    finally:
        con.close()

    doc: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_mode": EMBEDDING_MODE,
        "vector_dim": dim,
        "rows_written": len(rows),
        "policy_snapshot": {
            "artifact_path": _rel(args.policy),
            "status": policy_doc.get("status"),
            "policy_version": policy_doc.get("version"),
        },
        "verse_source": {
            "path": _rel(verse_path),
            "max_verses_cap": cap if cap > 0 else None,
            "unlimited": cap == 0,
        },
        "sqlite": {
            "path": _rel(args.sqlite_out),
            "table": "logos_vec_stub",
            "bytes_approx": args.sqlite_out.stat().st_size if args.sqlite_out.is_file() else 0,
        },
        "notes": (
            "hash_stub_v1 is deterministic noise for pipeline tests, not semantic similarity. "
            "Replace with real embedder when policy.status=active and ops approves."
        ),
    }

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(
            f"rows={len(rows)} dim={dim} sqlite={_rel(args.sqlite_out)} "
            f"report={_rel(args.report_json)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
