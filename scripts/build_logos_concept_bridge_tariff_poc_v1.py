#!/usr/bin/env python3
"""Phase 0: static concept_bridge for 'tariff' → verse paths ([HYPO], no scores)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_tariff_poc_v1_latest.json"
SCHEMA = "logos_concept_bridge_v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_bridge_doc() -> dict[str, Any]:
    nodes = [
        {"node_id": "concept:tariff", "kind": "modern_concept", "label_ko": "관세", "label_en": "tariff"},
        {
            "node_id": "function:trade_tribute",
            "kind": "function",
            "label_ko": "무역·조공·징수",
            "rationale_ko": "관세·무역장벽 은유 (operator_proxy)",
        },
        {
            "node_id": "function:scales_weighing",
            "kind": "function",
            "label_ko": "저울·징수·분배",
            "rationale_ko": "세금·관세 징수 은유",
        },
        {
            "node_id": "function:nation_divided",
            "kind": "function",
            "label_ko": "나라·연합 분열",
            "rationale_ko": "무역 분쟁·연합 균열 은유",
        },
        {
            "node_id": "lemma:hebrew:מס_proxy",
            "kind": "lemma_proxy",
            "label_ko": "징수·세 (proxy)",
            "rationale_ko": "무역·징수 담화 앵커",
        },
        {
            "node_id": "lemma:greek:κηνσος_proxy",
            "kind": "lemma_proxy",
            "label_ko": "조공·인두세 (proxy)",
            "rationale_ko": "Matt 22 조공 담화 앵커",
        },
        {
            "node_id": "lemma:aramaic:ערב_proxy",
            "kind": "lemma_proxy",
            "label_ko": "섞이다·붙이다 (proxy)",
            "rationale_ko": "철·진흙 혼합(연합 분열) 앵커",
        },
        {"node_id": "verse:Prov.11.1", "kind": "verse_ref", "verse_id": "hebrew::Prov.11.1", "label_ko": "잠언 11:1"},
        {"node_id": "verse:Matt.22.19", "kind": "verse_ref", "verse_id": "greek::Matt.22.19", "label_ko": "마태 22:19"},
        {"node_id": "verse:Dan.2.43", "kind": "verse_ref", "verse_id": "aramaic::Dan.2.43", "label_ko": "다니엘 2:43"},
    ]
    paths = [
        {
            "path_id": "path_trade_tribute",
            "steps": ["concept:tariff", "function:trade_tribute", "lemma:greek:κηνσος_proxy", "verse:Matt.22.19"],
            "note_ko": "관세·징수 → 조공 담화",
        },
        {
            "path_id": "path_scales",
            "steps": ["concept:tariff", "function:scales_weighing", "lemma:hebrew:מס_proxy", "verse:Prov.11.1"],
            "note_ko": "저울·징수 → 잠언",
        },
        {
            "path_id": "path_union_split",
            "steps": ["concept:tariff", "function:nation_divided", "lemma:aramaic:ערב_proxy", "verse:Dan.2.43"],
            "note_ko": "연합 분열 → 다니엘 2",
        },
    ]
    seed_verse_ids = ["greek::Matt.22.19", "hebrew::Prov.11.1", "aramaic::Dan.2.43"]
    return {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "human_signoff_completed": False,
            "generation_method": "static_template_v1",
            "human_reviewed": False,
        },
        "query": {"concept_id": "concept:tariff", "label_ko": "관세"},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {"seed_verse_ids": seed_verse_ids},
        "known_limitations": [
            "Static operator_proxy template; not LLM-generated.",
            "lemma_proxy labels are educational anchors; not morphology-verified.",
            "No topology_overlap_percent or prophecy_hit_rate fields.",
            "Does not replace era-blind text_blind 4.3% defense metric.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = _build_bridge_doc()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} paths={len(doc['paths'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
