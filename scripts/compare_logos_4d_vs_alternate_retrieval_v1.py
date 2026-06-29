#!/usr/bin/env python3
"""Side-by-side: 4D centroid ANN vs GraphRAG / typology / lemma for 6-topic seeds."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/logos_4d_vs_alternate_retrieval_v1_latest.json"


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--centroid-spike", type=Path, default=ROOT / "reports/logos_topic_4d_resonance_spike_bridge_v2_v1_latest.json")
    ap.add_argument("--graphrag", type=Path, default=ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json")
    ap.add_argument("--typology", type=Path, default=ROOT / "reports/logos_topic_typology_seed_retrieval_v1_latest.json")
    ap.add_argument("--lemma", type=Path, default=ROOT / "reports/logos_topic_lemma_edge_seed_retrieval_v1_latest.json")
    ap.add_argument("--out-json", type=Path, default=OUT)
    args = ap.parse_args()

    centroid = _read(args.centroid_spike)
    c_hits = sum(1 for t in centroid.get("topics") or [] if (t.get("seed_in_top_k") or []))

    channels = {
        "centroid_4d_ann_v2": {
            "topic_hits": f"{c_hits}/{len(centroid.get('topics') or [])}",
            "role": "demoted_monitoring",
        },
        "graphrag_router": _read(args.graphrag).get("summary") or {},
        "typology_boost": _read(args.typology).get("summary") or {},
        "lemma_edges": _read(args.lemma).get("summary") or {},
    }

    doc = {
        "schema": "logos_4d_vs_alternate_retrieval_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "final_action": "HOLD_EXPLORATION",
        "routing_recommendation": "primary=graphrag_router+gold_eval; assist=typology+lemma; demote=centroid_4d_organic_spike",
        "channels": channels,
        "interpretation_guard": "Compare channels only — no Track A / live promotion.",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "channels": channels, "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
