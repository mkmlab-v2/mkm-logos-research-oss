#!/usr/bin/env python3
"""Build Job 5-stage topology seed bundle from reading-pack slice ([HYPO], B-track).

Reproducible:
  py scripts/build_showroom_job_topology_seed_bundle_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.showroom_job_topology_seed_v1 import build_job_seed_bundle  # noqa: E402
from scripts.core.showroom_router_psalm_seed_v1 import (  # noqa: E402
    append_router_psalm_stubs,
    collect_psalm_refs_from_presets,
    default_psalm_router_refs,
)

DEFAULT_JOB_SLICE = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_job_reading_pack_slice_v1.json"
)
DEFAULT_OUT = ROOT / "docs/final/artifacts/showroom_job_topology_seed_bundle_v1_latest.json"
DEFAULT_PRESETS = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"

from scripts.core.enrich_bible_meaning_graph_cosmic_anchor_v1 import (  # noqa: E402
    merge_edges_jsonl,
    merge_jsonl,
)


def materialize_to_meaning_graph(bundle: dict, *, nodes_path: Path, edges_path: Path) -> dict[str, int]:
    node_rows: list[dict] = []
    for n in bundle.get("nodes") or []:
        kind = n.get("kind")
        if kind == "verse":
            node_rows.append(
                {
                    "schema": "showroom_job_verse_node_v1",
                    "node_id": n["id"],
                    "ref": n.get("ref"),
                    "kind": "verse",
                    "source_track": "B",
                    "research_only": True,
                    "hypothesis_class": "HYPO",
                    "stage_id": n.get("stage_id"),
                }
            )
        elif kind == "stage":
            node_rows.append(
                {
                    "schema": "showroom_job_stage_node_v1",
                    "node_id": n["id"],
                    "kind": "stage",
                    "label": n.get("label"),
                    "stage_id": n.get("stage_id"),
                    "source_track": "B",
                    "research_only": True,
                    "hypothesis_class": "HYPO",
                }
            )
    edge_rows: list[dict] = []
    for e in bundle.get("edges") or []:
        edge_rows.append(
            {
                "schema": "bible_meaning_graph_edge_v1",
                "src_node_id": e["src"],
                "dst_node_id": e["dst"],
                "edge_type": e.get("edge_type") or "link",
                "weight": float(e.get("weight") or 0.5),
                "source_track": "B",
                "research_only": True,
            }
        )
    return {
        "nodes_appended": merge_jsonl(nodes_path, node_rows, key_field="node_id"),
        "edges_appended": merge_edges_jsonl(edges_path, edge_rows),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--job-slice-json", type=Path, default=DEFAULT_JOB_SLICE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--merge-meaning-graph", action="store_true")
    ap.add_argument("--include-psalm-stubs", action="store_true")
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--graph-nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--graph-edges-jsonl", type=Path, default=DEFAULT_EDGES)
    args = ap.parse_args()

    if not args.job_slice_json.is_file():
        print(f"FAIL: missing {args.job_slice_json}", file=sys.stderr)
        return 1

    job_doc = json.loads(args.job_slice_json.read_text(encoding="utf-8"))
    bundle = build_job_seed_bundle(job_doc)
    if args.include_psalm_stubs:
        presets_doc = None
        if args.presets_json.is_file():
            presets_doc = json.loads(args.presets_json.read_text(encoding="utf-8"))
        psalm_refs = collect_psalm_refs_from_presets(presets_doc) or default_psalm_router_refs()
        bundle = append_router_psalm_stubs(bundle, psalm_refs)
    bundle["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle["source_job_slice"] = str(args.job_slice_json.relative_to(ROOT)).replace("\\", "/")
    bundle["reproducible_command"] = "py scripts/build_showroom_job_topology_seed_bundle_v1.py"

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.out_json} stages={bundle['stage_count']} "
        f"verses={bundle['verse_ref_count']} nodes={len(bundle['nodes'])} edges={len(bundle['edges'])}"
    )

    if args.merge_meaning_graph:
        stats = materialize_to_meaning_graph(
            bundle, nodes_path=args.graph_nodes_jsonl, edges_path=args.graph_edges_jsonl
        )
        print(f"MERGE meaning_graph nodes+={stats['nodes_appended']} edges+={stats['edges_appended']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
