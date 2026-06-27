#!/usr/bin/env python3
"""Combine corpus manifest (slice 1) + bible_meaning_graph JSONL stats and verse ref overlap.

Read-only on graph files; does not rewrite meaning graph artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"

ARTIFACT_SCHEMA = "logos_corpus_graph_bundle_v1"
VERSION = "1.0.0"
SLICE_ID = "slice2_corpus_graph_bundle"

VERSE_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.\d+\.\d+$")


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


def _verse_ref_from_node(row: dict[str, Any]) -> str | None:
    ref = row.get("ref")
    if isinstance(ref, str):
        s = ref.strip()
        if VERSE_REF_RE.match(s):
            return s
    nid = row.get("node_id")
    if isinstance(nid, str) and "::" in nid:
        tail = nid.split("::", 1)[1].strip()
        if VERSE_REF_RE.match(tail):
            return tail
    return None


def _stream_jsonl_stats(path: Path) -> tuple[int, Counter[str]]:
    """Return line count of valid JSON objects and edge_type histogram (edges file)."""
    n = 0
    hist: Counter[str] = Counter()
    if not path.is_file():
        return 0, hist
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict):
            continue
        n += 1
        et = o.get("edge_type")
        if isinstance(et, str) and et.strip():
            hist[et.strip()] += 1
    return n, hist


def _collect_graph_verse_refs(nodes_path: Path) -> set[str]:
    refs: set[str] = set()
    if not nodes_path.is_file():
        return refs
    for line in nodes_path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if not isinstance(o, dict):
            continue
        vr = _verse_ref_from_node(o)
        if vr:
            refs.add(vr)
    return refs


def _corpus_verse_ids(corpus_path: Path) -> set[str]:
    raw = corpus_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Corpus must be a JSON array")
    out: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid.strip():
            out.add(vid.strip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--skip-corpus-alignment",
        action="store_true",
        help="Do not load corpus JSON; overlap fields set to null/false.",
    )
    args = ap.parse_args()

    mf = args.manifest
    if not mf.is_file():
        print(f"Missing manifest: {mf}", file=sys.stderr)
        return 2

    manifest_body = json.loads(mf.read_text(encoding="utf-8"))
    manifest_sha = _sha256_file(mf)
    nodes_sha = _sha256_file(args.nodes_jsonl) if args.nodes_jsonl.is_file() else ""
    edges_sha = _sha256_file(args.edges_jsonl) if args.edges_jsonl.is_file() else ""

    bundle_material = "".join(sorted([manifest_sha, nodes_sha, edges_sha]))
    dedupe = hashlib.sha256(bundle_material.encode("utf-8")).hexdigest()

    nodes_lines = 0
    edges_lines = 0
    edge_hist: Counter[str] = Counter()
    if args.nodes_jsonl.is_file():
        for line in args.nodes_jsonl.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                o = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(o, dict):
                nodes_lines += 1

    edges_lines, edge_hist = _stream_jsonl_stats(args.edges_jsonl)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    alignment: dict[str, Any] = {
        "corpus_resolved_path": None,
        "corpus_digest_matches_manifest": None,
        "graph_verse_ref_distinct_count": 0,
        "graph_refs_in_corpus_count": None,
        "graph_refs_not_in_corpus_sample": [],
        "skipped_alignment_reason": None,
    }

    graph_refs = _collect_graph_verse_refs(args.nodes_jsonl)
    alignment["graph_verse_ref_distinct_count"] = len(graph_refs)

    if args.skip_corpus_alignment:
        alignment["skipped_alignment_reason"] = "--skip-corpus-alignment"
    else:
        inp_rel = manifest_body.get("input_path")
        if not isinstance(inp_rel, str) or not inp_rel.strip():
            alignment["skipped_alignment_reason"] = "manifest missing input_path"
        else:
            corpus_path = ROOT / inp_rel.replace("/", "\\") if "\\" not in inp_rel else ROOT / inp_rel
            if not corpus_path.is_file():
                alignment["skipped_alignment_reason"] = f"corpus not found: {corpus_path}"
            else:
                alignment["corpus_resolved_path"] = _rel_to_root(corpus_path)
                digest = _sha256_file(corpus_path)
                expected = manifest_body.get("input_sha256")
                alignment["corpus_digest_matches_manifest"] = digest == expected
                try:
                    corpus_ids = _corpus_verse_ids(corpus_path)
                except (MemoryError, json.JSONDecodeError) as e:
                    alignment["skipped_alignment_reason"] = f"corpus load failed: {e}"
                    corpus_ids = set()
                if alignment.get("skipped_alignment_reason") is None:
                    corpus_ids_canon = {canonical_verse_ref(v) for v in corpus_ids}
                    graph_refs_canon = {canonical_verse_ref(v) for v in graph_refs}
                    in_corpus = graph_refs_canon & corpus_ids_canon
                    not_in = sorted(graph_refs_canon - corpus_ids_canon)
                    alignment["graph_refs_in_corpus_count"] = len(in_corpus)
                    alignment["graph_refs_not_in_corpus_sample"] = not_in[:16]
                    if graph_refs != graph_refs_canon or corpus_ids != corpus_ids_canon:
                        alignment["verse_ref_canonicalization_applied"] = True

    snap = {
        "manifest_path": _rel_to_root(mf),
        "manifest_file_sha256": manifest_sha,
        "manifest_ts_utc": manifest_body.get("ts_utc"),
        "corpus_input_path": manifest_body.get("input_path"),
        "corpus_input_sha256": manifest_body.get("input_sha256"),
        "corpus_verse_count": manifest_body.get("verse_count"),
    }

    doc = {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "ts_utc": ts,
        "hypothesis_tier": "B",
        "source_slice": {
            "slice_id": SLICE_ID,
            "description": "Manifest + meaning graph JSONL bundle (read-only stats)",
        },
        "manifest_snapshot": snap,
        "graph_files": {
            "nodes_jsonl_path": _rel_to_root(args.nodes_jsonl),
            "nodes_sha256": nodes_sha or None,
            "nodes_line_count": nodes_lines,
            "edges_jsonl_path": _rel_to_root(args.edges_jsonl),
            "edges_sha256": edges_sha or None,
            "edges_line_count": edges_lines,
            "edge_type_counts": dict(edge_hist),
        },
        "alignment": alignment,
        "dedupe_bundle_key_sha256": dedupe,
        "notes": "",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
