#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Question → Logos subgraph router → semantic bundle → magic_orb insight + graph_bloom."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

DEFAULT_OUT_CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_ROUTER_OUT = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_INSIGHT_OUT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Run question semantic RAG bridge chain.")
    ap.add_argument("--query", required=True)
    ap.add_argument("--query-id", default="q01")
    ap.add_argument("--top-bridges", type=int, default=6)
    ap.add_argument("--skip-ann-lite", action="store_true")
    ap.add_argument("--expand-graph", action="store_true", help="enrich graph_bloom from bible_meaning_graph")
    ap.add_argument("--sync-public", action="store_true")
    ap.add_argument("--router-out", type=Path, default=DEFAULT_ROUTER_OUT)
    ap.add_argument("--insight-out", type=Path, default=DEFAULT_INSIGHT_OUT)
    ap.add_argument("--bloom-out", type=Path, default=ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT_CHAIN)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    router_out = args.router_out if args.router_out.is_absolute() else ROOT / args.router_out
    chain_out = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    insight_out = args.insight_out if args.insight_out.is_absolute() else ROOT / args.insight_out
    bloom_out = args.bloom_out if args.bloom_out.is_absolute() else ROOT / args.bloom_out

    steps: dict[str, Any] = {}

    router_cmd = [
        PY,
        str(ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"),
        "--query-id",
        args.query_id,
        "--query",
        args.query,
        "--top-bridges",
        str(args.top_bridges),
        "--output-json",
        str(router_out.relative_to(ROOT)).replace("\\", "/"),
    ]
    if args.dry_run:
        print("[dry-run]", " ".join(router_cmd))
        steps["subgraph_router"] = {"ok": True, "dry_run": True}
    else:
        rc = _run(router_cmd)
        steps["subgraph_router"] = {"ok": rc == 0, "exit_code": rc, "artifact": str(router_out)}
        if rc != 0:
            return rc

    bundle_path = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
    if bundle_path.is_file():
        steps["bridge_bundle"] = {
            "ok": True,
            "artifact": str(bundle_path.relative_to(ROOT)).replace("\\", "/"),
            "reused": True,
        }
    else:
        steps["bridge_bundle"] = {
            "ok": True,
            "artifact": None,
            "reused": False,
            "note": "bundle missing; insight builder synthesizes rag from router",
        }

    ann_status = "skipped_flag"
    if not args.skip_ann_lite:
        ann_status = "skipped_flag"  # ANN lite optional; flag-only until wired
    steps["ann_lite"] = {"status": ann_status}

    bloom_cmd = [
        PY,
        str(ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"),
        "--query",
        args.query,
        "--router-json",
        str(router_out),
    ]
    if args.expand_graph:
        bloom_cmd.append("--expand-graph")

    bloom_cmd.extend(["--out-json", str(bloom_out)])

    if args.dry_run:
        print("[dry-run]", " ".join(bloom_cmd))
    else:
        rc = _run(bloom_cmd)
        if rc != 0:
            return rc

    insight_cmd = [
        PY,
        str(ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"),
        "--query",
        args.query,
        "--query-id",
        args.query_id,
        "--router-json",
        str(router_out),
        "--bloom-json",
        str(bloom_out),
        "--out-json",
        str(insight_out),
        "--caps-json-inline",
        json.dumps(
            {
                "rag_evidence": 24,
                "subgraph_paths": 12,
                "subgraph_verses": 12,
                "ann_top_k_default": 8,
                "lod_node_cap": 48,
                "lod_edge_cap": 56,
            }
        ),
    ]
    if args.sync_public:
        insight_cmd.append("--sync-public")

    if args.dry_run:
        print("[dry-run]", " ".join(insight_cmd))
        steps["insight_payload"] = {"ok": True, "dry_run": True}
    else:
        rc = _run(insight_cmd)
        steps["insight_payload"] = {"ok": rc == 0, "exit_code": rc, "artifact": str(insight_out)}
        if rc != 0:
            return rc

    router_doc = json.loads(router_out.read_text(encoding="utf-8-sig")) if router_out.is_file() else {}
    chain_doc = {
        "schema": "question_semantic_rag_bridge_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": args.query,
        "query_id": args.query_id,
        "steps": {
            **steps,
            "subgraph_router": {
                "ok": True,
                "artifact": str(router_out.relative_to(ROOT)).replace("\\", "/"),
                "bridges_matched": router_doc.get("bridges_matched"),
                "paths": len(router_doc.get("paths") or []),
                "verse_ids": len(router_doc.get("verse_ids") or []),
            },
            "ann_lite": steps.get("ann_lite", {"status": ann_status}),
            "bridge_bundle": steps.get("bridge_bundle", {"ok": True}),
            "graph_bloom": {
                "ok": True,
                "artifact": str(bloom_out.relative_to(ROOT)).replace("\\", "/"),
                "expand_graph": bool(args.expand_graph),
            },
            "insight_payload": steps.get("insight_payload", {"ok": True}),
        },
        "caps": {
            "rag_evidence": 24,
            "subgraph_paths": 12,
            "subgraph_verses": 12,
            "ann_top_k_default": 8,
            "lod_node_cap": 48,
            "lod_edge_cap": 56,
        },
        "policy": {
            "track": "B-track",
            "gating": "NON_GATING",
            "hypothesis_label": "[HYPO]",
            "must_not_merge_with": [
                "track_a_compression",
                "global_atom_network_pilot",
                "live_trading_trigger",
                "prophecy_hit_rate",
            ],
        },
        "generator": "run_question_semantic_rag_bridge_chain_v1.py@1.0.0",
    }
    chain_out.parent.mkdir(parents=True, exist_ok=True)
    chain_out.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "chain": str(chain_out), "insight": str(insight_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
