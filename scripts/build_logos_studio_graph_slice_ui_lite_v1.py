#!/usr/bin/env python3
"""Build UI-lite graph_slice + hop_index for browser (LOD). Full slice stays in artifact.

  py scripts/build_logos_studio_graph_slice_ui_lite_v1.py
  py scripts/build_logos_studio_graph_slice_ui_lite_v1.py --max-nodes 900
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.lens_context_mesh_v1 import build_hop_index_from_slice  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402
from scripts.patch_logos_studio_graph_slice_router_verse_stubs_v1 import (  # noqa: E402
    STUDIO_PRESET_ALLOWLIST,
)

FULL_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
ROUTER = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"
OUT_SLICE = ROOT / "docs/final/artifacts/logos_studio_graph_slice_ui_lite_v1_latest.json"
OUT_HOP = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_ui_lite_v1_latest.json"
STUDIO_SLICE = ROOT / "projects/no1kmedi/public/data/logos_studio/graph_slice_v1.json"
STUDIO_HOP = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"
OUT_REPORT = ROOT / "reports/logos_studio_graph_slice_ui_lite_v1_latest.json"

VERSE_REF_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _preset_seed_ids(full: dict[str, Any], presets_doc: dict[str, Any]) -> set[str]:
    node_by_ref: dict[str, str] = {}
    for n in full.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        ref = n.get("ref")
        if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
            node_by_ref[canonical_verse_ref(ref.strip())] = str(n.get("id"))
    seeds: set[str] = set()
    for preset in presets_doc.get("presets") or []:
        if not isinstance(preset, dict):
            continue
        for nid in preset.get("highlight_node_ids") or []:
            if isinstance(nid, str) and nid.strip():
                seeds.add(nid.strip())
        path_block = preset.get("path") or preset.get("router_path_v1") or {}
        if isinstance(path_block, dict):
            for ref in path_block.get("verse_refs") or []:
                if isinstance(ref, str):
                    cref = canonical_verse_ref(ref.strip())
                    if cref in node_by_ref:
                        seeds.add(node_by_ref[cref])
    return seeds


def _embed_demo_pin_ids(
    full_doc: dict[str, Any],
    presets_doc: dict[str, Any],
    router_doc: dict[str, Any] | None,
) -> set[str]:
    """Studio embed allowlist verse_refs must survive ui_lite cap (Playwright smoke)."""
    node_by_ref: dict[str, str] = {}
    for n in full_doc.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        ref = n.get("ref")
        if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
            node_by_ref[canonical_verse_ref(ref.strip())] = str(n.get("id"))

    pins: set[str] = set()
    presets_by_id = {
        str(p.get("id")): p for p in presets_doc.get("presets") or [] if isinstance(p, dict) and p.get("id")
    }
    router_presets = (router_doc or {}).get("presets") or {}

    for preset_id in STUDIO_PRESET_ALLOWLIST:
        refs: list[str] = []
        block = router_presets.get(preset_id) or {}
        rp = block.get("router_path_v1") or block
        if isinstance(rp, dict):
            refs.extend(str(r) for r in (rp.get("verse_refs") or []))
        preset = presets_by_id.get(preset_id) or {}
        prp = preset.get("router_path_v1") or {}
        if isinstance(prp, dict):
            refs.extend(str(r) for r in (prp.get("verse_refs") or []))
        for raw in refs:
            cref = canonical_verse_ref(raw.strip())
            if cref in node_by_ref:
                pins.add(node_by_ref[cref])
        for nid in rp.get("node_ids") or [] if isinstance(rp, dict) else []:
            if isinstance(nid, str) and nid.strip():
                pins.add(nid.strip())
    return pins


def build_lite(
    full_doc: dict[str, Any],
    presets_doc: dict[str, Any],
    *,
    max_nodes: int,
    router_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    nodes_in = [dict(n) for n in full_doc.get("nodes") or [] if isinstance(n, dict)]
    edges_in = [dict(e) for e in full_doc.get("edges") or [] if isinstance(e, dict)]
    node_by_id = {str(n["id"]): n for n in nodes_in if n.get("id")}

    keep: set[str] = set()
    for n in nodes_in:
        nid = str(n.get("id") or "")
        kind = str(n.get("kind") or "")
        if not nid:
            continue
        if n.get("book_anchor") or kind in ("theme", "regime"):
            keep.add(nid)
        if n.get("hub_score", 0) and float(n.get("hub_score") or 0) >= 0.18:
            keep.add(nid)

    pin_ids = _embed_demo_pin_ids(full_doc, presets_doc, router_doc)
    for sid in _preset_seed_ids(full_doc, presets_doc):
        keep.add(sid)

    # 1-hop neighbors from seeds
    frontier = list(keep)
    for e in edges_in:
        src, dst = str(e.get("src") or ""), str(e.get("dst") or "")
        if src in keep or dst in keep:
            if src:
                keep.add(src)
            if dst:
                keep.add(dst)

    if len(keep) < max_nodes:
        verses = [
            n
            for n in nodes_in
            if str(n.get("kind") or "") == "verse" and str(n.get("id")) not in keep
        ]
        verses.sort(key=lambda n: (-float(n.get("hub_score") or 0), str(n.get("id"))))
        for n in verses:
            if len(keep) >= max_nodes:
                break
            keep.add(str(n["id"]))

    if len(keep) > max_nodes:
        trim_pool = keep - pin_ids
        ranked = sorted(
            trim_pool,
            key=lambda nid: (
                0 if node_by_id.get(nid, {}).get("book_anchor") else 1,
                -float(node_by_id.get(nid, {}).get("hub_score") or 0),
                nid,
            ),
        )
        budget = max(0, max_nodes - len(pin_ids))
        keep = pin_ids | set(ranked[:budget])

    nodes_out = [node_by_id[nid] for nid in keep if nid in node_by_id]
    kept = set(keep)
    edges_out = [
        e
        for e in edges_in
        if str(e.get("src") or "") in kept and str(e.get("dst") or "") in kept
    ]

    kind_counts: dict[str, int] = defaultdict(int)
    for n in nodes_out:
        kind_counts[str(n.get("kind") or "other")] += 1

    return {
        **{k: v for k, v in full_doc.items() if k not in ("nodes", "edges", "stats")},
        "schema_version": "logos_studio_graph_slice_ui_lite_v1",
        "ui_lite_v1": True,
        "full_slice_pointer": "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
        "nodes": nodes_out,
        "edges": edges_out,
        "stats": {
            "node_count": len(nodes_out),
            "edge_count": len(edges_out),
            "kinds": dict(kind_counts),
            "full_node_count": len(nodes_in),
            "lite_cap": max_nodes,
        },
        "disclaimer": full_doc.get("disclaimer"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full-slice-json", type=Path, default=FULL_SLICE)
    ap.add_argument("--presets-json", type=Path, default=PRESETS)
    ap.add_argument("--max-nodes", type=int, default=900)
    ap.add_argument("--write-studio-public", action="store_true", default=True)
    args = ap.parse_args()

    if not args.full_slice_json.is_file():
        print(json.dumps({"ok": False, "error": "full_slice_missing"}, ensure_ascii=False))
        return 1

    full_doc = _load(args.full_slice_json)
    presets_doc = _load(args.presets_json) if args.presets_json.is_file() else {"presets": []}
    router_doc = _load(ROUTER) if ROUTER.is_file() else None
    lite_doc = build_lite(full_doc, presets_doc, max_nodes=args.max_nodes, router_doc=router_doc)
    lite_doc["generated_at_utc"] = _utc()
    lite_doc["research_only"] = True
    lite_doc["send_gate"] = "HOLD"

    hop_doc = build_hop_index_from_slice(
        lite_doc,
        lens_id="logos",
        pack_id="lens_pack@logos_showroom_ui_lite",
        source_slice_path="docs/final/artifacts/logos_studio_graph_slice_ui_lite_v1_latest.json",
    )

    text = json.dumps(lite_doc, ensure_ascii=False, indent=2) + "\n"
    OUT_SLICE.write_text(text, encoding="utf-8")
    OUT_HOP.write_text(json.dumps(hop_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_studio_public:
        STUDIO_SLICE.parent.mkdir(parents=True, exist_ok=True)
        STUDIO_SLICE.write_text(text, encoding="utf-8")
        STUDIO_HOP.write_text(json.dumps(hop_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    full_nodes = len(full_doc.get("nodes") or [])
    lite_nodes = len(lite_doc.get("nodes") or [])
    report = {
        "schema": "logos_studio_graph_slice_ui_lite_v1",
        "ok": True,
        "full_nodes": full_nodes,
        "lite_nodes": lite_nodes,
        "lite_edges": len(lite_doc.get("edges") or []),
        "max_nodes": args.max_nodes,
        "reproduce": "py scripts/build_logos_studio_graph_slice_ui_lite_v1.py",
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
