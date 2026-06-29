#!/usr/bin/env python3
"""Build narrative inter-hop bridge artifact and merge INTER_HOP_BRIDGE_CONTAIN edges."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_narrative_inter_hop_bridge_v1 import (
    build_inter_hop_bridge_report,
    merge_inter_hop_lemma_edges,
)

BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_narrative_inter_hop_bridge_v1_latest.json"
MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    if not args.bridge_json.is_file():
        print(f"FAIL: missing {args.bridge_json}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    report = build_inter_hop_bridge_report(bridge)
    lemma_edges = list(report.pop("lemma_edges") or [])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    merged_added = 0
    merged_total = 0
    if not args.no_merge:
        merged_added, merged_total = merge_inter_hop_lemma_edges(lemma_edges)
        MANIFEST.write_text(
            json.dumps(
                {
                    "schema": "logos_lemma_verse_edges_v1",
                    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "edge_count": merged_total,
                    "narrative_inter_hop_bridge_added": merged_added,
                    "note": "Includes narrative_inter_hop_bridge_v1 INTER_HOP_BRIDGE_CONTAIN slice.",
                    "reproduce": "py scripts/build_logos_narrative_inter_hop_bridge_v1.py",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    summary = report["summary"]
    print(f"WROTE: {args.out}")
    print(
        f"  pairs={summary['inter_hop_pair_count']} bridge_pair_rate={summary['bridge_pair_rate']} "
        f"lemma_edges_built={summary['lemma_edges_built']} merge_added={merged_added}"
    )
    if summary["bridge_pair_rate"] < 1.0:
        print("FAIL: bridge_pair_rate < 1.0", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
