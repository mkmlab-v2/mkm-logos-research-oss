#!/usr/bin/env python3
"""Phase 2 static concept_bridge: covenant stability under crisis ([HYPO], no scores)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_covenant_crisis_poc_v1_latest.json"
SCHEMA = "logos_concept_bridge_v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_bridge_doc() -> dict[str, Any]:
    nodes = [
        {
            "node_id": "concept:covenant_stability_crisis",
            "kind": "modern_concept",
            "label_ko": "위기 가운데 언약의 안정",
            "label_en": "covenant stability under crisis",
        },
        {
            "node_id": "function:steadfast_love",
            "kind": "function",
            "label_ko": "신실·인자하심의 지속",
            "rationale_ko": "언약 신실(hesed) 은유",
        },
        {
            "node_id": "function:new_covenant_heart",
            "kind": "function",
            "label_ko": "새 언약·마음에 기록",
            "rationale_ko": "Jer 31 새 언약 담화",
        },
        {
            "node_id": "function:transient_wicked_removed",
            "kind": "function",
            "label_ko": "악인·빙산처럼 사라짐",
            "rationale_ko": "Job 24 시련·전환 은유 (operator_proxy)",
        },
        {
            "node_id": "lemma:hebrew:hesed_proxy",
            "kind": "lemma_proxy",
            "label_ko": "hesed (proxy)",
            "rationale_ko": "Ps 89 언약 신실 앵커",
        },
        {
            "node_id": "lemma:hebrew:berit_proxy",
            "kind": "lemma_proxy",
            "label_ko": "berit (proxy)",
            "rationale_ko": "Jer 31 언약 앵커",
        },
        {
            "node_id": "lemma:hebrew:avar_proxy",
            "kind": "lemma_proxy",
            "label_ko": "avar (proxy)",
            "rationale_ko": "Job 24 전환 앵커",
        },
        {"node_id": "verse:Ps.89.28", "kind": "verse_ref", "verse_id": "hebrew::Ps.89.28", "label_ko": "시 89:28"},
        {"node_id": "verse:Jer.31.33", "kind": "verse_ref", "verse_id": "hebrew::Jer.31.33", "label_ko": "렘 31:33"},
        {"node_id": "verse:Job.24.19", "kind": "verse_ref", "verse_id": "hebrew::Job.24.19", "label_ko": "욥 24:19"},
    ]
    paths = [
        {
            "path_id": "path_hesed_covenant",
            "steps": [
                "concept:covenant_stability_crisis",
                "function:steadfast_love",
                "lemma:hebrew:hesed_proxy",
                "verse:Ps.89.28",
            ],
            "note_ko": "신실·언약 → 시편 89",
        },
        {
            "path_id": "path_new_covenant",
            "steps": [
                "concept:covenant_stability_crisis",
                "function:new_covenant_heart",
                "lemma:hebrew:berit_proxy",
                "verse:Jer.31.33",
            ],
            "note_ko": "새 언약 → 예레미야 31",
        },
        {
            "path_id": "path_crisis_transient",
            "steps": [
                "concept:covenant_stability_crisis",
                "function:transient_wicked_removed",
                "lemma:hebrew:avar_proxy",
                "verse:Job.24.19",
            ],
            "note_ko": "위기·전환 → 욥 24 (KO retrieval top-1 align)",
        },
    ]
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
        "query": {"concept_id": "concept:covenant_stability_crisis", "label_ko": "위기 가운데 언약의 안정"},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {
            "seed_verse_ids": ["hebrew::Ps.89.28", "hebrew::Jer.31.33", "hebrew::Job.24.19"]
        },
        "known_limitations": [
            "Static template aligned to logos_semantic_query_gold q01; not LLM-generated.",
            "lemma_proxy labels are educational anchors; not morphology-verified.",
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
    print(json.dumps({"ok": True, "paths": len(doc["paths"]), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
