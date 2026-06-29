#!/usr/bin/env python3
"""G2-c — Bundle 31k sasang routing overlay with Logos corpus meaning graph (B-track; read-only)."""

from __future__ import annotations

import argparse
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

DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_manifest_v1_latest.json"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
DEFAULT_GRAPH_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json"

VERSE_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.\d+\.\d+$")


def _rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _verse_ref_from_node(row: dict[str, Any]) -> str | None:
    ref = row.get("ref")
    if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
        return ref.strip()
    nid = row.get("node_id")
    if isinstance(nid, str) and "::" in nid:
        tail = nid.split("::", 1)[1].strip()
        if VERSE_REF_RE.match(tail):
            return tail
    return None


def _verse_ref_from_edge_side(row: dict[str, Any], *, side: str) -> str | None:
    ref_keys = ["source_ref", "src_ref"] if side == "src" else ["target_ref", "dst_ref"]
    node_keys = ["src_node_id", "src_node", "source_node_id"] if side == "src" else ["dst_node_id", "dst_node", "target_node_id"]

    for key in ref_keys:
        val = row.get(key)
        if isinstance(val, str) and VERSE_REF_RE.match(val.strip()):
            return val.strip()

    for key in node_keys:
        val = row.get(key)
        if isinstance(val, str) and "::" in val:
            tail = val.split("::", 1)[1].strip()
            if VERSE_REF_RE.match(tail):
                return tail
    return None


def _load_corpus_verse_ids(jsonl_path: Path, limit: int | None = None) -> set[str]:
    ids: set[str] = set()
    with jsonl_path.open(encoding="utf-8-sig") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            s = line.strip()
            if not s:
                continue
            row = json.loads(s)
            vid = str(row.get("verse_id") or "")
            if vid:
                ids.add(vid)
    return ids


def _graph_overlap_stats(
    *,
    corpus_ids: set[str],
    nodes_path: Path,
    edges_path: Path,
) -> dict[str, Any]:
    node_hits = 0
    node_total = 0
    edge_hits = 0
    edge_total = 0
    edge_types: Counter[str] = Counter()

    if nodes_path.is_file():
        for line in nodes_path.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                row = json.loads(s)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            ref = _verse_ref_from_node(row)
            if ref:
                node_total += 1
                if ref in corpus_ids:
                    node_hits += 1

    if edges_path.is_file():
        for line in edges_path.read_text(encoding="utf-8-sig").splitlines():
            s = line.strip()
            if not s:
                continue
            try:
                row = json.loads(s)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            edge_total += 1
            et = str(row.get("edge_type") or "unknown")
            edge_types[et] += 1
            src = _verse_ref_from_edge_side(row, side="src") or ""
            dst = _verse_ref_from_edge_side(row, side="dst") or ""
            if src in corpus_ids or dst in corpus_ids:
                edge_hits += 1

    return {
        "meaning_graph_nodes_verse_overlap": node_hits,
        "meaning_graph_nodes_verse_total": node_total,
        "meaning_graph_edges_touching_corpus": edge_hits,
        "meaning_graph_edges_total": edge_total,
        "edge_type_histogram": dict(sorted(edge_types.items())),
    }


def build_bundle(
    *,
    manifest_path: Path,
    jsonl_path: Path,
    graph_bundle_path: Path,
    nodes_path: Path,
    edges_path: Path,
) -> dict[str, Any]:
    manifest = _load(manifest_path) if manifest_path.is_file() else {}
    graph_bundle = _load(graph_bundle_path) if graph_bundle_path.is_file() else {}
    corpus_ids = _load_corpus_verse_ids(jsonl_path)
    overlap = _graph_overlap_stats(corpus_ids=corpus_ids, nodes_path=nodes_path, edges_path=edges_path)

    return {
        "schema": "logos_corpus_sasang_routing_graph_bundle_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "track_a_promotion": False,
        "overlay_kind": "sasang_routing_sidecar_on_gematria_path",
        "corpus_verse_count": len(corpus_ids),
        "sasang_routing_manifest": _rel_or_abs(manifest_path),
        "sasang_routing_jsonl": _rel_or_abs(jsonl_path),
        "posture_histogram": manifest.get("posture_histogram") or {},
        "logos_corpus_graph_bundle_pointer": (
            _rel_or_abs(graph_bundle_path) if graph_bundle_path.is_file() else None
        ),
        "logos_corpus_graph_bundle_slice_id": graph_bundle.get("source_slice", {}).get("slice_id"),
        "graph_overlap": overlap,
        "network_layers": [
            "verse_coordinate_corpus_31k",
            "sasang_routing_sidecar_jsonl",
            "bible_meaning_graph_nodes_edges",
        ],
        "must_not_merge_into": list(manifest.get("must_not_merge_into") or []),
        "disclaimer_ko": (
            "좌표망+라우팅+의미그래프 병렬 번들 — Track A·SEND·예언투표 합선 없음"
        ),
        "reproduce": "py scripts/build_logos_corpus_sasang_routing_graph_bundle_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--graph-bundle", type=Path, default=DEFAULT_GRAPH_BUNDLE)
    ap.add_argument("--nodes", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {args.jsonl}"}))
        return 1

    doc = build_bundle(
        manifest_path=args.manifest,
        jsonl_path=args.jsonl,
        graph_bundle_path=args.graph_bundle,
        nodes_path=args.nodes,
        edges_path=args.edges,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "corpus_verse_count": doc["corpus_verse_count"],
                "out": str(args.out),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
