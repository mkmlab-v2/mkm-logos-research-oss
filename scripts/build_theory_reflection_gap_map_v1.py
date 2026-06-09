#!/usr/bin/env python3
"""L2 theory reflection gap map — links multi-res bench to formula slots ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMULAS = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
FUSION = ROOT / "reports/multi_res_fusion_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/theory_reflection_gap_map_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    formulas = {}
    if FORMULAS.is_file():
        formulas = json.loads(FORMULAS.read_text(encoding="utf-8-sig"))
    fusion = {}
    if FUSION.is_file():
        fusion = json.loads(FUSION.read_text(encoding="utf-8-sig"))

    unrecovered = formulas.get("unrecovered_slots") or formulas.get("vault_pending") or []
    if isinstance(unrecovered, dict):
        unrecovered = list(unrecovered.keys())
    n_unrecovered = len(unrecovered) if isinstance(unrecovered, list) else 51

    doc = {
        "schema": "theory_reflection_gap_map_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] gap map — Cursor rules reflect ops pattern, not full 75-formula TOE",
        "lanes": {
            "L1_ops_inject": {
                "status": "partial",
                "evidence": "reports/mkm_ops_memory_index_token_bench_v1_latest.json",
                "cursor_surface": "alwaysApply rules + CENTRAL one-liners",
            },
            "L2_multi_res_fills": {
                "status": "implemented_bench",
                "evidence": "reports/multi_res_fusion_bench_v1_latest.json",
                "fused_reduction_percent": (fusion.get("fused") or {}).get("reduction_percent"),
            },
            "L3_unrecovered_formula_slots": {
                "status": "vault_pending",
                "count": n_unrecovered,
                "policy": "Do not promote empty UNRECOVERED slots to alwaysApply",
            },
            "L4_worldview_full_constitution": {
                "status": "pointer_only",
                "evidence": "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md",
                "cursor_surface": "central-agent-memory.mdc §1.0.5 pointer",
            },
            "L5_todo_coordinate_harness": {
                "status": "implemented_bench",
                "evidence": "reports/multi_res_todo_index_v1_latest.json",
                "replay_contract": "reports/multi_res_harness_moss_replay_contract_v1_latest.json",
                "policy": "[HYPO] evidence→replay→human GO; no todo_queue auto-enqueue",
            },
        },
        "multi_res_link": {
            "fusion_bench": str(FUSION.relative_to(ROOT)).replace("\\", "/") if FUSION.is_file() else None,
            "todo_index": "reports/multi_res_todo_index_v1_latest.json",
            "harness_moss_replay_contract": "reports/multi_res_harness_moss_replay_contract_v1_latest.json",
            "quality_claim_allowed": False,
        },
    }
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK: lanes={len(doc['lanes'])} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
