#!/usr/bin/env python3
"""Phase2b: cloud/infra resilience concept_bridge (LLM plan → static materialize, no API) [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_cloud_resilience_poc_v1_latest.json"
DEFAULT_PLAN = ROOT / "docs/final/artifacts/logos_concept_bridge_llm_plan_v1_latest.json"
SCHEMA = "logos_concept_bridge_v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_bridge_doc(*, plan_path: Path | None) -> dict[str, Any]:
    plan_ref = None
    if plan_path and plan_path.is_file():
        plan_ref = plan_path.relative_to(ROOT).as_posix() if plan_path.is_relative_to(ROOT) else str(plan_path)

    nodes = [
        {
            "node_id": "concept:cloud_infra_resilience",
            "kind": "modern_concept",
            "label_ko": "클라우드·인프라 복원력",
            "label_en": "cloud infrastructure resilience",
        },
        {
            "node_id": "function:refined_foundation",
            "kind": "function",
            "label_ko": "견고한 기초·정제된 재료",
            "rationale_ko": "Job 28 정제·탐색 은유 (operator_proxy)",
        },
        {
            "node_id": "function:multi_region_failover",
            "kind": "function",
            "label_ko": "분산·대체 경로 유지",
            "rationale_ko": "철·진흙·다중 왕국 은유",
        },
        {
            "node_id": "function:renewed_city",
            "kind": "function",
            "label_ko": "새로운 질서·회복된 구조",
            "rationale_ko": "계시록 새 예루살렘 은유",
        },
        {
            "node_id": "lemma:hebrew:yasar_proxy",
            "kind": "lemma_proxy",
            "label_ko": "yasar/정제 (proxy)",
            "rationale_ko": "Job 28 정제 담화",
        },
        {
            "node_id": "lemma:hebrew:barzel_proxy",
            "kind": "lemma_proxy",
            "label_ko": "barzel/철 (proxy)",
            "rationale_ko": "Dan 2 철·진흙",
        },
        {
            "node_id": "lemma:greek:polis_proxy",
            "kind": "lemma_proxy",
            "label_ko": "polis/성 (proxy)",
            "rationale_ko": "Rev 21 새 성",
        },
        {"node_id": "verse:Job.28.17", "kind": "verse_ref", "verse_id": "hebrew::Job.28.17", "label_ko": "욥 28:17"},
        {"node_id": "verse:Dan.2.33", "kind": "verse_ref", "verse_id": "hebrew::Dan.2.33", "label_ko": "단 2:33"},
        {"node_id": "verse:Rev.21.2", "kind": "verse_ref", "verse_id": "greek::Rev.21.2", "label_ko": "계 21:2"},
    ]
    paths = [
        {
            "path_id": "path_refined_foundation",
            "steps": [
                "concept:cloud_infra_resilience",
                "function:refined_foundation",
                "lemma:hebrew:yasar_proxy",
                "verse:Job.28.17",
            ],
            "note_ko": "정제·기초 → 욥 28",
        },
        {
            "path_id": "path_failover_kingdoms",
            "steps": [
                "concept:cloud_infra_resilience",
                "function:multi_region_failover",
                "lemma:hebrew:barzel_proxy",
                "verse:Dan.2.33",
            ],
            "note_ko": "분산·왕국 → 단 2",
        },
        {
            "path_id": "path_renewed_structure",
            "steps": [
                "concept:cloud_infra_resilience",
                "function:renewed_city",
                "lemma:greek:polis_proxy",
                "verse:Rev.21.2",
            ],
            "note_ko": "회복·새 구조 → 계 21",
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
            "generation_method": "llm_plan_template_v1",
            "human_reviewed": False,
            "llm_plan_artifact": plan_ref,
            "llm_api_called": False,
        },
        "query": {
            "concept_id": "concept:cloud_infra_resilience",
            "label_ko": "클라우드·인프라 복원력",
        },
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {
            "seed_verse_ids": ["hebrew::Job.28.17", "hebrew::Dan.2.33", "greek::Rev.21.2"],
        },
        "known_limitations": [
            "Materialized from logos_concept_bridge_llm_plan_v1 without live LLM API.",
            "lemma_proxy labels are educational; not morphology-verified.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--llm-plan-json", type=Path, default=DEFAULT_PLAN)
    args = ap.parse_args()

    doc = _build_bridge_doc(plan_path=args.llm_plan_json if args.llm_plan_json.is_file() else None)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "paths": len(doc["paths"]), "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
