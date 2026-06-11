#!/usr/bin/env python3
"""n=20 web_ops memory retrieval proxy bench — pins vs full gate JSON ([HYPO]).

Reports raw (field-tag routing + pin inject) vs repair_v2 (+ slice) and token delta.

  py scripts/bench_mkm_ops_memory_web_ops_retrieval_v1.py
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    assemble_ops_memory_pins_text,
    assemble_ops_memory_repair_v2_text,
    load_index,
    route_nodes_by_field_tags,
    utc_now_iso,
)

DEFAULT_GATE = SCRIPT_ROOT / "reports/web_ops_regime_gate_v1_latest.json"
DEFAULT_OUT = SCRIPT_ROOT / "reports/mkm_ops_memory_web_ops_retrieval_bench_v1_latest.json"

SCENARIOS: tuple[tuple[str, str], ...] = (
    ("q01_nebius_balance", "Nebius 잔액 prepaid balance $25"),
    ("q02_no_gpu", "GPU spinup no_gpu 비용 감사"),
    ("q03_gate_pass", "web_ops gate_pass 통과 여부"),
    ("q04_worst_action", "worst_final_action ALLOW HOLD"),
    ("q05_tier3_auth", "Tier3 Human auth OAuth 결제"),
    ("q06_pointer_drift", "pointer drift baseline 해시"),
    ("q07_health_ok", "health_ok web_ops 헬스"),
    ("q08_observation_source", "observation_source CDP live"),
    ("q09_cost_audit", "cost_audit Nebius Azure"),
    ("q10_infra_lane", "infra web_ops 레인 재개"),
    ("q11_research_only", "research_only B-track 격벽"),
    ("q12_prepaid", "nebius_prepaid_only 선불"),
    ("q13_azure_portal", "Azure portal feasibility"),
    ("q14_regime_gate", "web_ops regime gate probe"),
    ("q15_balance_usd", "nebius_balance_usd field"),
    ("q16_cdp_probe", "cdp probe observation"),
    ("q17_weekly_task", "weekly web_ops regime task"),
    ("q18_allow_read", "ALLOW_READ read_only_dashboard"),
    ("q19_hold_payment", "HOLD_PAYMENT payment risk"),
    ("q20_combined", "Nebius web_ops infra cost drift health gate"),
)


def _count_tokens(text: str) -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return {"tokens": len(enc.encode(text)), "method": "tiktoken:cl100k_base"}
    except Exception as exc:  # noqa: BLE001
        est = max(1, len(text) // 4)
        return {"tokens": est, "method": "char_div_4_estimate", "note": str(exc)}


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_가-힣$]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--slice-max-chars", type=int, default=800)
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    index = load_index(args.index)
    full_gate_text = ""
    if args.gate_json.is_file():
        full_gate_text = args.gate_json.read_text(encoding="utf-8-sig")

    rows: list[dict[str, Any]] = []
    raw_jaccards: list[float] = []
    repair_jaccards: list[float] = []
    coord_jaccards: list[float] = []
    raw_tokens: list[int] = []
    repair_tokens: list[int] = []
    coord_tokens: list[int] = []

    for scenario_id, query in SCENARIOS:
        routed = route_nodes_by_field_tags(index, query)
        raw_text = assemble_ops_memory_pins_text(
            root, routed, include_slice=False, max_total_chars=None
        )
        repair_text = assemble_ops_memory_repair_v2_text(
            root,
            routed,
            slice_max_chars=args.slice_max_chars,
            query=query,
        )
        coord_text = assemble_ops_memory_repair_v2_text(
            root,
            routed,
            slice_max_chars=args.slice_max_chars,
            query=query,
            coordinate_filter=True,
        )
        raw_tok = _count_tokens(raw_text)["tokens"]
        repair_tok = _count_tokens(repair_text)["tokens"]
        coord_tok = _count_tokens(coord_text)["tokens"]
        raw_j = jaccard(query, raw_text)
        repair_j = jaccard(query, repair_text)
        coord_j = jaccard(query, coord_text)
        raw_jaccards.append(raw_j)
        repair_jaccards.append(repair_j)
        coord_jaccards.append(coord_j)
        raw_tokens.append(raw_tok)
        repair_tokens.append(repair_tok)
        coord_tokens.append(coord_tok)
        rows.append(
            {
                "scenario_id": scenario_id,
                "query": query,
                "routed_node_ids": [nid for nid, _ in routed],
                "routed_count": len(routed),
                "raw": {
                    "tokens": raw_tok,
                    "jaccard_vs_query": round(raw_j, 4),
                },
                "repair_v2": {
                    "tokens": repair_tok,
                    "jaccard_vs_query": round(repair_j, 4),
                    "slice_max_chars": args.slice_max_chars,
                },
                "coordinate_v1": {
                    "tokens": coord_tok,
                    "jaccard_vs_query": round(coord_j, 4),
                    "slice_max_chars": args.slice_max_chars,
                    "label": "query-filtered json_pointer coordinates",
                },
                "delta": {
                    "jaccard_repair_v2_minus_raw": round(repair_j - raw_j, 4),
                    "jaccard_coordinate_v1_minus_raw": round(coord_j - raw_j, 4),
                    "tokens_added_by_slice": repair_tok - raw_tok,
                    "tokens_coordinate_v1": coord_tok,
                },
            }
        )

    full_gate_tok = _count_tokens(full_gate_text)["tokens"] if full_gate_text else 0
    avg_raw_tok = sum(raw_tokens) / len(raw_tokens) if raw_tokens else 0
    doc = {
        "schema": "mkm_ops_memory_web_ops_retrieval_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] retrieval proxy — not Track A·live merge",
        "generated_at_utc": utc_now_iso(),
        "scenario_count": len(SCENARIOS),
        "index_path": str(args.index),
        "full_gate_json": {
            "path": str(args.gate_json),
            "tokens": full_gate_tok,
            "present": bool(full_gate_text),
        },
        "aggregate": {
            "raw": {
                "mean_jaccard_vs_query": round(sum(raw_jaccards) / len(raw_jaccards), 4),
                "mean_tokens_per_scenario": round(avg_raw_tok, 2),
            },
            "repair_v2": {
                "mean_jaccard_vs_query": round(
                    sum(repair_jaccards) / len(repair_jaccards), 4
                ),
                "mean_tokens_per_scenario": round(
                    sum(repair_tokens) / len(repair_tokens), 2
                ),
            },
            "coordinate_v1": {
                "mean_jaccard_vs_query": round(
                    sum(coord_jaccards) / len(coord_jaccards), 4
                ),
                "mean_tokens_per_scenario": round(
                    sum(coord_tokens) / len(coord_tokens), 2
                ),
            },
            "delta": {
                "mean_jaccard_repair_v2_minus_raw": round(
                    (sum(repair_jaccards) - sum(raw_jaccards)) / len(repair_jaccards), 4
                ),
                "mean_jaccard_coordinate_v1_minus_raw": round(
                    (sum(coord_jaccards) - sum(raw_jaccards)) / len(coord_jaccards), 4
                ),
                "tokens_saved_vs_full_gate_json": (
                    full_gate_tok - int(avg_raw_tok) if full_gate_tok else None
                ),
                "reduction_ratio_vs_full_gate": (
                    round(1 - (avg_raw_tok / full_gate_tok), 4)
                    if full_gate_tok
                    else None
                ),
            },
        },
        "scenarios": rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out), **doc["aggregate"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
