#!/usr/bin/env python3
"""Insight payload cap ablation bench — token vs caps profile ([HYPO] / B-track).

Reuses router/bundle/chain on disk; sweeps caps without rerunning full bridge chain.

  py scripts/build_mkm_ltm_insight_cap_ablation_bench_v1.py
  py scripts/build_mkm_ltm_insight_cap_ablation_bench_v1.py --query "욥이 고난을 받은 이유"
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import utc_now_iso  # noqa: E402

DEFAULT_OUT = SCRIPT_ROOT / "reports" / "mkm_ltm_insight_cap_ablation_bench_v1_latest.json"
DEFAULT_BUNDLE = SCRIPT_ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
DEFAULT_CHAIN = SCRIPT_ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_ROUTER = SCRIPT_ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_QUERY = "욥이 고난을 받은 이유"
DEFAULT_QUERY_ID = "job_suffering_reason"

CAP_PROFILES: dict[str, dict[str, int]] = {
    "baseline_production": {
        "rag_evidence": 24,
        "subgraph_paths": 12,
        "subgraph_verses": 12,
        "lod_node_cap": 48,
        "lod_edge_cap": 56,
    },
    "tight": {
        "rag_evidence": 12,
        "subgraph_paths": 6,
        "subgraph_verses": 6,
        "lod_node_cap": 24,
        "lod_edge_cap": 28,
    },
    "minimal": {
        "rag_evidence": 8,
        "subgraph_paths": 4,
        "subgraph_verses": 4,
        "lod_node_cap": 16,
        "lod_edge_cap": 20,
    },
    "ultra_min": {
        "rag_evidence": 4,
        "subgraph_paths": 2,
        "subgraph_verses": 2,
        "lod_node_cap": 8,
        "lod_edge_cap": 12,
    },
}


def _count_tokens(text: str) -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return {"tokens": len(enc.encode(text)), "method": "tiktoken:cl100k_base"}
    except Exception as exc:  # noqa: BLE001
        est = max(1, len(text) // 4)
        return {"tokens": est, "method": "char_div_4_estimate", "note": str(exc)}


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_module(name: str, rel: str) -> Any:
    path = SCRIPT_ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _measure_profile(
    *,
    profile_id: str,
    caps: dict[str, int],
    query: str,
    query_id: str,
    bundle: dict[str, Any],
    chain: dict[str, Any] | None,
    router: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    digest: dict[str, Any] | None,
) -> dict[str, Any]:
    insight_mod = _load_module(
        "build_magic_orb_question_insight_payload_v1",
        "scripts/build_magic_orb_question_insight_payload_v1.py",
    )
    bloom_mod = _load_module(
        "build_magic_orb_graph_bloom_v1",
        "scripts/build_magic_orb_graph_bloom_v1.py",
    )

    ann_top = insight_mod._ann_top_verse_ids(list(bundle.get("rag_evidence") or []))
    bloom = bloom_mod.build_bloom(
        query=query,
        router=router,
        ann_top_verse_ids=ann_top,
        expand_graph=False,
        lod_node_cap=int(caps.get("lod_node_cap") or 48),
        lod_edge_cap=int(caps.get("lod_edge_cap") or 56),
    )

    payload = insight_mod.build_payload(
        query=query,
        query_id=query_id,
        bundle=bundle,
        chain=chain,
        router=router,
        graph_bloom=bloom,
        caps=caps,
        shadow=shadow,
        digest=digest,
        enrich_four_slot=True,
    )

    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    token_row = _count_tokens(serialized)
    bloom_nodes = len((bloom or {}).get("nodes") or [])
    bloom_edges = len((bloom or {}).get("edges") or [])
    rag_count = len(payload.get("rag_evidence") or [])
    slots_count = len(payload.get("structured_insight_slots") or [])
    four_slot = payload.get("four_slot_response_v1") or {}
    return {
        "profile_id": profile_id,
        "caps": caps,
        "char_count": len(serialized),
        **token_row,
        "rag_evidence_count": rag_count,
        "structured_insight_slots_count": slots_count,
        "graph_bloom_nodes": bloom_nodes,
        "graph_bloom_edges": bloom_edges,
        "four_slot_present": bool(four_slot),
        "send_gate": (four_slot.get("enforcement") or {}).get("send_gate"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--query-id", default=DEFAULT_QUERY_ID)
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--chain-json", type=Path, default=DEFAULT_CHAIN)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    bundle = _load_json(args.bundle_json.resolve())
    if not bundle:
        print(f"FAIL: missing bundle: {args.bundle_json}", file=sys.stderr)
        return 1
    router = _load_json(args.router_json.resolve())
    if not router:
        print(f"FAIL: missing router: {args.router_json}", file=sys.stderr)
        return 1

    chain = _load_json(args.chain_json.resolve())
    if chain:
        chain = {
            **chain,
            "_path": str(args.chain_json.resolve().relative_to(root)).replace("\\", "/"),
        }

    shadow_path = root / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
    digest_path = root / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
    shadow = _load_json(shadow_path)
    digest = _load_json(digest_path)

    profiles: dict[str, Any] = {}
    baseline_tokens: int | None = None
    for profile_id, caps in CAP_PROFILES.items():
        row = _measure_profile(
            profile_id=profile_id,
            caps=caps,
            query=args.query,
            query_id=args.query_id,
            bundle=bundle,
            chain=chain,
            router=router,
            shadow=shadow,
            digest=digest,
        )
        tokens = int(row["tokens"])
        if profile_id == "baseline_production":
            baseline_tokens = tokens
        profiles[profile_id] = row

    if baseline_tokens is None:
        print("FAIL: baseline profile missing", file=sys.stderr)
        return 1

    for profile_id, row in profiles.items():
        tokens = int(row["tokens"])
        saved = max(0, baseline_tokens - tokens)
        row["saved_tokens_vs_baseline_production"] = saved
        row["savings_ratio_vs_baseline_production"] = (
            round(saved / baseline_tokens, 4) if baseline_tokens else 0.0
        )

    best = min(profiles.values(), key=lambda r: int(r["tokens"]))
    doc: dict[str, Any] = {
        "schema": "mkm_ltm_insight_cap_ablation_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] cap ablation — not Track A SLA; do not cite as DMF/external KPI",
        "generated_at_utc": utc_now_iso(),
        "query": args.query,
        "query_id": args.query_id,
        "inputs": {
            "bundle": str(args.bundle_json.relative_to(root)).replace("\\", "/"),
            "router": str(args.router_json.relative_to(root)).replace("\\", "/"),
            "chain": str(args.chain_json.relative_to(root)).replace("\\", "/"),
        },
        "profiles": profiles,
        "aggregate": {
            "profile_count": len(profiles),
            "baseline_production_tokens": baseline_tokens,
            "lowest_token_profile": best["profile_id"],
            "lowest_token_count": int(best["tokens"]),
            "max_savings_ratio_vs_baseline": max(
                float(r["savings_ratio_vs_baseline_production"]) for r in profiles.values()
            ),
        },
        "policy": {
            "gating": "NON_GATING",
            "must_not_merge_with": ["track_a_compression", "dmf_external_kpi", "live_trading_trigger"],
        },
        "reproduce": "py scripts/build_mkm_ltm_insight_cap_ablation_bench_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"baseline_tokens={baseline_tokens} "
        f"lowest={best['profile_id']}:{best['tokens']} "
        f"max_savings_ratio={doc['aggregate']['max_savings_ratio_vs_baseline']}"
    )
    for pid, row in profiles.items():
        print(
            f"  {pid}: tokens={row['tokens']} rag={row['rag_evidence_count']} "
            f"bloom_nodes={row['graph_bloom_nodes']} savings={row['savings_ratio_vs_baseline_production']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
