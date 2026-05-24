#!/usr/bin/env python3
"""Phase 0: static concept_bridge for 'semiconductor' → verse paths ([HYPO], no scores)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_concept_bridge_semiconductor_poc_v1_latest.json"
SCHEMA = "logos_concept_bridge_v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_bridge_doc() -> dict[str, Any]:
    nodes = [
        {"node_id": "concept:semiconductor", "kind": "modern_concept", "label_ko": "반도체", "label_en": "semiconductor"},
        {
            "node_id": "function:refined_silica",
            "kind": "function",
            "label_ko": "극도로 정제된 규소/유리",
            "rationale_ko": "반도체 기판·정제 재료 은유 (operator_proxy)",
        },
        {
            "node_id": "function:light_etching",
            "kind": "function",
            "label_ko": "빛으로 미세 새김",
            "rationale_ko": "노광·회로 패터닝 은유",
        },
        {
            "node_id": "function:iron_clay_mix",
            "kind": "function",
            "label_ko": "이질 물질 혼합·제어",
            "rationale_ko": "철·진흙 발혼 은유",
        },
        {
            "node_id": "lemma:hebrew:זכוך_proxy",
            "kind": "lemma_proxy",
            "label_ko": "정제/유리 계열 (proxy)",
            "rationale_ko": "Job 28 정제 유리 담화 앵커",
        },
        {
            "node_id": "lemma:hebrew:פתח_proxy",
            "kind": "lemma_proxy",
            "label_ko": "새기다 (proxy)",
            "rationale_ko": "Zech 3 돌에 새김 앵커",
        },
        {
            "node_id": "lemma:aramaic:ערב_proxy",
            "kind": "lemma_proxy",
            "label_ko": "섞이다 (proxy)",
            "rationale_ko": "Dan 2 철·진흙 혼합 앵커",
        },
        {"node_id": "verse:Job.28.17", "kind": "verse_ref", "verse_id": "hebrew::Job.28.17", "label_ko": "욥 28:17"},
        {"node_id": "verse:Zech.3.9", "kind": "verse_ref", "verse_id": "hebrew::Zech.3.9", "label_ko": "스가랴 3:9"},
        {"node_id": "verse:Dan.2.43", "kind": "verse_ref", "verse_id": "aramaic::Dan.2.43", "label_ko": "다니엘 2:43"},
    ]
    paths = [
        {
            "path_id": "path_refined_glass",
            "steps": ["concept:semiconductor", "function:refined_silica", "lemma:hebrew:זכוך_proxy", "verse:Job.28.17"],
            "note_ko": "정제 재료 → 욥기 지혜 담화",
        },
        {
            "path_id": "path_light_etch",
            "steps": ["concept:semiconductor", "function:light_etching", "lemma:hebrew:פתח_proxy", "verse:Zech.3.9"],
            "note_ko": "광학 새김 → 스가랴 돌",
        },
        {
            "path_id": "path_iron_clay",
            "steps": ["concept:semiconductor", "function:iron_clay_mix", "lemma:aramaic:ערב_proxy", "verse:Dan.2.43"],
            "note_ko": "이질 혼합 → 다니엘 2",
        },
    ]
    seed_verse_ids = ["aramaic::Dan.2.43", "hebrew::Zech.3.9", "hebrew::Job.28.17", "aramaic::Dan.2.10"]
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
        "query": {"concept_id": "concept:semiconductor", "label_ko": "반도체"},
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
    ap.add_argument("--run-seed-chain", action="store_true", help="After write, run BFS seed chain on daniel seeds")
    args = ap.parse_args()

    doc = _build_bridge_doc()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} paths={len(doc['paths'])}")

    if args.run_seed_chain:
        chain_py = ROOT / "scripts/run_logos_graph_seed_chain_v1.py"
        proc = subprocess.run([sys.executable, str(chain_py)], cwd=str(ROOT), check=False)
        if proc.returncode != 0:
            return proc.returncode
        chain_path = ROOT / "docs/final/artifacts/logos_graph_seed_chain_v1_latest.json"
        if chain_path.is_file():
            doc["graph_rag_hooks"]["seed_chain_json"] = str(
                chain_path.relative_to(ROOT)
            ).replace("\\", "/")
            out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
