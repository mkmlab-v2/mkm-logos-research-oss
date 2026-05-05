#!/usr/bin/env python3
"""Build logos core corpus manifest (slice 1): SHA-256, verse count, duplicate/null checks.

Reads `verse_4pipeline_full_31102.json`-style **top-level JSON array** of verse rows.
Uses full file parse (expect ~10² MB-class corpora on dev machines; use smaller fixture in CI).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "logos" / "verse_4pipeline_full_31102.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_corpus_manifest_v1_latest.json"

ARTIFACT_SCHEMA = "logos_corpus_manifest_v1"
VERSION = "1.0.0"
SLICE_ID = "slice1_core_corpus_manifest"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def _load_verse_array(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Expected top-level JSON array")
    return [x for x in data if isinstance(x, dict)]


def _integrity(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ids: list[str | None] = []
    for r in rows:
        vid = r.get("verse_id")
        ids.append(vid.strip() if isinstance(vid, str) and vid.strip() else None)
    null_ct = sum(1 for v in ids if v is None)
    non_null = [v for v in ids if v is not None]
    unique = len(set(non_null))
    dup = len(non_null) != unique
    return {
        "null_verse_id_count": null_ct,
        "duplicate_verse_id_detected": dup,
        "unique_verse_id_count": unique,
    }


def _samples(rows: list[dict[str, Any]], scan: int) -> tuple[list[str], list[str]]:
    head: list[str] = []
    tail: list[str] = []
    for r in rows[:scan]:
        v = r.get("verse_id")
        if isinstance(v, str) and v.strip():
            head.append(v.strip())
        if len(head) >= 8:
            break
    for r in rows[-scan:]:
        v = r.get("verse_id")
        if isinstance(v, str) and v.strip():
            tail.append(v.strip())
    return head[:8], tail[-8:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Verse JSON array file")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Manifest JSON output path")
    ap.add_argument(
        "--verse-count-override",
        type=int,
        default=None,
        help="Skip JSON parse; emit manifest with fixed verse_count (hash/size still computed)",
    )
    args = ap.parse_args()

    inp = args.input
    if not inp.is_file():
        print(f"Missing input: {inp}", file=sys.stderr)
        return 2

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rel_input = _rel_to_root(inp)
    input_bytes = inp.stat().st_size
    digest = _sha256_file(inp)

    if args.verse_count_override is not None:
        doc = {
            "schema": ARTIFACT_SCHEMA,
            "version": VERSION,
            "ts_utc": ts,
            "hypothesis_tier": "B",
            "source_slice": {
                "slice_id": SLICE_ID,
                "description": "manifest with verse_count override (parse skipped)",
            },
            "input_path": rel_input,
            "input_bytes": input_bytes,
            "input_sha256": digest,
            "verse_count": int(args.verse_count_override),
            "verse_count_method": "override",
            "sample_verse_ids_head": [],
            "sample_verse_ids_tail": [],
            "integrity": {
                "null_verse_id_count": 0,
                "duplicate_verse_id_detected": False,
                "unique_verse_id_count": 0,
            },
            "notes": "verse_count_override: integrity not computed.",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0

    try:
        rows = _load_verse_array(inp)
    except MemoryError:
        print(
            "MemoryError loading JSON. Use a smaller fixture, machine with more RAM, "
            "or stream tooling (future).",
            file=sys.stderr,
        )
        return 3
    verse_count = len(rows)
    integrity = _integrity(rows)
    head, tail = _samples(rows, 500)

    doc = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "source_slice": {
            "slice_id": SLICE_ID,
            "description": "Core verse_4pipeline JSON array manifest",
        },
        "input_path": rel_input,
        "input_bytes": input_bytes,
        "input_sha256": digest,
        "verse_count": verse_count,
        "verse_count_method": "json_load",
        "sample_verse_ids_head": head,
        "sample_verse_ids_tail": tail,
        "integrity": {
            "null_verse_id_count": integrity["null_verse_id_count"],
            "duplicate_verse_id_detected": integrity["duplicate_verse_id_detected"],
            "unique_verse_id_count": integrity["unique_verse_id_count"],
        },
        "notes": "",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
