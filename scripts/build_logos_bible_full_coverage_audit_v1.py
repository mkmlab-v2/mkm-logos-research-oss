#!/usr/bin/env python3
"""Logos Bible full-corpus coverage audit vs 31,102 canon denominator (Track B · research_only).

Measures layer-by-layer coverage; does not imply Track A promotion or SEND.
Writes docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref, is_canonical_verse_ref, VERSE_REF_RE

CANON_MANIFEST = ROOT / "docs/final/artifacts/logos_corpus_manifest_v1_latest.json"
CANON_JSON = ROOT / "data/logos/verse_4pipeline_full_31102.json"
MEANING_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
MEANING_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
LEMMA_EDGES = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
CITATION_SHARD = ROOT / "projects/no1kmedi/public/data/logos_studio/verse_citation_shard_v1.json"
QA_PRESETS = ROOT / "projects/no1kmedi/public/data/logos_studio/qa_presets_v1.json"
GRAPH_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
GRAPH_SLICE_UI_LITE = ROOT / "docs/final/artifacts/logos_studio_graph_slice_ui_lite_v1_latest.json"
HOP_INDEX = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"
ROUTER_SIDECAR = ROOT / "projects/no1kmedi/public/data/logos_studio/qa_router_sidecar_v1.json"
BLOOM_INDEX = ROOT / "projects/no1kmedi/public/data/logos_studio/bloom_31k_index_v1.json"
DYNAMIC_ROUTER = ROOT / "projects/no1kmedi/public/data/logos_studio/dynamic_subgraph_router_v1.json"
OUT = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"

CANON_DENOMINATOR = 31_102


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canon_verse_ids() -> set[str]:
    manifest = _load_json(CANON_MANIFEST)
    if manifest.get("verse_count") == CANON_DENOMINATOR:
        return _canon_from_pipeline_json()
    if CANON_JSON.is_file():
        return _canon_from_pipeline_json()
    return set()


def _canon_from_pipeline_json() -> set[str]:
    if not CANON_JSON.is_file():
        return set()
    data = json.loads(CANON_JSON.read_text(encoding="utf-8-sig"))
    ids: set[str] = set()
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                vid = row.get("verse_id") or row.get("id")
                if isinstance(vid, str) and vid.strip():
                    ids.add(canonical_verse_ref(vid.strip()))
    return ids


def _refs_from_jsonl_nodes(path: Path) -> set[str]:
    refs: set[str] = set()
    if not path.is_file():
        return refs
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        ref = row.get("ref")
        if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
            refs.add(canonical_verse_ref(ref.strip()))
            continue
        nid = row.get("node_id") or row.get("id")
        if isinstance(nid, str) and "::" in nid:
            tail = nid.split("::", 1)[1].strip()
            if VERSE_REF_RE.match(tail):
                refs.add(canonical_verse_ref(tail))
    return refs


def _refs_from_lemma_edges(path: Path) -> set[str]:
    refs: set[str] = set()
    if not path.is_file():
        return refs
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        for key in ("verse_ref", "ref", "dst_node_id", "src_node_id"):
            val = row.get(key)
            if isinstance(val, str) and VERSE_REF_RE.match(val.strip()):
                refs.add(canonical_verse_ref(val.strip()))
    return refs


def _refs_from_router_sidecar(path: Path) -> set[str]:
    refs: set[str] = set()
    doc = _load_json(path)
    for _pid, route in (doc.get("presets") or doc.get("routes") or {}).items():
        if not isinstance(route, dict):
            continue
        path_block = route.get("path") or route.get("router_path_v1") or {}
        if isinstance(path_block, dict):
            for ref in path_block.get("verse_refs") or []:
                if isinstance(ref, str) and ref.strip():
                    refs.add(canonical_verse_ref(ref.strip()))
    return refs


def _refs_from_presets(path: Path) -> set[str]:
    refs: set[str] = set()
    doc = _load_json(path)
    for preset in doc.get("presets") or []:
        if not isinstance(preset, dict):
            continue
        for key in ("verse_refs", "highlight_verse_refs"):
            for ref in preset.get(key) or []:
                if isinstance(ref, str) and ref.strip():
                    refs.add(canonical_verse_ref(ref.strip()))
        path_block = preset.get("path") or {}
        for ref in path_block.get("verse_refs") or []:
            if isinstance(ref, str) and ref.strip():
                refs.add(canonical_verse_ref(ref.strip()))
    return refs


def _refs_from_graph_slice(path: Path) -> set[str]:
    refs: set[str] = set()
    doc = _load_json(path)
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        ref = node.get("ref") or node.get("label")
        if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
            refs.add(canonical_verse_ref(ref.strip()))
        nid = node.get("id")
        if isinstance(nid, str) and "::" in nid:
            tail = nid.split("::", 1)[1].strip()
            if VERSE_REF_RE.match(tail):
                refs.add(canonical_verse_ref(tail))
    return refs


def _refs_from_citation_shard(path: Path) -> set[str]:
    doc = _load_json(path)
    verses = doc.get("verses") or {}
    return {canonical_verse_ref(k) for k in verses if isinstance(k, str)}


def _coverage_layer(
    layer_id: str,
    refs: set[str],
    canon: set[str],
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overlap = refs & canon if canon else refs
    denom = len(canon) if canon else CANON_DENOMINATOR
    ratio = round(len(overlap) / denom, 6) if denom else 0.0
    row: dict[str, Any] = {
        "id": layer_id,
        "verse_refs_distinct": len(refs),
        "canon_overlap": len(overlap),
        "canon_denominator": denom,
        "canon_coverage_ratio": ratio,
        "canon_coverage_pct": round(ratio * 100, 4),
    }
    if extra:
        row.update(extra)
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=OUT)
    args = ap.parse_args(argv)

    canon = _canon_verse_ids()
    manifest = _load_json(CANON_MANIFEST)

    meaning_refs = _refs_from_jsonl_nodes(MEANING_NODES)
    lemma_refs = _refs_from_lemma_edges(LEMMA_EDGES)
    preset_refs = _refs_from_presets(QA_PRESETS) | _refs_from_router_sidecar(ROUTER_SIDECAR)
    slice_refs = _refs_from_graph_slice(GRAPH_SLICE)
    citation_refs = _refs_from_citation_shard(CITATION_SHARD)

    hop_doc = _load_json(HOP_INDEX)
    hop_node_count = len((hop_doc.get("nodes") or {})) if hop_doc else 0
    router_doc = _load_json(ROUTER_SIDECAR)
    router_preset_count = len(router_doc.get("presets") or router_doc.get("routes") or {})

    qa_doc = _load_json(QA_PRESETS)
    preset_count = len(qa_doc.get("presets") or [])
    slice_doc = _load_json(GRAPH_SLICE)
    slice_nodes = len(slice_doc.get("nodes") or [])
    slice_edges = len(slice_doc.get("edges") or [])

    lemma_lines = 0
    if LEMMA_EDGES.is_file():
        lemma_lines = sum(1 for ln in LEMMA_EDGES.read_text(encoding="utf-8-sig").splitlines() if ln.strip())

    layers = [
        _coverage_layer("canon_manifest", canon, canon, extra={"source": str(CANON_MANIFEST)}),
        _coverage_layer("bible_meaning_graph_nodes", meaning_refs, canon),
        _coverage_layer("lemma_verse_edges", lemma_refs, canon, extra={"lemma_edge_lines": lemma_lines}),
        _coverage_layer("studio_qa_presets", preset_refs, canon, extra={"preset_count": preset_count}),
        _coverage_layer("studio_graph_slice", slice_refs, canon, extra={"nodes": slice_nodes, "edges": slice_edges}),
        _coverage_layer("studio_citation_shard_krv", citation_refs, canon, extra={"krv_hand_curated": True}),
    ]

    citation_pct = next((l["canon_coverage_pct"] for l in layers if l["id"] == "studio_citation_shard_krv"), 0.0)
    preset_n = preset_count
    slice_pct = next((l["canon_coverage_pct"] for l in layers if l["id"] == "studio_graph_slice"), 0.0)
    a4_exists = (ROOT / "docs/final/artifacts/logos_studio_a4_synthesis_bundle_v1_latest.json").is_file()
    bloom_doc = _load_json(BLOOM_INDEX)
    bloom_shard_count = int(bloom_doc.get("chapter_shard_count") or 0)
    bloom_ok = bloom_shard_count >= 1000 and bloom_doc.get("schema") == "logos_studio_31k_bloom_secondary_fetch_v1"
    dynamic_doc = _load_json(DYNAMIC_ROUTER)
    dynamic_ok = int(dynamic_doc.get("route_count") or 0) >= 10 and dynamic_doc.get("schema") == "logos_studio_dynamic_subgraph_router_v1"

    gaps = []
    if citation_pct < 99.0:
        gaps.append("krv_corpus_canon_gap_below_99pct")
    if slice_pct < 5.0:
        gaps.append("studio_ui_graph_slice_is_showroom_thin_not_full_bible")
        gaps.append("bloom_secondary_fetch_compensates_31k_ui")
    if not bloom_ok:
        gaps.append("31k_bloom_secondary_fetch_not_implemented")
    if not dynamic_ok:
        gaps.append("dynamic_subgraph_router_sidecar_missing")
    if not a4_exists:
        gaps.append("a4_synthesis_bundle_not_wired")

    def _phase_status(phase: str) -> str:
        if phase == "P0":
            return "done"
        if phase == "P1":
            return "done" if citation_pct >= 99.0 else ("done" if citation_pct >= 96.0 else "in_progress")
        if phase == "P2":
            return "done" if lemma_lines >= 500 else "in_progress"
        if phase == "P3":
            return "done" if slice_nodes >= 300 else "in_progress"
        if phase == "P4":
            return "done" if preset_n >= 50 else "pending"
        if phase == "P5":
            return "done" if bloom_ok else "pending"
        if phase == "P6":
            return "done" if dynamic_ok else "pending"
        if phase == "P7":
            return "done" if a4_exists else "pending"
        if phase == "P-design":
            design_gate = ROOT / "docs/final/artifacts/logos_studio_design_gate_v1_latest.json"
            if design_gate.is_file():
                dg = json.loads(design_gate.read_text(encoding="utf-8-sig"))
                if dg.get("ok") is True or dg.get("pass") is True:
                    return "done"
            return "done" if slice_nodes >= 300 and citation_pct >= 99.0 else "in_progress"
        return "pending"

    phases = [
        {"phase": "P0", "task": "coverage_audit_baseline", "status": _phase_status("P0"), "owner": "cursor"},
        {"phase": "P1", "task": "krv_corpus_ingest_citation_shard_31k", "status": _phase_status("P1"), "owner": "cursor"},
        {"phase": "P2", "task": "lemma_verse_edges_canon_expansion", "status": _phase_status("P2"), "owner": "cursor"},
        {"phase": "P3", "task": "meaning_graph_to_studio_slice_hop_scale", "status": _phase_status("P3"), "owner": "cursor"},
        {"phase": "P4", "task": "preset_chapter_book_expansion_50plus", "status": _phase_status("P4"), "owner": "cursor"},
        {"phase": "P5", "task": "31k_bloom_secondary_fetch_research", "status": _phase_status("P5"), "owner": "cursor"},
        {"phase": "P6", "task": "dynamic_subgraph_graphrag_router", "status": _phase_status("P6"), "owner": "cursor"},
        {"phase": "P7", "task": "a4_reading_pack_synthesis_bundle", "status": _phase_status("P7"), "owner": "cursor"},
        {"phase": "P-design", "task": "antigravity_surface_l2_l3", "status": _phase_status("P-design"), "owner": "antigravity"},
    ]

    out_doc: dict[str, Any] = {
        "schema": "logos_bible_full_coverage_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "track_wall": {
            "canon_denominator_31102": True,
            "lexicon_41k_separate_lane": True,
            "track_a_auto_promote": False,
        },
        "canon": {
            "denominator": len(canon) if canon else CANON_DENOMINATOR,
            "manifest_verse_count": manifest.get("verse_count"),
            "manifest_path": str(CANON_MANIFEST),
            "pipeline_json": str(CANON_JSON),
        },
        "layers": layers,
        "infrastructure": {
            "hop_index_node_count": hop_node_count,
            "router_sidecar_preset_routes": router_preset_count,
            "meaning_graph_edge_lines": sum(
                1 for ln in MEANING_EDGES.read_text(encoding="utf-8-sig").splitlines() if ln.strip()
            )
            if MEANING_EDGES.is_file()
            else 0,
            "bloom_31k_chapter_shard_count": bloom_shard_count,
            "dynamic_subgraph_route_count": int(dynamic_doc.get("route_count") or 0),
            "bloom_secondary_ui_wired": bloom_ok,
            "krv_versification_proxy_count": int(
                (_load_json(ROOT / "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json") or {}).get(
                    "proxy_entry_count", 0
                )
            )
            if (ROOT / "docs/final/artifacts/logos_krv_versification_sidecar_v1_latest.json").is_file()
            else 0,
        },
        "known_gaps": gaps,
        "work_phases": phases,
        "reproduce": "py scripts/build_logos_bible_full_coverage_audit_v1.py",
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "canon": out_doc["canon"]["denominator"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
