#!/usr/bin/env python3
"""Build lemma spike edges and merge (target lemma_hit_anchors)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_lemma_anchor_spike_v1 import build_lemma_spike_report, merge_spike_edges

BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_lemma_anchor_spike_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=60)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    report = build_lemma_spike_report(target_hits=args.target, bridge=bridge)
    edges = list(report.pop("edges") or [])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    merged_added = 0
    merged_total = 0
    if not args.no_merge and edges:
        merged_added, merged_total = merge_spike_edges(edges, path_id=str(report.get("path_id")))
        MANIFEST.write_text(
            json.dumps(
                {
                    "schema": "logos_lemma_verse_edges_v1",
                    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "edge_count": merged_total,
                    "lemma_spike_added": merged_added,
                    "target_lemma_hit_anchors": args.target,
                    "reproduce": "py scripts/build_logos_lemma_anchor_spike_v1.py",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"WROTE: {args.out}")
    print(
        f"  baseline={report['baseline_lemma_hit_anchors']} target={args.target} "
        f"candidates={report['candidate_anchor_count']} edges={len(edges)} merge_added={merged_added}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
