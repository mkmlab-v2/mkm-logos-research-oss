#!/usr/bin/env python3
"""Build a lite SQLite vector store (hash_stub_v1 or optional sentence-transformers).

Neural path requires policy.status=active (or --allow-stub-policy-embedding for dev).
Large verse JSON: use --stream or env LOGOS_VERSE_STREAM_BYTES_THRESHOLD (default 32MiB) + ijson.

Default verse source: corpus manifest input_path; rows capped by --max-verses (default 500).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_ann_lite_embedding_v1 import (
    EMBEDDING_SENTENCE_TRANSFORMERS,
    encode_sentence_transformer_batch,
    load_sentence_transformer,
    neural_embedding_allowed,
    sha256_blob,
)
from scripts.logos_vector_hash_stub_v1 import EMBEDDING_MODE, hash_stub_v1_embedding_blob

DEFAULT_POLICY = ROOT / "docs/final/artifacts/LOGOS_VECTOR_INDEX_POLICY_V1.json"
DEFAULT_CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_REPORT = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1_latest.json"
DEFAULT_SQLITE = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"

ARTIFACT_SCHEMA = "logos_vector_index_ann_lite_build_report_v1"
VERSION = "1.1.0"


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve())


def _stream_threshold_bytes(cli_val: int | None) -> int:
    if cli_val is not None:
        return cli_val
    raw = os.environ.get("LOGOS_VERSE_STREAM_BYTES_THRESHOLD", "")
    if raw.strip().isdigit():
        return int(raw.strip())
    return 32 * 1024 * 1024


def iter_verse_dicts(
    path: Path,
    max_verses: int,
    *,
    force_stream: bool,
    stream_threshold_bytes: int,
) -> Iterator[dict[str, Any]]:
    cap = max_verses if max_verses > 0 else None
    n = 0
    size = path.stat().st_size
    stream = force_stream or size >= stream_threshold_bytes
    if stream:
        try:
            import ijson as ij
        except ImportError:
            raise RuntimeError(
                "STREAM_IJSON_REQUIRED: pip install ijson (large verse JSON or --stream)"
            ) from None

        with path.open("rb") as f:
            for item in ij.items(f, "item"):
                if cap is not None and n >= cap:
                    break
                if isinstance(item, dict) and item.get("verse_id"):
                    yield item
                    n += 1
        return

    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("verse JSON must be a top-level array")
    for item in raw:
        if cap is not None and n >= cap:
            break
        if isinstance(item, dict) and item.get("verse_id"):
            yield item
            n += 1


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
    ap.add_argument(
        "--embedding-backend",
        choices=("hash_stub_v1", "sentence_transformers"),
        default="hash_stub_v1",
        help="hash_stub_v1 (default) or sentence_transformers (policy-gated).",
    )
    ap.add_argument(
        "--sentence-transformer-model",
        type=str,
        default=None,
        metavar="MODEL_ID",
        help="Overrides policy embedding.model_id when backend is sentence_transformers.",
    )
    ap.add_argument(
        "--allow-stub-policy-embedding",
        action="store_true",
        help="Allow neural backend while policy.status is stub (local/dev only).",
    )
    ap.add_argument(
        "--max-wall-seconds",
        type=float,
        default=7200.0,
        help="Wall-clock budget for neural embedding loops (default 7200).",
    )
    ap.add_argument(
        "--stream",
        action="store_true",
        help="Force ijson streaming parse (needs: pip install ijson).",
    )
    ap.add_argument(
        "--stream-threshold-bytes",
        type=int,
        default=None,
        help="Override byte threshold for auto stream (default env or 32MiB).",
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

    emb_cfg = policy_doc.get("embedding") or {}
    max_chars = int(emb_cfg.get("max_chars_per_chunk") or 8192)
    try:
        batch_size = int(emb_cfg.get("batch_size", 32))
    except (TypeError, ValueError):
        batch_size = 32
    normalize = emb_cfg.get("normalize_vectors") is not False

    stream_threshold = _stream_threshold_bytes(args.stream_threshold_bytes)

    backend = args.embedding_backend
    embedding_mode_out = EMBEDDING_MODE
    dim_out = args.vector_dim
    st_model_id: str | None = None

    if backend == "sentence_transformers":
        ok, _reason = neural_embedding_allowed(policy_doc, args.allow_stub_policy_embedding)
        if not ok:
            print(
                "Neural embeddings require policy.status=active or --allow-stub-policy-embedding.",
                file=sys.stderr,
            )
            return 5
        st_model_id = args.sentence_transformer_model or emb_cfg.get("model_id")
        if not isinstance(st_model_id, str) or not st_model_id.strip() or st_model_id.startswith(
            "TBD"
        ):
            print(
                "Set embedding.model_id in policy or pass --sentence-transformer-model.",
                file=sys.stderr,
            )
            return 2
        embedding_mode_out = EMBEDDING_SENTENCE_TRANSFORMERS
    else:
        dim_out = args.vector_dim
        if dim_out < 8 or dim_out > 4096:
            print("--vector-dim must be between 8 and 4096.", file=sys.stderr)
            return 2

    start_m = time.monotonic()
    max_wall = float(args.max_wall_seconds)

    args.sqlite_out.parent.mkdir(parents=True, exist_ok=True)
    if args.sqlite_out.exists():
        args.sqlite_out.unlink()

    rows_written = 0
    notes_parts: list[str] = []

    try:
        gen = iter_verse_dicts(
            verse_path,
            args.max_verses,
            force_stream=args.stream,
            stream_threshold_bytes=stream_threshold,
        )
    except RuntimeError as e:
        err = str(e)
        if "STREAM_IJSON" in err or "ijson" in err.lower():
            print(err, file=sys.stderr)
            return 7
        raise

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

        if backend == "hash_stub_v1":
            for row in gen:
                if time.monotonic() - start_m > max_wall:
                    print("max_wall_seconds exceeded.", file=sys.stderr)
                    return 9
                vid = str(row["verse_id"])
                blob = hash_stub_v1_embedding_blob(vid, dim_out)
                h = sha256_blob(blob)
                cur.execute(
                    "INSERT INTO logos_vec_stub VALUES (?,?,?,?,?)",
                    (vid, dim_out, embedding_mode_out, h, blob),
                )
                rows_written += 1
        else:
            try:
                model = load_sentence_transformer(st_model_id or "")
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return 6
            dim_out = model.get_sentence_embedding_dimension()
            batch: list[dict[str, Any]] = []
            for row in gen:
                if time.monotonic() - start_m > max_wall:
                    print("max_wall_seconds exceeded.", file=sys.stderr)
                    return 9
                batch.append(row)
                if len(batch) >= batch_size:
                    try:
                        pairs = encode_sentence_transformer_batch(
                            model,
                            batch,
                            max_chars=max_chars,
                            normalize=normalize,
                            start_monotonic=start_m,
                            max_wall_seconds=max_wall,
                        )
                    except TimeoutError:
                        print("max_wall_seconds exceeded during encode.", file=sys.stderr)
                        return 9
                    for vid, blob, d in pairs:
                        h = sha256_blob(blob)
                        cur.execute(
                            "INSERT INTO logos_vec_stub VALUES (?,?,?,?,?)",
                            (vid, d, embedding_mode_out, h, blob),
                        )
                        rows_written += 1
                    batch = []
            if batch:
                try:
                    pairs = encode_sentence_transformer_batch(
                        model,
                        batch,
                        max_chars=max_chars,
                        normalize=normalize,
                        start_monotonic=start_m,
                        max_wall_seconds=max_wall,
                    )
                except TimeoutError:
                    print("max_wall_seconds exceeded during encode.", file=sys.stderr)
                    return 9
                for vid, blob, d in pairs:
                    h = sha256_blob(blob)
                    cur.execute(
                        "INSERT INTO logos_vec_stub VALUES (?,?,?,?,?)",
                        (vid, d, embedding_mode_out, h, blob),
                    )
                    rows_written += 1

        con.commit()
    finally:
        con.close()

    if rows_written == 0:
        print("No verse rows with verse_id found.", file=sys.stderr)
        return 3

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cap = args.max_verses

    doc: dict[str, Any] = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "embedding_backend": backend,
        "embedding_mode": embedding_mode_out,
        "vector_dim": dim_out,
        "rows_written": rows_written,
        "policy_snapshot": {
            "artifact_path": _rel(args.policy),
            "status": policy_doc.get("status"),
            "policy_version": policy_doc.get("version"),
        },
        "verse_source": {
            "path": _rel(verse_path),
            "max_verses_cap": cap if cap > 0 else None,
            "unlimited": cap == 0,
            "stream_parsing_used": args.stream
            or verse_path.stat().st_size >= stream_threshold,
            "stream_threshold_bytes": stream_threshold,
        },
        "sqlite": {
            "path": _rel(args.sqlite_out),
            "table": "logos_vec_stub",
            "bytes_approx": args.sqlite_out.stat().st_size if args.sqlite_out.is_file() else 0,
        },
        "notes": "",
    }

    if backend == "sentence_transformers":
        doc["sentence_transformer_model_id"] = st_model_id
        notes_parts.append(
            "sentence_transformers backend — semantic quality depends on model; Track B / gated."
        )
    else:
        notes_parts.append(
            "hash_stub_v1 is deterministic noise for pipeline tests, not semantic similarity."
        )

    doc["notes"] = " ".join(notes_parts)

    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.dry_run:
        print(
            f"rows={rows_written} dim={dim_out} mode={embedding_mode_out} "
            f"sqlite={_rel(args.sqlite_out)} report={_rel(args.report_json)}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
