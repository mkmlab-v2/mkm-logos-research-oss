#!/usr/bin/env python3
"""Inject router verse stub nodes into graph slice for Studio preset coverage (B1a).

Maps API/router ``verse_refs`` missing from ``graph_slice`` to ``showroom_router_stub_verse::*``
nodes linked to the preset's first mapped spine node. Research-only · NON_GATING.

Reproduce:
  py scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py
  py scripts/check_logos_studio_graph_slice_router_coverage_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from lens_context_mesh_v1 import build_hop_index_from_slice  # noqa: E402
from logos_studio_preset_graph_helpers_v1 import verse_node_ids  # noqa: E402
from logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_ROUTER = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"
DEFAULT_HOP_OUT = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"
DEFAULT_STUDIO_HOP_MIRROR = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"

STUDIO_PRESET_ALLOWLIST = (
    "job_job_suffering_reason",
    "isaiah_youtube_spine_v1",
    "bigset_topic_nephilim",
    "topic_ezra_1_anchor",
)

STUB_PREFIX = "showroom_router_stub_verse::"
ANCHOR_PREFIX = "showroom_router_stub_anchor::"


def _ensure_preset_anchor_node(
    preset_id: str,
    node_by_id: dict[str, dict[str, Any]],
) -> str:
    nid = f"{ANCHOR_PREFIX}{preset_id}"
    if nid not in node_by_id:
        node_by_id[nid] = {
            "id": nid,
            "label": preset_id,
            "kind": "preset_anchor",
            "hub_score": 0.25,
            "router_preset_anchor": True,
            "research_only": True,
            "evidence_tier": "hypo_research_only",
        }
    return nid


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _refs_in_slice(graph_doc: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for n in graph_doc.get("nodes") or []:
        for raw in (n.get("ref"), n.get("label")):
            c = canonical_verse_ref(str(raw or ""))
            if c:
                out.add(c)
    return out


def _stub_node_id(ref: str) -> str:
    return f"{STUB_PREFIX}{canonical_verse_ref(ref)}"


def _collect_preset_verse_refs(router_doc: dict[str, Any], preset_ids: set[str]) -> dict[str, list[str]]:
    presets = router_doc.get("presets") or {}
    out: dict[str, list[str]] = {}
    for pid in preset_ids:
        block = presets.get(pid) or {}
        rp = block.get("router_path_v1") or block
        refs = [canonical_verse_ref(str(r)) for r in (rp.get("verse_refs") or [])]
        refs = [r for r in refs if r]
        if refs:
            out[pid] = list(dict.fromkeys(refs))
    return out


def _anchor_node_id(graph_doc: dict[str, Any], router_doc: dict[str, Any], preset_id: str) -> str | None:
    block = (router_doc.get("presets") or {}).get(preset_id) or {}
    rp = block.get("router_path_v1") or block
    node_ids = [str(x) for x in (rp.get("node_ids") or []) if x]
    slice_ids = {str(n.get("id")) for n in graph_doc.get("nodes") or []}
    for nid in node_ids:
        if nid in slice_ids:
            return nid
    mapped = verse_node_ids(graph_doc, set(_collect_preset_verse_refs(router_doc, {preset_id}).get(preset_id) or []))
    return mapped[0] if mapped else None


def patch_slice(
    graph_doc: dict[str, Any],
    router_doc: dict[str, Any],
    preset_ids: set[str],
) -> tuple[dict[str, Any], list[str]]:
    slice_refs = _refs_in_slice(graph_doc)
    preset_refs = _collect_preset_verse_refs(router_doc, preset_ids)
    missing: set[str] = set()
    for refs in preset_refs.values():
        for ref in refs:
            if ref not in slice_refs:
                missing.add(ref)

    if not missing:
        return graph_doc, []

    node_by_id = {str(n["id"]): dict(n) for n in graph_doc.get("nodes") or []}
    edge_key = lambda e: (e["src"], e["dst"], e.get("edge_type") or "link")  # noqa: E731
    edges: list[dict[str, Any]] = list(graph_doc.get("edges") or [])
    seen_edges = {edge_key(e) for e in edges}

    anchor_by_ref: dict[str, str] = {}
    for preset_id, refs in preset_refs.items():
        anchor = _anchor_node_id(graph_doc, router_doc, preset_id)
        if not anchor:
            anchor = _ensure_preset_anchor_node(preset_id, node_by_id)
        for ref in refs:
            if ref in slice_refs or ref not in missing:
                continue
            if ref not in anchor_by_ref:
                anchor_by_ref[ref] = anchor

    added: list[str] = []
    for ref in sorted(missing):
        nid = _stub_node_id(ref)
        if nid in node_by_id:
            continue
        anchor = anchor_by_ref.get(ref)
        if not anchor:
            continue
        node_by_id[nid] = {
            "id": nid,
            "label": ref,
            "ref": ref,
            "kind": "verse",
            "hub_score": 0.18,
            "router_verse_stub": True,
            "research_only": True,
            "evidence_tier": "hypo_research_only",
        }
        for src, dst in ((anchor, nid), (nid, anchor)):
            key = (src, dst, "router_verse_stub")
            if key in seen_edges:
                continue
            seen_edges.add(key)
            edges.append(
                {
                    "src": src,
                    "dst": dst,
                    "edge_type": "router_verse_stub",
                    "weight": 0.35,
                }
            )
        added.append(ref)
        slice_refs.add(ref)

    if not added:
        return graph_doc, []

    kind_counts: dict[str, int] = defaultdict(int)
    nodes_out = list(node_by_id.values())
    for n in nodes_out:
        kind_counts[str(n.get("kind") or "other")] += 1

    doc = dict(graph_doc)
    doc["nodes"] = nodes_out
    doc["edges"] = edges
    stats = dict(doc.get("stats") or {})
    stats["node_count"] = len(nodes_out)
    stats["edge_count"] = len(edges)
    stats["kinds"] = dict(kind_counts)
    stats["router_verse_stub_count"] = sum(1 for n in nodes_out if n.get("router_verse_stub"))
    doc["stats"] = stats
    patch_meta = dict(doc.get("router_verse_stub_patch_v1") or {})
    patch_meta.update(
        {
            "patched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "added_refs": added,
            "preset_allowlist": sorted(preset_ids),
        }
    )
    doc["router_verse_stub_patch_v1"] = patch_meta
    return doc, added


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--hop-out-json", type=Path, default=DEFAULT_HOP_OUT)
    ap.add_argument("--studio-hop-mirror", type=Path, default=DEFAULT_STUDIO_HOP_MIRROR)
    ap.add_argument("--no-hop-rebuild", action="store_true")
    ap.add_argument("--no-studio-hop-mirror", action="store_true")
    ap.add_argument(
        "--all-presets",
        action="store_true",
        help="Patch every preset in router sidecar (default: studio embed allowlist only)",
    )
    args = ap.parse_args()

    if not args.slice_json.is_file():
        print(json.dumps({"ok": False, "error": f"slice missing: {args.slice_json}"}))
        return 2
    if not args.router_json.is_file():
        print(json.dumps({"ok": False, "error": f"router missing: {args.router_json}"}))
        return 2

    graph_doc = _load(args.slice_json)
    router_doc = _load(args.router_json)
    preset_ids = set(router_doc.get("presets") or {})
    if not args.all_presets:
        preset_ids &= set(STUDIO_PRESET_ALLOWLIST)

    patched, added = patch_slice(graph_doc, router_doc, preset_ids)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(patched, ensure_ascii=False, indent=2) + "\n"
    args.out_json.write_text(text, encoding="utf-8")

    hop_written = False
    if added and not args.no_hop_rebuild:
        rel_src = str(args.out_json.relative_to(ROOT)).replace("\\", "/")
        hop_doc = build_hop_index_from_slice(
            patched,
            lens_id="logos",
            pack_id="lens_pack@logos_showroom",
            source_slice_path=rel_src,
        )
        hop_text = json.dumps(hop_doc, ensure_ascii=False, indent=2) + "\n"
        args.hop_out_json.parent.mkdir(parents=True, exist_ok=True)
        args.hop_out_json.write_text(hop_text, encoding="utf-8")
        hop_written = True
        if not args.no_studio_hop_mirror:
            args.studio_hop_mirror.parent.mkdir(parents=True, exist_ok=True)
            args.studio_hop_mirror.write_text(hop_text, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "schema": "logos_studio_graph_slice_router_verse_stub_patch_v1",
                "added_refs": added,
                "added_count": len(added),
                "preset_count": len(preset_ids),
                "out": str(args.out_json.relative_to(ROOT)).replace("\\", "/"),
                "hop_rebuilt": hop_written,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
