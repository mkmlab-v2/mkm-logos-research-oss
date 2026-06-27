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
BRIDGE = ROOT / "docs/final/artifacts/worldview_formula_crosslink_bridge_v1_latest.json"
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

    unrecovered = int(formulas.get("unrecovered_slots", 51))
    documented_with_expr = int(formulas.get("documented_with_expr", 0))
    l3_status = "complete" if unrecovered == 0 else "vault_pending"

    ops_index = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    l1_status = "partial"
    l1_evidence = "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
    if ops_index.is_file():
        idx = json.loads(ops_index.read_text(encoding="utf-8-sig"))
        nodes = idx.get("nodes") or {}
        if "prism_ops_theory_mathematization_gate" in nodes:
            l1_status = "implemented_pointer"
            l1_evidence = "storage/meta/mkm_ops_memory_index_v1.json#prism_ops_theory_mathematization_gate"

    l4_status = "pointer_only"
    l4_evidence = "docs/final/MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md"
    if BRIDGE.is_file():
        bridge = json.loads(BRIDGE.read_text(encoding="utf-8-sig"))
        if bridge.get("ok"):
            l4_status = "implemented_pointer"
            l4_evidence = "docs/final/artifacts/worldview_formula_crosslink_bridge_v1_latest.json"

    doc = {
        "schema": "theory_reflection_gap_map_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] gap map — Cursor rules reflect ops pattern, not full 75-formula TOE",
        "lanes": {
            "L1_ops_inject": {
                "status": l1_status,
                "evidence": l1_evidence,
                "cursor_surface": "alwaysApply rules + CENTRAL one-liners + ops memory theory overlay",
            },
            "L2_multi_res_fills": {
                "status": "implemented_bench",
                "evidence": "reports/multi_res_fusion_bench_v1_latest.json",
                "fused_reduction_percent": (fusion.get("fused") or {}).get("reduction_percent"),
            },
            "L3_unrecovered_formula_slots": {
                "status": l3_status,
                "count": unrecovered,
                "documented_with_expr": documented_with_expr,
                "policy": "Do not promote empty UNRECOVERED slots to alwaysApply",
            },
            "L4_worldview_full_constitution": {
                "status": l4_status,
                "evidence": l4_evidence,
                "cursor_surface": "WORLDVIEW §5 ↔ 75 JSON bidirectional bridge",
            },
            "L5_todo_coordinate_harness": {
                "status": "implemented_bench",
                "evidence": "reports/multi_res_todo_index_v1_latest.json",
                "replay_contract": "reports/multi_res_harness_moss_replay_contract_v1_latest.json",
                "policy": "[HYPO] evidence→replay→human GO; no todo_queue auto-enqueue",
            },
            "L6_theory_promotion_registry": {
                "status": "implemented_pointer",
                "evidence": "docs/final/artifacts/mkm_theory_formula_promotion_registry_v1_latest.json",
                "policy": "promotion_to_a_track_allowed=false; B-track gate pointers only",
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
