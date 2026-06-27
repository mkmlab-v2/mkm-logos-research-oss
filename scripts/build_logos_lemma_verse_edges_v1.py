#!/usr/bin/env python3
"""Phase 1+: lemma↔verse edges from concept_bridge + corpus graph tokens ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

DEFAULT_CORPUS_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
DEFAULT_BRIDGE = ROOT / "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json"
DEFAULT_GRAPH_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"

TOK_RE = re.compile(r"[\u0590-\u05FF]{3,}")


def _corpus_verse_ids(manifest_path: Path) -> set[str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rel = manifest.get("input_path")
    if not isinstance(rel, str):
        return set()
    corpus_path = ROOT / rel.replace("/", "\\")
    if not corpus_path.is_file():
        return set()
    data = json.loads(corpus_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return set()
    return {
        str(row.get("verse_id")).strip()
        for row in data
        if isinstance(row, dict) and isinstance(row.get("verse_id"), str) and row.get("verse_id").strip()
    }


def _filter_edges_to_corpus(
    rows: list[dict[str, Any]],
    corpus_ids: set[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    if not corpus_ids:
        return rows, []
    kept: list[dict[str, Any]] = []
    dropped: list[str] = []
    for row in rows:
        dst = str(row.get("dst_node_id") or "").strip()
        et = str(row.get("edge_type") or "")
        if et == "CONTAIN" and dst and dst not in corpus_ids:
            dropped.append(dst)
            continue
        kept.append(row)
    return kept, dropped


def _is_lemma_step(sid: str) -> bool:
    return sid.startswith("lemma:") or sid.startswith(("lp_", "node_lemma_")) or "lemma" in sid.lower()


def _resolve_verse_dst(sid: str, verse_by_short: dict[str, str]) -> str:
    if sid.startswith("verse:"):
        raw = verse_by_short.get(sid, sid.split(":", 1)[1])
        return canonical_verse_ref(raw)
    if sid in verse_by_short:
        return canonical_verse_ref(verse_by_short[sid])
    c = canonical_verse_ref(sid)
    if c and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+", c):
        return c
    return ""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_edges(bridge_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not bridge_path.is_file():
        raise FileNotFoundError(bridge_path)
    doc = json.loads(bridge_path.read_text(encoding="utf-8"))
    verse_by_short: dict[str, str] = {}
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("node_id") or "")
        vid = node.get("verse_id")
        if nid.startswith("verse:") and vid:
            verse_by_short[nid] = canonical_verse_ref(str(vid))
        elif node.get("kind") == "verse_ref" and nid:
            verse_by_short[nid] = canonical_verse_ref(str(vid or nid))

    rows: list[dict[str, Any]] = []
    edge_i = 0
    for path in doc.get("paths") or []:
        if not isinstance(path, dict):
            continue
        steps = path.get("steps") or []
        if not isinstance(steps, list):
            continue
        lemma_id: str | None = None
        for step in steps:
            sid = str(step) if isinstance(step, str) else str((step or {}).get("node_id") or "")
            if not sid:
                continue
            if _is_lemma_step(sid):
                lemma_id = sid
            elif lemma_id:
                dst = _resolve_verse_dst(sid, verse_by_short)
                if not dst:
                    lemma_id = None
                    continue
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::{edge_i}",
                        "src_node_id": lemma_id,
                        "dst_node_id": dst,
                        "edge_type": "CONTAIN",
                        "weight": 0.5,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "path_id": path.get("path_id"),
                        "source_bridge": bridge_path.relative_to(ROOT).as_posix()
                        if bridge_path.is_relative_to(ROOT)
                        else str(bridge_path),
                    }
                )
                edge_i += 1
                lemma_id = None
    manifest = {
        "schema": "logos_lemma_verse_edges_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "source_bridge": bridge_path.relative_to(ROOT).as_posix()
        if bridge_path.is_relative_to(ROOT)
        else str(bridge_path),
        "edge_count": len(rows),
        "note": "Educational proxy edges from concept_bridge; not morphology-verified.",
    }
    return rows, manifest


def build_edges_from_registry(registry_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not registry_path.is_file():
        raise FileNotFoundError(registry_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    merged: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    bridge_sources: list[str] = []
    edge_i = 0
    for entry in registry.get("entries") or []:
        if not isinstance(entry, dict) or not entry.get("present"):
            continue
        rel = entry.get("artifact_path")
        if not isinstance(rel, str):
            continue
        bridge_path = ROOT / rel.replace("/", "\\") if "\\" not in rel else Path(rel)
        if not bridge_path.is_file():
            bridge_path = ROOT / rel
        if not bridge_path.is_file():
            continue
        rows, _ = build_edges(bridge_path)
        bridge_sources.append(bridge_path.relative_to(ROOT).as_posix() if bridge_path.is_relative_to(ROOT) else str(bridge_path))
        for row in rows:
            key = (str(row.get("src_node_id")), str(row.get("dst_node_id")))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            row = dict(row)
            row["edge_id"] = f"lemma_verse::reg_{edge_i}"
            edge_i += 1
            merged.append(row)
    manifest = {
        "schema": "logos_lemma_verse_edges_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "source_registry": registry_path.relative_to(ROOT).as_posix()
        if registry_path.is_relative_to(ROOT)
        else str(registry_path),
        "bridge_sources_count": len(bridge_sources),
        "edge_count": len(merged),
        "note": "CONTAIN edges from all human-reviewed registry bridges; not morphology-verified.",
    }
    return merged, manifest


def _edges_from_graph_nodes(
    nodes_path: Path,
    *,
    max_edges: int,
    tokens_per_verse: int,
) -> list[dict[str, Any]]:
    if not nodes_path.is_file() or max_edges <= 0:
        return []
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    edge_i = 0
    with nodes_path.open("r", encoding="utf-8") as f:
        for line in f:
            if len(rows) >= max_edges:
                break
            line = line.strip()
            if not line:
                continue
            node = json.loads(line)
            if not isinstance(node, dict):
                continue
            ref = str(node.get("ref") or "")
            corpus = str(node.get("corpus") or "unknown")
            text = str(node.get("text_norm") or "")
            if not ref or not text:
                continue
            tokens = TOK_RE.findall(text)[:tokens_per_verse]
            for tok in tokens:
                if len(rows) >= max_edges:
                    break
                lemma_id = f"lemma:{corpus}:{tok}_heuristic"
                key = (lemma_id, ref)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "schema": "logos_lemma_verse_edge_v1",
                        "edge_id": f"lemma_verse::graph_{edge_i}",
                        "src_node_id": lemma_id,
                        "dst_node_id": ref,
                        "edge_type": "LEMMA_VERSE_HEURISTIC",
                        "weight": 0.35,
                        "hypothesis_tier": "B",
                        "research_only": True,
                        "source": "bible_meaning_graph_nodes_v1",
                    }
                )
                edge_i += 1
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build logos lemma-verse edges v1 (Phase 1+)")
    ap.add_argument("--bridge-json", type=Path, default=DEFAULT_BRIDGE)
    ap.add_argument(
        "--registry-json",
        type=Path,
        default=None,
        help="Merge CONTAIN edges from all present registry bridges (overrides --bridge-json).",
    )
    ap.add_argument("--graph-nodes-jsonl", type=Path, default=DEFAULT_GRAPH_NODES)
    ap.add_argument("--include-graph-heuristic", action="store_true", default=True)
    ap.add_argument("--no-graph-heuristic", action="store_false", dest="include_graph_heuristic")
    ap.add_argument("--graph-max-edges", type=int, default=47)
    ap.add_argument("--graph-tokens-per-verse", type=int, default=2)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument(
        "--corpus-manifest",
        type=Path,
        default=DEFAULT_CORPUS_MANIFEST,
        help="When set and present, drop CONTAIN edges whose dst is not in corpus.",
    )
    ap.add_argument("--no-corpus-filter", action="store_true")
    args = ap.parse_args()

    if args.registry_json:
        reg_path = args.registry_json if args.registry_json.is_absolute() else ROOT / args.registry_json
        rows, manifest = build_edges_from_registry(reg_path)
    else:
        rows, manifest = build_edges(args.bridge_json)
    if args.include_graph_heuristic:
        graph_rows = _edges_from_graph_nodes(
            args.graph_nodes_jsonl,
            max_edges=args.graph_max_edges,
            tokens_per_verse=args.graph_tokens_per_verse,
        )
        rows.extend(graph_rows)
        manifest["graph_heuristic_edges"] = len(graph_rows)
    if not args.no_corpus_filter and args.corpus_manifest.is_file():
        corpus_ids = _corpus_verse_ids(args.corpus_manifest)
        rows, dropped = _filter_edges_to_corpus(rows, corpus_ids)
        if dropped:
            manifest["dropped_not_in_corpus_count"] = len(dropped)
            manifest["dropped_not_in_corpus_sample"] = dropped[:16]
    manifest["edge_count"] = len(rows)
    manifest["note"] = (
        "Bridge proxy + optional corpus graph heuristic tokens; not morphology-verified."
    )
    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else "")
    args.out_jsonl.write_text(text, encoding="utf-8")
    args.manifest_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "edge_count": len(rows), "out": str(args.out_jsonl)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
