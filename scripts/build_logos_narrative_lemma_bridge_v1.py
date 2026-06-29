#!/usr/bin/env python3
"""Build narrative lemma bridge edges and merge into logos_lemma_verse_edges_v1.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_narrative_lemma_bridge_v1 import (
    LEMMA_EDGES,
    build_narrative_lemma_bridge_report,
    merge_jsonl,
)

BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"
OUT_REPORT = ROOT / "docs/final/artifacts/logos_narrative_lemma_bridge_v1_latest.json"
OUT_SLICE = ROOT / "docs/final/artifacts/logos_narrative_lemma_bridge_edges_v1.jsonl"
MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out-report", type=Path, default=OUT_REPORT)
    parser.add_argument("--out-slice", type=Path, default=OUT_SLICE)
    parser.add_argument("--merge-into", type=Path, default=LEMMA_EDGES)
    parser.add_argument("--max-atoms-per-verse", type=int, default=8)
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    if not args.bridge_json.is_file():
        print(f"FAIL: missing {args.bridge_json}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    report = build_narrative_lemma_bridge_report(
        bridge,
        max_atoms_per_verse=args.max_atoms_per_verse,
    )
    edges = list(report.get("edges") or [])

    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    report_write = {k: v for k, v in report.items() if k != "edges"}
    report_write["edge_count"] = len(edges)
    args.out_report.write_text(json.dumps(report_write, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.out_slice.parent.mkdir(parents=True, exist_ok=True)
    args.out_slice.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in edges) + ("\n" if edges else ""),
        encoding="utf-8",
    )

    merged_added = 0
    merged_total = 0
    if not args.no_merge and args.merge_into:
        merged, merged_added = merge_jsonl(base_path=args.merge_into, new_rows=edges)
        merged_total = len(merged)
        args.merge_into.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
            encoding="utf-8",
        )
        MANIFEST.write_text(
            json.dumps(
                {
                    "schema": "logos_lemma_verse_edges_v1",
                    "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "hypothesis_tier": "B",
                    "research_only": True,
                    "edge_count": merged_total,
                    "narrative_lemma_bridge_added": merged_added,
                    "note": "Includes narrative_lemma_bridge_v1 BI_ATOM_CONTAIN slice from 41k bidirectional index.",
                    "reproduce": "py scripts/build_logos_narrative_lemma_bridge_v1.py",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    print(f"WROTE: {args.out_report}")
    print(
        f"  narrative_verses={report['inputs']['narrative_verse_count']} "
        f"edges_built={len(edges)} merge_added={merged_added} merge_total={merged_total}"
    )
    if report["summary"]["verses_missing_atoms"] > 0:
        print("FAIL: narrative verse missing bidirectional atoms", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
