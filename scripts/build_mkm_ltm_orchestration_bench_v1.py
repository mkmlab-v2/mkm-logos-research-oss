#!/usr/bin/env python3
"""MKM LTM Orchestration OS bench — naive vs shallow vs orchestrated query path ([HYPO]).

Measures token proxy (tiktoken cl100k_base) and optional semantic RAG bridge latency.
MKM-reproducible metrics only — not DMF/external bench numbers.

  py scripts/build_mkm_ltm_orchestration_bench_v1.py
  py scripts/build_mkm_ltm_orchestration_bench_v1.py --run-bridge-chain
  py scripts/build_mkm_ltm_orchestration_bench_v1.py --run-bridge-chain --skip-panorama
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    DEFAULT_INDEX_PATH,
    LANE_OPS_PACKS,
    assemble_ops_memory_pins_text,
    load_index,
    nodes_for_resume,
    route_nodes_by_field_tags,
    utc_now_iso,
)

DEFAULT_OUT = SCRIPT_ROOT / "reports" / "mkm_ltm_orchestration_bench_v1_latest.json"
DEFAULT_CHAIN = SCRIPT_ROOT / "reports" / "question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_ROUTER = SCRIPT_ROOT / "reports" / "question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_INSIGHT = SCRIPT_ROOT / "docs" / "final" / "artifacts" / "magic_orb_question_insight_v1_latest.json"
DEFAULT_BLOOM = SCRIPT_ROOT / "docs" / "final" / "artifacts" / "magic_orb_graph_bloom_v1_latest.json"
DEFAULT_BRIDGE = (
    SCRIPT_ROOT / "docs" / "final" / "artifacts" / "semantic_rag_bridge_insight_bundle_v1_latest.json"
)

DEFAULT_QUERY = "욥이 고난을 받은 이유"
DEFAULT_QUERY_ID = "job_suffering_reason"


def _count_tokens(text: str, *, encoding_name: str = "cl100k_base") -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return {"tokens": len(enc.encode(text)), "method": f"tiktoken:{encoding_name}"}
    except Exception as exc:  # noqa: BLE001
        est = max(1, len(text) // 4)
        return {"tokens": est, "method": "char_div_4_estimate", "note": str(exc)}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _file_token_row(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    if not text.strip():
        return {"path": str(path.relative_to(SCRIPT_ROOT)).replace("\\", "/"), "present": False}
    counted = _count_tokens(text)
    return {
        "path": str(path.relative_to(SCRIPT_ROOT)).replace("\\", "/"),
        "present": True,
        "char_count": len(text),
        **counted,
    }


def _naive_baseline_text(root: Path) -> str:
    parts: list[str] = []
    for rel in ("MISSION_LOG.md", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"):
        p = root / rel
        if p.is_file():
            parts.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n\n---\n\n".join(parts)


def _lane_inject_text(root: Path, lane: str) -> str:
    index = load_index(DEFAULT_INDEX_PATH)
    lines: list[str] = []
    for _node_id, node in nodes_for_resume(index, lane=lane, root=root):
        lines.append(node.get("essence") or "")
        for tag in node.get("must_keep_tags") or []:
            lines.append(str(tag))
    return "\n".join(lines)


def _ops_routed_inject(root: Path, query: str) -> dict[str, Any]:
    index = load_index(DEFAULT_INDEX_PATH)
    routed = route_nodes_by_field_tags(index, query, max_nodes=4)
    shallow = assemble_ops_memory_pins_text(root, routed, include_slice=False)
    deep = assemble_ops_memory_pins_text(
        root,
        routed,
        include_slice=True,
        query=query,
        coordinate_filter=True,
    )
    shallow_count = _count_tokens(shallow)
    deep_count = _count_tokens(deep)
    return {
        "query": query,
        "routed_node_count": len(routed),
        "shallow_pins": {"char_count": len(shallow), **shallow_count},
        "deep_pins_with_slice": {"char_count": len(deep), **deep_count},
    }


def _orchestrated_artifact_bundle(
    *,
    router: Path,
    insight: Path,
    bloom: Path,
    bridge: Path,
    chain: Path,
) -> dict[str, Any]:
    rows = {
        "router_sidecar": _file_token_row(router),
        "insight_payload": _file_token_row(insight),
        "graph_bloom": _file_token_row(bloom),
        "bridge_bundle": _file_token_row(bridge),
        "chain_report": _file_token_row(chain),
    }
    present = [r for r in rows.values() if r.get("present")]
    total_tokens = sum(int(r.get("tokens") or 0) for r in present)
    total_chars = sum(int(r.get("char_count") or 0) for r in present)
    return {
        "artifacts": rows,
        "aggregate": {
            "artifact_count_present": len(present),
            "total_tokens": total_tokens,
            "total_chars": total_chars,
            "method": present[0].get("method") if present else None,
        },
    }


def _run_bridge_chain(
    root: Path,
    *,
    query: str,
    query_id: str,
    skip_panorama: bool,
) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(root / "scripts" / "run_question_semantic_rag_bridge_chain_v1.py"),
        "--query",
        query,
        "--query-id",
        query_id,
        "--skip-ann-lite",
        "--no-sync-public-by-query",
    ]
    if skip_panorama:
        cmd.append("--skip-panorama")
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    tail = ((proc.stderr or "") + (proc.stdout or ""))[-1500:]
    return {
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "latency_ms": elapsed_ms,
        "command": " ".join(cmd),
        "tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--run-bridge-chain", action="store_true")
    ap.add_argument("--skip-panorama", action="store_true")
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--query-id", default=DEFAULT_QUERY_ID)
    ap.add_argument("--sample-ops-query", default="logos router graphrag gold regression")
    args = ap.parse_args()
    root = args.workspace_root.resolve()

    if not DEFAULT_INDEX_PATH.is_file():
        print("FAIL: ops index missing — run build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    baseline_text = _naive_baseline_text(root)
    if not baseline_text.strip():
        print("FAIL: naive baseline empty (MISSION_LOG + CENTRAL)", file=sys.stderr)
        return 1

    baseline_count = _count_tokens(baseline_text)
    baseline_t = int(baseline_count["tokens"])

    lanes: dict[str, Any] = {}
    for lane in sorted(LANE_OPS_PACKS):
        inject = _lane_inject_text(root, lane)
        inject_count = _count_tokens(inject)
        inject_t = int(inject_count["tokens"])
        saved = max(0, baseline_t - inject_t)
        ratio = round(saved / baseline_t, 4) if baseline_t else 0.0
        lanes[lane] = {
            "inject_tokens": inject_t,
            "saved_tokens_vs_naive_baseline": saved,
            "savings_ratio_vs_naive_baseline": ratio,
            "char_count": len(inject),
            "method": inject_count.get("method"),
        }

    mean_lane_ratio = round(
        sum(row["savings_ratio_vs_naive_baseline"] for row in lanes.values()) / max(1, len(lanes)),
        4,
    )

    bridge_run: dict[str, Any] | None = None
    if args.run_bridge_chain:
        bridge_run = _run_bridge_chain(
            root,
            query=args.query,
            query_id=args.query_id,
            skip_panorama=args.skip_panorama,
        )
        if not bridge_run.get("ok"):
            print(f"FAIL: bridge chain exit {bridge_run.get('exit_code')}", file=sys.stderr)
            print(bridge_run.get("tail", ""), file=sys.stderr)
            return 1

    orchestrated = _orchestrated_artifact_bundle(
        router=DEFAULT_ROUTER,
        insight=DEFAULT_INSIGHT,
        bloom=DEFAULT_BLOOM,
        bridge=DEFAULT_BRIDGE,
        chain=DEFAULT_CHAIN,
    )
    orch_t = int(orchestrated["aggregate"]["total_tokens"])
    orch_saved = max(0, baseline_t - orch_t)
    orch_ratio = round(orch_saved / baseline_t, 4) if baseline_t else 0.0

    ops_sample = _ops_routed_inject(root, args.sample_ops_query)
    shallow_t = int(ops_sample["shallow_pins"]["tokens"])
    deep_t = int(ops_sample["deep_pins_with_slice"]["tokens"])

    doc: dict[str, Any] = {
        "schema": "mkm_ltm_orchestration_bench_v1",
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] orchestration token/latency bench — not commercial SLA or DMF claim",
        "generated_at_utc": utc_now_iso(),
        "query_context": {
            "bridge_query": args.query,
            "bridge_query_id": args.query_id,
            "sample_ops_query": args.sample_ops_query,
        },
        "naive_baseline": {
            "sources": ["MISSION_LOG.md", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"],
            "char_count": len(baseline_text),
            **baseline_count,
        },
        "shallow_lane_inject": {
            "lanes": lanes,
            "aggregate": {
                "lane_count": len(lanes),
                "mean_savings_ratio_vs_naive_baseline": mean_lane_ratio,
            },
        },
        "orchestrated_query_path": {
            **orchestrated,
            "saved_tokens_vs_naive_baseline": orch_saved,
            "savings_ratio_vs_naive_baseline": orch_ratio,
        },
        "ops_memory_routing_sample": {
            **ops_sample,
            "shallow_saved_vs_naive": max(0, baseline_t - shallow_t),
            "deep_saved_vs_naive": max(0, baseline_t - deep_t),
        },
        "bridge_chain_run": bridge_run,
        "policy": {
            "gating": "NON_GATING",
            "must_not_merge_with": ["track_a_compression", "live_trading_trigger", "dmf_external_kpi"],
            "note": "Use raw/repair dual reporting elsewhere; this bench is inject-size + latency only.",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"WROTE: {args.out}")
    print(
        f"naive_baseline_tokens={baseline_t} "
        f"orchestrated_tokens={orch_t} "
        f"orchestrated_savings_ratio={orch_ratio} "
        f"mean_lane_savings_ratio={mean_lane_ratio}"
    )
    if bridge_run:
        print(f"bridge_chain_latency_ms={bridge_run['latency_ms']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
