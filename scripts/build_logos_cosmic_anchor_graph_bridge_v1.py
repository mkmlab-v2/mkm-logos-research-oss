#!/usr/bin/env python3
"""ADV-3 — Link 300 cosmic anchors to GraphRAG lemma/themed/meaning graph (HYPO).

Does NOT modify batch anchors or gematria_bridge_v1 kernel.

Reproducible:
  py scripts/build_logos_cosmic_anchor_graph_bridge_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BATCH_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1"
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_batch_v1_manifest_latest.json"
LEMMA = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
GRAPH_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
MKMLIFE_BATCH = ROOT / "projects/mkm/mkm-life/public/data/logos_cosmic_anchor_batch_v1"
OUT = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"

from scripts.core.logos_cosmic_anchor_graph_bridge_v1 import (
    build_narrative_path_samples,
    build_resonance_edges,
    link_anchor,
    load_lemma_index,
    load_meaning_graph,
    load_themed_bridge_index,
)


def build_report(
    *,
    batch_dir: Path = BATCH_DIR,
    manifest_path: Path = MANIFEST,
    lemma_path: Path = LEMMA,
    nodes_path: Path = NODES,
    edges_path: Path = EDGES,
    graph_bundle_path: Path = GRAPH_BUNDLE,
) -> dict[str, Any]:
    generated_at_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stems = sorted(manifest.get("paths", {}).keys())

    lemma_index = load_lemma_index(lemma_path)
    ref_to_node, graph_adj = load_meaning_graph(nodes_path, edges_path)
    themed_paths = sorted((ROOT / "docs/final/artifacts").glob("logos_concept_bridge_themed_*_v1_latest.json"))
    verse_to_themes = load_themed_bridge_index(themed_paths)

    linked: list[dict[str, Any]] = []
    for stem in stems:
        anchor = json.loads((batch_dir / f"{stem}.json").read_text(encoding="utf-8"))
        linked.append(
            link_anchor(
                anchor,
                file_stem=stem,
                lemma_index=lemma_index,
                ref_to_node=ref_to_node,
                graph_adj=graph_adj,
                verse_to_themes=verse_to_themes,
            )
        )

    manifest_stem_set = set(stems)
    linked_manifest = list(linked)
    if MKMLIFE_BATCH.is_dir():
        for path in sorted(MKMLIFE_BATCH.glob("*.json")):
            stem = path.stem
            if stem in manifest_stem_set:
                continue
            anchor = json.loads(path.read_text(encoding="utf-8"))
            linked.append(
                link_anchor(
                    anchor,
                    file_stem=stem,
                    lemma_index=lemma_index,
                    ref_to_node=ref_to_node,
                    graph_adj=graph_adj,
                    verse_to_themes=verse_to_themes,
                )
            )

    resonance_edges = build_resonance_edges(linked_manifest, top_k=3)
    narrative_samples = build_narrative_path_samples(linked, resonance_edges)

    lemma_hit_anchors = sum(1 for row in linked_manifest if row["lemma_edge_count"] > 0)
    themed_hit_anchors = sum(1 for row in linked_manifest if row["themed_bridge_ids"])
    graph_hit_anchors = sum(1 for row in linked_manifest if row["meaning_graph_edge_count"] > 0)

    bundle = {}
    if graph_bundle_path.is_file():
        bundle = json.loads(graph_bundle_path.read_text(encoding="utf-8"))

    return {
        "schema": "logos_cosmic_anchor_graph_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": generated_at_utc,
        "hypothesis_class": "HYPO",
        "research_only": True,
        "non_gating": True,
        "forbidden_synthesis": True,
        "track_a_blocked": True,
        "materialize_batch": False,
        "kernel_recipe_id": "gematria_bridge_v1",
        "graph_bundle_path": graph_bundle_path.relative_to(ROOT).as_posix() if bundle else None,
        "graph_bundle_nodes": (bundle.get("graph_files") or {}).get("nodes_line_count"),
        "anchor_count": len(linked_manifest),
        "summary": {
            "lemma_hit_anchors": lemma_hit_anchors,
            "themed_bridge_hit_anchors": themed_hit_anchors,
            "meaning_graph_hit_anchors": graph_hit_anchors,
            "resonance_edge_count": len(resonance_edges),
            "narrative_sample_count": len(narrative_samples),
            "themed_bridge_files": len(themed_paths),
            "narrative_supplemental_stem_count": len(linked) - len(linked_manifest),
        },
        "resonance_edges": resonance_edges[:500],
        "narrative_path_samples": narrative_samples,
        "per_anchor": linked_manifest,
        "disclaimer_ko": (
            "[HYPO] Cosmic anchor ↔ GraphRAG/lemma/themed bridge 링크 리포트. "
            "서사 전이·신학·체질 단정 아님. Track A·live·SEND 금지."
        ),
        "reproducible_command": "py scripts/build_logos_cosmic_anchor_graph_bridge_v1.py",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, default=BATCH_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    report = build_report(batch_dir=args.batch_dir, manifest_path=args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"WROTE: {args.out}")
    print(
        f"  anchors={report['anchor_count']} lemma_hits={s['lemma_hit_anchors']} "
        f"themed={s['themed_bridge_hit_anchors']} narratives={s['narrative_sample_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
