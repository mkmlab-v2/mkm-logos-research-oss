#!/usr/bin/env python3
"""Emit dual-lane subgraph router contract (Logos vs Pet) — machine SSOT, no Track A merge."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/graph_subgraph_router_lane_contract_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_contract() -> dict:
    return {
        "schema": "graph_subgraph_router_lane_contract_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lanes": {
            "logos_bible": {
                "corpus_id": "logos_verse_31k",
                "bridge_registry": "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json",
                "router_script": "scripts/run_logos_subgraph_graphrag_router_v1.py",
                "replay_batch": "scripts/Invoke-LogosSubgraphReplayBatch_v1.ps1",
                "gold_json": "docs/final/artifacts/logos_semantic_query_gold_human_v1.json",
                "default_node_cap": 128,
                "default_edge_cap": 140,
                "router_kind": "token_overlap_logos_subgraph_v1",
                "must_not_merge_with": ["global_atom_network_pilot", "pet_b2c_device", "track_a_compression"],
            },
            "pet_b2c_device": {
                "corpus_id": "pet_companion_slots_kv",
                "bridge_registry": "docs/final/artifacts/pet_companion_observation_bridge_registry_v1_latest.json",
                "router_script": "scripts/run_pet_companion_subgraph_router_v1.py",
                "poc_chain": "scripts/Invoke-PetCompanionSubgraphGraphPoC_v1.ps1",
                "device_graph_sync": "scripts/Invoke-PetCompanionDeviceGraphBridgeSync_v1.ps1",
                "device_bridge_schema": "docs/final/schemas/pet_companion_device_memory_bridge_request_v1.schema.json",
                "default_node_cap": 128,
                "default_edge_cap": 140,
                "router_kind": "token_overlap_pet_observation_subgraph_v1",
                "must_not_merge_with": ["mkm_ops_memory_graph", "logos_bible_subgraph", "track_a_compression"],
            },
        },
        "four_prohibition_lines": [
            "Subgraph router uses token overlap on bridge registries — not 4D gematria vector routing.",
            "Global atom network (~6.4M edges) must not merge into Logos Bible or Pet device subgraph mainline.",
            "q01-q12 / pet replay batches prove registry path coverage only — not prophecy hit_rate.",
            "Track A compression lexicon path and Logos ANN RAG remain isolated lanes.",
        ],
        "marketing_guardrails_ref": "docs/final/marketing_guardrails_v1.md",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_contract(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
