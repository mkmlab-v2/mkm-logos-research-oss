#!/usr/bin/env python3
"""Merge bloom chapter shard verse stubs into studio graph_slice (W2+).

Lightweight nodes for verses not yet in primary slice — complements krv_batch corpus expand.
  py scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py --target-canon-pct 35
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

from scripts.lens_context_mesh_v1 import build_hop_index_from_slice  # noqa: E402
from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
STUDIO_SLICE = ROOT / "projects/no1kmedi/public/data/logos_studio/graph_slice_v1.json"
SHARD_DIR = ROOT / "docs/final/artifacts/logos_studio_bloom_shards_v1"
HOP_OUT = ROOT / "docs/final/artifacts/lens_context_mesh_hop_index_logos_v1_latest.json"
STUDIO_HOP = ROOT / "projects/no1kmedi/public/data/logos_studio/context_mesh_hop_index_v1.json"
OUT_REPORT = ROOT / "reports/logos_bloom_chapter_stub_merge_v1_latest.json"

STUB_PREFIX = "bloom_chapter_stub"
VERSE_REF_RE = re.compile(r"^[A-Za-z0-9]+\.\d+\.\d+$")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _verse_refs_in_slice(doc: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for node in doc.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        ref = node.get("ref")
        if isinstance(ref, str) and VERSE_REF_RE.match(ref.strip()):
            refs.add(canonical_verse_ref(ref.strip()))
    return refs


def _stub_id(ref: str) -> str:
    return f"{STUB_PREFIX}::{ref}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--target-canon-pct", type=float, default=35.0)
    ap.add_argument("--canon-denominator", type=int, default=31102)
    ap.add_argument("--slice-json", type=Path, default=SLICE)
    ap.add_argument("--studio-slice-json", type=Path, default=STUDIO_SLICE)
    ap.add_argument("--shard-dir", type=Path, default=SHARD_DIR)
    ap.add_argument("--skip-hop-rebuild", action="store_true")
    args = ap.parse_args()

    if not args.slice_json.is_file():
        print(json.dumps({"ok": False, "error": "slice_missing"}, ensure_ascii=False))
        return 1
    if not args.shard_dir.is_dir():
        print(json.dumps({"ok": False, "error": "shard_dir_missing"}, ensure_ascii=False))
        return 2

    doc = _load_json(args.slice_json)
    existing_refs = _verse_refs_in_slice(doc)
    target_refs = max(1, int(args.canon_denominator * args.target_canon_pct / 100.0))
    if len(existing_refs) >= target_refs:
        report = {
            "schema": "logos_bloom_chapter_stub_merge_v1",
            "ok": True,
            "skipped": True,
            "reason": "slice_already_at_target",
            "existing_verse_refs": len(existing_refs),
            "target_verse_refs": target_refs,
        }
        OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    node_by_id = {str(n["id"]): dict(n) for n in doc.get("nodes") or []}
    edges: list[dict[str, Any]] = list(doc.get("edges") or [])
    seen_edges = {(e["src"], e["dst"], e.get("edge_type") or "link") for e in edges}

    added = 0
    need = target_refs - len(existing_refs)

    for shard_path in sorted(args.shard_dir.glob("*.json")):
        if added >= need:
            break
        shard = _load_json(shard_path)
        for ref in shard.get("verse_refs") or []:
            if added >= need:
                break
            if not isinstance(ref, str):
                continue
            cref = canonical_verse_ref(ref.strip())
            if not VERSE_REF_RE.match(cref) or cref in existing_refs:
                continue
            nid = _stub_id(cref)
            if nid in node_by_id:
                existing_refs.add(cref)
                continue
            node_by_id[nid] = {
                "id": nid,
                "label": cref,
                "ref": cref,
                "kind": "verse",
                "corpus": "bloom_chapter_stub",
                "hub_score": 0.08,
                "bloom_chapter_stub_v1": True,
                "research_only": True,
                "evidence_tier": "hypo_research_only",
            }
            existing_refs.add(cref)
            added += 1
            book = cref.split(".", 1)[0]
            anchor_id = f"canon_book_anchor::{book}"
            if anchor_id in node_by_id:
                key = (anchor_id, nid, "bloom_book_contains")
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"src": anchor_id, "dst": nid, "edge_type": "bloom_book_contains", "weight": 0.3})

    doc["nodes"] = list(node_by_id.values())
    doc["edges"] = edges
    stats = dict(doc.get("stats") or {})
    stats["bloom_chapter_stub_count"] = sum(1 for n in doc["nodes"] if n.get("bloom_chapter_stub_v1"))
    stats["node_count"] = len(doc["nodes"])
    stats["edge_count"] = len(edges)
    doc["stats"] = stats
    doc["bloom_chapter_stub_merge_v1"] = {
        "merged_at_utc": _utc(),
        "added_stubs": added,
        "target_verse_refs": target_refs,
        "research_only": True,
        "send_gate": "HOLD",
    }

    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.slice_json.write_text(text, encoding="utf-8")
    args.studio_slice_json.parent.mkdir(parents=True, exist_ok=True)
    args.studio_slice_json.write_text(text, encoding="utf-8")

    hop_rebuilt = False
    if not args.skip_hop_rebuild and added > 0:
        rel_src = str(args.slice_json.relative_to(ROOT)).replace("\\", "/")
        hop_doc = build_hop_index_from_slice(
            doc,
            lens_id="logos",
            pack_id="lens_pack@logos_showroom",
            source_slice_path=rel_src,
        )
        hop_text = json.dumps(hop_doc, ensure_ascii=False, indent=2) + "\n"
        HOP_OUT.write_text(hop_text, encoding="utf-8")
        STUDIO_HOP.write_text(hop_text, encoding="utf-8")
        hop_rebuilt = True

    report = {
        "schema": "logos_bloom_chapter_stub_merge_v1",
        "ok": True,
        "added_stubs": added,
        "verse_refs_after": len(existing_refs),
        "target_verse_refs": target_refs,
        "hop_rebuilt": hop_rebuilt,
        "reproduce": "py scripts/merge_logos_studio_bloom_chapter_stubs_into_graph_slice_v1.py --target-canon-pct 35",
    }
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
