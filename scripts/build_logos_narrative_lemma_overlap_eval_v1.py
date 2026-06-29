#!/usr/bin/env python3
"""Write logos_narrative_lemma_overlap_eval_v1_latest.json from bridge + lemma/bi indexes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.logos_narrative_lemma_overlap_eval_v1 import build_narrative_lemma_overlap_report

OUT = ROOT / "docs/final/artifacts/logos_narrative_lemma_overlap_eval_v1_latest.json"
BRIDGE = ROOT / "docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge-json", type=Path, default=BRIDGE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    if not args.bridge_json.is_file():
        print(f"FAIL: missing {args.bridge_json}", file=sys.stderr)
        return 1

    bridge = json.loads(args.bridge_json.read_text(encoding="utf-8"))
    report = build_narrative_lemma_overlap_report(bridge)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    print(f"WROTE: {args.out}")
    print(
        f"  samples={report['narrative_sample_count']} "
        f"hop_lemma_edge_hit_rate={s['hop_lemma_edge_hit_rate']} "
        f"hop_bidirectional_atom_hit_rate={s['hop_bidirectional_atom_hit_rate']} "
        f"mean_inter_hop_atom_jaccard={s['mean_inter_hop_atom_jaccard']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
